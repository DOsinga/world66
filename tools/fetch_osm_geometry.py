#!/usr/bin/env python3
"""
Fetch OSM geometry for Street, Square, and Park POIs.

For each POI with category Street/Square/Park that has lat/lng but no stored
geometry, queries the Overpass API and writes the coordinates back into the
frontmatter as a `geometry` field.

Usage:
    python3 tools/fetch_osm_geometry.py <city_path>

    e.g.  python3 tools/fetch_osm_geometry.py europe/netherlands/amsterdam

The `geometry` field is a list of [lat, lon] pairs representing the matched
OSM way (the largest one if multiple ways share the name in the bounding box).
For closed ways (parks, squares) it is a polygon; for open ways (streets) it
is a polyline.

Rate-limiting: 1 request/second to respect Overpass usage policy.
"""

import sys
import time
import urllib.parse
import urllib.request
import json
from pathlib import Path

import frontmatter

SCRIPT_DIR = Path(__file__).parent
CONTENT_DIR = SCRIPT_DIR.parent / "content"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX_DELTA = 0.04          # degrees around the POI's lat/lng to search
GEOMETRY_CATEGORIES = {"Street", "Square", "Park"}
SLEEP_BETWEEN = 1.0        # seconds between Overpass requests


def query_overpass(name: str, lat: float, lng: float) -> list[list[float]] | None:
    """Return the geometry of the best-matching OSM way, or None."""
    d = BBOX_DELTA
    bbox = f"{lat - d},{lng - d},{lat + d},{lng + d}"
    # Escape name for Overpass QL string
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    query = f'[out:json][timeout:15];way["name"="{escaped}"]({bbox});out geom;'
    url = OVERPASS_URL + "?data=" + urllib.parse.quote(query)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "world66-restore/1.0 (open content travel guide)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"    Overpass error: {exc}")
        return None

    elements = [
        el for el in data.get("elements", [])
        if el.get("type") == "way" and el.get("geometry")
    ]
    if not elements:
        return None

    # Pick the longest way (most geometry points)
    best = max(elements, key=lambda el: len(el["geometry"]))
    return [[p["lat"], p["lon"]] for p in best["geometry"]]


def process_city(city_path: str) -> None:
    content_dir = CONTENT_DIR / city_path
    if not content_dir.is_dir():
        print(f"Directory not found: {content_dir}")
        sys.exit(1)

    poi_files = list(content_dir.rglob("*.md"))
    candidates = []
    for path in poi_files:
        post = frontmatter.load(path)
        if post.get("type") != "poi":
            continue
        if post.get("category") not in GEOMETRY_CATEGORIES:
            continue
        lat = post.get("latitude")
        lng = post.get("longitude")
        if lat is None or lng is None:
            continue
        if post.get("geometry"):
            continue  # already done
        candidates.append((path, post, float(lat), float(lng)))

    print(f"Found {len(candidates)} POIs needing geometry in {city_path}")

    for path, post, lat, lng in candidates:
        name = post.get("title", path.stem)
        print(f"  Fetching: {name} ({lat}, {lng}) ...", end=" ", flush=True)
        geometry = query_overpass(name, lat, lng)
        time.sleep(SLEEP_BETWEEN)

        if geometry is None:
            print("no match")
            continue

        post["geometry"] = geometry
        with open(path, "wb") as f:
            frontmatter.dump(post, f)
        print(f"saved ({len(geometry)} points)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    process_city(sys.argv[1])
