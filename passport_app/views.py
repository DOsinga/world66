import hashlib
import json
import mimetypes
import re
import secrets
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .scenarios import pick_scenarios
from .wordlist import generate_passphrase

PASSPORT_DIR = Path(settings.BASE_DIR) / "passports"
PASSWORDS_FILE = PASSPORT_DIR / ".passwords.json"
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}


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
        "experiences": [],
        "photos": [],
        "scenario_ids": [],
        "scenario_responses": {},
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
        return redirect(f"/passport/{slug}/experiences")

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


@_require_auth
def passport_experiences(request, slug):
    passport = _load_passport(slug)
    if not passport:
        raise Http404
    error = None
    if request.method == "POST":
        experiences = []
        for i in range(1, 4):
            title = request.POST.get(f"title_{i}", "").strip()
            description = request.POST.get(f"description_{i}", "").strip()
            if title:
                experiences.append({"title": title, "description": description})
        if len(experiences) < 1:
            error = "Please describe at least one travel experience."
        else:
            passport["experiences"] = experiences
            passport["step"] = max(passport.get("step", 0), 1)
            _save_passport(passport)
            return redirect(f"/passport/{slug}/photos")
    return render(request, "passport/experiences.html", {"passport": passport, "error": error})


def _fuzzy_match_place(query: str) -> dict | None:
    """Find best World66 page for query using the FTS search index. Returns {title, url} or None."""
    import sqlite3
    q = query.strip()
    if len(q) < 2:
        return None
    search_db = Path(settings.BASE_DIR) / "search.db"
    if not search_db.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{search_db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        words = q.split()
        parts = ['"' + w.replace('"', '""') + '"' for w in words[:-1]]
        parts.append('"' + words[-1].replace('"', '""') + '"*')
        fts_query = " ".join(parts)
        row = conn.execute(
            """SELECT title, url_path FROM docs WHERE docs MATCH ?
               ORDER BY CASE WHEN lower(title) = lower(?) THEN 0
                              WHEN lower(title) LIKE (lower(?) || '%') THEN 1
                              ELSE 2 END, rank LIMIT 1""",
            (fts_query, q, q),
        ).fetchone()
        conn.close()
        if row:
            return {"title": row["title"], "url": "/" + row["url_path"]}
    except Exception:
        pass
    return None


def _save_image(upload, dest: Path) -> None:
    """Convert any uploaded image (including HEIC) to JPEG and save to dest."""
    import pillow_heif
    import PIL.Image
    pillow_heif.register_heif_opener()
    img = PIL.Image.open(upload)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.save(dest, "JPEG", quality=88, optimize=True)


@_require_auth
def passport_photos(request, slug):
    passport = _load_passport(slug)
    if not passport:
        raise Http404
    error = None
    if request.method == "POST":
        photos_dir = PASSPORT_DIR / slug / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        saved = list(passport.get("photos", []))

        for i in range(1, 4):
            f = request.FILES.get(f"photo_{i}")
            if not f:
                continue
            ext = Path(f.name).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTS:
                error = f"Unsupported file type: {ext}"
                break
            filename = f"photo_{len(saved) + 1}.jpg"
            dest = photos_dir / filename
            try:
                _save_image(f, dest)
            except Exception as exc:
                error = f"Could not process image: {exc}"
                break
            saved.append(filename)
            if len(saved) >= 3:
                break

        if not error:
            passport["photos"] = saved[:3]
            passport["step"] = max(passport.get("step", 0), 2)
            _save_passport(passport)
            return redirect(f"/passport/{slug}/places")

    return render(request, "passport/photos.html", {
        "passport": passport,
        "photo_urls": [f"/passport/{slug}/photo/{p}" for p in passport.get("photos", [])],
        "error": error,
    })


@_require_auth
def passport_places(request, slug):
    passport = _load_passport(slug)
    if not passport:
        raise Http404

    if request.method == "POST":
        place_types = ["bar", "sight", "restaurant"]
        places = []
        for t in place_types:
            query = request.POST.get(f"place_{t}", "").strip()
            if query:
                match = _fuzzy_match_place(query)
                places.append({"type": t, "query": query, "match": match})
        passport["places"] = places
        passport["step"] = max(passport.get("step", 0), 3)
        _save_passport(passport)
        return redirect(f"/passport/{slug}/scenarios")

    existing = {p["type"]: p["query"] for p in passport.get("places", [])}
    return render(request, "passport/places.html", {
        "passport": passport,
        "existing": existing,
    })


@_require_auth
def passport_scenarios(request, slug):
    passport = _load_passport(slug)
    if not passport:
        raise Http404

    if request.method == "POST":
        raw = request.POST.get("responses", "")
        try:
            responses = json.loads(raw)
        except (ValueError, TypeError):
            responses = {}
        passport["scenario_responses"] = responses
        passport["step"] = max(passport.get("step", 0), 4)
        _save_passport(passport)
        return redirect(f"/passport/{slug}")

    # Redo: discard existing scenarios and pick a fresh random set
    if request.GET.get("redo"):
        passport["scenario_ids"] = []
        passport["scenario_responses"] = {}
        _save_passport(passport)
        return redirect(f"/passport/{slug}/scenarios")

    # Pick 3 random scenarios if not yet assigned
    if not passport.get("scenario_ids"):
        chosen = pick_scenarios(3)
        passport["scenario_ids"] = [s["id"] for s in chosen]
        _save_passport(passport)

    from .scenarios import SCENARIOS
    scenario_map = {s["id"]: s for s in SCENARIOS}
    scenarios = [scenario_map[sid] for sid in passport["scenario_ids"] if sid in scenario_map]

    return render(request, "passport/scenarios.html", {
        "passport": passport,
        "scenarios_json": json.dumps(scenarios),
        "existing_responses": json.dumps(passport.get("scenario_responses", {})),
    })


def _traveler_summary(scenario_data: list) -> dict:
    """Score selected options across categories and return archetype label + emoji."""
    scores = {
        "culture":   0,
        "nightlife": 0,
        "food":      0,
        "adventure": 0,
        "urban":     0,
        "nature":    0,
        "luxury":    0,
        "budget":    0,
    }
    culture_kw   = {"museum", "gallery", "gallery", "art", "cathedral", "palace", "monastery",
                    "tomb", "ruins", "archaeological", "concert", "opera", "theatre", "exhibition",
                    "library", "basilica", "chapel", "fortress", "castle"}
    nightlife_kw = {"bar", "club", "cocktail", "beer", "pub", "wine", "gin", "sake", "mezcal",
                    "speakeasy", "karaoke", "jazz", "music", "ruin bar", "nightlife", "late-night",
                    "tasting", "brewery", "tavern"}
    food_kw      = {"market", "food", "restaurant", "eat", "lunch", "breakfast", "dinner",
                    "cooking", "street food", "bakery", "café", "cafe", "sushi", "ramen",
                    "taco", "pizza", "gelato", "brunch", "bbq", "barbecue", "bun", "dumpling"}
    adventure_kw = {"hike", "surf", "kayak", "climb", "trek", "bike", "cycling", "bungee",
                    "skydiving", "rafting", "snorkel", "dive", "mountain", "volcano", "safari"}
    urban_kw     = {"neighbourhood", "neighborhood", "street", "wander", "walk", "quarter",
                    "district", "alley", "mural", "graffiti", "flea market", "vintage", "canal"}
    nature_kw    = {"beach", "island", "park", "garden", "forest", "waterfall", "lake",
                    "hot spring", "geyser", "glacier", "reef", "bay", "coast", "botanical"}
    luxury_kw    = {"private", "michelin", "chef", "butler", "yacht", "helicopter", "villa",
                    "splurge", "luxury", "first class", "vip", "exclusive"}
    budget_kw    = {"free", "€20", "cheap", "picnic", "tip-based", "hostel", "no plan"}

    def kw_match(text: str, kws: set) -> bool:
        t = text.lower()
        return any(k in t for k in kws)

    sid_type = {
        "luxury_splurge": "luxury", "private_tour": "luxury",
        "beer_and_cocktails": "nightlife", "nightlife_types": "nightlife",
        "food_extreme": "food", "shopping_styles": "urban",
        "budget_day": "budget", "super_touristy": "urban",
    }

    for item in scenario_data:
        sid = item["scenario"]["id"]
        base = sid_type.get(sid)
        for opt in item["selected"]:
            name = opt["name"]
            if base:
                scores[base] += 2
            if kw_match(name, culture_kw):   scores["culture"]   += 1
            if kw_match(name, nightlife_kw): scores["nightlife"] += 1
            if kw_match(name, food_kw):      scores["food"]      += 1
            if kw_match(name, adventure_kw): scores["adventure"] += 1
            if kw_match(name, urban_kw):     scores["urban"]     += 1
            if kw_match(name, nature_kw):    scores["nature"]    += 1
            if kw_match(name, luxury_kw):    scores["luxury"]    += 1
            if kw_match(name, budget_kw):    scores["budget"]    += 1

    labels = {
        "culture":   ("Culture Vulture",    "🎨"),
        "nightlife": ("Night Owl",           "🌙"),
        "food":      ("Foodie",              "🍜"),
        "adventure": ("Adventure Seeker",    "🧗"),
        "urban":     ("Urban Explorer",      "🏙️"),
        "nature":    ("Nature Lover",        "🌿"),
        "luxury":    ("Luxury Traveller",    "💎"),
        "budget":    ("Resourceful Roamer",  "🎒"),
    }

    # Archetype → (content image path, city name)
    archetype_images = {
        "culture":   ("europe/italy/tuscany/florence.jpg",       "Florence"),
        "nightlife": ("europe/germany/berlin.jpg",               "Berlin"),
        "food":      ("asia/japan/tokyo.jpg",                    "Tokyo"),
        "adventure": ("africa/southafrica/capetown.jpg",         "Cape Town"),
        "urban":     ("europe/unitedkingdom/england/london.jpg", "London"),
        "nature":    ("europe/iceland/reykjavik.jpg",            "Reykjavik"),
        "luxury":    ("europe/france/paris.jpg",                 "Paris"),
        "budget":    ("asia/thailand/bangkok.jpg",               "Bangkok"),
    }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = ranked[0] if ranked[0][1] > 0 else ("urban", 0)
    second = next((r for r in ranked[1:] if r[1] > 0 and r[0] != top[0]), None)

    label, emoji = labels[top[0]]
    if second:
        label2, emoji2 = labels[second[0]]
        combo = f"{emoji} {label} · {emoji2} {label2}"
    else:
        combo = f"{emoji} {label}"

    img_path, img_city = archetype_images.get(top[0], ("europe/france/paris.jpg", "Paris"))

    return {
        "label": label, "emoji": emoji, "combo": combo, "scores": scores,
        "cover_image_url": f"/content-image/{img_path}",
        "cover_image_city": img_city,
    }


@_require_auth
def passport_detail(request, slug):
    passport = _load_passport(slug)
    if not passport:
        raise Http404

    from .scenarios import SCENARIOS
    scenario_map = {s["id"]: s for s in SCENARIOS}
    responses = passport.get("scenario_responses", {})
    scenario_data = []
    for sid in passport.get("scenario_ids", []):
        s = scenario_map.get(sid)
        if not s:
            continue
        selected_indices = responses.get(sid, [])
        selected = [s["options"][i] for i in selected_indices if i < len(s["options"])]
        scenario_data.append({"scenario": s, "selected": selected})

    photo_urls = [f"/passport/{slug}/photo/{p}" for p in passport.get("photos", [])]
    summary = _traveler_summary(scenario_data) if scenario_data else None

    return render(request, "passport/detail.html", {
        "passport": passport,
        "photo_urls": photo_urls,
        "scenario_data": scenario_data,
        "summary": summary,
        "step": passport.get("step", 0),
        "places": passport.get("places", []),
    })


def passport_photo(request, slug, filename):
    """Serve a passport photo — requires authentication."""
    # Prevent directory traversal
    if ".." in filename or "/" in filename:
        raise Http404
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise Http404
    passwords = _load_passwords()
    if slug not in passwords or not _passport_authenticated(request, slug):
        raise Http404
    file_path = PASSPORT_DIR / slug / "photos" / filename
    if not file_path.is_file():
        raise Http404
    content_type = mimetypes.types_map.get(ext, "application/octet-stream")
    return FileResponse(open(file_path, "rb"), content_type=content_type)
