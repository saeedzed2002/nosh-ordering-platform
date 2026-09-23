# Phase 1: experience, content, and information architecture

## Status and decision record

This document turns the product intent in the roadmap into an implementation
contract for the next phases. It describes planned behavior; it does not claim
that the routes, accounts, ordering, administration, or data below exist in
the current Phase 0 application.

| Decision | Locked initial choice | Consequence |
| --- | --- | --- |
| Customer language | English, left-to-right | All Phase 2 components and Phase 3 customer copy are designed and tested in LTR. Persian is a later product decision that requires a complete RTL pass, not right-aligned English UI. |
| Brand and menu | Nosh Kitchen & Delivery; contemporary Levantine grill | Food, imagery, editorial voice, and seed data share one coherent single-restaurant identity. |
| Location model | One fictional location: Nosh Kitchen — Market Quarter | Customer selection is retained in the journey so a later additional location does not require a checkout redesign. |
| Payment, courier, and communication | Local simulation only | The product never accepts card details, sends messages, renders a map, or represents a courier location as live. |
| Customer identity | Optional until the account phase | A guest can complete the mock ordering journey in Phase 9. Persisted favorites, addresses, history, reordering, and review authoring require an authenticated customer in Phase 12 or 13. |

## Product vocabulary

Use these terms consistently in customer copy, admin copy, API fields, and
tests. Avoid developer vocabulary such as "record", "payload", or "mutation"
in the product UI.

| Term | Customer meaning | Admin meaning |
| --- | --- | --- |
| dish | A food item that can be customised and ordered. | The menu item being created, priced, published, hidden, or updated. |
| collection | A small curated group, such as Kitchen favourites. | A hand-picked placement of existing dishes; it does not change a dish's category. |
| unavailable | A dish cannot be ordered now. | A reversible operational state; it is preferred over deletion. |
| fulfilment | Pickup or delivery. | The method and preparation context assigned to an order. |
| order reference | A shareable, non-sequential identifier shown after checkout. | A lookup reference; it is not a customer secret or an authorization mechanism. |
| order update | A time-stamped change in the order journey. | A valid, attributable status transition with an optional concise note. |
| online ordering | Whether the restaurant accepts new orders. | On, paused until a defined time, or off. |
| mock payment | A clearly simulated checkout result. | Never a payment provider integration or stored card data. |

## Customer journey contract

### Entry, discovery, and menu

| Entry point | Customer action | Destination and result | Failure or unavailable state |
| --- | --- | --- | --- |
| Home | Select **View menu** or a featured collection. | `/menu`, optionally with a category or collection filter; the chosen context is visible. | Show a retryable menu-unavailable panel. The home page remains usable and never invents menu results. |
| Home | Select **Pickup** or **Delivery**. | Sets a provisional fulfilment preference for the next menu and cart steps. | If the selected method is unavailable, explain the reason and show the available method; do not silently change the choice. |
| Global navigation | Select **Menu**, **Locations**, or **About**. | `/menu`, `/locations`, or `/about`; the target page has one clear primary purpose. | A broken or missing route returns a readable not-found page with a route back to the menu. |
| Menu | Search, filter, sort, or clear filters. | `/menu` preserves meaningful filters in the URL so the view can be bookmarked and refreshed. | An empty result says what was searched or filtered and provides **Clear filters**. API failure provides **Try again**. |
| Menu | Select an available dish. | `/menu/:dishSlug` shows price, image, description, ingredients, dietary tags, allergens, options, and preparation information when supplied. | A retired slug uses a readable not-found page. An unavailable dish stays inspectable but cannot be added. |
| Dish detail | Open allergen information. | The information is adjacent to ordering controls and describes known declared allergens only. | Missing information is shown as **Allergen information is not available for this dish**; it is never guessed. |

### Customisation, cart, and checkout

| Entry point | Customer action | Destination and result | Failure or unavailable state |
| --- | --- | --- | --- |
| Dish detail | Choose options, quantity, and a short kitchen note, then select **Add to cart**. | A valid configured dish is added to `/cart`; the cart count and concise feedback update. | Required choices, selection limits, and note length are explained beside the relevant field. A server rejection preserves the choices and shows a retryable message. |
| Cart | Change quantity, edit a dish, or remove a dish. | Totals are recalculated from server-validated prices. **Edit** returns to the relevant dish configuration. | If price, options, or availability changed, identify the affected line and require customer confirmation before checkout. |
| Cart | Select **Checkout**. | `/checkout` starts with the selected fulfilment method and current cart validation. | An empty or invalid cart remains on `/cart` with an explanation and a menu route. |
| Checkout | Choose location, pickup/delivery, immediate/scheduled time, recipient details, address when needed, and instructions. | The review step shows the selected details and a transparent item, discount, delivery, and total breakdown. | Field errors are specific, announced accessibly, and do not clear completed fields. An unavailable time or capacity conflict offers a new valid choice. |
| Checkout review | Confirm the explicitly labelled mock payment. | A successful idempotent order creation redirects to `/orders/:publicReference`. | A simulated failure explains that no order was created; a retry uses the same idempotency key until the outcome is known. |

### Confirmation, tracking, and returning customers

| Entry point | Customer action | Destination and result | Failure or unavailable state |
| --- | --- | --- | --- |
| Confirmation | Review receipt or continue tracking. | `/orders/:publicReference` shows ordered-item snapshots, fulfilment instructions, estimated time, and an immutable timeline. | An unknown reference provides a not-found state. Access rules never reveal another customer’s private details. |
| Tracking | Refresh or wait for an update. | Light polling refreshes order state without claiming live GPS. Pickup and delivery labels follow the status model in the roadmap. | A temporary refresh failure preserves the last confirmed state, states that it may be out of date, and exposes **Try again**. |
| Account (Phase 12) | Sign in, open history, save an address, add a favorite, or reorder. | `/account/*` actions affect only the signed-in customer. Reorder returns a newly validated cart, never a copied historic total. | Authentication expiry returns to sign-in while preserving the intended safe destination. Ownership failures never disclose whether another customer’s object exists. |
| Completed order (Phase 13) | Select **Add a review** below an eligible menu card or dish page, then write one review. | The authenticated customer sees the action only for their completed, unreviewed dish. The `/account#reviews` section accepts one review per completed order item: `delivered` for delivery or `handed_to_customer` for pickup. It submits feedback to moderation. | Guests, other customers, ineligible items, and duplicate reviews see no authoring action; server checks still prevent invalid writes. |

## Order-language and transition contract

Customer labels must describe what has happened, rather than an internal queue
name. The API may use stable machine values, but the UI presents the following
language.

| Fulfilment | Customer state | Plain-language explanation | Next valid state |
| --- | --- | --- | --- |
| Pickup or delivery | Submitted | The restaurant has received the order and will review it. | Accepted, Declined, Needs contact, Cancelled |
| Pickup or delivery | Accepted | The restaurant accepted the order. | Preparing, Cancelled, Needs contact |
| Pickup or delivery | Preparing | The kitchen is making the order. | Ready for pickup or Ready for courier |
| Pickup | Ready for pickup | The order is ready to collect at Nosh Kitchen — Market Quarter. | Handed to customer |
| Delivery | Ready for courier | The order is packed and waiting for courier handoff. | Handed to courier |
| Delivery | Handed to courier | The restaurant recorded handoff to a courier. This is not a live-location signal. | Out for delivery |
| Delivery | Out for delivery | The restaurant recorded that the courier left with the order. This is not a live-location signal. | Delivered |
| Pickup | Handed to customer | The restaurant recorded collection. | Terminal |
| Delivery | Delivered | The restaurant recorded delivery. | Terminal |
| Pickup or delivery | Declined, Cancelled, or Needs contact | The reason and a clear recovery path are shown. | Terminal or administrator-approved recovery only |

Scheduled orders retain a scheduled time and become eligible for Accepted or
Preparing only in the defined operational window. An admin cannot skip a
customer-visible transition. Every accepted transition appends an immutable
event with time, actor, and optional note.

## Planned route map

Routes marked **planned** are contracts for later implementation and must not
be linked as working product features before their phase is complete.

| Area | Route | Phase | Primary purpose |
| --- | --- | --- | --- |
| Customer | `/` | 3 | Editorial entry and order discovery. |
| Customer | `/menu` | 7 | Searchable, filterable menu discovery. |
| Customer | `/menu/:dishSlug` | 7-8 | Dish information and customisation. |
| Customer | `/cart` | 8 | Trustworthy editable cart. |
| Customer | `/checkout` | 9 | Mock-order checkout and confirmation handoff. |
| Customer | `/orders/:publicReference` | 9-10 | Confirmation, receipt, and tracker. |
| Customer | `/locations` | 3 | Location, hours, and fulfilment information. |
| Customer | `/about` | 3 | Restaurant story and product boundary. |
| Customer | `/account/*` | 12-13 | Sign-in, profile, addresses, history, favorites, and reviews. |
| Admin | `/admin/sign-in` | 5 | Dedicated administrator sign-in. |
| Admin | `/admin` | 5, 11 | Daily task desk and actionable counts. |
| Admin | `/admin/home` | 5 | Draft, preview, and publish home content. |
| Admin | `/admin/media` | 5 | Media library and safe image authoring. |
| Admin | `/admin/menu` | 6 | Menu, category, option, price, and availability management. |
| Admin | `/admin/orders` | 11 | Operational order queues and guarded transitions. |
| Admin | `/admin/reviews` | 13 | Review moderation queue. |
| Admin | `/admin/promotions`, `/admin/reports`, `/admin/settings`, `/admin/customers`, `/admin/audit-log` | 14 | Remaining operational administration. |

## Administrator workflow contract

### Add a dish

1. The administrator selects **Add a dish** from `/admin` or `/admin/menu`.
2. The guided editor collects basic details, category, price, image, dietary
   tags, allergens, option groups, and availability in recognisable steps.
3. Each step validates only its own required information. The card preview
   always identifies draft status.
4. **Save draft** retains private work. **Preview** shows the public result
   without publishing. **Publish** requires an explicit final confirmation.
5. A success state identifies the dish and gives a route to view it in the
   menu. Validation, upload, or concurrent-edit failures retain entered data
   and explain the specific corrective action.

### Update price or availability

1. The administrator opens a dish from `/admin/menu`.
2. A price change requires a positive currency amount and a reason suitable
   for the audit log. Availability uses the explicit choices **Available**,
   **Temporarily unavailable**, or a schedule.
3. The result states when the public menu will reflect the change. Existing
   order snapshots are never altered.
4. A conflicting update shows the newer value and allows a deliberate reload;
   it never overwrites silently.

### Upload or replace an image

1. The administrator starts in `/admin/media` or the dish/home editor.
2. The product validates supported image type and size before accepting the
   file. The author supplies alt text, focal point, source, and credit where
   relevant.
3. The author can preview, crop, reorder, replace, or return to the previous
   asset. Replacement shows all current usages before publication.
4. The system never declare an asset as original or licensed without supplied
   evidence. Invalid files leave the published asset unchanged and show the
   accepted file requirements.

### Pause online ordering

1. The administrator selects **Pause online ordering** from `/admin` or
   `/admin/settings`.
2. The control shows **On**, **Pause until**, and **Off**, plus a customer
   message preview. Pausing requires a specific end time.
3. A confirmation writes an audit event and updates the customer menu and
   checkout availability state.
4. Existing orders remain manageable. A failed update preserves the last
   confirmed availability state and requires an explicit retry.

### Process a new order

1. The administrator opens the **Needs approval** queue at `/admin/orders`.
2. The side panel shows customer details appropriate to the role, items,
   allergens, notes, fulfilment, required time, payment-simulation label, and
   timeline.
3. Only valid next actions appear. Each change requires a readable result,
   records the actor and time, and refreshes the customer tracker through
   polling.
4. Decline, cancellation, or needs-contact paths require a customer-safe
   reason. Invalid transitions, stale queue data, and server failure leave the
   order in its last confirmed state.

## Roles and authorization boundaries

| Role | Customer capabilities | Admin capabilities | Server rule |
| --- | --- | --- | --- |
| Guest | Browse public content; build a local cart; complete the permitted mock checkout flow. | None. | Cannot access account data, favorites, saved addresses, or admin routes. |
| Customer | Own profile, addresses, favorites, orders, eligible reviews, and reorder flow. | None. | Object ownership is enforced server-side for every private object. |
| Kitchen | None beyond any future staff-visible order context. | View operational order details and perform only assigned valid kitchen transitions. | Cannot publish content, alter prices, manage roles, or view unrelated customer data. |
| Manager | None by default. | Manage content, media, menu, availability, promotions, reviews, reports, and assigned order work. | Cannot manage owner roles or bypass audit logging. |
| Owner | None by default. | Full local-demo administration, including manager and kitchen access management. | Sensitive writes still require audit events and protected API authorization. |

Frontend route guards improve usability only. They are never treated as
authorization. The backend remains the authority for roles, ownership, totals,
availability, promotion validation, and state transitions.

## Customer-facing error copy

| Situation | Required message | Recovery action |
| --- | --- | --- |
| Menu data cannot load | **We could not load the menu. Please try again.** | Retry without losing current URL filters. |
| No matching dishes | **No dishes match those filters.** | Clear filters. |
| Dish became unavailable | **This dish is not available right now.** | Return to the menu or choose a replacement. |
| Required customisation missing | **Choose an option before adding this dish.** | Move focus to the relevant option group. |
| Cart changed | **Your cart was updated because a price or option changed.** | Review the highlighted lines before checkout. |
| Ordering paused | **Online ordering is paused until [local time].** | Show the next available time or alternative fulfilment when known. |
| Capacity or time unavailable | **That time is no longer available. Choose another time.** | Keep the form values and present valid options. |
| Mock payment failure | **This simulated payment did not create an order.** | Retry safely or return to the cart. |
| Tracker refresh failed | **This order may have an update. Try refreshing.** | Preserve last confirmed event and retry. |
| Unauthorized route | **Sign in to continue.** | Sign in and return to the requested safe route. |
| Not found | **We could not find that page or order.** | Return to menu or account, without leaking private data. |

## Content inventory

| Content group | Required fields | Authoring state | Public placement |
| --- | --- | --- | --- |
| Hero | Eyebrow, heading, supporting copy, primary action, image, image alt text, focal point, credit/source | Draft, preview, published | Home hero |
| Featured dish | Existing dish reference, label, short editorial copy, image placement | Draft, preview, published | Home and collection surfaces |
| Collections | Name, slug, description, ordered dish references, active state | Draft, preview, published | Home and menu discovery |
| Kitchen story | Heading, short body, image, alt text, credit/source | Draft, preview, published | Home and About |
| Location | Name, fictional address text, hours, phone placeholder, pickup instructions, delivery area copy, fulfilment methods | Draft, preview, published | Locations, checkout, tracking |
| Promotion | Code, label, description, value type/value, minimum order, valid window, usage limit, active state | Draft, preview, active | Home, menu, checkout when backend-valid |
| Dish | Name, slug, category, description, image, alt text, base price, tags, allergens, ingredients, options, availability | Draft, preview, published/hidden | Menu, dish detail, collections |
| Operational message | Online-ordering state, pause end time, customer-safe explanation | Confirmed active state | Menu, cart, checkout |

Every visual asset needs meaningful alt text. Decorative images use an empty
alt value only when adjacent text already provides the same information. No
asset is assumed to be licensed, original, or publishable merely because it is
present in local storage.

## Seed-data plan

These are deterministic future seed requirements for Phase 4. They establish a
useful demo data set without implying real orders, reviews, or restaurant
operations.

| Dataset | Planned content |
| --- | --- |
| Location | One fictional location, `market-quarter`, with pickup and simulated delivery, defined opening hours, a preparation-time default, and a demo capacity. |
| Categories | `Fire & Grill`, `Grain & Greens`, `Handhelds`, `Sides`, `Sweet Finish`, and `Drinks`, each with a stable display order. |
| Dishes | Sixteen dishes: four grill dishes, three bowls/salads, three handhelds, three sides, two desserts, and one drink. Each includes a price, description, image metadata, availability, at least one useful tag where applicable, and declared allergens. |
| Options | Required protein or base choices where appropriate; optional sauce, spice, side, extra-protein, and removal choices with explicit minimum, maximum, and price deltas. |
| Allergens and tags | Declared wheat/gluten, sesame, dairy, egg, soy, nuts, and peanut data where applicable; vegetarian, vegan, halal-style, spicy, and gluten-aware tags only when each declaration is supported by seed attributes. |
| Collections | `Kitchen favourites`, `Bright lunch`, and `Weekend slow-down`, each containing ordered existing dishes rather than duplicated food data. |
| Media | Hero, kitchen-story, location, category, and dish assets with source, alt text, focal point, usage references, and publication state. Local generated development assets stay explicitly labelled as such. |
| Home content | One hero, one featured-dish placement, one story block, one location callout, and at most one active demo promotion placement. |
| Users and roles | Owner, manager, kitchen, and two customer identities using non-secret deterministic seed identifiers. Local credentials are introduced only with the authentication implementation and never committed as a production secret. |
| Orders | A compact, clearly fictional distribution of pickup and delivery orders across submitted, active, ready, completed, declined, cancelled, and needs-contact states; each stores immutable snapshots and timeline events. |
| Reviews and promotions | At least one completed-order item eligible for a future review test, plus approved, pending, and hidden review states. One backend-validated demo promotion exercises valid, expired, minimum-order, and usage-limit paths. |

## Phase 1 acceptance trace

| Acceptance requirement | Evidence in this document |
| --- | --- |
| Every primary action has a destination, result, and failure state. | Customer journey and administrator workflow contracts. |
| Customer and administrator workflows are defined before UI expansion. | Journey, route map, operational workflows, and role boundaries. |
| Language and RTL/LTR behavior are explicit. | Decision record locks English LTR and defines the required condition for future RTL work. |
| Terminology and customer-facing errors are consistent. | Product vocabulary, order-language contract, and error-copy table. |
| Future data has a defined, realistic demo shape. | Content inventory and deterministic seed-data plan. |
| No decorative action is left ambiguous. | Every current or planned primary action is tied to a stated route, outcome, and failure/recovery path. |
