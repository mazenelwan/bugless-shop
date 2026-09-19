# Customer Accounts

Last updated: 2026-09-14 (Phase 6 scope refactored)

## Phase 3 activation contract

Phase 3 is complete. It adds customer-facing authentication on the existing
`accounts.User` model while preserving optional guest checkout and the six
public SOT pages.

Chosen baseline:

- email and password authentication;
- no mandatory email verification;
- no social login;
- no saved-address model;
- no marketing-consent or account-deletion workflow yet;
- registration signs the new user in immediately;
- first and last names are optional profile fields;
- login email may be edited through the profile and remains normalized/unique;
- password reset uses Django's single-use token flow and console email locally;
- logout is POST-only; and
- authentication abuse controls use the configured Django cache with hashed
  keys and user-readable HTTP 429 responses.

## Route contract

All routes use the `accounts:` namespace:

| Path | Name | Access/method |
|---|---|---|
| `/accounts/register/` | `accounts:register` | Anonymous GET/POST; authenticated users redirect to profile |
| `/accounts/login/` | `accounts:login` | Anonymous GET/POST; safe local `next` supported |
| `/accounts/logout/` | `accounts:logout` | Authenticated POST only |
| `/accounts/profile/` | `accounts:profile` | Authenticated GET/POST |
| `/accounts/password/change/` | `accounts:password_change` | Authenticated GET/POST |
| `/accounts/password/change/done/` | `accounts:password_change_done` | Authenticated GET |
| `/accounts/password/reset/` | `accounts:password_reset` | Anonymous GET/POST |
| `/accounts/password/reset/done/` | `accounts:password_reset_done` | Anonymous GET |
| `/accounts/reset/<uidb64>/<token>/` | `accounts:password_reset_confirm` | Anonymous token GET/POST |
| `/accounts/reset/done/` | `accounts:password_reset_complete` | Anonymous GET |
| `/accounts/orders/` | `accounts:order_list` | Authenticated GET; owner-filtered |
| `/accounts/orders/<number>/` | `accounts:order_detail` | Authenticated GET; owner-filtered |

Unknown, guest-owned, and another customer's account order number must return
404 from account order detail. The private token URL remains available for
guest/email-link confirmation.

## Form contract

Registration fields:

- `email` (required, normalized, case-insensitively unique);
- `first_name` (optional);
- `last_name` (optional);
- `password1` and `password2` (required and passed through Django password
  validators); and
- optional hidden `next`, accepted only when it is a safe same-host URL.

Login fields:

- `username` HTML field containing the email login identity;
- `password`; and
- optional hidden `next`, validated by Django's login view.

Profile fields:

- `email`;
- `first_name`; and
- `last_name`.

Password change/reset forms use Django's standard forms and token generator.
Password reset must not reveal whether an email address exists.

All state-changing forms require CSRF. Validation errors are bound to individual
fields plus a safe non-field summary. Passwords and tokens are never re-rendered
or logged.

## Session and redirect rules

- Registration calls Django `login()`, which rotates the anonymous session.
- Successful login uses Django's safe redirect handling; external `next`
  destinations are ignored.
- Password change uses `PasswordChangeView`, which updates the session auth
  hash so the user stays signed in.
- Logout accepts POST only and redirects Home.
- Anonymous access to profile/orders/password change redirects to login with a
  local `next` value.

## Abuse-control baseline

The default cache-backed limits are configurable:

- login: 10 failed/submitted attempts per 300 seconds per IP/email fingerprint;
- registration: 5 attempts per 300 seconds per IP fingerprint; and
- password reset: 5 attempts per 300 seconds per IP/email fingerprint.

Cache keys use `salted_hmac` over scope, `REMOTE_ADDR`, and normalized email;
raw email/IP values are not placed in cache keys or logs. Successful login and
registration clear their matching bucket. Reset requests do not clear it.

This is an application-level learning baseline, not complete production bot
defense. A shared cache and edge/provider limits would be required before any
multi-process deployment, which is outside this project's scope. The code must
not trust `X-Forwarded-For` directly.

## Visual contract

No account SOT exists. Account pages use a namespaced `accounts/accounts.css`
that reuses the Bugless Fit red/black typography, spacing, cards, controls, and
responsive proportions. Existing public templates/classes are not changed to
fit account pages. A direct Account link is not added to the authored public
navigation during Phase 3.

## Order ownership integration

Account order pages are read-only and filter by `Order.customer=request.user`.
They render immutable order/contact/money/item snapshots. Guest orders are not
claimed merely because their email matches a later account. Phase 4 now
associates each new signed-in checkout directly with the session user; the
submitted email remains an immutable delivery/contact snapshot and cannot
select or override ownership.

## Phase 3 acceptance

- Registration, login, POST logout, profile update, password change, and reset
  flow work using named routes and CSRF.
- Duplicate normalized email is rejected safely.
- Unsafe external `next` is ignored.
- Sessions rotate/update correctly.
- Reset responses do not enumerate accounts.
- Throttled requests return 429 without exposing identifiers.
- Account pages require authentication.
- Account order data is owner-filtered and guest orders are excluded.
- Public/guest storefront access remains unchanged.
- Standard checks, tests, static collection, and documentation pass.

## Implemented structure and verification

- `accounts/forms.py` owns normalized registration, login, profile, and reset
  forms and their field-safe validation.
- `accounts/views.py` composes Django authentication views with safe redirects,
  session handling, POST-only logout, throttling, profile updates, and private
  order reads.
- `accounts/throttling.py` owns cache counters and HMAC-only cache keys. Cache
  outages fail open so a cache failure cannot lock every customer out; no raw
  identifier is logged.
- `accounts/urls.py` exposes every named route in the route contract.
- `templates/accounts/` and `accounts/static/accounts/accounts.css` provide the
  responsive, namespaced account UI without changing the six public SOT pages.
- `store/selectors.customer_orders()` centralizes owner-filtered account order
  reads.

The 13 targeted account tests passed on a fresh migrated test database. They
cover normalization and duplicates, registration/login redirects, POST-only
logout, protected profile updates, password change session continuity,
enumeration-safe and single-use reset tokens, owner isolation, HMAC key
privacy, throttling, and CSRF. `check`, `makemigrations --check`, and static
collection dry run also passed. No Phase 3 schema migration was required
because the approved profile uses fields already present on `accounts.User`.

## Deferred decisions

- Mandatory email verification and email-change reconfirmation.
- Saved addresses.
- Social login.
- Marketing preferences.
- Account deletion/export and final retention/request rules. Phase 5 enforces a
  retention hold and exposes no automatic deletion or bulk export until the
  legal/business period and requester-verification process are approved.
- Distributed cache, edge rate limiting, CAPTCHA, and provider abuse controls.
- Production email delivery.
