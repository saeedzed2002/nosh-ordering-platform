# Nosh Kitchen & Delivery

Nosh is a local-first restaurant-ordering demo for one fictional brand. It combines a customer ordering journey with a role-protected operations workspace and is designed to be reproducible on a developer machine.

## What this demonstrates

- Customer menu discovery, dish configuration, a server-checked local cart, checkout, order tracking, account management, reorder, and eligible reviews.
- An operations workspace for menu publishing, order fulfilment, promotions, restaurant settings, customer lookup, and reports.
- Server-enforced catalogue, pricing, availability, capacity, ownership, and order-lifecycle rules rather than browser-only checks.
- A React/Vite frontend, FastAPI backend, PostgreSQL, generated OpenAPI client declarations, and reproducible Docker Compose development.

## Scope and evidence

The repository implements the documented Phase 0 through Phase 17 local-demo scope. It includes migrations, deterministic seed data, backend and frontend checks, authenticated browser scenarios, and a repeatable handoff runbook. The current local-demo baseline is released as [v0.1.0-local-demo](https://github.com/saeedzed2002/nosh-ordering-platform/releases/tag/v0.1.0-local-demo).

Nosh deliberately does **not** claim real payments, delivery-partner integration, messages, maps, password recovery, or public production hosting. Payment and fulfilment are simulated; no card data is accepted or stored.

## Architecture

~~~text
React/Vite customer and operations applications
                    |
                 FastAPI
                    |
               PostgreSQL
                    |
           Docker Compose local stack
~~~

## Explore the implementation

- [Customer and operations experience contract](docs/phase-1-experience-information-architecture.md)
- [Data, authentication, and media contract](docs/phase-4-data-auth-media-contract.md)
- [Order transaction and receipt boundaries](docs/phase-9-checkout-and-confirmation.md)
- [Quality and browser-evidence workflow](docs/phase-15-quality-accessibility.md)
- [Reproducible local-demo handoff](docs/phase-17-demo-handoff.md)

## Local run

1. Create a local environment file.

   ~~~powershell
   Copy-Item .env.example .env
   ~~~

   Set a unique local NOSH_JWT_SECRET of at least 32 bytes and a non-empty NOSH_SEED_ADMIN_PASSWORD in .env. These values are required local configuration and are not committed.

2. Start the stack and wait for its health checks.

   ~~~powershell
   docker compose up --build --detach --wait
   docker compose ps
   ~~~

3. Open the customer application at http://localhost:5173, API documentation at http://localhost:8000/docs, and readiness at http://localhost:8000/api/v1/health.

4. Apply migrations and seed the local demo.

   ~~~powershell
   docker compose exec backend uv run python -m app.commands.seed
   docker compose exec backend uv run alembic current
   ~~~

The final command should report the current revision as head. Re-running the seed is safe for the Nosh-owned demo rows and committed food images. It does not erase orders, customer-created records, uploaded media, or other local work.

## Local checks

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
~~~

Set NOSH_E2E_ADMIN_PASSWORD to the same untracked local seed password to include the authenticated manager browser scenario. Without it, that scenario is intentionally skipped.

## Product boundaries

- The initial customer language is English LTR and the demo has one fictional location.
- A public order reference is not an authorization credential; the public tracker excludes private recipient, delivery-address, and instruction snapshots.
- Customer account lookups are filtered by the authenticated customer in the server query; a foreign object returns the same generic 404 as a missing one.
- Local validation remains distinct from GitHub Actions and production evidence.
