import json
import re
import uuid
from html import unescape
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from store.models import Category, Order, Product


class PublicCatalogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", stdout=StringIO())

    def test_all_authored_public_pages_render_their_derived_templates(self):
        cases = (
            ("store:home", "store/home.html", "store/css/home.css"),
            ("store:shop", "store/shop.html", "store/css/shop2.css"),
            ("store:checkout", "store/checkout.html", "store/css/checkout.css"),
            ("store:contact", "store/contact.html", "store/css/contact.css"),
            ("store:about", "store/about.html", "store/css/about.css"),
        )

        for route_name, template_name, static_path in cases:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template_name)
                self.assertContains(response, f"/static/{static_path}")
                self.assertNotContains(response, 'href="index.html"')
                self.assertNotContains(response, 'href="shop2.html"')

    def test_home_and_shop_preserve_authored_merchandising_order(self):
        home = self.client.get(reverse("store:home"))
        shop = self.client.get(reverse("store:shop"))
        expected = ["Men's Shirts", "Jacket", "Pants", "T-Shirts", "Polo", "Shoes"]

        for response in (home, shop):
            self.assertEqual(
                [category.name for category in response.context["categories"]],
                expected,
            )

        first_category = Category.objects.get(name=expected[0])
        self.assertContains(
            home,
            f'{reverse("store:shop")}#{first_category.slug}',
        )
        self.assertContains(shop, f'id="{first_category.slug}"')

    def test_shop_renders_database_products_and_public_cart_identifiers(self):
        response = self.client.get(reverse("store:shop"))
        product = Product.objects.get(legacy_id="shirts-01")

        self.assertContains(response, product.name)
        self.assertContains(response, str(product.public_id))
        self.assertContains(response, "(4.9⭐)")

        match = re.search(
            r'<script id="bf-catalog-data" type="application/json">(.*?)</script>',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        payload = json.loads(unescape(match.group(1)))
        self.assertEqual(len(payload), 24)
        self.assertEqual(
            {"productId", "legacyId", "name", "price", "image", "url", "available", "variants"},
            set(payload[0]),
        )

    def test_search_matches_category_and_hides_unmatched_categories(self):
        response = self.client.get(reverse("store:search"), {"q": "jacket"})
        categories = list(response.context["categories"])

        self.assertEqual([category.name for category in categories], ["Jacket"])
        self.assertEqual(len(categories[0].visible_products), 4)
        self.assertNotContains(response, 'id="pants"')

    def test_inactive_product_and_category_are_not_public(self):
        product = Product.objects.get(legacy_id="shoes-04")
        product.is_active = False
        product.save(update_fields=("is_active", "updated_at"))

        shop_response = self.client.get(reverse("store:shop"))
        detail_response = self.client.get(
            reverse("store:product_detail", args=(product.slug,))
        )

        self.assertNotContains(shop_response, str(product.public_id))
        self.assertEqual(detail_response.status_code, 404)

        category = Category.objects.get(name="Jacket")
        category.is_active = False
        category.save(update_fields=("is_active", "updated_at"))
        jacket = Product.objects.filter(category=category).first()
        self.assertEqual(
            self.client.get(
                reverse("store:product_detail", args=(jacket.slug,))
            ).status_code,
            404,
        )

    def test_product_detail_is_server_rendered_with_related_products(self):
        product = Product.objects.get(legacy_id="shirts-01")
        response = self.client.get(
            reverse("store:product_detail", args=(product.slug,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "store/product_detail.html")
        self.assertContains(response, product.sku)
        self.assertContains(response, "EGP 459.00")
        self.assertEqual(len(response.context["related"]), 4)

    def test_legacy_page_routes_redirect_to_named_django_routes(self):
        cases = (
            ("/index.html", reverse("store:home")),
            ("/shop2.html", reverse("store:shop")),
            ("/checkout.html", reverse("store:checkout")),
            ("/contact.html", reverse("store:contact")),
            ("/about.html", reverse("store:about")),
        )
        for legacy_path, destination in cases:
            with self.subTest(path=legacy_path):
                response = self.client.get(legacy_path)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response.headers["Location"], destination)

        product = Product.objects.get(legacy_id="shirts-01")
        response = self.client.get("/product.html", {"id": product.legacy_id})
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.headers["Location"],
            reverse("store:product_detail", args=(product.slug,)),
        )


class OrderConfirmationPrivacyTests(TestCase):
    def make_order(self, **overrides):
        values = {
            "customer_name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "01000000000",
            "address": "Cairo",
        }
        values.update(overrides)
        return Order.objects.create(**values)

    def test_confirmation_requires_matching_private_token(self):
        order = self.make_order()

        self.assertEqual(self.client.get(f"/order/{order.number}/").status_code, 404)
        self.assertEqual(
            self.client.get(
                reverse(
                    "store:order_confirmation",
                    args=(order.number, uuid.uuid4()),
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "store:order_confirmation",
                    args=(order.number, order.confirmation_token),
                )
            ).status_code,
            200,
        )

    def test_authenticated_customer_cannot_open_another_customers_order(self):
        User = get_user_model()
        owner = User.objects.create_user("owner@example.com", "Owner-password-728!")
        intruder = User.objects.create_user("intruder@example.com", "Other-password-827!")
        order = self.make_order(customer=owner)
        self.client.force_login(intruder)

        response = self.client.get(
            reverse(
                "store:order_confirmation",
                args=(order.number, order.confirmation_token),
            )
        )

        self.assertEqual(response.status_code, 404)
