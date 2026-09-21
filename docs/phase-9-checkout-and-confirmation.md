# Phase 9 — Checkout and immutable order confirmation

Phase 9 converts the validated browser cart into a durable local-demo order.
It does not implement an external payment provider, a delivery partner,
inventory reservation, order operations, tracking, or customer accounts.

## Delivered customer flow

| Surface | Behaviour |
| --- | --- |
| Cart drawer | A server-quoted cart now links to `/checkout`. An empty or unquoted cart cannot place an order. |
| `/checkout` | Collects published location, pickup or delivery, immediate or scheduled timing, recipient details, delivery address when required, kitchen instructions, promotion code, and a labelled mock-payment outcome. |
| Payment simulation | The customer can deliberately simulate an approval or decline. No card number, cardholder name, account, processor, or money transfer exists in this project. A declined simulation writes no order. |
| `/orders/{publicReference}` | Reads a refresh-safe receipt with immutable items, selected options, totals, location, method, timing, and status event. Private recipient, address, and instruction snapshots are deliberately not returned by this public route. |

The local seed creates the active `WELCOME10` promotion: ten percent off a
qualifying order of at least `$20.00`. It is only an input hint in the browser;
the server validates its state, timing, threshold, and usage limit when the
order is created.

## Server-authoritative order transaction

`POST /api/v1/orders/checkout` accepts a cart draft and an idempotency key. It
does not trust a client-side item name, price, option copy, subtotal, promotion
result, or total.

Within one database transaction the service:

1. returns an earlier matching result when the same idempotency key and request
   fingerprint are replayed; a changed request with the same key is rejected;
2. confirms the published location and requested fulfilment capability;
3. runs the same published-catalog validation and quote logic used by the cart;
4. locks the selected promotion row while checking its state, window,
   minimum, and usage capacity;
5. writes the order, immutable item/price/option snapshots, recipient and
   fulfilment snapshots, payment outcome, and initial status event; and
6. increments promotion usage only with the successful order commit.

The order tables use foreign-key indexes for operational lookup and check
constraints for status, fulfilment method, currency, non-negative amounts, and
the total equation. Historical items keep their menu item identifier without a
foreign key so an administrative catalog deletion cannot invalidate a saved
receipt.

## Receipt privacy boundary

The route uses a non-sequential random reference such as `N-...`, but that is
not treated as access control. `GET /api/v1/orders/{publicReference}` returns
only customer-safe receipt data: line snapshots, totals, restaurant location,
method, timing, and status. Private recipient name, email, phone, delivery
address, and kitchen instructions stay in the durable internal snapshots and
are not serialized by this unauthenticated endpoint.

## Validation

Backend integration tests cover:

- server price and option snapshot creation;
- receipt stability after a live menu price change;
- replay of the same idempotency key without a second order or promotion use;
- declined mock payment without an order or promotion mutation; and
- the established cart option and availability checks shared by checkout.

Frontend lint, type-check, and production build confirm the compiled checkout
and receipt routes. Rendered browser QA against the existing Docker stack covers
cart-to-checkout navigation, the responsive checkout layout, successful local
mock payment, a refresh-safe receipt, redacted public receipt data, and the
recoverable declined-payment state.

## Deliberate boundary

An order begins as `submitted` or `scheduled`. Later phases own accepted,
preparing, ready, courier, delivery, cancellation, and support transitions.
This phase stores the extensible status vocabulary and event table but does not
pretend those operational flows, courier tracking, or customer account access
already exist.
