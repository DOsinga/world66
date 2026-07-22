"""
Proxy to tab.bi's trip-planning API for the "Add to Trip" button.

Unlike guide/overlays.py, tab.bi supplies no content of its own — it just
lets a visitor add an existing world66 POI or place to one of their tab.bi
trips. Every call is proxied server-side (never called directly from
browser JS) because tab.bi's write endpoint doesn't send CORS headers,
and to keep the partner base URL and error handling in one place.

Auth on tab.bi's side is a passphrase per trip, not an account/login — a
plan is only reachable by whoever knows its passphrase.
"""

import json
import logging
import re
import unicodedata

import httpx
from django.conf import settings

from .models import load_page

logger = logging.getLogger(__name__)


def _tabbi_slugify(text):
    """Exact mirror of tab.bi's own _slugify() (plans/views.py _slugify).

    tab.bi's city_slug is a hyphenated slug of a stop's display title, not
    a world66 path segment ("Chiang Mai" -> "chiang-mai", not "chiangmai").
    Sending anything else would silently create a duplicate stop instead
    of adding to the existing one, so this must match byte-for-byte.
    """
    nfd = unicodedata.normalize("NFD", text.lower())
    ascii_text = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def _post(path, payload):
    """POST JSON to tab.bi and return the parsed response.

    tab.bi returns a JSON body (with an "error" key) even on 4xx statuses
    (e.g. a wrong passphrase, or a full stop) — that's a legitimate answer,
    not a failure, so it's read and passed through rather than swallowed.
    Only a genuine network/timeout/malformed-response problem soft-fails
    to a generic {"error": ...} — a slow or unreachable tab.bi must never
    break the page it's called from.
    """
    base_url = getattr(settings, "TABBI_BASE_URL", "https://tab.bi")
    timeout = getattr(settings, "TABBI_TIMEOUT", 10)
    url = f"{base_url.rstrip('/')}{path}"
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("Tab.bi request to %s failed: %s", url, exc)
        return {"error": "Could not reach tab.bi. Please try again later."}
    if not isinstance(data, dict):
        return {"error": "Unexpected response from tab.bi."}
    return data


def list_plans(passphrase):
    """Look up the trip(s) matching a passphrase. Returns {"plans": [...]} or {"error": ...}."""
    return _post("/api/plans", {"passphrase": passphrase})


def add_to_trip(passphrase, plan_slug, city_path, poi_path):
    """Add one world66 content path (a POI, or a place's own path) to a trip's stop.

    city_path is a world66 content path (e.g. a POI's parent city, or a
    place's own path when adding the place itself) — its title is looked
    up and slugified the way tab.bi slugifies a stop heading, since tab.bi's
    city_slug has nothing to do with world66's own path segments. tab.bi
    auto-creates the stop if that slug isn't already in the plan.

    On success, attaches a trip_url built from settings.TABBI_BASE_URL so
    the partner host never has to be known by client-side JS.
    """
    city_page = load_page(city_path)
    if not city_page:
        return {"error": "Could not resolve that place."}
    city_slug = _tabbi_slugify(city_page.title)

    result = _post("/api/plan/add-pois", {
        "plan_slug": plan_slug,
        "city_slug": city_slug,
        "poi_paths": [poi_path],
        "passphrase": passphrase,
    })
    if "error" not in result:
        base_url = getattr(settings, "TABBI_BASE_URL", "https://tab.bi").rstrip("/")
        result["trip_url"] = f"{base_url}/plans/{plan_slug}/{city_slug}/"
    return result
