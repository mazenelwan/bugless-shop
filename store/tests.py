import json
from django.test import TestCase
from django.urls import reverse
from .models import Category, ContactMessage, Order, Product, ProductImage

class CommerceFlowTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Test category')
        self.product = Product.objects.create(name='Test shirt', sku='TEST-SHIRT-1', price='100.00', stock=3, category=category)
        ProductImage.objects.create(product=self.product, image='https://example.com/shirt.jpg', is_primary=True)
    def test_product_is_database_backed(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertContains(response, 'EGP 100.00')
        self.assertContains(response, 'TEST-SHIRT-1')
    def test_checkout_uses_server_price_and_reduces_stock(self):
        response = self.client.post(reverse('create_order'), data=json.dumps({'customer': {'name':'Ada', 'email':'ada@example.com', 'phone':'010', 'address':'Cairo'}, 'items':[{'product_id':self.product.id, 'quantity':2, 'size':'M', 'color':'Black'}]}), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(Order.objects.get().total_amount, 200)
    def test_contact_message_is_persisted(self):
        self.client.post(reverse('contact'), {'name':'Ada','email':'ada@example.com','message':'Hello'})
        self.assertEqual(ContactMessage.objects.count(), 1)
