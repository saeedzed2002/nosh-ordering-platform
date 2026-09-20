# Nosh backend

The backend now contains the Phase 4 data, media, and administrator-authentication
foundation. Checkout, orders, customer accounts, and administrative editing screens
remain later roadmap work.

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
five deterministic users, six categories, sixteen dishes, options, allergens,
collections, home content, and generated development-only media placeholders.
