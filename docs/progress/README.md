# Implementation Progress

Last updated: 2026-09-16 (Phase 6 and simplified dashboard complete)

## Delivery protocol

Work is organized into dependency-ordered phases. Every phase is documented
here before its application code begins.

Status markers:

- `[x]` complete and verified
- `[~]` active
- `[ ]` planned
- `[!]` requires a user/product/infrastructure decision

Before activation, a phase must document:

1. objective and boundaries;
2. accepted decisions and unresolved gates;
3. routes, data contracts, models/migrations, and UI surfaces it may change;
4. dependency-ordered subtasks;
5. happy-path and rejection-path acceptance criteria;
6. verification commands; and
7. documentation that must change.

A phase is complete only when implementation, migrations, proportionate tests,
required visual checks, and all affected documentation agree. Discovered work
belongs in its owning phase and is not silently pulled forward.

## Current position

`[x] Phase 6 - Security, concurrency, browser E2E, and monitoring`

Phases 0 through 6 are complete within the learning/local-development scope.
The follow-up simplified Django admin dashboard is also complete: contacts are
view-only, orders are immutable with service-backed status actions only, and
products/images/variants have role-scoped CRUD. Deployment and production-
readiness work remain explicitly outside the roadmap.

## Roadmap

| Phase | Category | Intended outcome | Status |
|---|---|---|---|
| 0 | Discovery and governance | Preserve the SOT, inventory the repository, and establish durable phase/document rules. | Complete |
| 1 | Architecture, identity, and database | Establish app boundaries, settings, identifiers, schema, migrations, admin, seed, and recovery path. | Complete |
| 2 | Public frontend and catalog integration | Render all authored public pages through Django with database catalog data and one cart contract. | Complete |
| 3 | Authentication and customer accounts | Add secure identity flows and customer-owned data while keeping guest checkout. | Complete |
| 4 | Cart, checkout, promotions, inventory, and orders | Deliver one validated, atomic, idempotent server-authoritative commerce flow. | Complete |
| 5 | Contact, admin, and business operations | Complete validated contact and safe staff/order operations. | Complete |
| 6 | Security, concurrency, browser E2E, and monitoring | Deepen application security, prove concurrent transaction behavior, automate critical browser journeys, and add privacy-safe local observability. | Complete |

## Phase 0 - Discovery and governance

### Objective

Protect the completed standalone frontend and establish enough repository
memory and evidence to implement safely.

### Completed work

- [x] Read every file under `docs/` and inventoried frontend, templates,
  settings, models, migrations, admin, seed, tests, and local database.
- [x] Established all 21 `frontend/` files as immutable SOT.
- [x] Recorded SHA-256 integrity and the original 3-test health baseline.
- [x] Recorded local counts and confirmed no user/order/contact/variant data.
- [x] Established this phase-gated roadmap and domain documentation.
- [x] Recorded that this directory is not a Git worktree.

### Exit evidence

SOT and local data were understood before Phase 1 schema work. The original
`store/0001_initial.py` was already applied and was preserved.

## Phase 1 - Architecture, identity, and database foundation

### Objective and boundary

Create a migration-backed foundation that supports accounts, catalog,
promotions, and later atomic checkout without modifying public SOT pages.
Visible authentication and production checkout were explicitly out of scope.

### Accepted decisions

- Optional accounts plus guest checkout.
- Custom email-based user in a dedicated `accounts` app.
- Recoverable local SQLite backup and clean rebuild because audited rows were
  reproducible catalog seed only.
- EGP and cash on delivery.
- Explicit zero-default delivery/tax fields.
- Database promotions; SOT promo codes development-only.
- Current 24 products are development seed.
- UUID public product/variant identity, readable slug routes, legacy import IDs.
- Variant stock replaces product stock when active variants exist.
- Ratings are display metadata, not review aggregates.

See D-007 through D-016 in `docs/decisions/README.md`.

### Completed subtasks

#### 1A - Decisions and data audit

- [x] Confirmed authentication is part of the target.
- [x] Resolved guest/account checkout policy.
- [x] Resolved identity and local-data preservation policy.
- [x] Defaulted schema-affecting money/promotion/privacy rules explicitly.
- [x] Classified the SOT catalog as development seed.

#### 1B - Boundaries and settings

- [x] Added `accounts` ownership and kept catalog/commerce in `store`.
- [x] Defined model/selector/validator/service/view boundaries.
- [x] Namespaced `store:` and reserved `accounts:` URLs.
- [x] Added strict environment parsing for booleans/non-negative integers,
  production secret enforcement, hosts/origins, PostgreSQL URL decoding/options,
  email, static/media, cookies, SSL, HSTS, and proxy handling.
- [x] Enabled Django password validators.
- [x] Defined future HTML/JSON error and personal-data logging conventions.
- [x] Updated `.env.example` without real credentials.

#### 1C - Domain schema

- [x] Added `accounts.User` with email login and case-insensitive uniqueness.
- [x] Added nullable order ownership for guest/account orders.
- [x] Added explicit category/product merchandising order.
- [x] Added immutable UUID public IDs and retained legacy IDs.
- [x] Added image-primary/order constraints.
- [x] Defined variant identity/options/order and stock authority.
- [x] Added scoped, windowed, limited fixed/percentage promotions.
- [x] Expanded order money, currency, payment state, idempotency identifier,
  private confirmation token, promotion snapshot, and customer snapshot.
- [x] Expanded immutable order-item product/variant/SKU/options/money snapshots.
- [x] Added database constraints and workflow/read indexes.

#### 1D - Migrations, recovery, seed, and admin

- [x] Added `accounts/0001_initial.py`.
- [x] Preserved `store/0001_initial.py`; added store migrations 0002-0004.
- [x] Used add-nullable/populate/enforce migrations for unique UUIDs.
- [x] Moved the old database to
  `db.pre-custom-user.20260913.sqlite3` rather than deleting it.
- [x] Migrated a clean `db.sqlite3` and reseeded successfully.
- [x] Made seed parsing atomic, deterministic, idempotent, ordered, and strict.
- [x] Made demo promotions explicit with `--with-demo-promotions`.
- [x] Added safe admin list/search/filter/order/read-only behavior.
- [x] Reviewed schema operations/constraints for Django SQLite/PostgreSQL
  portability and tested PostgreSQL URL configuration. Actual PostgreSQL
  execution was deferred to Phase 6 and is now covered by its race suite.

#### 1E - Tests and documentation

- [x] Added account, environment, identifier, constraint, inventory,
  promotion, order, migration-freshness, and seed tests.
- [x] Ran standard checks, fresh migrations, active-database seed, and
  idempotency verification.
- [x] Updated architecture, backend, catalog, orders, testing, decisions, root
  memory, and this phase ledger.

### Acceptance evidence

- Fresh test databases apply all account/store migrations.
- Active local database has 6 categories, 24 products, 24 images, no duplicate
  rows, and no default demo promotions.
- Case-insensitive identity/promotion conflicts and invalid catalog/order rules
  are rejected.
- Backup location and upgrade strategy are documented.
- Standard checks pass in the final 40-test suite.

### Deferred by design

Account HTTP screens are Phase 3; checkout service/idempotency use is Phase 4;
contact validation/operational workflows are Phase 5; real PostgreSQL
concurrency/security/E2E/monitoring are Phase 6. Deployment is out of scope.

## Phase 2 - Public frontend and catalog integration

### Objective and boundary

Render Home, Shop, Product, Checkout shell, Contact shell, and About through
Django while preserving the SOT presentation and making catalog display/search
database-authoritative. Production order/contact submission was out of scope.

### Activated decisions

- Admin controls category/product order.
- SOT ratings remain optional display metadata.
- Remote image URLs remain compatible through visual parity.
- Existing six pages retain their own authored DOM/style; shared partials are
  used only where structure is common.
- New account-only pages will inherit the visual language in Phase 3 because no
  account SOT exists.
- Canonical `bfCart` Version 1 uses UUID identity only.
- Checkout cannot fake or submit an order until Phase 4.
- Confirmation URLs require a private token.

See D-017 through D-022 in `docs/decisions/README.md`.

### Completed subtasks

#### 2A - Static/template preservation

- [x] Captured a pre-integration hash manifest for all 21 SOT files.
- [x] Copied six exact CSS derivatives and the exact About image into
  `store/static/store/`.
- [x] Kept `frontend/` out of Django static discovery.
- [x] Added minimal head, public-header, and footer partials.
- [x] Removed the obsolete pre-integration base template.
- [x] Converted all six authored pages with `{% static %}` and named
  `{% url %}` links while preserving classes/IDs/layout.

#### 2B - Routes and catalog reads

- [x] Added Home, Shop, search, Product, Checkout, Contact, About, private
  confirmation, and legacy compatibility routes.
- [x] Added reusable public selectors for visibility/order/search/related items.
- [x] Rendered categories/products/prices/images/ratings/sold-out state/gallery,
  product-specific options, and related products from database data.
- [x] Added same-category related products with deterministic fallback.
- [x] Added server search across product/category/description/SKU with live
  client enhancement.

#### 2C - Shared browser behavior

- [x] Added one accessible mobile-menu module.
- [x] Defined `bfCart` Version 1 with product UUID, nullable variant UUID, and
  bounded quantity only.
- [x] Implemented deterministic migration for the two incompatible legacy cart
  shapes, dropping ambiguous/malformed data.
- [x] Added cross-page cart badge/sidebar/quantity/remove/clear/Buy Now behavior.
- [x] Used server-rendered JSON only for display metadata.
- [x] Disabled client promotion authority, fake success, submission, and cart
  clearing on Checkout until Phase 4.

#### 2D - Safety, verification, and documentation

- [x] Added route, template/static, visibility, order, search, inactive/missing,
  legacy redirect, confirmation privacy, static-integrity, and transitional
  endpoint rejection tests.
- [x] Passed Node syntax parsing for all six browser modules.
- [x] Passed static collection dry run with only admin/namespaced assets.
- [x] Compared every SOT/Django page at 1440x1200 and 390x844.
- [x] Retained 24 screenshots in `.proofs/phase2/`.
- [x] Rechecked all 21 SOT hashes; no file changed.
- [x] Documented intentional nonvisual/content differences and deferred work in
  every affected domain document.

### Acceptance evidence

- Every authored public page is Django-rendered.
- All internal links are named routes and local assets are namespaced static
  references.
- Active database catalog records, explicit ordering, search, variants, and
  related products drive public output.
- SOT assets are isolated and byte-for-byte intact.
- Desktop/mobile visual pairs preserve authored presentation.
- Public Checkout never creates a placeholder/insecure order.
- Standard checks pass in the final 40-test suite.

### Intentional limitations

- Contact POST validation is Phase 5.
- Checkout submission, promotion application, variant decrement, request
  idempotency, and authoritative final totals are Phase 4.
- Search/catalog pages are not paginated.
- Remote dependencies remain until production hardening.
- Browser screenshots are manual evidence, not automated pixel-diff CI.

## Phase 3 - Authentication and customer accounts

### Objective and boundary

Implement secure customer identity flows on `accounts.User` while preserving
optional guest checkout and without redesigning the six existing public pages.
Order-history integration may require Phase 4 data but route/authorization
contracts can be prepared.

### Activation decisions

- [x] Email/password registration is immediately usable; mandatory verification
  is deferred.
- [x] Saved addresses, marketing consent, account deletion/retention, and social
  login are deferred rather than modeled speculatively.
- [x] Password reset uses Django tokens and console email locally; production
  provider delivery is intentionally outside this learning project's scope.
- [x] Cache-backed HMAC-keyed throttles protect login, registration, and reset;
  shared cache/edge infrastructure is outside scope, while Phase 6 may deepen
  local security and failure-behavior tests.
- [x] Account order pages filter only by explicit `Order.customer` ownership;
  guest orders are not claimed by matching email.

### Frozen implementation contract

- Routes, access rules, HTTP methods, form fields, safe redirect behavior,
  session handling, rate limits, templates, and ownership rules are specified
  in `docs/accounts/README.md`.
- Registration requires email/password, accepts optional first/last name, signs
  in the user, and redirects only to a safe local target or profile.
- Profile permits normalized unique email and optional name edits.
- Logout is POST-only.
- Password change/reset use Django's built-in forms, session hash, token
  generator, and enumeration-safe reset behavior.
- No existing public navigation structure is redesigned for an account link.
- Account order list/detail are read-only and owner-filtered.

### Completed subtasks

- [x] Document exact account routes, form fields, redirects, and branded visual
  treatment before code.
- [x] Add registration, login, POST logout, password change, and password reset
  using Django authentication primitives.
- [x] Normalize email and expose safe field/non-field errors.
- [x] Validate `next` redirects and rotate sessions correctly.
- [x] Use the approved existing email/first/last profile fields; no speculative
  address migration was added.
- [x] Protect private account pages and add account-scoped order placeholders or
  integration as appropriate.
- [x] Add rate limits/abuse controls for login/register/reset.
- [x] Test duplicates, invalid credentials, safe redirects, sessions/logout,
  reset token behavior, authorization, and guest/account policy.
- [x] Update accounts, architecture, frontend, orders, testing, decisions, and
  this ledger.

### Acceptance evidence

- Thirteen account HTTP tests pass on a fresh migrated database.
- Authentication uses Django password/session/token machinery; reset remains
  enumeration-safe and tokens are single-use.
- Unsafe redirects, CSRF failures, duplicates, rate-limit excess, anonymous
  private access, and cross-owner order access are rejected.
- Static collection resolves the namespaced account stylesheet; no public SOT
  file or public navigation structure changed.
- `check` and `makemigrations --check` pass with no model drift.

### Exit criteria

All approved identity flows work end-to-end, security/authorization rejection
paths pass, account data remains private, and guest storefront use still works.

## Phase 4 - Cart, checkout, promotions, inventory, and orders

### Objective and boundary

Replace the disabled Checkout submission and transitional endpoint with one
UUID-based, validated, atomic, idempotent, server-authoritative order flow.

### Activation decisions

- [x] Use name/email/phone/address, with optional city/notes; delivery remains
  zero until delivery-zone rules are approved.
- [x] Tax remains explicitly zero until jurisdiction rules are approved.
- [x] Implement variant-safe behavior generically; production inventory/catalog
  approval is separate from service correctness.
- [x] Implement database promotions without activating production codes.
- [x] Bound input at 64 KiB, 50 submitted lines, 99 units per normalized line,
  and the database money ceiling.
- [x] Do not reserve/expire stock before commit; tracking is deferred.
- [x] Keep cash on delivery; online payment is deferred.

### Completed subtasks

- [x] Freeze request/success/error/idempotency contracts in docs before code.
- [x] Add typed customer/cart/promotion validation using public UUIDs.
- [x] Resolve and lock all rows in deterministic order.
- [x] Validate all lines/options/stock before mutation.
- [x] Calculate subtotal/discount/delivery/tax/total with `Decimal`.
- [x] Create order/items and decrement the correct inventory atomically.
- [x] Bind request idempotency to `Order.idempotency_key` and return the same
  result for retry.
- [x] Apply/lock/increment valid promotion usage.
- [x] Wire Checkout and clear `bfCart` only after confirmed success.
- [x] Add account ownership/history integration and private confirmations.
- [x] Test malformed/stale/tampered carts, variants, promos, rounding,
  rollback, retry, total authority, and privacy. Real PostgreSQL race execution
  was deferred to and is now covered by Phase 6.
- [x] Update every affected domain document and this ledger.

### Acceptance evidence

- Added and applied store migration 0005 for the semantic request fingerprint;
  migration freshness passes.
- Strict quote/create APIs accept only Version 1 public UUID lines and return
  the documented stable envelope and statuses.
- All catalog, variant, promotion, price, quantity, customer, and retry checks
  complete before writes; one atomic block owns order/item/stock/usage changes.
- Identical retries replay with HTTP 200; changed semantics conflict without
  mutation; a forced mid-write exception proves complete rollback.
- Checkout uses server quote/create, CSRF, cryptographic retry keys, safe field
  feedback, authenticated identity prefill, and success-only clearing.
- Confirmation remains private; signed-in orders appear only for their owner.
- The full fresh-database suite passes 74 tests. Django checks, migration drift,
  six Node syntax checks, static collection, and SOT integrity all pass.
- Active development data remains unchanged at 6 categories, 24 products, 24
  images, and zero variants/promotions/orders/items/contacts/users.

### Exit criteria

All commerce paths use Version 1 IDs, the server owns every calculation,
rollback leaves no partial data, retry cannot duplicate an order, inventory is
correct, and confirmation/history access is private.

## Phase 5 - Contact, admin, and business operations

### Objective and boundary

Complete production-safe visitor contact and staff workflows for live catalog,
promotion, order, and inventory operations.

### Activation decisions

- [x] Use a hidden honeypot plus configurable HMAC-keyed cache throttles; a
  UUID submitted with the form provides duplicate-write idempotency.
- [x] Keep notifications provider-neutral through Django email, disabled until
  a staff destination is configured, post-commit, and failure-isolated. Do not
  send visitor acknowledgements yet.
- [x] Use least-privilege Catalog Manager, Fulfillment Staff, Customer Support,
  and Store Manager groups backed by separate operation permissions.
- [x] Permit only the sequential order and payment transitions frozen in
  D-037; direct admin editing is not an operational path.
- [x] Permit cancellation only before shipment, require paid/pending payment to
  be resolved first, atomically restock the original authority once, retain
  promotion usage, and audit every change.
- [x] Enforce a retention hold: no automatic PII deletion/anonymization/export,
  permission-scoped access, no admin deletion, and non-PII audit payloads until
  a business/legal schedule and verified-request procedure are approved.

### Frozen implementation contract

- Contact remains `GET/POST /contact/`; invalid forms bind safe errors in the
  authored layout and successful/new-or-replayed submissions redirect back
  with success feedback.
- Contact bodies are capped at 16 KiB; name/email/message are required, visible
  values are normalized/bounded, UUID form keys are unique, and notifications
  are scheduled only for newly committed messages.
- `Order.inventory_restocked_at`, immutable `OrderEvent`, contact submission
  UUIDs, and immutable `ContactMessageEvent` are migration-backed.
- Order/contact status and payment fields become read-only in admin. Named
  actions call permission-checking transactional services; order/contact/audit
  history cannot be added, changed, or deleted through admin.
- `configure_staff_roles` is the explicit idempotent group provisioning step.

### Completed subtasks

- [x] Replace raw contact creation with a Django form, bound errors, success
  feedback, PRG, duplicate handling, and abuse controls.
- [x] Add approved contact notifications after reliable persistence.
- [x] Add order transition service and permissions.
- [x] Add atomic idempotent cancellation/restock where approved.
- [x] Harden admin inlines/actions/read-only snapshots and add auditability.
- [x] Apply retention/export/deletion rules.
- [x] Test contact rejection/CSRF/duplicates/spam, admin permissions,
  transitions, restock, notification failure, and audit records.
- [x] Update all affected documentation and this ledger.

### Acceptance evidence

- Added/applied `store.0006_phase5_operations`: safely populated contact UUIDs
  and fingerprints, added a restock marker, custom permissions, immutable
  order/contact events, and backfilled submitted events for existing contacts.
- Contact validates/bounds/normalizes every authored field, rejects CSRF,
  oversized bodies, honeypot fills, and rate excess, safely binds errors, uses
  PRG success, and distinguishes identical replay from changed-key conflict.
- New contact persistence and submitted audit are atomic. Optional staff email
  runs only after commit; success/failure is audited and provider failure leaves
  the message intact.
- Order and payment transition graphs reject skipped/terminal changes. Atomic
  cancellation restores only the original product or variant once; paid or
  pending payments, missing targets, stock overflow, and audit failure reject
  or roll back without partial mutation. Promotion usage remains consumed.
- Order/contact snapshots, lifecycle fields, and audit inlines are read-only;
  admin add/delete paths are disabled and named actions are permission-gated.
- `configure_staff_roles` was run on the active database, provisioning four
  groups with 18/8/7/30 exact permissions; its idempotency is tested.
- The fresh-database project suite passes 99 tests in 96.401 seconds. Final
  checks, migration freshness, static dry-run, six Node parses, migration
  application, and all 21 SOT hashes pass.
- Active development state is still 6 categories, 24 products/images, zero
  variants/promotions/orders/items/contacts/events/users, plus four staff
  groups.

### Exit criteria

Contact is validated and abuse-aware; staff can operate the store without
changing immutable history or corrupting stock; policies are enforced and
tested.

## Phase 6 - Security, concurrency, browser E2E, and monitoring

### Objective and boundary

Use the completed store as a learning environment to deepen application
security, exercise its transaction/idempotency contracts under real concurrent
database access, make critical browser flows repeatable, and expose failures
through privacy-safe local monitoring.

Hosting, domains, production service providers, deployment configuration,
CI/CD, backup/restore systems, launch approval, uptime engineering, production
performance budgets, and production-readiness certification are outside this
phase and outside the project roadmap.

### Activation decisions

- [x] Keep Phase 6 learning/local-development focused; do not add deployment or
  backup work and do not claim production readiness.
- [x] Use the installed PostgreSQL 18 binaries to run an isolated,
  loopback-only learning/test cluster. Do not alter or depend on the existing
  Windows PostgreSQL service and do not introduce Docker.
- [x] Use Playwright with Chromium at the existing 1440x1200 and 390x844 proof
  viewports; browser binaries and Node packages may be installed locally.
- [x] Add structured privacy-safe local logs, request correlation, explicit
  security/operation events, and a local health diagnostic. Do not add an
  external monitoring/SaaS dependency.

### Completed subtasks

- [x] Write a repository-specific threat model and test authorization/IDOR,
  CSRF/session behavior, unsafe methods/content types, input/resource limits,
  static/source isolation, secret/token handling, rate-limit failure behavior,
  security headers, and PII-safe errors/logging.
- [x] Run migrations, constraints, checkout idempotency, stock/promotion races,
  and cancellation/transition races against real local PostgreSQL with
  deterministic multi-connection tests.
- [x] Add a repeatable browser E2E harness for public catalog/cart/product,
  guest and account checkout/confirmation/history, account security flows,
  contact validation/replay, and permissioned admin operations.
- [x] Exercise the critical E2E flows at the existing 1440x1200 and 390x844
  viewports while preserving SOT behavior; use screenshots/traces only as
  deterministic debugging evidence, not a redesign mechanism.
- [x] Add the approved local monitoring layer and tests proving useful events,
  failure visibility, health diagnostics, and redaction of passwords, tokens,
  message bodies, addresses, email, and phone where not explicitly necessary.
- [x] Keep unit/integration/E2E/concurrency commands reproducible from the
  repository root and update affected contracts, evidence, and this ledger.

### Exit criteria

The threat-driven security suite and existing tests pass; real PostgreSQL
evidence covers the important concurrent write invariants; critical desktop
and mobile browser journeys run repeatably; local monitoring makes failures
useful without exposing protected data; and the documentation records both the
evidence and unproved limits. Completion does not imply deployability.

### Exit evidence

- The current SQLite suite discovers 118 tests and passes with only the four
  intentionally PostgreSQL-gated tests skipped.
- All four multi-connection PostgreSQL 18 races pass against the isolated local
  cluster: matching retry, last stock, one-use promotion, and duplicate cancel.
- Five Playwright scenarios pass in both desktop and mobile Chromium projects,
  for ten browser runs total.
- Security headers, safe structured logs, correlation IDs, the database health
  endpoint, source isolation, and privacy redaction are implemented and tested.
- Django checks/migration freshness, static dry-run, six Node parses, and all 21
  SOT hashes pass. Residual learning-only limits are recorded in security and
  testing documentation.

## Follow-up - Simplified Django admin dashboard

### Objective and completed work

- [x] Reuse and brand Django admin as the Bugless Fit dashboard.
- [x] Make ContactMessage and its event history strictly view-only in admin.
- [x] Keep every order/item/event field immutable and expose only named,
  sequential, service-backed business-status actions; remove payment actions.
- [x] Preserve safe cancellation/restock/audit behavior for cancelled orders.
- [x] Provide Product CRUD for current product fields plus image/variant
  inlines, including role-scoped deletion.
- [x] Reconcile staff groups to 21/6/5/28 exact permissions and remove direct
  order/contact model change plus payment/contact-workflow permissions.
- [x] Add focused admin tests and desktop/mobile browser journeys for read-only
  contacts, status-only orders, and product CRUD.

## Known risks and constraints

- This is not a Git worktree, so filesystem backup and narrowly scoped edits are
  important.
- The pre-custom-user database is a deliberate backup; do not overwrite it.
- The 21 SOT files are immutable.
- The current catalog is seed/demo data and remote-image dependent.
- Notification delivery/provider, distributed edge controls, and a legal PII
  request/retention process are intentionally outside this learning project's
  scope; safe defaults remain notification-off and retention hold.
- Phase 6 proof is local and intentionally narrow: one PostgreSQL version,
  Chromium, no distributed load, no vendor audit, and no production monitoring.

## Verification log

| Date | Evidence | Result |
|---|---|---|
| 2026-09-13 | Baseline `check`, migrations, and 3 tests | Passed. |
| 2026-09-13 | Read-only database audit | Only reproducible 6/24/24 catalog rows. |
| 2026-09-13 | Backup, fresh migrate, seed | Old DB preserved; new DB migrated and seeded. |
| 2026-09-14 | SOT hash comparison | All 21 files unchanged. |
| 2026-09-14 | Desktop/mobile visual review | 24 SOT/Django screenshots retained and reviewed. |
| 2026-09-14 | Node syntax checks | All 6 new browser modules passed. |
| 2026-09-14 | `collectstatic --dry-run` | Passed; 140 namespaced/admin assets resolved. |
| 2026-09-14 | `check` and `makemigrations --check` | Passed; no issues or model drift. |
| 2026-09-14 | Full Django suite | Passed; 40 tests on a fresh migrated test database. |
| 2026-09-14 | Active seed/count audit | Idempotent 6/24/24; zero variants/promos/orders/contacts/users. |
| 2026-09-14 | Targeted Phase 3 account suite | Passed; 13 tests on a fresh migrated test database. |
| 2026-09-14 | Phase 3 checks/static dry run | Passed; no model drift and 141 assets resolved. |
| 2026-09-14 | Phase 4 focused commerce verification | Passed; 31 tests across API/service/UI/admin integration. |
| 2026-09-14 | Active migration 0005 | Applied request fingerprint field successfully. |
| 2026-09-14 | Final full Django suite | Passed; 74 tests in 143.848 seconds on a fresh migrated database. |
| 2026-09-14 | Final standard/static/JS/SOT gates | Passed; no issues/drift, all modules parse, assets resolve, all hashes match. |
| 2026-09-14 | Phase 5 activation regression recap | Phase 3: 13 tests passed in 45.028s; Phase 4 focused: 25 tests passed in 1.128s. |
| 2026-09-14 | Phase 5 focused contact/operations/admin coverage | Passed validation, abuse, replay, notification, permissions, transitions, restock, rollback, role, and audit paths. |
| 2026-09-14 | Active migration/roles | Applied `store.0006`; provisioned four exact least-privilege groups. |
| 2026-09-14 | Final full Django suite | Passed; 99 tests in 96.401 seconds on a fresh migrated database. |
| 2026-09-14 | Final Phase 5 gates | `check`, migration freshness, static dry-run, six JS parses, and all 21 SOT hashes passed. |
| 2026-09-16 | Current full Django suite | Passed; 118 discovered with 4 PostgreSQL-only skips in 127.147s. |
| 2026-09-16 | Isolated PostgreSQL 18 concurrency | Passed all 4 multi-connection races in 7.540s; cleanup fallback left no listener. |
| 2026-09-16 | Playwright desktop/mobile | Passed 5 scenarios in both viewports, 10 runs total. |
| 2026-09-16 | Simplified admin dashboard | Product CRUD, immutable/status-only orders, read-only contacts, and exact permissions passed focused and browser coverage. |
| 2026-09-16 | Dashboard staff-role reconciliation | Active groups updated to 21/6/5/28 exact permissions. |
| 2026-09-16 | Final current gates | `check`, migration freshness, static dry-run, six JS parses, and all 21 SOT hashes passed. |

## Next concrete action

No roadmap phase is active. Await the next product request while preserving the
completed local-learning scope; deployment and backup engineering remain out
of scope.
