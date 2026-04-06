#!/usr/bin/env python3
"""
Geocode World66 locations and POIs using Nominatim (OpenStreetMap).

Reads markdown files from content/, builds a query from the path hierarchy
or address field, and stores results in locations.json.

Resumable — saves progress every 100 lookups. Respects Nominatim's
1 request/second rate limit.
"""

import json
import os
import sys
import time
from pathlib import Path

import frontmatter
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

SCRIPT_DIR = Path(__file__).parent
CONTENT_DIR = SCRIPT_DIR.parent / "content"
LOCATIONS_FILE = SCRIPT_DIR / "locations.json"

SAVE_EVERY = 100

# Nominatim requires a unique user agent
geocoder = Nominatim(user_agent="world66-restore/1.0 (restoring open content travel guide)")


def load_locations():
    if LOCATIONS_FILE.exists():
        with open(LOCATIONS_FILE) as f:
            return json.load(f)
    return {}


def save_locations(locations):
    tmp = str(LOCATIONS_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(locations, f, indent=2)
    os.replace(tmp, LOCATIONS_FILE)


def load_meta(path):
    try:
        return frontmatter.load(path).metadata
    except Exception:
        return {}


def build_query(rel_path, meta):
    """Build a geocoding query from the file path and metadata."""
    page_type = meta.get("type", "location")
    address = meta.get("address", "")

    # Skip pages that aren't real places
    if "about" in rel_path.lower() or "changes" in rel_path.lower():
        return None

    # For POIs with an address, use it directly
    if address and address != "None":
        return address

    # Build query: "City, Country" — always use title + country (second path segment)
    parts = rel_path.replace(".md", "").split(os.sep)
    # parts[0] = continent, parts[1] = country, parts[2+] = region/city

    if len(parts) < 2:
        return None  # continent-level page, skip

    # Try to get the country name from its .md frontmatter
    country_slug = parts[1]
    country = country_slug.replace("_", " ").title()
    for country_md in [
        CONTENT_DIR / parts[0] / country_slug / f"{country_slug}.md",
        CONTENT_DIR / parts[0] / f"{country_slug}.md",
    ]:
        if country_md.is_file():
            cm = load_meta(country_md)
            if cm.get("title"):
                country = cm["title"]
            break

    # Use title from frontmatter for the place name
    title = meta.get("title", parts[-1].replace("_", " ").title())

    if len(parts) == 2:
        # Country-level page — just query the country name
        return title
    else:
        return f"{title}, {country}"


def geocode_query(query):
    """Geocode a query string. Returns (lat, lng) or None."""
    for attempt in range(3):
        try:
            result = geocoder.geocode(query, timeout=10)
            if result:
                return round(result.latitude, 6), round(result.longitude, 6)
            return None
        except GeocoderTimedOut:
            time.sleep(2)
        except GeocoderServiceError as e:
            print(f"    Service error: {e}")
            time.sleep(5)
    return None


def collect_pages():
    """Collect all markdown files, locations first then sections then POIs."""
    pages = []
    for root, dirs, files in os.walk(CONTENT_DIR):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            filepath = Path(root) / fname
            rel_path = os.path.relpath(filepath, CONTENT_DIR)
            meta = load_meta(filepath)
            page_type = meta.get("type", "location")
            if page_type == "section":
                continue  # sections inherit their location's coords
            pages.append((rel_path, meta, page_type))

    # Sort: locations first (they're parents), then POIs
    type_order = {"location": 0, "poi": 1}
    pages.sort(key=lambda x: (type_order.get(x[2], 9), x[0]))
    return pages


def find_parent_coords(rel_path, locations):
    """Try to find coordinates from a parent location."""
    parts = rel_path.replace(".md", "").split(os.sep)
    # Walk up the path looking for a geocoded parent
    for i in range(len(parts) - 1, 0, -1):
        parent_key = os.sep.join(parts[:i])
        # Try with .md suffix
        for key in [parent_key + ".md", parent_key + os.sep + parts[i-1] + ".md"]:
            if key in locations and locations[key].get("lat"):
                return locations[key]["lat"], locations[key]["lng"]
    return None


def run():
    locations = load_locations()
    pages = collect_pages()

    already_done = sum(1 for p in pages if p[0] in locations)
    remaining = [p for p in pages if p[0] not in locations]

    print(f"Total pages: {len(pages)}")
    print(f"Already geocoded: {already_done}")
    print(f"Remaining: {len(remaining)}")
    print()

    count = 0
    geocoded = 0
    inherited = 0
    failed = 0
    start_time = time.time()

    try:
        for rel_path, meta, page_type in remaining:
            query = build_query(rel_path, meta)

            result = None
            source = None

            if query:
                result = geocode_query(query)
                if result:
                    source = "geocoded"
                    geocoded += 1
                else:
                    failed += 1
                time.sleep(1.1)  # Nominatim rate limit
            else:
                failed += 1

            locations[rel_path] = {
                "query": query,
                "lat": result[0] if result else None,
                "lng": result[1] if result else None,
                "source": source,
                "type": page_type,
            }

            count += 1
            status = f"({result[0]:.4f}, {result[1]:.4f})" if result else "MISS"
            if count % 10 == 0 or result:
                print(f"  [{count}/{len(remaining)}] {status} {rel_path}")

            if count % SAVE_EVERY == 0:
                save_locations(locations)
                elapsed = time.time() - start_time
                rate = count / elapsed if elapsed > 0 else 0
                eta = (len(remaining) - count) / rate / 3600 if rate > 0 else 0
                print(f"  --- Saved. {geocoded} geocoded, {inherited} inherited, "
                      f"{failed} failed, ETA ~{eta:.1f}h ---")

    except KeyboardInterrupt:
        print("\nInterrupted!")

    save_locations(locations)
    print(f"\nDone! {geocoded} geocoded, {inherited} inherited, {failed} failed")


if __name__ == "__main__":
    run()
