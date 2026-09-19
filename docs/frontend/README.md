# Frontend Source of Truth and Django Integration

Last updated: 2026-09-16 (Phase 6 browser evidence)

## Source-of-truth rule

Every file below `frontend/` is preserved user work. Its rendered appearance,
DOM/class hooks, spacing, typography, colors, imagery, and responsive behavior
are the public UI contract. Django templates/static modules are derived copies
and may change; the SOT may not be edited to make integration easier.

All 21 SOT SHA-256 values were captured before Phase 2 and compared afterward.
The final manifest matched byte-for-byte and is retained in
`docs/frontend/sot-sha256.txt`.

## SOT inventory

| Page | HTML | CSS | JavaScript |
|---|---|---|---|
| Home | `index.html` | `home.css` | `home.js` |
| Shop | `shop2.html` | `shop2.css` | `shop2 (4).js`, `shop-product-links.js`, `product-data.js`, and inline cart code |
| Product | `product.html` | `product.css` | `product.js`, `product-data.js` |
| Checkout | `checkout.html` | `checkout.css` | `checkout.js` |
| Contact | `contact.html` | `contact.css` | `contact.js` |
| About | `about.html` | `about.css` | `about.js` |

The About photo
`WhatsApp Image 2025-09-28 at 07.29.37_52263063.jpg` remains beside the
standalone page so its original relative path still works.

## Derived Django page map

| Route | Template | Namespaced CSS | Progressive JavaScript |
|---|---|---|---|
| Home | `templates/store/home.html` | `store/css/home.css` | `store/js/site.js`, `store/js/home.js` |
| Shop | `templates/store/shop.html` | `store/css/shop2.css` | `store/js/site.js`, `store/js/cart.js`, `store/js/shop.js` |
| Product | `templates/store/product_detail.html` | `store/css/product.css` | `store/js/site.js`, `store/js/cart.js`, `store/js/product.js` |
| Checkout | `templates/store/checkout.html` | `store/css/checkout.css` | `store/js/site.js`, `store/js/cart.js`, `store/js/checkout.js` |
| Contact | `templates/store/contact.html` | `store/css/contact.css` | `store/js/site.js` |
| About | `templates/store/about.html` | `store/css/about.css` | `store/js/site.js` |

`templates/store/order_confirmation.html` is an additional secure,
server-rendered state; no standalone confirmation page exists.

The derived About image is
`store/static/store/images/about-profile.jpg`. All six derived CSS files and
that image are byte-for-byte copies of the corresponding SOT assets.

## Shared markup

Three partials are used only where the authored pages share a stable structure:

- `partials/head_dependencies.html`: third-party fonts/icons/framework links;
- `partials/public_header.html`: brand, server search, navigation, cart hook,
  and accessible mobile-menu controls; and
- `partials/about_footer.html`: authored informational footer.

There is deliberately no generic base template forcing every page into a new
DOM. The obsolete pre-integration `base.html` was removed. Each page keeps its
own authored outer structure and stylesheet behavior.

## Dynamic data rules

- Home category cards come from active categories in admin-controlled order.
- Home-to-Shop category fragments use the stable category slug rather than a
  name containing spaces or punctuation.
- Shop sections/cards come from active database categories/products in authored
  order.
- Product detail, price, image gallery, stock status, option controls, and
  related products are rendered by Django.
- Search submits to a named Django route and is progressively filtered in the
  current document while typing.
- Internal links use `{% url %}`; local assets use `{% static %}`.
- Legacy authored `.html` paths remain usable through permanent redirects,
  not template-relative links.
- Catalog metadata is embedded with Django's safe `json_script` mechanism.

## Canonical browser cart

Storage key: `bfCart`.

Version 1 shape:

```json
{
  "version": 1,
  "lines": [
    {
      "productId": "server-issued-product-uuid",
      "variantId": "server-issued-variant-uuid-or-null",
      "quantity": 1
    }
  ]
}
```

Rules:

- local storage contains only server identifiers and an integer quantity;
- it never stores an authoritative name, image, price, discount, availability,
  subtotal, or total;
- a line key is `productId + variantId`;
- duplicate keys coalesce in first-seen order;
- quantity must be an integer from 1 through 99; merged values cap at 99;
- malformed entries are discarded;
- cart badge, sidebar, quantity, remove, clear, Buy Now, and checkout navigation
  use this same module across public pages;
- prices shown in the browser are estimates from server-rendered display
  metadata, not order values.

### Legacy migration

The first Phase 2 load deterministically upgrades old array-based Shop/Product
carts:

1. resolve a current UUID directly when present;
2. otherwise resolve an authored legacy ID;
3. otherwise resolve a normalized name only when exactly one catalog product
   has that name;
4. resolve legacy size/color to a variant only when exactly one variant matches;
5. drop missing, malformed, or ambiguous legacy lines; and
6. coalesce the resulting canonical lines and immediately persist Version 1.

This specifically avoids guessing among the four authored products that share
the name `Man Long Sleeve Shirt`.

Canonical lines whose products later disappear remain visible as unavailable
display entries until removed. Checkout server validation rejects those stale
identifiers during quote/create.

## Page interactions

- `site.js` provides one keyboard/ARIA-aware mobile menu behavior.
- `home.js` live-filters category projects without preventing authoritative
  search submission.
- `shop.js` navigates cards to their server slug, adds variantless available
  products, and sends variant-backed products to detail for an exact selection.
- `product.js` controls gallery thumbnails, quantity, exact variant matching,
  Add to Cart, Buy Now, and the cart sidebar.
- `checkout.js` renders the canonical cart summary, requests advisory promo
  quotes, creates orders through the canonical API, retains a session-scoped
  cryptographic retry UUID across network failures, binds safe validation
  feedback, prevents duplicate button submits, clears state only after
  confirmed create/replay, and follows the private confirmation URL. It never
  sends browser names/prices/totals as commerce authority.

## Account UI addition

Phase 3 added templates under `templates/accounts/` and the namespaced
`accounts/accounts.css`. No account-page SOT exists, so those screens reuse the
brand's red/black visual language without changing the DOM, styles, or
navigation of the six authored public pages. Static discovery resolves the
account stylesheet alongside namespaced store assets.

## Intentional Phase 2 differences from standalone behavior

These changes do not redesign the pages:

- Relative page/asset URLs became named Django/static URLs.
- Search placeholder copy says `Search products` instead of the unrelated
  `Search for Destinations`.
- Product identifiers/status copy comes from current database SKU/availability.
- Search is server-backed in addition to live filtering.
- Contact posts to Django with CSRF instead of the nonexistent
  `contact-mail.php`; Phase 5 added invisible idempotency/honeypot controls and
  error/success states inside the authored form structure without modifying
  the byte-identical SOT-derived stylesheet.
- The Google Map is allowed to load in the Django page; it was blank in one
  standalone capture because of local file/timing behavior.
- Invalid/malformed accessibility hooks and external-link attributes were
  corrected where the visual result did not change.
- Checkout disables the SOT's insecure client promo list and fake order success.
  Phase 2 displayed an explicit stop until the secure Phase 4 service existed.

## Phase 4 Checkout integration

The existing Checkout structure, classes, stylesheet, item summary, promo box,
shipping fields, button, and responsive behavior remain in place. Integration
changes are limited to server-owned behavior and safe attributes:

- the form holds named quote/create route URLs and a Django CSRF token;
- signed-in users receive escaped name/email initial values; guest fields stay
  blank;
- input lengths mirror server/schema limits; the SOT field set remains intact,
  so optional `city` is submitted as blank rather than adding a new visual row;
- Apply sends only cart UUIDs/quantities and the code, then renders server quote
  totals as an estimate;
- Confirm sends the customer strings, normalized cart, promo code, and retry
  UUID—never display price or total data;
- server field errors are inserted with `textContent`, controls receive
  `aria-invalid`, and no raw HTML/error body is rendered;
- a network failure retains cart and retry key; an idempotency conflict is not
  silently replaced with a new key; and
- successful create or replay clears `bfCart`/retry state and redirects to the
  tokenized, `noindex`/`no-store` server confirmation with immutable items and
  totals.

No authored file under `frontend/` and no derived SOT CSS/image changed during
Phase 4. The complete 74-test run revalidated all 21 source hashes and every
exact CSS/image derivative. Browser module syntax and static collection also
passed. Phase 6 now runs the critical Playwright journeys at 1440x1200 and
390x844, including guest/account checkout, private confirmation/history,
contact validation/replay, read-only contact admin, and status-only order admin.

## Visual comparison evidence

`.proofs/phase2/` contains:

- `sot-desktop/`: six pages at 1440 x 1200;
- `django-desktop/`: the corresponding six Django routes;
- `sot-mobile/`: six pages at 390 x 844; and
- `django-mobile/`: the corresponding six Django routes.

Manual pair review confirmed the authored structure, spacing, responsive
overflow behavior, typography, colors, and imagery were preserved. Expected
content-only differences are listed above. Browser capture logged no page or
asset failures; only the optional, unspecified `/favicon.ico` returned 404.

## Static isolation

- Django static discovery sees `store/...` assets and Django admin assets.
- It does not see unnamespaced `home.css`, `product-data.js`, or the flat
  SOT bundle.
- `collectstatic --noinput --dry-run` resolves 141 files without exposing
  backend source, the SQLite database, templates, or environment files.

## External dependencies and deferred hardening

The design still uses Bootstrap, jQuery, Popper, Boxicons, Google Fonts, Font
Awesome, remote product/marketing images, Google Maps, and authored external
links. Phase 6 tested their browser/security implications and CSP behavior
without redesigning the public UI. The completed harness stubs all third-party
requests deterministically and fails on browser CSP/refusal errors. Production
CDN, fallback, and managed-media selection remain outside this learning project.

Dedicated JavaScript unit tests and automated screenshot-diff thresholds do not
exist. Phase 2 retains the manual screenshot pairs; Phase 6 adds repeatable
Chromium E2E with failure-only screenshots/traces rather than pixel-diff claims.
