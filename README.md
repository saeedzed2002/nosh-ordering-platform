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
workflow, and the Phase 10 customer-tracker-and-order-lifecycle workflow:

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

Customer menu discovery, dish customization, the local cart, checkout, and
order tracking are implemented. The staff order desk, customer accounts, real
payments, real delivery integration, and customer reviews are not yet
implemented and must not be represented as working product flows.

## Local run

1. Create a local environment file.

   ~~~powershell
   Copy-Item .env.example .env
   ~~~

   Before starting the backend, set a unique local `NOSH_JWT_SECRET` of at
   least `32` bytes and a non-empty `NOSH_SEED_ADMIN_PASSWORD` in `.env`.
   They are required environment configuration, not committed demo values.

2. Start the full local stack.

   ~~~powershell
   docker compose up --build
   ~~~

3. Open the applications.

   - Customer shell: http://localhost:5173
   - API documentation: http://localhost:8000/docs
   - API readiness: http://localhost:8000/api/v1/health

4. In a second terminal, apply the schema and seed the local demo.

   ~~~powershell
   docker compose exec backend uv run alembic upgrade head
   docker compose exec backend uv run python -m app.commands.seed
   ~~~

To stop the stack, run:

~~~powershell
docker compose down
~~~

Removing the database volume deletes local demo data. Do that only when an
intentional reset is required. The next migration-and-seed sequence recreates
the initial products and their two committed demo-food images:

~~~powershell
docker compose down --volumes
~~~

## Local checks

~~~powershell
Set-Location frontend
npm install
npm run check
npm run test -- --run

Set-Location ../backend
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
~~~

## Product boundaries

- The initial customer language is English LTR.
- The initial demo has one fictional location.
- Payment and fulfillment are simulated; no card data is accepted or stored.
- A public order reference is not an authorization credential. The public
  tracker excludes private recipient, delivery-address, and instruction
  snapshots while exposing only the restaurant's fictional local-demo contact.
- The `origin` remote is connected to the private GitHub repository. Local
  validation remains distinct from GitHub Actions and production evidence.

See docs/phase-0-foundation.md for architectural choices and explicit
assumptions, and docs/phase-1-experience-information-architecture.md for the
planned customer/admin behavior and seed-data contract. See
docs/phase-2-design-system.md for component and interaction conventions, and
docs/phase-3-customer-landing.md for the dynamic landing-page contract. See
docs/phase-5-admin-home-and-media.md for the home/media workflow and
docs/phase-6-menu-administration.md for the menu administration contract and
docs/phase-7-customer-menu.md for the live menu/discovery contract. See
docs/phase-8-trustworthy-cart.md for the cart and server-quote contract, and
docs/phase-9-checkout-and-confirmation.md for order transaction and receipt
boundaries. See docs/phase-10-customer-tracker-and-lifecycle.md for the
tracking and lifecycle boundaries.
