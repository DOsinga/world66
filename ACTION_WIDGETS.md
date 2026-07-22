# Action Widgets

Action widgets let a third party add an *action* to content that already exists on world66 — without supplying any content of its own. This is the mechanism for something like "add this place to a trip in another app": world66 has no idea what the action does, and doesn't need to. Contrast with [OVERLAYS.md](OVERLAYS.md), where a supplier *provides* extra POIs/sections for one specific location — an action widget instead reaches every POI and location page on the site, and does nothing but call out to its own, separately-hosted script.

## How it works

1. A widget author hosts their own JS file, wherever they like.
2. We register `{name, script_url}` in `action_widgets.yaml` (repo root), via normal PR review.
3. World66 renders a small, inert `<span class="w66-place">` element next to every POI and location page, carrying that place's content path, title, and type as `data-*` attributes — see below. It carries no visible UI and no behavior of its own.
4. World66 includes each registered widget's `<script src="...">` tag once per page, after every `.w66-place` element already exists in the DOM.
5. Everything else — finding those elements, deciding what to render, handling clicks, authenticating, calling its own API — is the widget's own code, running against its own domain. World66's Python never sees a widget's API shape, auth model, or ID scheme.

See `guide/action_widgets.py` for the (deliberately tiny) implementation — it only loads the registry file. There is no fetching, caching, or partner-specific logic anywhere in world66's code.

## Registering a widget

Add one entry to `action_widgets.yaml`:

```yaml
- name: example-widget
  script_url: https://example.com/w66-widget.js
  display_name: Example Widget
```

`name` just needs to be unique in the registry (used in the rendered `data-w66-widget` attribute, and as the value posted by the visitor toggle described below). `script_url` is included verbatim as a `<script src="...">` — world66 does not fetch, inspect, or cache it. Optional `display_name` is shown instead of `name` in the visitor-facing toggle.

## The `.w66-place` contract

Rendered once per POI (in every POI list row, and on a POI's own detail page) and once per location page (city, feature, island, country — every `loc_type`, not just some of them; a widget decides for itself what it cares about):

```html
<span class="w66-place"
      data-path="asia/thailand/chiangmai/huen_phen"
      data-title="Huen Phen"
      data-type="poi"
      data-parent-path="asia/thailand/chiangmai"></span>
```

| Attribute | Meaning |
|---|---|
| `data-path` | This place's own world66 content path. |
| `data-title` | This place's display title. |
| `data-type` | `"poi"` or `"location"`. |
| `data-loc-type` | Location pages only: `country`, `region`, `city`, `feature`, or `island` (from the page's own `loc_type` frontmatter) — use this to decide which granularity your widget cares about. |
| `data-parent-path` | The nearest ancestor location's content path (a POI's containing city/feature/island, or a location's own path). World66 computes this because a widget can't reliably re-derive "nearest ancestor *location*" from the path string alone — path segments can be sections or features too, not just locations. |

Your `<script>` tag executes after every `.w66-place` element on the page already exists in the DOM (world66 places the script includes at the end of the page), so a normal, synchronous script can simply run:

```js
document.querySelectorAll('.w66-place').forEach(function (el) {
  // render whatever UI you want into/near el, using el.dataset.path etc.
});
```

## Letting a visitor turn a widget off

Any page shows a "Place action widgets" disclosure (next to the equivalent "Partner listings" one for overlay suppliers — see [OVERLAYS.md](OVERLAYS.md)) whenever at least one widget is registered at all, with one checkbox per registered widget (labelled "Show {display_name}"). Unchecking a box and saving stops that widget's `<script>` tag from being included on any subsequent page — the widget's own script never loads, so it can't run at all, rather than world66 asking it to hide itself. The preference is stored in the visitor's session (same signed-cookie mechanism as the overlay toggle, no database) and defaults to every widget shown for a fresh visitor. Mechanically: `guide/action_widgets.py`'s `active_widgets()` filters `registered_widgets()` against `request.session[action_widgets.SESSION_KEY]`; the toggle form posts to `/action-widget-prefs`.

## What this means for CORS

Your script tag executes in **world66.ai's** page origin, not yours — hosting the script file on your own domain does not change that. Any `fetch()` your widget makes back to your own API is still a cross-origin browser request from world66.ai, and is subject to normal CORS rules. If your widget needs to call your own API from the browser, **your API must send its own `Access-Control-Allow-Origin` headers** — this is entirely your responsibility; world66 has no server-side proxy for widget traffic and won't add one per partner.

## What action widgets are not

- Not a way to supply content — see [OVERLAYS.md](OVERLAYS.md) for that.
- Not something world66 filters or judges eligibility for — every POI and every location page (any `loc_type`) gets a `.w66-place` element; a widget decides what it wants to act on using `data-type`/`data-loc-type`.
- Not a server-side integration of any kind — world66 renders a DOM hook and a `<script>` tag and nothing else. No world66 Python code should ever know a specific partner's API shape, auth model, or ID scheme; if a partner's contract can't be satisfied by a client-side script alone, it doesn't fit this mechanism.
