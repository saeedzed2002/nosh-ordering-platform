# Phase 5 — Local administration, home content, and media

## Delivered scope

Phase 5 adds a usable local administration workflow without broadening the
customer ordering scope.

| Capability | Delivered behavior |
| --- | --- |
| Staff entry | `/admin/sign-in` uses the existing server-issued token pair. The server remains the authority for owner and manager permissions. |
| Task desk | `/admin` gives a concise choice between home-page publishing and media maintenance. |
| Home editor | `/admin/home` edits the seeded home sections, saves a durable private draft, renders a live preview, and publishes a selected saved revision. |
| History | Each save and publish records the editor, time, headline, image, action, and copy snapshot. The latest saved draft is distinct from live content. |
| Loss prevention | Switching sections reloads the saved version; an unsaved edit causes the browser leave warning; publishing is unavailable until a saved draft exists. |
| Media library | `/admin/media` lists source assets, supports local JPEG/PNG/WebP uploads, accessible alt text, source/credit notes, focal-point cropping, visibility, newest/oldest ordering, and current home-page usage. |
| Customer reflection | Published home content is loaded by the public landing page on its next load. Development placeholder images retain the existing licensed visual fallback until an administrator replaces them with a customer-ready asset. |

## Route and permission boundaries

| Route | Required server role | Purpose |
| --- | --- | --- |
| `/api/v1/admin/home` | `owner` or `manager` | Read editable home sections. |
| `/api/v1/admin/home/{content_key}/draft` | `owner` or `manager` | Save a private content snapshot. |
| `/api/v1/admin/home/{content_key}/publish` | `owner` or `manager` | Apply one saved snapshot to the public home content. |
| `/api/v1/admin/media` | `owner` or `manager` | List and upload library assets. |
| `/api/v1/admin/media/{media_id}` | `owner` or `manager` | Update metadata, focal crop, and visibility. |
| `/api/v1/admin/media/{media_id}/thumbnail` | `owner` or `manager` | Read a private image preview with an authorization header. |

The client-side route guard is for navigation only. It does not replace these
server-side role checks.

## Content safety rules

- A draft revision never changes `/api/v1/catalog/home`.
- Publishing requires a revision from the selected home section.
- A selected image becomes published with the home content that uses it.
- A currently published home image cannot be returned to `draft` until it is
  replaced in the live home section.
- The original file is retained; changing the focal point regenerates only its
  `480 × 480` WebP thumbnail.
- Media is not deleted in Phase 5. Usage history remains visible instead of
  silently breaking a published section.

## Verification evidence

The automated suite covers the database migration, owner authorization,
private-draft behavior, public publish behavior, revision ordering, protected
thumbnails, image metadata updates, and prevention of hiding a live image.

The Phase 5 browser acceptance path is:

1. Sign in at `/admin/sign-in` with a seeded owner or manager account.
2. Select **Hero welcome** in `/admin/home`.
3. Change the heading or choose an image, then select **Save draft**.
4. Confirm the adjacent preview and the new history entry.
5. Select **Publish saved draft**, then refresh `/` to see the published copy.

This phase deliberately does not implement menu pages, product details, a
persistent cart, checkout, customer accounts, or order operations. Those are
later roadmap phases.
