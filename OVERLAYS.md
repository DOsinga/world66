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

`content_path` must exactly match an existing city/feature/island page's own path (no trailing slash). `name` is a short, unique slug for this supplier — it's used to namespace overlay URLs and must not collide with another registered supplier on the same path.

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

## What overlays are not

- Not a way to publish editorial content. STYLE.md's "we're a guide, not a booking engine" rule still applies to everything in `content/`; overlay content is a separate, clearly-labeled commercial layer, not a loophole for booking links in the ranked editorial voice.
- Not visible sitewide — v1 only surfaces overlay content on the location page(s) a feed is registered against. It never appears on the home page, the tag index, or anywhere else that scans the whole content tree.
- Not a booking/negotiation backend. The `action.handler` dispatch table is deliberately extensible, but nothing beyond a plain outbound link is implemented yet.
