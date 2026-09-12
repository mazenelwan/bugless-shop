import ast
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from store.models import Category, Product, ProductImage

class Command(BaseCommand):
    help = 'Imports the existing static Shop catalog into the database.'
    def handle(self, *args, **options):
        source = Path(__file__).resolve().parents[3] / 'product-data.js'
        match = re.search(r'var rows = (\[[\s\S]*?\]);', source.read_text(encoding='utf-8'))
        if not match: self.stderr.write('Could not read the existing catalog.'); return
        for product_id, category_name, name, price, image in ast.literal_eval(match.group(1)):
            category, _ = Category.objects.get_or_create(name=category_name)
            product, _ = Product.objects.update_or_create(sku=f'BF-{product_id.upper()}', defaults={'name': name, 'price': price, 'description': f'A {category_name.rstrip("s").lower()} from the BUGLESS FIT collection.', 'category': category, 'stock': 10, 'is_active': True})
            ProductImage.objects.update_or_create(product=product, display_order=0, defaults={'image': image, 'alt_text': name, 'is_primary': True})
        self.stdout.write(self.style.SUCCESS('Imported the existing Shop catalog.'))
