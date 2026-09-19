from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("search/", views.search, name="search"),
    path("contact/", views.contact, name="contact"),
    path("about/", views.about, name="about"),
    path("checkout/", views.checkout, name="checkout"),
    path(
        "order/<str:number>/<uuid:token>/",
        views.order_confirmation,
        name="order_confirmation",
    ),
    path("api/checkout/", views.create_order, name="create_order"),
    path("api/checkout/quote/", views.quote_order, name="quote_order"),
    path(
        "index.html",
        RedirectView.as_view(pattern_name="store:home", permanent=True),
        name="legacy_home",
    ),
    path(
        "shop2.html",
        RedirectView.as_view(pattern_name="store:shop", permanent=True),
        name="legacy_shop",
    ),
    path("product.html", views.legacy_product, name="legacy_product"),
    path(
        "checkout.html",
        RedirectView.as_view(pattern_name="store:checkout", permanent=True),
        name="legacy_checkout",
    ),
    path(
        "contact.html",
        RedirectView.as_view(pattern_name="store:contact", permanent=True),
        name="legacy_contact",
    ),
    path(
        "about.html",
        RedirectView.as_view(pattern_name="store:about", permanent=True),
        name="legacy_about",
    ),
]
