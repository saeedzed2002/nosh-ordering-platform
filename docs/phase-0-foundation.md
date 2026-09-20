# Phase 0 foundation

## Purpose

The first milestone establishes a reproducible local development baseline for
Nosh Kitchen & Delivery. It deliberately avoids claiming that the restaurant
ordering product is already implemented.

## Chosen defaults

The roadmap lists several inputs that normally require confirmation before
Phase 0. Work began using these reversible defaults:

| Decision | Initial default | Reason |
| --- | --- | --- |
| Customer language | English LTR | The customer language was not supplied; this avoids a partial RTL implementation. |
| Restaurant locations | One fictional location | The product is a single-brand direct-ordering service, not a marketplace. |
| Payments and delivery | Simulated in future phases | The roadmap explicitly excludes real providers from this local demo. |
| API base | /api/v1 | Preserves a stable contract boundary before product endpoints are added. |

## Runtime layout

| Service | Local address | Responsibility |
| --- | --- | --- |
| frontend | http://localhost:5173 | React/Vite customer shell and future admin client |
| backend | http://localhost:8000 | FastAPI API, OpenAPI documentation, and health endpoints |
| postgres | localhost:5432 | Future persistent ordering data |

The backend readiness endpoint executes SELECT 1 against PostgreSQL. The
separate liveness endpoint does not depend on the database, so container
orchestration can distinguish a process failure from a database failure.

## Deliberate exclusions

- No customer identity, admin identity, JWT, or persistence models exist yet.
- No menu item, availability, order, payment, tracking, review, media, or
  promotion behavior exists yet.
- No remote repository, deployment, paid service, or public domain is
  configured.
- The generated food image is an original local development visual asset; it
  must not be presented as a real restaurant photo or evidence of a live
  service.

## Next implementation boundary

Phase 1 should lock the customer journey, administrator workflows, route map,
terminology, failure states, content inventory, and seeded demo data before
expanding product code. Phase 2 then turns the initial visual direction into
documented, accessible components and motion rules.
