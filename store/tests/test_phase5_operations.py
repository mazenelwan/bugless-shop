from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import TestCase

from store.management.commands.configure_staff_roles import ROLE_PERMISSIONS
from store.models import (
    Category,
    ContactMessage,
    ContactMessageEvent,
    Order,
    OrderEvent,
    OrderItem,
    Product,
    ProductVariant,
    Promotion,
)
from store.services.operations import (
    OperationsError,
    transition_contact_message,
    transition_order,
    transition_payment,
)


class OperationsServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="operator@example.com",
            password="Strong-password-829!",
            is_staff=True,
        )
        self.category = Category.objects.create(name="Operations")
        self.product = Product.objects.create(
            name="Operations shirt",
            sku="OPS-SHIRT",
            price=Decimal("100.00"),
            stock=3,
            category=self.category,
        )

    def grant(self, *codenames):
        permissions = Permission.objects.filter(
            content_type__app_label="store",
            codename__in=codenames,
        )
        self.user.user_permissions.add(*permissions)
        self.user = get_user_model().objects.get(pk=self.user.pk)

    def create_order(self, **overrides):
        values = {
            "customer_name": "Ada",
            "email": "ada@example.com",
            "phone": "01000000000",
            "address": "Cairo",
            "subtotal_amount": Decimal("200.00"),
            "total_amount": Decimal("200.00"),
        }
        values.update(overrides)
        return Order.objects.create(**values)

    def add_product_item(self, order, product=None, quantity=2):
        product = product or self.product
        return OrderItem.objects.create(
            order=order,
            product=product,
            product_public_id=product.public_id,
            product_name=product.name,
            product_sku=product.sku,
            price=product.price,
            quantity=quantity,
            subtotal=product.price * quantity,
        )

    def test_forward_transition_is_sequential_idempotent_and_audited(self):
        self.grant("transition_order")
        order = self.create_order()

        changed = transition_order(order.pk, Order.Status.CONFIRMED, self.user)
        replay = transition_order(order.pk, Order.Status.CONFIRMED, self.user)

        self.assertTrue(changed.changed)
        self.assertFalse(replay.changed)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        event = order.events.get()
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.from_status, Order.Status.PENDING)
        self.assertEqual(event.to_status, Order.Status.CONFIRMED)

        with self.assertRaises(OperationsError):
            transition_order(order.pk, Order.Status.DELIVERED, self.user)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)

    def test_order_transition_requires_explicit_permission(self):
        order = self.create_order()

        with self.assertRaises(PermissionDenied):
            transition_order(order.pk, Order.Status.CONFIRMED, self.user)

    def test_cancellation_restocks_product_exactly_once_and_audits(self):
        self.grant("cancel_order")
        order = self.create_order()
        self.add_product_item(order)

        first = transition_order(order.pk, Order.Status.CANCELLED, self.user)
        second = transition_order(order.pk, Order.Status.CANCELLED, self.user)

        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertIsNotNone(order.inventory_restocked_at)
        self.assertEqual(order.events.count(), 2)
        self.assertEqual(
            order.events.filter(
                event_type=OrderEvent.EventType.INVENTORY_RESTOCKED
            ).count(),
            1,
        )

    def test_cancellation_restocks_variant_not_product(self):
        self.grant("cancel_order")
        variant = ProductVariant.objects.create(
            product=self.product,
            size="M",
            color="Black",
            stock=2,
        )
        order = self.create_order(subtotal_amount="300.00", total_amount="300.00")
        OrderItem.objects.create(
            order=order,
            product=self.product,
            variant=variant,
            product_public_id=self.product.public_id,
            variant_public_id=variant.public_id,
            product_name=self.product.name,
            product_sku=self.product.sku,
            variant_label=variant.label,
            selected_size=variant.size,
            selected_color=variant.color,
            price=self.product.price,
            quantity=3,
            subtotal=Decimal("300.00"),
        )

        transition_order(order.pk, Order.Status.CANCELLED, self.user)

        self.product.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(variant.stock, 5)

    def test_missing_inventory_target_rejects_without_partial_restock(self):
        self.grant("cancel_order")
        order = self.create_order(subtotal_amount="300.00", total_amount="300.00")
        self.add_product_item(order, quantity=2)
        missing_product = Product.objects.create(
            name="Deleted shirt",
            sku="DELETED-SHIRT",
            price="100.00",
            stock=0,
            category=self.category,
        )
        self.add_product_item(order, product=missing_product, quantity=1)
        missing_product.delete()

        with self.assertRaises(OperationsError):
            transition_order(order.pk, Order.Status.CANCELLED, self.user)

        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertIsNone(order.inventory_restocked_at)
        self.assertEqual(order.events.count(), 0)

    def test_paid_order_must_be_refunded_before_cancellation(self):
        self.grant("cancel_order")
        order = self.create_order(payment_status=Order.PaymentStatus.PAID)
        self.add_product_item(order)

        with self.assertRaisesMessage(OperationsError, "refund the payment"):
            transition_order(order.pk, Order.Status.CANCELLED, self.user)

        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_payment_receipt_and_refund_are_separately_permitted_and_audited(self):
        self.grant("record_order_payment")
        order = self.create_order()

        transition_payment(order.pk, Order.PaymentStatus.PAID, self.user)
        with self.assertRaises(PermissionDenied):
            transition_payment(order.pk, Order.PaymentStatus.REFUNDED, self.user)

        self.grant("refund_order")
        transition_payment(order.pk, Order.PaymentStatus.REFUNDED, self.user)

        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.REFUNDED)
        self.assertEqual(
            list(
                order.events.filter(
                    event_type=OrderEvent.EventType.PAYMENT_CHANGED
                ).values_list("from_payment_status", "to_payment_status")
            ),
            [
                (Order.PaymentStatus.UNPAID, Order.PaymentStatus.PAID),
                (Order.PaymentStatus.PAID, Order.PaymentStatus.REFUNDED),
            ],
        )

    def test_promotion_usage_is_not_credited_on_cancellation(self):
        self.grant("cancel_order")
        promotion = Promotion.objects.create(
            code="OPS10",
            name="Operations promo",
            discount_type=Promotion.DiscountType.FIXED,
            value="10.00",
            times_used=1,
        )
        order = self.create_order(
            promotion=promotion,
            promotion_code=promotion.code,
            discount_amount="10.00",
            total_amount="190.00",
        )
        self.add_product_item(order)

        transition_order(order.pk, Order.Status.CANCELLED, self.user)

        promotion.refresh_from_db()
        self.assertEqual(promotion.times_used, 1)

    def test_audit_failure_rolls_back_status_and_stock(self):
        self.grant("cancel_order")
        order = self.create_order()
        self.add_product_item(order)

        with patch.object(OrderEvent.objects, "create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                transition_order(order.pk, Order.Status.CANCELLED, self.user)

        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertIsNone(order.inventory_restocked_at)

    def test_contact_workflow_is_permission_checked_sequential_and_audited(self):
        message = ContactMessage.objects.create(
            request_fingerprint="a" * 64,
            name="Ada",
            email="ada@example.com",
            message="Hello",
        )
        with self.assertRaises(PermissionDenied):
            transition_contact_message(message.pk, ContactMessage.Status.READ, self.user)

        self.grant("manage_contactmessage")
        with self.assertRaises(OperationsError):
            transition_contact_message(message.pk, ContactMessage.Status.REPLIED, self.user)

        first = transition_contact_message(message.pk, ContactMessage.Status.READ, self.user)
        replay = transition_contact_message(message.pk, ContactMessage.Status.READ, self.user)
        second = transition_contact_message(
            message.pk,
            ContactMessage.Status.REPLIED,
            self.user,
        )

        self.assertTrue(first.changed)
        self.assertFalse(replay.changed)
        self.assertTrue(second.changed)
        message.refresh_from_db()
        self.assertEqual(message.status, ContactMessage.Status.REPLIED)
        self.assertEqual(message.events.count(), 2)
        self.assertTrue(
            message.events.filter(
                event_type=ContactMessageEvent.EventType.STATUS_CHANGED,
                actor=self.user,
            ).exists()
        )


class StaffRoleCommandTests(TestCase):
    def test_command_creates_exact_idempotent_role_permissions(self):
        output = StringIO()

        call_command("configure_staff_roles", stdout=output)
        call_command("configure_staff_roles", stdout=output)

        self.assertEqual(
            set(Group.objects.filter(name__in=ROLE_PERMISSIONS).values_list("name", flat=True)),
            set(ROLE_PERMISSIONS),
        )
        for role_name, expected_codenames in ROLE_PERMISSIONS.items():
            with self.subTest(role=role_name):
                group = Group.objects.get(name=role_name)
                actual_codenames = set(
                    group.permissions.filter(
                        content_type__app_label="store"
                    ).values_list("codename", flat=True)
                )
                self.assertEqual(actual_codenames, expected_codenames)
