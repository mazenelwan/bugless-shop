# Security and Local Monitoring

Last updated: 2026-09-16 (Phase 6 verified)

## Scope

This is a threat model and verification contract for a local learning project.
It improves and demonstrates application security; it is not a production
security certification. Deployment, edge controls, production secrets,
external monitoring, backups, and operational response services remain out of
scope by decision D-042.

## Assets and trust boundaries

Protected assets are account credentials/sessions, customer contact and
delivery snapshots, private order confirmation tokens, catalog/inventory and
promotion state, immutable audit history, staff permissions, and logs.

Untrusted boundaries are every browser field, query string, JSON body,
local-storage value, retry UUID, forwarded header, remote catalog URL, and
staff action input. Django/database state is authoritative. The public web,
account pages, checkout APIs, contact form, token confirmation, admin, health
diagnostic, third-party presentation resources, and local logs are the exposed
surfaces reviewed in this phase.

## Threats, controls, and evidence

| Threat | Implemented control | Evidence |
|---|---|---|
| Browser money/stock/promotion tampering | Strict UUID-only schema; unknown fields rejected; server reloads catalog and calculates money | Phase 4 checkout and endpoint-safety tests |
| Oversell, double-submit, promo overuse, or double restock | Atomic writes, deterministic row locks, unique fingerprints/events, idempotent transitions | Four real multi-connection PostgreSQL races in `test_phase6_concurrency.py` |
| Order IDOR or bearer-token disclosure | Owner-filtered account querysets; number plus UUID confirmation; cross-owner 404; `no-store`; same-origin referrer policy; URL-free structured logs | Catalog/account tests, E2E wrong-token 404, logging tests |
| CSRF, unsafe methods, session fixation, or open redirect | Django CSRF middleware/tokens, POST-only writes/logout, session rotation, local-host `next` validation, HttpOnly/Lax session and CSRF cookies | Account/contact/checkout tests and Phase 6 boundary tests |
| Password guessing, reset enumeration, or raw throttle identifiers | Django password hashing/validation and reset tokens; generic reset response; HMAC-only peer/email cache keys; local rate limits | Phase 3 account tests and safe-log tests |
| Stored/reflected script injection | Django auto-escaping; typed/length-bounded fields; no authored inline executable script; CSP limits scripts to self and pinned CDN origin | Existing bound-error tests, CSP assertions, desktop/mobile E2E |
| Request/memory exhaustion | Global 64 KiB in-memory body ceiling, narrower 16 KiB contact ceiling, cart line/quantity/value limits, field lengths, cache throttles | Checkout/contact rejection tests |
| Source, database, template, or environment disclosure | Namespaced static configuration only; no repository/static root finder | Static manifest tests and Phase 6 sensitive-path 404 matrix |
| Host/header/log injection or accidental PII logging | Host allow-list; generated UUID request IDs; log formatter serializes only fixed fields and safe tokens; Django request/security loggers use the same formatter | Host, correlation, newline/private-URL, and formatter tests |
| Over-privileged or unaudited staff mutation | Four exact groups, read-only contacts/orders, service-backed order-status actions only, catalog CRUD permissions, and immutable snapshots/events | Permission tests plus desktop/mobile Store Manager browser journeys |
| Silent database failure | Minimal `GET /health/` performs `SELECT 1`, returns only `ok/unavailable`, and emits a correlated safe event | Healthy/failure/method monitoring tests |
| Known framework vulnerabilities | Django 5.2 LTS floor raised to the current security-patched 5.2.17 release | Dependency version, full regression suite, and official Django security release record |

## Header policy

Every Django response receives CSP, Permissions Policy, frame denial,
nosniff, same-origin referrer and opener policies, same-origin resource policy,
and cross-domain-policy denial. The CSP permits local scripts plus the existing
jsDelivr dependency; styles permit the existing stylesheet origins and inline
style attributes; images permit HTTPS because the catalog/SOT uses remote
images; only Google Maps may frame content. `object-src` and workers are denied.

`style-src 'unsafe-inline'` is a deliberate SOT compatibility exception.
`script-src` does not permit inline execution. Browser E2E proves the local
critical journeys still work while all third-party requests are deterministically
stubbed, so commerce and account correctness do not rely on those providers.

## Logging and health contract

`RequestMonitoringMiddleware` generates a new UUID for every request and does
not trust an incoming correlation header. It returns `X-Request-ID` and records
only named route, method, status, and rounded duration. Checkout/contact/staff
services emit result codes and internal numeric object IDs after commit where
appropriate. Authentication/contact rate limits emit scope-only events.

`SafeJsonFormatter` ignores the free-form log message, interpolation arguments,
unknown extras, raw paths, and query strings. The only accepted fields are
fixed event/state/code tokens, integer IDs/status/timing, logger/level/time,
exception class, and a valid request UUID. Passwords, CSRF/reset/confirmation
tokens, names, email, phone, addresses, cart/contact bodies, and admin search
terms are never valid log fields.

`GET /health/` checks the default database and returns either
`{"ok":true,"database":"ok"}` or a generic 503 unavailable response. It is
never cached and exposes no exception, host, credentials, migration state,
counts, or user data.

## Residual learning-only limits

- The cache throttle is per-process unless the learner configures a shared
  cache; there is no edge rate limiter or CAPTCHA.
- CSP must retain inline styles and broad HTTPS images to preserve the authored
  SOT, and several presentation dependencies remain remote without local
  vendoring/SRI. Critical E2E stubs them, but that does not audit those vendors.
- `DEBUG=True`, non-secure cookies, and the fallback secret are local defaults.
  The secure-cookie/SSL/HSTS switches exist for study, but this project will not
  define a deployment profile.
- The health endpoint is intentionally unauthenticated and reveals only binary
  database availability. There is no uptime service or alert delivery.
- No penetration test, distributed load test, malware scan, third-party code
  audit, or production incident-response claim is made.
