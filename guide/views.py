import json
import sqlite3
from functools import lru_cache
from pathlib import Path

import markdown as md
from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe

from .models import (
    CONTENT_DIR, NAV_TYPES, find_tagged_pois,
    load_page, load_tag_index, resolve_tag_route,
)

SEARCH_DB = Path(settings.BASE_DIR) / "search.db"


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
    context_nav = None  # nav page used to reach this POI (for sidebar context)

    if not page:
        # Try virtual tag-based routing: city/nav-slug/poi-slug
        page, context_nav = resolve_tag_route(path)

    if not page:
        redirects = _load_redirects()
        new_path = redirects.get(path)
        if new_path:
            return redirect("/" + new_path, permanent=True)
        raise Http404

    # Derive parent for nav/poi pages
    parent = None
    if page.page_type in NAV_TYPES | {"poi"} and "/" in page.path:
        parent_path = page.path.rsplit("/", 1)[0]
        parent = load_page(parent_path)

    # Build sidebar nav: nav_pages from the parent (city or section_group).
    # For POIs the immediate parent is the section, which has no nav children —
    # walk up one more level to the city so the sidebar shows all city sections.
    parent_nav = []
    parent_locations = []
    active_nav = None   # which nav item should be highlighted in the sidebar
    if parent:
        parent_nav, parent_locations, _ = parent.children()
        if page.page_type == "poi" and not parent_nav and "/" in parent.path:
            # Parent is a section with no nav children — use grandparent (city)
            grandparent = load_page(parent.path.rsplit("/", 1)[0])
            if grandparent and grandparent.page_type == "location":
                parent_nav, parent_locations, _ = grandparent.children()
                active_nav = parent   # mark the section as active in the sidebar

    # For a POI reached via a context nav page, build sidebar from that nav page
    nav_siblings = []
    if context_nav:
        nav_siblings = context_nav.tagged_pois()

    # Neighbourhood sidebar context (for PR #105 Amsterdam content)
    neighbourhood_page = None
    neighbourhood_pois = []
    if page.page_type == "poi":
        from .models import find_neighbourhood_page
        neighbourhood_title = page.meta.get("neighbourhood")
        if neighbourhood_title and parent and "/" in parent.path:
            city_path = parent.path.rsplit("/", 1)[0]
            neighbourhood_page = find_neighbourhood_page(city_path, neighbourhood_title)
            if neighbourhood_page:
                neighbourhood_pois = neighbourhood_page.neighbourhood_pois()
        elif parent and parent.page_type == "neighbourhood":
            neighbourhood_page = parent
            neighbourhood_pois = parent.neighbourhood_pois()

    body_html = md.markdown(page.body) if page.body else ""
    nav_pages, locations, pois = page.children()

    # Nav pages collect their POIs by tag
    if page.page_type in NAV_TYPES:
        pois = page.tagged_pois()

    # Collect distinct categories from POIs (for filter UI)
    poi_categories = []
    if page.page_type in NAV_TYPES and pois:
        poi_categories = sorted(set(p.category for p in pois if p.category))

    # Group nav_pages by type for the sidebar template
    nav_grouped = _group_nav_pages(nav_pages)

    # Map context
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))

    path_parts = page.path.split("/")
    continent_slug = path_parts[0] if path_parts else None
    is_continent = len(path_parts) == 1 and page.page_type == "location"

    markers = _collect_markers(page, nav_pages, locations, pois)

    image_path = _image_path(page)
    hero_image_url = f'/content-image/{image_path}' if image_path else None
    hero_image_source = page.meta.get('image_source', '') if image_path else ''
    hero_image_license = page.meta.get('image_license', '') if image_path else ''

    return render(request, "guide/page.html", {
        "page": page,
        "parent": parent,
        "sections": nav_pages,           # child nav pages of current page (location sidebar)
        "locations": locations,
        "pois": pois,
        "parent_sections": parent_nav,   # sibling nav pages (section/poi sidebar)
        "parent_locations": parent_locations,
        "active_nav": active_nav,        # nav page to mark active (when POI bumped to grandparent nav)
        "nav_grouped": nav_grouped,
        "context_nav": context_nav,
        "nav_siblings": nav_siblings,
        "body_html": body_html,
        "breadcrumbs": page.breadcrumbs(),
        "lat": lat,
        "lng": lng,
        "continent_slug": continent_slug,
        "is_continent": is_continent,
        "markers_json": mark_safe(json.dumps(markers)),
        "hero_image_url": hero_image_url,
        "hero_image_source": hero_image_source,
        "hero_image_license": hero_image_license,
        "tags": page.tags,
        "is_poi": page.page_type == "poi",
        "poi_categories": poi_categories,
        "neighbourhood_page": neighbourhood_page,
        "neighbourhood_pois": neighbourhood_pois,
    })


def search(request):
    query = request.GET.get("q", "").strip()
    has_db = SEARCH_DB.is_file()
    return render(request, "guide/search.html", {
        "query": query,
        "has_db": has_db,
    })


def search_api(request):
    query = request.GET.get("q", "").strip()
    if not query or not SEARCH_DB.is_file():
        return JsonResponse({"results": []})

    conn = sqlite3.connect(f"file:{SEARCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        words = query.split()
        parts = ['"' + w.replace('"', '""') + '"' for w in words[:-1]]
        parts.append('"' + words[-1].replace('"', '""') + '"*')
        fts_query = " ".join(parts)
        rows = conn.execute(
            """SELECT title, url_path, page_type, location
               FROM docs
               WHERE docs MATCH ?
               ORDER BY
                   CASE WHEN lower(title) = lower(?) THEN 0
                        WHEN lower(title) LIKE (lower(?) || '%') THEN 1
                        ELSE 2
                   END,
                   rank
               LIMIT 30""",
            (fts_query, query, query),
        ).fetchall()
        results = [
            {"title": row["title"], "url": "/" + row["url_path"],
             "page_type": row["page_type"], "location": row["location"] or ""}
            for row in rows
        ]
    except sqlite3.OperationalError:
        results = []
    finally:
        conn.close()

    return JsonResponse({"results": results})


def tag_index(request, tag):
    index = load_tag_index()
    pages = index.get(tag, [])
    if not pages and tag not in index:
        raise Http404
    return render(request, "guide/tag.html", {"tag": tag, "pages": pages})


def _group_nav_pages(nav_pages):
    """Group a flat list of nav pages by type for sidebar rendering.

    Returns a list of (group_label, [pages]) tuples, where section_group
    pages become group headers with their children listed beneath them.
    Plain sections are returned as (None, [page]) single-item groups.
    """
    groups = []
    group_types = {}
    for p in nav_pages:
        if p.page_type == "section_group":
            group_types[p.slug] = p
        else:
            groups.append(p)
    # For now return flat — template can check page_type directly
    return nav_pages


_SIGHT_SLUGS = {"sights", "museums", "attractions", "beaches", "landmarks", "things_to_do"}


def _marker_from_page(page, highlight=False):
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "name": page.title,
                "url": page.get_absolute_url(), "highlight": highlight}
    return None


def _collect_markers(page, nav_pages, locations, pois):
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

    for nav in nav_pages:
        if nav.page_type == "section_group":
            continue
        is_sight = nav.slug in _SIGHT_SLUGS
        for poi in nav.tagged_pois():
            add(_marker_from_page(poi, highlight=is_sight))

    return markers


def _image_path(page):
    image = page.meta.get('image', '')
    if not image:
        return None
    for candidate in [
        f'{page.path}/{image}',
        f'{page.path.rsplit("/", 1)[0]}/{image}' if '/' in page.path else image,
    ]:
        if (CONTENT_DIR / candidate).is_file():
            return candidate
    return None


def content_image(request, path):
    file_path = (CONTENT_DIR / path).resolve()
    if not file_path.is_relative_to(CONTENT_DIR.resolve()):
        raise Http404
    if not file_path.is_file() or file_path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise Http404
    return FileResponse(open(file_path, 'rb'))


def _safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
