import json
from functools import lru_cache
from pathlib import Path

import markdown as md
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe

from .models import CONTENT_DIR, load_page


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

    # Map context — validate lat/lng as floats
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))

    path_parts = page.path.split("/")
    continent_slug = path_parts[0] if path_parts else None
    is_continent = len(path_parts) == 1 and page.page_type == "location"

    # Collect map markers from children
    markers = _collect_markers(page, sections, locations, pois)

    # Build hero image URL if page has an image
    hero_image_url = None
    img_rel = _image_path(page)
    if img_rel:
        hero_image_url = f'/content-image/{img_rel}'

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
        "hero_image_url": hero_image_url,
    })


def _marker_from_page(page):
    """Extract a map marker dict from a page, or None if no coords."""
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "name": page.title, "url": page.get_absolute_url()}
    return None


def _collect_markers(page, sections, locations, pois):
    """Collect map markers from child pages.

    For locations: markers come from child locations (cities in a country).
    For sections: markers come from POIs.
    Also gathers POIs from all sections (including their subdirectories).
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
        for poi in section.pois():
            add(_marker_from_page(poi))

    return markers


def _image_path(page):
    """Build the content-relative path to a page's hero image."""
    image = page.meta.get('image', '')
    if not image:
        return None
    # Check both possible locations for the image file
    for candidate in [
        f'{page.path}/{image}',                                          # inside directory
        f'{page.path.rsplit("/", 1)[0]}/{image}' if '/' in page.path else image,  # next to .md
    ]:
        if (CONTENT_DIR / candidate).is_file():
            return candidate
    return None


def content_image(request, path):
    """Serve an image file from the content directory."""
    file_path = (CONTENT_DIR / path).resolve()
    if not file_path.is_relative_to(CONTENT_DIR.resolve()):
        raise Http404
    if not file_path.is_file() or file_path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise Http404
    return FileResponse(open(file_path, 'rb'))


def _safe_float(value):
    """Return value as float, or None if invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
