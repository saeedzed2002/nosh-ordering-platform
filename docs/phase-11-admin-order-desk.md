# Phase 11 — Admin order desk

Phase 11 turns the existing protected lifecycle seam into a daily staff
workflow. It does not add customer accounts, real payment capture, courier
integrations, customer self-service cancellation, notifications, or live maps.

## Delivered workflow

`/admin/orders` presents counts and lists for these operational queues:

- `Needs approval`, `Scheduled`, `Active`, `Ready`, `Completed`, and `Archive`;
- free-text reference/customer search, fulfilment method, exact status,
  location, created-date range, and queue filters; and
- a side panel containing the customer's contact and delivery details, ordered
  choices, immutable allergen snapshots, kitchen notes, and the status-event
  timeline.

The order panel exposes only the next statuses permitted by the server. A
separate confirmation with a controlled reason is required for `Needs contact`,
`Declined`, and `Cancelled`. `Kitchen` can perform normal kitchen progression
but cannot decline or cancel an order; `Manager` and `Owner` can perform those
sensitive outcomes. The API repeats these checks, so hiding a browser button
does not create authorization.

## Protected API boundary

The staff desk uses authenticated routes only:

- `GET /api/v1/admin/orders` provides the filtered desk, queue counts, and
  location references;
- `GET /api/v1/admin/orders/{publicReference}` returns the private staff
  detail; and
- `POST /api/v1/admin/orders/{publicReference}/transitions` records a guarded
  lifecycle change.

Public `GET /api/v1/orders/{publicReference}` remains redacted. It never gains
the recipient email, phone, delivery address, kitchen instructions, or event
actor identity exposed to staff.

## Kitchen controls

`Manager` and `Owner` can save controls through:

`GET /api/v1/admin/orders/controls`

`PUT /api/v1/admin/orders/locations/{locationId}/controls`

For each location, the desk manages:

- online ordering `On`, `Timed pause`, or `Off`;
- a timezone-aware future end time for a timed pause;
- the preparation estimate used by later orders; and
- a demo limit for concurrent active orders.

The state and pause-window relationship are constrained in PostgreSQL by
migration `20260921_06`. The public location response states whether ordering
is currently available. The cart quote and checkout reject an `Off` or active
timed-pause location with `409`. Checkout locks its location row and counts
capacity-consuming active orders before it saves a new order, so concurrent
requests cannot both use the final capacity slot. Scheduled and terminal orders
do not consume that active-order capacity.

## Order history and care data

New checkout line snapshots retain the dish ingredients, dietary tags, selected
options, price, and known allergens. This allows the staff desk to show the
care data associated with the actual order even after a menu change. Older
local orders fall back to their linked menu item's current allergens so the
upgrade remains readable; the fallback is not presented as a historical
snapshot.

## Validation

Backend tests cover queue assignment and filters, staff-only private detail,
allergen snapshots, valid delivery progression, sensitive-role rejection,
online-ordering pause enforcement, and capacity rejection. Frontend checks
cover type checking, linting, production build, and the focused browser-unit
suite. Runtime migration and browser checks remain separate evidence.

## Deliberate boundary

This is a local operational desk, not a full dispatch platform. It has no
assignment algorithm, courier identity, live capacity forecasting, event
stream, SMS/email automation, payment refunds, customer account history, or
production audit-export facility. The capacity control is intentionally a
simple active-order limit for the local demo, not a staffing or kitchen-load
model.
