# Nosh Kitchen & Delivery

Nosh is a local-only direct ordering demo for one fictional restaurant brand.
It intentionally does not process real payments, send messages, use maps, or
claim production readiness.

## Current milestone

This repository currently implements the Phase 0 foundation:

- independent React/Vite and FastAPI applications;
- a PostgreSQL-backed readiness endpoint;
- Docker Compose local development with hot reload;
- baseline formatting, linting, unit tests, and GitHub Actions.

The customer experience is an intentionally limited visual shell. Menu,
customization, checkout, tracking, accounts, and administration are not yet
implemented and must not be represented as working product flows.

## Local run

1. Create a local environment file.

   ~~~powershell
   Copy-Item .env.example .env
   ~~~

2. Start the full local stack.

   ~~~powershell
   docker compose up --build
   ~~~

3. Open the applications.

   - Customer shell: http://localhost:5173
   - API documentation: http://localhost:8000/docs
   - API readiness: http://localhost:8000/api/v1/health

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
- A GitHub remote has not been supplied, so this repository cannot be pushed
  until the user provides one.

See docs/phase-0-foundation.md for architectural choices and explicit
assumptions.
