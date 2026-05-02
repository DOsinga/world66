from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from django.conf import settings

CONTENT_DIR = Path(settings.BASE_DIR) / "content"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _route_distance(route: list) -> float:
    if len(route) < 2:
        return 0.0
    total = sum(
        _haversine(route[i][0], route[i][1], route[i + 1][0], route[i + 1][1])
        for i in range(len(route) - 1)
    )
    return round(total, 1)


def _route_svg(route: list) -> str:
    """Render the walk route as a compact SVG path for card previews."""
    if len(route) < 2:
        return ""
    lats = [p[0] for p in route]
    lngs = [p[1] for p in route]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    lat_range = max_lat - min_lat or 0.001
    lng_range = max_lng - min_lng or 0.001
    W, H = 120, 80
    pts = " ".join(
        f"{((lng - min_lng) / lng_range * W):.1f},{(H - (lat - min_lat) / lat_range * H):.1f}"
        for lat, lng in route
    )
    return (
        f'<svg viewBox="-4 -4 {W+8} {H+8}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        f'<polyline points="{pts}" stroke="currentColor" stroke-width="3" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


def _city_name(parts: list[str]) -> str:
    return parts[-1].replace("_", " ").title() if parts else ""


def _url_parts(file_path: Path) -> list[str]:
    rel = file_path.relative_to(CONTENT_DIR).with_suffix("")
    parts = list(rel.parts)
    # Collapse directory-index duplication (city/city.md → city)
    if len(parts) >= 2 and parts[-1] == parts[-2]:
        parts = parts[:-1]
    return parts


# ---------------------------------------------------------------------------
# Walk dataclass
# ---------------------------------------------------------------------------

@dataclass
class Walk:
    title: str
    path: str          # URL path, e.g. "europe/netherlands/amsterdam/jordaan_walk"
    city_name: str
    city_path: str     # URL path of the parent city
    continent: str
    latitude: float
    longitude: float
    waypoints: list    # raw slugs from frontmatter
    route: list        # list of [lat, lng]
    body: str
    image_url: str | None
    distance_km: float = 0.0
    route_svg: str = field(default="", repr=False)

    @property
    def stops(self) -> int:
        return len(self.waypoints)

    @property
    def duration_min(self) -> int:
        return int(self.distance_km / 5 * 60) if self.distance_km else 0

    @property
    def absolute_url(self) -> str:
        return f"/walks/{self.path}"

    @property
    def gpx_url(self) -> str:
        return f"/walks/{self.path}.gpx"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _load_walk(file_path: Path) -> Walk | None:
    try:
        post = frontmatter.load(str(file_path))
    except Exception:
        return None

    meta = post.metadata
    if meta.get("type") != "walk":
        return None

    parts = _url_parts(file_path)
    city_parts = parts[:-1]
    continent = parts[0] if parts else ""

    route = meta.get("route", [])
    img = meta.get("image")
    image_url = None
    if img:
        dir_rel = "/".join(str(file_path.parent.relative_to(CONTENT_DIR)).split("/"))
        image_url = f"/content-image/{dir_rel}/{img}"

    return Walk(
        title=meta.get("title", file_path.stem.replace("_", " ").title()),
        path="/".join(parts),
        city_name=_city_name(city_parts),
        city_path="/".join(city_parts),
        continent=continent,
        latitude=float(meta.get("latitude", 0) or 0),
        longitude=float(meta.get("longitude", 0) or 0),
        waypoints=meta.get("waypoints", []),
        route=route,
        body=post.content or "",
        image_url=image_url,
        distance_km=_route_distance(route),
        route_svg=_route_svg(route),
    )


def load_all_walks() -> list[Walk]:
    walks = []
    for f in sorted(CONTENT_DIR.rglob("*.md")):
        w = _load_walk(f)
        if w:
            walks.append(w)
    return walks


def load_walk(path: str) -> Walk | None:
    """Load a single walk by URL path."""
    file_path = CONTENT_DIR / (path + ".md")
    if file_path.exists():
        return _load_walk(file_path)
    # Try directory-index form: city/city.md
    parts = path.rstrip("/").split("/")
    file_path2 = CONTENT_DIR / Path(*parts) / (parts[-1] + ".md")
    if file_path2.exists():
        return _load_walk(file_path2)
    return None


def walks_by_city(walks: list[Walk]) -> list[dict]:
    """Group walks by city, sorted by walk count descending."""
    cities: dict[str, dict] = {}
    for w in walks:
        if w.city_path not in cities:
            cities[w.city_path] = {
                "name": w.city_name,
                "path": w.city_path,
                "continent": w.continent,
                "walks": [],
            }
        cities[w.city_path]["walks"].append(w)
    return sorted(cities.values(), key=lambda c: len(c["walks"]), reverse=True)
