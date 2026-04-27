import json
import re
import sqlite3
import subprocess
from pathlib import Path

import markdown as md
from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

from .models import (
    CONTENT_DIR, NAV_TYPES, build_city_tag_index, find_tagged_pois,
    load_page, load_page_from_branch, load_tag_index, resolve_tag_route, _find_city_path,
)

SEARCH_DB = Path(settings.BASE_DIR) / "search.db"


def home(request):
    from .models import load_continents
    continents_raw = load_continents()
    continents = []
    for cont, countries in continents_raw:
        sorted_countries = sorted(
            countries,
            key=lambda l: float(l.meta.get('score', 0) or 0),
            reverse=True,
        )
        # Use the continent's own image; fall back to top-scored country
        img = _image_path(cont)
        if not img:
            for country in sorted_countries[:10]:
                img = _image_path(country)
                if img:
                    break
        image_url = f'/content-image/{img}' if img else None
        continents.append({
            'page': cont,
            'countries': sorted_countries[:8],
            'total': len(countries),
            'image_url': image_url,
        })
    return render(request, "guide/home.html", {'continents': continents})


def location_or_section(request, path):
    path = path.strip("/")
    branch = request.GET.get('branch')

    page = load_page_from_branch(path, branch) if branch else load_page(path)
    context_nav = None  # nav page used to reach this POI (for sidebar context)

    if not page:
        # Try virtual tag-based routing: city/nav-slug/poi-slug
        page, context_nav = resolve_tag_route(path)

    if not page:
        raise Http404

    # Derive parent for nav/poi pages
    parent = None
    if page.page_type in NAV_TYPES | {"poi"} and "/" in page.path:
        parent_path = page.path.rsplit("/", 1)[0]
        parent = load_page(parent_path)

    # Build sidebar nav: nav_pages from the parent (city or section).
    # For POIs the immediate parent is the section, which has no nav children —
    # walk up one more level to the city so the sidebar shows all city sections.
    parent_nav = []
    parent_locations = []
    active_nav = None   # which nav item should be highlighted in the sidebar
    if parent and page.page_type != "neighbourhood":
        parent_nav, parent_locations, _ = parent.children()
        parent_nav = [p for p in parent_nav if p.page_type != "neighbourhood"]
        if page.page_type == "poi" and not parent_nav and "/" in parent.path:
            # Parent is a section with no nav children — use grandparent (city)
            grandparent = load_page(parent.path.rsplit("/", 1)[0])
            if grandparent and grandparent.page_type == "location":
                parent_nav, parent_locations, _ = grandparent.children()
                parent_nav = [p for p in parent_nav if p.page_type != "neighbourhood"]
                active_nav = parent   # mark the section as active in the sidebar

    # For a POI reached via a context nav page, build sidebar from that nav page
    nav_siblings = []
    if context_nav:
        nav_siblings = context_nav.tagged_pois()
        if active_nav is None:
            active_nav = context_nav  # highlight the context section in the city sidebar

    # Contextual URL prefix for POI links on nav pages (section/neighbourhood/theme).
    # Generates URLs like /city/de_pijp/albert_cuypmarkt instead of canonical /city/albert_cuypmarkt.
    poi_context_prefix = None
    _city_path = _find_city_path(page.path) if page.page_type in NAV_TYPES else None
    if page.page_type in NAV_TYPES and _city_path:
        poi_context_prefix = f"/{_city_path}/{page.slug}/"
    body_html = md.markdown(page.body) if page.body else ""

    # Normalise vibe time slots to a list; load any referenced POIs
    vibe_time_slots = []
    vibe_pois = []
    if page.page_type == "vibe":
        tday = page.meta.get("time_of_day", "")
        vibe_time_slots = tday if isinstance(tday, list) else ([tday] if tday else [])
        for poi_path in page.meta.get("pois", []):
            poi_page = load_page(poi_path)
            if poi_page:
                vibe_pois.append(poi_page)

    nav_pages, locations, pois = page.children()

    # Build the city tag index once so all tagged_pois() calls reuse it.
    # Only build for actual city-level pages: nav pages (sections), or location
    # pages that have sections but no child locations (cities, not countries/continents).
    city_tag_index = None
    _COLLECTS_POIS = NAV_TYPES | {"neighbourhood"}
    _cpath = _city_path if page.page_type in _COLLECTS_POIS else (
        page.path if nav_pages and not locations else None
    )
    if _cpath:
        city_tag_index = build_city_tag_index(_cpath)

    # Neighbourhoods, vibes and walks are type:poi with category + tags.
    neighbourhoods = city_tag_index.get("neighbourhoods", []) if city_tag_index else []
    neighbourhoods = [p for p in neighbourhoods if not p.meta.get("hide_from_city")]
    vibe_items = city_tag_index.get("vibes", []) if city_tag_index else []
    city_walk_items = city_tag_index.get("city_walks", []) if city_tag_index else []

    # Nav pages and neighbourhood pages collect their POIs by tag
    if page.page_type in _COLLECTS_POIS:
        pois = page.tagged_pois(_city_tag_index=city_tag_index)

    # Collect distinct categories from POIs (for filter UI)
    poi_categories = []
    if page.page_type in _COLLECTS_POIS and pois:
        poi_categories = sorted(set(p.category for p in pois if p.category))

    # Walk: load route coordinates and waypoint pages
    walk_route = []
    walk_waypoints = []
    if page.page_type == "walk":
        walk_route = page.meta.get("route", [])
        city_path = _find_city_path(page.path)
        if city_path:
            seen_paths = set()
            for wp_slug in page.meta.get("waypoints", []):
                wp = load_page(city_path + "/" + wp_slug)
                if wp and wp.path not in seen_paths:
                    seen_paths.add(wp.path)
                    walk_waypoints.append(wp)
            # Also include POIs linked in the body text that aren't already waypoints
            for link_path in re.findall(r'\]\((/[^)]+)\)', page.body or ''):
                link_path = link_path.strip('/')
                wp = load_page(link_path)
                if wp and wp.page_type == 'poi' and wp.path not in seen_paths:
                    seen_paths.add(wp.path)
                    walk_waypoints.append(wp)

    # Map context
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))

    path_parts = page.path.split("/")
    continent_slug = path_parts[0] if path_parts else None
    is_continent = len(path_parts) == 1 and page.page_type == "location"
    continent_bounds = page.meta.get("map_bounds") if is_continent else None
    page_map_bounds = page.meta.get("map_bounds") if not is_continent else None

    image_path = _image_path(page, branch)
    branch_qs = f'?branch={branch}' if branch else ''
    hero_image_url = f'/content-image/{image_path}{branch_qs}' if image_path else None
    hero_image_source = page.meta.get('image_source', '') if image_path else ''
    hero_image_license = page.meta.get('image_license', '') if image_path else ''

    # Attach image_url to each neighbourhood for card display
    for nb in neighbourhoods:
        nb_img = _image_path(nb, branch)
        nb.image_url = f'/content-image/{nb_img}{branch_qs}' if nb_img else None

    for d in vibe_items:
        d_img = _image_path(d, branch)
        d.image_url = f'/content-image/{d_img}{branch_qs}' if d_img else None
        tday = d.meta.get("time_of_day", "")
        d.time_slots = tday if isinstance(tday, list) else ([tday] if tday else [])
        d.primary_time = d.time_slots[0] if d.time_slots else ""

    # Sort locations by score descending, attach image_url and word_cloud, split into top 9 and rest
    locations = sorted(locations, key=lambda loc: float(loc.meta.get('score', 0) or 0), reverse=True)
    for loc in locations:
        loc_img = _image_path(loc, branch)
        loc.image_url = f'/content-image/{loc_img}{branch_qs}' if loc_img else None
        loc.card_children = []
        loc.card_children_total = 0
        if not loc.image_url:
            child_navs, child_locs, child_pois = loc.children()
            scored_locs = sorted(child_locs, key=lambda p: float(p.meta.get('score', 0) or 0), reverse=True)
            # Inherit image from highest-scoring child that has one
            for cl in scored_locs:
                cl_img = _image_path(cl, branch)
                if cl_img:
                    loc.image_url = f'/content-image/{cl_img}{branch_qs}'
                    loc.card_children = scored_locs[:5]
                    loc.card_children_total = len(scored_locs)
                    break
            # If still no image, build word cloud
            if not loc.image_url:
                children = (child_locs + child_pois)[:25]
                if len(children) >= 4:
                    top = max(children, key=lambda p: float(p.meta.get('score', 0) or 0))
                    rest = [p.title for p in children if p is not top][:24]
                    mid = len(rest) // 2
                    loc.word_cloud_center = top.title
                    loc.word_cloud_top = rest[:mid]
                    loc.word_cloud_bottom = rest[mid:]
                else:
                    loc.word_cloud_center = loc.title
                    loc.word_cloud_top = []
                    loc.word_cloud_bottom = [p.title for p in children]
    top_locations = locations[:9]
    more_locations = sorted(locations, key=lambda loc: loc.title)

    # Inspiration image strip for section pages — up to 12 POI images
    poi_images = []
    if page.page_type == "vibe":
        for poi in vibe_pois:
            img_path = _image_path(poi, branch)
            if img_path:
                poi_images.append({'url': f'/content-image/{img_path}{branch_qs}', 'title': poi.title, 'href': poi.get_absolute_url()})
    elif page.page_type in NAV_TYPES:
        for poi in pois:
            img_path = _image_path(poi, branch)
            if img_path:
                href = (poi_context_prefix + poi.slug) if poi_context_prefix else poi.get_absolute_url()
                poi_images.append({'url': f'/content-image/{img_path}{branch_qs}', 'title': poi.title, 'href': href})
            if len(poi_images) >= 12:
                break

    # Map markers: top 9 for initial view, all locations for dynamic zoom filtering
    markers = _collect_markers(page, nav_pages, top_locations, pois, city_tag_index=city_tag_index)
    markers_full = _collect_markers(page, nav_pages, locations, pois, city_tag_index=city_tag_index)

    # For vibe pages, build markers from the referenced POIs
    if page.page_type == "vibe" and vibe_pois:
        vibe_markers = [m for m in (_marker_from_page(p, highlight=True) for p in vibe_pois) if m]
        markers = vibe_markers
        markers_full = vibe_markers
        if lat is None and lng is None and vibe_markers:
            lat = vibe_markers[0]["lat"]
            lng = vibe_markers[0]["lng"]

    breadcrumbs = page.breadcrumbs()

    return render(request, "guide/page.html", {
        "page": page,
        "parent": parent,
        "sections": nav_pages,           # child nav pages of current page (location sidebar)
        "locations": locations,
        "top_locations": top_locations,
        "more_locations": more_locations,
        "neighbourhood_items": neighbourhoods,
        "vibe_items": vibe_items,
        "city_walk_items": city_walk_items,
        "vibe_time_slots": vibe_time_slots,
        "pois": pois,
        "parent_sections": parent_nav,   # sibling nav pages (section/poi sidebar)
        "parent_locations": parent_locations,
        "active_nav": active_nav,        # nav page to mark active (when POI bumped to grandparent nav)

        "context_nav": context_nav,
        "nav_siblings": nav_siblings,
        "body_html": body_html,
        "breadcrumbs": breadcrumbs,
        "lat": lat,
        "lng": lng,
        "continent_slug": continent_slug,
        "is_continent": is_continent,
        "continent_bounds": mark_safe(json.dumps(continent_bounds)) if continent_bounds else "null",
        "page_map_bounds": mark_safe(json.dumps(page_map_bounds)) if page_map_bounds else "null",
        "markers_json": mark_safe(json.dumps(markers)),
        "markers_full_json": mark_safe(json.dumps(markers_full)),
        "hero_image_url": hero_image_url,
        "hero_image_source": hero_image_source,
        "hero_image_license": hero_image_license,
        "walk_route": mark_safe(json.dumps(walk_route)),
        "walk_waypoints": walk_waypoints,
        "tags": [t.replace("_", " ") for t in page.tags],
        "is_poi": page.page_type == "poi",
        "poi_categories": poi_categories,
        "poi_context_prefix": poi_context_prefix,
        "poi_images": poi_images,
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


_SIGHT_SLUGS = {"sights", "museums", "attractions", "landmarks", "things_to_do"}


def _marker_from_page(page, highlight=False):
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "name": page.title,
                "url": page.get_absolute_url(), "highlight": highlight,
                "score": float(page.meta.get("score", 0) or 0)}
    return None


def _collect_markers(page, nav_pages, locations, pois, city_tag_index=None):
    markers = []
    seen = set()

    def add(m):
        if m and (m["lat"], m["lng"]) not in seen:
            seen.add((m["lat"], m["lng"]))
            markers.append(m)

    for loc in locations:
        add(_marker_from_page(loc))

    page_is_sight = page.slug in _SIGHT_SLUGS
    for poi in pois:
        poi_tags = set(poi.meta.get("tags") or [])
        if page.page_type == "location" and not poi_tags & _SIGHT_SLUGS:
            continue
        add(_marker_from_page(poi, highlight=page_is_sight))

    # Only collect POIs from nav sections when there are no child locations.
    # On continent/country/region pages the nav sections span the whole
    # hierarchy and would pull in POIs from cities across the entire region.
    # On city pages, restrict to sightseeing sections only so the map stays focused.
    if not locations:
        for nav in nav_pages:
            if nav.slug not in _SIGHT_SLUGS:
                continue
            for poi in nav.tagged_pois(_city_tag_index=city_tag_index):
                add(_marker_from_page(poi, highlight=True))

    return markers


def _image_path(page, branch=None):
    image = page.meta.get('image', '')
    if not image:
        return None
    for candidate in [
        f'{page.path}/{image}',
        f'{page.path.rsplit("/", 1)[0]}/{image}' if '/' in page.path else image,
    ]:
        if branch:
            result = subprocess.run(
                ['git', 'cat-file', '-e', f'{branch}:content/{candidate}'],
                capture_output=True, check=False, cwd=str(settings.BASE_DIR),
            )
            if result.returncode == 0:
                return candidate
        elif (CONTENT_DIR / candidate).is_file():
            return candidate
    return None


def content_image(request, path):
    branch = request.GET.get('branch')
    if branch:
        suffix = Path(path).suffix.lower()
        if suffix not in ('.jpg', '.jpeg', '.png', '.webp'):
            raise Http404
        result = subprocess.run(
            ['git', 'show', f'{branch}:content/{path}'],
            capture_output=True, check=False,
            cwd=str(settings.BASE_DIR),
        )
        if result.returncode != 0:
            raise Http404
        content_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
        from django.http import HttpResponse
        return HttpResponse(result.stdout, content_type=content_types[suffix])
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


_CONTINENT_SLUGS = {
    'europe', 'northamerica', 'southamerica', 'asia', 'africa',
    'australiaandpacific', 'middleeast', 'centralamerica', 'caribbean',
}


def _display_title_from_path(url_path):
    '''europe/ireland/cork/bars_and_cafes → "Cork - Bars and Cafes"'''
    parts = url_path.split('/')
    # Strip continent + country prefix so we start from region/city level
    if parts and parts[0] in _CONTINENT_SLUGS and len(parts) > 2:
        parts = parts[2:]
    return ' - '.join(p.replace('_', ' ').title() for p in parts)


def _get_file_diffs(branch):
    '''Run git diff once; return per-file list of up to 4 changed lines (+ added, - removed).'''
    result = subprocess.run(
        ['git', 'diff', '--unified=0', f'origin/main...{branch}', '--', 'content/'],
        capture_output=True, text=True, check=False,
        cwd=str(settings.BASE_DIR),
    )
    file_diffs = {}   # filepath → {'added': [...], 'removed': [...], 'more': bool}
    cur = None

    for raw in result.stdout.splitlines():
        if raw.startswith('+++ '):
            cur = raw[6:] if raw.startswith('+++ b/') else None  # None = deleted file
            if cur and cur not in file_diffs:
                file_diffs[cur] = {'added': [], 'removed': [], 'more': False}
        elif cur:
            if raw.startswith('+'):
                sign, text = '+', raw[1:].strip()
            elif raw.startswith('-') and not raw.startswith('---'):
                sign, text = '-', raw[1:].strip()
            else:
                continue
            # Skip YAML fence lines and empty
            if not text or text == '---':
                continue
            bucket = file_diffs[cur]['added' if sign == '+' else 'removed']
            if len(bucket) < 2:
                bucket.append(text)
            else:
                file_diffs[cur]['more'] = True

    return file_diffs


def review(request):
    '''Show all pages changed on a branch vs origin/main.'''
    branch = request.GET.get('branch', 'HEAD')
    result = subprocess.run(
        ['git', 'log', branch, '--not', 'origin/main',
         '--no-merges', '--name-only', '--format=COMMIT: %s', '--', 'content/'],
        capture_output=True, text=True, check=False,
        cwd=str(settings.BASE_DIR),
    )
    if result.returncode != 0:
        return render(request, 'guide/review.html', {'error': result.stderr.strip() or 'git log failed', 'branch': branch})

    del_result = subprocess.run(
        ['git', 'diff', f'origin/main...{branch}', '--name-only', '--diff-filter=D'],
        capture_output=True, text=True, check=False,
        cwd=str(settings.BASE_DIR),
    )
    deleted_files = set(del_result.stdout.splitlines())
    file_diffs = _get_file_diffs(branch)

    pages = _parse_review_log(result.stdout, deleted_files, file_diffs)
    return render(request, 'guide/review.html', {'pages': pages, 'error': None, 'branch': branch})


def _parse_review_log(output, deleted_files=None, file_diffs=None):
    deleted_files = deleted_files or set()
    file_diffs = file_diffs or {}
    pages = {}
    for line in output.splitlines():
        if not line.startswith('content/') or not line.endswith('.md'):
            continue
        raw = line.rstrip()
        url_path = _file_to_url_path(raw)
        if url_path in pages:
            continue
        is_deleted = raw in deleted_files
        diff = file_diffs.get(raw, {})
        pages[url_path] = {
            'url_path': url_path,
            'title': _display_title_from_path(url_path),
            'deleted': is_deleted,
            'added': diff.get('added', []),
            'removed': diff.get('removed', []),
            'more': diff.get('more', False),
        }
    return list(pages.values())


def _file_to_url_path(file_path):
    '''content/a/b/c/c.md → a/b/c  (collapses directory-index duplication)'''
    path = file_path.removeprefix('content/').removesuffix('.md')
    parts = path.split('/')
    if len(parts) >= 2 and parts[-1] == parts[-2]:
        parts = parts[:-1]
    return '/'.join(parts)


# ── Travel plans ──────────────────────────────────────────────────────────────

PLANS_DIR = Path(settings.BASE_DIR) / "plans"


def _parse_plan(path):
    """Load and parse a plan markdown file. Returns a dict or None."""
    import frontmatter as fm
    if not path.is_file():
        return None
    post = fm.load(path)
    slug = path.stem
    title = post.metadata.get("title", slug)
    stops = _parse_stops(post.content, slug)
    return {"slug": slug, "title": title, "body": post.content, "stops": stops}


def _parse_stops(body, plan_slug):
    """Parse plan markdown into stops, enriching each item with page data."""
    import re as _re
    stops = []
    current = None
    for line in body.splitlines():
        h2 = _re.match(r'^##\s+(.+)$', line)
        if h2:
            heading = h2.group(1)
            if '|' in heading:
                city, dates = heading.split('|', 1)
            else:
                city, dates = heading, ''
            city = city.strip()
            city_slug = city.lower().replace(' ', '-')
            current = {
                "city": city,
                "city_slug": city_slug,
                "dates": dates.strip(),
                "url": f"/plans/{plan_slug}/{city_slug}/",
                "items": [],
            }
            stops.append(current)
            continue
        if current is None:
            continue
        bullet = _re.match(r'^[-*]\s+(.+)$', line)
        if bullet:
            text = bullet.group(1).strip()
            page = load_page(text) if _re.match(r'^[\w/_-]+$', text) else None
            image_url = None
            if page:
                img = _image_path(page)
                if img:
                    image_url = f'/content-image/{img}'
            current["items"].append({
                "text": text,
                "page": page,
                "image_url": image_url,
            })
    return stops


def _stop_markers(stop):
    """Return JSON-serialisable marker list for a single stop."""
    markers = []
    for item in stop["items"]:
        page = item["page"]
        if page and page.meta.get("latitude") and page.meta.get("longitude"):
            markers.append({
                "lat": float(page.meta["latitude"]),
                "lng": float(page.meta["longitude"]),
                "title": page.title,
                "url": page.get_absolute_url(),
            })
    return markers


def plan_list(request):
    import frontmatter as fm
    plans = []
    for f in sorted(PLANS_DIR.glob("*.md")):
        post = fm.load(f)
        plans.append({"slug": f.stem, "title": post.metadata.get("title", f.stem)})
    return render(request, "guide/plan_list.html", {"plans": plans})


def plan_detail(request, slug):
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        raise Http404

    # One marker per stop — use centroid of its POIs
    stop_markers = []
    for stop in plan["stops"]:
        pts = _stop_markers(stop)
        if pts:
            lat = sum(m["lat"] for m in pts) / len(pts)
            lng = sum(m["lng"] for m in pts) / len(pts)
            stop_markers.append({
                "lat": lat, "lng": lng,
                "title": stop["city"], "dates": stop["dates"],
                "url": stop["url"],
            })

    return render(request, "guide/plan_detail.html", {
        "plan": plan,
        "stop_markers": mark_safe(json.dumps(stop_markers)),
    })


def plan_stop(request, slug, city_slug):
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        raise Http404
    stop = next((s for s in plan["stops"] if s["city_slug"] == city_slug), None)
    if not stop:
        raise Http404
    markers = _stop_markers(stop)
    return render(request, "guide/plan_stop.html", {
        "plan": plan,
        "stop": stop,
        "markers": mark_safe(json.dumps(markers)),
    })
