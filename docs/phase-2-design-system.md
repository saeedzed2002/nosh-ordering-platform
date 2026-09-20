# Phase 2: Nosh design system and component library

## Scope

Phase 2 establishes the visual and interaction primitives used by later
customer and administration work. It does not make menu, cart persistence,
checkout, accounts, or administration functional. The current customer shell
uses the new button, focus-managed drawer, toast, typography, and icon system
only as a foundation for those later flows.

## Visual system

The design keeps the roadmap's warm-cream canvas, deep-olive operational
surface, and restrained orange action accent. The signature is the tension
between editorial food typography and deliberately calm transactional controls:
the type invites appetite, while controls are compact, explicit, and
predictable.

| Token | Value | Intended use |
| --- | --- | --- |
| `surface-canvas` | `#F6F1E8` | Main customer canvas. |
| `surface-muted` | `#E8DDCC` | Quiet image fallback and secondary surfaces. |
| `surface-raised` | `#FFFDF8` | Controls, food cards, and drawers. |
| `surface-inverse` | `#0D2417` | High-emphasis bands and operational messages. |
| `text-strong` | `#171813` | Primary reading text. |
| `action-primary` | `#FF6A16` | Primary action, focus treatment, and high-priority feedback only. |
| `status-available` | `#28723D` | Available/healthy status. |
| `status-preparing` | `#B97700` | In-progress status. |
| `status-ready` | `#16698A` | Ready state. |
| `status-unavailable` | `#AD3E2C` | Error and unavailable state. |

`Noto Serif Variable` is bundled locally for display typography and `Source
Sans 3 Variable` for interface/body typography. Both are installed packages,
not runtime font requests. English LTR is the current product language; no
claim of Persian coverage or RTL readiness is made by this phase.

Primary actions use strong dark text on `action-primary`. This preserves the
specified orange while meeting the contrast requirement; light text on this
orange did not meet the required ratio in the isolated accessibility review.

## Components and ownership

| Component | Variants and states | Accessibility/behavior contract |
| --- | --- | --- |
| `Button` | Primary, secondary, danger, quiet; compact, icon, disabled, loading. | Native button semantics, visible focus, disabled semantics, and loading state. |
| `IconButton` | Quiet or secondary icon action. | Requires an accessible label; decorative icon is hidden from assistive technology. |
| `TextField` and `SelectField` | Default, hint, focused, invalid. | Native labelled fields with unique IDs, announced errors, and `aria-describedby`. |
| `StatusBadge` | Available, preparing, ready, unavailable. | Text accompanies every color; color is never the only signal. |
| `QuantityStepper` | Minimum, maximum, disabled, live value. | Explicit increase/decrease labels and polite quantity output. |
| `FoodCard` | Available and unavailable. | Image alternative text, a textual status, and an unavailable action that cannot be invoked. |
| `Drawer` | Open, closed, keyboard-dismissed. | Uses Radix Dialog for modal semantics, focus management, `Escape` close, screen-reader title/description, and an inert background. |
| `ToastNotice` | Open, dismissed, auto-close. | Uses Radix Toast with a visible dismiss action and no action that is unsafe to ignore. |
| `Skeleton` | Reduced-motion and default. | Decorative only; uses a quiet opacity pulse rather than a visual gradient. |

`lucide-react` supplies a single consistent outlined icon family. The current
set uses a fixed optical size and stroke treatment rather than mixed emoji or
ad hoc glyphs. Native select controls intentionally remain native: they are
the more predictable baseline for the current small option sets. Radix is used
where focus trapping and live-region mechanics provide real value.

## Motion rules

| Interaction | Default behavior | Reduced-motion behavior |
| --- | --- | --- |
| Button hover | Color change and a one-pixel lift over `160ms`. | Immediate state change. |
| Drawer | Right-edge entry over `180ms`; overlay fades in. | Immediate open/close. |
| Toast | Bottom-edge entry over `180ms`. | Immediate open/close. |
| Skeleton | Low-contrast opacity pulse. | One static frame. |
| Page navigation | Native smooth anchor scroll. | Native instant anchor scroll. |

All nonessential motion is overridden inside `prefers-reduced-motion`. No
animation communicates an order state, payment result, or delivery location.

## Component review surface

Storybook is configured through `frontend/.storybook/` and includes the
accessibility addon. The first stories cover buttons (including loading and
inverse-surface states), fields, status badges, food cards, skeletons, toast
notices, and the focus-managed drawer. Run it locally with:

~~~powershell
Set-Location frontend
npm run storybook
~~~

Build the static review surface without publishing it:

~~~powershell
npm run build-storybook
~~~

## Deliberate boundaries

- Components do not calculate order totals, validate menu options, or persist
  cart data; those rules remain backend-owned and arrive in later phases.
- The current cart drawer is a component demonstration with truthful phase
  language, not a claim of a working cart.
- The local hero image remains a development-only visual asset. It is not
  passed off as a restaurant photograph or as licensed production media.
- No design-system dependency starts a public server or contacts an external
  service at runtime.

## Acceptance trace

| Phase acceptance requirement | Evidence |
| --- | --- |
| Coherent reusable components | Shared typed `ui/` components and tokens in `styles.css`. |
| Focus, loading, error, disabled, mobile, inverse-surface states | Button, field, drawer, toast, status, responsive, and reduced-motion contracts above. |
| Accessible dialog/drawer and notification primitives | Radix Dialog and Toast abstractions with visible labels and close behavior. |
| Stable isolated review | Storybook stories and accessibility addon. |
| Original visual direction | Tokens and typography follow the Nosh product direction; no reference-site assets, layouts, or copy were introduced. |
