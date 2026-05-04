from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

import frontmatter
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from guide.models import CONTENT_DIR, load_page

BASE_DIR = Path(settings.BASE_DIR)
PLANS_DIR = BASE_DIR / "plans"
PLANS_DIR.mkdir(exist_ok=True)

_PASSWORDS_FILE = BASE_DIR / ".passwords.json"
_GEOCACHE_FILE = BASE_DIR / ".geocache.json"
_SEARCH_DB = BASE_DIR / "search.db"

# ---------------------------------------------------------------------------
# Passphrase wordlist (BIP-39 style short list, easy to type/read)
# ---------------------------------------------------------------------------
_WORDS = [
    "amber","apple","arrow","atlas","azure","badge","berry","birch","blade",
    "bloom","blaze","brave","brick","brook","brush","cabin","candy","cargo",
    "cedar","chalk","charm","chess","chief","chord","cider","civic","claim",
    "cloak","cloud","clover","coast","cobra","coral","crane","creek","crest",
    "crisp","cross","crown","crush","curve","daisy","dance","delta","depot",
    "derby","diver","dome","draft","drake","drift","drive","drone","dunes",
    "eagle","earthy","ebony","ember","envoy","epoch","fable","fargo","feast",
    "ferry","field","finch","fjord","flare","flash","fleet","flint","flora",
    "flume","flute","folio","forge","forum","frost","gable","gecko","geyser",
    "ghost","glade","glare","glass","glide","globe","glyph","gnome","grail",
    "grain","grand","grape","gravel","grove","guide","guild","gusto","haven",
    "hawke","hazel","heath","hedge","heron","hinge","holly","homer","honor",
    "hornet","hover","humid","husky","hydra","hyena","igloo","inlet","ionic",
    "ivory","jaguar","jasper","jetty","jewel","joust","jumbo","kayak","kelp",
    "knoll","koala","kraken","lance","larch","laser","latch","layer","leafy",
    "ledge","lemon","level","light","lilac","linen","lingo","llama","lodge",
    "lofty","lotus","lupin","lustre","lynch","lyric","maple","march","marsh",
    "marvel","mason","meadow","merlin","metro","mimic","mirth","mocha","model",
    "moose","mossy","motif","mound","mount","murky","myrrh","nexus","noble",
    "nomad","north","notch","nymph","oakum","oasis","ocean","ochre","olive",
    "onset","opal","orbit","otter","outpost","oxide","oyster","panda","panel",
    "paper","patch","pearl","pebble","perch","pilot","pinch","pixel","plaid",
    "plain","plume","plunge","polar","poppy","portal","prism","prone","proof",
    "proud","prune","pulse","punch","pygmy","quail","quartz","quest","queue",
    "quill","quota","rabbi","raven","razor","realm","redux","regal","relay",
    "renew","resin","ridge","rivet","robin","rocky","rogue","roman","roost",
    "rover","rowdy","royal","ruddy","runic","rustic","sable","salvo","sandy",
    "sapphire","savvy","scout","scribe","sepal","serif","shale","shark","shelf",
    "shell","shift","shore","shrub","sigma","silex","silky","skiff","skimp",
    "slate","sleet","slick","slope","smelt","snowy","solar","solid","sonar",
    "sonic","spark","spawn","speck","spell","spire","spore","spray","squad",
    "squall","stark","stave","steel","steep","stern","stoic","stoke","stony",
    "storm","strap","straw","strip","strum","strut","stump","suede","suite",
    "sulky","sunlit","supple","surge","swamp","swath","sweet","swept","swift",
    "sword","synth","talon","tansy","taupe","tempo","tepid","terra","thatch",
    "thicket","thorn","tiger","tilde","tinge","titan","token","topaz","torch",
    "totem","trace","trail","tramp","trench","trend","tribe","trill","trout",
    "trove","truce","trunk","tuber","tulip","tundra","tweed","twine","ultra",
    "umbra","unity","urban","usher","valve","vapor","vault","veldt","verge",
    "visor","vixen","vocal","vogue","void","vortex","vulture","walnut","walrus",
    "warden","weave","wedge","wheat","wheel","whirl","wicker","wilder","wimble",
    "woven","wrath","xenon","yacht","yarrow","zebra","zenith","zephyr","zinc",
]


def _generate_passphrase(n=3) -> str:
    return "-".join(secrets.choice(_WORDS) for _ in range(n))


def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _load_passwords() -> dict:
    if _PASSWORDS_FILE.exists():
        return json.loads(_PASSWORDS_FILE.read_text())
    return {}


def _save_password(slug: str, pw_hash: str) -> None:
    data = _load_passwords()
    data[slug] = pw_hash
    _PASSWORDS_FILE.write_text(json.dumps(data, indent=2))


def _check_password(slug: str, pw: str) -> bool:
    data = _load_passwords()
    return data.get(slug) == _hash_password(pw)


# ---------------------------------------------------------------------------
# Session-based auth per plan
# ---------------------------------------------------------------------------

def _plan_authenticated(request, slug: str) -> bool:
    return request.session.get(f"plan_auth_{slug}") is True


def _mark_plan_authenticated(request, slug: str) -> None:
    request.session[f"plan_auth_{slug}"] = True


def _require_plan_auth(view_func):
    @wraps(view_func)
    def wrapper(request, slug, *args, **kwargs):
        if not _plan_authenticated(request, slug):
            return HttpResponseRedirect(f"/plans/join/?next=/plans/{slug}/")
        return view_func(request, slug, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Plan file helpers
# ---------------------------------------------------------------------------

def _plan_file(slug: str) -> Path:
    return PLANS_DIR / f"{slug}.md"


def _load_plan(slug: str) -> frontmatter.Post | None:
    f = _plan_file(slug)
    if not f.exists():
        return None
    return frontmatter.load(str(f))


def _save_plan(slug: str, post: frontmatter.Post) -> None:
    _plan_file(slug).write_text(frontmatter.dumps(post))


def _plan_title(post: frontmatter.Post) -> str:
    return post.metadata.get("title", "Untitled Plan")


def _normalize(text: str) -> str:
    """Slug-safe: lowercase, spaces→hyphens, remove non-alphanum."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)


# ---------------------------------------------------------------------------
# Geocoding helpers
# ---------------------------------------------------------------------------

def _load_geocache() -> dict:
    if _GEOCACHE_FILE.exists():
        return json.loads(_GEOCACHE_FILE.read_text())
    return {}


def _save_geocache(cache: dict) -> None:
    _GEOCACHE_FILE.write_text(json.dumps(cache, indent=2))


def _geocode_nominatim(query: str) -> tuple[float, float] | None:
    import urllib.request, urllib.parse
    cache = _load_geocache()
    if query in cache:
        return tuple(cache[query])
    url = (
        "https://nominatim.openstreetmap.org/search?"
        + urllib.parse.urlencode({"q": query, "format": "json", "limit": "1"})
    )
    req = urllib.request.Request(url, headers={"User-Agent": "world66-plans/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            results = json.load(r)
        if results:
            lat, lng = float(results[0]["lat"]), float(results[0]["lon"])
            cache[query] = [lat, lng]
            _save_geocache(cache)
            return lat, lng
    except Exception:
        pass
    return None


def _city_coords(city_path: str) -> tuple[float, float] | None:
    page = load_page(city_path)
    if page and page.latitude and page.longitude:
        return page.latitude, page.longitude
    return None


# ---------------------------------------------------------------------------
# Parse plan markdown into structured stops
# ---------------------------------------------------------------------------

def _parse_stops(section_body: str, city_path: str) -> list[dict]:
    stops = []
    for line in section_body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            item = line[2:].strip()
            if item.startswith("http"):
                stops.append({"type": "url", "url": item, "title": item})
            elif "/" in item:
                page = load_page(item)
                stops.append({
                    "type": "poi",
                    "path": item,
                    "title": page.title if page else item.split("/")[-1].replace("_", " ").title(),
                    "page": page,
                })
            else:
                stops.append({"type": "note", "text": item})
    return stops


def _parse_plan(post: frontmatter.Post) -> list[dict]:
    """Parse plan body into city sections."""
    sections = []
    current = None
    body = post.content

    for line in body.splitlines():
        if line.startswith("## "):
            if current:
                sections.append(current)
            # Parse "## City | Date range" or "## City | Date"
            header = line[3:].strip()
            parts = [p.strip() for p in header.split("|")]
            city_name = parts[0]
            date_range = parts[1] if len(parts) > 1 else ""
            current = {
                "city_name": city_name,
                "date_range": date_range,
                "lines": [],
                "path": None,
            }
        elif current is not None:
            current["lines"].append(line)

    if current:
        sections.append(current)

    # Resolve city paths and parse stops
    for section in sections:
        body_text = "\n".join(section["lines"])
        # Try to find the city path from content lines
        for line in section["lines"]:
            line = line.strip()
            if line.startswith("- ") and "/" in line and not line[2:].startswith("http"):
                candidate_path = line[2:].strip()
                # Walk up the path to find the location
                parts = candidate_path.split("/")
                for depth in range(len(parts), 0, -1):
                    candidate = "/".join(parts[:depth])
                    page = load_page(candidate)
                    if page and page.page_type == "location":
                        section["path"] = candidate
                        break
                if section["path"]:
                    break
        section["stops"] = _parse_stops(body_text, section.get("path", ""))

    return sections


def _stop_markers(sections: list[dict]) -> list[dict]:
    markers = []
    for section in sections:
        for stop in section.get("stops", []):
            if stop["type"] == "poi" and stop.get("page"):
                page = stop["page"]
                if page.latitude and page.longitude:
                    markers.append({
                        "title": page.title,
                        "lat": page.latitude,
                        "lng": page.longitude,
                        "path": stop["path"],
                    })
    return markers


def _image_path(stop: dict) -> str | None:
    if stop.get("page") and stop["page"].image_url:
        return stop["page"].image_url
    return None


# ---------------------------------------------------------------------------
# W66 search helper (resolves a free-text destination to a content path)
# ---------------------------------------------------------------------------

def _resolve_destination(query: str) -> str | None:
    """Try to resolve a destination name to a content path via the search index."""
    if not _SEARCH_DB.is_file():
        return None
    conn = sqlite3.connect(f"file:{_SEARCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        words = query.split()
        parts = ['"' + w.replace('"', '""') + '"' for w in words[:-1]]
        parts.append('"' + words[-1].replace('"', '""') + '"*')
        fts_query = " ".join(parts)
        rows = conn.execute(
            """SELECT url_path FROM docs
               WHERE docs MATCH ? AND page_type = 'location'
               ORDER BY CASE WHEN lower(title) = lower(?) THEN 0 ELSE 1 END
               LIMIT 1""",
            (fts_query, query),
        ).fetchall()
        return rows[0]["url_path"] if rows else None
    except Exception:
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# API: create plan (called by MCP server)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def api_plan_create(request):
    """
    POST /api/plans/create
    Body (JSON): {
      "destination": "Marseille",          # free text or content path
      "start_date":  "2026-07-06",
      "end_date":    "2026-07-12",
      "notes":       "..."                 # optional
    }
    Returns: {
      "url":        "https://world66.ai/plans/<slug>/",
      "slug":       "<slug>",
      "passphrase": "word-word-word",
      "city_path":  "europe/france/midi/cotedazur/marseille"  # or null
    }
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

    # Resolve destination to a content path
    city_path = None
    if "/" in destination:
        # Caller passed a content path directly
        page = load_page(destination)
        if page:
            city_path = destination
            city_title = page.title
        else:
            city_title = destination.split("/")[-1].replace("_", " ").title()
    else:
        city_path = _resolve_destination(destination)
        if city_path:
            page = load_page(city_path)
            city_title = page.title if page else destination
        else:
            city_title = destination

    # Build slug
    date_part = start_date[:7].replace("-", "-")  # YYYY-MM
    base_slug = _normalize(f"{city_title}-{date_part}")
    suffix = secrets.token_hex(3)
    slug = f"{base_slug}-{suffix}"

    # Generate passphrase
    passphrase = _generate_passphrase(3)
    _save_password(slug, _hash_password(passphrase))

    # Build date range string
    if end_date and end_date != start_date:
        # Format: "6–12 July 2026"
        try:
            from datetime import date
            s = date.fromisoformat(start_date)
            e = date.fromisoformat(end_date)
            if s.month == e.month:
                date_str = f"{s.day}–{e.day} {s.strftime('%B %Y')}"
            else:
                date_str = f"{s.strftime('%-d %B')} – {e.strftime('%-d %B %Y')}"
        except ValueError:
            date_str = f"{start_date} – {end_date}"
    else:
        try:
            from datetime import date
            s = date.fromisoformat(start_date)
            date_str = s.strftime("%-d %B %Y")
        except ValueError:
            date_str = start_date

    # Build plan markdown
    content_lines = [f"## {city_title} | {date_str}"]
    if notes:
        content_lines.append(f"- {notes}")
    if city_path:
        content_lines.append(f"- {city_path}")
    content_lines.append("")

    post = frontmatter.Post(
        content="\n".join(content_lines),
        title=f"Trip to {city_title}",
        created_by="tabbi-mcp",
    )
    _save_plan(slug, post)

    base_url = request.build_absolute_uri("/").rstrip("/")
    plan_url = f"{base_url}/plans/{slug}/"

    return JsonResponse({
        "url":        plan_url,
        "slug":       slug,
        "passphrase": passphrase,
        "city_path":  city_path,
        "city_title": city_title,
    })


# ---------------------------------------------------------------------------
# Web views
# ---------------------------------------------------------------------------

def plan_list(request):
    plans = []
    for f in sorted(PLANS_DIR.glob("*.md")):
        post = frontmatter.load(str(f))
        plans.append({"slug": f.stem, "title": _plan_title(post)})
    return render(request, "plans/plan_list.html", {"plans": plans})


def plan_new(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            return render(request, "plans/plan_new.html", {"error": "Title is required"})

        slug = _normalize(title) + "-" + secrets.token_hex(3)
        passphrase = _generate_passphrase(3)
        _save_password(slug, _hash_password(passphrase))

        post = frontmatter.Post(content="", title=title)
        _save_plan(slug, post)
        _mark_plan_authenticated(request, slug)

        return HttpResponseRedirect(f"/plans/{slug}/created/")
    return render(request, "plans/plan_new.html")


def plan_join(request):
    next_url = request.GET.get("next", "/plans/")
    if request.method == "POST":
        slug = request.POST.get("slug", "").strip()
        pw   = request.POST.get("passphrase", "").strip()
        if _check_password(slug, pw):
            _mark_plan_authenticated(request, slug)
            return HttpResponseRedirect(next_url or f"/plans/{slug}/")
        return render(request, "plans/plan_join.html", {
            "error": "Wrong plan ID or passphrase.",
            "next": next_url,
        })
    return render(request, "plans/plan_join.html", {"next": next_url})


def plan_created(request, slug):
    post = _load_plan(slug)
    if not post:
        raise Http404
    passwords = _load_passwords()
    # We can't recover the passphrase (hashed) — show slug only, passphrase shown once
    return render(request, "plans/plan_created.html", {
        "slug": slug,
        "title": _plan_title(post),
        "plan_url": request.build_absolute_uri(f"/plans/{slug}/"),
    })


@_require_plan_auth
def plan_detail(request, slug):
    post = _load_plan(slug)
    if not post:
        raise Http404
    sections = _parse_plan(post)
    markers  = _stop_markers(sections)
    return render(request, "plans/plan_detail.html", {
        "slug":     slug,
        "title":    _plan_title(post),
        "sections": sections,
        "markers_json": mark_safe(json.dumps(markers)),
    })


@_require_plan_auth
def plan_edit(request, slug):
    post = _load_plan(slug)
    if not post:
        raise Http404
    if request.method == "POST":
        new_body = request.POST.get("body", "")
        post.content = new_body
        _save_plan(slug, post)
        return HttpResponseRedirect(f"/plans/{slug}/")
    return render(request, "plans/plan_edit.html", {
        "slug":  slug,
        "title": _plan_title(post),
        "body":  post.content,
    })


@_require_plan_auth
def plan_poi_add(request, slug, city_slug=None):
    post = _load_plan(slug)
    if not post:
        raise Http404
    poi_path = request.POST.get("path", "").strip()
    if poi_path:
        post.content = post.content.rstrip() + f"\n- {poi_path}\n"
        _save_plan(slug, post)
    return HttpResponseRedirect(f"/plans/{slug}/")


@_require_plan_auth
def plan_poi_remove(request, slug, city_slug):
    post = _load_plan(slug)
    if not post:
        raise Http404
    poi_path = request.POST.get("path", "").strip()
    if poi_path:
        lines = [l for l in post.content.splitlines() if l.strip() != f"- {poi_path}"]
        post.content = "\n".join(lines) + "\n"
        _save_plan(slug, post)
    return HttpResponseRedirect(f"/plans/{slug}/")


@_require_plan_auth
def plan_note_edit(request, slug, city_slug):
    post = _load_plan(slug)
    if not post:
        raise Http404
    # Simple: rewrite the entire body (sent as JSON)
    try:
        body = json.loads(request.body)
        post.content = body.get("body", post.content)
        _save_plan(slug, post)
        return JsonResponse({"ok": True})
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)


@_require_plan_auth
def plan_stop(request, slug, city_slug):
    post = _load_plan(slug)
    if not post:
        raise Http404
    sections = _parse_plan(post)
    section = next(
        (s for s in sections if _normalize(s["city_name"]) == city_slug),
        None,
    )
    if not section:
        raise Http404
    city_page = load_page(section["path"]) if section.get("path") else None
    return render(request, "plans/plan_stop.html", {
        "slug":      slug,
        "title":     _plan_title(post),
        "section":   section,
        "city_page": city_page,
    })
