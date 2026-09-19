# Catalog

Last updated: 2026-09-16 (admin product CRUD)

## Current development seed

`python manage.py seed_catalog` parses the preserved
`frontend/product-data.js` and imports:

- 6 categories;
- 24 products, four in each category;
- 24 primary product images;
- 0 variants; and
- 0 promotions by default.

The category order is:

1. Men's Shirts
2. Jacket
3. Pants
4. T-Shirts
5. Polo
6. Shoes

Each product retains its authored within-category order. This data is the
development and visual-integration baseline, not approved production inventory.

## Seed behavior

- The command reads UTF-8 source from the immutable SOT directory.
- Parsing is limited to the authored five-value `rows` array and uses
  `ast.literal_eval`; arbitrary JavaScript is never executed.
- Missing, unparseable, or structurally invalid source data raises
  `CommandError`.
- The complete operation is atomic.
- Categories are updated by name, products by deterministic SKU, and their
  primary images by product/display order.
- Re-running updates imported fields without duplicating rows.
- Existing product UUIDs and nonblank generated slugs are preserved.
- The command does not delete catalog records that are absent from the SOT;
  destructive synchronization requires a separately approved policy.
- Every seeded variantless product starts with stock 10.

The optional command:

```powershell
python manage.py seed_catalog --with-demo-promotions
```

creates/updates and activates `SAVE10`, `SAVE20`, and `WELCOME50` for
development only. A normal seed never publishes those promotions.

## Product identity

- Database primary keys are internal implementation details.
- `Product.public_id` is the immutable UUID used in browser cart/API contracts.
- `ProductVariant.public_id` performs the same role for a selected variant.
- `Product.slug` is the readable detail URL.
- `Product.legacy_id` retains authored IDs such as `shirts-01` solely for
  import and permanent legacy redirects.
- SKU is a staff/business identifier; seed SKUs use the
  `BF-<UPPERCASE-LEGACY-ID>` form.

Names, card positions, prices, and slugs are not cart identity.

## Merchandising and visibility

- `Category.display_order` then category ID controls public category order.
- `Product.display_order` then product ID controls order inside its category.
- Both order fields are list-editable in Django admin.
- Public catalog selectors require both product and category to be active.
- Empty categories and categories with no matches are omitted from public
  results.
- A product detail route returns 404 for an inactive product or one in an
  inactive category.
- `featured` is modeled/admin-manageable but does not currently override the
  authored page order.

## Admin product management

The Django admin Product page is the catalog CRUD surface. Catalog Managers and
Store Managers can create, read, update, and delete products using the current
model fields. Ordered product images and product-specific variants remain
editable inlines on the same page, including add/change/delete operations.

Immutable product and variant public UUIDs and timestamps remain read-only.
Deleting a product cascades its live image/variant rows, while historical order
items retain immutable product/variant/name/SKU/option/money snapshots and use
nullable live references. For temporary unavailability, staff should normally
use `is_active` or `sold_out` rather than deleting the catalog record.

## Availability and variants

For products with no active variants:

```text
available stock = Product.stock
```

For products with active variants:

```text
available stock = sum(stock of active variants)
```

A product is displayed as available only when it and its category are active,
`sold_out` is false, and authoritative stock is positive. The Product page
renders distinct active color/size options and a JSON map of exact variant
combinations. Shop sends variant-backed products to Product detail instead of
adding an ambiguous line.

No global size/color list is invented. Product-specific variants must be
created in the database/admin when real inventory is supplied.

## Images and ratings

- Category and product images remain URL-compatible to reproduce the SOT.
- Each product may have multiple ordered images.
- The database enforces one primary image per product and a unique display
  position per product.
- Templates use the first ordered image only as a fallback when no primary row
  exists.
- SOT rating values are stored as optional decimal display metadata constrained
  from 0.0 through 5.0. They are not customer review aggregates.
- Managed uploads/object storage and a true review system are outside the
  current learning roadmap.

## Public search

`/search/?q=...` and `/shop/?q=...` perform case-insensitive database search
over:

- product name;
- product description;
- category name; and
- SKU.

Whitespace is trimmed. Django ORM parameterization handles the query safely.
JavaScript also performs an immediate filter over the already rendered result
set, but submitting the search always requests authoritative server results.

## Related products

Product detail asks for four active related products:

1. other products in the same category, in merchandising order;
2. if fewer than four exist, active products from the rest of the catalog in
   deterministic catalog order.

The current product and already selected same-category rows are excluded.

## Current local result

After the Phase 1/2 idempotency run:

```text
users=0
categories=6
products=24
images=24
variants=0
promotions=0
orders=0
contacts=0
```

## Deferred catalog decisions

- Production approval/replacement of the current 24 products.
- Real variant matrices, per-variant inventory, and SKU policy.
- Managed product media/object storage and remote-image fallbacks.
- Product review/rating ownership.
- Pagination and catalog scale thresholds.
- Whether `HomeContent` should eventually replace any authored marketing copy.
