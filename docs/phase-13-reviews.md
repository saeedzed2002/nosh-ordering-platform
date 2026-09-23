# Phase 13 — Eligible reviews and moderation

Reviews are tied to an immutable `order_item`, not a browser visit or public
order reference. A customer can create one review only when the item belongs to
their authenticated account and its order is complete: `delivered` for delivery
or `handed_to_customer` for pickup.

New feedback begins `pending`. The public dish API returns approved reviews
only. `Manager` and `Owner` moderate the protected `/admin/reviews` queue with
approve, reject, hide, and restore; reject/hide require an internal reason.
Customer contact details and internal reasons never appear publicly.

The authenticated account endpoint `/api/v1/account/reviews/eligible-menu-items`
returns only menu slugs with at least one customer-owned completed order item
that has no review. The customer UI uses this result to show `Add a review`
below eligible menu cards and on the matching dish page; guests, other
customers, incomplete orders, and already-reviewed items see no action.

Migration `20260923_08` stores review eligibility, rating/text, moderation
state, moderation actor/time, and indexed public/moderation lookups.
