import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from store.models import (
    Category,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    Promotion,
)
from store.services.checkout import create_checkout, parse_checkout_request


class CheckoutPhase4Tests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Shirts")
        self.product = Product.objects.create(
            name="Server shirt",
            sku="SERVER-SHIRT",
            price=Decimal("100.00"),
            stock=10,
            category=self.category,
        )
        self.customer = {
            "name": "  Ada Lovelace  ",
            "email": "  ADA@Example.COM ",
            "phone": "+20 100 000 0000",
            "address": "  1 Cairo Street  ",
            "city": " Cairo ",
            "notes": " Leave at reception ",
        }

    def line(self, product=None, *, variant=None, quantity=1, **extra):
        value = {
            "productId": str((product or self.product).public_id),
            "variantId": str(variant.public_id) if variant else None,
            "quantity": quantity,
        }
        value.update(extra)
        return value

    def payload(self, *, lines=None, key=None, promotion="", customer=None, **extra):
        value = {
            "version": 1,
            "idempotencyKey": str(key or uuid.uuid4()),
            "customer": self.customer if customer is None else customer,
            "promotionCode": promotion,
            "lines": lines or [self.line()],
        }
        value.update(extra)
        return value

    def post_create(self, payload=None, *, raw=None, content_type="application/json"):
        body = raw if raw is not None else json.dumps(payload or self.payload())
        return self.client.post(
            reverse("store:create_order"),
            data=body,
            content_type=content_type,
        )

    def post_quote(self, *, lines=None, promotion=""):
        return self.client.post(
            reverse("store:quote_order"),
            data=json.dumps(
                {
                    "version": 1,
                    "promotionCode": promotion,
                    "lines": lines or [self.line()],
                }
            ),
            content_type="application/json",
        )

    def promotion(self, code="SAVE10", **overrides):
        values = {
            "code": code,
            "name": "Ten percent",
            "discount_type": Promotion.DiscountType.PERCENTAGE,
            "value": Decimal("10.00"),
            "is_active": True,
        }
        values.update(overrides)
        return Promotion.objects.create(**values)

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["fields"], dict)

    def test_create_uses_server_money_normalizes_customer_and_snapshots_item(self):
        response = self.post_create()

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(
            {
                "subtotal": data["subtotal"],
                "discount": data["discount"],
                "delivery": data["delivery"],
                "tax": data["tax"],
                "total": data["total"],
            },
            {
                "subtotal": "100.00",
                "discount": "0.00",
                "delivery": "0.00",
                "tax": "0.00",
                "total": "100.00",
            },
        )
        self.assertFalse(data["replayed"])
        self.assertIn(data["orderNumber"], data["confirmationUrl"])

        order = Order.objects.get()
        item = order.items.get()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)
        self.assertEqual(order.customer_name, "Ada Lovelace")
        self.assertEqual(order.email, "ada@example.com")
        self.assertEqual(order.address, "1 Cairo Street")
        self.assertEqual(len(order.request_fingerprint), 64)
        self.assertEqual(item.product_public_id, self.product.public_id)
        self.assertEqual(item.price, Decimal("100.00"))
        self.assertEqual(item.subtotal, Decimal("100.00"))

    def test_unknown_client_price_is_rejected_without_mutation(self):
        response = self.post_create(
            self.payload(lines=[self.line(price="0.01")])
        )

        self.assert_error(response, 400, "invalid_payload")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertFalse(Order.objects.exists())

    def test_authenticated_order_is_owned_and_visible_in_account_history(self):
        user = get_user_model().objects.create(email="customer@example.com")
        self.client.force_login(user)
        customer = dict(self.customer, email="customer@example.com")

        response = self.post_create(self.payload(customer=customer))

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.customer, user)
        history = self.client.get(reverse("accounts:order_list"))
        self.assertContains(history, order.number)

    def test_checkout_prefills_signed_in_identity_and_exposes_named_api_urls(self):
        user = get_user_model().objects.create(
            email="customer@example.com",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("store:checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Ada Lovelace"')
        self.assertContains(response, 'value="customer@example.com"')
        self.assertContains(
            response,
            f'data-create-url="{reverse("store:create_order")}"',
        )
        self.assertContains(
            response,
            f'data-quote-url="{reverse("store:quote_order")}"',
        )
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_identical_retry_replays_without_second_stock_or_usage_change(self):
        promotion = self.promotion()
        key = uuid.uuid4()
        payload = self.payload(
            key=key,
            promotion="save10",
            lines=[self.line(quantity=2)],
        )
        equivalent_retry = self.payload(
            key=key,
            promotion=" SAVE10 ",
            lines=[self.line(), self.line()],
        )

        first = self.post_create(payload)
        second = self.post_create(equivalent_retry)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.json()["data"]["orderNumber"],
            second.json()["data"]["orderNumber"],
        )
        self.assertTrue(second.json()["data"]["replayed"])
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        promotion.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertEqual(promotion.times_used, 1)

    def test_changed_retry_key_reuse_conflicts_without_mutation(self):
        key = uuid.uuid4()
        first = self.post_create(self.payload(key=key))
        changed = self.post_create(
            self.payload(key=key, lines=[self.line(quantity=2)])
        )

        self.assertEqual(first.status_code, 201)
        self.assert_error(changed, 409, "idempotency_conflict")
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)

    def test_duplicate_lines_coalesce_into_one_snapshot(self):
        response = self.post_create(
            self.payload(lines=[self.line(quantity=2), self.line(quantity=3)])
        )

        self.assertEqual(response.status_code, 201)
        item = OrderItem.objects.get()
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.subtotal, Decimal("500.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_quote_calculates_current_money_without_mutation(self):
        promotion = self.promotion()
        response = self.post_quote(promotion="save10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["total"], "90.00")
        self.assertEqual(response.json()["data"]["promotion"]["code"], "SAVE10")
        self.product.refresh_from_db()
        promotion.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(promotion.times_used, 0)
        self.assertFalse(Order.objects.exists())

    def test_variant_stock_is_the_only_stock_decremented(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            size="M",
            color="Black",
            stock=3,
        )
        response = self.post_create(
            self.payload(lines=[self.line(variant=variant, quantity=2)])
        )

        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        variant.refresh_from_db()
        item = OrderItem.objects.get()
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(variant.stock, 1)
        self.assertEqual(item.variant_public_id, variant.public_id)
        self.assertEqual(item.variant_label, "Black / M")

    def test_variant_is_required_and_must_belong_to_product(self):
        ProductVariant.objects.create(product=self.product, size="M", stock=3)
        missing = self.post_create(self.payload())
        self.assert_error(missing, 409, "variant_required")

        other = Product.objects.create(
            name="Other",
            sku="OTHER",
            price=Decimal("50.00"),
            stock=0,
            category=self.category,
        )
        other_variant = ProductVariant.objects.create(
            product=other,
            size="M",
            stock=3,
        )
        wrong = self.post_create(
            self.payload(lines=[self.line(variant=other_variant)])
        )
        self.assert_error(wrong, 409, "variant_unavailable")
        self.assertFalse(Order.objects.exists())

    def test_inactive_and_insufficient_catalog_state_are_rejected(self):
        self.product.is_active = False
        self.product.save(update_fields=("is_active", "updated_at"))
        inactive = self.post_create(self.payload())
        self.assert_error(inactive, 409, "product_unavailable")

        self.product.is_active = True
        self.product.stock = 1
        self.product.save(update_fields=("is_active", "stock", "updated_at"))
        insufficient = self.post_create(
            self.payload(lines=[self.line(quantity=2)])
        )
        self.assert_error(insufficient, 409, "insufficient_stock")
        self.assertFalse(Order.objects.exists())

    def test_scoped_percentage_rounds_half_up_and_honors_cap(self):
        self.product.price = Decimal("100.05")
        self.product.save(update_fields=("price", "updated_at"))
        promotion = self.promotion(maximum_discount=Decimal("10.01"))
        promotion.products.add(self.product)

        response = self.post_create(self.payload(promotion="SAVE10"))

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["subtotal"], "100.05")
        self.assertEqual(data["discount"], "10.01")
        self.assertEqual(data["total"], "90.04")

    def test_fixed_promotion_is_capped_to_eligible_subtotal(self):
        promotion = self.promotion(
            code="FIXED",
            name="Fixed",
            discount_type=Promotion.DiscountType.FIXED,
            value=Decimal("500.00"),
        )
        promotion.categories.add(self.category)

        response = self.post_create(self.payload(promotion="fixed"))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["discount"], "100.00")
        self.assertEqual(response.json()["data"]["total"], "0.00")

    def test_promotion_minimum_scope_window_and_global_limit_rejections(self):
        minimum = self.promotion(code="MIN", minimum_subtotal=Decimal("101.00"))
        self.assert_error(
            self.post_quote(promotion=minimum.code),
            400,
            "promotion_minimum_not_met",
        )

        other_category = Category.objects.create(name="Other category")
        scoped = self.promotion(code="SCOPED")
        scoped.categories.add(other_category)
        self.assert_error(
            self.post_quote(promotion=scoped.code),
            400,
            "promotion_not_applicable",
        )

        future = self.promotion(
            code="FUTURE",
            starts_at=timezone.now() + timedelta(days=1),
        )
        self.assert_error(
            self.post_quote(promotion=future.code),
            409,
            "promotion_unavailable",
        )

        exhausted = self.promotion(code="USED", usage_limit=1, times_used=1)
        self.assert_error(
            self.post_quote(promotion=exhausted.code),
            409,
            "promotion_unavailable",
        )
        self.assertFalse(Order.objects.exists())

    def test_guest_per_customer_promotion_limit_uses_normalized_email(self):
        promotion = self.promotion(per_customer_limit=1)
        first = self.post_create(self.payload(promotion=promotion.code))
        self.assertEqual(first.status_code, 201)

        second_customer = dict(self.customer, email="ADA@example.com")
        second = self.post_create(
            self.payload(promotion=promotion.code, customer=second_customer)
        )
        self.assert_error(second, 409, "promotion_customer_limit")

        third_customer = dict(self.customer, email="grace@example.com")
        third = self.post_create(
            self.payload(promotion=promotion.code, customer=third_customer)
        )
        self.assertEqual(third.status_code, 201)
        promotion.refresh_from_db()
        self.assertEqual(promotion.times_used, 2)

    def test_validation_rejects_media_json_schema_customer_and_quantity(self):
        self.assert_error(
            self.post_create(content_type="text/plain"),
            415,
            "invalid_content_type",
        )
        self.assert_error(
            self.post_create(raw="{"),
            400,
            "invalid_json",
        )
        self.assert_error(
            self.post_create(raw='{"version":1,"version":1}'),
            400,
            "invalid_json",
        )
        self.assert_error(
            self.post_create(self.payload(version="1")),
            400,
            "invalid_payload",
        )
        self.assert_error(
            self.post_create(self.payload(lines=[self.line(quantity=True)])),
            400,
            "invalid_cart",
        )
        invalid_customer = dict(self.customer, email="not-an-email", phone="12")
        invalid = self.post_create(self.payload(customer=invalid_customer))
        self.assert_error(invalid, 400, "invalid_customer")
        self.assertIn("customer.email", invalid.json()["error"]["fields"])
        self.assertIn("customer.phone", invalid.json()["error"]["fields"])
        non_text = self.post_create(
            self.payload(customer=dict(self.customer, name=123))
        )
        self.assert_error(non_text, 400, "invalid_customer")
        self.assertFalse(Order.objects.exists())

    @override_settings(CHECKOUT_MAX_BODY_BYTES=20)
    def test_body_size_limit_rejects_before_domain_validation(self):
        response = self.post_create()
        self.assert_error(response, 400, "payload_too_large")
        self.assertFalse(Order.objects.exists())

    def test_line_count_and_combined_quantity_limits_are_enforced(self):
        too_many = self.post_create(self.payload(lines=[self.line()] * 51))
        self.assert_error(too_many, 400, "invalid_cart")

        combined = self.post_create(
            self.payload(lines=[self.line(quantity=50), self.line(quantity=50)])
        )
        self.assert_error(combined, 400, "invalid_cart")
        self.assertFalse(Order.objects.exists())

    def test_unknown_or_stale_uuid_is_rejected(self):
        response = self.post_create(
            self.payload(
                lines=[
                    {
                        "productId": str(uuid.uuid4()),
                        "variantId": None,
                        "quantity": 1,
                    }
                ]
            )
        )
        self.assert_error(response, 409, "product_unavailable")
        self.assertFalse(Order.objects.exists())

    def test_atomic_failure_rolls_back_order_stock_and_promotion_usage(self):
        promotion = self.promotion()
        parsed = parse_checkout_request(self.payload(promotion=promotion.code))

        with patch(
            "store.services.checkout.OrderItem.objects.bulk_create",
            side_effect=RuntimeError("simulated item failure"),
        ):
            with self.assertRaisesMessage(RuntimeError, "simulated item failure"):
                create_checkout(parsed, user=None)

        self.product.refresh_from_db()
        promotion.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(promotion.times_used, 0)
        self.assertFalse(Order.objects.exists())

    def test_create_endpoint_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("store:create_order"),
            data=json.dumps(self.payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Order.objects.exists())
