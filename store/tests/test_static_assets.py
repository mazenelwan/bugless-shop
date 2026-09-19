import hashlib
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class DerivedStaticAssetTests(SimpleTestCase):
    ASSET_PAIRS = (
        ("home.css", "store/css/home.css"),
        ("shop2.css", "store/css/shop2.css"),
        ("product.css", "store/css/product.css"),
        ("checkout.css", "store/css/checkout.css"),
        ("contact.css", "store/css/contact.css"),
        ("about.css", "store/css/about.css"),
    )

    def digest(self, path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def test_namespaced_css_is_an_exact_derivative_of_the_sot(self):
        for source_name, static_name in self.ASSET_PAIRS:
            with self.subTest(asset=source_name):
                source = settings.BASE_DIR / "frontend" / source_name
                derived = finders.find(static_name)
                self.assertIsNotNone(derived)
                self.assertEqual(self.digest(source), self.digest(derived))

    def test_namespaced_about_image_is_an_exact_derivative_of_the_sot(self):
        source = (
            settings.BASE_DIR
            / "frontend"
            / "WhatsApp Image 2025-09-28 at 07.29.37_52263063.jpg"
        )
        derived = finders.find("store/images/about-profile.jpg")
        self.assertIsNotNone(derived)
        self.assertEqual(self.digest(source), self.digest(derived))

    def test_frontend_sot_matches_the_recorded_manifest(self):
        manifest_path = settings.BASE_DIR / "docs" / "frontend" / "sot-sha256.txt"
        manifest = {}
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            digest, filename = line.split("  ", 1)
            manifest[filename] = digest

        frontend = settings.BASE_DIR / "frontend"
        actual_names = {path.name for path in frontend.iterdir() if path.is_file()}
        self.assertEqual(set(manifest), actual_names)
        for filename, expected_digest in manifest.items():
            with self.subTest(asset=filename):
                self.assertEqual(
                    self.digest(frontend / filename),
                    expected_digest.casefold(),
                )

    def test_unnamespaced_sot_assets_are_not_exposed_by_static_finders(self):
        self.assertIsNone(finders.find("home.css"))
        self.assertIsNone(finders.find("product-data.js"))
