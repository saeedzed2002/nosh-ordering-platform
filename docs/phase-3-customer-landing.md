# Phase 3: Dynamic customer landing page

## Scope

Phase 3 turns the Phase 2 component foundation into the first reviewable
customer experience. It adds an editorial home page, local preview menu data,
category discovery, a page-session cart, a sticky navigation bar, and clear
movement between the hero, menu preview, and cart drawer.

The experience remains a local product demonstration. It does not claim live
menu availability, a payment provider, delivery dispatch, an account, or a
persisted order. Those require backend rules and arrive in later phases.

## Customer route

1. The hero moves a visitor to `#menu` or the kitchen story without a hidden
   route change.
2. Category controls filter the visible preview dishes from one deterministic
   client-side data source.
3. Available dishes add to a page-session cart. Unavailable dishes remain
   visibly unavailable and cannot be added.
4. The sticky cart control exposes the count and opens a focus-managed drawer.
5. Quantity changes recalculate the local subtotal. Decreasing an item to zero
   removes it. The drawer states that it is not checkout or persisted order
   data.

## Data and visual assets

`frontend/src/data/customerPreview.ts` owns the intentional preview content:
categories, dishes, kitchen moments, and benefit copy. Prices are integer cents
and are only formatted at the presentation boundary. This avoids treating a
formatted currency string as a business value.

`frontend/src/assets/nosh-seasonal-spread.webp` is a local generated food image
used in the flatbread, promotion, and seasonal preview treatment. It contains
no text, logos, people, or claims about an actual restaurant dish. The existing
local hero image is retained as `nosh-hero-food.webp`, a compressed development
visual asset. Neither asset is evidence
of production photography, live inventory, or an operating venue.

Both delivered images retain their `1536×1024` visual dimensions while reducing
the customer bundle's food-image payload from `5.64 MB` of PNG sources to
`451 KB` of WebP files (about `92%` smaller). The output was visually reviewed
after conversion rather than assuming a file extension alone proves quality.

## Accessibility and responsive behavior

- The page keeps a skip link, semantic landmarks, labelled navigation, and
  text alternatives for meaningful food images.
- Cart actions announce their state through an accessible label; unavailable
  dish actions are native disabled buttons.
- The cart uses the Phase 2 Radix-backed drawer, including focus management and
  a keyboard dismiss path.
- Category and fulfilment controls are native toggle buttons with explicit
  pressed state rather than an incomplete custom radio implementation.
- The header becomes a two-row mobile control surface, the primary menu action
  remains visible, category cards become horizontally usable, and large content
  sections collapse intentionally.
- Motion remains within the Phase 2 reduced-motion contract. The landing adds
  no animation that conveys an order, payment, or delivery result.

## Acceptance trace

| Phase acceptance requirement | Evidence |
| --- | --- |
| Editorial hero and direct action | Hero, selected fulfilment state, `#menu` action, and image treatment in `App.tsx`. |
| Discovery and landing sections | Category rail, featured dishes, promotion, kitchen story, benefits, location, and footer. |
| Sticky navigation and seeded cart | `customerPreview.ts`, sticky header, count, local subtotal, and quantity controls. |
| Clear home-to-menu-to-cart route | Hero/menu anchors, add-to-cart feedback, and focus-managed cart drawer. |
| Intentional mobile behavior | CSS breakpoints plus a `375×812` browser emulation with no horizontal overflow. |

## Deliberate boundaries

- State is intentionally limited to the current page session. Refreshing clears
  the preview cart.
- There is no payment, order submission, confirmation number, map request, or
  delivery tracking implementation in this phase.
- The `Local API ready` footer state proves only the existing local readiness
  endpoint; it is not a claim that the menu or cart is backend-connected.
