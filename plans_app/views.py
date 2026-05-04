import hashlib
import json
import re
import secrets
import subprocess
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.utils.safestring import mark_safe

from guide.models import CONTENT_DIR, load_page

import sqlite3
from django.conf import settings as _settings
_SEARCH_DB = Path(_settings.BASE_DIR) / "search.db"

def resolve_location_name(name: str):
    """Resolve a free-text city name to a content path via the search index."""
    if not _SEARCH_DB.is_file():
        return None
    conn = sqlite3.connect(f"file:{_SEARCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        words = name.split()
        parts = ['"' + w.replace('"', '""') + '"' for w in words[:-1]]
        parts.append('"' + words[-1].replace('"', '""') + '"*')
        rows = conn.execute(
            """SELECT url_path FROM docs WHERE docs MATCH ? AND page_type='location'
               ORDER BY CASE WHEN lower(title)=lower(?) THEN 0 ELSE 1 END LIMIT 1""",
            (" ".join(parts), name),
        ).fetchall()
        return rows[0]["url_path"] if rows else None
    except Exception:
        return None
    finally:
        conn.close()

PLANS_DIR = Path(settings.BASE_DIR) / "plans"
_PASSWORDS_FILE = PLANS_DIR / ".passwords.json"
_GEOCACHE_FILE = PLANS_DIR / ".geocache.json"


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"{salt}${h.hex()}"


def _check_password(password, stored):
    if "$" not in stored:
        # Legacy sha256 hash (no salt) from old stub views
        import hashlib as _hl
        return secrets.compare_digest(_hl.sha256(password.encode()).hexdigest(), stored)
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
            # Plan has no password yet — let the user set one via the new plan flow
            return HttpResponseRedirect(f"/plans/new/?slug={slug}")
        if not _plan_authenticated(request, slug):
            return HttpResponseRedirect(f"/plans/join/?next={request.path}")
        return view_fn(request, slug, *args, **kwargs)
    return wrapper


def _plan_title(slug):
    import frontmatter as fm
    path = PLANS_DIR / f"{slug}.md"
    if not path.is_file():
        return slug
    return fm.load(path).metadata.get("title", slug)


# ── Content helpers ───────────────────────────────────────────────────────────

def _image_path(page):
    """Return the relative content path for a page's image, or None."""
    image = page.meta.get("image", "")
    if not image:
        return None
    for candidate in [
        f"{page.path}/{image}",
        f"{page.path.rsplit('/', 1)[0]}/{image}" if "/" in page.path else image,
    ]:
        if (CONTENT_DIR / candidate).is_file():
            return candidate
    return None


def _normalize(s):
    return re.sub(r"[\s_\-]+", "", s.lower())


def _find_poi_in_city(text, city_path):
    city_dir = CONTENT_DIR / city_path
    if not city_dir.is_dir():
        return None
    needle = _normalize(text)
    best = None
    for md_file in city_dir.rglob("*.md"):
        slug = md_file.stem
        if _normalize(slug) == needle:
            rel = str(md_file.relative_to(CONTENT_DIR).with_suffix(""))
            page = load_page(rel)
            if page and page.page_type == "poi":
                return page
        if best is None and needle in _normalize(slug):
            rel = str(md_file.relative_to(CONTENT_DIR).with_suffix(""))
            page = load_page(rel)
            if page and page.page_type == "poi":
                best = page
    if best:
        return best
    for md_file in city_dir.rglob("*.md"):
        rel = str(md_file.relative_to(CONTENT_DIR).with_suffix(""))
        page = load_page(rel)
        if page and page.page_type == "poi" and needle in _normalize(page.title):
            return page
    return None


# ── Geocoding ─────────────────────────────────────────────────────────────────

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


# ── Plan parsing ──────────────────────────────────────────────────────────────

def _parse_plan(path):
    import frontmatter as fm
    if not path.is_file():
        return None
    post = fm.load(path)
    slug = path.stem
    title = post.metadata.get("title", slug)
    stops = _parse_stops(post.content, slug)
    keywords = []
    for line in post.content.splitlines():
        m = re.match(r"^interests:\s*(.+)$", line.strip(), re.IGNORECASE)
        if m:
            keywords = [k.strip().lower() for k in re.split(r"[,;]+", m.group(1)) if k.strip()]
            break
    return {"slug": slug, "title": title, "body": post.content, "stops": stops, "keywords": keywords}


def _parse_stops(body, plan_slug):
    stops = []
    current = None
    _months = (r"(?:january|february|march|april|may|june|july|august"
               r"|september|october|november|december"
               r"|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b")
    _date_re = re.compile(
        rf"\b(\d{{1,2}}\s+{_months}|{_months}\s+\d{{1,2}})",
        re.IGNORECASE,
    )

    for line in body.splitlines():
        h2 = re.match(r"^##\s+(.+)$", line)
        if h2:
            heading = h2.group(1)
            if "|" in heading:
                city_part, dates = heading.split("|", 1)
            else:
                dm = _date_re.search(heading)
                if dm:
                    city_part = heading[:dm.start()]
                    dates = heading[dm.start():]
                else:
                    city_part, dates = heading, ""
            city_part = city_part.strip()
            if "/" in city_part:
                city_path = city_part
                city_name = city_part.split("/")[-1].replace("_", " ").title()
            else:
                city_name = city_part
                # Try full name first, then strip country suffix after comma
                city_path = resolve_location_name(city_part)
                if not city_path and "," in city_part:
                    city_name = city_part.split(",")[0].strip()
                    city_path = resolve_location_name(city_name)
            # Slug must be URL-safe: strip commas and other non-slug chars
            city_slug = re.sub(r"[^a-z0-9]+", "-", city_name.lower()).strip("-")
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
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if bullet:
            text = bullet.group(1).strip()
            page = None
            external_url = None
            display_label = None
            display_domain = None
            if re.match(r"^https?://", text):
                external_url = text
                from urllib.parse import urlparse as _urlparse
                _p = _urlparse(text)
                display_domain = _p.netloc.lstrip("www.")
                display_path = (_p.path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").title()
                                if _p.path and _p.path != "/" else "")
                display_label = display_path or display_domain
            elif text.startswith("/"):
                page = load_page(text.lstrip("/"))
            elif re.match(r"^[\w/_-]+$", text):
                page = load_page(text)
                if not page and current.get("city_path"):
                    page = _find_poi_in_city(text, current["city_path"])
            else:
                if current.get("city_path"):
                    page = _find_poi_in_city(text, current["city_path"])
            image_url = None
            if page:
                img = _image_path(page)
                if img:
                    image_url = f"/content-image/{img}"
            current["items"].append({
                "text": text,
                "page": page,
                "external_url": external_url,
                "display_label": display_label if external_url else None,
                "display_domain": display_domain if external_url else None,
                "image_url": image_url,
            })

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


def authenticated_plan_stops(request):
    """Return list of {slug, title, stops, poi_paths} for authenticated plans.

    Public API used by guide.views to show trip tags on POI pages.
    """
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


# ── Passphrase generation ─────────────────────────────────────────────────────

_PASSPHRASE_WORDS = [
    "canyon", "delta", "fjord", "glacier", "harbor", "lagoon", "meadow", "mesa",
    "oasis", "rapids", "reef", "ridge", "steppe", "summit", "tundra", "valley",
    "atlas", "compass", "ferry", "lantern", "passage", "pilgrim", "rover", "voyage",
    "amber", "birch", "cedar", "cobalt", "coral", "crimson", "dusk", "ember",
    "falcon", "fern", "flint", "heron", "indigo", "jasper", "lemon", "lotus",
    "maple", "marigold", "mist", "moonrise", "mossy", "ochre", "onyx", "pebble",
    "pine", "pollen", "quartz", "saffron", "sage", "scarlet", "sienna", "slate",
    "spruce", "sterling", "talon", "thistle", "thorn", "topaz", "umber", "wren",
    "ancient", "azure", "bold", "bright", "calm", "distant", "golden", "hidden",
    "ivory", "jade", "keen", "lofty", "lunar", "misty", "noble", "pale",
    "quiet", "rugged", "serene", "silent", "silver", "slow", "solar", "spare",
    "stone", "swift", "tall", "vast", "warm", "wild",
]


def _generate_passphrase():
    import random
    passwords = _load_passwords()
    existing = set(passwords.keys())
    for _ in range(100):
        words = random.sample(_PASSPHRASE_WORDS, 3)
        phrase = "-".join(words)
        if phrase not in existing:
            return phrase
    return "-".join(random.sample(_PASSPHRASE_WORDS, 3)) + f"-{random.randint(10,99)}"


# ── Views ─────────────────────────────────────────────────────────────────────

def plan_list(request):
    authenticated = set(request.session.get("authenticated_plans", []))
    join_error = request.session.pop("plan_join_error", None)
    plans = []
    for f in sorted(PLANS_DIR.glob("*.md")):
        slug = f.stem
        if slug not in authenticated:
            continue
        plan = _parse_plan(f)
        if not plan:
            continue
        stops = plan["stops"]
        total_places = sum(len(s["items"]) for s in stops)
        cover_url = None
        for stop in stops:
            if cover_url:
                break
            city_page = load_page(stop["city_path"]) if stop.get("city_path") else None
            img = _image_path(city_page) if city_page else None
            if img:
                cover_url = f"/content-image/{img}"
            else:
                for item in stop["items"]:
                    if item.get("image_url"):
                        cover_url = item["image_url"]
                        break
        all_dates = [s["dates"] for s in stops if s.get("dates")]
        date_range = (f"{all_dates[0].split('–')[0].strip()} – {all_dates[-1].split('–')[-1].strip()}"
                      if len(all_dates) > 1 else (all_dates[0] if all_dates else None))
        cities = [s["city"] for s in stops]
        plans.append({
            "slug": slug,
            "title": plan["title"],
            "stop_count": len(stops),
            "place_count": total_places,
            "cities": cities,
            "date_range": date_range,
            "cover_url": cover_url,
        })
    return render(request, "plans/plan_list.html", {"plans": plans, "join_error": join_error})


def plan_join(request):
    next_url = request.GET.get("next", "")
    error = None
    if request.method == "POST":
        pw = request.POST.get("password", "").strip()
        next_url = request.POST.get("next", "").strip()
        # Extract slug from next_url if possible (e.g. /plans/<slug>/...)
        slug_from_next = None
        if next_url:
            m = re.match(r"^/plans/([^/]+)/", next_url)
            if m:
                slug_from_next = m.group(1)
        passwords = _load_passwords()
        matched_slug = None
        if slug_from_next and slug_from_next in passwords:
            if _check_password(pw, passwords[slug_from_next]):
                matched_slug = slug_from_next
        if not matched_slug:
            for slug, hashed in passwords.items():
                if _check_password(pw, hashed):
                    matched_slug = slug
                    break
        if matched_slug:
            _mark_plan_authenticated(request, matched_slug)
            return HttpResponseRedirect(next_url or f"/plans/{matched_slug}/")
        error = "Wrong passphrase — check what was shown when the trip was created."
    return render(request, "plans/plan_join.html", {"error": error, "next": next_url})


def plan_new(request):
    error = None
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            error = "Please enter a trip title."
        else:
            import frontmatter as fm
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            path = PLANS_DIR / f"{slug}.md"
            if path.exists():
                error = f"A trip named '{slug}' already exists."
            else:
                passphrase = _generate_passphrase()
                keywords_raw = request.POST.get("keywords", "").strip()
                body_lines = []
                if keywords_raw:
                    body_lines.append(f"interests: {keywords_raw}\n")
                title_words = re.split(r"[\s,&+]+", title)
                city_headings = []
                i = 0
                while i < len(title_words):
                    matched = False
                    for length in range(min(4, len(title_words) - i), 0, -1):
                        phrase = " ".join(title_words[i:i+length])
                        if resolve_location_name(phrase):
                            city_headings.append(f"## {phrase}")
                            i += length
                            matched = True
                            break
                    if not matched:
                        i += 1
                if city_headings:
                    if body_lines:
                        body_lines.append("")
                    body_lines.extend(city_headings)
                body = "\n".join(body_lines)
                post = fm.Post(body, title=title, passphrase=passphrase)
                with open(path, "wb") as fh:
                    fm.dump(post, fh)
                _save_password(slug, passphrase)
                request.session[f"new_plan_passphrase_{slug}"] = passphrase
                return HttpResponseRedirect(f"/plans/{slug}/created/")
    return render(request, "plans/plan_new.html", {"error": error})


def plan_created(request, slug):
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        raise Http404
    passphrase = request.session.pop(f"new_plan_passphrase_{slug}", None)
    # Mark authenticated so the user can proceed directly to the plan
    if passphrase:
        _mark_plan_authenticated(request, slug)
    return render(request, "plans/plan_created.html", {"plan": plan, "passphrase": passphrase})


@_require_plan_auth
def plan_detail(request, slug):
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        raise Http404

    for stop in plan["stops"]:
        city_page = load_page(stop["city_path"]) if stop.get("city_path") else None
        img = _image_path(city_page) if city_page else None
        if not img:
            for item in stop["items"]:
                if item.get("image_url"):
                    stop["city_image_url"] = item["image_url"]
                    break
        stop["city_image_url"] = f"/content-image/{img}" if img else stop.get("city_image_url")

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

    if len(plan["stops"]) == 1:
        return HttpResponseRedirect(plan["stops"][0]["url"])

    return render(request, "plans/plan_detail.html", {
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
    if not markers:
        coords = _city_coords(stop)
        if coords:
            markers = [{"lat": coords[0], "lng": coords[1], "title": stop["city"], "url": stop.get("destination_url") or ""}]
    city_snippet = None
    city_image_url = None
    if city_page:
        city_snippet = city_page.meta.get("snippet") or ""
        if not city_snippet and city_page.body:
            first_para = re.split(r"\n\n+", city_page.body.strip())[0]
            first_para = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first_para)
            first_para = re.sub(r"[*_`#>]+", "", first_para).strip()
            city_snippet = first_para[:300] + ("…" if len(first_para) > 300 else "")
        img = _image_path(city_page)
        if img:
            city_image_url = f"/content-image/{img}"

    suggestions = []
    if stop.get("city_path"):
        already_added = {item["text"] for item in stop["items"]}
        already_added_paths = {item["page"].path for item in stop["items"] if item["page"]}
        note_needles = [_normalize(item["text"]) for item in stop["items"]
                        if not item["page"] and not item["external_url"]]
        _KEYWORD_EXPANSIONS = {
            "art": ["museum", "gallery", "art", "culture", "exhibition"],
            "culture": ["museum", "theatre", "theater", "opera", "concert", "culture", "heritage", "history"],
            "opera": ["opera", "concert", "music", "theatre", "theater"],
            "music": ["music", "concert", "jazz", "opera", "nightlife"],
            "food": ["restaurant", "food", "market", "cafe", "dining", "cuisine"],
            "hiking": ["hiking", "nature", "walk", "park", "outdoors", "trail"],
            "beaches": ["beach", "sea", "coast", "swimming", "waterfront"],
            "history": ["history", "heritage", "museum", "monument", "cathedral", "church", "castle"],
            "architecture": ["architecture", "building", "design"],
            "nightlife": ["nightlife", "bar", "club", "music"],
            "shopping": ["shopping", "market", "shop"],
            "nature": ["nature", "park", "garden", "outdoors"],
        }
        expanded_keywords = set()
        for k in plan.get("keywords", []):
            kn = k.lower().strip()
            expanded_keywords.add(_normalize(kn))
            for exp in _KEYWORD_EXPANSIONS.get(kn, []):
                expanded_keywords.add(_normalize(exp))

        city_dir = CONTENT_DIR / stop["city_path"]
        for md_file in sorted(city_dir.rglob("*.md")):
            rel = str(md_file.relative_to(CONTENT_DIR).with_suffix(""))
            if rel in already_added or rel in already_added_paths:
                continue
            page = load_page(rel)
            if not page or page.page_type != "poi":
                continue
            img = _image_path(page)
            slug_norm = _normalize(page.path.split("/")[-1])
            title_norm = _normalize(page.title)
            tags_norm = [_normalize(t) for t in page.tags]
            poi_text = slug_norm + " " + title_norm + " " + " ".join(tags_norm)
            note_match = any(n in poi_text or poi_text in n for n in note_needles) if note_needles else False
            keyword_match = any(k in poi_text for k in expanded_keywords) if expanded_keywords else False
            score = (2 if note_match else 0) + (2 if keyword_match else 0) + (1 if img else 0)
            suggestions.append({
                "page": page,
                "image_url": f"/content-image/{img}" if img else None,
                "_score": score,
                "note_match": note_match or keyword_match,
            })
        suggestions.sort(key=lambda x: -x["_score"])

    return render(request, "plans/plan_stop.html", {
        "plan": plan,
        "stop": stop,
        "markers": mark_safe(json.dumps(markers)),
        "city_snippet": city_snippet,
        "city_image_url": city_image_url,
        "suggestions": suggestions,
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
    return render(request, "plans/plan_edit.html", {
        "plan": {"slug": slug, "title": post.metadata.get("title", slug)},
        "body": post.content,
        "passphrase": post.metadata.get("passphrase"),
    })


def _plan_file_add(slug, city_slug, poi_path):
    path = PLANS_DIR / f"{slug}.md"
    import frontmatter as fm
    post = fm.load(path)
    lines = post.content.splitlines()
    insert_at = None
    in_section = False
    for i, line in enumerate(lines):
        h2 = re.match(r"^##\s+(.+)$", line)
        if h2:
            heading = h2.group(1)
            city_raw = heading.split("|", 1)[0].strip()
            if "/" in city_raw:
                heading_slug = city_raw.split("/")[-1].replace("_", " ").lower().replace(" ", "-")
            else:
                heading_slug = city_raw.lower().replace(" ", "-")
            in_section = (heading_slug == city_slug)
            if in_section:
                insert_at = i + 1
            continue
        if in_section:
            if re.match(r"^[-*]\s+", line):
                insert_at = i + 1
            elif line.strip() == "":
                pass
            else:
                break
    if insert_at is None:
        return False
    if any(l.strip().lstrip("-* ") == poi_path for l in lines):
        return False
    lines.insert(insert_at, f"- {poi_path}")
    post.content = "\n".join(lines)
    with open(path, "wb") as fh:
        fm.dump(post, fh)
    return True


def _plan_file_remove(slug, poi_path):
    path = PLANS_DIR / f"{slug}.md"
    import frontmatter as fm
    post = fm.load(path)
    lines = post.content.splitlines()
    new_lines = [l for l in lines if l.strip().lstrip("-* ") != poi_path]
    if len(new_lines) == len(lines):
        return False
    post.content = "\n".join(new_lines)
    with open(path, "wb") as fh:
        fm.dump(post, fh)
    return True


@_require_plan_auth
def plan_poi_add(request, slug, city_slug=None):
    if request.method != "POST":
        raise Http404
    poi_path = request.POST.get("poi_path", "").strip()
    if poi_path:
        if city_slug is None:
            plan = _parse_plan(PLANS_DIR / f"{slug}.md")
            if plan:
                for stop in plan["stops"]:
                    cp = stop.get("city_path")
                    if cp and poi_path.startswith(cp + "/"):
                        city_slug = stop["city_slug"]
                        break
                if city_slug is None:
                    for stop in plan["stops"]:
                        cs = stop["city_slug"].replace("-", "")
                        if cs in poi_path.replace("/", "").replace("_", "").lower():
                            city_slug = stop["city_slug"]
                            break
        if city_slug:
            _plan_file_add(slug, city_slug, poi_path)
    return HttpResponseRedirect(request.POST.get("next", f"/plans/{slug}/"))


@_require_plan_auth
def plan_note_edit(request, slug, city_slug):
    if request.method != "POST":
        raise Http404
    old_text = request.POST.get("old_text", "").strip()
    new_text = request.POST.get("new_text", "").strip()
    if old_text and new_text and old_text != new_text:
        import frontmatter as fm
        path = PLANS_DIR / f"{slug}.md"
        post = fm.load(path)
        lines = post.content.splitlines()
        new_lines = [
            re.sub(r"^([-*]\s+)" + re.escape(old_text) + r"$", r"\g<1>" + new_text, l)
            for l in lines
        ]
        post.content = "\n".join(new_lines)
        with open(path, "wb") as fh:
            fm.dump(post, fh)
    return HttpResponseRedirect(request.POST.get("next", f"/plans/{slug}/{city_slug}/"))


@_require_plan_auth
def plan_poi_remove(request, slug, city_slug):
    if request.method != "POST":
        raise Http404
    poi_path = request.POST.get("poi_path", "").strip()
    if poi_path:
        _plan_file_remove(slug, poi_path)
    return HttpResponseRedirect(request.POST.get("next", f"/plans/{slug}/{city_slug}/"))


# ── MCP API endpoint ──────────────────────────────────────────────────────────

import secrets as _secrets
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

_WORDS = [
    "amber","apple","arrow","azure","badge","berry","birch","blade","bloom","blaze",
    "brave","brick","brook","cedar","chalk","charm","coral","crane","creek","crest",
    "daisy","delta","drake","drift","eagle","ember","feast","ferry","field","finch",
    "fjord","flare","flash","fleet","flora","forge","frost","gecko","geyser","ghost",
    "glade","globe","grail","grain","grove","guide","haven","hazel","heath","heron",
    "holly","honor","ivory","jasper","jewel","kayak","kelp","lance","larch","laser",
    "leafy","ledge","lemon","lilac","lotus","maple","marsh","meadow","merlin","metro",
    "mocha","mossy","mound","mount","nexus","noble","nomad","oasis","ocean","olive",
    "opal","orbit","otter","oyster","panda","pearl","pebble","perch","pilot","pixel",
    "plaid","plume","polar","poppy","prism","pulse","quartz","quest","quill","raven",
    "razor","realm","regal","ridge","rivet","robin","rocky","royal","sable","sandy",
    "scout","serif","shark","shelf","shell","shift","shore","sigma","slate","solar",
    "spark","spell","spire","spray","stark","steel","stern","stoic","storm","swift",
    "sword","talon","tempo","terra","tiger","titan","token","topaz","torch","trace",
    "trail","trout","trove","tulip","ultra","unity","urban","vault","veldt","verge",
    "walnut","weave","wheat","wheel","woven","xenon","yacht","zebra","zenith","zephyr",
]

def _generate_passphrase(n=3):
    return "-".join(_secrets.choice(_WORDS) for _ in range(n))


@csrf_exempt
@require_POST
def api_plan_create(request):
    """
    POST /api/plans/create
    Body (JSON): { "destination", "start_date", "end_date", "notes" }
    Returns: { "url", "slug", "passphrase", "city_path", "city_title" }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)

    destination = body.get("destination", "").strip()
    start_date  = body.get("start_date", "").strip()
    end_date    = body.get("end_date", "").strip()
    notes       = body.get("notes", "").strip()

    if not destination or not start_date:
        return JsonResponse({"error": "destination and start_date are required"}, status=400)

    # Resolve city path
    if "/" in destination:
        city_path  = destination
        city_page  = load_page(destination)
        city_title = city_page.title if city_page else destination.split("/")[-1].replace("_", " ").title()
    else:
        city_path  = resolve_location_name(destination)
        city_page  = load_page(city_path) if city_path else None
        city_title = city_page.title if city_page else destination

    # Build date range string
    try:
        from datetime import date as _date
        s = _date.fromisoformat(start_date)
        e = _date.fromisoformat(end_date) if end_date else s
        if s.month == e.month and s.year == e.year:
            date_str = f"{s.day}–{e.day} {s.strftime('%B %Y')}" if s != e else s.strftime("%-d %B %Y")
        else:
            date_str = f"{s.strftime('%-d %B')} – {e.strftime('%-d %B %Y')}"
    except ValueError:
        date_str = f"{start_date} – {end_date}" if end_date else start_date

    # Build slug and passphrase
    import re as _re
    base = _re.sub(r"[^\w\s-]", "", city_title.lower()).strip()
    base = _re.sub(r"[\s_]+", "-", base)
    month_part = start_date[:7]
    slug = f"{base}-{month_part}-{_secrets.token_hex(3)}"

    passphrase = _generate_passphrase(3)
    _save_password(slug, passphrase)
    request.session[f"new_plan_passphrase_{slug}"] = passphrase

    # Write plan file
    import frontmatter as _fm
    content_lines = [f"## {city_title} | {date_str}"]
    if notes:
        content_lines.append(f"- {notes}")
    if city_path:
        content_lines.append(f"- {city_path}")
    post = _fm.Post("\n".join(content_lines) + "\n", title=f"Trip to {city_title}", created_by="tabbi-mcp")
    PLANS_DIR.mkdir(exist_ok=True)
    (PLANS_DIR / f"{slug}.md").write_text(_fm.dumps(post))

    base_url = request.build_absolute_uri("/").rstrip("/")
    return JsonResponse({
        "url":        f"{base_url}/plans/{slug}/created/",
        "slug":       slug,
        "passphrase": passphrase,
        "city_path":  city_path,
        "city_title": city_title,
    })
