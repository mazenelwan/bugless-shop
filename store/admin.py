from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied

from .models import (
    Category,
    ContactMessage,
    ContactMessageEvent,
    HomeContent,
    Order,
    OrderEvent,
    OrderItem,
    Product,
    ProductImage,
    ProductVariant,
    Promotion,
)
from .services.operations import (
    OperationsError,
    transition_order,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    ordering = ("display_order", "id")


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    ordering = ("display_order", "id")
    readonly_fields = ("public_id",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "display_order",
        "price",
        "stock",
        "sold_out",
        "is_active",
        "featured",
    )
    list_editable = ("display_order", "sold_out", "is_active", "featured")
    list_filter = ("category", "sold_out", "is_active", "featured")
    search_fields = ("name", "sku", "legacy_id", "description")
    ordering = ("category__display_order", "display_order", "id")
    readonly_fields = ("public_id", "created_at", "updated_at")
    list_select_related = ("category",)
    inlines = (ProductImageInline, ProductVariantInline)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "is_active", "updated_at")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "discount_type",
        "value",
        "is_active",
        "starts_at",
        "ends_at",
        "times_used",
    )
    list_filter = ("discount_type", "is_active", "starts_at", "ends_at")
    search_fields = ("code", "name", "description")
    filter_horizontal = ("categories", "products")
    readonly_fields = ("times_used", "created_at", "updated_at")
    ordering = ("code",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "product",
        "variant",
        "product_public_id",
        "variant_public_id",
        "product_name",
        "product_sku",
        "variant_label",
        "price",
        "quantity",
        "selected_size",
        "selected_color",
        "subtotal",
    )

    def has_add_permission(self, request, obj=None):
        return False


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    fields = (
        "event_type",
        "from_status",
        "to_status",
        "from_payment_status",
        "to_payment_status",
        "actor",
        "note",
        "created_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "customer_name",
        "phone",
        "total_amount",
        "currency",
        "payment_status",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    search_fields = ("number", "customer_name", "email", "phone")
    ordering = ("-created_at", "-id")
    list_select_related = ("customer", "promotion")
    date_hierarchy = "created_at"
    inlines = (OrderItemInline, OrderEventInline)
    actions = (
        "mark_confirmed",
        "mark_preparing",
        "mark_shipped",
        "mark_delivered",
        "cancel_and_restock",
    )
    readonly_fields = (
        "number",
        "confirmation_token",
        "idempotency_key",
        "request_fingerprint",
        "customer",
        "customer_name",
        "phone",
        "email",
        "address",
        "city",
        "subtotal_amount",
        "discount_amount",
        "delivery_fee",
        "tax_amount",
        "total_amount",
        "currency",
        "promotion",
        "promotion_code",
        "payment_method",
        "payment_status",
        "status",
        "inventory_restocked_at",
        "notes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_transition_order_permission(self, request):
        return request.user.has_perm("store.transition_order")

    def has_cancel_order_permission(self, request):
        return request.user.has_perm("store.cancel_order")

    def _run_order_action(self, request, queryset, operation, target, label):
        changed = 0
        unchanged = 0
        failed = 0
        first_error = ""
        for order_id in queryset.order_by("pk").values_list("pk", flat=True):
            try:
                result = operation(
                    order_id,
                    target,
                    request.user,
                    note="Django admin action",
                )
            except (OperationsError, PermissionDenied) as error:
                failed += 1
                first_error = first_error or str(error)
            else:
                if result.changed:
                    changed += 1
                else:
                    unchanged += 1

        if changed:
            self.message_user(request, f"{changed} order(s) {label}.", messages.SUCCESS)
        if unchanged:
            self.message_user(
                request,
                f"{unchanged} order(s) were already in the requested state.",
                messages.INFO,
            )
        if failed:
            detail = f" First error: {first_error}" if first_error else ""
            self.message_user(
                request,
                f"{failed} order(s) could not be updated.{detail}",
                messages.WARNING,
            )

    @admin.action(description="Move selected orders to confirmed", permissions=["transition_order"])
    def mark_confirmed(self, request, queryset):
        self._run_order_action(
            request,
            queryset,
            transition_order,
            Order.Status.CONFIRMED,
            "moved to confirmed",
        )

    @admin.action(description="Move selected orders to preparing", permissions=["transition_order"])
    def mark_preparing(self, request, queryset):
        self._run_order_action(
            request,
            queryset,
            transition_order,
            Order.Status.PREPARING,
            "moved to preparing",
        )

    @admin.action(description="Move selected orders to shipped", permissions=["transition_order"])
    def mark_shipped(self, request, queryset):
        self._run_order_action(
            request,
            queryset,
            transition_order,
            Order.Status.SHIPPED,
            "moved to shipped",
        )

    @admin.action(description="Move selected orders to delivered", permissions=["transition_order"])
    def mark_delivered(self, request, queryset):
        self._run_order_action(
            request,
            queryset,
            transition_order,
            Order.Status.DELIVERED,
            "moved to delivered",
        )

    @admin.action(description="Cancel and restock selected orders", permissions=["cancel_order"])
    def cancel_and_restock(self, request, queryset):
        self._run_order_action(
            request,
            queryset,
            transition_order,
            Order.Status.CANCELLED,
            "cancelled and restocked",
        )

@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("order", "event_type", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("order__number",)
    readonly_fields = (
        "order",
        "actor",
        "event_type",
        "from_status",
        "to_status",
        "from_payment_status",
        "to_payment_status",
        "note",
        "created_at",
    )
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ContactMessageEventInline(admin.TabularInline):
    model = ContactMessageEvent
    extra = 0
    can_delete = False
    fields = ("event_type", "from_status", "to_status", "actor", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "phone", "subject")
    ordering = ("-created_at", "-id")
    inlines = (ContactMessageEventInline,)
    actions = ()
    readonly_fields = (
        "submission_id",
        "request_fingerprint",
        "name",
        "email",
        "phone",
        "subject",
        "message",
        "status",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessageEvent)
class ContactMessageEventAdmin(admin.ModelAdmin):
    list_display = ("contact_message_id", "event_type", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    readonly_fields = (
        "contact_message",
        "actor",
        "event_type",
        "from_status",
        "to_status",
        "created_at",
    )
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HomeContent)
class HomeContentAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "is_active", "updated_at")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "description")
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at")


admin.site.site_header = "Bugless Fit dashboard"
admin.site.site_title = "Bugless Fit dashboard"
admin.site.index_title = "Store management"
