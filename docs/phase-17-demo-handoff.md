# Phase 17 — Local demo handoff

Phase 17 closes the roadmap as a reproducible local demonstration. It does not
deploy Nosh, create external accounts, or turn its simulated services into
production integrations.

## Clean local runbook

From a fresh clone, create an untracked `.env` from `.env.example`. Set a
unique `NOSH_JWT_SECRET` of at least 32 bytes and a non-empty
`NOSH_SEED_ADMIN_PASSWORD`. Neither value is committed.

~~~powershell
Copy-Item .env.example .env
docker compose up --build --detach --wait
docker compose exec backend uv run python -m app.commands.seed
docker compose exec backend uv run alembic current
docker compose ps
~~~

The migration command must report the current revision as `(head)`. Verify the
three user-facing local endpoints before a demo:

| Surface | Local URL | Expected result |
| --- | --- | --- |
| Customer application | `http://localhost:5173` | The Nosh landing page and menu are available. |
| API readiness | `http://localhost:8000/api/v1/health` | JSON with application and database status `ok`. |
| API documentation | `http://localhost:8000/docs` | FastAPI documentation for the versioned API. |

`docker compose down` stops containers while retaining the named PostgreSQL and
media volumes. `docker compose down --volumes` is an intentional destructive
reset: it removes orders, local edits, uploaded media, and all other local
state. Run it only when a clean demo database is explicitly wanted, then repeat
the seed command above. The seed ensures its Nosh-owned rows and two committed
food images exist, but does not remove user-created records during a normal
re-seed.

## Seeded demo access

All identities below are fictional local data. Their password is the current
untracked `NOSH_SEED_ADMIN_PASSWORD`; no credential is stored in Git. Re-running
the seed re-applies that password to these five seed identities.

| Identity | Role | Use in the demo |
| --- | --- | --- |
| `owner@nosh.example` | Owner | Full local administration, including audit and customer-account state. |
| `manager@nosh.example` | Manager | Home, media, menu, reviews, promotions, reports, and order operations. |
| `kitchen@nosh.example` | Kitchen | Permitted kitchen order-progress transitions. |
| `maya@nosh.example` | Customer | Customer account, order history, favorites, reorder, and eligible review flow. |
| `jordan@nosh.example` | Customer | A second ownership boundary for account demonstrations. |

Use `/admin/sign-in` for staff identities and `/account/sign-in` for customer
identities. The seed includes one published fictional location, 16 menu items,
their published catalog relationships, `WELCOME10`, and two committed food
assets copied into the Docker media volume. Ordinary browser checkout tests and
manual demos may create additional local orders; those are not canonical seed
data and remain until an intentional volume reset.

## Demonstrable flows

1. A guest can browse `/menu`, choose required and optional dish choices, see
   the server-quoted price, place a clearly labelled mock-payment order, and
   open the redacted receipt/tracker.
2. A signed-in customer can manage profile data, addresses and favorites, view
   owned history, build a newly validated reorder draft, and submit an eligible
   review for a delivered item.
3. A manager can edit and publish home/menu content, process the protected
   order queues, moderate reviews, manage promotions and restaurant controls,
   and inspect local reports. The owner additionally has customer-state and
   audit-log access.

## Explicit limits

- Payments are approve/decline simulations. Nosh accepts no card data, moves no
  money, creates no provider payment intent, and has no refund or webhook flow.
- Delivery states are staff-entered records. There is no dispatch system,
  courier identity, live location, map, capacity forecast, or delivery-partner
  API.
- Nosh sends no email, SMS, or push notification and implements no device-token
  registration or recovery-email flow.
- This is a single-host Docker development setup. It has no HTTPS, managed
  secrets, production backup/restore process, observability service, rate-limit
  policy, external storage, or deployment configuration.
- The public order reference is a local-demo tracker locator, not an
  authorization credential. Private contact, delivery-address, instruction,
  token, and audit data are excluded from public tracker responses.

## Evidence commands

The following commands exercise distinct boundaries. A local pass is not a
claim that GitHub Actions or a production environment passed.

~~~powershell
Set-Location backend
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run python scripts/export_openapi.py
uv run pytest tests/test_phase_16_contract.py -q

Set-Location ../frontend
npm run generate:api
npm run check
npm run test -- --run
npm run test:e2e
~~~

The contract artifacts are regenerated from FastAPI and checked into
`docs/contracts/openapi-v1.json` and `frontend/src/api/generated/v1.ts`.
GitHub Actions rejects drift. The browser suite uses a local manager password
only when `NOSH_E2E_ADMIN_PASSWORD` is explicitly supplied; do not place that
password in source control.
