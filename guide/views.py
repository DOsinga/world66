import markdown as md
from django.http import Http404
from django.shortcuts import render

from .models import load_continents, load_page


def home(request):
    continents = load_continents()
    return render(request, "guide/home.html", {"continents": continents})


def location_or_section(request, path):
    path = path.strip("/")

    page = load_page(path)
    if not page:
        raise Http404

    # Derive parent for section/poi pages
    parent = None
    if page.page_type in ("section", "poi") and "/" in page.path:
        parent_path = page.path.rsplit("/", 1)[0]
        parent = load_page(parent_path)

    parent_sections = []
    if parent:
        parent_sections, _, _ = parent.children()

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

    return render(request, "guide/page.html", {
        "page": page,
        "parent": parent,
        "sections": sections,
        "locations": locations,
        "pois": pois,
        "parent_sections": parent_sections,
        "body_html": body_html,
        "breadcrumbs": page.breadcrumbs(),
        "lat": lat,
        "lng": lng,
        "continent_slug": continent_slug,
        "is_continent": is_continent,
    })


def _safe_float(value):
    """Return value as float, or None if invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
