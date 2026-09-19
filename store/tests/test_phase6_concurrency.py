import threading
import uuid
from decimal import Decimal
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import connection, connections
from django.test import TransactionTestCase

from store.models import Category, Order, OrderEvent, OrderItem, Product, Promotion
from store.services.checkout import CheckoutError, create_checkout, parse_checkout_request
from store.services.operations import transition_order


@skipUnless(
    connection.vendor == "postgresql",
    "Phase 6 race tests require PostgreSQL row locks.",
)
class PostgreSQLConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.category = Category.objects.create(name="Concurrency")
        self.customer = {
            "name": "Concurrency Learner",
            "email": "race@example.com",
            "phone": "+20 100 000 0000",
            "address": "1 Local Test Street",
            "city": "Cairo",
            "notes": "",
        }

    def make_product(self, sku, *, stock=1):
        return Product.objects.create(
            name=f"Race product {sku}",
            sku=sku,
            price=Decimal("100.00"),
            stock=stock,
            category=self.category,
        )

    def payload(self, product, *, key=None, promotion=""):
        return parse_checkout_request(
            {
                "version": 1,
                "idempotencyKey": str(key or uuid.uuid4()),
                "customer": self.customer,
                "promotionCode": promotion,
                "lines": [
                    {
                        "productId": str(product.public_id),
                        "variantId": None,
                        "quantity": 1,
                    }
                ],
            }
        )

    def race(self, *operations):
        barrier = threading.Barrier(len(operations))
        outcomes = [None] * len(operations)

        def run(index, operation):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                outcomes[index] = ("result", operation())
            except BaseException as error:  # Captured and asserted in the main thread.
                outcomes[index] = ("error", error)
            finally:
                connections.close_all()

        threads = [
            threading.Thread(target=run, args=(index, operation), daemon=True)
            for index, operation in enumerate(operations)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads), "race timed out")
        self.assertTrue(all(outcome is not None for outcome in outcomes))
        return outcomes

    def test_identical_concurrent_checkout_creates_once_and_replays_once(self):
        product = self.make_product("IDEMPOTENT", stock=1)
        key = uuid.uuid4()
        first_payload = self.payload(product, key=key)
        second_payload = self.payload(product, key=key)

        outcomes = self.race(
            lambda: create_checkout(first_payload, AnonymousUser()),
            lambda: create_checkout(second_payload, AnonymousUser()),
        )

        self.assertEqual([kind for kind, _ in outcomes], ["result", "result"])
        results = [value for _, value in outcomes]
        self.assertEqual(sorted(result.replayed for result in results), [False, True])
        self.assertEqual(results[0].order.pk, results[1].order.pk)
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

    def test_distinct_checkouts_competing_for_last_item_have_one_winner(self):
        product = self.make_product("LAST-STOCK", stock=1)
        first_payload = self.payload(product)
        second_payload = self.payload(product)

        outcomes = self.race(
            lambda: create_checkout(first_payload, AnonymousUser()),
            lambda: create_checkout(second_payload, AnonymousUser()),
        )

        results = [value for kind, value in outcomes if kind == "result"]
        errors = [value for kind, value in outcomes if kind == "error"]
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CheckoutError)
        self.assertEqual(errors[0].code, "insufficient_stock")
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)

    def test_shared_promotion_limit_is_consumed_by_only_one_checkout(self):
        first_product = self.make_product("PROMO-A", stock=2)
        second_product = self.make_product("PROMO-B", stock=2)
        promotion = Promotion.objects.create(
            code="ONEUSE",
            name="One use only",
            discount_type=Promotion.DiscountType.FIXED,
            value=Decimal("10.00"),
            usage_limit=1,
            is_active=True,
        )
        first_payload = self.payload(first_product, promotion=promotion.code)
        second_payload = self.payload(second_product, promotion=promotion.code)

        outcomes = self.race(
            lambda: create_checkout(first_payload, AnonymousUser()),
            lambda: create_checkout(second_payload, AnonymousUser()),
        )

        results = [value for kind, value in outcomes if kind == "result"]
        errors = [value for kind, value in outcomes if kind == "error"]
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CheckoutError)
        self.assertEqual(errors[0].code, "promotion_unavailable")
        promotion.refresh_from_db()
        first_product.refresh_from_db()
        second_product.refresh_from_db()
        self.assertEqual(promotion.times_used, 1)
        self.assertEqual(first_product.stock + second_product.stock, 3)
        self.assertEqual(Order.objects.count(), 1)

    def test_duplicate_cancellation_restocks_and_audits_exactly_once(self):
        product = self.make_product("CANCEL", stock=0)
        order = Order.objects.create(
            customer_name="Concurrency Learner",
            email="race@example.com",
            phone="01000000000",
            address="Local test",
            subtotal_amount=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_public_id=product.public_id,
            product_name=product.name,
            product_sku=product.sku,
            price=product.price,
            quantity=1,
            subtotal=product.price,
        )
        actor = get_user_model().objects.create_superuser(
            email="race-operator@example.com",
            password="Local-test-password-829!",
        )

        def cancel():
            thread_actor = get_user_model().objects.get(pk=actor.pk)
            return transition_order(order.pk, Order.Status.CANCELLED, thread_actor)

        outcomes = self.race(cancel, cancel)

        self.assertEqual([kind for kind, _ in outcomes], ["result", "result"])
        self.assertEqual(
            sorted(result.changed for _, result in outcomes),
            [False, True],
        )
        product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(product.stock, 1)
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertIsNotNone(order.inventory_restocked_at)
        self.assertEqual(
            order.events.filter(
                event_type=OrderEvent.EventType.INVENTORY_RESTOCKED
            ).count(),
            1,
        )
        self.assertEqual(
            order.events.filter(event_type=OrderEvent.EventType.STATUS_CHANGED).count(),
            1,
        )
