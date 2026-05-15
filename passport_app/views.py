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

PASSPORT_DIR = Path(settings.BASE_DIR) / "passports"
PASSWORDS_FILE = PASSPORT_DIR / ".passwords.json"
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


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
            return redirect(f"/passport/{slug}/protect/")
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
        return redirect(f"/passport/{data['slug']}/protect/")
    return render(request, "passport/new.html")


def passport_protect(request, slug):
    """Set the passphrase for a new passport (first-time signup)."""
    if not _passport_path(slug).is_file():
        raise Http404
    passwords = _load_passwords()
    if slug in passwords:
        return redirect(f"/passport/{slug}/login/")
    error = None
    if request.method == "POST":
        phrase = request.POST.get("phrase", "").strip()
        if len(phrase) < 4:
            error = "Your passphrase needs to be at least 4 characters."
        else:
            _save_password(slug, phrase)
            _mark_authenticated(request, slug)
            passport = _load_passport(slug)
            return redirect(f"/passport/{slug}/experiences/")
    passport = _load_passport(slug)
    return render(request, "passport/protect.html", {"passport": passport, "error": error})


def passport_login(request, slug):
    if not _passport_path(slug).is_file():
        raise Http404
    passwords = _load_passwords()
    if slug not in passwords:
        return redirect(f"/passport/{slug}/protect/")
    next_url = request.GET.get("next", f"/passport/{slug}/")
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
            return redirect(f"/passport/{slug}/photos/")
    return render(request, "passport/experiences.html", {"passport": passport, "error": error})


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
            filename = f"photo_{len(saved) + 1}{ext}"
            dest = photos_dir / filename
            with open(dest, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)
            saved.append(filename)
            if len(saved) >= 3:
                break

        if not error:
            passport["photos"] = saved[:3]
            passport["step"] = max(passport.get("step", 0), 2)
            _save_passport(passport)
            return redirect(f"/passport/{slug}/scenarios/")

    return render(request, "passport/photos.html", {
        "passport": passport,
        "photo_urls": [f"/passport/{slug}/photo/{p}" for p in passport.get("photos", [])],
        "error": error,
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
        passport["step"] = max(passport.get("step", 0), 3)
        _save_passport(passport)
        return redirect(f"/passport/{slug}/")

    # Pick 5 random scenarios if not yet assigned
    if not passport.get("scenario_ids"):
        chosen = pick_scenarios(5)
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

    return render(request, "passport/detail.html", {
        "passport": passport,
        "photo_urls": photo_urls,
        "scenario_data": scenario_data,
        "step": passport.get("step", 0),
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
