import ast
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from store.models import Category, Product, ProductImage, Promotion


CATEGORY_METADATA = {
    "Men's Shirts": {
        "order": 0,
        "image": "https://dfcdn.defacto.com.tr/cms/1378da6f8b0940c7966225d45eab4ac5.jpg",
    },
    "Jacket": {
        "order": 1,
        "image": "https://dfcdn.defacto.com.tr/cms/8de15d4aa5644f7286b0335603bc53cd.jpg",
    },
    "Pants": {
        "order": 2,
        "image": "https://dfcdn.defacto.com.tr/cms/9e6f7d6b85cb43498a4de9c6ffa68421.jpg",
    },
    "T-Shirts": {
        "order": 3,
        "image": "https://dfcdn.defacto.com.tr/6/E4005AX_25SM_GN654_04_01.jpg",
    },
    "Polo": {
        "order": 4,
        "image": "https://dfcdn.defacto.com.tr/6/D5993AX_24SM_KH202_01_01.jpg",
    },
    "Shoes": {
        "order": 5,
        "image": "https://pronto-eg.com/cdn/shop/products/15052-1-5_copy_27f4143b-53f1-458f-b0fa-1365141d6f4a.jpg?v=1671282625&width=640",
    },
}

DISPLAY_RATINGS = {
    "shirts-01": "4.9",
    "shirts-02": "4.4",
    "shirts-03": "4.4",
    "shirts-04": "4.9",
    "jacket-01": "4.9",
    "jacket-02": "4.4",
    "jacket-03": "4.4",
    "jacket-04": "4.9",
    "pants-01": "3.9",
    "pants-02": "4.5",
    "pants-03": "4.6",
    "pants-04": "4.7",
    "tshirts-01": "4.2",
    "tshirts-02": "4.1",
    "tshirts-03": "4.4",
    "tshirts-04": "4.3",
    "polo-01": "4.6",
    "polo-02": "3.4",
    "polo-03": "4.5",
    "polo-04": "4.8",
    "shoes-01": "4.9",
    "shoes-02": "4.4",
    "shoes-03": "4.4",
    "shoes-04": "4.9",
}

DEMO_PROMOTIONS = (
    {
        "code": "SAVE10",
        "name": "Development 10% promotion",
        "discount_type": Promotion.DiscountType.PERCENTAGE,
        "value": Decimal("10.00"),
    },
    {
        "code": "SAVE20",
        "name": "Development 20% promotion",
        "discount_type": Promotion.DiscountType.PERCENTAGE,
        "value": Decimal("20.00"),
    },
    {
        "code": "WELCOME50",
        "name": "Development EGP 50 promotion",
        "discount_type": Promotion.DiscountType.FIXED,
        "value": Decimal("50.00"),
    },
)


class Command(BaseCommand):
    help = "Import the preserved standalone catalog into the development database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-demo-promotions",
            action="store_true",
            help="Create and activate the three SOT demo promotion codes for development.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rows = self._read_source_rows()
        category_positions = {}

        for product_id, category_name, name, price, image in rows:
            metadata = CATEGORY_METADATA.get(
                category_name,
                {"order": len(category_positions), "image": ""},
            )
            category, _ = Category.objects.update_or_create(
                name=category_name,
                defaults={
                    "description": f"Shop the Bugless Fit {category_name} collection.",
                    "image": metadata["image"],
                    "display_order": metadata["order"],
                    "is_active": True,
                },
            )

            product_position = category_positions.get(category_name, 0)
            category_positions[category_name] = product_position + 1
            sku = f"BF-{product_id.upper()}"
            product, _ = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "legacy_id": product_id,
                    "name": name,
                    "price": Decimal(str(price)),
                    "old_price": None,
                    "rating": Decimal(DISPLAY_RATINGS[product_id]),
                    "description": (
                        f"A {category_name.rstrip('s').lower()} from the "
                        "BUGLESS FIT collection."
                    ),
                    "category": category,
                    "display_order": product_position,
                    "stock": 10,
                    "sold_out": False,
                    "is_active": True,
                },
            )
            ProductImage.objects.update_or_create(
                product=product,
                display_order=0,
                defaults={
                    "image": image,
                    "alt_text": name,
                    "is_primary": True,
                },
            )

        if options["with_demo_promotions"]:
            for definition in DEMO_PROMOTIONS:
                Promotion.objects.update_or_create(
                    code=definition["code"],
                    defaults={**definition, "is_active": True},
                )

        message = (
            f"Catalog ready: {Category.objects.count()} categories, "
            f"{Product.objects.count()} products, "
            f"{ProductImage.objects.count()} images."
        )
        if options["with_demo_promotions"]:
            message += " Development promotions are active."
        self.stdout.write(self.style.SUCCESS(message))

    @staticmethod
    def _read_source_rows():
        source = Path(__file__).resolve().parents[3] / "frontend" / "product-data.js"
        if not source.exists():
            raise CommandError(f"Catalog source is missing: {source}")

        match = re.search(
            r"var rows = (\[[\s\S]*?\]);",
            source.read_text(encoding="utf-8"),
        )
        if not match:
            raise CommandError("Could not parse frontend/product-data.js.")

        try:
            rows = ast.literal_eval(match.group(1))
        except (SyntaxError, ValueError) as exc:
            raise CommandError("Catalog source contains invalid data.") from exc

        if not isinstance(rows, list) or not all(
            isinstance(row, list) and len(row) == 5 for row in rows
        ):
            raise CommandError("Catalog source rows must each contain five values.")
        return rows
