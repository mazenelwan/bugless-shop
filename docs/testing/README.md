# Verification and Testing

Last updated: 2026-09-16 (Phase 6 and admin dashboard verified)

## Standard commands

Run from the repository root after implementation changes:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test -v 2
```

After static/settings changes:

```powershell
python manage.py collectstatic --noinput --dry-run
```

After changing a browser module:

```powershell
node --check store/static/store/js/cart.js
node --check store/static/store/js/checkout.js
node --check store/static/store/js/home.js
node --check store/static/store/js/product.js
node --check store/static/store/js/shop.js
node --check store/static/store/js/site.js
```

Fresh local catalog setup:

```powershell
python manage.py migrate
python manage.py seed_catalog
python manage.py configure_staff_roles
```

Development demo promotions are opt-in:

```powershell
python manage.py seed_catalog --with-demo-promotions
```

## Baseline

Before Phase 1, the repository had 3 tests:

- database-backed product detail;
- server price and stock decrement in the old successful checkout path; and
- contact-message persistence.

All three passed on 2026-09-13.

## Phase 1/2 automated result

The Phase 1/2 closing suite discovered 40 tests and applied every migration
available at that checkpoint to a fresh in-memory SQLite database. Coverage
included:

### Accounts and settings

- normalized email login identity;
- case-insensitive email conflict;
- superuser flag enforcement;
- strict environment booleans;
- PostgreSQL URL percent decoding/options/connection settings; and
- rejection of invalid non-negative integer settings.

### Catalog schema and seed

- immutable UUID public product identity and readable slugs;
- old-price constraint;
- variant-stock precedence and required options;
- one primary image per product;
- promotion percentage and case-insensitive code constraints;
- order identifier uniqueness and total validation;
- deterministic category/product order;
- seed idempotency; and
- explicit demo-promotion opt-in.

### Public integration

- all six authored public page templates and namespaced styles;
- named route rendering;
- database product data and UUID cart metadata;
- authored merchandising order;
- category/name search;
- inactive category/product suppression and 404 behavior;
- related product fallback;
- legacy `.html` redirects;
- private confirmation token matching; and
- authenticated cross-customer order privacy.

### Transitional write safety

- old happy-path server price/stock behavior;
- duplicate-line rejection without order/stock mutation;
- variant-product rejection without mutation;
- non-object JSON rejection; and
- non-object item rejection.

### Static integrity

- the recorded manifest covers and matches all 21 SOT files;
- each of six namespaced CSS derivatives matches its SOT SHA-256;
- the namespaced About image matches its SOT SHA-256; and
- unnamespaced SOT assets are absent from static discovery.

### Admin safeguards

- foundational models are registered, with product images/variants available
  through product inlines;
- custom-user creation renders email and no username input; and
- product/order identifiers, financial/contact snapshots, and order-item
  history are read-only where required.

## Phase 1/2 command evidence

| Date | Command/check | Result |
|---|---|---|
| 2026-09-13 | Existing database audit | Only 6 categories, 24 products, and 24 images; no users, orders/items, variants, contacts, or Home rows. |
| 2026-09-13 | Fresh `migrate` after custom-user rebuild | Passed through `accounts.0001` and `store.0001-0004`. |
| 2026-09-13 | `seed_catalog` | 6 categories, 24 products, 24 images. |
| 2026-09-14 | SOT SHA-256 before/after manifest comparison | All 21 files unchanged; manifest retained in `docs/frontend/sot-sha256.txt`. |
| 2026-09-14 | Six Node `--check` commands | All browser modules passed syntax parsing. |
| 2026-09-14 | `python manage.py check` | Passed with no issues. |
| 2026-09-14 | `python manage.py makemigrations --check` | Passed; no model changes detected. |
| 2026-09-14 | `python manage.py test -v 2` | Passed; 40 tests. |
| 2026-09-14 | `collectstatic --noinput --dry-run` | Passed; 140 Django admin and namespaced store files resolved. |
| 2026-09-14 | Idempotent active-database seed rerun | Still 6 categories, 24 products, 24 images; no default promotions. |
| 2026-09-14 | `showmigrations accounts store` | All accounts/store migrations applied. |

## Phase 3 automated result

The targeted account suite discovers 13 tests and applies every migration to a
fresh in-memory SQLite database. It covers normalized registration/login,
case-insensitive conflicts, external redirect rejection, POST-only logout,
protected profile edits, password-change session continuity, enumeration-safe
reset responses, single-use reset tokens, explicit order ownership, throttling,
HMAC cache-key privacy, and CSRF rejection.

| Date | Command/check | Result |
|---|---|---|
| 2026-09-14 | `python manage.py test accounts.tests.test_views --verbosity 2` | Passed; 13 tests. |
| 2026-09-14 | `python manage.py check` | Passed with no issues after account implementation. |
| 2026-09-14 | `python manage.py makemigrations --check` | Passed; Phase 3 required no schema changes. |
| 2026-09-14 | `collectstatic --noinput --dry-run` | Passed; 141 admin/store/account assets resolved. |

## Phase 4 automated result

The final project suite discovers 74 tests and applies migrations through
`store.0005` to a fresh in-memory SQLite database. Twenty-one focused Phase 4
tests plus updated endpoint/privacy/admin coverage verify:

- strict JSON media type, body-size, duplicate-key, unknown-field, UUID,
  customer-type, email/phone, line-count, quantity, and CSRF rejection;
- stale/inactive product and exact variant membership/stock rejection;
- duplicate line coalescing and correct product-versus-variant decrement;
- database-owned price, immutable item/contact/money snapshots, zero delivery
  and tax, and authenticated owner association;
- fixed/percentage promotion scope, minimum, cap, window, global/customer
  limit, half-up rounding, and quote non-mutation;
- matching retry replay with no second stock/promo mutation and changed-key
  semantics returning a conflict;
- forced item-write failure rolling back order, item, inventory, and promotion
  state;
- named Checkout API URLs, escaped signed-in identity prefill, `no-store`
  caching, private token confirmation, and owner-filtered history; and
- rejection of browser price fields instead of accepting stale/tampered money.

| Date | Command/check | Result |
|---|---|---|
| 2026-09-14 | Focused commerce/API/UI integration suite | Passed; 31 tests. |
| 2026-09-14 | `python manage.py test --verbosity 2` | Passed; 74 tests in 143.848 seconds. |
| 2026-09-14 | `python manage.py migrate` | Applied `store.0005_order_request_fingerprint` to active SQLite. |
| 2026-09-14 | `python manage.py check` | Passed with no issues after final implementation. |
| 2026-09-14 | `python manage.py makemigrations --check` | Passed; no model/migration drift. |
| 2026-09-14 | Six Node `--check` commands | All browser modules passed after Checkout wiring. |
| 2026-09-14 | `collectstatic --noinput --dry-run --verbosity 0` | Passed; namespaced assets resolve. |
| 2026-09-14 | Full-suite SOT/static integrity tests | All 21 SOT hashes and exact CSS/image derivatives match. |
| 2026-09-14 | Active database count audit | 6 categories, 24 products/images; zero variants, promotions, orders/items, contacts, and users. |

## Phase 5 automated result

The closing suite discovers 99 tests and applies migrations through
`store.0006` to a fresh in-memory SQLite database. Twenty-five new/expanded
tests cover:

- contact UUID rendering, normalization, required/format/length validation,
  escaped bound values, PRG success, CSRF/method/body limits, honeypot rejection,
  per-peer throttling, and HMAC-only cache keys;
- identical contact replay without a second row/event/notification and changed
  reuse conflict without mutation;
- notification-after-commit success audit and provider-failure audit without
  rolling back the persisted contact;
- distinct service/admin permissions, sequential/idempotent business and
  payment transitions, contact workflow transitions, and attributable events;
- exact product-versus-variant cancellation restock, paid-payment rejection,
  missing-target and forced-audit rollback, one-time retry behavior, and
  retained promotion usage;
- immutable admin snapshots/events, disabled admin add/delete paths, action
  visibility by permission, and exact idempotent staff-group provisioning.

| Date | Command/check | Result |
|---|---|---|
| 2026-09-14 | Phase 3 recap: `python manage.py test accounts.tests.test_views --verbosity 1` | Passed; 13 tests in 45.028s. |
| 2026-09-14 | Phase 4 recap: focused checkout/safety suite | Passed; 25 tests in 1.128s. |
| 2026-09-14 | `python manage.py migrate` | Applied `store.0006_phase5_operations` to active SQLite. |
| 2026-09-14 | `python manage.py configure_staff_roles` | Created four groups with 18/8/7/30 permissions. |
| 2026-09-14 | `python manage.py test --verbosity 1` | Passed; 99 tests in 96.401s. |
| 2026-09-14 | `python manage.py check` | Passed with no issues. |
| 2026-09-14 | `python manage.py makemigrations --check` | Passed; no model/migration drift. |
| 2026-09-14 | `collectstatic --noinput --dry-run --verbosity 0` | Passed; all namespaced/admin assets resolve. |
| 2026-09-14 | Six Node `--check` commands | Passed; all browser modules parse. |
| 2026-09-14 | Independent SOT manifest check | Passed; all 21 standalone source files are byte-identical. |
| 2026-09-14 | Active data audit | 6/24/24 catalog, four staff groups, and zero variants/promos/orders/items/contacts/events/users. |

## Phase 6 and simplified-dashboard automated result

The current SQLite suite discovers 118 tests. It passes 114 and skips only the
four PostgreSQL-gated concurrency tests. Thirteen Phase 6 security/monitoring
tests cover response headers, generated request correlation, health success and
generic database failure, unsafe methods/content types, CSRF, cookie flags,
host rejection, sensitive-path isolation, and allow-listed PII-safe logging.

The isolated PostgreSQL 18 harness applies all migrations and separately runs
four real multi-connection races: matching idempotent checkout, last-stock
competition, a one-use promotion, and duplicate cancellation/restock. The
Playwright harness runs five critical journeys in both 1440x1200 and 390x844
Chromium projects. Those ten runs cover guest/account commerce, private
confirmation/history, contact validation/replay, status-only order admin, and
read-only contact admin.

The dashboard-focused tests additionally prove product create/update/delete
with a current ProductImage inline, immutable order/contact detail pages,
status-only order actions, absence of payment/contact workflow actions, and the
exact reconciled staff-role permissions.

| Date | Command/check | Result |
|---|---|---|
| 2026-09-16 | `python manage.py test --verbosity 1` | Passed; 118 discovered, 4 PostgreSQL-only skips, in 127.147s. |
| 2026-09-16 | `scripts/run_postgres_concurrency.ps1` | Passed all 4 real PostgreSQL races in 7.540s; no listener remained on port 55432. |
| 2026-09-16 | `npm run test:e2e` | Passed all 10 desktop/mobile Chromium runs. |
| 2026-09-16 | `python manage.py check` and `makemigrations --check` | Passed; no issues or model drift. |
| 2026-09-16 | `collectstatic --noinput --dry-run --verbosity 0` and six Node syntax checks | Passed. |
| 2026-09-16 | Independent SOT manifest check | All 21 standalone frontend files remain byte-identical. |
| 2026-09-16 | `python manage.py configure_staff_roles` | Reconciled Catalog/Fulfillment/Support/Manager to 21/6/5/28 permissions. |

## Visual verification

Twenty-four PNGs are retained under `.proofs/phase2/`:

| Page | Standalone SOT | Django | Viewports |
|---|---|---|---|
| Home | `sot-*/home.png` | `django-*/home.png` | 1440x1200, 390x844 |
| Shop | `sot-*/shop.png` | `django-*/shop.png` | 1440x1200, 390x844 |
| Product | `sot-*/product.png` | `django-*/product.png` | 1440x1200, 390x844 |
| Checkout | `sot-*/checkout.png` | `django-*/checkout.png` | 1440x1200, 390x844 |
| Contact | `sot-*/contact.png` | `django-*/contact.png` | 1440x1200, 390x844 |
| About | `sot-*/about.png` | `django-*/about.png` | 1440x1200, 390x844 |

Manual pair review confirmed equivalent page structure, classes, layout,
spacing, typography, colors, imagery, and authored mobile overflow behavior.
The expected content/behavior differences are documented in
`docs/frontend/README.md`.

The local Django browser run returned 200 for every page and required static
asset. The only browser-log 404 was the optional `/favicon.ico`, for which the
SOT supplies no asset.

## Corrections caught during implementation

- Django warned that adding a callable default directly to an existing unique
  UUID field could duplicate values during migration. The initial generated
  approach was not accepted; store migrations 0002-0004 use the safe nullable,
  per-row population, then required/unique sequence.
- The first dynamic Home draft assigned the second category row classes as
  `option-1`, `option-2`, `option-3`; SOT inspection showed the authored order
  is `option-2`, `option-3`, `option-1`. The template was corrected before the
  retained screenshots and final tests.
- The transitional checkout endpoint could raise an attribute error for a JSON
  array or non-object item. Explicit type guards and rejection-without-mutation
  tests were added in Phase 2; Phase 4 then removed that contract completely.
- The first manifest assertion treated uppercase and lowercase hexadecimal
  digests as different. The test now normalizes digest case; an independent
  PowerShell verification also confirms 21 of 21 exact byte hashes.
- Django forms can coerce non-string values. Checkout now verifies every JSON
  customer value is a string before passing it to the form; a rejection test
  protects that strict contract.
- Idempotency is checked both before work and after product/promotion lock
  acquisition. This was kept deliberately because a concurrent matching
  request may finish while the second transaction is blocked.
- The service locks all variants for selected products, including inactive
  ones, before deciding whether product or variant stock is authoritative.

## Residual verification limits

- There is no dedicated JavaScript unit harness; critical runtime behavior is
  covered by Chromium E2E and server integration tests.
- Screenshot capture is retained evidence, not an automated pixel-diff gate.
- Playwright intentionally uses Chromium only. It stubs remote images, fonts,
  maps, and other third-party requests; vendor behavior and offline fallbacks
  are not certified.
- PostgreSQL evidence is four deterministic correctness races, not a
  distributed load/performance test. In the managed Windows shell `pg_ctl`
  cannot signal the child server, so the script uses its bounded force-stop
  fallback and verifies that the isolated port is closed.
- Production variants/promotions were not invented; isolated tests prove their
  rules while the active development database intentionally contains none.
- Contact notification remains disabled; production providers, distributed
  edge throttling, and a legal/business retention-request process are outside
  this learning project's scope.
