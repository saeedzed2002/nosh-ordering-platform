# Nosh Kitchen & Delivery

Nosh is a local-only direct ordering demo for one fictional restaurant brand.
It intentionally does not process real payments, send messages, use maps, or
claim production readiness.

## Current milestone

This repository currently implements the Phase 0 foundation, the Phase 1
experience/information-architecture contract, the Phase 2 component foundation,
the Phase 3 dynamic customer landing page, the Phase 4 durable backend
foundation, and the Phase 5 local administration workflow:

- independent React/Vite and FastAPI applications;
- a PostgreSQL-backed readiness endpoint;
- Docker Compose local development with hot reload;
- baseline formatting, linting, unit tests, and GitHub Actions.
- defined customer journey, administrator workflows, route map, terminology,
  failure states, content inventory, and deterministic future seed-data shape.
- reusable accessible controls, status states, focus-managed overlays, local
  licensed typography, motion rules, and Storybook component review.
- customer-facing content discovery, seeded preview dishes, and a clearly
  browser-only cart with an explicit home-to-menu-to-cart route.
- Phase 4 durable catalog schema, versioned migration, repeatable local seed,
  volume-backed media validation/thumbnailing, read APIs, and server-enforced
  administrator access/refresh tokens.
- Phase 5 role-protected administrator routes, durable home-page drafts and
  publish history, focal-point-aware media management, and non-technical
  `/admin/home` and `/admin/media` workflows.

The customer experience is intentionally limited to the completed landing,
location, and about routes. Menu detail, customization, checkout, tracking,
and customer accounts are not yet implemented and must not be represented as
working product flows.

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
intentional reset is required:

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
- Payment and fulfillment are simulated in later phases.
- The `origin` remote is connected to the private GitHub repository. Local
  validation remains distinct from GitHub Actions and production evidence.

See docs/phase-0-foundation.md for architectural choices and explicit
assumptions, and docs/phase-1-experience-information-architecture.md for the
planned customer/admin behavior and seed-data contract. See
docs/phase-2-design-system.md for component and interaction conventions, and
docs/phase-3-customer-landing.md for the dynamic landing-page contract. See
docs/phase-5-admin-home-and-media.md for the completed local administration
workflow and its boundaries.
