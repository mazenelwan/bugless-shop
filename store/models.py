import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.text import slugify


ZERO = Decimal("0.00")


def generate_order_number():
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:12].upper()
    return f"BF-{date_part}-{random_part}"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("display_order", "id")
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    legacy_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    sku = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(ZERO)],
    )
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(ZERO)],
    )
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(ZERO), MaxValueValidator(Decimal("5.0"))],
        help_text="Optional display score from the source catalog; not a review aggregate.",
    )
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.PROTECT,
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    stock = models.PositiveIntegerField(
        default=0,
        help_text="Used only when the product has no active variants.",
    )
    sold_out = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("category__display_order", "display_order", "id")
        indexes = [
            models.Index(
                fields=("is_active", "category", "display_order"),
                name="product_catalog_order_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(old_price__isnull=True) | Q(old_price__gte=F("price")),
                name="product_old_price_not_below_price",
            )
        ]

    def clean(self):
        super().clean()
        if self.old_price is not None and self.old_price < self.price:
            raise ValidationError(
                {"old_price": "Old price cannot be lower than the current price."}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.sku}")
        if self.legacy_id == "":
            self.legacy_id = None
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        images = list(self.images.all())
        return next((image for image in images if image.is_primary), images[0] if images else None)

    @property
    def active_variants(self):
        return [variant for variant in self.variants.all() if variant.is_active]

    @property
    def uses_variants(self):
        return bool(self.active_variants)

    @property
    def available_stock(self):
        variants = self.active_variants
        if variants:
            return sum(variant.stock for variant in variants)
        return self.stock

    @property
    def available(self):
        return self.is_active and not self.sold_out and self.available_stock > 0

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product",),
                condition=Q(is_primary=True),
                name="one_primary_image_per_product",
            ),
            models.UniqueConstraint(
                fields=("product", "display_order"),
                name="unique_product_image_order",
            ),
        ]

    def __str__(self):
        return self.alt_text or f"Image for {self.product}"


class ProductVariant(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    size = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=40, blank=True)
    stock = models.PositiveIntegerField(default=0)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product", "size", "color"),
                name="unique_product_variant",
            ),
            models.CheckConstraint(
                condition=~(Q(size="") & Q(color="")),
                name="product_variant_has_option",
            ),
        ]

    def clean(self):
        super().clean()
        self.size = self.size.strip()
        self.color = self.color.strip()
        if not self.size and not self.color:
            raise ValidationError("A product variant must have a size or color.")

    @property
    def label(self):
        return " / ".join(filter(None, (self.color, self.size)))

    @property
    def available(self):
        return self.is_active and self.stock > 0 and self.product.is_active

    def __str__(self):
        return " / ".join(filter(None, (self.product.name, self.color, self.size)))


class Promotion(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed amount"

    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=12, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    maximum_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    per_customer_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(default=False, db_index=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="promotions")
    products = models.ManyToManyField(Product, blank=True, related_name="promotions")

    class Meta:
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(
                Lower("code"),
                name="promotion_code_case_insensitive_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(discount_type="fixed", value__gt=ZERO)
                    | Q(
                        discount_type="percentage",
                        value__gt=ZERO,
                        value__lte=Decimal("100.00"),
                    )
                ),
                name="promotion_value_valid_for_type",
            ),
            models.CheckConstraint(
                condition=Q(maximum_discount__isnull=True)
                | Q(maximum_discount__gt=ZERO),
                name="promotion_max_discount_positive",
            ),
            models.CheckConstraint(
                condition=Q(starts_at__isnull=True)
                | Q(ends_at__isnull=True)
                | Q(ends_at__gt=F("starts_at")),
                name="promotion_window_valid",
            ),
        ]

    def clean(self):
        super().clean()
        self.code = self.code.strip().upper()
        if self.discount_type == self.DiscountType.PERCENTAGE and self.value > 100:
            raise ValidationError({"value": "Percentage promotions cannot exceed 100%."})
        if self.value <= ZERO:
            raise ValidationError({"value": "Promotion value must be greater than zero."})
        if self.maximum_discount is not None and self.maximum_discount <= ZERO:
            raise ValidationError(
                {"maximum_discount": "Maximum discount must be greater than zero."}
            )
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "End time must be after start time."})

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_current(self):
        now = timezone.now()
        return (
            self.is_active
            and (self.starts_at is None or self.starts_at <= now)
            and (self.ends_at is None or self.ends_at > now)
            and (self.usage_limit is None or self.times_used < self.usage_limit)
        )

    def __str__(self):
        return self.code


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PREPARING = "preparing", "Preparing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = "cash_on_delivery", "Cash on delivery"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    number = models.CharField(
        max_length=24,
        unique=True,
        editable=False,
        default=generate_order_number,
    )
    confirmation_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        default="",
        editable=False,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )
    customer_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    currency = models.CharField(max_length=3, default="EGP")
    promotion = models.ForeignKey(
        Promotion,
        null=True,
        blank=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )
    promotion_code = models.CharField(max_length=40, blank=True)
    payment_method = models.CharField(
        max_length=24,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH_ON_DELIVERY,
    )
    payment_status = models.CharField(
        max_length=12,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    inventory_restocked_at = models.DateTimeField(null=True, blank=True, editable=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("status", "created_at"), name="order_status_created_idx"),
            models.Index(fields=("email", "created_at"), name="order_email_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(subtotal_amount__gte=ZERO),
                name="order_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__gte=ZERO)
                & Q(discount_amount__lte=F("subtotal_amount")),
                name="order_discount_within_subtotal",
            ),
            models.CheckConstraint(
                condition=Q(delivery_fee__gte=ZERO),
                name="order_delivery_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(tax_amount__gte=ZERO),
                name="order_tax_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(total_amount__gte=ZERO),
                name="order_total_nonnegative",
            ),
        ]
        permissions = [
            ("transition_order", "Can transition order status"),
            ("cancel_order", "Can cancel and restock orders"),
            ("record_order_payment", "Can record order payment"),
            ("refund_order", "Can record order refunds"),
        ]

    def clean(self):
        super().clean()
        expected_total = (
            self.subtotal_amount
            - self.discount_amount
            + self.delivery_fee
            + self.tax_amount
        )
        if self.total_amount != expected_total:
            raise ValidationError(
                {"total_amount": "Total does not match subtotal, discount, delivery, and tax."}
            )

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    product_public_id = models.UUIDField(null=True, blank=True, editable=False)
    variant_public_id = models.UUIDField(null=True, blank=True, editable=False)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=80, blank=True)
    variant_label = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(ZERO)],
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    selected_size = models.CharField(max_length=40, blank=True)
    selected_color = models.CharField(max_length=40, blank=True)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(ZERO)],
    )

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="order_item_quantity_positive"),
            models.CheckConstraint(condition=Q(price__gte=ZERO), name="order_item_price_nonnegative"),
            models.CheckConstraint(
                condition=Q(subtotal__gte=ZERO),
                name="order_item_subtotal_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"


class OrderEvent(models.Model):
    class EventType(models.TextChoices):
        STATUS_CHANGED = "status_changed", "Status changed"
        PAYMENT_CHANGED = "payment_changed", "Payment changed"
        INVENTORY_RESTOCKED = "inventory_restocked", "Inventory restocked"

    order = models.ForeignKey(Order, related_name="events", on_delete=models.CASCADE)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="order_events",
        on_delete=models.SET_NULL,
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12, blank=True)
    from_payment_status = models.CharField(max_length=12, blank=True)
    to_payment_status = models.CharField(max_length=12, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("order", "event_type"),
                condition=Q(event_type="inventory_restocked"),
                name="one_inventory_restock_event_per_order",
            )
        ]

    def __str__(self):
        return f"{self.order.number}: {self.get_event_type_display()}"


class ContactMessage(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        READ = "read", "Read"
        REPLIED = "replied", "Replied"
        ARCHIVED = "archived", "Archived"

    submission_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request_fingerprint = models.CharField(max_length=64, editable=False)
    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)

    class Meta:
        ordering = ("-created_at", "-id")
        permissions = [
            ("manage_contactmessage", "Can manage contact message workflow"),
        ]

    def __str__(self):
        return f'{self.name}: {self.subject or "Message"}'


class ContactMessageEvent(models.Model):
    class EventType(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        STATUS_CHANGED = "status_changed", "Status changed"
        NOTIFICATION_SENT = "notification_sent", "Notification sent"
        NOTIFICATION_FAILED = "notification_failed", "Notification failed"

    contact_message = models.ForeignKey(
        ContactMessage,
        related_name="events",
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="contact_message_events",
        on_delete=models.SET_NULL,
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("contact_message", "event_type"),
                condition=Q(event_type="submitted"),
                name="one_submitted_event_per_contact",
            )
        ]

    def __str__(self):
        return f"Contact {self.contact_message_id}: {self.get_event_type_display()}"


class HomeContent(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    cta_text = models.CharField(max_length=80, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return self.title
