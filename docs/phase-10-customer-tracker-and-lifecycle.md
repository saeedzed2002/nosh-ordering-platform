# Phase 10 — Customer tracker and order lifecycle

Phase 10 turns the refresh-safe receipt route into a clear, customer-safe
tracker. It deliberately does not build the daily staff order desk, queues,
search, filters, online-order controls, or operational side panel; those are
Phase 11 work.

## Delivered customer tracker

`/orders/{publicReference}` now checks the order endpoint every `15` seconds
and has an explicit manual refresh action. It renders:

- the current status and a pickup- or delivery-specific progress sequence;
- a timestamped vertical event history;
- the immutable ordered items and totals;
- kitchen location, fictional local-demo restaurant contact, initial kitchen
  estimate, and pickup/delivery handoff information; and
- explicit `needs contact`, `declined`, and `cancelled` states with readable
  next-step guidance.

The motion on the active progress step respects `prefers-reduced-motion`.

The tracker is intentionally not a courier map. In particular, `Handed to
courier` records the kitchen handoff, while `Out for delivery` is a later
staff-recorded delivery state. Neither state claims live GPS, a courier
position, or a real delivery integration.

## Public response boundary

`GET /api/v1/orders/{publicReference}` remains unauthenticated only for the
local-demo receipt/tracker. It returns safe order snapshots, status events,
restaurant contact, preparation estimate, location, and restaurant handoff
instructions. Recipient name, email, phone, delivery address, and customer
instructions remain internal order snapshots and are not returned.

New orders snapshot the location preparation time and fictional restaurant
contact. Pre-Phase-10 orders fall back to their linked location so an ordinary
local upgrade does not make an existing receipt unreadable.

## Lifecycle guardrail

Phase 10 adds the protected integration seam that records status changes:

`POST /api/v1/admin/orders/{publicReference}/transitions`

Only server-authenticated `owner`, `manager`, or `kitchen` roles can use it.
The browser has no staff-transition UI in this phase. The endpoint is present
so the customer tracker can be verified against genuine staff-authored changes
before Phase 11 builds the staff desk.

The service locks the selected order row and permits only these normal paths:

| Fulfilment | Valid customer path |
| --- | --- |
| Pickup | `Submitted` → `Accepted` → `Preparing` → `Ready for pickup` → `Handed to customer` |
| Delivery | `Submitted` → `Accepted` → `Preparing` → `Ready for courier` → `Handed to courier` → `Out for delivery` → `Delivered` |
| Scheduled | `Scheduled` can enter `Accepted` or `Preparing` only when its preparation window opens. |

An active order may enter `Needs contact`, `Declined`, or `Cancelled` using a
controlled, customer-safe reason. Terminal statuses cannot change again;
invalid jumps return `409`. A transition stores its actor, UTC timestamp, and
server-generated customer-safe note in immutable event history. The public
tracker does not expose actor identity.

## Schema and validation

Migration `20260921_05` adds a required `locations.contact_phone` field with a
fictional local-demo default. The repeatable seed sets the same contact value.

Backend tests cover role protection, the complete delivery path, invalid-jump
rejection, controlled issue reasons, the scheduled preparation window, public
redaction, and persisted actor data. Frontend tests cover distinct pickup and
delivery progress paths plus the explicit no-live-map copy. Browser QA covers
desktop and `390 × 844` mobile tracker rendering, no horizontal overflow, and
an authenticated local staff transition reflected in the public tracker.

## Deliberate boundary

The tracker still uses a public reference for a local demo, not customer
authentication. It has no account order history, cancellation request flow,
real restaurant phone, SMS/email updates, payment provider, courier API, GPS,
or WebSocket. `15`-second polling is intentionally sufficient until measured
runtime need justifies a persistent connection.
