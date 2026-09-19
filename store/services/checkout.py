import hashlib
import json
import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from store.forms import CheckoutCustomerForm
from store.models import Order, OrderItem, Product, ProductVariant, Promotion


logger = logging.getLogger(__name__)

CART_VERSION = 1
MAX_SUBMITTED_LINES = 50
MAX_LINE_QUANTITY = 99
MAX_ORDER_AMOUNT = Decimal("9999999999.99")
CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class CheckoutError(Exception):
    def __init__(self, code, message, *, fields=None, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.fields = fields or {}
        self.status = status


@dataclass(frozen=True)
class RequestedLine:
    product_id: UUID
    variant_id: UUID | None
    quantity: int
    source_index: int


@dataclass(frozen=True)
class CartRequest:
    lines: tuple[RequestedLine, ...]
    promotion_code: str


@dataclass(frozen=True)
class CheckoutRequest:
    cart: CartRequest
    idempotency_key: UUID
    customer: dict


@dataclass(frozen=True)
class CatalogState:
    products: dict
    variants_by_id: dict
    variants_by_product: dict


@dataclass(frozen=True)
class ResolvedLine:
    requested: RequestedLine
    product: Product
    variant: ProductVariant | None
    subtotal: Decimal


@dataclass(frozen=True)
class Pricing:
    lines: tuple[ResolvedLine, ...]
    subtotal: Decimal
    discount: Decimal
    delivery: Decimal
    tax: Decimal
    total: Decimal
    promotion: Promotion | None


@dataclass(frozen=True)
class CheckoutResult:
    order: Order
    replayed: bool


def _error(code, message, field, field_message, *, status=400):
    raise CheckoutError(
        code,
        message,
        fields={field: [field_message]},
        status=status,
    )


def _reject_unknown_fields(value, allowed, path):
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        _error(
            "invalid_payload",
            "Review the highlighted checkout details.",
            path,
            f"Unknown field(s): {', '.join(unknown)}.",
        )


def _parse_uuid(value, path, *, code="invalid_cart"):
    if not isinstance(value, str):
        _error(
            code,
            "Review the highlighted checkout details.",
            path,
            "Enter a valid UUID string.",
        )
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError):
        _error(
            code,
            "Review the highlighted checkout details.",
            path,
            "Enter a valid UUID string.",
        )
    if str(parsed) != value.casefold():
        _error(
            code,
            "Review the highlighted checkout details.",
            path,
            "Enter a canonical UUID string.",
        )
    return parsed


def _parse_cart_fields(data):
    version = data.get("version")
    if type(version) is not int or version != CART_VERSION:
        _error(
            "invalid_payload",
            "Review the highlighted checkout details.",
            "version",
            "Only checkout payload version 1 is supported.",
        )

    promotion_code = data.get("promotionCode", "")
    if not isinstance(promotion_code, str):
        _error(
            "invalid_promotion",
            "Review the highlighted checkout details.",
            "promotionCode",
            "Enter a promotion code as text.",
        )
    promotion_code = promotion_code.strip().upper()
    if len(promotion_code) > 40:
        _error(
            "invalid_promotion",
            "Review the highlighted checkout details.",
            "promotionCode",
            "Promotion codes may contain at most 40 characters.",
        )

    raw_lines = data.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        _error(
            "invalid_cart",
            "Review the highlighted checkout details.",
            "lines",
            "Add at least one item to the cart.",
        )
    if len(raw_lines) > MAX_SUBMITTED_LINES:
        _error(
            "invalid_cart",
            "Review the highlighted checkout details.",
            "lines",
            f"A checkout may contain at most {MAX_SUBMITTED_LINES} submitted lines.",
        )

    merged = {}
    for index, raw_line in enumerate(raw_lines):
        path = f"lines.{index}"
        if not isinstance(raw_line, dict):
            _error(
                "invalid_cart",
                "Review the highlighted checkout details.",
                path,
                "Each cart line must be an object.",
            )
        _reject_unknown_fields(
            raw_line,
            {"productId", "variantId", "quantity"},
            path,
        )
        missing = [
            key
            for key in ("productId", "variantId", "quantity")
            if key not in raw_line
        ]
        if missing:
            _error(
                "invalid_cart",
                "Review the highlighted checkout details.",
                path,
                f"Missing field(s): {', '.join(missing)}.",
            )

        product_id = _parse_uuid(raw_line["productId"], f"{path}.productId")
        raw_variant_id = raw_line["variantId"]
        variant_id = (
            None
            if raw_variant_id is None
            else _parse_uuid(raw_variant_id, f"{path}.variantId")
        )
        quantity = raw_line["quantity"]
        if type(quantity) is not int or not 1 <= quantity <= MAX_LINE_QUANTITY:
            _error(
                "invalid_cart",
                "Review the highlighted checkout details.",
                f"{path}.quantity",
                f"Enter a whole number from 1 to {MAX_LINE_QUANTITY}.",
            )

        key = (product_id, variant_id)
        if key in merged:
            first = merged[key]
            quantity += first.quantity
            if quantity > MAX_LINE_QUANTITY:
                _error(
                    "invalid_cart",
                    "Review the highlighted checkout details.",
                    f"lines.{first.source_index}.quantity",
                    f"Combined quantity may not exceed {MAX_LINE_QUANTITY}.",
                )
            merged[key] = RequestedLine(
                product_id,
                variant_id,
                quantity,
                first.source_index,
            )
        else:
            merged[key] = RequestedLine(product_id, variant_id, quantity, index)

    lines = tuple(
        sorted(
            merged.values(),
            key=lambda line: (
                line.product_id.hex,
                line.variant_id.hex if line.variant_id else "",
            ),
        )
    )
    return CartRequest(lines=lines, promotion_code=promotion_code)


def parse_quote_request(data):
    if not isinstance(data, dict):
        _error(
            "invalid_payload",
            "Review the highlighted checkout details.",
            "payload",
            "The request body must be a JSON object.",
        )
    _reject_unknown_fields(data, {"version", "promotionCode", "lines"}, "payload")
    return _parse_cart_fields(data)


def parse_checkout_request(data):
    if not isinstance(data, dict):
        _error(
            "invalid_payload",
            "Review the highlighted checkout details.",
            "payload",
            "The request body must be a JSON object.",
        )
    _reject_unknown_fields(
        data,
        {"version", "idempotencyKey", "customer", "promotionCode", "lines"},
        "payload",
    )
    cart = _parse_cart_fields(data)

    idempotency_key = _parse_uuid(
        data.get("idempotencyKey"),
        "idempotencyKey",
        code="invalid_payload",
    )
    raw_customer = data.get("customer")
    if not isinstance(raw_customer, dict):
        _error(
            "invalid_customer",
            "Review the highlighted checkout details.",
            "customer",
            "Customer details must be an object.",
        )
    _reject_unknown_fields(
        raw_customer,
        {"name", "email", "phone", "address", "city", "notes"},
        "customer",
    )
    required_customer_fields = ("name", "email", "phone", "address")
    for field_name in required_customer_fields:
        if field_name not in raw_customer or not isinstance(
            raw_customer[field_name], str
        ):
            _error(
                "invalid_customer",
                "Review the highlighted checkout details.",
                f"customer.{field_name}",
                "This field is required and must be text.",
            )
    for field_name in ("city", "notes"):
        if field_name in raw_customer and not isinstance(
            raw_customer[field_name], str
        ):
            _error(
                "invalid_customer",
                "Review the highlighted checkout details.",
                f"customer.{field_name}",
                "This field must be text.",
            )
    form = CheckoutCustomerForm(raw_customer)
    if not form.is_valid():
        fields = {}
        for field_name, errors in form.errors.get_json_data().items():
            path = "customer" if field_name == "__all__" else f"customer.{field_name}"
            fields[path] = [entry["message"] for entry in errors]
        raise CheckoutError(
            "invalid_customer",
            "Review the highlighted checkout details.",
            fields=fields,
        )

    return CheckoutRequest(
        cart=cart,
        idempotency_key=idempotency_key,
        customer=dict(form.cleaned_data),
    )


def request_fingerprint(payload, user):
    actor = f"account:{user.pk}" if getattr(user, "is_authenticated", False) else "guest"
    semantic = {
        "version": CART_VERSION,
        "actor": actor,
        "customer": payload.customer,
        "promotionCode": payload.cart.promotion_code,
        "lines": [
            {
                "productId": str(line.product_id),
                "variantId": str(line.variant_id) if line.variant_id else None,
                "quantity": line.quantity,
            }
            for line in payload.cart.lines
        ],
    }
    encoded = json.dumps(
        semantic,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_catalog(lines, *, lock):
    product_ids = [line.product_id for line in lines]
    products_query = (
        Product.objects.filter(public_id__in=product_ids)
        .select_related("category")
        .order_by("public_id")
    )
    if lock:
        products_query = products_query.select_for_update()
    products = list(products_query)
    product_pks = [product.pk for product in products]

    variants_query = ProductVariant.objects.filter(product_id__in=product_pks).order_by(
        "public_id"
    )
    if lock:
        variants_query = variants_query.select_for_update()
    variants = list(variants_query)

    variants_by_product = {product.pk: [] for product in products}
    for variant in variants:
        variants_by_product[variant.product_id].append(variant)
    return CatalogState(
        products={product.public_id: product for product in products},
        variants_by_id={variant.public_id: variant for variant in variants},
        variants_by_product=variants_by_product,
    )


def _validate_lines(cart, state):
    resolved = []
    subtotal = ZERO
    for requested in cart.lines:
        base_path = f"lines.{requested.source_index}"
        product = state.products.get(requested.product_id)
        if (
            product is None
            or not product.is_active
            or not product.category.is_active
            or product.sold_out
        ):
            _error(
                "product_unavailable",
                "One or more cart items are no longer available.",
                f"{base_path}.productId",
                "This product is unavailable.",
                status=409,
            )

        product_variants = state.variants_by_product.get(product.pk, [])
        active_variants = [variant for variant in product_variants if variant.is_active]
        selected_variant = None
        if active_variants:
            if requested.variant_id is None:
                _error(
                    "variant_required",
                    "Select an available product option.",
                    f"{base_path}.variantId",
                    "This product requires a variant.",
                    status=409,
                )
            selected_variant = state.variants_by_id.get(requested.variant_id)
            if (
                selected_variant is None
                or selected_variant.product_id != product.pk
                or not selected_variant.is_active
            ):
                _error(
                    "variant_unavailable",
                    "Select an available product option.",
                    f"{base_path}.variantId",
                    "This variant is unavailable for the selected product.",
                    status=409,
                )
            available_stock = selected_variant.stock
        else:
            if requested.variant_id is not None:
                _error(
                    "variant_not_allowed",
                    "Review the selected product option.",
                    f"{base_path}.variantId",
                    "This product does not accept a variant.",
                    status=409,
                )
            available_stock = product.stock

        if available_stock < requested.quantity:
            _error(
                "insufficient_stock",
                "One or more cart quantities exceed current stock.",
                f"{base_path}.quantity",
                "The requested quantity is no longer available.",
                status=409,
            )

        line_subtotal = product.price * requested.quantity
        subtotal += line_subtotal
        if subtotal > MAX_ORDER_AMOUNT:
            _error(
                "order_value_limit",
                "This order exceeds the supported value limit.",
                "lines",
                f"Subtotal may not exceed EGP {MAX_ORDER_AMOUNT:.2f}.",
            )
        resolved.append(
            ResolvedLine(
                requested=requested,
                product=product,
                variant=selected_variant,
                subtotal=line_subtotal,
            )
        )
    return tuple(resolved), subtotal


def _load_promotion(code, *, lock):
    if not code:
        return None
    query = Promotion.objects.filter(code__iexact=code)
    if lock:
        query = query.select_for_update()
    promotion = query.first()
    if promotion is None:
        _error(
            "promotion_invalid",
            "This promotion code cannot be applied.",
            "promotionCode",
            "Enter a valid promotion code.",
        )
    return promotion


def _promotion_discount(
    promotion,
    lines,
    subtotal,
    *,
    user=None,
    customer=None,
    enforce_customer_limit=False,
):
    if promotion is None:
        return ZERO

    now = timezone.now()
    if (
        not promotion.is_active
        or (promotion.starts_at is not None and promotion.starts_at > now)
        or (promotion.ends_at is not None and promotion.ends_at <= now)
        or (
            promotion.usage_limit is not None
            and promotion.times_used >= promotion.usage_limit
        )
    ):
        _error(
            "promotion_unavailable",
            "This promotion code is not currently available.",
            "promotionCode",
            "This promotion cannot be used now.",
            status=409,
        )

    if subtotal < promotion.minimum_subtotal:
        _error(
            "promotion_minimum_not_met",
            "This order does not meet the promotion minimum.",
            "promotionCode",
            f"A subtotal of EGP {promotion.minimum_subtotal:.2f} is required.",
        )

    product_scope = set(promotion.products.values_list("pk", flat=True))
    category_scope = set(promotion.categories.values_list("pk", flat=True))
    if product_scope or category_scope:
        eligible_subtotal = sum(
            (
                line.subtotal
                for line in lines
                if line.product.pk in product_scope
                or line.product.category_id in category_scope
            ),
            ZERO,
        )
    else:
        eligible_subtotal = subtotal

    if eligible_subtotal <= ZERO:
        _error(
            "promotion_not_applicable",
            "This promotion does not apply to the current cart.",
            "promotionCode",
            "Add an eligible product before using this code.",
        )

    if promotion.per_customer_limit is not None and enforce_customer_limit:
        uses = Order.objects.filter(promotion=promotion)
        if getattr(user, "is_authenticated", False):
            uses = uses.filter(customer=user)
        else:
            uses = uses.filter(email__iexact=customer["email"])
        if uses.count() >= promotion.per_customer_limit:
            _error(
                "promotion_customer_limit",
                "This promotion has reached its customer limit.",
                "promotionCode",
                "This promotion cannot be used again for this customer.",
                status=409,
            )

    if promotion.discount_type == Promotion.DiscountType.PERCENTAGE:
        discount = (eligible_subtotal * promotion.value / Decimal("100")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
    else:
        discount = min(promotion.value, eligible_subtotal)
    if promotion.maximum_discount is not None:
        discount = min(discount, promotion.maximum_discount)
    return min(discount, subtotal).quantize(CENT, rounding=ROUND_HALF_UP)


def _pricing(cart, state, promotion, *, user=None, customer=None, enforce_limit=False):
    lines, subtotal = _validate_lines(cart, state)
    discount = _promotion_discount(
        promotion,
        lines,
        subtotal,
        user=user,
        customer=customer,
        enforce_customer_limit=enforce_limit,
    )
    delivery = ZERO
    tax = ZERO
    return Pricing(
        lines=lines,
        subtotal=subtotal,
        discount=discount,
        delivery=delivery,
        tax=tax,
        total=subtotal - discount + delivery + tax,
        promotion=promotion,
    )


def quote_cart(cart, user=None):
    state = _load_catalog(cart.lines, lock=False)
    promotion = _load_promotion(cart.promotion_code, lock=False)
    return _pricing(
        cart,
        state,
        promotion,
        user=user,
        enforce_limit=getattr(user, "is_authenticated", False),
    )


def _existing_result(order, fingerprint):
    if order.request_fingerprint != fingerprint:
        logger.warning(
            "Checkout idempotency conflict.",
            extra={
                "event": "checkout_idempotency_conflict",
                "object_type": "order",
                "object_id": order.pk,
            },
        )
        raise CheckoutError(
            "idempotency_conflict",
            "This checkout retry key was already used with different details.",
            fields={
                "idempotencyKey": [
                    "Do not create a new attempt until the earlier order is checked."
                ]
            },
            status=409,
        )
    logger.info(
        "Checkout replayed.",
        extra={
            "event": "checkout_replayed",
            "object_type": "order",
            "object_id": order.pk,
        },
    )
    return CheckoutResult(order=order, replayed=True)


def _find_existing(payload, fingerprint, *, lock=False):
    query = Order.objects.filter(idempotency_key=payload.idempotency_key)
    if lock:
        query = query.select_for_update()
    else:
        query = query.select_related("promotion")
    order = query.first()
    return _existing_result(order, fingerprint) if order else None


def create_checkout(payload, user):
    fingerprint = request_fingerprint(payload, user)
    existing = _find_existing(payload, fingerprint)
    if existing:
        return existing

    try:
        with transaction.atomic():
            existing = _find_existing(payload, fingerprint, lock=True)
            if existing:
                return existing

            state = _load_catalog(payload.cart.lines, lock=True)
            existing = _find_existing(payload, fingerprint, lock=True)
            if existing:
                return existing

            promotion = _load_promotion(payload.cart.promotion_code, lock=True)
            existing = _find_existing(payload, fingerprint, lock=True)
            if existing:
                return existing

            pricing = _pricing(
                payload.cart,
                state,
                promotion,
                user=user,
                customer=payload.customer,
                enforce_limit=True,
            )
            customer_owner = user if getattr(user, "is_authenticated", False) else None
            order = Order.objects.create(
                idempotency_key=payload.idempotency_key,
                request_fingerprint=fingerprint,
                customer=customer_owner,
                customer_name=payload.customer["name"],
                email=payload.customer["email"],
                phone=payload.customer["phone"],
                address=payload.customer["address"],
                city=payload.customer["city"],
                notes=payload.customer["notes"],
                subtotal_amount=pricing.subtotal,
                discount_amount=pricing.discount,
                delivery_fee=pricing.delivery,
                tax_amount=pricing.tax,
                total_amount=pricing.total,
                currency="EGP",
                promotion=promotion,
                promotion_code=promotion.code if promotion else "",
                payment_method=Order.PaymentMethod.CASH_ON_DELIVERY,
                payment_status=Order.PaymentStatus.UNPAID,
                status=Order.Status.PENDING,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=line.product,
                        variant=line.variant,
                        product_public_id=line.product.public_id,
                        variant_public_id=(
                            line.variant.public_id if line.variant else None
                        ),
                        product_name=line.product.name,
                        product_sku=line.product.sku,
                        variant_label=line.variant.label if line.variant else "",
                        selected_size=line.variant.size if line.variant else "",
                        selected_color=line.variant.color if line.variant else "",
                        price=line.product.price,
                        quantity=line.requested.quantity,
                        subtotal=line.subtotal,
                    )
                    for line in pricing.lines
                ]
            )

            for line in pricing.lines:
                if line.variant is not None:
                    line.variant.stock -= line.requested.quantity
                    line.variant.save(update_fields=("stock",))
                else:
                    line.product.stock -= line.requested.quantity
                    line.product.save(update_fields=("stock", "updated_at"))

            if promotion is not None:
                promotion.times_used += 1
                promotion.save(update_fields=("times_used", "updated_at"))

            transaction.on_commit(
                lambda order_id=order.pk: logger.info(
                    "Checkout created.",
                    extra={
                        "event": "checkout_created",
                        "object_type": "order",
                        "object_id": order_id,
                    },
                ),
                robust=True,
            )

            return CheckoutResult(order=order, replayed=False)
    except IntegrityError:
        existing = _find_existing(payload, fingerprint)
        if existing:
            return existing
        raise


def _money(value):
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def pricing_data(pricing):
    return {
        "currency": "EGP",
        "subtotal": _money(pricing.subtotal),
        "discount": _money(pricing.discount),
        "delivery": _money(pricing.delivery),
        "tax": _money(pricing.tax),
        "total": _money(pricing.total),
        "promotion": (
            {"code": pricing.promotion.code, "name": pricing.promotion.name}
            if pricing.promotion
            else None
        ),
    }


def order_data(result):
    order = result.order
    return {
        "currency": order.currency,
        "subtotal": _money(order.subtotal_amount),
        "discount": _money(order.discount_amount),
        "delivery": _money(order.delivery_fee),
        "tax": _money(order.tax_amount),
        "total": _money(order.total_amount),
        "promotion": (
            {
                "code": order.promotion_code,
                "name": order.promotion.name if order.promotion else "",
            }
            if order.promotion_code
            else None
        ),
        "orderNumber": order.number,
        "replayed": result.replayed,
    }
