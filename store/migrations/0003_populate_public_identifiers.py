import uuid

from django.db import migrations


def populate_public_identifiers(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    ProductVariant = apps.get_model("store", "ProductVariant")
    Order = apps.get_model("store", "Order")
    OrderItem = apps.get_model("store", "OrderItem")

    for product in Product.objects.filter(public_id__isnull=True).iterator():
        Product.objects.filter(pk=product.pk).update(public_id=uuid.uuid4())

    for variant in ProductVariant.objects.filter(public_id__isnull=True).iterator():
        ProductVariant.objects.filter(pk=variant.pk).update(public_id=uuid.uuid4())

    for order in Order.objects.iterator():
        updates = {}
        if order.confirmation_token is None:
            updates["confirmation_token"] = uuid.uuid4()
        if order.idempotency_key is None:
            updates["idempotency_key"] = uuid.uuid4()
        if updates:
            Order.objects.filter(pk=order.pk).update(**updates)

    for item in OrderItem.objects.select_related("product", "variant").iterator():
        updates = {}
        if item.product_id:
            updates["product_public_id"] = item.product.public_id
            updates["product_sku"] = item.product.sku
        if item.variant_id:
            updates["variant_public_id"] = item.variant.public_id
            updates["variant_label"] = " / ".join(
                value for value in (item.variant.color, item.variant.size) if value
            )
        if updates:
            OrderItem.objects.filter(pk=item.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0002_promotion_alter_category_options_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_public_identifiers, migrations.RunPython.noop),
    ]
