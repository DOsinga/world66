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
    if page:
        return page_view(request, page)

    # Try as a section/poi (last segment is the page, parent is the location)
    if "/" in path:
        parent_path, slug = path.rsplit("/", 1)
        parent = load_page(parent_path)
        if parent:
            # Look for slug.md in parent's directory
            from .models import CONTENT_DIR, _load_page_from_file
            md_file = CONTENT_DIR / parent_path / f"{slug}.md"
            if md_file.is_file():
                page = _load_page_from_file(md_file, path)
                if page:
                    return page_view(request, page, parent=parent)

    raise Http404


def page_view(request, page, parent=None):
    body_html = md.markdown(page.body) if page.body else ""
    sections, locations, pois = page.children()

    # For section/poi pages, load parent's sections for the sidebar
    if page.page_type in ("section", "poi") and not parent:
        # Derive parent from path
        if "/" in page.path:
            parent_path = page.path.rsplit("/", 1)[0]
            parent = load_page(parent_path)

    parent_sections = []
    if parent:
        parent_sections, _, _ = parent.children()

    # For section pages, load POIs
    if page.page_type == "section":
        pois = page.pois()

    # Map context
    lat = page.meta.get("latitude")
    lng = page.meta.get("longitude")
    # For continent pages, pass the slug for the country map
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
