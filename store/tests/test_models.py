from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from store.models import (
    Category,
    Order,
    Product,
    ProductImage,
    ProductVariant,
    Promotion,
)


class CatalogModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Shirts", display_order=2)
        self.product = Product.objects.create(
            category=self.category,
            name="Oxford Shirt",
            sku="BF-TEST-01",
            price=Decimal("100.00"),
            stock=8,
        )

    def test_product_has_immutable_public_identifier_and_readable_slug(self):
        public_id = self.product.public_id

        self.product.name = "Renamed Oxford Shirt"
        self.product.save()
        self.product.refresh_from_db()

        self.assertEqual(self.product.public_id, public_id)
        self.assertIn("bf-test-01", self.product.slug)

    def test_old_price_cannot_be_below_current_price(self):
        self.product.old_price = Decimal("99.99")

        with self.assertRaises(ValidationError):
            self.product.full_clean()

    def test_active_variant_stock_replaces_aggregate_stock(self):
        self.assertEqual(self.product.available_stock, 8)

        ProductVariant.objects.create(
            product=self.product,
            size="M",
            stock=3,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=self.product,
            size="L",
            stock=7,
            is_active=False,
        )

        self.assertTrue(self.product.uses_variants)
        self.assertEqual(self.product.available_stock, 3)

    def test_variant_requires_at_least_one_option(self):
        variant = ProductVariant(product=self.product, stock=1)

        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_only_one_primary_image_is_allowed(self):
        ProductImage.objects.create(
            product=self.product,
            image="https://example.com/one.jpg",
            is_primary=True,
            display_order=0,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductImage.objects.create(
                product=self.product,
                image="https://example.com/two.jpg",
                is_primary=True,
                display_order=1,
            )


class PromotionAndOrderModelTests(TestCase):
    def test_percentage_promotion_cannot_exceed_one_hundred(self):
        promotion = Promotion(
            code="TOO-MUCH",
            name="Invalid",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            value=Decimal("100.01"),
        )

        with self.assertRaises(ValidationError):
            promotion.full_clean()

    def test_promotion_codes_are_case_insensitively_unique(self):
        Promotion.objects.create(
            code="SAVE10",
            name="Ten percent",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Promotion.objects.create(
                code="save10",
                name="Duplicate",
                discount_type=Promotion.DiscountType.FIXED,
                value=Decimal("10.00"),
            )

    def test_order_identifiers_are_unique_and_total_is_validated(self):
        order = Order(
            customer_name="Ada Lovelace",
            email="ada@example.com",
            phone="01000000000",
            address="Cairo",
            subtotal_amount=Decimal("100.00"),
            discount_amount=Decimal("10.00"),
            delivery_fee=Decimal("5.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("95.00"),
        )
        order.full_clean()
        order.save()

        second = Order.objects.create(
            customer_name="Grace Hopper",
            email="grace@example.com",
            phone="01100000000",
            address="Cairo",
        )

        self.assertNotEqual(order.number, second.number)
        self.assertNotEqual(order.confirmation_token, second.confirmation_token)
        self.assertNotEqual(order.idempotency_key, second.idempotency_key)

        order.total_amount = Decimal("94.99")
        with self.assertRaises(ValidationError):
            order.full_clean()

