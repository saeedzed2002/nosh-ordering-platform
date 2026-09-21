# Phase 8 — Food customization and trustworthy cart

Phase 8 turns the published dish detail into a safe local ordering draft. It
does not create an order or begin checkout; those remain Phase 9 work.

## Delivered customer flow

| Surface | Behaviour |
| --- | --- |
| `/menu/{slug}` | Shows required and optional option groups, their selection limits, quantity, and an optional kitchen note. The immediate price preview updates as the customer makes valid choices. |
| Header cart | Shows the quantity of saved local cart items and opens a focus-managed cart drawer. |
| Cart drawer | Shows the server-quoted price, selected choices, kitchen note, editable quantity, removal, compatible dish suggestions, and a clear Phase 9 checkout boundary. |

Unavailable dishes remain readable, but their configuration fields and add
action are disabled. A missing required choice is explained next to the group;
the browser also prevents a choice above the configured maximum.

## Server-authoritative quote

`POST /api/v1/catalog/cart/quote` validates an ephemeral cart draft against the
current published catalog. It does not write an order or reserve inventory.

For every line, the endpoint verifies that:

- the dish and its category are still published;
- the dish is currently available at the default published location;
- every selected option belongs to that dish and is still available;
- each option group meets its configured minimum and maximum selection count;
- quantity is between `1` and `20`; and
- all lines use the same currency.

The response returns normalized kitchen choices, a current unit price, each
line total, and the current subtotal. The client may show an immediate preview,
but only retains a newly added or edited line after this endpoint succeeds.

## Local-cart contract

The browser persists only a versioned draft at
`nosh.customer-cart.v1`. It stores the client line identifier, dish slug,
option identifiers, quantity, and optional note — never a trusted price or
published product copy. On reload, the cart asks the server for a fresh quote.
If a dish, option, or availability state has changed, the drawer preserves the
draft for review and offers removal rather than presenting a stale total.

## Validation

Backend tests cover a valid quoted extra, required-choice rejection,
maximum-choice rejection, and the unavailable-dish boundary. Frontend unit
tests cover required-choice handling and the immediate price preview. Browser
QA covers the required-choice message, preview update, successful quoted add,
cart drawer, reload persistence, unavailable action, desktop/mobile layout,
and console health.

## Deliberate boundary

The cart has no checkout route, fulfillment selection, customer identity,
payment, order record, inventory reservation, or delivery integration. A cart
quote is not an order and has no transactional side effect.
