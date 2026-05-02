"""
TimeSpace — event and venue loading from the filesystem.

Events live in spacetime_app/events/*.md with frontmatter:

    ---
    title: Late Night at Miniatur Wunderland
    poi: europe/germany/hamburg/miniatur_wunderland
    date: 2026-05-15
    time_start: "19:00"
    time_end: "23:00"          # optional
    category: museum           # concert | market | festival | exhibition | food | sport | museum | other
    url: https://...           # optional
    ---
    Optional extra description.

The `poi` field is a W66 content path. Coordinates, name, image, and snippet
are loaded from world66_content at render time.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import frontmatter
from django.conf import settings

from world66_content.models import load_page

# ── Constants ────────────────────────────────────────────────────────────────

# POI tags that indicate a likely event venue
VENUE_TAGS = {
    "concert", "music", "theatre", "theater", "museum", "gallery",
    "market", "festival", "park", "stadium", "cinema", "nightlife",
    "bar", "restaurant", "club",
}


def _events_dir() -> Path:
    base = getattr(settings, "SPACETIME_EVENTS_DIR", None)
    if base:
        return Path(base)
    return Path(settings.BASE_DIR) / "spacetime_app" / "events"


def _pois_dir() -> Path:
    return Path(settings.BASE_DIR) / "spacetime_app" / "pois"


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class Venue:
    """A W66 POI used as an event venue."""
    path: str            # e.g. europe/germany/hamburg/miniatur_wunderland
    title: str
    lat: float
    lng: float
    snippet: str = ""
    image: str = ""
    image_url: str = ""
    tags: list = field(default_factory=list)


@dataclass
class Event:
    slug: str
    title: str
    poi_path: str        # W66 content path
    date: date
    time_start: str = ""
    time_end: str = ""
    category: str = "other"
    url: str = ""
    description: str = ""
    venue: Optional[Venue] = None

    @property
    def datetime_start(self) -> Optional[datetime]:
        if self.time_start:
            try:
                return datetime.combine(self.date, datetime.strptime(self.time_start, "%H:%M").time())
            except ValueError:
                pass
        return None

    @property
    def is_past(self) -> bool:
        return self.date < date.today()

    @property
    def is_today(self) -> bool:
        return self.date == date.today()


# ── Loaders ──────────────────────────────────────────────────────────────────

def load_venue(poi_path: str) -> Optional[Venue]:
    """
    Load a venue by path. Checks in order:
    1. Shadow POI (spacetime/<slug>) — path starts with 'spacetime/'
    2. W66 content tree
    Returns None if not found or no coordinates.
    """
    if poi_path.startswith("spacetime/"):
        return _load_shadow_venue(poi_path)
    return _load_w66_venue(poi_path)


def _load_shadow_venue(poi_path: str) -> Optional[Venue]:
    """Load a venue from the spacetime shadow POI list."""
    slug = poi_path.removeprefix("spacetime/")
    path = _pois_dir() / f"{slug}.md"
    if not path.exists():
        return None
    try:
        post = frontmatter.load(str(path))
    except Exception:
        return None

    # If this shadow POI has been claimed by W66, redirect transparently
    w66_path = post.get("w66_path")
    if w66_path:
        return _load_w66_venue(w66_path)

    lat = post.get("latitude") or post.get("lat")
    lng = post.get("longitude") or post.get("lng")
    if lat is None or lng is None:
        return None

    return Venue(
        path=poi_path,
        title=post.get("title", slug),
        lat=float(lat),
        lng=float(lng),
        snippet=post.get("snippet", ""),
        tags=post.get("tags", []) or [],
    )


def _load_w66_venue(poi_path: str) -> Optional[Venue]:
    """Load a venue from the W66 content tree."""
    try:
        page = load_page(poi_path)
    except Exception:
        return None
    if page is None:
        return None
    lat = page.meta.get("latitude") or page.meta.get("lat")
    lng = page.meta.get("longitude") or page.meta.get("lng")
    if lat is None or lng is None:
        return None

    image = page.meta.get("image", "")
    image_url = ""
    if image:
        from world66_content.models import CONTENT_DIR
        content_path = CONTENT_DIR / poi_path
        for candidate in [content_path.parent / image, content_path / image]:
            if candidate.exists():
                rel = candidate.relative_to(CONTENT_DIR)
                image_url = f"/content-media/{rel}"
                break

    return Venue(
        path=poi_path,
        title=page.title,
        lat=float(lat),
        lng=float(lng),
        snippet=page.meta.get("snippet", ""),
        image=image,
        image_url=image_url,
        tags=page.meta.get("tags", []) or [],
    )


def load_event(path: Path) -> Optional[Event]:
    """Parse a single event markdown file."""
    try:
        post = frontmatter.load(str(path))
    except Exception:
        return None

    slug = path.stem
    title = post.get("title", slug)
    poi_path = post.get("poi", "")
    raw_date = post.get("date")

    if not poi_path or not raw_date:
        return None

    if isinstance(raw_date, str):
        try:
            raw_date = date.fromisoformat(raw_date)
        except ValueError:
            return None

    event = Event(
        slug=slug,
        title=title,
        poi_path=poi_path,
        date=raw_date,
        time_start=str(post.get("time_start", "")),
        time_end=str(post.get("time_end", "")),
        category=post.get("category", "other"),
        url=post.get("url", ""),
        description=post.content.strip(),
    )
    event.venue = load_venue(poi_path)
    return event


def load_all_events(include_past: bool = False) -> list[Event]:
    """Load all events, sorted by date ascending. Drops events with no venue."""
    events = []
    for path in sorted(_events_dir().glob("*.md")):
        event = load_event(path)
        if event is None or event.venue is None:
            continue
        if not include_past and event.is_past:
            continue
        events.append(event)
    events.sort(key=lambda e: e.date)
    return events


# ── Geo helpers ──────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def nearby_events(events: list[Event], lat: float, lng: float, radius_km: float = 25) -> list[Event]:
    return [e for e in events if e.venue and haversine_km(lat, lng, e.venue.lat, e.venue.lng) <= radius_km]


def nearby_venue_pois(lat: float, lng: float, radius_km: float = 25) -> list[Venue]:
    """
    Scan the W66 content tree for POIs near the given point that have
    venue-like tags. Used to populate the map when there are no events.
    """
    from world66_content.models import CONTENT_DIR
    venues = []
    for md in CONTENT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(str(md))
        except Exception:
            continue
        if post.get("type") != "poi":
            continue
        poi_lat = post.get("latitude") or post.get("lat")
        poi_lng = post.get("longitude") or post.get("lng")
        if poi_lat is None or poi_lng is None:
            continue
        tags = set(post.get("tags") or [])
        if not tags & VENUE_TAGS:
            continue
        if haversine_km(lat, lng, float(poi_lat), float(poi_lng)) > radius_km:
            continue
        path = str(md.relative_to(CONTENT_DIR).with_suffix(""))
        venues.append(Venue(
            path=path,
            title=post.get("title", path),
            lat=float(poi_lat),
            lng=float(poi_lng),
            snippet=post.get("snippet", ""),
            tags=list(tags),
        ))
    return venues
