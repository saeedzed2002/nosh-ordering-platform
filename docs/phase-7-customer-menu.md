# Phase 7 — Customer menu and food discovery

Phase 7 replaces the browser-only seeded dish preview with published catalog
data. It deliberately stops before customization and cart work, which belong
to Phase 8.

## Delivered customer flow

| Route | Behaviour |
| --- | --- |
| `/menu` | Loads the published menu and default published location in parallel. It provides search, category, dietary, allergen-avoidance, availability, and sort controls. Active controls are represented in the URL. |
| `/menu/{slug}` | Reads one published dish directly. It shows price, availability, preparation time, dish/category images, ingredients, dietary tags, allergen notes, published option groups, and related dishes. |
| Home | Uses the published catalog for the live dish preview and links into the customer menu instead of rendering seeded browser menu records. |

Cards and details make an unavailable state explicit. There is no add-to-cart
control in this phase, so an unavailable dish cannot enter an order. The detail
route says why it cannot be added rather than hiding the dish or implying that
it is purchasable.

## API behaviour

`GET /api/v1/catalog/menu-items` now resolves availability against the first
published location when `location_slug` is absent. Supplying a published
`location_slug` retains the explicit-location behaviour. This gives the public
customer route a meaningful availability state without hard-coding a seed
location in the frontend.

`GET /api/v1/catalog/menu-items/{slug}` returns the same public, published-only
shape for a single dish. Missing, private, or hidden-category dishes return
`404`.

The existing catalog model currently supplies one primary dish image and, where
available, a category image. The detail interface presents those honestly as a
small image gallery. Nutrition is not modelled or seeded, so the interface
states that it is not published rather than inventing values.

## Interaction and resilience rules

- Search is deferred before filtering the card list so long menus do not make
  typing feel delayed.
- Dietary filters require every selected tag. Allergen filters exclude dishes
  containing any selected allergen.
- Filter/sort state uses query parameters, so a copied menu URL reproduces the
  current view.
- The route provides a skeleton while the catalog is loading, a retry state for
  a failed catalog request, and a clear-filters empty state.
- Filter updates use a short opacity transition; reduced-motion preferences are
  respected by the existing global interaction behaviour.

## Validation

Automated coverage includes the default-location availability resolution and
the published dish-detail route. Browser QA covers the live customer menu,
URL-preserved category filtering, unavailable dish detail, console health, and
desktop/mobile layout without horizontal overflow.

## Deliberate boundary

Phase 7 does not choose options, compute a cart total, persist a cart, collect
order notes, or create an order. Those actions require server-authoritative
pricing and are scheduled for Phase 8.
