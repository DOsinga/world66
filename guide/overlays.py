"""
External content overlays.

Third-party suppliers publish a JSON file describing extra POIs and
sections for one specific location (registered in overlay_sources.yaml
at the repo root). World66 fetches that file, converts each entry into
an ordinary Page, and merges it into the normal rendering pipeline —
build_city_tag_index() and Page.children() in models.py — so overlay
POIs show up in tagged section lists and on the map, and overlay
sections show up in the sidebar, exactly like native content.

Overlay content is never git-committed, never touches the filesystem,
and never participates in the sitewide aggregate views (home page,
tag index, story POIs) — it only appears on the location page(s) it is
registered against. A supplier feed that is slow, unreachable, or
malformed silently contributes nothing; it never breaks a page.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

import httpx
import yaml
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OVERLAY_REGISTRY_PATH = Path(settings.BASE_DIR) / "overlay_sources.yaml"

# Page types an overlay entry may declare.
_OVERLAY_PAGE_TYPES = {"poi", "section"}


@lru_cache(maxsize=1)
def _load_registry():
    """Load overlay_sources.yaml once per process.

    Each entry: {content_path, name, feed_url}. content_path is matched
    exactly against the city/feature/island page an overlay attaches to.
    """
    if not OVERLAY_REGISTRY_PATH.is_file():
        return []
    try:
        with open(OVERLAY_REGISTRY_PATH) as f:
            data = yaml.safe_load(f) or []
    except (OSError, yaml.YAMLError):
        logger.warning("Could not read overlay registry at %s", OVERLAY_REGISTRY_PATH)
        return []
    if not isinstance(data, list):
        return []
    entries = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if not entry.get("content_path") or not entry.get("feed_url") or not entry.get("name"):
            continue
        entries.append(entry)
    return entries


def _registry_entries_for(content_path):
    return [e for e in _load_registry() if e["content_path"] == content_path]


def fetch_overlay_feed(url):
    """Fetch and parse a supplier's overlay JSON. Soft-fails to None on any error."""
    timeout = getattr(settings, "OVERLAY_FETCH_TIMEOUT", 10)
    max_bytes = getattr(settings, "OVERLAY_MAX_RESPONSE_BYTES", 2_000_000)
    try:
        chunks = []
        total = 0
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    logger.warning("Overlay feed %s exceeded max size, discarding", url)
                    return None
                chunks.append(chunk)
        data = json.loads(b"".join(chunks).decode("utf-8"))
    except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Could not fetch overlay feed %s: %s", url, exc)
        return None
    if not isinstance(data, dict):
        return None
    return data


def _cached_fetch(url):
    """fetch_overlay_feed(), cached for OVERLAY_CACHE_TTL seconds.

    A failed fetch is cached too (as a sentinel), so an unreachable
    supplier doesn't get hit on every single page view.
    """
    cache_key = f"overlay_feed:{url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return None if cached == "__EMPTY__" else cached
    data = fetch_overlay_feed(url)
    ttl = getattr(settings, "OVERLAY_CACHE_TTL", 900)
    cache.set(cache_key, data if data is not None else "__EMPTY__", ttl)
    return data


def _validate_entry(entry, entry_type):
    if not isinstance(entry, dict):
        return False
    if entry_type not in _OVERLAY_PAGE_TYPES:
        return False
    if not entry.get("slug") or not entry.get("title"):
        return False
    if entry_type == "poi" and ("latitude" not in entry or "longitude" not in entry):
        return False
    return True


def overlay_entry_to_page(entry, entry_type, base_path, source_name):
    """Build a plain Page from one validated overlay JSON entry.

    Path is <content_path>/<slug> — the same shape a native section or POI
    would have — so links into overlay content look and resolve exactly
    like links into native content. This means an overlay section/POI slug
    must not collide with a real slug at that content_path (real content
    always wins; see resolve_overlay_route()), and if two suppliers are
    ever registered against the same content_path, their slugs must not
    collide with each other either — there's no per-supplier namespace.
    """
    from .models import Page  # deferred: models.py imports this module at load time

    slug = entry["slug"]
    meta = {k: v for k, v in entry.items() if k not in ("slug", "title", "body")}
    meta["is_overlay"] = True
    meta["overlay_source"] = source_name
    return Page(
        slug=slug,
        path=f"{base_path}/{slug}",
        title=entry["title"],
        page_type=entry_type,
        body=entry.get("body", ""),
        meta=meta,
    )


def load_overlay_for_path(content_path):
    """Fetch + convert every registered overlay feed for content_path.

    Returns (extra_sections, extra_pois), both lists of Page.
    """
    extra_sections = []
    extra_pois = []
    for reg in _registry_entries_for(content_path):
        data = _cached_fetch(reg["feed_url"])
        if not data:
            continue
        for entry in data.get("sections") or []:
            if _validate_entry(entry, "section"):
                extra_sections.append(
                    overlay_entry_to_page(entry, "section", content_path, reg["name"])
                )
            else:
                logger.warning("Skipping invalid overlay section from %s", reg["feed_url"])
        for entry in data.get("pois") or []:
            if _validate_entry(entry, "poi"):
                extra_pois.append(
                    overlay_entry_to_page(entry, "poi", content_path, reg["name"])
                )
            else:
                logger.warning("Skipping invalid overlay POI from %s", reg["feed_url"])
    return extra_sections, extra_pois


def resolve_overlay_route(path):
    """Resolve <content_path>/<slug> or <content_path>/<section_slug>/<poi_slug>
    for a registered overlay — used as a fallback once load_page() and
    resolve_tag_route() have both already failed to find a real file.

    Returns (page, context_nav) like resolve_tag_route() — context_nav is
    the overlay section when a POI was reached via city/section/poi, else
    None. Matched against the registry directly (not by walking the path
    upward) since a content_path is always registered exactly, never as
    a prefix that needs discovering.
    """
    for reg in _load_registry():
        base_path = reg["content_path"]
        prefix = base_path + "/"
        if not path.startswith(prefix):
            continue
        rest = path[len(prefix):].split("/")
        extra_sections, extra_pois = load_overlay_for_path(base_path)

        if len(rest) == 1:
            slug = rest[0]
            for page in extra_sections + extra_pois:
                if page.slug == slug:
                    return page, None

        elif len(rest) == 2:
            section_slug, poi_slug = rest
            section = next((s for s in extra_sections if s.slug == section_slug), None)
            if not section:
                continue
            from .models import build_city_tag_index  # deferred: avoids a cycle

            index = build_city_tag_index(base_path)
            for poi in index.get(section.nav_tag, []):
                if poi.slug == poi_slug:
                    return poi, section

    return None, None


def _handle_url_action(action):
    handler = action.get("handler") or {}
    target = handler.get("target")
    if not target:
        return None
    return {
        "label": action.get("label") or (action.get("type") or "").title() or "Open",
        "href": target,
        "target": "_blank",
    }


# Dispatch table for action.handler.kind. "url" is the only kind implemented
# today (renders a link/button); this is the extension point for a future
# server-side handler (e.g. a webhook proxy) without touching call sites.
ACTION_HANDLERS = {
    "url": _handle_url_action,
}


def resolve_action(action):
    """Turn an overlay POI's `action` dict into template-ready button data.

    Returns None (button omitted) on any unrecognized shape or handler
    kind, rather than raising — a malformed action must never break a page.
    """
    if not isinstance(action, dict):
        return None
    handler = action.get("handler") or {}
    kind = handler.get("kind")
    resolver = ACTION_HANDLERS.get(kind)
    if not resolver:
        logger.warning("Unknown overlay action handler kind: %r", kind)
        return None
    try:
        return resolver(action)
    except Exception:
        logger.exception("Overlay action handler %r raised", kind)
        return None
