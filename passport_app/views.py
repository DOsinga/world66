import hashlib
import json
import random
import secrets
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from .wordlist import generate_passphrase

PASSPORT_DIR = Path(settings.BASE_DIR) / "passports"
PASSWORDS_FILE = PASSPORT_DIR / ".passwords.json"
SEARCH_DB = Path(settings.BASE_DIR) / "search.db"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{h}"


def _check_password(password: str, stored: str) -> bool:
    parts = stored.split(":", 1)
    if len(parts) != 2:
        return False
    salt = parts[0]
    return secrets.compare_digest(_hash_password(password, salt), stored)


def _load_passwords() -> dict:
    if not PASSWORDS_FILE.is_file():
        return {}
    return json.loads(PASSWORDS_FILE.read_text())


def _save_password(slug: str, password: str) -> None:
    PASSPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = _load_passwords()
    data[slug] = _hash_password(password)
    PASSWORDS_FILE.write_text(json.dumps(data))


def _passport_authenticated(request, slug: str) -> bool:
    return slug in request.session.get("authenticated_passports", [])


def _mark_authenticated(request, slug: str) -> None:
    current = list(request.session.get("authenticated_passports", []))
    if slug not in current:
        current.append(slug)
        request.session["authenticated_passports"] = current


def _require_auth(view_fn):
    @wraps(view_fn)
    def wrapper(request, slug, *args, **kwargs):
        passwords = _load_passwords()
        if slug not in passwords:
            return redirect(f"/passport/{slug}/protect")
        if not _passport_authenticated(request, slug):
            return redirect(f"/passport/{slug}/login/?next={request.path}")
        return view_fn(request, slug, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Passport data helpers
# ---------------------------------------------------------------------------

def _passport_path(slug: str) -> Path:
    return PASSPORT_DIR / slug / "passport.json"


def _load_passport(slug: str) -> dict | None:
    path = _passport_path(slug)
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _save_passport(data: dict) -> None:
    slug = data["slug"]
    path = _passport_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _new_passport(title: str) -> dict:
    slug = secrets.token_hex(5)
    return {
        "slug": slug,
        "title": title or "My Travel Passport",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "step": 0,
        "liked_pois": [],
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def passport_list(request):
    known_slugs = request.session.get("authenticated_passports", [])
    passports = []
    for slug in known_slugs:
        data = _load_passport(slug)
        if data:
            passports.append(data)
    return render(request, "passport/list.html", {"passports": passports})


def passport_new(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        data = _new_passport(title)
        _save_passport(data)
        return redirect(f"/passport/{data['slug']}/protect")
    return render(request, "passport/new.html")


def passport_protect(request, slug):
    """Generate and confirm a passphrase for a new passport."""
    if not _passport_path(slug).is_file():
        raise Http404
    passwords = _load_passwords()
    if slug in passwords:
        return redirect(f"/passport/{slug}/login")

    session_key = f"passport_phrase_{slug}"

    if request.method == "POST":
        phrase = request.session.get(session_key, "")
        if not phrase:
            # Session expired — regenerate
            return redirect(f"/passport/{slug}/protect")
        _save_password(slug, phrase)
        del request.session[session_key]
        _mark_authenticated(request, slug)
        return redirect(f"/passport/{slug}/swipe")

    # GET — generate a fresh phrase and store it in the session
    phrase = generate_passphrase(4)
    request.session[session_key] = phrase
    passport = _load_passport(slug)
    return render(request, "passport/protect.html", {
        "passport": passport,
        "phrase": phrase,
    })


def passport_login(request, slug):
    if not _passport_path(slug).is_file():
        raise Http404
    passwords = _load_passwords()
    if slug not in passwords:
        return redirect(f"/passport/{slug}/protect")
    next_url = request.GET.get("next", f"/passport/{slug}")
    error = None
    if request.method == "POST":
        next_url = request.POST.get("next", next_url)
        phrase = request.POST.get("phrase", "")
        if _check_password(phrase, passwords[slug]):
            _mark_authenticated(request, slug)
            return redirect(next_url)
        error = "Wrong passphrase."
    passport = _load_passport(slug)
    return render(request, "passport/login.html", {
        "passport": passport,
        "error": error,
        "next": next_url,
    })


def _load_swipe_pois(n: int = 40) -> list[dict]:
    """Return a diverse set of POIs with city images from the search index."""
    if not SEARCH_DB.is_file():
        return []
    try:
        conn = sqlite3.connect(f"file:{SEARCH_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        # Pull a broad sample of indexed POIs with real content
        rows = conn.execute(
            """SELECT url_path, title, body
               FROM docs
               WHERE page_type = 'poi' AND length(body) > 80
               ORDER BY RANDOM()
               LIMIT 800"""
        ).fetchall()

        # Compute parent city path for each POI
        pois = []
        parent_paths = set()
        for row in rows:
            parts = row["url_path"].split("/")
            if len(parts) < 2:
                continue
            parent = "/".join(parts[:-1])
            snippet = (row["body"] or "").strip()
            # Keep first sentence as snippet
            end = snippet.find(". ")
            if end > 0:
                snippet = snippet[: end + 1]
            snippet = snippet[:180]
            pois.append({
                "url_path": row["url_path"],
                "title": row["title"],
                "snippet": snippet,
                "parent_path": parent,
            })
            parent_paths.add(parent)

        # Batch-fetch city images for all parent paths
        parent_list = list(parent_paths)
        geo_map = {}
        for i in range(0, len(parent_list), 500):
            chunk = parent_list[i : i + 500]
            ph = ",".join("?" for _ in chunk)
            for geo_row in conn.execute(
                f"SELECT url_path, title, image FROM geo WHERE url_path IN ({ph}) AND image != ''",
                chunk,
            ):
                geo_map[geo_row["url_path"]] = dict(geo_row)

        conn.close()
    except Exception:
        return []

    # Keep only POIs whose parent city has an image
    good = [p for p in pois if p["parent_path"] in geo_map]

    # Geographic diversity: max 3 per parent city
    by_city: dict = defaultdict(list)
    for p in good:
        by_city[p["parent_path"]].append(p)
    selected = []
    for city_pois in by_city.values():
        random.shuffle(city_pois)
        selected.extend(city_pois[:3])
    random.shuffle(selected)

    # Enrich with image URL
    result = []
    for p in selected[:n]:
        geo = geo_map[p["parent_path"]]
        city_path = geo["url_path"]
        img = geo["image"]
        p["city"] = geo["title"]
        p["image_url"] = f"/content-image/{city_path}/{img}"
        result.append(p)

    return result


@_require_auth
def passport_swipe(request, slug):
    passport = _load_passport(slug)
    if not passport:
        raise Http404

    if request.method == "POST":
        raw = request.POST.get("liked", "")
        try:
            liked = json.loads(raw)
        except (ValueError, TypeError):
            liked = []
        passport["liked_pois"] = liked
        passport["step"] = max(passport.get("step", 0), 1)
        _save_passport(passport)
        return redirect(f"/passport/{slug}")

    # Redo: clear existing likes and show fresh POIs
    if request.GET.get("redo"):
        passport["liked_pois"] = []
        passport["step"] = 0
        _save_passport(passport)
        return redirect(f"/passport/{slug}/swipe")

    pois = _load_swipe_pois(40)
    return render(request, "passport/swipe.html", {
        "passport": passport,
        "pois_json": json.dumps(pois),
    })


@_require_auth
def passport_detail(request, slug):
    passport = _load_passport(slug)
    if not passport:
        raise Http404

    liked_pois = passport.get("liked_pois", [])
    cover_image_url = liked_pois[0].get("image_url") if liked_pois else None

    return render(request, "passport/detail.html", {
        "passport": passport,
        "liked_pois": liked_pois,
        "cover_image_url": cover_image_url,
        "step": passport.get("step", 0),
    })
