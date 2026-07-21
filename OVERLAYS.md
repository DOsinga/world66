# Content Overlays

Overlays let a third-party commercial supplier attach extra POIs and sections to an existing location page — without ever touching `content/`. This is the mechanism for bookable activities (elephant camps, cooking classes, tour operators, etc.): editorial guide content stays hand-written and git-tracked; commercial content stays external, live, and swappable.

## How it works

1. A supplier publishes a JSON file at a URL they control and keep updated.
2. We register that URL against exactly one content path in `overlay_sources.yaml` (repo root), via normal PR review. The registry — not the feed — is the sole authority on which path a supplier may attach to.
3. World66 fetches the feed at render time (cached for `OVERLAY_CACHE_TTL` seconds, default 15 minutes), converts each entry into an ordinary page, and merges it into the existing rendering pipeline: extra sections appear in the sidebar, extra POIs appear in whichever tagged section(s) they declare, and on the map — exactly like native content, but visually marked with a "Partner" badge.
4. A slow, unreachable, or malformed feed contributes nothing and never breaks the page it would have appeared on.

See `guide/overlays.py` for the implementation.

## Registering a supplier

Add one entry to `overlay_sources.yaml`:

```yaml
- content_path: asia/thailand/andamancoast/phuket
  name: example-supplier
  feed_url: https://supplier.example.com/world66-overlay.json
```

`content_path` must exactly match an existing city/feature/island page's own path (no trailing slash). `name` is a short label for this supplier (shown nowhere in URLs — see below); it just needs to be unique in the registry. Optional `display_name` is shown instead of `name` in the visitor-facing toggle described below.

### URLs

An overlay section gets a URL that looks exactly like a native one: `<content_path>/<section-slug>` (e.g. `asia/thailand/chiangmai/nature_wildlife`). An overlay POI reached from within that section's listing looks like `<content_path>/<section-slug>/<poi-slug>` — the same `city/section/poi` shape native content already uses. There's no supplier name or marker anywhere in the URL.

This means an overlay section or POI slug must not collide with a real one at that `content_path` — real content always wins a collision (the overlay entry is silently dropped, not shown twice), so check for accidental slug clashes before registering. If two suppliers are ever registered against the same `content_path`, their slugs must not collide with each other either — there's no per-supplier namespace to fall back on.

## Feed schema

```json
{
  "sections": [
    {
      "slug": "book_activity",
      "title": "Book an Activity",
      "body": "Optional intro prose, rendered as markdown, same as any section page."
    }
  ],
  "pois": [
    {
      "slug": "elephant-camp-half-day",
      "title": "Elephant Nature Camp Half-Day Tour",
      "latitude": 18.79,
      "longitude": 98.95,
      "snippet": "Ethical elephant encounter, half-day, includes lunch",
      "body": "Longer description, markdown, same as any POI page.",
      "tags": ["book_activity", "things_to_do"],
      "score": 8.0,
      "duration": "4 hours",
      "action": {
        "type": "book",
        "label": "Book Now",
        "handler": {"kind": "url", "target": "https://supplier.example.com/book/123"}
      }
    }
  ]
}
```

- **`sections`** — each becomes a new nav page under the registered location, alongside its existing sections (Things to Do, Eating Out, etc.). Required: `slug`, `title`. Optional: `body`.
- **`pois`** — each becomes a new POI. Required: `slug`, `title`, `latitude`, `longitude`. `tags` determines which section(s) it appears in — tag it with an existing section's slug (e.g. `things_to_do`) to appear there, a new overlay section's slug to appear there, or both.
- Any other field a POI defines (`snippet`, `score`, `duration`, etc.) is stored as-is and displayed the same way native frontmatter would be — same property table, same `DISPLAY_PROPERTIES` mapping (`guide/models.py`).
- **`action`** (POIs only) — optional. `type` is a free-form label (`"book"`, `"reserve"`, ...) used as the button's default label if `label` isn't set. `handler.kind` selects how the action is carried out:
  - `"url"` (the only kind implemented today) — `handler.target` is a URL; clicking the button opens it in a new tab. No server-side state, no negotiation.
  - Other `handler.kind` values are reserved for future use (e.g. a server-side webhook proxy) — an unrecognized kind is ignored (the button is simply omitted), never an error.
- **`show_on_map`** (POIs only) — optional, defaults to `false`. Overlay POIs never contribute a map marker on any map (city page, section page, or the `/explore` view) unless a POI explicitly sets `"show_on_map": true`. The default is off so third-party listings don't clutter a map the guide didn't curate — sections/listings are unaffected either way; this only controls map markers.

## Letting a visitor turn a supplier off

Any page within a city that has a registered overlay shows a small "Partner listings" disclosure with one checkbox per registered supplier (labelled "Show {display_name}", falling back to `name`). A checked box shows that supplier's sections and POIs; unchecking it and saving hides them everywhere on the site — the preference is stored in the visitor's session (`django.contrib.sessions`, signed-cookie backend, no database) and applies on every subsequent request until changed again. A fresh visitor with no preference set sees every registered supplier by default (opt-out, not opt-in — every box starts checked).

Mechanically: `guide/views.py` reads the session at the top of `_location_or_section()` and calls `overlays.set_disabled_sources()`, which stores the disabled names in a `contextvars.ContextVar` for the rest of that request. `build_city_tag_index()` and `Page.children()` read it indirectly through `_registry_entries_for()` — no request object needs to be threaded through those (or any other) call sites. The toggle form posts to `/overlay-prefs` (CSRF-protected, redirects back to the referring page).

If a visitor hides a supplier and then follows an old link straight to one of that supplier's own section/POI URLs, they'll get a 404 rather than the hidden content — an intentional, honest consequence of them asking not to see it, not a bug.

## What overlays are not

- Not a way to publish editorial content. STYLE.md's "we're a guide, not a booking engine" rule still applies to everything in `content/`; overlay content is a separate, clearly-labeled commercial layer, not a loophole for booking links in the ranked editorial voice.
- Not visible sitewide — v1 only surfaces overlay content on the location page(s) a feed is registered against. It never appears on the home page, the tag index, or anywhere else that scans the whole content tree.
- Not a booking/negotiation backend. The `action.handler` dispatch table is deliberately extensible, but nothing beyond a plain outbound link is implemented yet.
