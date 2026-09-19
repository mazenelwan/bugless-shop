# Decision Log

Last updated: 2026-09-16 (simplified staff dashboard)

Accepted decisions must not be reversed silently. Update this log and every
affected domain contract when a decision changes.

| ID | Status | Decision | Reason |
|---|---|---|---|
| D-001 | Accepted | `frontend/` is the visual and interaction SOT. | Explicit user instruction. |
| D-002 | Accepted | Backend code and pre-integration Django templates may be refactored/replaced. | Explicit user instruction; they were not authoritative. |
| D-003 | Accepted | Preserve SOT files and implement editable Django copies. | Retains original work and makes visual comparison possible. |
| D-004 | Accepted | Django/database state owns catalog identity, prices, discounts, totals, availability, and stock. | Correctness and tamper resistance. |
| D-005 | Accepted | Keep the SOT bundle flat under `frontend/`. | Original paths are sibling-relative. |
| D-006 | Accepted | `docs/` is durable cross-session memory and is part of each phase's acceptance. | Explicit user instruction. |
| D-007 | Accepted | Support optional customer accounts and guest checkout. | Preserves the guest-first SOT while adding account value. |
| D-008 | Accepted | Start with EGP and cash on delivery; model delivery/tax explicitly with zero defaults. | Matches current product behavior without blocking future business rules. |
| D-009 | Accepted | Promotions live in the database; SOT codes are development-only seed data. | Prevents browser-authoritative discounts and accidental publication. |
| D-010 | Accepted | Treat the 24 SOT products as deterministic development seed data. | Production catalog approval was not provided. |
| D-011 | Accepted | Deliver through documented dependency-ordered phases with explicit gates. | Explicit user instruction. |
| D-012 | Accepted | Customer authentication/account functionality is part of the target. | Explicit user instruction; D-007 defines its checkout relationship. |
| D-013 | Accepted | Use a dedicated custom email-user app now; preserve and rebuild the reproducible local SQLite database. | Avoids a late user-model migration; audited data contained no users/orders/messages. |
| D-014 | Accepted | Products/variants use immutable UUID public IDs; slugs are routes and legacy IDs are import/redirect-only. | Cart identity must survive mutable catalog edits. |
| D-015 | Accepted | Product stock is authoritative without active variants; active variant stock is authoritative otherwise. | Establishes one lock/decrement source. |
| D-016 | Accepted | SOT ratings are optional validated display metadata, not review aggregates. | No review system or source counts exist. |
| D-017 | Accepted | Django uses only namespaced derived assets under `store/static/store/`; `frontend/` is excluded from static discovery. | Preserves SOT integrity and prevents accidental repository/source exposure. |
| D-018 | Accepted | `bfCart` Version 1 stores only product UUID, nullable variant UUID, and quantity; legacy carts migrate only when identity is deterministic. | One cross-page contract without browser-owned commerce data. |
| D-019 | Accepted | Phase 2 Checkout renders the cart/form but refuses submission, browser promotions, fake success, and cart clearing until Phase 4. | Avoids presenting insecure placeholder commerce as a real order. |
| D-020 | Accepted | Order confirmation requires number plus private UUID token, with authenticated cross-owner access returning 404. | Removes guessable number-only disclosure while preserving guest/email-link access. |
| D-021 | Accepted | Preserve remote image URL compatibility for Phase 2; choose managed media/object storage before production. | Required for SOT parity without prematurely selecting infrastructure. |
| D-022 | Accepted | New JSON APIs will use an `ok/data` or structured `error` envelope; logs exclude secrets, bodies, tokens, addresses, and unnecessary PII. | Stable clients, safe field errors, and privacy. The old checkout response is explicitly transitional. |
| D-023 | Accepted | Phase 3 uses email/password accounts without mandatory verification or social login; saved addresses, marketing consent, and deletion/retention workflows are deferred. | Delivers secure core identity without inventing unapproved data or provider dependencies. |
| D-024 | Accepted | Registration signs the user in, profile permits normalized email/name edits, logout is POST-only, and safe local `next` redirects are supported. | Standard Django session behavior with CSRF and open-redirect protection. |
| D-025 | Accepted | Password change/reset use Django primitives; reset is enumeration-safe and console email remains the local provider. | Reuses audited token/session behavior while production email is undecided. |
| D-026 | Accepted | Login, registration, and reset receive configurable cache-backed throttles keyed by an HMAC of scope, direct peer IP, and optional email. | Provides a dependency-free abuse baseline without storing raw identifiers; shared-cache/edge enforcement would be required only for use beyond this learning environment. |
| D-027 | Accepted | Account order history is owner-filtered by `Order.customer`; guest orders are never claimed by email matching. | Prevents account data disclosure and unsafe retroactive ownership. |
| D-028 | Accepted | Phase 4 ships EGP cash-on-delivery with zero delivery/tax, optional accounts, no pre-commit reservation/expiry, and no production promo seed; online payment and nonzero fees/tax remain deferred. | Implements the previously documented baseline without inventing provider or jurisdiction rules. |
| D-029 | Accepted | Checkout JSON Version 1 is strict and UUID-only, with a 64 KiB body, 1-50 submitted lines, quantities 1-99 after duplicate coalescing, and the schema money ceiling. | Bounds work and storage while matching the canonical browser cart. |
| D-030 | Accepted | The service sorts and locks products, variants, and promotion deterministically, validates the complete cart before writes, and decrements variant stock instead of product stock whenever active variants exist. | Preserves atomicity and one inventory authority while reducing deadlock risk. |
| D-031 | Accepted | Promotion minimum uses full subtotal; scope is the union of selected products/categories; percentage rounds half-up once; caps apply after calculation; creation, not quote/replay, consumes usage. | Makes every discount deterministic and server-authoritative. |
| D-032 | Accepted | A client UUID is bound to a SHA-256 fingerprint of normalized order semantics and actor; matching retries replay the order, changed reuse conflicts, and replays never revalidate current catalog state. | Prevents duplicate orders while making ambiguous key reuse fail safely. |
| D-033 | Accepted | Checkout uses a read-only server quote for promo feedback and clears `bfCart` only after successful create/replay, then follows the private confirmation URL. | Preserves SOT interaction intent without granting browser authority or faking success. |
| D-034 | Accepted | Checkout requires name/email/phone/address, permits optional city/notes, case-folds email, bounds text, and permits common phone punctuation with 7-15 digits. | Provides usable typed validation without prematurely modeling saved addresses or delivery zones. |
| D-035 | Accepted | Contact submissions use a bounded Django form, a per-form UUID idempotency key, POST/redirect/GET, an invisible honeypot, and configurable HMAC-keyed direct-peer-IP/email cache throttles. | Prevents accidental duplicate writes and provides a dependency-free abuse baseline without retaining raw throttle identifiers. |
| D-036 | Accepted | Contact staff notifications are optional, disabled until `CONTACT_NOTIFICATION_EMAIL` is configured, dispatched only after commit, and audited; delivery failure never rolls back the persisted message. Visitor acknowledgements remain disabled. | Persistence must be reliable independently of an email provider, and no unapproved visitor-mail workflow should be invented. |
| D-037 | Accepted | Order status changes use explicit sequential transitions: pending to confirmed/cancelled, confirmed to preparing/cancelled, preparing to shipped/cancelled, and shipped to delivered. Payment changes use an independently audited state machine; refund status records a completed external/manual refund and does not move money. | Prevents arbitrary admin state edits and avoids falsely claiming that the application processes refunds. |
| D-038 | Accepted | Pre-shipment cancellation is atomic and idempotent, restores the exact product or variant row originally decremented once, and records immutable audit events. Paid/pending-payment orders must be refunded or resolved first; missing inventory targets reject the whole cancellation. Promotion usage is not credited back. | Protects stock and campaign-limit integrity while failing safely when historical live references cannot be restored. |
| D-039 | Accepted | Staff operations use least-privilege Django permissions and four idempotently configurable groups: Catalog Manager, Fulfillment Staff, Customer Support, and Store Manager. Order transition, cancellation, payment recording, refund recording, and contact workflow permissions are distinct. | Staff should receive only the operational powers required by their role, without requiring blanket superuser access. |
| D-040 | Accepted | Order/contact submissions and audit events are immutable in admin; lifecycle changes go through services/actions, and order/contact/audit deletion is disabled in admin. | Preserves historical truth and makes every supported staff state change attributable. |
| D-041 | Accepted | Until a business/legal retention period and request-verification process are approved, the application performs no automatic PII deletion, anonymization, or bulk export. Admin access is permission-scoped and deletion is denied; audit rows contain identifiers/state only, not message bodies or address snapshots. | A retention hold is safer than silently destroying records or exposing an unapproved export/erasure workflow. This would need review before any use beyond the learning environment. |
| D-042 | Accepted | Phase 6 is a learning-focused engineering phase limited to application security, real concurrency behavior, repeatable browser E2E testing, and privacy-safe local monitoring. Hosting, deployment, release engineering, CI/CD, production providers, backup/restore systems, launch approval, and production-readiness claims are explicitly out of scope. | The project will not be deployed to production; the remaining work should teach and prove application behavior rather than build unused operations infrastructure. |
| D-043 | Accepted | Phase 6 concurrency evidence will use the installed PostgreSQL 18 binaries to create an isolated loopback-only test cluster, without changing or depending on the existing Windows PostgreSQL service. | SQLite cannot prove row locks, while a separate local cluster provides real multi-connection PostgreSQL behavior without introducing Docker or touching unrelated databases. |
| D-044 | Accepted | Browser E2E uses Playwright with Chromium at 1440x1200 and 390x844, with a deterministic local SQLite fixture database and failure-only traces/screenshots. | One browser engine and the existing proof viewports give repeatable learning evidence without pretending to be a production browser/device certification matrix. |
| D-045 | Accepted | Monitoring remains local: structured allow-listed JSON logs, generated request correlation IDs, privacy-safe operation/security events, and a minimal database-aware health diagnostic; no SaaS exporter is added. | This makes failures inspectable while avoiding an unnecessary provider and preventing request bodies, credentials, tokens, addresses, messages, and unnecessary contact data from reaching logs. |
| D-046 | Accepted | The supported Django line remains 5.2 LTS, but the dependency floor is raised from the broad 5.0 baseline to security-patched Django 5.2.17. | The installed 5.2.7 predates multiple published security fixes; staying on the same LTS feature line minimizes compatibility risk while applying the current patches. |
| D-047 | Accepted | Use the existing Django admin as the simple staff dashboard. Contact messages are view-only. Orders and their history remain immutable, and the dashboard exposes only service-backed business-status actions; payment and contact-workflow actions are not exposed or provisioned to the standard staff groups. Products retain CRUD for their current fields, images, and variants, including delete permission for Catalog Managers and Store Managers. This supersedes only the admin-surface and role-provisioning portions of D-037 through D-040; their transaction, audit, restock, and immutable-history rules remain active. | Explicit user direction requested a minimal dashboard with read-only contact messages, status-only order manipulation, and product CRUD. Reusing Django admin keeps the surface small while routing cancellation and other order-status changes through the existing safe services. |

## Resolved Phase 1/2 decision gates

- Account policy: optional accounts plus guest checkout.
- Identity: custom email user introduced before account data existed.
- Local data: old SQLite file retained as a recoverable backup; active database
  rebuilt and reseeded.
- Payment/currency: cash on delivery and EGP.
- Delivery/tax: represented, zero until rules are approved.
- Promotions: database entities; demo codes opt-in only.
- Catalog status: deterministic development seed.
- Ordering: explicit admin-controlled category/product display order.
- Ratings: display metadata only.
- Images: remote-compatible through parity; managed storage later.
- Confirmation: private UUID bearer token plus account ownership boundary.

## Open future decisions

These are not blockers for the active/completed scope:

- Phase 3 deferred: mandatory email verification, saved addresses, marketing
  consent, account deletion/retention, social login, and production-grade
  distributed/edge abuse controls.
- Phase 4 deferred after the accepted baseline: nonzero delivery/tax,
  production catalog/promo approval, lower business-specific order limits,
  online payment, expiry/reservations, and tracking.
- Phase 5 deferred product choices remain intentionally unset for this learning
  project: notification stays off and the retention hold stays active.
- Phase 6 uses the local PostgreSQL/Playwright/monitoring choices in D-043 to
  D-045. No production services or release workflow will be selected.

## Adding or changing a decision

Record the date, status, decision, and enough reasoning to avoid rediscovery.
When a decision changes, add a superseding entry or explicitly mark the old one
superseded; update architecture, domain docs, phase plan, migrations/tests, and
the implementation together.
