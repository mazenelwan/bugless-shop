from io import StringIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from store.models import (
    Category,
    ContactMessage,
    ContactMessageEvent,
    HomeContent,
    Order,
    OrderEvent,
    OrderItem,
    Product,
    ProductImage,
    ProductVariant,
    Promotion,
)


class AdminConfigurationTests(TestCase):
    def test_foundation_models_are_available_in_admin(self):
        expected_models = (
            get_user_model(),
            Category,
            Product,
            Promotion,
            Order,
            OrderEvent,
            ContactMessage,
            ContactMessageEvent,
            HomeContent,
        )

        for model in expected_models:
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)

        product_admin = admin.site._registry[Product]
        inline_models = {inline.model for inline in product_admin.inlines}
        self.assertEqual(inline_models, {ProductImage, ProductVariant})

    def test_user_add_page_uses_email_without_a_username_field(self):
        User = get_user_model()
        staff_user = User.objects.create_superuser(
            email="admin@example.com",
            password="Admin-password-928!",
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse("admin:accounts_user_add"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="email"')
        self.assertNotContains(response, 'name="username"')

    def test_order_and_item_snapshots_are_read_only_in_admin(self):
        product_admin = admin.site._registry[Product]
        order_admin = admin.site._registry[Order]
        item_inline = order_admin.inlines[0](Order, admin.site)
        event_inline = order_admin.inlines[1](Order, admin.site)
        contact_admin = admin.site._registry[ContactMessage]

        self.assertIn("public_id", product_admin.readonly_fields)
        self.assertTrue(
            {
                "number",
                "confirmation_token",
                "idempotency_key",
                "request_fingerprint",
                "customer_name",
                "subtotal_amount",
                "discount_amount",
                "delivery_fee",
                "tax_amount",
                "total_amount",
                "status",
                "payment_status",
                "inventory_restocked_at",
            }.issubset(order_admin.readonly_fields)
        )
        self.assertFalse(order_admin.has_add_permission(None))
        self.assertFalse(order_admin.has_change_permission(None))
        self.assertFalse(order_admin.has_delete_permission(None))
        self.assertFalse(item_inline.can_delete)
        self.assertFalse(item_inline.has_add_permission(None))
        self.assertFalse(event_inline.can_delete)
        self.assertFalse(event_inline.has_add_permission(None))
        self.assertIn("notes", order_admin.readonly_fields)
        self.assertTrue(
            {
                "product_public_id",
                "variant_public_id",
                "product_name",
                "product_sku",
                "variant_label",
                "price",
                "quantity",
                "subtotal",
            }.issubset(item_inline.readonly_fields)
        )
        self.assertIs(item_inline.model, OrderItem)
        self.assertTrue(
            {
                "submission_id",
                "request_fingerprint",
                "name",
                "email",
                "phone",
                "subject",
                "message",
                "status",
            }.issubset(contact_admin.readonly_fields)
        )
        self.assertNotIn("status", contact_admin.list_editable)
        self.assertFalse(contact_admin.has_add_permission(None))
        self.assertFalse(contact_admin.has_change_permission(None))
        self.assertFalse(contact_admin.has_delete_permission(None))
        self.assertEqual(contact_admin.actions, ())

        self.assertEqual(
            set(order_admin.actions),
            {
                "mark_confirmed",
                "mark_preparing",
                "mark_shipped",
                "mark_delivered",
                "cancel_and_restock",
            },
        )
        self.assertNotIn("mark_payment_paid", order_admin.actions)
        self.assertNotIn("mark_payment_refunded", order_admin.actions)

        order_event_admin = admin.site._registry[OrderEvent]
        contact_event_admin = admin.site._registry[ContactMessageEvent]
        for event_admin in (order_event_admin, contact_event_admin):
            self.assertFalse(event_admin.has_add_permission(None))
            self.assertFalse(event_admin.has_change_permission(None))
            self.assertFalse(event_admin.has_delete_permission(None))

    def test_only_order_status_actions_are_exposed_and_permission_gated(self):
        User = get_user_model()
        staff_user = User.objects.create_user(
            email="operator@example.com",
            password="Admin-password-928!",
            is_staff=True,
        )
        request = RequestFactory().get("/admin/store/order/")
        request.user = staff_user
        order_admin = admin.site._registry[Order]
        contact_admin = admin.site._registry[ContactMessage]

        self.assertNotIn("mark_confirmed", order_admin.get_actions(request))
        self.assertNotIn("cancel_and_restock", order_admin.get_actions(request))
        self.assertNotIn("mark_read", contact_admin.get_actions(request))
        self.assertNotIn("mark_payment_paid", order_admin.get_actions(request))
        self.assertNotIn("mark_payment_refunded", order_admin.get_actions(request))

        permissions = Permission.objects.filter(
            content_type__app_label="store",
            codename__in=(
                "transition_order",
                "manage_contactmessage",
            ),
        )
        staff_user.user_permissions.add(*permissions)
        request.user = User.objects.get(pk=staff_user.pk)

        self.assertIn("mark_confirmed", order_admin.get_actions(request))
        self.assertNotIn("cancel_and_restock", order_admin.get_actions(request))
        self.assertNotIn("mark_read", contact_admin.get_actions(request))

    def test_catalog_manager_can_create_update_and_delete_current_products(self):
        call_command("configure_staff_roles", stdout=StringIO())
        category = Category.objects.create(name="Dashboard products")
        user = get_user_model().objects.create_user(
            email="catalog-dashboard@example.com",
            password="Admin-password-928!",
            is_staff=True,
        )
        user.groups.add(Group.objects.get(name="Catalog Manager"))
        self.client.force_login(user)

        add_payload = {
            "legacy_id": "",
            "name": "Dashboard shirt",
            "slug": "",
            "sku": "DASH-SHIRT-01",
            "description": "Managed through the simple product page.",
            "price": "250.00",
            "old_price": "300.00",
            "rating": "4.5",
            "category": str(category.pk),
            "display_order": "1",
            "stock": "8",
            "is_active": "on",
            "images-TOTAL_FORMS": "1",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
            "images-0-image": "https://example.com/dashboard-shirt.jpg",
            "images-0-alt_text": "Dashboard shirt",
            "images-0-is_primary": "on",
            "images-0-display_order": "0",
            "variants-TOTAL_FORMS": "0",
            "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "0",
            "variants-MAX_NUM_FORMS": "1000",
            "_save": "Save",
        }
        response = self.client.post(reverse("admin:store_product_add"), add_payload)

        self.assertRedirects(response, reverse("admin:store_product_changelist"))
        product = Product.objects.get(sku="DASH-SHIRT-01")
        image = product.images.get()
        self.assertEqual(product.name, "Dashboard shirt")
        self.assertEqual(image.alt_text, "Dashboard shirt")

        change_payload = {
            **add_payload,
            "name": "Updated dashboard shirt",
            "stock": "12",
            "images-INITIAL_FORMS": "1",
            "images-0-id": str(image.pk),
        }
        response = self.client.post(
            reverse("admin:store_product_change", args=(product.pk,)),
            change_payload,
        )

        self.assertRedirects(response, reverse("admin:store_product_changelist"))
        product.refresh_from_db()
        self.assertEqual(product.name, "Updated dashboard shirt")
        self.assertEqual(product.stock, 12)

        response = self.client.post(
            reverse("admin:store_product_delete", args=(product.pk,)),
            {"post": "yes"},
        )

        self.assertRedirects(response, reverse("admin:store_product_changelist"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_staff_roles_match_the_read_only_and_product_crud_dashboard(self):
        call_command("configure_staff_roles", stdout=StringIO())

        catalog_permissions = set(
            Group.objects.get(name="Catalog Manager").permissions.values_list(
                "codename",
                flat=True,
            )
        )
        self.assertTrue(
            {
                "add_product",
                "change_product",
                "delete_product",
                "add_productimage",
                "change_productimage",
                "delete_productimage",
                "add_productvariant",
                "change_productvariant",
                "delete_productvariant",
            }.issubset(catalog_permissions)
        )

        manager_permissions = set(
            Group.objects.get(name="Store Manager").permissions.values_list(
                "codename",
                flat=True,
            )
        )
        self.assertIn("transition_order", manager_permissions)
        self.assertIn("cancel_order", manager_permissions)
        self.assertNotIn("change_order", manager_permissions)
        self.assertNotIn("record_order_payment", manager_permissions)
        self.assertNotIn("refund_order", manager_permissions)
        self.assertIn("view_contactmessage", manager_permissions)
        self.assertNotIn("change_contactmessage", manager_permissions)
        self.assertNotIn("manage_contactmessage", manager_permissions)
