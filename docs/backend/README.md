# Django Backend

Last updated: 2026-09-16 (simplified staff dashboard)

## Applications

- Project package: `buglessfit`.
- `accounts`: custom email-based user model, manager, forms, throttling, views,
  templates, admin, migration, and customer order pages.
- `store`: catalog, promotions, orders, validated contact persistence,
  transactional checkout/operations/contact services, audit events, management
  commands, admin, public views, templates, and static assets.
- Supported dependency range: Django `>=5.2.17,<5.3` and
  `psycopg[binary]>=3.1`.

## Current routes

All storefront route names use the `store:` namespace.

| Path | Name | Method | Purpose |
|---|---|---|---|
| `/` | `store:home` | GET | Database-ordered category Home page |
| `/shop/` | `store:shop` | GET | Active catalog and optional `q` filtering |
| `/search/?q=...` | `store:search` | GET | Server-backed Shop search |
| `/product/<slug>/` | `store:product_detail` | GET | Active product, gallery, variants, and related products |
| `/checkout/` | `store:checkout` | GET | Checkout UI, signed-in identity prefill, and server display catalog |
| `/contact/` | `store:contact` | GET/POST | Validated, idempotent, abuse-aware SOT-shaped contact page |
| `/about/` | `store:about` | GET | Authored About page |
| `/order/<number>/<uuid:token>/` | `store:order_confirmation` | GET | Private token-protected confirmation |
| `/api/checkout/quote/` | `store:quote_order` | POST JSON | Read-only authoritative cart/promotion estimate |
| `/api/checkout/` | `store:create_order` | POST JSON | Atomic, idempotent order creation |
| `/health/` | `health` | GET | Minimal database-aware local health diagnostic |
| `/admin/` | Django admin | GET/POST | Staff administration |

Permanent compatibility redirects exist for `/index.html`, `/shop2.html`,
`/checkout.html`, `/contact.html`, and `/about.html`. The legacy
`/product.html?id=<legacy-id>` route resolves an active database product and
redirects to its slug route.

The `accounts:` namespace is mounted at `/accounts/` and provides register,
login, POST-only logout, profile, password change/reset, and owner-filtered
order list/detail routes. The exact path/method contract is maintained in
`docs/accounts/README.md`.

## Models

### Identity

`accounts.User` subclasses `AbstractUser`, removes `username`, and uses a
normalized case-insensitive unique email as `USERNAME_FIELD`. The custom
manager enforces staff/superuser flags, and the admin supports safe email-based
creation and search.

### Catalog

- `Category`: name, slug, description, remote-compatible image URL, explicit
  display order, active flag, timestamps.
- `Product`: UUID public ID, optional legacy ID, slug, SKU, catalog content,
  current/old EGP price, optional SOT display rating, explicit display order,
  aggregate stock, sold-out/active/featured flags, timestamps.
- `ProductImage`: URL, alt text, one-primary constraint, unique per-product
  display order.
- `ProductVariant`: UUID public ID, product, size/color options, stock,
  display order, active flag, unique option combination, and at least one
  nonblank option requirement.
- `HomeContent`: retained generic admin model; the authored Home page currently
  uses category data plus preserved marketing content rather than this model.

### Promotions and orders

- `Promotion`: case-insensitive code, fixed/percentage value, minimum subtotal,
  optional cap/window/global and per-customer limits, usage counter,
  active flag, and optional category/product scope.
- `Order`: unique generated number, private UUID confirmation token, unique
  UUID idempotency field, SHA-256 request fingerprint, nullable account owner,
  immutable contact/address snapshot, separate
  subtotal/discount/delivery/tax/total fields, EGP currency, promotion/code
  snapshot, cash-on-delivery payment method, payment status, lifecycle status,
  one-time inventory-restock marker, notes, and timestamps.
- `OrderItem`: nullable live product/variant references plus immutable public
  IDs, SKU, name, option label, selected options, unit price, quantity, and
  subtotal snapshots.
- `OrderEvent`: immutable actor, event type, old/new business or payment state,
  non-PII operation note, and timestamp. A partial unique constraint permits
  only one inventory-restocked event per order.

### Contact

`ContactMessage` stores an immutable unique submission UUID and semantic
fingerprint, normalized name/email/optional phone/subject/message, workflow
status, and timestamps. `ContactMessageEvent` stores immutable submission,
notification outcome, and attributable status-transition events without
copying submitted content.

## Database safeguards

- Case-insensitive unique constraints protect user email and promotion code.
- Public product/variant IDs and order tokens/keys are unique UUIDs.
- Old product price cannot be below current price.
- Product image primary/order constraints prevent ambiguous galleries.
- Variant rows require an option and unique product/size/color combination.
- Order and item amounts/quantities have nonnegative/positive checks.
- Order discount cannot exceed subtotal.
- Promotion percentage/value/window/cap rules have database checks.
- Contact submission UUIDs are unique; submitted-contact and inventory-restock
  audit event uniqueness prevents duplicate semantic events.
- Catalog and order workflow fields have indexes aligned with public/admin
  reads.

Model validation remains important for friendly messages; database constraints
are the last line of defense.

## Selectors and query behavior

`store/selectors.py` contains:

- `public_products()`: active products in active categories, ordered by
  category/product merchandising order, with category/images/variants loaded;
- `public_categories(query="")`: active categories containing matching
  products, with safe `icontains` search over product name, description,
  category name, and SKU; and
- `related_products(product, limit=4)`: same-category products first, then
  deterministic cross-category fallback.

Public views reuse these selectors so inactive records cannot leak through
individual routes.

`customer_orders(user)` returns only orders whose explicit `customer` foreign
key is the authenticated user. Email equality never grants ownership of a
guest order.

## Account HTTP behavior

Account forms normalize email and reject case-insensitive conflicts. Django's
authentication/password primitives provide session rotation, safe `next`
validation, password-change session continuity, enumeration-safe reset, and
single-use tokens. Login, registration, and reset are protected by configurable
cache counters whose keys contain only an HMAC of the direct peer IP and
optional normalized identity. Existing public navigation is unchanged.

## Admin behavior

- Users: email-based list/search/filter/create, permission controls, read-only
  login/join timestamps.
- Categories: display order and active status editable from the list.
- Products: full CRUD for the current product fields plus image and variant
  inlines; UUIDs and timestamps remain read-only. Catalog Managers and Store
  Managers receive the corresponding product/image/variant delete permissions.
- Promotions: type/status/date filters, scope selection, and read-only usage
  count.
- Orders: searchable/filterable workflow view; every model field and all item
  and event inlines are read-only. The only dashboard mutations are the named
  sequential order-status actions, including safe cancellation/restock, over
  `store.services.operations`. Payment fields and payment actions are not
  editable or exposed.
- Contact submissions and their events are view-only in the dashboard: no add,
  edit, delete, or workflow action is exposed.
- Order, contact, and audit rows cannot be added/deleted through admin. Catalog
  and Home content retain their existing safe merchandising controls.
- `configure_staff_roles` creates/reconciles Catalog Manager, Fulfillment Staff,
  Customer Support, and Store Manager groups. Product/image/variant deletion is
  limited to the two catalog-capable roles; orders and contacts receive no
  direct model-change permission, and no role receives payment or contact-
  workflow permissions.

## Settings behavior

- Strict boolean and non-negative integer parsing.
- Development-only secret fallback; production requires an explicit secret.
- Comma-separated hosts and trusted origins.
- PostgreSQL URL parsing with decoded credentials/name, driver options,
  connection max age, and health checks.
- SQLite development fallback.
- Django password validators enabled.
- Secure/same-site cookie, nosniff, referrer, frame, SSL, HSTS, and trusted-proxy
  controls exposed through environment settings.
- Console email default and explicit static/media roots.
- Configurable 65,536-byte checkout JSON ceiling.
- Configurable 16,384-byte contact body ceiling, contact rate/window limits,
  and an optional blank-by-default staff notification destination.
- Generated request IDs, allow-listed structured JSON logs, security headers,
  and a generic database-aware local health response.
- No static finder exposes `frontend/`, the database, templates, or source.

`.env.example` documents every current environment input and contains no real
secret.

## Commerce service and API behavior

`store/forms.py` validates the customer snapshot. `store/services/checkout.py`
owns strict Version 1 parsing, normalization, deterministic UUID ordering,
catalog/variant resolution, row locking, promotion eligibility/math,
idempotency fingerprints, immutable snapshots, and atomic writes. `store/views.py`
only validates the JSON transport, calls that layer, and serializes the stable
`ok/data` or `error` envelope.

The parser rejects bodies over the configured byte limit, duplicate JSON keys,
unknown fields, noncanonical IDs, noninteger/bool quantities, invalid customer
types, more than 50 submitted lines, and normalized quantities over 99.
Customer email is case-folded; phone input permits common punctuation but must
contain 7-15 digits.

Quote recalculates current database prices, stock, and promotion value without
writing. Create first checks the retry key, locks products and variants in UUID
order plus the selected promotion, rechecks idempotency after blocking,
validates all lines before writes, calculates with `Decimal`, creates the order
and item snapshots, decrements only the authoritative stock source, consumes a
promotion once, and commits together. Matching retries return HTTP 200 and the
stored order; a different fingerprint returns 409. New orders return 201.

Checkout and confirmation responses are `no-store`. The complete wire format,
promotion rules, statuses, and idempotency semantics are maintained in
`docs/orders/README.md`.

## Contact and operations services

`ContactForm` validates and normalizes the five authored fields plus a UUID
submission key and invisible honeypot. `store.services.contact` fingerprints
normalized semantics, makes UUID replay idempotent/conflicting reuse explicit,
uses HMAC-only cache throttle keys, persists/audits atomically, and schedules a
staff email only after commit. Email failure is audited and cannot roll back a
message. Invalid forms render safe errors; success/replay use PRG feedback.

`store.services.operations` continues to own the documented sequential order,
payment, and contact state graphs for domain safety and tests. The simplified
admin exposes only order-status transitions. Cancellation locks and validates
all historical inventory references,
restores the exact product/variant authority, marks the order, and creates
status/restock events in one transaction. Identical completed transitions are
no-ops; invalid state, missing rows, overflow, permission failure, or write
failure cannot partially mutate stock or lifecycle state.

## Known deferred work

- Deployment, backups, CI/CD, production providers, distributed edge controls,
  and production-readiness work are explicitly out of scope. Notification-off
  and retention-hold defaults remain appropriate for this learning project.
