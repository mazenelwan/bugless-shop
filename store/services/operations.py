from collections import defaultdict
from dataclasses import dataclass
import logging

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from store.models import (
    ContactMessage,
    ContactMessageEvent,
    Order,
    OrderEvent,
    OrderItem,
    Product,
    ProductVariant,
)


logger = logging.getLogger(__name__)

MAX_STOCK_VALUE = 2_147_483_647

ORDER_TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.PREPARING, Order.Status.CANCELLED},
    Order.Status.PREPARING: {Order.Status.SHIPPED, Order.Status.CANCELLED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}

PAYMENT_TRANSITIONS = {
    Order.PaymentStatus.UNPAID: {Order.PaymentStatus.PAID},
    Order.PaymentStatus.PENDING: {
        Order.PaymentStatus.PAID,
        Order.PaymentStatus.FAILED,
    },
    Order.PaymentStatus.FAILED: {Order.PaymentStatus.PENDING},
    Order.PaymentStatus.PAID: {Order.PaymentStatus.REFUNDED},
    Order.PaymentStatus.REFUNDED: set(),
}

CONTACT_TRANSITIONS = {
    ContactMessage.Status.NEW: {
        ContactMessage.Status.READ,
        ContactMessage.Status.ARCHIVED,
    },
    ContactMessage.Status.READ: {
        ContactMessage.Status.REPLIED,
        ContactMessage.Status.ARCHIVED,
    },
    ContactMessage.Status.REPLIED: {ContactMessage.Status.ARCHIVED},
    ContactMessage.Status.ARCHIVED: set(),
}


class OperationsError(Exception):
    pass


@dataclass(frozen=True)
class TransitionResult:
    instance: object
    changed: bool


def _require_permission(actor, codename):
    if actor is None or not actor.has_perm(f"store.{codename}"):
        raise PermissionDenied(f"The {codename} permission is required.")


def _safe_note(note):
    return str(note or "").strip()[:200]


def _locked_inventory(items):
    if not items:
        raise OperationsError("The order has no items to restock.")

    product_ids = {item.product_id for item in items if item.product_id is not None}
    variant_ids = {item.variant_id for item in items if item.variant_id is not None}

    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=product_ids)
        .order_by("pk")
    }
    variants = {
        variant.pk: variant
        for variant in ProductVariant.objects.select_for_update()
        .filter(pk__in=variant_ids)
        .order_by("pk")
    }

    if len(products) != len(product_ids):
        raise OperationsError("An original product inventory row no longer exists.")
    if len(variants) != len(variant_ids):
        raise OperationsError("An original variant inventory row no longer exists.")
    return products, variants


def _restock_order_items(order):
    items = list(
        OrderItem.objects.select_for_update().filter(order=order).order_by("pk")
    )
    products, variants = _locked_inventory(items)
    product_quantities = defaultdict(int)
    variant_quantities = defaultdict(int)

    for item in items:
        has_variant_snapshot = item.variant_public_id is not None
        if has_variant_snapshot or item.variant_id is not None:
            if item.variant_id is None or item.product_id is None:
                raise OperationsError("An original variant inventory row no longer exists.")
            variant = variants[item.variant_id]
            if variant.product_id != item.product_id:
                raise OperationsError("An order item no longer matches its original variant.")
            variant_quantities[item.variant_id] += item.quantity
        else:
            if item.product_id is None:
                raise OperationsError("An original product inventory row no longer exists.")
            product_quantities[item.product_id] += item.quantity

    for product_id, quantity in product_quantities.items():
        if products[product_id].stock + quantity > MAX_STOCK_VALUE:
            raise OperationsError("Restoring this order would exceed the stock limit.")
    for variant_id, quantity in variant_quantities.items():
        if variants[variant_id].stock + quantity > MAX_STOCK_VALUE:
            raise OperationsError("Restoring this order would exceed the stock limit.")

    for product_id in sorted(product_quantities):
        product = products[product_id]
        product.stock += product_quantities[product_id]
        product.save(update_fields=("stock", "updated_at"))
    for variant_id in sorted(variant_quantities):
        variant = variants[variant_id]
        variant.stock += variant_quantities[variant_id]
        variant.save(update_fields=("stock",))


def transition_order(order_id, target_status, actor, *, note=""):
    if target_status not in Order.Status.values:
        raise OperationsError("Unknown order status.")
    permission = "cancel_order" if target_status == Order.Status.CANCELLED else "transition_order"
    _require_permission(actor, permission)

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.status == target_status:
            if target_status == Order.Status.CANCELLED and not order.inventory_restocked_at:
                raise OperationsError("The cancelled order has no restock record.")
            logger.info(
                "Order transition replayed.",
                extra={
                    "event": "order_transition_replayed",
                    "operation": "order_status",
                    "object_type": "order",
                    "object_id": order.pk,
                    "to_state": target_status,
                },
            )
            return TransitionResult(instance=order, changed=False)
        if target_status not in ORDER_TRANSITIONS.get(order.status, set()):
            raise OperationsError(
                f"Order cannot move from {order.get_status_display()} to "
                f"{Order.Status(target_status).label}."
            )

        previous_status = order.status
        if target_status == Order.Status.CANCELLED:
            if order.payment_status in {
                Order.PaymentStatus.PAID,
                Order.PaymentStatus.PENDING,
            }:
                raise OperationsError(
                    "Resolve or refund the payment before cancelling this order."
                )
            if order.inventory_restocked_at:
                raise OperationsError("Inventory was already restored for this order.")
            _restock_order_items(order)
            order.inventory_restocked_at = timezone.now()

        order.status = target_status
        update_fields = ["status", "updated_at"]
        if target_status == Order.Status.CANCELLED:
            update_fields.append("inventory_restocked_at")
        order.save(update_fields=update_fields)
        OrderEvent.objects.create(
            order=order,
            actor=actor,
            event_type=OrderEvent.EventType.STATUS_CHANGED,
            from_status=previous_status,
            to_status=target_status,
            note=_safe_note(note),
        )
        if target_status == Order.Status.CANCELLED:
            OrderEvent.objects.create(
                order=order,
                actor=actor,
                event_type=OrderEvent.EventType.INVENTORY_RESTOCKED,
                from_status=previous_status,
                to_status=target_status,
                note=_safe_note(note),
            )
        transaction.on_commit(
            lambda order_id=order.pk, old=previous_status, new=target_status: logger.info(
                "Order transitioned.",
                extra={
                    "event": "order_transition_completed",
                    "operation": "order_status",
                    "object_type": "order",
                    "object_id": order_id,
                    "from_state": old,
                    "to_state": new,
                },
            ),
            robust=True,
        )
        return TransitionResult(instance=order, changed=True)


def transition_payment(order_id, target_status, actor, *, note=""):
    if target_status not in Order.PaymentStatus.values:
        raise OperationsError("Unknown payment status.")
    permission = (
        "refund_order"
        if target_status == Order.PaymentStatus.REFUNDED
        else "record_order_payment"
    )
    _require_permission(actor, permission)

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.payment_status == target_status:
            logger.info(
                "Payment transition replayed.",
                extra={
                    "event": "payment_transition_replayed",
                    "operation": "payment_status",
                    "object_type": "order",
                    "object_id": order.pk,
                    "to_state": target_status,
                },
            )
            return TransitionResult(instance=order, changed=False)
        if target_status not in PAYMENT_TRANSITIONS.get(order.payment_status, set()):
            raise OperationsError(
                f"Payment cannot move from {order.get_payment_status_display()} to "
                f"{Order.PaymentStatus(target_status).label}."
            )
        if order.status == Order.Status.CANCELLED:
            raise OperationsError("Payment cannot change after order cancellation.")

        previous_status = order.payment_status
        order.payment_status = target_status
        order.save(update_fields=("payment_status", "updated_at"))
        OrderEvent.objects.create(
            order=order,
            actor=actor,
            event_type=OrderEvent.EventType.PAYMENT_CHANGED,
            from_payment_status=previous_status,
            to_payment_status=target_status,
            note=_safe_note(note),
        )
        transaction.on_commit(
            lambda order_id=order.pk, old=previous_status, new=target_status: logger.info(
                "Payment transitioned.",
                extra={
                    "event": "payment_transition_completed",
                    "operation": "payment_status",
                    "object_type": "order",
                    "object_id": order_id,
                    "from_state": old,
                    "to_state": new,
                },
            ),
            robust=True,
        )
        return TransitionResult(instance=order, changed=True)


def transition_contact_message(message_id, target_status, actor):
    if target_status not in ContactMessage.Status.values:
        raise OperationsError("Unknown contact status.")
    _require_permission(actor, "manage_contactmessage")

    with transaction.atomic():
        message = ContactMessage.objects.select_for_update().get(pk=message_id)
        if message.status == target_status:
            logger.info(
                "Contact transition replayed.",
                extra={
                    "event": "contact_transition_replayed",
                    "operation": "contact_status",
                    "object_type": "contact_message",
                    "object_id": message.pk,
                    "to_state": target_status,
                },
            )
            return TransitionResult(instance=message, changed=False)
        if target_status not in CONTACT_TRANSITIONS.get(message.status, set()):
            raise OperationsError(
                f"Message cannot move from {message.get_status_display()} to "
                f"{ContactMessage.Status(target_status).label}."
            )

        previous_status = message.status
        message.status = target_status
        message.save(update_fields=("status", "updated_at"))
        ContactMessageEvent.objects.create(
            contact_message=message,
            actor=actor,
            event_type=ContactMessageEvent.EventType.STATUS_CHANGED,
            from_status=previous_status,
            to_status=target_status,
        )
        transaction.on_commit(
            lambda message_id=message.pk, old=previous_status, new=target_status: logger.info(
                "Contact message transitioned.",
                extra={
                    "event": "contact_transition_completed",
                    "operation": "contact_status",
                    "object_type": "contact_message",
                    "object_id": message_id,
                    "from_state": old,
                    "to_state": new,
                },
            ),
            robust=True,
        )
        return TransitionResult(instance=message, changed=True)
