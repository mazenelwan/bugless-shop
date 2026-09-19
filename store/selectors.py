from django.db.models import Prefetch, Q

from .models import Category, Order, Product


def public_products():
    return (
        Product.objects.filter(is_active=True, category__is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")
        .order_by("category__display_order", "display_order", "id")
    )


def public_categories(query=""):
    product_queryset = public_products()
    normalized_query = query.strip()
    if normalized_query:
        product_queryset = product_queryset.filter(
            Q(name__icontains=normalized_query)
            | Q(description__icontains=normalized_query)
            | Q(category__name__icontains=normalized_query)
            | Q(sku__icontains=normalized_query)
        )

    category_ids = product_queryset.values("category_id")
    return (
        Category.objects.filter(is_active=True, id__in=category_ids)
        .order_by("display_order", "id")
        .prefetch_related(
            Prefetch(
                "products",
                queryset=product_queryset,
                to_attr="visible_products",
            )
        )
    )


def related_products(product, limit=4):
    same_category = list(
        public_products()
        .filter(category=product.category)
        .exclude(pk=product.pk)[:limit]
    )
    if len(same_category) == limit:
        return same_category

    excluded_ids = [product.pk, *(item.pk for item in same_category)]
    fallback = list(
        public_products().exclude(pk__in=excluded_ids)[: limit - len(same_category)]
    )
    return same_category + fallback


def customer_orders(user):
    return (
        Order.objects.filter(customer=user)
        .select_related("promotion")
        .prefetch_related("items")
        .order_by("-created_at", "-id")
    )
