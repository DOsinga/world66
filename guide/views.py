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
    load_geo_index,
)

SEARCH_DB = Path(settings.BASE_DIR) / "search.db"

# Keywords for POI title/snippet matching, keyed by mood chip text.
# Used to score cities by their POI composition when tags are absent.
MOOD_KEYWORDS = {
    "A slow morning with nowhere to be — coffee, a neighbourhood bakery, watching the city wake up": [
        "cafe", "coffee", "bakery", "patisserie", "boulangerie", "brunch", "espresso", "tearoom",
    ],
    "Somewhere that earned its scars — old stones, half-forgotten stories, places that have outlived everyone who built them": [
        "museum", "cathedral", "church", "castle", "palace", "fort", "ruin", "basilica",
        "abbey", "monastery", "synagogue", "mosque", "temple", "historic",
    ],
    "Hungry and curious — street food, a crowded market, eating something you can't pronounce": [
        "restaurant", "market", "kitchen", "brasserie", "bistro", "tavern", "trattoria",
        "tapas", "sushi", "eatery", "diner", "food", "cuisine", "taqueria",
    ],
    "Following the art — a gallery you almost walked past, a mural on a side street, something that makes you stop": [
        "museum", "gallery", "art", "mural", "exhibition", "painting", "sculpture",
        "opera", "theatre", "cinema",
    ],
    "Out of the city noise — somewhere green, a path that goes nowhere in particular, birds instead of traffic": [
        "park", "garden", "forest", "nature", "trail", "lake", "mountain", "beach",
        "botanical", "reserve", "valley", "waterfall", "wildlife",
    ],
    "When the sun goes down — a bar with no tourists, live music somewhere, staying out later than planned": [
        "bar", "pub", "brewery", "cocktail", "jazz", "nightclub", "lounge", "wine",
        "distillery", "club",
    ],
}

_NATURE_MOOD = "Out of the city noise — somewhere green, a path that goes nowhere in particular, birds instead of traffic"
_NATURE_LOC_TYPES = {"feature", "island"}


def about(request):
    return render(request, "guide/about.html")


def next_up(request):
    return render(request, "guide/next.html")


def _safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def page_coords_api(request):
    path = request.GET.get("path", "").strip("/")
    if not path:
        return JsonResponse({"error": "path required"}, status=400)
    page = load_page(path)
    if not page:
        return JsonResponse({"error": "not found"}, status=404)
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is None or lng is None:
        return JsonResponse({"error": "no coordinates"}, status=404)
    return JsonResponse({"lat": lat, "lng": lng, "title": page.title})


def nearby_api(request):
    import math

    lat = _safe_float(request.GET.get("lat"))
    lng = _safe_float(request.GET.get("lng"))
    mode = request.GET.get("mode", "walking")
    mood = request.GET.get("mood", "").strip()
    exclude_path = request.GET.get("exclude", "").strip("/")

    if lat is None or lng is None:
        return JsonResponse({"error": "lat and lng required"}, status=400)

    # loc_types accepted for location bands — city, island, feature; exclude region/country/continent
    _CITY_LOC_TYPES = {"city", "island", "feature", ""}

    BANDS = {
        "walking":      {"min_km": 0,   "max_km": 2,   "types": {"poi"}},
        "drive":        {"min_km": 0,   "max_km": 60,  "types": {"location"}},
        "destinations": {"min_km": 60,  "max_km": 250, "types": {"location"}},
    }
    band = BANDS.get(mode, BANDS["walking"])

    def haversine(lat1, lng1, lat2, lng2):
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
             + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
        return 2 * R * math.asin(math.sqrt(a))

    results = []
    for item in load_geo_index():
        if item["page_type"] not in band["types"]:
            continue
        if item["page_type"] == "location" and item.get("loc_type", "") not in _CITY_LOC_TYPES:
            continue
        if exclude_path and item["path"] == exclude_path:
            continue
        d = haversine(lat, lng, item["lat"], item["lng"])
        if band["min_km"] <= d <= band["max_km"]:
            if d < 1:
                label = f"{round(d * 1000)}m"
            elif d < 10:
                label = f"{d:.1f} km"
            else:
                label = f"{round(d)} km"
            results.append({
                "title": item["title"],
                "url": "/" + item["path"],
                "path_raw": item["path"],
                "page_type": item["page_type"],
                "loc_type": item.get("loc_type", ""),
                "image": item["image"],
                "score": item["score"],
                "distance_km": d,
                "distance_label": label,
                "snippet": item["snippet"],
            })

    results.sort(key=lambda x: x["distance_km"])
    limit = 60 if mood else 40

    if mood and results:
        results = _reorder_by_mood(mood, results[:limit])
    else:
        results = results[:40]

    for r in results:
        del r["distance_km"]
        r.pop("loc_type", None)
        r["image_url"] = _resolve_geo_image(r.pop("path_raw"), r.pop("image"))

    return JsonResponse({"results": results[:40], "mood_active": bool(mood)})


def _resolve_geo_image(path, image_filename):
    if not image_filename:
        return None
    for candidate in [
        f"{path}/{image_filename}",
        f"{path.rsplit('/', 1)[0]}/{image_filename}" if "/" in path else image_filename,
    ]:
        if (CONTENT_DIR / candidate).is_file():
            return f"/content-image/{candidate}"
    return None


def _city_poi_vibe_scores(keywords, city_paths):
    """
    One pass over the geo index: for each city path, count child POIs whose
    title+snippet contains at least one keyword. Returns {path: score 0-1}.

    Score = tanh(matches / SATURATION) so a city with 5+ matching POIs scores
    near 1.0 regardless of total POI count. This prevents small towns with a
    single matching POI from beating large cities on a ratio basis.
    """
    import math
    SATURATION = 5.0

    city_set = set(city_paths)
    matches = {p: 0 for p in city_paths}
    for item in load_geo_index():
        if item["page_type"] != "poi":
            continue
        parts = item["path"].split("/")
        for depth in range(2, len(parts)):
            parent = "/".join(parts[:depth])
            if parent in city_set:
                text = (item["title"] + " " + (item.get("snippet") or "")).lower()
                if any(kw in text for kw in keywords):
                    matches[parent] += 1
                break
    return {p: math.tanh(matches[p] / SATURATION) for p in city_paths}


def _reorder_by_mood(mood, results):
    try:
        import apsw
        import numpy as np
        import sqlite_vec

        if not SEARCH_DB.is_file():
            return results

        conn = apsw.Connection(str(SEARCH_DB), flags=apsw.SQLITE_OPEN_READONLY)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)

        # 1. Mood vector — pre-computed if it's a chip, otherwise call OpenAI
        mood_row = conn.execute(
            "SELECT embedding FROM embeddings WHERE path=?", (f"mood:{mood}",)
        ).fetchone()

        if mood_row:
            mood_vec = np.frombuffer(mood_row[0], dtype=np.float32).copy()
        else:
            from dotenv import load_dotenv
            load_dotenv()
            from openai import OpenAI

            resp = OpenAI().embeddings.create(
                model="text-embedding-3-small", input=[mood], dimensions=512
            )
            mood_vec = np.array(resp.data[0].embedding, dtype=np.float32)
            n = np.linalg.norm(mood_vec)
            if n:
                mood_vec /= n

        # 2. Item vectors — batch fetch from DB (path = url_path + ".md")
        paths = [r["url"].lstrip("/") + ".md" for r in results]
        placeholders = ",".join("?" * len(paths))
        rows = conn.execute(
            f"SELECT path, embedding FROM embeddings WHERE path IN ({placeholders})", paths
        ).fetchall()
        conn.close()

        emb_by_path = {
            row[0]: np.frombuffer(row[1], dtype=np.float32).copy() for row in rows
        }

        # 3. POI-composition vibe scores for location results
        location_results = [r for r in results if r.get("page_type") == "location"]
        poi_vibe = {}
        if location_results and mood in MOOD_KEYWORDS:
            city_paths = [r["path_raw"] for r in location_results]
            poi_vibe = _city_poi_vibe_scores(MOOD_KEYWORDS[mood], city_paths)

        # 4. Proximity score for locations — normalized within the result set
        loc_distances = [r["distance_km"] for r in results if r.get("page_type") == "location"]
        if loc_distances:
            d_min, d_max = min(loc_distances), max(loc_distances)
            d_range = d_max - d_min if d_max > d_min else 1.0
        else:
            d_min = d_range = 1.0

        # 5. Blend scores
        # POIs:      0.65 * sim + 0.35 * content_score
        # Locations: 0.35 * sim + 0.15 * content_score + 0.40 * poi_vibe + 0.10 * proximity
        finals = []
        for r, path in zip(results, paths):
            vec = emb_by_path.get(path)
            sim = float(np.dot(vec, mood_vec)) if vec is not None else 0.0
            content_score = r.get("score") or 0.5
            if r.get("page_type") == "location":
                loc_type = r.get("loc_type", "")
                if mood == _NATURE_MOOD:
                    if loc_type in _NATURE_LOC_TYPES:
                        pv = min(1.0, poi_vibe.get(r["path_raw"], 0.0) + 0.5)
                    else:
                        pv = 0.0
                else:
                    pv = poi_vibe.get(r["path_raw"], 0.0)
                prox = 1.0 - (r["distance_km"] - d_min) / d_range
                finals.append(0.35 * sim + 0.15 * content_score + 0.40 * pv + 0.10 * prox)
            else:
                finals.append(0.65 * sim + 0.35 * content_score)

        return [r for _, r in sorted(zip(finals, results), key=lambda x: -x[0])]

    except Exception:
        return results


def home(request):
    import random
    from .models import load_continents, load_story_pois, load_featured_cities
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
    import json
    all_story_pois = load_story_pois()
    story_pois = random.sample(all_story_pois, min(6, len(all_story_pois)))
    all_cities = load_featured_cities()
    cities_json = json.dumps([
        {
            'title': c['page'].title,
            'url': c['page'].get_absolute_url(),
            'image': c['image_url'],
            'country': c['country'],
            'lat': float(c['lat']),
            'lng': float(c['lng']),
            'score': c['score'],
        }
        for c in all_cities if c['lat'] and c['lng']
    ])
    return render(request, "guide/home.html", {
        'continents': continents,
        'story_pois': story_pois,
        'cities_json': cities_json,
    })


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

    # Don't show the neighbourhood strip unless at least 3 have images
    if sum(1 for nb in neighbourhoods if nb.image_url) < 3:
        neighbourhoods = []

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
    if page.page_type in NAV_TYPES:
        for poi in pois:
            img_path = _image_path(poi, branch)
            if img_path:
                href = (poi_context_prefix + poi.slug) if poi_context_prefix else poi.get_absolute_url()
                poi_images.append({'url': f'/content-image/{img_path}{branch_qs}', 'title': poi.title, 'href': href})
            if len(poi_images) >= 12:
                break

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
                {'section': s, 'body_html': md.markdown(s.body) if s.body else '', 'pois': sp}
                for s, sp in candidate_sections
            ]

    # Map markers: top 9 for initial view, all locations for dynamic zoom filtering
    markers = _collect_markers(page, nav_pages, top_locations, pois, city_tag_index=city_tag_index)
    markers_full = _collect_markers(page, nav_pages, locations, pois, city_tag_index=city_tag_index)

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
        "poi_images": poi_images,
        "inline_sections": inline_sections,
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


def _marker_from_page(page, highlight=False):
    lat = _safe_float(page.meta.get("latitude"))
    lng = _safe_float(page.meta.get("longitude"))
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "name": page.title,
                "url": page.get_absolute_url(), "highlight": highlight,
                "score": float(page.meta.get("score", 0) or 0),
                "snippet": page.meta.get("snippet", "")}
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
            if nav.page_type == "section_group":
                continue
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
