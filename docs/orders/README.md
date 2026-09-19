# Cart, Checkout, Promotions, Inventory, and Orders

Last updated: 2026-09-16 (status-only order dashboard)

## Phase boundary

Phase 1 established the durable promotion/order schema and inventory rules.
Phase 2 unified browser cart state and integrated the authored Checkout shell.
Phase 4 is complete. It replaced the transitional endpoint with quote and
create adapters over one authoritative commerce service. Phase 5 activated the
staff transition/cancellation/restock contract below, and Phase 6 proved its
important races against an isolated local PostgreSQL 18 cluster.

## Browser cart contract

`bfCart` Version 1 stores:

```json
{
  "version": 1,
  "lines": [
    {
      "productId": "product UUID",
      "variantId": null,
      "quantity": 1
    }
  ]
}
```

Only identifiers and quantity are persisted. Server-rendered catalog JSON
supplies names, images, prices, URLs, and display availability for cart UI. All
display money is an estimate and must be recalculated during checkout.

Legacy Shop/Product array shapes are upgraded deterministically where identity
is unambiguous; malformed or ambiguous lines are discarded. Full migration
rules are in `docs/frontend/README.md`.

## Checkout browser behavior

The Phase 4 Django Checkout page now:

- reads the canonical cart;
- renders item names, quantities, estimated line totals, subtotal, and total;
- retains the authored empty-cart and shipping form layout;
- displays server-rendered catalog metadata;
- never submits browser price/total values;
- sends Version 1 identifiers and quantities to the quote/create APIs;
- treats quote totals as an advisory server snapshot and create totals as final;
- sends the promo input to the database-backed quote/create service rather than
  applying the three SOT JavaScript codes;
- uses a cryptographically generated UUID stored in `sessionStorage` for safe
  network retries;
- binds safe validation summaries and marks corresponding inputs invalid;
- disables duplicate button submissions while a request is pending;
- clears `bfCart` and the retry key only after a successful create or replay;
  and
- navigates to the returned private confirmation URL rather than inventing a
  number or success state.

## Promotion foundation

`Promotion` supports:

- normalized, case-insensitively unique codes;
- fixed or percentage discounts;
- positive value and percentage-at-most-100 constraints;
- minimum subtotal;
- optional maximum discount;
- optional start/end window;
- optional global and per-customer limits;
- usage count;
- optional category/product scope; and
- inactive-by-default publication.

`SAVE10`, `SAVE20`, and `WELCOME50` are development data only and are
created/activated only with `seed_catalog --with-demo-promotions`. No promotion
is production-approved by this phase.

Promotion calculation is frozen as follows:

- input code is stripped and uppercased; blank means no promotion;
- inactive, unknown, early, expired, exhausted, or over-customer-limit codes
  are rejected without changing any state;
- `minimum_subtotal` applies to the complete cart subtotal;
- a promotion with no product/category scope applies to every line;
- otherwise the eligible lines are the union of explicitly scoped products and
  products in explicitly scoped categories;
- percentage discounts use the eligible subtotal and round once to cents with
  `ROUND_HALF_UP`;
- fixed discounts are capped at the eligible subtotal;
- `maximum_discount`, when present, is applied after the base calculation;
- the final discount is always capped at the full subtotal;
- promotion usage is locked and incremented once per newly committed order,
  never for a quote or idempotent replay; and
- per-customer use is counted by customer foreign key for authenticated orders
  and case-insensitive normalized order email for guest orders. Creation and
  cancellation both continue to count until Phase 5 defines reversal policy.

## Inventory contract

- Variantless product: lock and decrement `Product.stock`.
- Product with active variants: lock and decrement the selected
  `ProductVariant.stock`; product stock is ignored.
- Never decrement both levels.
- Product/category/variant must be active, `sold_out` must be false, and
  requested quantity must be within current stock.
- Validate the complete order before creating rows or changing inventory.

## Frozen Phase 5 operations contract

Business-status transitions are sequential and service-only:

```text
pending   -> confirmed | cancelled
confirmed -> preparing | cancelled
preparing -> shipped   | cancelled
shipped   -> delivered
delivered -> terminal
cancelled -> terminal
```

Payment status is independent and audited:

```text
unpaid  -> paid
pending -> paid | failed
failed  -> pending
paid    -> refunded
refunded -> terminal
```

The simplified Django admin exposes only business-status actions. Every order
field, including `status` and `payment_status`, remains read-only on the detail
page; selected orders move through named actions that call the service below.
Payment receipt/refund actions are not exposed and the standard staff groups do
not receive their permissions. Cancellation refuses paid or payment-pending
orders until that external state is resolved, and is available only from
pending, confirmed, or preparing.

Cancellation locks the order, its immutable line snapshots, and every referenced
inventory row in deterministic order. It verifies all targets first, restores
the exact product row used by a variantless purchase or exact variant row used
by a variant purchase, sets `inventory_restocked_at`, changes status, and writes
status/restock audit events in one transaction. A retry of an already-complete
cancellation is a no-op. A missing historical inventory row, invalid state,
permission failure, overflow, or write exception leaves all stock and order
state unchanged. Cancellation does not decrement `Promotion.times_used`; a
campaign use remains consumed to avoid cancellation-based limit cycling.

Forward transitions require `store.transition_order`; cancellation requires
`store.cancel_order`; payment receipt requires `store.record_order_payment`;
and refund recording requires `store.refund_order`. Immutable `OrderEvent`
rows retain actor, event type, old/new state, a non-PII operation note, and time.
Order snapshots, state fields, restock marker, items, and events are read-only
in admin, and order/item/event deletion is disabled there. Status changes occur
only through the named service-backed actions; payment transitions remain an
internal domain capability rather than a dashboard operation.

## Order schema

`Order` contains:

- unique human-facing number `BF-YYYYMMDD-<12 random hex>`;
- unique private UUID confirmation token;
- unique UUID idempotency field bound to the Phase 4 request key;
- a SHA-256 request fingerprint used to reject reuse with different semantics;
- nullable authenticated owner for optional-account plus guest checkout;
- customer name, email, phone, address, and city snapshots;
- subtotal, discount, delivery fee, tax, and grand total;
- EGP currency;
- nullable promotion relation and promotion-code snapshot;
- cash-on-delivery method;
- payment status;
- business status;
- notes and timestamps.

`OrderItem` keeps nullable current product/variant relations plus immutable
product UUID, variant UUID, SKU, product name, variant label, selected options,
unit price, quantity, and line subtotal snapshots. Historical order display
therefore survives catalog edits/deletion.

Database checks enforce positive item quantity, nonnegative item/order money,
discount not exceeding subtotal, and total model validation verifies:

```text
total = subtotal - discount + delivery + tax
```

## Confirmation privacy

The public URL contains both order number and the unguessable confirmation UUID:

```text
/order/<number>/<confirmation-token>/
```

A number alone is insufficient. A wrong token returns 404. An authenticated
customer presenting another customer's valid order URL also receives 404.
Guest and email-link access treat the token as a bearer secret, so it must not
be logged, placed in analytics, or shown in lists. Account order-history routes
enforce explicit customer ownership without relying on the token.

## Frozen Phase 4 HTTP contract

Both endpoints accept only `POST` with `Content-Type: application/json`, normal
Django CSRF protection, and a body no larger than 65,536 bytes. Duplicate JSON
object keys are invalid. Unknown object fields are rejected so client/schema
drift is visible.

### Quote

`POST /api/checkout/quote/` accepts:

```json
{
  "version": 1,
  "promotionCode": "OPTIONAL",
  "lines": [
    {
      "productId": "product UUID",
      "variantId": null,
      "quantity": 1
    }
  ]
}
```

The endpoint resolves current catalog, stock, and promotion state without
reserving or mutating it. Its totals are an estimate until create acquires
locks and recalculates. A guest quote cannot know the eventual email, so
per-customer promotion limits are enforced only by create for guests; signed-in
quotes can check the account limit.

### Create

`POST /api/checkout/` accepts:

```json
{
  "version": 1,
  "idempotencyKey": "client-generated UUID",
  "customer": {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "+20 100 000 0000",
    "address": "Delivery address",
    "city": "Cairo",
    "notes": "Optional order note"
  },
  "promotionCode": "OPTIONAL",
  "lines": [
    {
      "productId": "product UUID",
      "variantId": null,
      "quantity": 1
    }
  ]
}
```

`name`, `email`, `phone`, and `address` are required. `city` and `notes` are
optional and default to empty strings when omitted. Any supplied value must be
a JSON string.
Values are stripped; email is case-folded. Phone punctuation `+ - ( )` and
spaces are accepted, with 7 through 15 digits required. Maximum lengths match
the schema or explicit service caps: name 160, email 254, phone 40, address
500, city 100, and notes 2,000 characters.

No request may contain product text, SKU, options, price, discount, delivery,
tax, total, currency, status, owner, or payment values. The authenticated user
is read from the server session.

### Shared cart limits and normalization

- `version` must be the JSON integer `1`; booleans/strings are rejected.
- The submitted `lines` array must contain 1 through 50 objects.
- Each product/variant ID must be a canonical UUID string.
- `variantId` is either a UUID string or JSON `null`.
- Quantity must be a JSON integer from 1 through 99; booleans and numeric
  strings are rejected.
- Duplicate `(productId, variantId)` keys coalesce and their quantities sum;
  a sum over 99 is rejected.
- Canonical lines are sorted by product then variant UUID for fingerprinting,
  locking, snapshots, and deterministic behavior.
- The pre-discount subtotal may not exceed the order field ceiling of
  EGP 9,999,999,999.99.

### Success envelopes

Quote returns HTTP 200:

```json
{
  "ok": true,
  "data": {
    "currency": "EGP",
    "subtotal": "100.00",
    "discount": "10.00",
    "delivery": "0.00",
    "tax": "0.00",
    "total": "90.00",
    "promotion": {"code": "SAVE10", "name": "Save ten percent"}
  }
}
```

`promotion` is `null` when none applies. A new create returns HTTP 201 with the
same money/promotion fields plus `orderNumber`, `confirmationUrl`, and
`replayed: false`. An identical retry returns the stored order as HTTP 200 with
`replayed: true`.

Errors use the stable envelope:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_cart",
    "message": "Review the highlighted checkout details.",
    "fields": {"lines.0.quantity": ["Enter a whole number from 1 to 99."]}
  }
}
```

Invalid media type uses 415; malformed JSON/schema/customer/cart/promotion
input uses 400; current catalog, variant, stock, promotion availability, and
idempotency conflicts use 409. Messages never echo private request bodies or
secrets.

## Idempotency contract

The create key is a UUID and is globally unique. The server fingerprints the
cleaned customer snapshot, normalized/coalesced/sorted lines, promotion code,
and authenticated actor marker. The key itself is excluded from the hash.

- same key plus same fingerprint returns the original order and never
  decrements stock or promotion usage again;
- same key plus different fingerprint returns HTTP 409
  `idempotency_conflict` and never mutates state;
- replay behavior is independent of later catalog, stock, promo, or order
  status changes; and
- the browser retains a key across network errors and removes it only after a
  confirmed create/replay. It never auto-generates a replacement after a
  conflict because that could duplicate an already accepted order.

## Frozen atomic flow

1. Validate content type and typed top-level shape.
2. Normalize customer fields and idempotency key.
3. Coalesce duplicate line keys and sort them deterministically.
4. Return an existing fingerprint-matching idempotency result when present.
5. Lock products by public UUID, all their variants by public UUID, and then
   the selected promotion. Recheck idempotency after potentially blocking.
6. Resolve exact product/variant membership and current eligibility.
7. Validate every line and stock value before any write.
8. Calculate authoritative subtotal and scoped promotion discount with
   `Decimal`.
9. Apply the approved zero delivery/tax baseline.
10. Create the order and item snapshots.
11. Decrement only authoritative stock and increment promotion usage.
12. Commit once and return the private confirmation URL.
13. Clear `bfCart` only after the browser receives confirmed success.

Any rejection or exception must leave no order, items, promo usage, or stock
change.

## Implemented structure and migration

- `store/forms.py` validates and normalizes customer details.
- `store/services/checkout.py` defines typed request/result objects, strict
  parsing, canonical fingerprints, catalog/variant resolution, promotion math,
  pricing serialization, deterministic locks, and the atomic create operation.
- `store/views.py` owns only JSON transport concerns and the stable HTTP
  envelope; both commerce responses and the checkout/confirmation pages are
  marked `no-store`.
- `store/static/store/js/checkout.js` owns quote/create calls, safe feedback,
  the session retry key, and confirmed-success navigation/clearing.
- `templates/store/checkout.html` retains the SOT field/layout structure and
  exposes named endpoint URLs, limits, CSRF, and signed-in identity defaults.
- `templates/store/order_confirmation.html` renders immutable item and money
  snapshots behind the number/token boundary.
- `store/0005_order_request_fingerprint.py` adds the 64-character hash field;
  it is applied to the active SQLite database and fresh test databases. The
  order-number generator now uses 12 random hexadecimal characters while
  remaining within its existing 24-character field, so no field migration was
  needed for that code-level collision-hardening change.

## Verification and limitations

The original Phase 4 closing suite passed 74 tests. Current regression coverage includes strict
media/JSON/schema/type/size limits, stale/tampered UUIDs, customer validation,
duplicate coalescing, line limits, database price authority, product and
variant stock authority, fixed/percentage scope and half-up rounding, promo
window/minimum/global/customer limits, quote non-mutation, authenticated
ownership, CSRF, private confirmations, idempotent replay/conflict, and forced
transaction rollback with no partial state.

All browser modules pass Node syntax parsing, static collection succeeds, and
all 21 SOT hashes plus exact derived CSS/image hashes still match. Phase 6 now
adds repeatable desktop/mobile Playwright checkout/admin journeys and four real
PostgreSQL multi-connection races covering idempotency, last-stock contention,
promotion limits, and duplicate cancellation. The local seed has no variants,
promos, or orders, so tests create isolated examples instead of publishing demo
commerce data.

## Current policy decisions

- Optional customer accounts and guest checkout.
- EGP.
- Cash on delivery initially.
- Explicit delivery/tax fields with zero defaults until rules are approved.
- Database-backed promotions; SOT promo codes are development-only.
- Private token confirmation instead of guessable number-only access.
- Variant stock is authoritative whenever active variants exist.
- Name/email/phone/address are required; city/notes are optional.
- Maximum 50 submitted lines and 99 units per normalized line.
- No stock reservation or order expiry occurs before the atomic commit.
- Quotes do not reserve stock and create always recalculates.
- Sequential permissioned lifecycle/payment graphs and one-time atomic
  pre-shipment cancellation/restock are active.
- The staff dashboard exposes only service-backed order-status actions;
  payment status is view-only and payment actions are not provisioned.
- Cancellation does not credit promotion usage; refund status records a refund
  completed outside the application.

## Deferred business decisions

- Nonzero delivery areas/fees and more granular address fields.
- Nonzero tax rules.
- Production promotion codes/campaign approval.
- A business-specific limit below the documented technical cart/value ceiling.
- Order expiry/reservation policy.
- Customer/admin email, SMS, or WhatsApp providers.
- Online payment provider and payment lifecycle.
- Automated refund execution (current status records an external/manual event).
- Final PII retention/request procedure and expanded account order-history
  features.
