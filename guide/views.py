import json
from functools import lru_cache
from pathlib import Path

import markdown as md
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe

from .models import load_page, load_tag_index, load_search_index


@lru_cache(maxsize=1)
def _load_redirects():
    redirects_file = Path(settings.BASE_DIR) / "redirects.json"
    if redirects_file.exists():
        return json.loads(redirects_file.read_text())
    return {}


def home(request):
    return render(request, "guide/home.html")


def location_or_section(request, path):
    path = path.strip("/")

    page = load_page(path)
    if not page:
        # Check redirects (flattened sub-regions)
        redirects = _load_redirects()
        new_path = redirects.get(path)
        if new_path:
            return redirect("/" + new_path, permanent=True)
        raise Http404

    # Derive parent for section/poi pages
    parent = None
    if page.page_type in ("section", "poi") and "/" in page.path:
        parent_path = page.path.rsplit("/", 1)[0]
        parent = load_page(parent_path)

    parent_sections = []
    parent_locations = []
    if parent:
        parent_sections, parent_locations, _ = parent.children()

    body_html = md.markdown(page.body) if page.body else ""
    sections, locations, pois = page.children()

    # For section pages, load POIs
    if page.page_type == "section":
        pois = page.pois()

    # Collect distinct categories from POIs (for filter UI)
    poi_categories = []
    if page.page_type == "section" and pois:
        poi_categories = sorted(set(p.category for p in pois if p.category))

    # Map context — validate lat/lng as floats
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))

    path_parts = page.path.split("/")
    continent_slug = path_parts[0] if path_parts else None
    is_continent = len(path_parts) == 1 and page.page_type == "location"

    # Collect map markers from children
    markers = _collect_markers(page, sections, locations, pois)

    return render(request, "guide/page.html", {
        "page": page,
        "parent": parent,
        "sections": sections,
        "locations": locations,
        "pois": pois,
        "parent_sections": parent_sections,
        "parent_locations": parent_locations,
        "body_html": body_html,
        "breadcrumbs": page.breadcrumbs(),
        "lat": lat,
        "lng": lng,
        "continent_slug": continent_slug,
        "is_continent": is_continent,
        "markers_json": mark_safe(json.dumps(markers)),
        "tags": page.tags,
        "is_poi": page.page_type == "poi",
        "poi_categories": poi_categories,
    })


def search(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        q_lower = query.lower()
        index = load_search_index()
        results = [
            {"title": title, "url": "/" + url_path, "page_type": page_type}
            for title_lower, title, url_path, page_type in index
            if q_lower in title_lower
        ]
        results.sort(key=lambda r: (not r["title"].lower().startswith(q_lower), r["title"].lower()))
    return render(request, "guide/search.html", {"query": query, "results": results})


def tag_index(request, tag):
    index = load_tag_index()
    pages = index.get(tag, [])
    if not pages and tag not in index:
        raise Http404
    return render(request, "guide/tag.html", {"tag": tag, "pages": pages})


_SIGHT_SLUGS = {"sights", "museums", "attractions", "beaches", "landmarks", "things_to_do"}


def _marker_from_page(page, highlight=False):
    """Extract a map marker dict from a page, or None if no coords."""
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "name": page.title, "url": page.get_absolute_url(), "highlight": highlight}
    return None


def _collect_markers(page, sections, locations, pois):
    """Collect map markers from child pages.

    For locations: markers come from child locations (cities in a country).
    For sections: markers come from POIs.
    Also gathers POIs from all sections (including their subdirectories).
    Sights-section POIs are flagged highlight=True.
    """
    markers = []
    seen = set()

    def add(m):
        if m and (m["lat"], m["lng"]) not in seen:
            seen.add((m["lat"], m["lng"]))
            markers.append(m)

    for loc in locations:
        add(_marker_from_page(loc))

    for poi in pois:
        add(_marker_from_page(poi))

    # Gather POIs from inside each section's subdirectory
    for section in sections:
        is_sight = section.slug in _SIGHT_SLUGS
        for poi in section.pois():
            add(_marker_from_page(poi, highlight=is_sight))

    return markers


def _safe_float(value):
    """Return value as float, or None if invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
