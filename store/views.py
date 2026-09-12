import json
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Category, ContactMessage, Order, OrderItem, Product

def home(request): return render(request, 'store/home.html', {'home_content': []})
def shop(request):
    products = Product.objects.filter(is_active=True, category__is_active=True).select_related('category').prefetch_related('images')
    return render(request, 'store/shop.html', {'categories': Category.objects.filter(is_active=True).prefetch_related('products'), 'products': products})
def search(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.filter(is_active=True).filter(Q(name__icontains=query) | Q(category__name__icontains=query) | Q(description__icontains=query)).select_related('category').prefetch_related('images') if query else Product.objects.none()
    return render(request, 'store/shop.html', {'categories': [], 'products': products, 'query': query})
def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category').prefetch_related('images', 'variants'), slug=slug, is_active=True)
    related = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk).prefetch_related('images')[:4]
    return render(request, 'store/product_detail.html', {'product': product, 'related': related})
def contact(request):
    if request.method == 'POST':
        ContactMessage.objects.create(name=request.POST.get('name','').strip(), email=request.POST.get('email','').strip(), phone=request.POST.get('phone','').strip(), subject=request.POST.get('subject','').strip(), message=request.POST.get('message','').strip())
        return redirect('contact')
    return render(request, 'store/contact.html')
def checkout(request): return render(request, 'store/checkout.html')
def order_confirmation(request, number): return render(request, 'store/order_confirmation.html', {'order': get_object_or_404(Order, number=number)})
@require_POST
def create_order(request):
    try: data = json.loads(request.body)
    except (TypeError, json.JSONDecodeError): return JsonResponse({'error':'Invalid order payload.'}, status=400)
    items = data.get('items', []); customer = data.get('customer', {})
    if not items or not all(customer.get(k, '').strip() for k in ('name','email','phone','address')): return JsonResponse({'error':'Complete customer and cart information is required.'}, status=400)
    with transaction.atomic():
        order = Order.objects.create(customer_name=customer['name'].strip(), email=customer['email'].strip(), phone=customer['phone'].strip(), address=customer['address'].strip(), city=customer.get('city','').strip(), notes=customer.get('notes','').strip(), total_amount=Decimal('0'))
        total = Decimal('0')
        for item in items:
            try: quantity = int(item['quantity'])
            except (KeyError, TypeError, ValueError): return JsonResponse({'error':'Invalid quantity.'}, status=400)
            product = Product.objects.select_for_update().filter(pk=item.get('product_id'), is_active=True).first()
            if not product or not product.available or quantity < 1 or quantity > product.stock: return JsonResponse({'error':'One or more products are unavailable or out of stock.'}, status=400)
            subtotal = product.price * quantity; total += subtotal
            OrderItem.objects.create(order=order, product=product, product_name=product.name, price=product.price, quantity=quantity, selected_size=item.get('size',''), selected_color=item.get('color',''), subtotal=subtotal)
            product.stock -= quantity; product.save(update_fields=['stock', 'updated_at'])
        order.total_amount = total; order.save(update_fields=['total_amount', 'updated_at'])
    return JsonResponse({'number': order.number, 'total': str(order.total_amount)}, status=201)
