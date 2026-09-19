# Bugless Fit Project Memory

Last verified: 2026-09-16

This directory is the durable implementation record for the Bugless Fit Django
store. The 21 standalone files under `frontend/` remain the visual and
interaction source of truth (SOT); Django templates and namespaced static assets
are derived implementations.

## Resume protocol

1. Read the root `AGENTS.md`.
2. Read this page, then `progress/README.md`.
3. Read the domain documents linked below that apply to the next task.
4. Inspect code when documentation and implementation disagree.
5. Document every changed contract, route, model, rule, limitation, test result,
   and durable decision before declaring a phase complete.

## Domain index

- [Architecture](architecture/README.md): application boundaries, authority,
  settings, migrations, static files, and privacy conventions.
- [Accounts](accounts/README.md): authentication routes/forms, sessions,
  throttling, profile, and customer order-ownership contract.
- [Backend](backend/README.md): current apps, routes, models, forms, services,
  selectors, admin, and API behavior.
- [Catalog](catalog/README.md): identifiers, availability, ordering, search,
  related products, and deterministic seed behavior.
- [Frontend](frontend/README.md): SOT inventory, template/static mapping,
  `bfCart` contract, progressive enhancement, and visual evidence.
- [Orders](orders/README.md): cart, checkout APIs, validation, promotions,
  inventory, order schema, idempotency, and confirmation access.
- [Contact](contact/README.md): validated SOT-shaped form, idempotency, abuse
  controls, notifications, workflow audit, and retention boundary.
- [Testing](testing/README.md): commands, coverage, evidence, and remaining test
  environments.
- [Security and monitoring](security/README.md): Phase 6 threat model, headers,
  privacy-safe logs, health diagnostics, evidence, and residual limits.
- [Decisions](decisions/README.md): accepted architecture and product choices.
- [Progress](progress/README.md): phase gates, completed work, and next work.

## Current snapshot

- Phases 0 through 6 are complete: governance, architecture/database, public
  frontend/catalog integration, customer accounts, atomic commerce, validated
  contact, safe staff/order operations, security, real PostgreSQL concurrency,
  browser E2E, and privacy-safe local monitoring.
- The follow-up Django admin dashboard is simplified to read-only contact
  messages, immutable orders with status actions only, and catalog product CRUD.
  Deployment and backup engineering remain explicitly out of scope for this
  learning project.
- Django project: `buglessfit/`.
- Local applications: `accounts/` and `store/`.
- Derived public templates: `templates/store/`.
- Namespaced public assets: `store/static/store/`.
- Local database: `db.sqlite3`; PostgreSQL is selected through
  `DATABASE_URL`.
- Current development catalog: 6 categories, 24 products, 24 primary images,
  0 variants, and 0 promotions. There are four provisioned least-privilege
  staff groups and no orders, items, contacts, audit events, or users. The
  catalog is seed/demo data until separately approved for production.
- The pre-custom-user SQLite database is recoverable at
  `db.pre-custom-user.20260913.sqlite3`.
- The repository is not a Git worktree. Preserve unrelated files and use the
  backup/migration path rather than destructive resets.

## Implemented foundation

- `accounts.User` is the swappable email-login user model. Registration,
  login, POST-only logout, profile editing, password change/reset, throttling,
  and owner-filtered order history are implemented under `/accounts/`.
- Products and variants have immutable UUID public identifiers. Product slugs
  are readable routes; SOT IDs are retained only as legacy identifiers.
- Category/product display order, product images, variants, promotions, order
  money, private confirmation tokens, idempotency identifiers, ownership, and
  immutable item snapshots are migration-backed and admin-manageable.
- Public Home, Shop, Product, Checkout, Contact, and About pages
  render through Django using named routes and namespaced static assets.
- Browser cart state uses one versioned identifier-only `bfCart` shape across
  Shop, Product, and Checkout. Display metadata is server-rendered; it is never
  accepted as purchase authority.
- Checkout uses strict UUID-only quote/create APIs. The server validates and
  locks catalog/promotion state, owns all money, atomically writes immutable
  order snapshots and the correct inventory decrement, fingerprints retry
  semantics, associates signed-in owners, and returns private confirmations.
- The browser uses CSRF, a cryptographic session retry key, safe validation
  feedback, and clears `bfCart` only after confirmed create/replay.
- Contact uses a bounded Django form, UUID/fingerprint replay protection,
  honeypot and HMAC-keyed cache throttles, post-commit optional staff email,
  safe PRG feedback, and immutable workflow/notification events.
- Order/payment/contact lifecycle fields are read-only in admin. Permissioned
  order-status actions call transactional services; payment and contact-
  workflow actions are not exposed. Pre-shipment cancellation restores the
  exact original inventory authority once and writes immutable audit events.
- Catalog staff can create, update, and delete products and their current image
  and variant inlines while public identifiers remain immutable.
- `configure_staff_roles` owns the Catalog Manager, Fulfillment Staff, Customer
  Support, and Store Manager permission sets.

## Non-negotiable invariants

- Do not redesign or edit the six SOT pages to simplify integration.
- Django/database data owns product identity, price, discount, availability,
  totals, and stock.
- Treat local-storage and JSON data as untrusted.
- Validate a complete order before mutation; create the order and decrement the
  correct inventory rows atomically.
- Never expose source, templates, environment files, databases, or the flat SOT
  directory through Django static configuration.
- Add a migration for every schema change; never rewrite an applied migration
  to represent new work.
- Do not log raw checkout/contact bodies, passwords, tokens, addresses, or
  other unnecessary personal data.

## Latest verification summary

The latest verification commands and detailed results are maintained in
`testing/README.md` and `progress/README.md`. The current SQLite run applies all
migrations through `store.0006`, discovers 118 tests, and skips only four tests
that run separately and pass against PostgreSQL 18. Ten Playwright runs pass
across desktop/mobile Chromium. Django checks/migration freshness, six
JavaScript syntax checks, and static collection pass. All 21 SOT file hashes
remain unchanged, and 24 retained screenshots cover the Phase 2 six-page
SOT/Django pairs at desktop and mobile viewports.
