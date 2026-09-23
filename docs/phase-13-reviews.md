# Phase 13 — Eligible reviews and moderation

Reviews are tied to an immutable `order_item`, not a browser visit or public
order reference. A customer can create one review only when the item belongs to
their authenticated account and its order is `delivered`.

New feedback begins `pending`. The public dish API returns approved reviews
only. `Manager` and `Owner` moderate the protected `/admin/reviews` queue with
approve, reject, hide, and restore; reject/hide require an internal reason.
Customer contact details and internal reasons never appear publicly.

Migration `20260923_08` stores review eligibility, rating/text, moderation
state, moderation actor/time, and indexed public/moderation lookups.
