# Phase 14 — Operations, reports, and audit history

The protected `/api/v1/admin/operations` API supports the local restaurant
workflow without database or developer tools.

## Access boundaries

- `Manager` and `Owner` can manage promotions, restaurant settings, view
  customer summaries, and run reports.
- Only `Owner` can activate or deactivate a customer account and read the
  audit history.
- Customer summaries expose the account name, email, active state, order count,
  and up to 25 order summaries. They never expose passwords, authentication
  tokens, saved addresses, payment snapshots, or delivery details.

## Reporting contract

Reports are computed from orders in the requested inclusive date range. Demo
revenue and average order value exclude `declined` and `cancelled` orders.
Popular-food revenue uses the immutable order-line snapshot. Promotion use uses
the order's saved promotion snapshot, so a later promotion edit does not alter
historical reporting. Review moderation is grouped by its current status for
reviews created in the range.

## Audit contract

Migration `20260923_09` adds `audit_logs`. New sensitive operational writes are
recorded atomically with their source write: promotions, restaurant settings,
customer account state, order-desk controls, staff order transitions, and
review moderation. Existing home-content revisions and menu changes are also
mirrored into the central timeline. The records retain actor, time, target,
action, and safe before/after metadata; passwords, authentication tokens,
addresses, and payment details are intentionally absent.
