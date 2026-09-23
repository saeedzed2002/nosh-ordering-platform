# Nosh Kitchen & Delivery

Nosh is a local-only direct ordering demo for one fictional restaurant brand.
It intentionally does not process real payments, send messages, use maps, or
claim production readiness.

## Current milestone

This repository currently implements the Phase 0 foundation, the Phase 1
experience/information-architecture contract, the Phase 2 component foundation,
the Phase 3 dynamic customer landing page, the Phase 4 durable backend
foundation, the Phase 5 local administration workflow, the Phase 6 menu
administration workflow, the Phase 7 customer menu/discovery workflow, and the
Phase 8 trustworthy-cart workflow, and the Phase 9 checkout-and-confirmation
workflow, the Phase 10 customer-tracker-and-order-lifecycle workflow, and the
Phase 11 staff-order-desk workflow, the Phase 12 customer-account workflow,
the Phase 13 eligible-review workflow, the Phase 14 operational
administration workflow, and the Phase 15 quality, accessibility, and browser
evidence workflow, the Phase 16 mobile-ready contract workflow, and the Phase
17 reproducible local-demo handoff:

- independent React/Vite and FastAPI applications;
- a PostgreSQL-backed readiness endpoint;
- Docker Compose local development with hot reload;
- baseline formatting, linting, unit tests, and GitHub Actions.
- defined customer journey, administrator workflows, route map, terminology,
  failure states, content inventory, and deterministic future seed-data shape.
- reusable accessible controls, status states, focus-managed overlays, local
  licensed typography, motion rules, and Storybook component review.
- initial customer-facing content discovery and an explicit route map for the
  later ordering flow.
- Phase 4 durable catalog schema, versioned migration, repeatable local seed
  with committed demo-food source images copied into the media volume,
  validation/thumbnailing, read APIs, and server-enforced administrator
  access/refresh tokens.
- Phase 5 role-protected administrator routes, durable home-page drafts and
  publish history, focal-point-aware media management, and non-technical
  `/admin/home` and `/admin/media` workflows.
- Phase 6 role-protected menu desk and guided food workflow with server-enforced
  image/category publication rules, price and demo discount controls, option
  groups, allergens, category visibility, availability schedules, curated
  collections, featured placement, and durable catalog-change records.
- Phase 7 live customer `/menu` and `/menu/{slug}` routes. They read published
  API data, preserve search/filter/sort choices in the URL, display availability
  before a next action, and make ingredients, allergens, known choices,
  preparation information, complementary dishes, empty/error/retry states, and
  the absence of nutrition data clear.
- Phase 8 dish configuration and a versioned local cart. Required and optional
  options, selection limits, quantities, notes, current-price preview, cart
  edits, complementary suggestions, and the final quoted subtotal are checked
  against the published server catalog before a line is retained.
- Phase 9 `/checkout` and `/orders/{publicReference}` routes. The customer
  selects a published location, pickup or simulated delivery, immediate or
  scheduled timing, recipient details, instructions, and a server-validated
  demo promotion. An atomic order stores immutable line, price, option,
  fulfilment, payment, and status snapshots; an idempotency key prevents a
  duplicate order. The confirmation receipt is refresh-safe and deliberately
  omits private contact, address, and instruction data from its public route.
- Phase 10 keeps `/orders/{publicReference}` as a customer-safe tracker. It
  polls lightly for staff-recorded lifecycle changes, shows the distinct pickup
  or delivery journey, timestamps, initial kitchen estimate, location,
  restaurant contact, and customer-safe handoff instructions. It explicitly
  does not claim live courier GPS or a map.
- Phase 11 adds the protected `/admin/orders` operational desk: searchable
  order queues, private staff-only order context, guarded next-status actions,
  controlled issue reasons, and per-location online-ordering, preparation, and
  active-order-capacity controls. A paused, off, or capacity-full kitchen is
  enforced by the server during checkout; it is not merely a browser state.
- Phase 12 adds customer signup/sign-in, refresh-backed account sessions,
  protected profile and saved-address management, favorites, owned order
  history, and an editable reorder flow. A customer checkout is linked to its
  account without exposing that ownership in the public receipt. Reorder never
  copies a historical total: the server rebuilds the saved lines and validates
  current publication, options, availability, location ordering state, and
  price before a cart can be restored.
- Phase 13 permits one review only for an account-owned delivered order item.
  New feedback is pending until a `Manager` or `Owner` moderates it; public
  dish responses return approved reviews only.
- Phase 14 gives `Manager` and `Owner` a local operations workspace for
  promotions, restaurant profile/hours/fulfillment settings, customer lookup,
  and query-backed reports. Only the `Owner` can activate or deactivate a
  customer account and inspect safe before/after audit metadata.
- Phase 15 standardizes consequential administrator dialogs with keyboard-safe
  focus handling, fixes cross-origin customer `DELETE` requests, adds a
  committed favicon, and provides repeatable mobile, tablet, customer-order,
  and authenticated manager browser tests locally and in GitHub Actions.
- Phase 16 freezes the generated `/api/v1` OpenAPI snapshot, generated
  TypeScript client declarations, compatibility policy, ordering invariants,
  design-state contract, and explicit mobile/production boundaries.
- Phase 17 provides a verified local runbook, repeatable demo identities and
  data, persistence/reset behavior, and explicit simulated-service limits.

Customer menu discovery, dish customization, the local cart, checkout, order
tracking, the staff order desk, customer accounts, and eligible reviews are
implemented, as are local operations and reports. Real payments, real delivery
integration, password recovery, and claiming older guest orders are not
implemented and must not be represented as working product flows.

## Local run

1. Create a local environment file.

   ~~~powershell
   Copy-Item .env.example .env
   ~~~

   Before starting the backend, set a unique local `NOSH_JWT_SECRET` of at
   least `32` bytes and a non-empty `NOSH_SEED_ADMIN_PASSWORD` in `.env`.
   They are required environment configuration, not committed demo values.

2. Start the full local stack and wait for its health checks.

   ~~~powershell
   docker compose up --build --detach --wait
   docker compose ps
   ~~~

3. Open the applications.

   - Customer shell: http://localhost:5173
   - API documentation: http://localhost:8000/docs
   - API readiness: http://localhost:8000/api/v1/health

4. In a second terminal, apply migrations and seed or reconcile the local
   demo. The seed command applies migrations before it writes its data.

   ~~~powershell
   docker compose exec backend uv run python -m app.commands.seed
   docker compose exec backend uv run alembic current
   ~~~

   The final command should report the current revision as `(head)`. Re-running
   the seed is safe for the Nosh-owned demo rows and committed food images. It
   also resets the five seeded demo-account passwords to the current untracked
   `NOSH_SEED_ADMIN_PASSWORD`; it does not erase orders, customer-created
   records, uploaded media, or other local work.

To stop the stack, run:

~~~powershell
docker compose down
~~~

Removing volumes deletes all local database and media data. Do that only when
an intentional reset is required. The next migration-and-seed sequence
recreates the initial products and their two committed demo-food images:

~~~powershell
docker compose down --volumes
~~~

## Local checks

Set `NOSH_E2E_ADMIN_PASSWORD` to the same untracked local seed password before
running the browser suite when you want it to include the authenticated manager
scenario. Without it, that one authenticated scenario is intentionally skipped;
do not add the password to source control.

~~~powershell
Set-Location frontend
npm ci
npm run generate:api
npm run check
npm run test -- --run
npm run test:e2e

Set-Location ../backend
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q

Set-Location ..
docker compose config --quiet
docker compose ps
~~~

## Product boundaries

- The initial customer language is English LTR.
- The initial demo has one fictional location.
- Payment and fulfillment are simulated; no card data is accepted or stored.
- No email, SMS, push notification, live courier map, delivery-partner, or
  payment-provider integration exists in this local demo.
- A public order reference is not an authorization credential. The public
  tracker excludes private recipient, delivery-address, and instruction
  snapshots while exposing only the restaurant's fictional local-demo contact.
- Customer account routes require a customer-role token. Address, favorite,
  history, and reorder lookups filter by the authenticated customer in the
  server query; a foreign account object returns the same generic `404` as a
  missing one.
- The `origin` remote is connected to the private GitHub repository. Local
  validation remains distinct from GitHub Actions and production evidence.

See docs/phase-0-foundation.md for architectural choices and explicit
assumptions, and docs/phase-1-experience-information-architecture.md for the
planned customer/admin behavior and seed-data contract. See
docs/phase-2-design-system.md for component and interaction conventions, and
docs/phase-3-customer-landing.md for the dynamic landing-page contract. See
docs/phase-4-data-auth-media-contract.md for the durable data, authentication,
and media contract. See docs/phase-5-admin-home-and-media.md for the home/media
workflow and docs/phase-6-menu-administration.md for the menu administration
contract and docs/phase-7-customer-menu.md for the live menu/discovery contract.
See
docs/phase-8-trustworthy-cart.md for the cart and server-quote contract, and
docs/phase-9-checkout-and-confirmation.md for order transaction and receipt
boundaries. See docs/phase-10-customer-tracker-and-lifecycle.md for the
tracking and lifecycle boundaries, and docs/phase-11-admin-order-desk.md for
the protected operational order-desk contract. See
docs/phase-12-customer-accounts.md for account ownership, reorder, and privacy
boundaries, docs/phase-13-reviews.md for eligible review and moderation
boundaries, docs/phase-14-operations.md for restaurant operations, and
docs/phase-15-quality-accessibility.md for browser-test execution and the
quality/accessibility scope. See docs/phase-16-mobile-contract.md for the
versioned API, generated client types, and future native-client boundaries.
See docs/phase-17-demo-handoff.md for the reproducible demo runbook, seeded
account roles, reset boundary, validation commands, and explicit limitations.
