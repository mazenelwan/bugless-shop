# Architecture

Last updated: 2026-09-16 (Phase 6 closeout and simplified dashboard)

## Repository layout

```text
bugless-shop-main/
|-- AGENTS.md
|-- docs/                         durable contracts and phase record
|-- frontend/                     immutable standalone frontend SOT
|-- accounts/                     custom identity app
|-- buglessfit/                   project settings and root URL composition
|-- store/                        catalog, commerce, contact, and public pages
|   |-- management/commands/
|   |-- migrations/
|   |-- static/store/             namespaced derived assets
|   |-- services/                 transactional commerce services
|   |-- tests/
|   |-- admin.py
|   |-- forms.py
|   |-- models.py
|   |-- selectors.py
|   |-- urls.py
|   `-- views.py
|-- templates/store/              SOT-shaped Django templates and partials
|-- .proofs/phase2/               retained visual comparison screenshots
|-- db.sqlite3                    local development database
|-- db.pre-custom-user.20260913.sqlite3
|-- manage.py
|-- requirements.txt
`-- .env.example
```

The SOT stays flat because its original HTML uses sibling-relative assets and
page links. Django never serves that directory through a static-file finder.

## Application ownership

- `accounts` owns login identity, registration, sessions,
  password management, profile data, and customer account pages.
- `store` owns categories, products, product images, variants, promotions,
  orders, order items, contact messages, public storefront routes, and staff
  administration.
- `buglessfit` owns environment settings and top-level URL composition.
- `templates/store` and `store/static/store` are editable derived UI files.
- `frontend` owns the visual/interaction reference and is not runtime data.
- `docs` records current behavior, accepted choices, deferred work, and proof.

No domain may accept browser-supplied product names, prices, discounts, totals,
availability, or stock as authority.

## Layering rules

- Models store durable state and enforce database/model invariants.
- Selectors own reusable read/query behavior. `store/selectors.py` currently
  owns public catalog visibility/order/search and related-product selection.
- Django forms or typed payload validators own input parsing, normalization, and
  field-safe errors. Account, checkout, and contact validators are implemented.
- Services own multi-model and transactional writes. The checkout service owns
  all catalog/promotion resolution, money calculation, locking, snapshots,
  inventory mutation, promotion consumption, and idempotent replay. Contact
  submission/notification and permissioned staff lifecycle/restock services
  own their corresponding multi-row behavior.
- Views are HTTP adapters: select data, call validators/services, choose
  response status, and render/serialize the result.
- Model `save()` methods may normalize local values such as email, promo code,
  slug, or blank legacy ID. They must not perform cross-domain side effects.

## Identity contracts

- `AUTH_USER_MODEL = "accounts.User"`.
- Email is the login field, normalized with case folding, and protected by both
  field uniqueness and a case-insensitive database constraint.
- There is no username field.
- Accounts are optional; `Order.customer` is nullable for guest checkout.
- Order contact/address fields remain snapshots even when an account owns the
  order.
- `Product.public_id` and `ProductVariant.public_id` are immutable UUIDs
  used by browser/API contracts.
- Product detail routes use readable unique slugs.
- `Product.legacy_id` exists only for importing and redirecting authored SOT
  identifiers such as `shirts-01`.

## Public request/read flow

1. A namespaced `store:` route reaches a thin public view.
2. The selector filters inactive categories/products and applies explicit
   merchandising order.
3. Django renders the corresponding SOT-shaped template.
4. A JSON script element supplies server-rendered display metadata to the
   progressive cart module.
5. Browser modules handle navigation, filters, galleries, and local cart state.
6. No display-only browser value is used as a committed commerce value.

## Commerce write boundary

The implemented Phase 4 order flow:

1. parse one documented payload shape;
2. resolve UUID product/variant identifiers;
3. lock all relevant inventory rows;
4. validate every line, customer field, promotion, quantity, and stock level;
5. calculate all money with `Decimal` on the server;
6. create the order and immutable item snapshots;
7. decrement only the authoritative inventory rows;
8. commit all changes together; and
9. return the private confirmation URL before the browser clears `bfCart`.

`POST /api/checkout/quote/` is a read-only advisory calculation and
`POST /api/checkout/` is the sole order creation adapter. Both call typed
validation and commerce services; views do not calculate money or mutate stock.
The exact envelopes and limits are in `docs/orders/README.md`.

## Staff operations boundary

The simplified Django admin keeps order, payment, contact, and audit fields
immutable. Contact messages are view-only. The only order mutations exposed in
admin are named business-status actions; they call permission-checking services,
and the same services reject unauthorized direct Python callers. Product CRUD
uses the current Product form plus image and variant inlines. Sequential domain
transition graphs remain documented in `docs/orders/README.md` and
`docs/contact/README.md`, even where a capability is no longer dashboard-
exposed.

Cancellation is the inverse inventory transaction for pre-shipment orders. It
locks the order/items, then product and variant rows deterministically, validates
every historical target and stock ceiling before writing, restores the exact
authority used by checkout once, records the marker/state/audit rows, and
commits together. It never changes historical item snapshots or credits
promotion usage.

## Inventory and availability

- Without active variants, `Product.stock` is authoritative.
- With one or more active variants, the sum of active variant stock is the
  aggregate available stock and product-level stock is ignored.
- A purchasable product must belong to an active category, be active, not have
  `sold_out` set, and have positive authoritative stock.
- A selected variant must be active, belong to the selected product, exactly
  match its options, and have sufficient stock.
- Checkout locks/decrements the selected variant when active variants exist and
  never decrements both product and variant stock.

## Money and promotions

- Currency is EGP.
- Cash on delivery is the only modeled initial payment method.
- Subtotal, discount, delivery fee, tax, and total are separate order fields.
- Delivery and tax default to zero until business rules are approved.
- Promotion codes are normalized uppercase and case-insensitively unique.
- Promotions may be fixed or percentage based and may have a minimum subtotal,
  maximum discount, active window, global/per-customer limits, and category or
  product scope.
- Promotions are inactive by default. SOT demo codes are created only with an
  explicit development seed option.

## Error and personal-data conventions

HTML forms and checkout JSON calls use normal Django CSRF protection. Account
and contact forms bind field-safe errors; Checkout maps structured server
errors to safe summaries and matching customer/promotion controls.

The final JSON convention for new APIs is:

```json
{
  "ok": false,
  "error": {
    "code": "stable_machine_code",
    "message": "Safe user-readable summary.",
    "fields": {
      "field_name": ["Safe validation message."]
    }
  }
}
```

Successful checkout APIs return `{"ok": true, "data": {...}}`. Quote returns
200, a new order returns 201, and an identical replay returns 200. Transport or
schema errors use 400/415; current-state and idempotency conflicts use 409.

Logs may contain route, status, timing, internal correlation/order identifier,
and exception type. They must not contain passwords, reset/confirmation tokens,
raw request bodies, full addresses, contact message bodies, or unnecessary
email/phone data.

## URL and authorization structure

- Root URLs mount `accounts:` at `/accounts/` and `store:` at `/`.
- Account routes implement registration, login, POST-only logout, profile,
  password change/reset, and owner-filtered order history.
- Public templates use `{% url %}`; no derived internal navigation relies on
  relative `.html` links.
- Legacy authored `.html` URLs return permanent redirects.
- Confirmation access requires both the order number and an unguessable UUID
  token. If an authenticated user presents a token for another customer's
  order, the response is 404.
- The token currently acts as the guest/account email-link bearer credential;
  it must never be logged or exposed in public lists.
- Store services retain distinct transition, cancel/restock, payment receipt,
  refund record, and contact-workflow permissions. The explicit
  `configure_staff_roles` command reconciles four least-privilege dashboard
  groups, provisioning only order transition/cancellation, read-only contacts,
  and catalog CRUD (including product/image/variant deletion) for the relevant
  roles.

## Settings and local security posture

- Boolean environment values are parsed strictly; invalid values fail startup.
- Non-negative integer settings fail with `ImproperlyConfigured` when invalid.
- A development-only secret fallback is allowed only with `DEBUG=True`.
- `DEBUG=False` requires `SECRET_KEY`.
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are comma-separated settings.
- `DATABASE_URL` accepts PostgreSQL schemes, percent-decodes credentials/name,
  forwards driver query options, and enables persistent health-checked
  connections.
- SQLite is the local fallback.
- Cookie security, SSL redirect, HSTS, and trusted proxy behavior remain
  explicit settings for security learning/testing; no deployment profile will
  be selected in this project.
- Console email is the local default. Selecting a real provider is out of scope.
- `CHECKOUT_MAX_BODY_BYTES` defaults to 65,536 and is parsed as a nonnegative
  integer. The service independently bounds line counts and quantities.
- `CONTACT_MAX_BODY_BYTES` defaults to 16,384; rate count/window are strict
  nonnegative integers. Staff contact notification is disabled unless
  `CONTACT_NOTIFICATION_EMAIL` is configured and always runs after commit.
- Media is served by Django only in debug. Production object/media storage is
  out of scope.

## Static and media isolation

- Derived CSS, JavaScript, and the About image live below
  `store/static/store/`.
- All six CSS files and the About image are byte-for-byte copies of their SOT
  counterparts. JavaScript is rewritten as small progressive modules because
  the original scripts contain conflicting data contracts.
- There is no `STATICFILES_DIRS` entry exposing `frontend/` or the repository
  root.
- `STATIC_ROOT = BASE_DIR / "staticfiles"` is generated collection output.
- `MEDIA_ROOT = BASE_DIR / "media"` is separate from SOT/static files.

## Migration and recovery policy

- `store/0001_initial.py` remains unchanged.
- Phase 1 added `accounts/0001_initial.py` and store migrations 0002-0004.
- Phase 4 added and applied `store/0005_order_request_fingerprint.py`; existing
  rows receive a blank legacy fingerprint and cannot accidentally match a new
  client retry request.
- Phase 5 added and applied `store/0006_phase5_operations.py`. It safely
  populates unique contact submission UUIDs/fingerprints for existing rows,
  adds the order restock marker, creates order/contact audit models and custom
  permissions, and backfills one submitted event per existing contact.
- Unique UUID fields used an add-nullable, populate-existing-rows,
  enforce-non-null sequence.
- The old SQLite file was moved, not deleted, to
  `db.pre-custom-user.20260913.sqlite3`.
- A clean `db.sqlite3` was migrated and reseeded successfully; migrations
  through 0006 are applied to the active database.
- Migration behavior and PostgreSQL configuration parsing are tested locally.
  Phase 6 also runs four deterministic multi-connection races against an
  isolated loopback-only PostgreSQL 18 cluster; this is learning evidence, not
  a deployment or release certification.

## Evidence artifacts

`.proofs/phase2/` retains 24 PNGs:

- six SOT desktop screenshots;
- six Django desktop screenshots;
- six SOT mobile screenshots; and
- six Django mobile screenshots.

Temporary browser profiles used for capture were verified as children of that
proof directory and removed after capture. The screenshots remain for review.
