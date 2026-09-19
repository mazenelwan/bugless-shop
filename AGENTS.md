# Bugless Fit Repository Guidance

## Product contract

- This is a Django e-commerce application for Bugless Fit.
- The completed standalone frontend files under `frontend/` are the visual and interaction source of truth:
  - `frontend/index.html`, `frontend/home.css`, `frontend/home.js`
  - `frontend/shop2.html`, `frontend/shop2.css`, `frontend/shop2 (4).js`
  - `frontend/product.html`, `frontend/product.css`, `frontend/product.js`
  - `frontend/checkout.html`, `frontend/checkout.css`, `frontend/checkout.js`
  - `frontend/contact.html`, `frontend/contact.css`, `frontend/contact.js`
  - `frontend/about.html`, `frontend/about.css`, `frontend/about.js`
- Preserve the existing page structure, classes, IDs, spacing, typography, colors, imagery, and responsive behavior when turning those pages into Django templates. Do not redesign the public UI unless the user explicitly requests it.
- Django and the database are authoritative for catalog data, availability, prices, promotions, order totals, and inventory. Never trust client-submitted names, prices, discounts, or totals.

## Architecture

- Django project: `buglessfit/`
- Store application: `store/`
- Django templates: `templates/store/`
- The untouched public frontend source lives in `frontend/`; keep it available as the design reference while integrating it into Django.
- The existing browser cart key is `bfCart`. Keep cart data compatible across Shop, Product, and Checkout pages.
- PostgreSQL is selected through `DATABASE_URL`; SQLite is the local development fallback.
- Products, orders, stock, promotions, and contact messages should remain manageable through Django admin.

## Context and documentation protocol

- Start every new implementation session with `docs/README.md`, followed by `docs/progress/README.md`.
- Read only the domain documents linked from `docs/README.md` that apply to the current task.
- Update `docs/progress/README.md` whenever a task changes status.
- Update the relevant domain document when a data contract, route, model, business rule, or known limitation changes.
- Record durable choices and their reasoning in `docs/decisions/README.md`; do not silently reverse an accepted decision.
- Documentation describes the repository but does not override the user's latest instruction or the frontend SOT.

## Implementation rules

- Prefer server-rendered Django templates with small, progressively enhanced JavaScript modules.
- Keep public routes named and linked with Django's `{% url %}` tag; keep assets linked with `{% static %}`.
- Validate all forms and JSON payloads on the server and return field-safe, user-readable errors.
- Create orders atomically. Lock purchased inventory rows, validate requested variants, calculate all money server-side, and decrement stock only after the complete order has validated.
- Do not expose project source, the SQLite database, environment files, or templates through Django static-file configuration.
- Add a migration for every model change. Do not edit an applied migration to represent a new schema change.

## Verification

Run these from the repository root:

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check
```

For catalog setup in a fresh local database:

```powershell
python manage.py migrate
python manage.py seed_catalog
```

Tests should cover both happy paths and rejection paths, especially invalid carts, stale prices, inactive products, stock limits, variant selection, promo validation, contact validation, duplicate submission, and order confirmation access.
