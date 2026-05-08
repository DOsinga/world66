import hashlib
import json
import os
import re
import secrets
import subprocess
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.utils.safestring import mark_safe

from guide.models import CONTENT_DIR, load_page


@dataclass
class DraftPage:
    """A researched POI that lives in plans/pois/ — not yet published to content/."""
    title: str
    path: str       # e.g. ~pois/europe/france/marseille/vieux-port
    body: str
    category: str
    meta: dict = field(default_factory=dict)
    page_type: str = "poi"
    tags: list = field(default_factory=list)

    def get_absolute_url(self):
        # path is like ~pois/europe/germany/berlin/brandenburger-tor
        poi_rel = self.path[len("~pois/"):]  # strip ~pois/ prefix
        return f"/plans/draft-poi/{poi_rel}/"

import logging
import sqlite3
from django.conf import settings as _settings
_SEARCH_DB = Path(_settings.BASE_DIR) / "search.db"
_SEARCH_LOG = Path(_settings.BASE_DIR) / "logs" / "search.log"
_SEARCH_LOG.parent.mkdir(exist_ok=True)

_search_logger = logging.getLogger("w66.search")
if not _search_logger.handlers:
    _h = logging.FileHandler(_SEARCH_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    _search_logger.addHandler(_h)
    _search_logger.setLevel(logging.DEBUG)
    _search_logger.propagate = False


def resolve_location_name(name: str):
    """Resolve a free-text city name to a content path via the search index.

    Prefers exact title matches at shallower depths (more prominent locations).
    Understands "City, Country/Region" syntax — uses the part after the comma as a
    path hint to boost results whose URL contains that region.
    US sub-state cities are deprioritised unless the name contains a US hint.
    """
    if not _SEARCH_DB.is_file():
        _search_logger.warning("QUERY %r  db_missing", name)
        return None
    conn = sqlite3.connect(f"file:{_SEARCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # Split "City, Region" into a search term and a path hint.
        # "Lima, Peru" → search_term="Lima", path_hint="peru"
        # "Sacred Valley, Peru" → search_term="Sacred Valley", path_hint="peru"
        # "Nashville" → search_term="Nashville", path_hint=None
        if "," in name:
            search_term, hint_raw = name.split(",", 1)
            search_term = search_term.strip()
            path_hint = hint_raw.strip().lower().replace(" ", "")  # "Peru" → "peru"
        else:
            search_term = name.strip()
            path_hint = None

        words = search_term.split()
        parts = ['"' + w.replace('"', '""') + '"' for w in words[:-1]]
        parts.append('"' + words[-1].replace('"', '""') + '"*')
        fts_query = " ".join(parts)

        fts_rows = conn.execute(
            """SELECT url_path, title, aliases FROM docs
               WHERE docs MATCH ? AND page_type='location'
               ORDER BY CASE WHEN lower(title)=lower(?) THEN 0 ELSE 1 END
               LIMIT 20""",
            (fts_query, search_term),
        ).fetchall()

        # Always augment with a title/alias LIKE query so that spelling variants
        # (Cusco/Cuzco, Köln/Cologne) get a chance to surface with an exact-title score.
        like_rows = conn.execute(
            """SELECT url_path, title, aliases FROM docs
               WHERE (lower(title) LIKE ? OR lower(aliases) LIKE ?) AND page_type='location'
               LIMIT 20""",
            (f"%{search_term.lower()}%", f"%{search_term.lower()}%"),
        ).fetchall()

        # Merge, deduplicating by url_path (FTS results first, then LIKE extras)
        seen = set()
        rows = []
        for r in list(fts_rows) + list(like_rows):
            if r["url_path"] not in seen:
                seen.add(r["url_path"])
                rows.append(r)

        if not rows:
            _search_logger.info("QUERY %r  fts=%r  no_results", name, fts_query)
            return None

        # If we have a path_hint and none of the candidates match it, the FTS is
        # returning body-text noise (e.g. "Sacred Valley" mentioned in Bhutan pages).
        # In that case, bail out rather than returning a confidently wrong result.
        if path_hint and not any(path_hint in row["url_path"].lower() for row in rows):
            _search_logger.info(
                "QUERY %r  fts=%r  path_hint=%r  no_hint_match  returning None",
                name, fts_query, path_hint,
            )
            return None

        name_lower = name.lower()
        us_hint = any(h in name_lower for h in ("united states", "usa", ", us,", "ohio",
                      "texas", "california", "florida", "new york"))

        best_path = None
        best_score = None
        scored = []
        for row in rows:
            path = row["url_path"]
            title = row["title"]
            aliases = (row["aliases"] or "").lower().split()
            depth = path.count("/")
            exact = title.lower() == search_term.lower() or search_term.lower() in aliases

            # Boost when the path contains the region hint (e.g. "peru" in path for "Lima, Peru")
            hint_bonus = 0
            if path_hint and path_hint not in path.lower():
                hint_bonus = 5  # penalise results outside the hinted region

            # Penalise US sub-state paths unless a US hint was given
            us_penalty = 0
            if not us_hint and path.startswith("northamerica/unitedstates/") and depth >= 4:
                us_penalty = 10

            # Lower score = better
            score = (0 if exact else 2) + depth + hint_bonus + us_penalty
            scored.append((score, path, title))
            if best_score is None or score < best_score:
                best_score = score
                best_path = path

        scored.sort(key=lambda x: x[0])
        candidates = "  |  ".join(f"{p} ({t!r}, score={s})" for s, p, t in scored[:5])
        _search_logger.info(
            "QUERY %r  fts=%r  search_term=%r  path_hint=%r  us_hint=%s  winner=%r  candidates=[%s]",
            name, fts_query, search_term, path_hint, us_hint, best_path, candidates,
        )

        return best_path
    except Exception as exc:
        _search_logger.exception("QUERY %r  error: %s", name, exc)
        return None
    finally:
        conn.close()

PLANS_DIR = Path(settings.BASE_DIR) / "plans"
DRAFT_POIS_DIR = PLANS_DIR / "pois"
DRAFT_LOCATIONS_DIR = PLANS_DIR / "locations"


def _load_city_page(city_path: str):
    """Load a city page from content/ or from plans/locations/ for draft locations."""
    if not city_path:
        return None
    if city_path.startswith("~locations/"):
        import frontmatter as _fmloc
        slug = city_path[len("~locations/"):]
        loc_file = DRAFT_LOCATIONS_DIR / f"{slug}.md"
        if loc_file.is_file():
            post = _fmloc.load(str(loc_file))
            from guide.models import Page
            return Page(
                slug=slug,
                path=city_path,
                title=post.metadata.get("title", slug.replace("-", " ").title()),
                body=post.content,
                meta=post.metadata,
                page_type="location",
            )
        return None
    return load_page(city_path)
_PASSWORDS_FILE = PLANS_DIR / ".passwords.json"
_GEOCACHE_FILE = PLANS_DIR / ".geocache.json"


def _load_draft_pois(city_path: str) -> list[DraftPage]:
    """Load draft POIs for a city from plans/pois/<city_path>/."""
    import frontmatter as fm
    city_dir = DRAFT_POIS_DIR / city_path
    if not city_dir.is_dir():
        return []
    pages = []
    for md_file in sorted(city_dir.glob("*.md")):
        try:
            post = fm.load(str(md_file))
            slug = md_file.stem
            page_type = post.metadata.get("type", "poi")
            pages.append(DraftPage(
                title=post.metadata.get("title", slug),
                path=f"~pois/{city_path}/{slug}",
                body=post.content,
                category=post.metadata.get("category", ""),
                meta={
                    "snippet": post.content[:200].split("\n\n")[0],
                    "latitude": post.metadata.get("latitude"),
                    "longitude": post.metadata.get("longitude"),
                    "duration_hours": post.metadata.get("duration_hours"),
                    "stops": post.metadata.get("stops", []),
                },
                page_type=page_type,
                tags=[post.metadata.get("category", "").lower()],
            ))
        except Exception:
            continue
    return pages


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
        city_page = _load_city_page(city_path)
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

        # Trek: use its waypoints as markers
        if getattr(page, "page_type", None) == "trek":
            for wp in page.waypoints:
                if wp["lat"] and wp["lng"]:
                    markers.append({
                        "lat": float(wp["lat"]), "lng": float(wp["lng"]),
                        "title": wp["name"], "url": page.get_absolute_url() or "",
                    })
            continue

        lat = page.meta.get("latitude")
        lng = page.meta.get("longitude")
        if lat and lng:
            markers.append({
                "lat": float(lat), "lng": float(lng),
                "title": page.title, "url": page.get_absolute_url() or "",
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
                # Fallback: check draft locations directory
                if not city_path:
                    draft_slug = re.sub(r"[^a-z0-9]+", "-", city_name.lower()).strip("-")
                    if (DRAFT_LOCATIONS_DIR / f"{draft_slug}.md").is_file():
                        city_path = f"~locations/{draft_slug}"
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
            elif text.startswith("~locations/"):
                # Draft location reference — set city_path on the stop, don't add as item
                if current["city_path"] is None:
                    current["city_path"] = text
                continue
            elif text.startswith("~pois/"):
                # Draft POI from plans/pois/
                draft_rel = text[len("~pois/"):]  # e.g. europe/france/marseille/vieux-port
                parts = draft_rel.rsplit("/", 1)
                if len(parts) == 2:
                    draft_city, draft_slug = parts
                    import frontmatter as _fm
                    draft_file = DRAFT_POIS_DIR / draft_city / f"{draft_slug}.md"
                    if draft_file.is_file():
                        _post = _fm.load(str(draft_file))
                        page = DraftPage(
                            title=_post.metadata.get("title", draft_slug),
                            path=text,
                            body=_post.content,
                            category=_post.metadata.get("category", ""),
                            meta={"snippet": _post.content[:200].split("\n\n")[0],
                                  "latitude": _post.metadata.get("latitude"),
                                  "longitude": _post.metadata.get("longitude")},
                            tags=[_post.metadata.get("category", "").lower()],
                        )
            elif text.startswith("/"):
                page = load_page(text.lstrip("/"))
            elif re.match(r"^[\w/_-]+$", text):
                page = load_page(text)
                if not page and current.get("city_path"):
                    page = _find_poi_in_city(text, current["city_path"])
            else:
                if current.get("city_path"):
                    page = _find_poi_in_city(text, current["city_path"])
            # Skip location-type pages — they are the city/destination, not a POI
            if page and page.page_type == "location":
                page = None
                if not external_url:
                    continue
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
            city_page = _load_city_page(stop.get("city_path"))
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
        city_page = _load_city_page(stop.get("city_path"))
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
    city_page = _load_city_page(stop.get("city_path"))
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

    # Fall back to plan-stored image if content image not found
    if not city_image_url:
        stop_images = plan.get("stop_images") if isinstance(plan, dict) else {}
        if not stop_images:
            import frontmatter as _fm2
            _plan_file = PLANS_DIR / f"{plan['slug']}.md"
            if _plan_file.is_file():
                stop_images = _fm2.load(str(_plan_file)).metadata.get("stop_images", {})
        stored = stop_images.get(city_slug)
        if stored:
            city_image_url = f"/plans/image/{stored}"

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

        # Treks under this city — suggest before POIs
        city_page_for_treks = _load_city_page(stop["city_path"])
        if city_page_for_treks:
            _, child_locs, _ = city_page_for_treks.children()
            for trek_page in child_locs:
                if trek_page.page_type != "trek":
                    continue
                if trek_page.path in already_added or trek_page.path in already_added_paths:
                    continue
                img = _image_path(trek_page)
                suggestions.append({
                    "page": trek_page,
                    "image_url": f"/content-image/{img}" if img else None,
                    "_score": 5,
                    "note_match": False,
                    "is_draft": False,
                })

        # Real world66 vibes — suggest before POIs (score 4, after treks)
        city_dir = CONTENT_DIR / stop["city_path"]
        for md_file in sorted(city_dir.rglob("*.md")):
            rel = str(md_file.relative_to(CONTENT_DIR).with_suffix(""))
            if rel in already_added or rel in already_added_paths:
                continue
            page = load_page(rel)
            if not page or page.page_type != "vibe":
                continue
            img = _image_path(page)
            suggestions.append({
                "page": page,
                "image_url": f"/content-image/{img}" if img else None,
                "_score": 4,
                "note_match": False,
                "is_draft": False,
            })

        # Real world66 POIs
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
                "is_draft": False,
            })
        suggestions.sort(key=lambda x: -x["_score"])

    # Extract trek routes from plan items so the template can draw polylines
    trek_routes = []
    for item in stop["items"]:
        page = item["page"]
        if page and getattr(page, "page_type", None) == "trek":
            wps = [wp for wp in page.waypoints if wp["lat"] and wp["lng"]]
            if wps:
                trek_routes.append({
                    "title": page.title,
                    "url": page.get_absolute_url(),
                    "waypoints": wps,
                })

    return render(request, "plans/plan_stop.html", {
        "plan": plan,
        "stop": stop,
        "markers": mark_safe(json.dumps(markers)),
        "trek_routes": mark_safe(json.dumps(trek_routes)),
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
    # Don't add location-type pages — they are city headings, not POIs
    if not poi_path.startswith("~"):
        _page = load_page(poi_path.lstrip("/"))
        if _page and _page.page_type == "location":
            return False
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


def plan_image(request, image_path):
    """Serve an image stored inside the plans/ directory."""
    import mimetypes
    from django.http import FileResponse
    safe_path = image_path.lstrip("/")
    # Only allow images/... paths to prevent directory traversal
    if not safe_path.startswith("images/"):
        raise Http404
    file_path = PLANS_DIR / safe_path
    if not file_path.is_file():
        raise Http404
    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(open(file_path, "rb"), content_type=content_type or "image/jpeg")


def draft_poi_detail(request, poi_path):
    """Show a draft POI from plans/pois/<poi_path>.md"""
    import frontmatter as fm
    md_file = DRAFT_POIS_DIR / f"{poi_path}.md"
    if not md_file.is_file():
        raise Http404
    post = fm.load(str(md_file))
    import markdown as _md
    body_html = _md.markdown(post.content) if post.content else ""
    return render(request, "plans/draft_poi.html", {
        "title":    post.metadata.get("title", poi_path.split("/")[-1]),
        "category": post.metadata.get("category", ""),
        "body":     body_html,
        "lat":      post.metadata.get("latitude"),
        "lng":      post.metadata.get("longitude"),
    })


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


def _fetch_wikipedia_image(city_title: str, dest_dir: Path) -> str | None:
    """Fetch the main image for a Wikipedia article and save it to dest_dir.

    Uses the Wikimedia REST API (no key needed). Returns the saved filename or None.
    """
    import urllib.request
    import urllib.parse

    title_encoded = urllib.parse.quote(city_title.replace(" ", "_"))
    api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title_encoded}"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "Tabbi/1.0 (travel planner)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        _search_logger.warning("WIKIPEDIA_IMAGE_FETCH_FAILED %r: %s", city_title, exc)
        return None

    img_url = (data.get("originalimage") or data.get("thumbnail") or {}).get("source")
    if not img_url:
        return None

    ext = img_url.rsplit(".", 1)[-1].split("?")[0].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    slug = re.sub(r"[^a-z0-9]+", "-", city_title.lower()).strip("-")
    filename = f"{slug}-wiki.{ext}"
    dest = dest_dir / filename
    if dest.exists():
        return filename
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": "Tabbi/1.0 (travel planner)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            dest.write_bytes(resp.read())
        _search_logger.info("WIKIPEDIA_IMAGE_SAVED %r → %s", city_title, filename)
        return filename
    except Exception as exc:
        _search_logger.warning("WIKIPEDIA_IMAGE_DOWNLOAD_FAILED %r: %s", city_title, exc)
        return None


def _copy_location_image(city_page, plan_slug: str) -> str | None:
    """Copy a city page's hero image into plans/images/<plan_slug>/.

    Falls back to fetching from Wikipedia when no content image exists.
    Returns the relative path (e.g. 'images/<plan_slug>/<file>') or None.
    """
    import shutil
    dest_dir = PLANS_DIR / "images" / plan_slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    if city_page:
        img_rel = _image_path(city_page)
        if img_rel:
            src = CONTENT_DIR / img_rel
            if src.is_file():
                dest = dest_dir / src.name
                if not dest.exists():
                    shutil.copy2(src, dest)
                return f"images/{plan_slug}/{src.name}"

    # No content image — try Wikipedia
    if city_page:
        filename = _fetch_wikipedia_image(city_page.title, dest_dir)
        if filename:
            return f"images/{plan_slug}/{filename}"

    return None


def _create_draft_location(city_title: str, region_hint: str = "") -> str:
    """Create a draft location in plans/locations/ — NOT part of the w66 guide.

    Works like draft POIs: lives in plans/, referenced as ~locations/<slug>,
    only visible in a user's plan until a curator publishes it to content/.

    Returns the draft path, e.g. '~locations/sacred-valley'.
    """
    import frontmatter as _fm2

    slug = re.sub(r"[^a-z0-9]+", "-", city_title.lower()).strip("-")
    if not slug:
        slug = "unknown"

    DRAFT_LOCATIONS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DRAFT_LOCATIONS_DIR / f"{slug}.md"

    if not file_path.exists():
        meta = {"title": city_title, "type": "location"}
        if region_hint:
            meta["region_hint"] = region_hint
        post = _fm2.Post("", **meta)
        file_path.write_text(_fm2.dumps(post))

    draft_path = f"~locations/{slug}"
    _search_logger.info("DRAFT_LOCATION_CREATED %r  path=%r  hint=%r", city_title, draft_path, region_hint)
    return draft_path


def _resolve_stop(destination: str, start_date: str, end_date: str, notes: str) -> dict:
    """Resolve one stop's destination to a city_path, city_title, date_str."""
    import re as _re
    from datetime import date as _date

    dest = destination.strip()
    if "/" in dest:
        city_path  = dest
        city_page  = load_page(dest)
        city_title = city_page.title if city_page else dest.split("/")[-1].replace("_", " ").title()
    else:
        # Extract region hint from "City, Region" before resolving
        region_hint = ""
        if "," in dest:
            city_name, hint_raw = dest.split(",", 1)
            region_hint = hint_raw.strip()
            dest = city_name.strip()
        city_path = resolve_location_name(dest if not region_hint else f"{dest}, {region_hint}")
        if not city_path:
            city_path = _create_draft_location(dest, region_hint)
        city_page  = _load_city_page(city_path) if city_path else None
        city_title = city_page.title if city_page else dest

    try:
        s = _date.fromisoformat(start_date)
        e = _date.fromisoformat(end_date) if end_date else s
        if s.month == e.month and s.year == e.year:
            date_str = f"{s.day}–{e.day} {s.strftime('%B %Y')}" if s != e else s.strftime("%-d %B %Y")
        else:
            date_str = f"{s.strftime('%-d %B')} – {e.strftime('%-d %B %Y')}"
    except ValueError:
        date_str = f"{start_date} – {end_date}" if end_date else start_date

    city_slug = _re.sub(r"[^a-z0-9]+", "-", city_title.lower()).strip("-")
    return {
        "city_title": city_title,
        "city_path":  city_path or "",
        "city_slug":  city_slug,
        "city_page":  city_page,   # used by api_plan_create to copy image; not serialised
        "date_str":   date_str,
        "notes":      notes,
        "start_date": start_date,
    }


@csrf_exempt
@require_POST
def api_plan_create(request):
    """
    POST /api/plans/create
    Body (JSON): {
      "title": "optional trip title",
      "stops": [{"destination", "start_date", "end_date", "notes"}, ...]
    }
    Returns: { "url", "slug", "passphrase", "cities": [{city_title, city_path, city_slug}, ...] }
    """
    import re as _re
    import frontmatter as _fm

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)

    raw_stops = body.get("stops") or []
    if not raw_stops:
        return JsonResponse({"error": "stops list is required"}, status=400)

    # Resolve each stop
    resolved = []
    for s in raw_stops:
        resolved.append(_resolve_stop(
            destination=s.get("destination", ""),
            start_date=s.get("start_date", ""),
            end_date=s.get("end_date", ""),
            notes=s.get("notes", ""),
        ))

    # Build plan slug from first city + first date
    first = resolved[0]
    trip_title = body.get("title", "").strip() or (
        f"Trip to {', '.join(r['city_title'] for r in resolved)}"
    )
    base = _re.sub(r"[^\w\s-]", "", first["city_title"].lower()).strip()
    base = _re.sub(r"[\s_]+", "-", base)
    month_part = first["start_date"][:7]
    slug = f"{base}-{month_part}-{_secrets.token_hex(3)}"

    passphrase = _generate_passphrase(3)
    _save_password(slug, passphrase)
    request.session[f"new_plan_passphrase_{slug}"] = passphrase

    PLANS_DIR.mkdir(exist_ok=True)

    # Copy city images into plans/images/<slug>/ and record in frontmatter
    stop_images = {}
    for r in resolved:
        img_path = _copy_location_image(r.get("city_page"), slug)
        if img_path:
            stop_images[r["city_slug"]] = img_path

    # Build plan markdown with one ## section per stop
    content_lines = []
    for r in resolved:
        content_lines.append(f"## {r['city_title']} | {r['date_str']}")
        if r["notes"]:
            content_lines.append(f"- {r['notes']}")
        if r["city_path"]:
            content_lines.append(f"- {r['city_path']}")
        content_lines.append("")

    meta = {"title": trip_title, "created_by": "tabbi-mcp"}
    if stop_images:
        meta["stop_images"] = stop_images
    post = _fm.Post("\n".join(content_lines), **meta)
    (PLANS_DIR / f"{slug}.md").write_text(_fm.dumps(post))

    first_city_slug = resolved[0]["city_slug"]
    base_url = request.build_absolute_uri("/").rstrip("/")
    return JsonResponse({
        "url":        f"{base_url}/plans/join/?next=/plans/{slug}/{first_city_slug}/",
        "slug":       slug,
        "passphrase": passphrase,
        "cities":     [{"city_title": r["city_title"],
                        "city_path":  r["city_path"],
                        "city_slug":  r["city_slug"]} for r in resolved],
    })


def _check_plan_auth(body: dict, plan_slug: str) -> bool:
    """Return True if the request body carries valid auth for the given plan.

    Accepts either:
    - passphrase: the plan's own passphrase (preferred)
    - secret: the server-wide RESEARCH_SUBMIT_SECRET (legacy / server-to-server)
    """
    passphrase = body.get("passphrase", "")
    if passphrase:
        passwords = _load_passwords()
        hashed = passwords.get(plan_slug)
        return bool(hashed and _check_password(passphrase, hashed))
    server_secret = os.environ.get("RESEARCH_SUBMIT_SECRET", "")
    if server_secret:
        return secrets.compare_digest(body.get("secret", ""), server_secret)
    return False


@csrf_exempt
@require_POST
def api_plan_add_pois(request):
    """
    POST /api/plan/add-pois
    Body: { "plan_slug", "city_slug", "poi_paths": [...], "passphrase": "<plan passphrase>" }
    Adds existing w66 content paths directly to the plan file.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)

    plan_slug = body.get("plan_slug", "").strip()
    city_slug = body.get("city_slug", "").strip()

    if not plan_slug or not city_slug:
        return JsonResponse({"error": "plan_slug and city_slug are required"}, status=400)

    if not _check_plan_auth(body, plan_slug):
        return JsonResponse({"error": "unauthorized"}, status=403)

    poi_paths = body.get("poi_paths", [])
    if not isinstance(poi_paths, list):
        return JsonResponse({"error": "poi_paths must be a list"}, status=400)

    added = 0
    for path in poi_paths:
        if isinstance(path, str) and path.strip():
            if _plan_file_add(plan_slug, city_slug, path.strip()):
                added += 1

    return JsonResponse({"added": added})


@csrf_exempt
@require_POST
def api_research_submit(request):
    """
    POST /api/research/submit
    Body (JSON): {
      "plan_slug": "<slug>",
      "passphrase": "<plan passphrase>",
      "city_slug": "<city_slug>",
      "city_path": "europe/france/marseille",
      "city_title": "Marseille",
      "pois": [{"name", "category", "body", "latitude", "longitude"}, ...]
    }
    Writes draft POI files to plans/pois/<city_path>/ and returns {"written": N}.
    """
    import frontmatter as _fm

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)

    plan_slug  = body.get("plan_slug", "").strip()
    city_slug  = body.get("city_slug", "").strip()
    city_path  = body.get("city_path", "").strip().strip("/")
    city_title = body.get("city_title", "").strip()
    pois       = body.get("pois", [])

    if not isinstance(pois, list) or not city_title:
        return JsonResponse({"error": "city_title and pois are required"}, status=400)

    if plan_slug and not _check_plan_auth(body, plan_slug):
        return JsonResponse({"error": "unauthorized"}, status=403)

    # If city isn't in the guide yet, store drafts under uncategorised/<slug>
    if not city_path:
        _slug = re.sub(r"[^a-z0-9]+", "-", city_title.lower()).strip("-")
        city_path = f"uncategorised/{_slug}"

    city_dir = DRAFT_POIS_DIR / city_path
    city_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(text):
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        return text.strip("-")

    written = 0
    draft_paths = []
    for poi in pois:
        name      = poi.get("name", "").strip()
        poi_type  = poi.get("type", "poi")   # "poi" or "vibe"
        category  = poi.get("category", "Landmark")
        poi_body  = poi.get("body", "").strip()
        if not name or not poi_body:
            continue
        slug = _slugify(name)
        out_path = city_dir / f"{slug}.md"
        if out_path.exists():
            draft_paths.append(f"~pois/{city_path}/{slug}")
            continue
        meta = {"title": name, "type": poi_type, "category": category}
        if poi_type == "vibe":
            if poi.get("duration_hours"):
                meta["duration_hours"] = poi["duration_hours"]
            if poi.get("stops"):
                meta["stops"] = poi["stops"]
        else:
            lat = poi.get("latitude")
            lng = poi.get("longitude")
            if lat is not None:
                meta["latitude"]  = round(float(lat), 7)
            if lng is not None:
                meta["longitude"] = round(float(lng), 7)
        post = _fm.Post(poi_body, **meta)
        out_path.write_text(_fm.dumps(post))
        draft_paths.append(f"~pois/{city_path}/{slug}")
        written += 1

    # Add draft POIs directly to the plan file if plan_slug and city_slug provided
    if plan_slug and city_slug:
        for draft_path in draft_paths:
            _plan_file_add(plan_slug, city_slug, draft_path)

    return JsonResponse({"written": written, "city_path": city_path})
