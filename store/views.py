import json
import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import RequestDataTooBig
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import ContactForm
from .models import Order
from .selectors import public_categories, public_products, related_products
from .services.checkout import (
    CheckoutError,
    create_checkout,
    order_data,
    parse_checkout_request,
    parse_quote_request,
    pricing_data,
    quote_cart,
)
from .services.contact import ContactSubmissionError, submit_contact


logger = logging.getLogger(__name__)

def _catalog_payload():
    payload = []
    for product in public_products():
        primary_image = product.primary_image
        payload.append(
            {
                "productId": str(product.public_id),
                "legacyId": product.legacy_id,
                "name": product.name,
                "price": str(product.price),
                "image": primary_image.image if primary_image else "",
                "url": reverse("store:product_detail", args=(product.slug,)),
                "available": product.available,
                "variants": [
                    {
                        "variantId": str(variant.public_id),
                        "size": variant.size,
                        "color": variant.color,
                        "stock": variant.stock,
                        "available": variant.available,
                    }
                    for variant in product.active_variants
                ],
            }
        )
    return payload


def home(request):
    return render(request, "store/home.html", {"categories": public_categories()})


def shop(request):
    query = request.GET.get("q", "").strip()
    return render(
        request,
        "store/shop.html",
        {
            "categories": public_categories(query),
            "query": query,
            "cart_catalog": _catalog_payload(),
        },
    )


def search(request):
    return shop(request)


def product_detail(request, slug):
    product = get_object_or_404(public_products(), slug=slug)
    variants = product.active_variants
    color_options = list(dict.fromkeys(v.color for v in variants if v.color))
    size_options = list(dict.fromkeys(v.size for v in variants if v.size))
    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "related": related_products(product),
            "color_options": color_options,
            "size_options": size_options,
            "variant_payload": [
                {
                    "variantId": str(variant.public_id),
                    "color": variant.color,
                    "size": variant.size,
                    "stock": variant.stock,
                    "available": variant.available,
                }
                for variant in variants
            ],
            "cart_catalog": _catalog_payload(),
        },
    )


def about(request):
    return render(request, "store/about.html")


@require_http_methods(["GET", "POST"])
def contact(request):
    response_status = 200
    if request.method == "POST":
        try:
            body_too_large = len(request.body) > settings.CONTACT_MAX_BODY_BYTES
        except RequestDataTooBig:
            body_too_large = True

        if body_too_large:
            form = ContactForm(data={})
            form.is_valid()
            form.add_error(
                None,
                "Your message is too large. Shorten it and try again.",
            )
            response_status = 413
        else:
            form = ContactForm(request.POST)
            if form.is_valid():
                try:
                    submit_contact(form.cleaned_data, request)
                except ContactSubmissionError as error:
                    form.add_error(None, error.message)
                    response_status = error.status
                else:
                    messages.success(
                        request,
                        "Thank you. Your message has been sent successfully.",
                    )
                    return redirect("store:contact")
        submission_id = uuid.uuid4()
    else:
        submission_id = uuid.uuid4()
        form = ContactForm(initial={"submission_id": submission_id})

    return render(
        request,
        "store/contact.html",
        {"form": form, "contact_submission_id": submission_id},
        status=response_status,
    )


@require_GET
@never_cache
def checkout(request):
    initial_customer = {"name": "", "email": ""}
    if request.user.is_authenticated:
        initial_customer = {
            "name": request.user.get_full_name(),
            "email": request.user.email,
        }
    return render(
        request,
        "store/checkout.html",
        {
            "cart_catalog": _catalog_payload(),
            "initial_customer": initial_customer,
        },
    )


@require_GET
@never_cache
def order_confirmation(request, number, token):
    order = get_object_or_404(
        Order.objects.select_related("promotion").prefetch_related("items"),
        number=number,
        confirmation_token=token,
    )
    if (
        order.customer_id
        and request.user.is_authenticated
        and order.customer_id != request.user.pk
    ):
        raise Http404
    return render(request, "store/order_confirmation.html", {"order": order})


class DuplicateJsonKey(ValueError):
    pass


def _unique_json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateJsonKey(key)
        value[key] = item
    return value


def _checkout_error_response(error):
    return JsonResponse(
        {
            "ok": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "fields": error.fields,
            },
        },
        status=error.status,
    )


def _checkout_json(request):
    if request.content_type != "application/json":
        raise CheckoutError(
            "invalid_content_type",
            "Checkout requests must use JSON.",
            fields={"payload": ["Use Content-Type: application/json."]},
            status=415,
        )
    try:
        body = request.body
    except RequestDataTooBig:
        raise CheckoutError(
            "payload_too_large",
            "The checkout request is too large.",
            fields={"payload": ["Reduce the checkout request size."]},
            status=400,
        )
    if len(body) > settings.CHECKOUT_MAX_BODY_BYTES:
        raise CheckoutError(
            "payload_too_large",
            "The checkout request is too large.",
            fields={
                "payload": [
                    f"The request may contain at most {settings.CHECKOUT_MAX_BODY_BYTES} bytes."
                ]
            },
            status=400,
        )
    try:
        return json.loads(body, object_pairs_hook=_unique_json_object)
    except (DuplicateJsonKey, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        raise CheckoutError(
            "invalid_json",
            "The checkout request is not valid JSON.",
            fields={"payload": ["Send one valid JSON object without duplicate keys."]},
            status=400,
        )


@require_POST
@never_cache
def quote_order(request):
    try:
        cart = parse_quote_request(_checkout_json(request))
        pricing = quote_cart(cart, request.user)
    except CheckoutError as error:
        return _checkout_error_response(error)
    return JsonResponse({"ok": True, "data": pricing_data(pricing)}, status=200)


@require_POST
@never_cache
def create_order(request):
    try:
        payload = parse_checkout_request(_checkout_json(request))
        result = create_checkout(payload, request.user)
    except CheckoutError as error:
        logger.warning(
            "Checkout request rejected.",
            extra={
                "event": "checkout_rejected",
                "code": error.code,
                "status_code": error.status,
            },
        )
        return _checkout_error_response(error)

    data = order_data(result)
    data["confirmationUrl"] = reverse(
        "store:order_confirmation",
        args=(result.order.number, result.order.confirmation_token),
    )
    return JsonResponse(
        {"ok": True, "data": data},
        status=200 if result.replayed else 201,
    )


@require_GET
def legacy_product(request):
    legacy_id = request.GET.get("id", "").strip()
    product = get_object_or_404(public_products(), legacy_id=legacy_id)
    return redirect("store:product_detail", slug=product.slug, permanent=True)
