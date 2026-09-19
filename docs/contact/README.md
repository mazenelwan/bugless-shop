# Contact Domain

Last updated: 2026-09-16 (read-only contact dashboard)

## Phase 2 integration

`/contact/` now renders `templates/store/contact.html` with the exact derived
`store/css/contact.css`, the common named-route header/footer, the authored
business-detail cards, contact fields, and Google Map.

The derived form:

- posts to the named `store:contact` route instead of nonexistent
  `contact-mail.php`;
- includes a Django CSRF token;
- preserves the authored field names: `name`, `email`, `phone`, `subject`,
  and `message`; and
- uses POST/redirect/GET after the current successful write.

The page and route shell were completed in Phase 2; Phase 5 completed the
submission and staff workflow described below.

## Current persistence

`ContactMessage` stores:

- immutable unique submission UUID and semantic request fingerprint;
- name;
- email;
- optional phone;
- optional subject;
- message body;
- workflow status: new, read, replied, or archived; and
- created/updated timestamps.

Messages are searchable/filterable in Django admin. Submitted content, status,
and audit events are view-only; the dashboard exposes no add, edit, delete, or
workflow action.

## Frozen Phase 5 submission contract

- `ContactForm` owns normalization and safe errors. Name (160), valid
  case-folded email (254), and a nonblank message (5,000) are required; phone
  (40) and subject (200) are optional. Optional phone values use the checkout
  punctuation rule and contain 7-15 digits.
- The encoded request body is limited to `CONTACT_MAX_BODY_BYTES` (16,384 by
  default). Oversize requests are rejected without persistence.
- Each rendered form contains a UUID `submission_id`. Its database uniqueness
  plus a SHA-256 fingerprint of normalized semantics makes a double click or
  network replay return the same successful outcome while persisting/notifying
  exactly once; changed reuse returns a safe conflict without mutation.
- An invisible `website` honeypot rejects automated fills. Valid new attempts
  also consume configurable direct-peer-IP and normalized-email cache counters
  (`CONTACT_RATE_LIMIT=5`, `CONTACT_RATE_LIMIT_WINDOW=300` by default). Cache
  keys contain only salted HMAC digests; cache failure is logged without PII
  and fails open so a cache outage does not lose legitimate contact requests.
- Invalid submissions render the authored page with escaped retained values and
  field/non-field errors. Success and idempotent replay both use
  POST/redirect/GET plus Django message feedback.
- CSRF remains mandatory. Raw POST data and message bodies are never logged.

## Persistence, notifications, and workflow

`ContactMessage.submission_id` is immutable and unique. Each new message gets
an immutable submitted audit event. The audited workflow service retains its
validated new/read/replied/archived state graph for domain compatibility, but
the simplified dashboard does not expose it and the standard staff groups are
not provisioned `store.manage_contactmessage`.

When `CONTACT_NOTIFICATION_EMAIL` is nonblank, a provider-neutral Django email
is scheduled after the message transaction commits. Success/failure is audited;
failure is logged by row ID only and cannot roll back or delete the message.
No visitor acknowledgement is sent.

Contact fields, submission ID, timestamps, events, and status are read-only in
admin. Admin add/change/delete and all contact workflow actions are disabled.

## Retention boundary

The current enforced policy is a retention hold: there is no automatic delete,
anonymize, or bulk-export path until a business/legal period and a verified
data-request procedure are approved. Access is permission-scoped and audit rows
contain no submitted content. No production notification provider or final
legal retention workflow will be selected for this learning-only project;
those defaults must be reconsidered before any broader use.
