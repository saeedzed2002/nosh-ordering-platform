# Phase 15 — Quality, accessibility, performance, and E2E evidence

Phase 15 turns the earlier customer and administrator workflows into a
repeatable quality gate. It does not add a production payment, delivery, or
messaging integration.

## Accessibility and interaction repairs

- Consequential administrator overlays now use the shared `AdminModal`, built
  on Radix `Dialog`. It supplies the dialog relationship, focus trap, Escape
  dismissal, pointer-outside dismissal, and return of focus to the initiating
  control.
- The order-status reason selector receives initial focus. Review moderation
  focuses its private-reason input when it is required.
- Review moderation errors are visible inside the active dialog and announced
  as alerts rather than appearing behind the overlay.
- Existing skip links, focus-visible styles, quantity output, and reduced
  motion rules are exercised by browser tests. The customer quantity control
  keeps a visible numeric output between its decrement and increment buttons.
- The document now declares a committed vector favicon, removing the browser
  shell's missing `/favicon.ico` request.

## Browser evidence

`frontend/e2e/customer-and-admin.spec.ts` verifies these real browser flows
against the running local stack:

1. Customer menu at mobile and tablet widths, including the cart control,
   skip-link target, reduced-motion preference, and no horizontal overflow.
2. Desktop dish customization, quantity changes, cart quote, checkout, saved
   receipt, tracker, and absence of console or HTTP errors.
3. Authenticated manager navigation through unpublished home editing, the
   published menu board, and the order desk. It verifies that an unsaved home
   edit is not persisted after reload and that the issue dialog opens with the
   reason selector focused, closes with Escape, and restores focus to its
   initiating action.

The checkout test intentionally creates one ordinary local-demo order. It
does not edit or publish customer content, alter capacity controls, or invoke a
destructive order transition.

Run the public browser coverage against a healthy local stack with:

~~~powershell
Set-Location frontend
npm run test:e2e
~~~

Set `NOSH_E2E_ADMIN_PASSWORD` to the local seed password to enable the
authenticated manager scenario. Playwright uses its managed Chromium by
default. Where that browser download is unavailable, set
`NOSH_E2E_BROWSER_PATH` to a locally installed Chromium-compatible browser
executable before running the command. Neither environment value belongs in
source control.

The `browser-e2e` GitHub Actions job creates its own disposable Compose stack,
uses CI-only local credentials, seeds the demo, and installs Chromium before
running the same suite. A local pass is not evidence that an unobserved GitHub
Actions run has passed.

## Backend safety review

- CORS accepts only configured origins, has no credentialed cross-origin
  cookies, and now explicitly permits `DELETE`, matching the account address,
  favorite, and review endpoints used by the customer UI.
- Authentication and authorization remain server-side. The browser E2E suite
  signs in as a manager only through the public sign-in form; the test password
  is supplied only at execution time.
- Media reads resolve paths beneath the configured media root and reject path
  traversal. Public thumbnails require published media; original media requires
  an administrator role.
- Customer public receipts continue to exclude private recipient, address, and
  instruction data.

## Scope boundary

This phase verifies quality gates around existing local-demo behavior. Real
payments, courier location, notifications, recovery email, and production
deployment remain explicitly out of scope.
