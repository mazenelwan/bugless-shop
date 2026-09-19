from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from store.models import Category, Product, ProductImage, Promotion


class SeedCatalogCommandTests(TestCase):
    def run_seed(self, **options):
        call_command("seed_catalog", stdout=StringIO(), **options)

    def test_seed_is_ordered_and_idempotent(self):
        self.run_seed()
        identifiers = dict(Product.objects.values_list("sku", "public_id"))

        self.run_seed()

        self.assertEqual(Category.objects.count(), 6)
        self.assertEqual(Product.objects.count(), 24)
        self.assertEqual(ProductImage.objects.count(), 24)
        self.assertEqual(
            list(Category.objects.values_list("name", flat=True)),
            ["Men's Shirts", "Jacket", "Pants", "T-Shirts", "Polo", "Shoes"],
        )
        self.assertEqual(
            dict(Product.objects.values_list("sku", "public_id")),
            identifiers,
        )
        self.assertEqual(Promotion.objects.count(), 0)

    def test_demo_promotions_require_explicit_opt_in(self):
        self.run_seed(with_demo_promotions=True)
        self.run_seed(with_demo_promotions=True)

        self.assertEqual(Promotion.objects.count(), 3)
        self.assertEqual(Promotion.objects.filter(is_active=True).count(), 3)

