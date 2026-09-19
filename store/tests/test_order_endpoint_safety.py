import json
import uuid

from django.test import TestCase
from django.urls import reverse

from store.models import Category, Order, Product, ProductVariant


class CanonicalOrderEndpointSafetyTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Test category")
        self.product = Product.objects.create(
            name="Test product",
            sku="SAFE-01",
            price="50.00",
            stock=5,
            category=category,
        )
        self.customer = {
            "name": "Ada",
            "email": "ada@example.com",
            "phone": "01000000000",
            "address": "Cairo",
            "city": "",
            "notes": "",
        }

    def post(self, lines):
        return self.client.post(
            reverse("store:create_order"),
            data=json.dumps(
                {
                    "version": 1,
                    "idempotencyKey": str(uuid.uuid4()),
                    "customer": self.customer,
                    "promotionCode": "",
                    "lines": lines,
                }
            ),
            content_type="application/json",
        )

    def test_non_object_json_is_rejected_without_creating_an_order(self):
        response = self.client.post(
            reverse("store:create_order"),
            data=json.dumps([]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_payload")
        self.assertFalse(Order.objects.exists())

    def test_non_object_order_item_is_rejected_without_creating_an_order(self):
        response = self.post(["not-an-object"])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_cart")
        self.assertFalse(Order.objects.exists())

    def test_duplicate_lines_over_the_combined_limit_are_rejected_without_mutation(self):
        response = self.post(
            [
                {
                    "productId": str(self.product.public_id),
                    "variantId": None,
                    "quantity": 50,
                },
                {
                    "productId": str(self.product.public_id),
                    "variantId": None,
                    "quantity": 50,
                },
            ]
        )

        self.assertEqual(response.status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(Order.objects.count(), 0)

    def test_variant_product_requires_an_exact_variant(self):
        ProductVariant.objects.create(product=self.product, size="M", stock=5)

        response = self.post(
            [
                {
                    "productId": str(self.product.public_id),
                    "variantId": None,
                    "quantity": 1,
                }
            ]
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "variant_required")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(Order.objects.count(), 0)
