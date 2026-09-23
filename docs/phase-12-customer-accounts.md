# Phase 12 — Customer accounts, history, favorites, and reorder

Phase 12 reduces friction for a returning customer without turning a public
order reference into authorization. It adds local customer identity and owned
account data; it does not add password recovery, email verification, customer
support tooling, real payment, or a way to claim older guest orders.

## Delivered customer flow

`/account/sign-up` creates a `customer` role account and signs it in. The
separate `/account/sign-in` path accepts only that role, while existing
`/admin/sign-in` continues to accept staff roles only. Customer tokens refresh
through the existing local JWT lifecycle and a protected route preserves a
safe local destination after sign-in.

`/account` provides:

- profile name and email editing;
- labelled saved addresses, exactly one default address when any address
  exists, and address removal;
- favorites saved from a published dish detail page;
- a customer-owned order history with the public receipt link; and
- a `Reorder` action that returns an editable current cart and opens checkout
  at the original kitchen location.

Checkout remains guest-capable. When it receives a valid customer bearer token,
it assigns the new order to that account, pre-fills the name/email, and offers
the account's saved addresses. The public receipt remains redacted and does
not reveal `customer_id` or private contact data.

## Server ownership and data rules

Migration `20260923_07` adds nullable `orders.customer_id`,
`customer_addresses`, and `customer_favorites`. Older guest orders remain
unowned. A partial unique index permits only one default address per customer;
address changes lock the customer row before changing the default state.

All `/api/v1/account/*` routes require the server-side `customer` role. Each
address, favorite, history, and reorder lookup filters by the authenticated
`user_id` or `customer_id`. A foreign address, favorite, or order receives the
same generic `404` as a missing account object, avoiding an ownership oracle.

`POST /api/v1/orders/checkout` accepts an optional customer token. A staff
token is rejected, and idempotency replay additionally requires the same order
owner, so a guest and a customer cannot share a checkout key.

## Reorder validation

`POST /api/v1/account/orders/{publicReference}/reorder` does not copy the
historic subtotal, promotion, total, or payment outcome. It reconstructs cart
lines from the immutable order-item snapshot, locks the current published
location, and calls the current `quote_cart` service. The service checks:

1. online ordering is currently on and the location is published;
2. every dish and category is still published;
3. every saved choice still exists and is available;
4. every current option minimum/maximum still accepts the selection;
5. every dish is currently available for that location; and
6. the current menu price and currency.

If any rule changed, the route returns the existing server validation error and
does not restore a cart. A successful response has current quote data and
editable lines only; checkout independently validates the final request again.

## Validation evidence

Backend integration tests cover customer registration, role separation,
profile updates, default-address promotion, address/favorite ownership,
customer-owned checkout, cross-customer idempotency rejection, order history,
foreign reorder rejection, and a changed current menu price on reorder.
Frontend checks cover lint, type-check, production build, and the existing
browser-unit suite. Runtime verification applied migration `20260923_07` to
the existing local PostgreSQL stack, confirmed health and OpenAPI route
exposure, and browser-checked the responsive sign-in/sign-up surfaces without
entering credentials.
