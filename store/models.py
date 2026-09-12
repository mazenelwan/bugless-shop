from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

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
    is_active = models.BooleanField(default=True)
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self): return self.name

class Product(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    sku = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT)
    stock = models.PositiveIntegerField(default=0)
    sold_out = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    class Meta: ordering = ['category__name', 'name']
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(f'{self.name}-{self.sku}')
        super().save(*args, **kwargs)
    @property
    def available(self): return self.is_active and not self.sold_out and self.stock > 0
    def __str__(self): return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['display_order', 'id']

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    size = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=40, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta: constraints = [models.UniqueConstraint(fields=['product', 'size', 'color'], name='unique_product_variant')]
    def __str__(self): return ' / '.join(filter(None, [self.product.name, self.color, self.size]))

class Order(TimeStampedModel):
    class Status(models.TextChoices): PENDING='pending','Pending'; CONFIRMED='confirmed','Confirmed'; PREPARING='preparing','Preparing'; SHIPPED='shipped','Shipped'; DELIVERED='delivered','Delivered'; CANCELLED='cancelled','Cancelled'
    number = models.CharField(max_length=24, unique=True, editable=False)
    customer_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=80, default='Cash on delivery')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    def save(self, *args, **kwargs):
        if not self.number: self.number = f'BF-{self.created_at:%Y%m%d}' if self.created_at else ''
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f'BF-{self.pk:06d}'
            type(self).objects.filter(pk=self.pk).update(number=self.number)
    def __str__(self): return self.number or 'New order'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    selected_size = models.CharField(max_length=40, blank=True)
    selected_color = models.CharField(max_length=40, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

class ContactMessage(TimeStampedModel):
    class Status(models.TextChoices): NEW='new','New'; READ='read','Read'; REPLIED='replied','Replied'; ARCHIVED='archived','Archived'
    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    def __str__(self): return f'{self.name}: {self.subject or "Message"}'

class HomeContent(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    cta_text = models.CharField(max_length=80, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['display_order', 'id']
