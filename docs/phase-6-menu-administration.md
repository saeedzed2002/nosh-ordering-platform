# Phase 6 — Menu administration, price, options, and availability

Phase 6 makes the seeded catalog administrable without making the later
customer menu, dish-detail, cart, or checkout screens appear finished.

## Delivered workflow

| Surface | Behaviour |
| --- | --- |
| `/admin/menu` | A searchable, filterable service board with customer visibility and availability state, edit entry points, and one-click pause/resume actions. |
| `/admin/menu/new` | A guided four-step workflow: plate basics, price and service, choices and care, then a customer-card review. Each step blocks invalid continuation. |
| `/admin/menu/{slug}` | Reopens the same guided workflow with the current values and the latest recorded changes. |
| Categories | Administrators can safely hide or restore a category. Hiding excludes its published dishes from the public catalog and never deletes their records. |
| Featured placement | A published dish can be assigned to the existing `featured-dish` home-content placement. The public home API exposes its slug for the later customer-menu route. |
| Curated collections | Administrators can create and update ordered private or published collections from the menu desk. |

The route is restricted to `owner` and `manager`. `kitchen` receives `403`,
and no UI control attempts to bypass that server rule.

## Data rules

- A new menu item requires a category, image, price, location availability,
  name, URL slug, and customer description.
- The server rejects a discount greater than the base price. `display_order`
  cannot be negative.
- Option groups are typed as `choice`, `extra`, or `removal`. Required choices
  must have enough active options; maximum choices cannot exceed supplied
  options.
- Schedule state requires timezone-aware start and end timestamps, with an end
  after its start. The public catalog evaluates a schedule at read time: it is
  `available` only inside its window.
- A published item requires both a published category and published image.
  A published category with an image also requires that image to be published.
- Hiding published media that is currently used by a live menu item or category
  is rejected. Media usage lists now identify home, category, and menu use.
- `catalog_changes` records creation, updates, availability changes, category
  visibility changes, collection changes, and featured-placement changes with
  actor and snapshot metadata.

## API contract

| Route | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/admin/menu/setup` | `owner`, `manager` | Editing references: categories, allergens, media, locations, collections, and featured placement. |
| `GET/POST /api/v1/admin/menu` | `owner`, `manager` | Search the administrative board or create a full dish. |
| `GET/PUT /api/v1/admin/menu/{slug}` | `owner`, `manager` | Read or replace a complete dish including options, allergens, and availability. |
| `PATCH /api/v1/admin/menu/{slug}/availability` | `owner`, `manager` | Change one location’s state without overwriting dish content. |
| `POST/PUT /api/v1/admin/menu/categories...` | `owner`, `manager` | Create, update, hide, or restore categories. |
| `GET/POST/PUT /api/v1/admin/menu/collections...` | `owner`, `manager` | Read and maintain curated collections. |
| `GET/PUT /api/v1/admin/menu/featured` | `owner`, `manager` | Read or update featured-dish placement. |
| `GET /api/v1/catalog/menu-items` | Public | Published category/item data, ordered by category and item order, with actual availability, discounted price, option kind, and allergen information. |

## Migration and validation

Migration `20260921_02` adds the discount and item-order constraints, option
group kind, the catalogue-change ledger, and catalog-list index. It uses
Alembic batch operations so the test suite’s SQLite database and local
PostgreSQL use the same migration path.

The Phase 6 automated scenarios cover:

1. Owner creation of a published dish with image, price, required option, and
   allergen, followed by visibility through the public catalog API.
2. Fast pause and scheduled availability, including rejected incomplete
   schedules.
3. Role protection for the kitchen account.

## Deliberate boundary

This phase proves the data becomes public through the catalog API. It does not
replace the Phase 3 preview section with a customer `/menu` interface, and it
does not introduce a dish-detail route. Those user-facing discovery and
customisation screens remain Phase 7 and Phase 8 work.
