# Nosh backend

The backend now contains the Phase 4 durable data/media foundation through the
Phase 12 customer-account workflow. It supports the local checkout and order
lifecycle, role-protected administration, customer signup/sign-in, saved
addresses, favorites, owned order history, and server-revalidated reorder.
Real payments, delivery integrations, password recovery, and guest-order
claiming remain outside this local demo.

## Apply the local schema and seed the demo catalog

Set a unique `NOSH_JWT_SECRET` of at least 32 bytes and
`NOSH_SEED_ADMIN_PASSWORD` in the untracked root `.env` file first. The seed uses
that local password for the deterministic administrator identity
`owner@nosh.example`; it is never committed.

~~~powershell
uv run alembic upgrade head
uv run python -m app.commands.seed
~~~

The command can be run again safely. It creates one fictional location, roles,
five deterministic users (including two customer identities), six categories,
sixteen dishes, options, allergens, collections, home content, and committed
development-only demo-food media.
