# Phase 4: Data, authentication, and local media contract

## Purpose

Phase 4 introduces the durable backend boundary shared by the customer and
administrator experiences. This document fixes the storage and ownership rules
before the first migration is written. It does not claim that any of the models
or endpoints below are implemented yet.

## Data rules

- Every domain record uses a server-generated UUID primary key and UTC-aware
  creation/update timestamps.
- Money is stored as integer minor units with an explicit currency code; a
  formatted price is never persisted or used for validation.
- Public slugs are lowercase and unique within their owner scope. They are not
  substituted for primary keys in administrative mutations.
- Locations own business hours and menu availability. The initial product has
  one seeded location, but no table assumes only one can exist.
- Menu items reference a category and optional curated collections. Their
  availability, publication state, allergen links, option groups, and media are
  independently representable.
- Option groups own ordered options and carry the min/max selection rules that
  later order validation must enforce server-side.

## Authentication and authorization rules

- Users have one server-side role: `customer`, `staff`, or `admin`.
- Access and refresh tokens will be separate, short- and longer-lived JWTs.
  Refresh token rotation, revocation storage, password-reset flows, and public
  registration are explicitly outside the first authentication increment.
- Administrator routes will depend on a decoded current user and a server-side
  role check. A role or user identifier supplied by a browser is never trusted.
- Development credentials, JWT secrets, and local storage paths remain in
  environment configuration and are never committed.

## Local media rules

- Original files live under a named Docker volume, never under a public source
  directory or the repository.
- Metadata records keep MIME type, byte size, dimensions, checksum, alt text,
  focal point, credit, and derivative paths.
- Upload validation will allow an explicit image MIME allowlist and a bounded
  size before any file is persisted. The server will create a constrained
  thumbnail derivative rather than expose unvalidated uploads directly.
- A media record cannot be deleted while active menu or home content references
  it; later admin behavior must return a clear conflict response.

## Migration and seed order

1. Add database engine/session lifecycle and migration tooling.
2. Create users, roles, locations, hours, media, categories, and menu tables.
3. Create collections, allergens, option groups, options, and join tables.
4. Add an idempotent local seed command for the single Nosh location and the
   preview dishes already used by the frontend.
5. Add documented read endpoints and only then protected administrator sign-in
   and write endpoints.

## Acceptance evidence to collect

- Applying migrations to an empty database and rerunning the seed is safe.
- A normal Compose restart preserves database rows and volume-backed media.
- Invalid media type/size is rejected before persistence.
- Health, API base, seeded read data, and protected route behavior have focused
  tests and remain visible in OpenAPI.
