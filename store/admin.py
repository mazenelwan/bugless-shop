from django.contrib import admin
from .models import Category, ContactMessage, HomeContent, Order, OrderItem, Product, ProductImage, ProductVariant

class ProductImageInline(admin.TabularInline): model = ProductImage; extra = 1
class ProductVariantInline(admin.TabularInline): model = ProductVariant; extra = 1
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'old_price', 'stock', 'sold_out', 'is_active', 'featured')
    list_filter = ('category', 'sold_out', 'is_active', 'featured')
    search_fields = ('name', 'sku', 'description')
    ordering = ('category', 'name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at'); list_filter = ('is_active',); search_fields = ('name',); prepopulated_fields = {'slug': ('name',)}
class OrderItemInline(admin.TabularInline): model = OrderItem; extra = 0; readonly_fields = ('product_name', 'price', 'quantity', 'selected_size', 'selected_color', 'subtotal')
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'customer_name', 'phone', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at'); search_fields = ('number', 'customer_name', 'email', 'phone'); ordering = ('-created_at',); inlines = [OrderItemInline]
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'created_at'); list_filter = ('status', 'created_at'); search_fields = ('name', 'email', 'subject', 'message'); ordering = ('-created_at',)
@admin.register(HomeContent)
class HomeContentAdmin(admin.ModelAdmin): list_display = ('title', 'is_active', 'display_order', 'updated_at'); list_filter = ('is_active',); ordering = ('display_order',)
