import json
import re
import sqlite3
import subprocess
from dataclasses import replace
from pathlib import Path

import markdown as md
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.safestring import mark_safe

from . import github
from .models import (
    CONTENT_DIR, NAV_TYPES, build_city_tag_index, find_tagged_pois, find_locations_tagged,
    load_page, load_page_from_revision, load_tag_index, resolve_tag_route, _find_city_path,
)

SEARCH_DB = Path(settings.BASE_DIR) / "search.db"
HASH_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
INTERNAL_GUIDE_HREF_RE = re.compile(
    r'(<a\b[^>]*\bhref=")/(?!/|about(?:["/#?])|api/|content-image/|passport/|'
    r'regions(?:["/#?])|review(?:["/#?])|search(?:["/#?])|static/|tags/|[0-9a-fA-F]{7,40}/)'
)


def _resolve_revision_hash(value):
    """Return the full GitHub commit hash for an unambiguous hex revision prefix."""
    if not value or not HASH_RE.fullmatch(value):
        return None
    return github.resolve_commit(value) or None


def _resolve_any_revision(value):
    """Return the full commit hash for review input such as HEAD, a branch, or a hash."""
    if not value:
        return None
    resolved = github.resolve_commit(value)
    if resolved:
        return resolved

    # The review page can still inspect local-only branches while editing.
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{value}^{{commit}}"],
        capture_output=True, text=True, check=False,
        cwd=str(settings.BASE_DIR),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _short_revision(full_hash):
    return github.short_hash(full_hash)


def _prefix_internal_links(html, url_prefix):
    if not html or not url_prefix:
        return html
    return INTERNAL_GUIDE_HREF_RE.sub(
        lambda match: f'{match.group(1)}{url_prefix.strip("/")}/',
        html,
    )


def _revision_page(page, source_ref, url_revision):
    if not page or not source_ref:
        return page
    return replace(page, revision=url_revision, source_ref=source_ref)


def _prefixed_url(url, url_prefix):
    if not url or not url_prefix or not url.startswith("/"):
        return url
    return f"{url_prefix}{url}"


def about(request):
    return render(request, "guide/about.html")


def _city_snippet(page):
    snippet = page.meta.get('snippet', '')
    if snippet:
        return snippet
    for paragraph in page.body.split('\n\n'):
        text = ' '.join(paragraph.strip().split())
        if text:
            suffix = '...' if len(text) > 170 else ''
            return text[:170].rsplit(' ', 1)[0] + suffix
    return ''


def _globe_city_data(source_ref=None, url_revision=""):
    from .models import load_featured_cities
    url_prefix = f"/{url_revision}" if url_revision else ""
    city_cards = [c for c in load_featured_cities() if c['lat'] and c['lng']]
    city_cards = [
        {
            **city,
            "page": _revision_page(city["page"], source_ref, url_revision),
            "image_url": _prefixed_url(city["image_url"], url_prefix),
        }
        for city in city_cards
    ]
    return [
        {
            'title': c['page'].title,
            'url': c['page'].get_absolute_url(),
            'image': c['image_url'],
            'country': c['country'],
            'snippet': _city_snippet(c['page']),
            'lat': float(c['lat']),
            'lng': float(c['lng']),
            'score': c['score'],
            'path': c['page'].path,
        }
        for c in city_cards
    ]


def home(request, source_ref=None, url_revision=""):
    import random
    from .models import count_content_pages, load_continents, load_story_pois
    url_prefix = f"/{url_revision}" if url_revision else ""

    continents_raw = load_continents()
    continents = []
    for cont, countries in continents_raw:
        cont = _revision_page(cont, source_ref, url_revision)
        countries = [_revision_page(country, source_ref, url_revision) for country in countries]
        sorted_countries = sorted(
            countries,
            key=lambda l: float(l.meta.get('score', 0) or 0),
            reverse=True,
        )
        # Use the continent's own image; fall back to top-scored country
        img = _image_path(cont, source_ref)
        if not img:
            for country in sorted_countries[:10]:
                img = _image_path(country, source_ref)
                if img:
                    break
        image_url = f'{url_prefix}/content-image/{img}' if img else None
        continents.append({
            'page': cont,
            'countries': sorted_countries[:8],
            'total': len(countries),
            'image_url': image_url,
        })
    import json
    all_story_pois = load_story_pois()
    story_pois = random.sample(all_story_pois, min(6, len(all_story_pois)))
    story_pois = [
        {**poi, "page": _revision_page(poi["page"], source_ref, url_revision)}
        for poi in story_pois
    ]
    city_cards = _globe_city_data(source_ref, url_revision)
    cities_json = json.dumps(city_cards)
    globe_autoplay_embed_url = request.build_absolute_uri("/widgets/globe-explore?mode=autoplay")
    globe_explore_embed_url = request.build_absolute_uri("/widgets/globe-explore?mode=explore")
    photo_map_embed_url = request.build_absolute_uri("/widgets/photo-map")
    return render(request, "guide/home.html", {
        'continents': continents,
        'story_pois': story_pois,
        'cities_json': cities_json,
        'featured_city_count': f"{len(city_cards):,}",
        'search_page_count': f"{count_content_pages():,}",
        'url_prefix': url_prefix,
        'globe_autoplay_embed_url': globe_autoplay_embed_url,
        'globe_explore_embed_url': globe_explore_embed_url,
        'globe_autoplay_iframe': _iframe_code(globe_autoplay_embed_url, 560),
        'globe_explore_iframe': _iframe_code(globe_explore_embed_url, 560),
        'photo_map_embed_url': photo_map_embed_url,
        'photo_map_iframe': _iframe_code(photo_map_embed_url, 560),
    })


def home_at_revision(request, revision):
    source_ref = _resolve_revision_hash(revision)
    if not source_ref:
        raise Http404
    return home(request, source_ref=source_ref, url_revision=_short_revision(source_ref))


def widgets(request):
    embed_url = request.build_absolute_uri("/widgets/globe-explore?mode=autoplay")
    explore_url = request.build_absolute_uri("/widgets/globe-explore?mode=explore")
    photo_map_url = request.build_absolute_uri("/widgets/photo-map")
    return render(request, "guide/widgets/index.html", {
        "globe_embed_url": embed_url,
        "globe_iframe": _iframe_code(embed_url, 520),
        "globe_explore_embed_url": explore_url,
        "globe_explore_iframe": _iframe_code(explore_url, 520),
        "photo_map_embed_url": photo_map_url,
        "photo_map_iframe": _iframe_code(photo_map_url, 520),
    })


@xframe_options_exempt
def widget_globe_explore(request):
    height = _int_param(request, "height", 520, 280, 1200)
    scale = _float_param(request, "scale", 1, 0.6, 1.8)
    mode = request.GET.get("mode", "autoplay")
    if mode not in {"autoplay", "explore"}:
        mode = "autoplay"
    theme = request.GET.get("theme", "light")
    if theme not in {"light", "transparent"}:
        theme = "light"
    show_embed = _bool_param(request, "embed", True)
    show_fullscreen = _bool_param(request, "fullscreen", True)
    widget_url = request.build_absolute_uri()
    return render(request, "guide/widgets/globe_explore.html", {
        "cities_json": json.dumps(_globe_city_data()),
        "height": height,
        "scale": scale,
        "mode": mode,
        "theme": theme,
        "show_embed": show_embed,
        "show_fullscreen": show_fullscreen,
        "embed_code": _iframe_code(widget_url, height),
        "widget_url": widget_url,
    })


@xframe_options_exempt
def widget_photo_map(request):
    widget_url = request.build_absolute_uri()
    return render(request, "guide/widgets/photo_map.html", {
        "widget_url": widget_url,
        "embed_code": _iframe_code(widget_url, 560),
    })


def _bool_param(request, name, default):
    value = request.GET.get(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}


def _int_param(request, name, default, min_value, max_value):
    try:
        value = int(request.GET.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(max_value, value))


def _float_param(request, name, default, min_value, max_value):
    try:
        value = float(request.GET.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(max_value, value))


def _iframe_code(url, height):
    return (
        f'<iframe src="{url}" width="100%" height="{height}" '
        'style="border:0" loading="lazy" allow="fullscreen"></iframe>'
    )


def location_or_section(request, path):
    branch = request.GET.get("branch")
    if branch:
        full_hash = _resolve_any_revision(branch)
        if full_hash:
            return redirect(f"/{_short_revision(full_hash)}/{path.strip('/')}", permanent=False)
    return _location_or_section(request, path)


def location_or_section_at_revision(request, revision, path):
    source_ref = _resolve_revision_hash(revision)
    if not source_ref:
        raise Http404
    return _location_or_section(
        request, path, source_ref=source_ref, url_revision=_short_revision(source_ref)
    )


def _location_or_section(request, path, source_ref=None, url_revision=""):
    path = path.strip("/")

    page = (
        load_page_from_revision(path, source_ref, url_revision=url_revision)
        if source_ref else load_page(path)
    )
    context_nav = None  # nav page used to reach this POI (for sidebar context)

    if not page:
        # Try virtual tag-based routing: city/nav-slug/poi-slug
        page, context_nav = resolve_tag_route(path, source_ref, url_revision)

    if not page:
        raise Http404

    # Derive parent for nav/poi pages
    parent = None
    if page.page_type in NAV_TYPES | {"poi"} and "/" in page.path:
        parent_path = page.path.rsplit("/", 1)[0]
        parent = (
            load_page_from_revision(parent_path, source_ref, url_revision=url_revision)
            if source_ref else load_page(parent_path)
        )

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
            grandparent_path = parent.path.rsplit("/", 1)[0]
            grandparent = (
                load_page_from_revision(grandparent_path, source_ref, url_revision=url_revision)
                if source_ref else load_page(grandparent_path)
            )
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
    _city_path = (
        _find_city_path(page.path, source_ref, url_revision)
        if page.page_type in NAV_TYPES else None
    )
    if page.page_type in NAV_TYPES and page.page_type != "section_group" and _city_path:
        poi_context_prefix = f"{page.url_prefix}/{_city_path}/{page.slug}/"
    body_html = (
        _prefix_internal_links(md.markdown(page.body), page.url_prefix)
        if page.body else ""
    )
    nav_pages, locations, pois = page.children()

    # Separate neighbourhood pages from nav pages so they render inline under
    # the article body rather than in the sidebar sections list.
    neighbourhoods = [p for p in nav_pages if p.page_type == "neighbourhood" and not p.meta.get("hide_from_city")]
    nav_pages = [p for p in nav_pages if p.page_type != "neighbourhood"]

    # Build the city tag index once so all tagged_pois() calls reuse it.
    # Only build for actual city-level pages: nav pages (sections), or location
    # pages that have sections but no child locations (cities, not countries/continents).
    city_tag_index = None
    _cpath = _city_path if page.page_type in NAV_TYPES else (
        page.path if nav_pages and not locations else None
    )
    if _cpath:
        city_tag_index = build_city_tag_index(_cpath, source_ref, url_revision)

    # Nav pages collect their POIs by tag; section_groups collect their child nav pages
    if page.page_type == "section_group":
        pois = nav_pages
    elif page.page_type in NAV_TYPES:
        pois = page.tagged_pois(_city_tag_index=city_tag_index)
        # Highest-scored POIs first, so the numbered list reads as a ranking
        # (mirrors the score sort already applied to locations below).
        pois = sorted(pois, key=lambda p: float(p.meta.get("score", 0) or 0), reverse=True)

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
    continent_bounds = page.meta.get("map_bounds") if is_continent else None
    page_map_bounds = page.meta.get("map_bounds") if not is_continent else None

    image_path = _image_path(page, source_ref)
    hero_image_url = f'{page.url_prefix}/content-image/{image_path}' if image_path else None
    hero_image_source = page.meta.get('image_source', '') if image_path else ''
    hero_image_license = page.meta.get('image_license', '') if image_path else ''
    if not hero_image_url and page.page_type == "list":
        cover = _list_cover_image(page, source_ref, url_revision=url_revision)
        if cover:
            hero_image_url = cover["url"]
            hero_image_source = cover["source"]
            hero_image_license = cover["license"]

    # Attach image_url to each neighbourhood for card display
    for nb in neighbourhoods:
        nb_img = _image_path(nb, source_ref)
        nb.image_url = f'{nb.url_prefix}/content-image/{nb_img}' if nb_img else None

    # Don't show the neighbourhood strip unless at least 3 have images
    if sum(1 for nb in neighbourhoods if nb.image_url) < 3:
        neighbourhoods = []

    # Sort locations by score descending, attach image_url and word_cloud, split into top 9 and rest
    locations = sorted(locations, key=lambda loc: float(loc.meta.get('score', 0) or 0), reverse=True)
    for loc in locations:
        loc_img = _image_path(loc, source_ref)
        loc.image_url = f'{loc.url_prefix}/content-image/{loc_img}' if loc_img else None
        loc.card_children = []
        loc.card_children_total = 0
        if not loc.image_url:
            child_navs, child_locs, child_pois = loc.children()
            scored_locs = sorted(child_locs, key=lambda p: float(p.meta.get('score', 0) or 0), reverse=True)
            # Inherit image from highest-scoring child that has one
            for cl in scored_locs:
                cl_img = _image_path(cl, source_ref)
                if cl_img:
                    loc.image_url = f'{cl.url_prefix}/content-image/{cl_img}'
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
    _CARD_THRESHOLD = 18
    _CARD_MAX = 9
    _top_n = len(locations) if len(locations) <= _CARD_THRESHOLD else _CARD_MAX
    top_locations = locations[:_top_n]
    more_locations = sorted(locations[_top_n:], key=lambda loc: loc.title)

    # For feature pages: cities/locations that tag into this feature via tags: [feature_slug]
    linked_locations = []
    more_linked_locations = []
    if page.meta.get('loc_type') == 'feature':
        linked_locations = sorted(
            find_locations_tagged(page.slug, page.path),
            key=lambda p: float(p.meta.get('score', 0) or 0), reverse=True,
        )
        for loc in linked_locations:
            loc_img = _image_path(loc, source_ref)
            loc.image_url = f'{loc.url_prefix}/content-image/{loc_img}' if loc_img else None
        _ll_top_n = len(linked_locations) if len(linked_locations) <= _CARD_THRESHOLD else _CARD_MAX
        more_linked_locations = sorted(linked_locations[_ll_top_n:], key=lambda p: p.title)
        linked_locations = linked_locations[:_ll_top_n]

    # For section pages (e.g. day_trips): explicit linked_locations: paths in frontmatter
    elif page.meta.get('linked_locations'):
        for loc_path in page.meta['linked_locations']:
            loc = (load_page_from_revision(loc_path, source_ref, url_revision=url_revision)
                   if source_ref else load_page(loc_path))
            if not loc or loc.page_type != 'location':
                continue
            loc_img = _image_path(loc, source_ref)
            loc.image_url = f'{loc.url_prefix}/content-image/{loc_img}' if loc_img else None
            linked_locations.append(loc)

    # Day-trip cards: linked destinations + any genuine-attraction POIs kept in
    # the section, rendered together as one card grid.
    daytrip_cards = None
    if page.page_type == 'section' and linked_locations:
        daytrip_cards = [
            {'url': loc.get_absolute_url(), 'title': loc.title,
             'image_url': getattr(loc, 'image_url', None), 'snippet': loc.meta.get('snippet', '')}
            for loc in linked_locations
        ]
        for poi in pois:
            img_path = _image_path(poi, source_ref)
            url = (poi_context_prefix + poi.slug) if poi_context_prefix else poi.get_absolute_url()
            daytrip_cards.append({
                'url': url, 'title': poi.title,
                'image_url': f'{poi.url_prefix}/content-image/{img_path}' if img_path else None,
                'snippet': poi.meta.get('snippet', '') or '',
            })


    # For small city pages (< 8 POIs total): inline sections directly instead of section cards
    inline_sections = None
    if page.page_type == "location" and nav_pages and not locations and city_tag_index is not None:
        total_pois = 0
        candidate_sections = []
        seen_paths = set()
        for section in nav_pages:
            if section.page_type in ("neighbourhood", "section_group"):
                continue
            section_pois = []
            for poi in section.tagged_pois(_city_tag_index=city_tag_index):
                if poi.path not in seen_paths:
                    seen_paths.add(poi.path)
                    section_pois.append(poi)
                    total_pois += 1
            candidate_sections.append((section, section_pois))
        if total_pois < 8:
            inline_sections = [
                {
                    'section': s,
                    'body_html': _prefix_internal_links(md.markdown(s.body), page.url_prefix) if s.body else '',
                    'pois': sp,
                }
                for s, sp in candidate_sections
            ]

    _all_linked = linked_locations + more_linked_locations
    _map_top = top_locations + (linked_locations if _all_linked else [])
    _map_all = locations + (_all_linked if _all_linked else [])
    markers = _collect_markers(page, nav_pages, _map_top, pois, city_tag_index=city_tag_index)
    markers_full = _collect_markers(page, nav_pages, _map_all, pois, city_tag_index=city_tag_index)

    # Lists: a type=list page names its own members explicitly via `items:`
    # (POIs or locations, mixed freely, in display order) — no query, no
    # aggregation, just resolving paths the same way linked_locations does.
    list_items = None
    if page.page_type == "list":
        list_items = []
        for i, item_path in enumerate(page.meta.get("items") or []):
            item = (load_page_from_revision(item_path, source_ref, url_revision=url_revision)
                    if source_ref else load_page(item_path))
            if not item:
                continue
            item_img = _image_path(item, source_ref)
            list_items.append({
                "rank": i + 1,
                "url": item.get_absolute_url(),
                "title": item.title,
                "image_url": f"{item.url_prefix}/content-image/{item_img}" if item_img else None,
                "snippet": item.meta.get("snippet", "") or "",
            })

    # A location page (city/region/country/feature) may have one or more
    # type=list pages living in its own directory — feature the best-scored
    # one, link the rest.
    featured_list = None
    other_lists = []
    if page.page_type == "location":
        found_lists = page.find_lists()
        if found_lists:
            featured_list = found_lists[0]
            featured_img = _image_path(featured_list, source_ref)
            if featured_img:
                featured_list.image_url = f"{featured_list.url_prefix}/content-image/{featured_img}"
            else:
                cover = _list_cover_image(featured_list, source_ref, url_revision=url_revision)
                featured_list.image_url = cover["url"] if cover else None
            other_lists = found_lists[1:]

    # "Featured on" back-references: purely for display, manually kept in
    # sync with the list's own items: — not derived from anything.
    poi_lists = []
    for list_path in page.meta.get("lists") or []:
        list_page = (load_page_from_revision(list_path, source_ref, url_revision=url_revision)
                     if source_ref else load_page(list_path))
        if list_page:
            poi_lists.append(list_page)

    breadcrumbs = page.breadcrumbs()

    return render(request, "guide/page.html", {
        "page": page,
        "parent": parent,
        "sections": nav_pages,           # child nav pages of current page (location sidebar)
        "locations": locations,
        "top_locations": top_locations,
        "more_locations": more_locations,
        "neighbourhood_items": neighbourhoods,
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
        "tags": [t.replace("_", " ") for t in page.tags],
        "is_poi": page.page_type == "poi",
        "poi_categories": poi_categories,
        "poi_context_prefix": poi_context_prefix,
        "inline_sections": inline_sections,
        "linked_locations": linked_locations,
        "daytrip_cards": daytrip_cards,
        "more_linked_locations": more_linked_locations,
        "url_prefix": page.url_prefix,
        "list_items": list_items,
        "featured_list": featured_list,
        "other_lists": other_lists,
        "poi_lists": poi_lists,
    })


def _search_results(query):
    if not query or not SEARCH_DB.is_file():
        return []

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

    return results


def search(request):
    query = request.GET.get("q", "").strip()
    if request.GET.get("format", "").lower() == "json":
        return JsonResponse({"results": _search_results(query)})

    has_db = SEARCH_DB.is_file()
    return render(request, "guide/search.html", {
        "query": query,
        "has_db": has_db,
    })


def search_api(request):
    query = request.GET.get("q", "").strip()
    results = _search_results(query)
    return JsonResponse({"results": results})


def tag_index(request, tag):
    index = load_tag_index()
    pages = index.get(tag, [])
    if not pages and tag not in index:
        raise Http404
    return render(request, "guide/tag.html", {"tag": tag, "pages": pages})


_SIGHT_SLUGS = {"sights", "museums", "attractions", "landmarks", "things_to_do"}
_META_SLUGS   = {"neighbourhood"}   # organisational tags, not POI categories


def _marker_from_page_rich(page, highlight=False):
    """Extended marker that includes path, tags, and image_url for the explore map."""
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is None or lng is None:
        return None
    m = {
        "lat": lat, "lng": lng, "name": page.title,
        "url": page.get_absolute_url(), "path": page.path,
        "highlight": highlight,
        "score": float(page.meta.get("score", 0) or 0),
        "snippet": page.meta.get("snippet", ""),
        "tags": list(page.meta.get("tags") or []),
    }
    img = _image_path(page)
    if img:
        m["image_url"] = f"/content-image/{img}"
    return m


def _explore_markers(page):
    """Return (mode, markers) for the explore view.

    mode='locations' when the page has child city/location pages to browse.
    mode='city' when we're at city level and should show POIs.

    Primary (sightseeing) POIs come first with highlight=True.
    Secondary (eating, activities, etc.) follow with highlight=False.
    Curbside POIs are appended last with curbside=True; the map JS
    renders them only when zoomed in far enough.
    """
    sections, locations, pois = page.children()
    if locations:
        markers = [m for m in (_marker_from_page_rich(l) for l in locations) if m]
        markers.sort(key=lambda m: m["score"], reverse=True)
        return "locations", markers

    seen = set()
    primary   = []   # sightseeing
    secondary = []   # other categories
    curbside  = []   # curbside layer — shown at high map zoom only

    def _collect(poi, section_slug=None):
        m = _marker_from_page_rich(poi)
        if not m:
            return
        k = (m["lat"], m["lng"])
        if k in seen:
            return
        seen.add(k)
        tags = set(poi.meta.get("tags") or [])
        if "curbside" in tags:
            m["curbside"] = True
            curbside.append(m)
        elif (tags & _SIGHT_SLUGS) or (section_slug in _SIGHT_SLUGS):
            m["highlight"] = True
            primary.append(m)
        elif tags - _META_SLUGS:
            m["highlight"] = False
            secondary.append(m)

    for poi in pois:
        _collect(poi)
    for nav in sections:
        for poi in nav.tagged_pois():
            _collect(poi, section_slug=nav.slug)

    primary.sort(key=lambda m: m["score"], reverse=True)
    secondary.sort(key=lambda m: m["score"], reverse=True)
    return "city", primary + secondary + curbside


def api_page_content(request, path):
    """Return rendered body HTML and image for a page — used by the explore drawer."""
    path = path.strip("/")
    page = load_page(path)
    if not page:
        raise Http404
    body_html = (
        _prefix_internal_links(md.markdown(page.body), page.url_prefix)
        if page.body else ""
    )
    data = {
        "title": page.title,
        "url": page.get_absolute_url(),
        "body_html": body_html,
        "snippet": page.meta.get("snippet", ""),
    }
    img = _image_path(page)
    if img:
        data["image_url"] = f"/content-image/{img}"
        data["image_source"] = page.meta.get("image_source", "")
        data["image_license"] = page.meta.get("image_license", "")
        data["image_attribution"] = page.meta.get("image_attribution", "")
    return JsonResponse(data)


_CONTINENT_CENTROIDS = {
    "europe":             (54.0,   15.0),
    "asia":               (35.0,   90.0),
    "africa":             ( 0.0,   20.0),
    "northamerica":       (45.0, -100.0),
    "southamerica":       (-15.0,  -60.0),
    "australiaandpacific":(-25.0,  135.0),
}


def _world_markers():
    """Return markers for all continents (world-level explore)."""
    markers = []
    for slug, (lat, lng) in _CONTINENT_CENTROIDS.items():
        page = load_page(slug)
        if not page:
            continue
        m = {
            "lat": lat, "lng": lng,
            "name": page.title,
            "url": page.get_absolute_url(),
            "path": page.path,
            "highlight": True,
            "score": float(page.meta.get("score", 0) or 0),
            "snippet": page.meta.get("snippet", ""),
            "tags": list(page.meta.get("tags") or []),
        }
        img = _image_path(page)
        if img:
            m["image_url"] = f"/content-image/{img}"
        markers.append(m)
    return markers


def map_explore_world(request):
    markers = _world_markers()
    return render(request, "guide/map_explore.html", {
        "page": None,
        "page_title": "World",
        "parent_title": "",
        "parent_url": "",
        "parent_path_json": mark_safe("null"),
        "mode": "locations",
        "markers_json": mark_safe(json.dumps(markers)),
    })


def api_explore_world(request):
    markers = _world_markers()
    return JsonResponse({
        "title": "World",
        "path": "",
        "url": "/explore",
        "snippet": "",
        "mode": "locations",
        "markers": markers,
    })


def map_explore(request, path):
    path = path.strip("/")
    page = load_page(path)
    if not page:
        raise Http404
    mode, markers = _explore_markers(page)
    # Build parent info: top-level pages (continents) link up to world explore
    if "/" in page.path:
        parent = load_page(page.path.rsplit("/", 1)[0])
        parent_title = parent.title if parent else ""
        parent_url = parent.get_absolute_url() if parent else ""
        parent_path = parent.path if parent else ""
    else:
        parent_title = "World"
        parent_url = "/explore"
        parent_path = ""   # empty string = world root
    return render(request, "guide/map_explore.html", {
        "page": page,
        "page_title": page.title,
        "parent_title": parent_title,
        "parent_url": parent_url,
        "parent_path_json": mark_safe(json.dumps(parent_path)),
        "mode": mode,
        "markers_json": mark_safe(json.dumps(markers)),
    })


def api_explore(request, path):
    path = path.strip("/")
    page = load_page(path)
    if not page:
        raise Http404
    mode, markers = _explore_markers(page)
    data = {
        "title": page.title,
        "path": page.path,
        "url": page.get_absolute_url(),
        "snippet": page.meta.get("snippet", ""),
        "mode": mode,
        "markers": markers,
    }
    return JsonResponse(data)


def _marker_from_page(page, highlight=False):
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "name": page.title,
                "url": page.get_absolute_url(), "highlight": highlight,
                "score": float(page.meta.get("score", 0) or 0),
                "snippet": page.meta.get("snippet", "")}
    return None


def _collect_markers(page, nav_pages, locations, pois, city_tag_index=None, extra_locations=None):
    markers = []
    seen = set()

    def add(m):
        if m and (m["lat"], m["lng"]) not in seen:
            seen.add((m["lat"], m["lng"]))
            markers.append(m)

    for loc in locations:
        add(_marker_from_page(loc))

    # Linked destinations (e.g. day-trip locations on a section page) so the
    # map shows them alongside any genuine-attraction POIs in the section.
    for loc in extra_locations or []:
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
            if nav.page_type == "section_group":
                continue
            if nav.slug not in _SIGHT_SLUGS:
                continue
            for poi in nav.tagged_pois(_city_tag_index=city_tag_index):
                add(_marker_from_page(poi, highlight=True))

    return markers


IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')
IMAGE_CONTENT_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
}


def _safe_content_path(path):
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    return path.strip("/")


def _image_path(page, source_ref=None):
    image = page.meta.get('image', '')
    if not image:
        return None
    for candidate in [
        f'{page.path}/{image}',
        f'{page.path.rsplit("/", 1)[0]}/{image}' if '/' in page.path else image,
    ]:
        if source_ref:
            if github.file_exists(source_ref, f"content/{candidate}"):
                return candidate
        elif (CONTENT_DIR / candidate).is_file():
            return candidate
    return None


def _list_cover_image(list_page, source_ref=None, url_revision=None):
    """A list page has no image of its own — borrow one from the first of
    its items: that has one, rather than sourcing a dedicated image per list."""
    for item_path in list_page.meta.get("items") or []:
        item = (load_page_from_revision(item_path, source_ref, url_revision=url_revision)
                if source_ref else load_page(item_path))
        if not item:
            continue
        img = _image_path(item, source_ref)
        if img:
            return {
                "url": f"{item.url_prefix}/content-image/{img}",
                "source": item.meta.get("image_source", ""),
                "license": item.meta.get("image_license", ""),
            }
    return None


def content_image(request, path):
    branch = request.GET.get('branch')
    if branch:
        source_ref = _resolve_any_revision(branch)
        if not source_ref:
            raise Http404
        path = _safe_content_path(path)
        if not path:
            raise Http404
        suffix = Path(path).suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            raise Http404
        data = github.get_file_bytes(source_ref, f"content/{path}")
        if data is None:
            raise Http404
        return HttpResponse(data, content_type=IMAGE_CONTENT_TYPES[suffix])
    file_path = (CONTENT_DIR / path).resolve()
    if not file_path.is_relative_to(CONTENT_DIR.resolve()):
        raise Http404
    if not file_path.is_file() or file_path.suffix.lower() not in IMAGE_SUFFIXES:
        raise Http404
    return FileResponse(open(file_path, 'rb'))


def content_image_at_revision(request, revision, path):
    source_ref = _resolve_revision_hash(revision)
    if not source_ref:
        raise Http404
    path = _safe_content_path(path)
    if not path:
        raise Http404
    suffix = Path(path).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        raise Http404
    data = github.get_file_bytes(source_ref, f"content/{path}")
    if data is None:
        raise Http404
    return HttpResponse(data, content_type=IMAGE_CONTENT_TYPES[suffix])


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
    '''Show all pages changed on a revision vs origin/main.'''
    branch = request.GET.get('branch', 'HEAD')
    full_hash = _resolve_any_revision(branch)
    if not full_hash:
        return render(request, 'guide/review.html', {
            'error': f'Could not resolve {branch!r} to a git commit',
            'branch': branch,
        })
    short_hash = _short_revision(full_hash)
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
    return render(request, 'guide/review.html', {
        'pages': pages,
        'error': None,
        'branch': branch,
        'short_hash': short_hash,
        'full_hash': full_hash,
    })


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
