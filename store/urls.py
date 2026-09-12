from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), path('shop/', views.shop, name='shop'), path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('search/', views.search, name='search'), path('contact/', views.contact, name='contact'), path('checkout/', views.checkout, name='checkout'),
    path('order/<str:number>/', views.order_confirmation, name='order_confirmation'), path('api/checkout/', views.create_order, name='create_order'),
]
