import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
from functools import wraps
from pathlib import Path

import markdown as md
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

_PASSWORDS_FILE = Path(settings.BASE_DIR) / "plans" / ".passwords.json"


def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"{salt}${h.hex()}"


def _check_password(password, stored):
    salt, _ = stored.split("$", 1)
    return secrets.compare_digest(_hash_password(password, salt), stored)


def _load_passwords():
    if not _PASSWORDS_FILE.is_file():
        return {}
    return json.loads(_PASSWORDS_FILE.read_text())


def _save_password(slug, password):
    data = _load_passwords()
    data[slug] = _hash_password(password)
    _PASSWORDS_FILE.write_text(json.dumps(data))


def _plan_authenticated(request, slug):
    return slug in request.session.get("authenticated_plans", [])


def _mark_plan_authenticated(request, slug):
    plans = request.session.get("authenticated_plans", [])
    if slug not in plans:
        plans = plans + [slug]
        request.session["authenticated_plans"] = plans


def _require_plan_auth(view_fn):
    @wraps(view_fn)
    def wrapper(request, slug, *args, **kwargs):
        passwords = _load_passwords()
        if slug not in passwords:
            return HttpResponseRedirect(f"/auth/signup/{slug}/")
        if not _plan_authenticated(request, slug):
            return HttpResponseRedirect(f"/auth/login/{slug}/?next={request.path}")
        return view_fn(request, slug, *args, **kwargs)
    return wrapper


def auth_signup(request, slug):
    passwords = _load_passwords()
    if slug in passwords:
        return HttpResponseRedirect(f"/auth/login/{slug}/")
    # Check the plan actually exists
    if not (Path(settings.BASE_DIR) / "plans" / f"{slug}.md").is_file():
        raise Http404
    error = None
    if request.method == "POST":
        pw = request.POST.get("password", "")
        pw2 = request.POST.get("password2", "")
        if len(pw) < 6:
            error = "Choose at least 6 characters."
        elif pw != pw2:
            error = "Passwords don't match."
        else:
            _save_password(slug, pw)
            _mark_plan_authenticated(request, slug)
            return HttpResponseRedirect(f"/plans/{slug}/")
    plan_title = _plan_title(slug)
    return render(request, "guide/signup.html", {"error": error, "slug": slug, "plan_title": plan_title})


def auth_login(request, slug):
    passwords = _load_passwords()
    if slug not in passwords:
        return HttpResponseRedirect(f"/auth/signup/{slug}/")
    error = None
    next_url = request.GET.get("next", f"/plans/{slug}/")
    if request.method == "POST":
        next_url = request.POST.get("next", next_url)
        if _check_password(request.POST.get("password", ""), passwords[slug]):
            _mark_plan_authenticated(request, slug)
            return HttpResponseRedirect(next_url)
        error = "Wrong passphrase."
    plan_title = _plan_title(slug)
    return render(request, "guide/login.html", {"error": error, "next": next_url, "slug": slug, "plan_title": plan_title})


def auth_logout(request):
    request.session.flush()
    return HttpResponseRedirect("/")


def _authenticated_plan_stops(request):
    """Return list of {slug, title, stops, poi_paths} for authenticated plans."""
    result = []
    for slug in request.session.get("authenticated_plans", []):
        plan = _parse_plan(PLANS_DIR / f"{slug}.md")
        if plan:
            poi_paths = {item["text"] for s in plan["stops"] for item in s["items"]}
            result.append({
                "slug": slug,
                "title": plan["title"],
                "stops": [{"city": s["city"], "city_slug": s["city_slug"], "url": s["url"]} for s in plan["stops"]],
                "poi_paths": poi_paths,
            })
    return result


def _plan_title(slug):
    import frontmatter as fm
    path = Path(settings.BASE_DIR) / "plans" / f"{slug}.md"
    if not path.is_file():
        return slug
    return fm.load(path).metadata.get("title", slug)

from .models import (
    CONTENT_DIR, NAV_TYPES, build_city_tag_index, find_tagged_pois,
    load_page, load_page_from_branch, load_tag_index, resolve_tag_route, _find_city_path,
    resolve_location_name,
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
        "plan_stops": _authenticated_plan_stops(request),
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
                city_part, dates = heading.split('|', 1)
            else:
                # Auto-detect date: find first occurrence of a day number or month name.
                # Month names must end at a word boundary to avoid matching city names
                # like "Marseille" (starts with "Mar").
                _months = (r'(?:january|february|march|april|may|june|july|august'
                           r'|september|october|november|december'
                           r'|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b')
                _date_re = _re.compile(
                    rf'\b(\d{{1,2}}\s+{_months}|{_months}\s+\d{{1,2}})',
                    _re.IGNORECASE,
                )
                _dm = _date_re.search(heading)
                if _dm:
                    city_part = heading[:_dm.start()]
                    dates = heading[_dm.start():]
                else:
                    city_part, dates = heading, ''
            city_part = city_part.strip()
            # Resolve city name to a content path (e.g. "Palo Alto" → "northamerica/…/paloalto")
            # If it already looks like a content path (contains /), use it directly
            if '/' in city_part:
                city_path = city_part
                city_name = city_part.split('/')[-1].replace('_', ' ').title()
            else:
                city_name = city_part
                city_path = resolve_location_name(city_part)
            city_slug = city_name.lower().replace(' ', '-')
            current = {
                "city": city_name,
                "city_slug": city_slug,
                "city_path": city_path,
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
            # Support internal paths, absolute URLs, and relative /paths
            page = None
            external_url = None
            display_label = None
            display_domain = None
            if _re.match(r'^https?://', text):
                external_url = text
                from urllib.parse import urlparse as _urlparse
                _p = _urlparse(text)
                display_domain = _p.netloc.lstrip('www.')
                display_path = (_p.path.rstrip('/').rsplit('/', 1)[-1].replace('-', ' ').replace('_', ' ').title()
                                if _p.path and _p.path != '/' else '')
                display_label = display_path or display_domain
            elif text.startswith('/'):
                page = load_page(text.lstrip('/'))
            elif _re.match(r'^[\w/_-]+$', text):
                page = load_page(text)
            image_url = None
            if page:
                img = _image_path(page)
                if img:
                    image_url = f'/content-image/{img}'
            current["items"].append({
                "text": text,
                "page": page,
                "external_url": external_url,
                "display_label": display_label if external_url else None,
                "display_domain": display_domain if external_url else None,
                "image_url": image_url,
            })

    # Derive destination URL: prefer resolved city_path, fall back to first POI's parent
    for stop in stops:
        if stop.get("city_path"):
            stop["destination_url"] = "/" + stop["city_path"]
        else:
            dest_url = None
            for item in stop["items"]:
                if item["page"] and "/" in item["page"].path:
                    dest_url = "/" + item["page"].path.rsplit("/", 1)[0]
                    break
            stop["destination_url"] = dest_url

    return stops


_GEOCACHE_FILE = Path(settings.BASE_DIR) / "plans" / ".geocache.json"


def _load_geocache():
    if _GEOCACHE_FILE.exists():
        try:
            return json.loads(_GEOCACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_geocache(cache):
    _GEOCACHE_FILE.write_text(json.dumps(cache, indent=2))


def _geocode_nominatim(query):
    """Return (lat, lng) from Nominatim, or None on failure."""
    import urllib.request
    import urllib.parse
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "World66/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def _city_coords(stop):
    """Return (lat, lng) for a stop's city, geocoding if necessary."""
    city_path = stop.get("city_path")
    city_name = stop.get("city", "")
    cache_key = f"city:{city_path or city_name}"

    if city_path:
        city_page = load_page(city_path)
        if city_page and city_page.meta.get("latitude") and city_page.meta.get("longitude"):
            return float(city_page.meta["latitude"]), float(city_page.meta["longitude"])

    geocache = _load_geocache()
    if cache_key in geocache:
        return tuple(geocache[cache_key]) if geocache[cache_key] else None

    result = _geocode_nominatim(city_name)
    geocache[cache_key] = list(result) if result else None
    _save_geocache(geocache)
    return result


def _stop_markers(stop):
    """Return JSON-serialisable marker list for a single stop.

    Geocodes POIs that are missing coordinates via Nominatim and caches results.
    """
    geocache = _load_geocache()
    cache_dirty = False
    markers = []
    city_name = stop.get("city", "")

    for item in stop["items"]:
        page = item["page"]
        if not page:
            continue
        lat = page.meta.get("latitude")
        lng = page.meta.get("longitude")
        if lat and lng:
            markers.append({
                "lat": float(lat), "lng": float(lng),
                "title": page.title, "url": page.get_absolute_url(),
            })
        elif page.path not in geocache:
            # Try to geocode; store None on failure to avoid retrying
            result = _geocode_nominatim(f"{page.title}, {city_name}")
            geocache[page.path] = list(result) if result else None
            cache_dirty = True
            if result:
                markers.append({
                    "lat": result[0], "lng": result[1],
                    "title": page.title, "url": page.get_absolute_url(),
                })
        elif geocache[page.path]:
            lat, lng = geocache[page.path]
            markers.append({
                "lat": lat, "lng": lng,
                "title": page.title, "url": page.get_absolute_url(),
            })

    if cache_dirty:
        _save_geocache(geocache)
    return markers


def plan_list(request):
    import frontmatter as fm
    authenticated = set(request.session.get("authenticated_plans", []))
    join_error = request.session.pop("plan_join_error", None)
    plans = []
    for f in sorted(PLANS_DIR.glob("*.md")):
        slug = f.stem
        if slug not in authenticated:
            continue
        post = fm.load(f)
        plans.append({
            "slug": slug,
            "title": post.metadata.get("title", slug),
        })
    return render(request, "guide/plan_list.html", {"plans": plans, "join_error": join_error})


def plan_join(request):
    """Try a passphrase against all plans and authenticate the matching one."""
    if request.method != "POST":
        return HttpResponseRedirect("/plans/")
    pw = request.POST.get("password", "")
    passwords = _load_passwords()
    for slug, hashed in passwords.items():
        if _check_password(pw, hashed):
            _mark_plan_authenticated(request, slug)
            return HttpResponseRedirect(f"/plans/{slug}/")
    request.session["plan_join_error"] = "No trip found with that passphrase."
    return HttpResponseRedirect("/plans/")


_PASSPHRASE_WORDS = [
    # places & landscapes
    "canyon", "delta", "fjord", "glacier", "harbor", "lagoon", "meadow", "mesa",
    "oasis", "rapids", "reef", "ridge", "steppe", "summit", "tundra", "valley",
    # travel & movement
    "atlas", "compass", "ferry", "lantern", "passage", "pilgrim", "rover", "voyage",
    # nature
    "amber", "birch", "cedar", "cobalt", "coral", "crimson", "dusk", "ember",
    "falcon", "fern", "flint", "heron", "indigo", "jasper", "lemon", "lotus",
    "maple", "marigold", "mist", "moonrise", "mossy", "ochre", "onyx", "pebble",
    "pine", "pollen", "quartz", "saffron", "sage", "scarlet", "sienna", "slate",
    "spruce", "sterling", "talon", "thistle", "thorn", "topaz", "umber", "wren",
    # adjectives
    "ancient", "azure", "bold", "bright", "calm", "distant", "golden", "hidden",
    "ivory", "jade", "keen", "lofty", "lunar", "misty", "noble", "pale",
    "quiet", "rugged", "serene", "silent", "silver", "slow", "solar", "spare",
    "stone", "swift", "tall", "vast", "warm", "wild",
]


def _generate_passphrase():
    """Generate a unique 3-word passphrase not already used by any plan."""
    import random
    passwords = _load_passwords()
    existing = set(passwords.keys())
    for _ in range(100):
        words = random.sample(_PASSPHRASE_WORDS, 3)
        phrase = "-".join(words)
        if phrase not in existing:
            return phrase
    # Extremely unlikely fallback: add a number
    return "-".join(random.sample(_PASSPHRASE_WORDS, 3)) + f"-{random.randint(10,99)}"


def plan_new(request):
    error = None
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            error = "Please enter a trip title."
        else:
            import frontmatter as fm
            slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            path = PLANS_DIR / f"{slug}.md"
            if path.exists():
                error = f"A trip named '{slug}' already exists."
            else:
                passphrase = _generate_passphrase()
                post = fm.Post("", title=title)
                with open(path, "wb") as fh:
                    fm.dump(post, fh)
                _save_password(slug, passphrase)
                _mark_plan_authenticated(request, slug)
                request.session["new_plan_passphrase"] = passphrase
                return HttpResponseRedirect(f"/plans/{slug}/created/")
    return render(request, "guide/plan_new.html", {"error": error})


@_require_plan_auth
def plan_created(request, slug):
    passphrase = request.session.pop("new_plan_passphrase", None)
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        raise Http404
    return render(request, "guide/plan_created.html", {"plan": plan, "passphrase": passphrase})


@_require_plan_auth
def plan_detail(request, slug):
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        raise Http404

    # One marker per stop — use centroid of its POIs, fall back to city page coords
    stop_markers = []
    for stop in plan["stops"]:
        pts = _stop_markers(stop)
        if pts:
            lat = sum(m["lat"] for m in pts) / len(pts)
            lng = sum(m["lng"] for m in pts) / len(pts)
        else:
            coords = _city_coords(stop)
            if coords:
                lat, lng = coords
            else:
                continue
        stop_markers.append({
            "lat": lat, "lng": lng,
            "title": stop["city"], "dates": stop["dates"],
            "url": stop["url"],
        })

    return render(request, "guide/plan_detail.html", {
        "plan": plan,
        "stop_markers": mark_safe(json.dumps(stop_markers)),
    })


@_require_plan_auth
def plan_stop(request, slug, city_slug):
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        raise Http404
    stop = next((s for s in plan["stops"] if s["city_slug"] == city_slug), None)
    if not stop:
        raise Http404
    markers = _stop_markers(stop)
    city_page = load_page(stop["city_path"]) if stop.get("city_path") else None
    # Fall back to city coords (from content or geocoded) if no POI markers
    if not markers:
        coords = _city_coords(stop)
        if coords:
            markers = [{
                "lat": coords[0], "lng": coords[1],
                "title": stop["city"],
                "url": stop.get("destination_url") or "",
            }]
    city_snippet = None
    city_image_url = None
    if city_page:
        # Use explicit snippet, or extract first non-empty paragraph from body
        city_snippet = city_page.meta.get("snippet") or ""
        if not city_snippet and city_page.body:
            import re as _re
            first_para = _re.split(r'\n\n+', city_page.body.strip())[0]
            # Strip markdown markup for plain text display
            first_para = _re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', first_para)
            first_para = _re.sub(r'[*_`#>]+', '', first_para).strip()
            city_snippet = first_para[:300] + ("…" if len(first_para) > 300 else "")
        img = _image_path(city_page)
        if img:
            city_image_url = f"/content-image/{img}"
    return render(request, "guide/plan_stop.html", {
        "plan": plan,
        "stop": stop,
        "markers": mark_safe(json.dumps(markers)),
        "city_snippet": city_snippet,
        "city_image_url": city_image_url,
    })


@_require_plan_auth
def plan_edit(request, slug):
    path = PLANS_DIR / f"{slug}.md"
    if not path.is_file():
        raise Http404
    import frontmatter as fm
    if request.method == "POST":
        body = request.POST.get("body", "")
        post = fm.load(path)
        post.content = body
        with open(path, "wb") as fh:
            fm.dump(post, fh)
        return HttpResponseRedirect(f"/plans/{slug}/")
    post = fm.load(path)
    return render(request, "guide/plan_edit.html", {
        "plan": {"slug": slug, "title": post.metadata.get("title", slug)},
        "body": post.content,
    })


def _plan_file_add(slug, city_slug, poi_path):
    """Add poi_path as a bullet under the matching city heading."""
    path = PLANS_DIR / f"{slug}.md"
    import frontmatter as fm
    post = fm.load(path)
    lines = post.content.splitlines()
    # Find the city heading and the end of its bullet block
    insert_at = None
    in_section = False
    for i, line in enumerate(lines):
        h2 = re.match(r'^##\s+(.+)$', line)
        if h2:
            heading = h2.group(1)
            city_raw = heading.split('|', 1)[0].strip()
            # Support both city names ("Palo Alto") and content paths ("northamerica/…")
            if '/' in city_raw:
                heading_slug = city_raw.split('/')[-1].replace('_', ' ').lower().replace(' ', '-')
            else:
                heading_slug = city_raw.lower().replace(' ', '-')
            in_section = (heading_slug == city_slug)
            if in_section:
                insert_at = i + 1  # default: right after heading
            continue
        if in_section:
            if re.match(r'^[-*]\s+', line):
                insert_at = i + 1  # keep advancing to end of bullets
            elif line.strip() == '':
                pass  # skip blank lines within section
            else:
                break  # hit something else, stop
    if insert_at is None:
        return False
    # Check not already present
    if any(l.strip().lstrip('-* ') == poi_path for l in lines):
        return False
    lines.insert(insert_at, f'- {poi_path}')
    post.content = '\n'.join(lines)
    with open(path, 'wb') as fh:
        fm.dump(post, fh)
    return True


def _plan_file_remove(slug, poi_path):
    """Remove the bullet line for poi_path from the plan."""
    path = PLANS_DIR / f"{slug}.md"
    import frontmatter as fm
    post = fm.load(path)
    lines = post.content.splitlines()
    new_lines = [l for l in lines if l.strip().lstrip('-* ') != poi_path]
    if len(new_lines) == len(lines):
        return False
    post.content = '\n'.join(new_lines)
    with open(path, 'wb') as fh:
        fm.dump(post, fh)
    return True


@_require_plan_auth
def plan_poi_add(request, slug, city_slug=None):
    if request.method != 'POST':
        raise Http404
    poi_path = request.POST.get('poi_path', '').strip()
    if poi_path:
        if city_slug is None:
            # Auto-detect: find the stop whose city_path is a prefix of the poi path
            plan = _parse_plan(PLANS_DIR / f"{slug}.md")
            if plan:
                for stop in plan["stops"]:
                    cp = stop.get("city_path")
                    if cp and poi_path.startswith(cp + "/"):
                        city_slug = stop["city_slug"]
                        break
                # Fall back: match city_slug in poi path string
                if city_slug is None:
                    for stop in plan["stops"]:
                        cs = stop["city_slug"].replace('-', '')
                        if cs in poi_path.replace('/', '').replace('_', '').lower():
                            city_slug = stop["city_slug"]
                            break
        if city_slug:
            _plan_file_add(slug, city_slug, poi_path)
    return HttpResponseRedirect(request.POST.get('next', f'/plans/{slug}/'))


@_require_plan_auth
def plan_note_edit(request, slug, city_slug):
    if request.method != 'POST':
        raise Http404
    old_text = request.POST.get('old_text', '').strip()
    new_text = request.POST.get('new_text', '').strip()
    if old_text and new_text and old_text != new_text:
        import frontmatter as fm
        path = PLANS_DIR / f"{slug}.md"
        post = fm.load(path)
        lines = post.content.splitlines()
        new_lines = [
            re.sub(r'^([-*]\s+)' + re.escape(old_text) + r'$', r'\g<1>' + new_text, l)
            for l in lines
        ]
        post.content = '\n'.join(new_lines)
        with open(path, 'wb') as fh:
            fm.dump(post, fh)
    return HttpResponseRedirect(request.POST.get('next', f'/plans/{slug}/{city_slug}/'))


@_require_plan_auth
def plan_poi_remove(request, slug, city_slug):
    if request.method != 'POST':
        raise Http404
    poi_path = request.POST.get('poi_path', '').strip()
    if poi_path:
        _plan_file_remove(slug, poi_path)
    return HttpResponseRedirect(request.POST.get('next', f'/plans/{slug}/{city_slug}/'))
