import json
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
    return render(request, "guide/home.html")


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

    # Build sidebar nav: nav_pages from the parent (city or section_group).
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
    if page.page_type in NAV_TYPES and page.page_type != "section_group" and _city_path:
        poi_context_prefix = f"/{_city_path}/{page.slug}/"
    body_html = md.markdown(page.body) if page.body else ""
    nav_pages, locations, pois = page.children()

    # Separate neighbourhood pages from nav pages so they render inline under
    # the article body rather than in the sidebar sections list.
    neighbourhoods = [p for p in nav_pages if p.page_type == "neighbourhood"]
    nav_pages = [p for p in nav_pages if p.page_type != "neighbourhood"]

    # Build the city tag index once so all tagged_pois() calls reuse it.
    city_tag_index = None
    _cpath = _city_path if page.page_type in NAV_TYPES else (page.path if nav_pages else None)
    if _cpath:
        city_tag_index = build_city_tag_index(_cpath)

    # Nav pages collect their POIs by tag; section_groups collect their child nav pages
    if page.page_type == "section_group":
        pois = nav_pages
    elif page.page_type in NAV_TYPES:
        pois = page.tagged_pois(_city_tag_index=city_tag_index)

    # Collect distinct categories from POIs (for filter UI)
    poi_categories = []
    if page.page_type in NAV_TYPES and pois:
        poi_categories = sorted(set(p.category for p in pois if p.category))

    # Map context
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))

    path_parts = page.path.split("/")
    continent_slug = path_parts[0] if path_parts else None
    is_continent = len(path_parts) == 1 and page.page_type == "location"

    markers = _collect_markers(page, nav_pages, locations, pois, city_tag_index=city_tag_index)

    image_path = _image_path(page, branch)
    branch_qs = f'?branch={branch}' if branch else ''
    hero_image_url = f'/content-image/{image_path}{branch_qs}' if image_path else None
    hero_image_source = page.meta.get('image_source', '') if image_path else ''
    hero_image_license = page.meta.get('image_license', '') if image_path else ''

    return render(request, "guide/page.html", {
        "page": page,
        "parent": parent,
        "sections": nav_pages,           # child nav pages of current page (location sidebar)
        "locations": locations,
        "neighbourhood_items": neighbourhoods,
        "pois": pois,
        "parent_sections": parent_nav,   # sibling nav pages (section/poi sidebar)
        "parent_locations": parent_locations,
        "active_nav": active_nav,        # nav page to mark active (when POI bumped to grandparent nav)

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
        "tags": [t.replace("_", " ") for t in page.tags],
        "is_poi": page.page_type == "poi",
        "poi_categories": poi_categories,
        "poi_context_prefix": poi_context_prefix,
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


_SIGHT_SLUGS = {"sights", "museums", "attractions", "beaches", "landmarks", "things_to_do"}


def _marker_from_page(page, highlight=False):
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "name": page.title,
                "url": page.get_absolute_url(), "highlight": highlight}
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

    for poi in pois:
        add(_marker_from_page(poi))

    for nav in nav_pages:
        if nav.page_type == "section_group":
            continue
        is_sight = nav.slug in _SIGHT_SLUGS
        for poi in nav.tagged_pois(_city_tag_index=city_tag_index):
            add(_marker_from_page(poi, highlight=is_sight))

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
