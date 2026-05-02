#!/usr/bin/env python3
"""
Check shadow POIs against W66 content to find ones that now exist there.

For each shadow POI in spacetime_app/pois/, looks for a W66 POI within
100m with a similar title. Prints matches so an agent can delist them.

Usage:
    venv/bin/python spacetime_app/todo/check_w66.py
    venv/bin/python spacetime_app/todo/check_w66.py --verbose
"""
import sys
import math
from pathlib import Path

import frontmatter

BASE = Path(__file__).parent.parent.parent
POIS_DIR = BASE / "spacetime_app" / "pois"
CONTENT_DIR = BASE / "content"
VERBOSE = "--verbose" in sys.argv


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def title_similarity(a, b):
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return 1.0
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def load_shadow_pois():
    pois = []
    for path in sorted(POIS_DIR.glob("*.md")):
        try:
            post = frontmatter.load(str(path))
        except Exception:
            continue
        if post.get("w66_path"):
            continue  # already claimed
        lat = post.get("latitude") or post.get("lat")
        lng = post.get("longitude") or post.get("lng")
        if lat is None or lng is None:
            continue
        pois.append({
            "slug": path.stem,
            "path": path,
            "title": post.get("title", path.stem),
            "lat": float(lat),
            "lng": float(lng),
            "location": post.get("location", ""),
        })
    return pois


def scan_w66_pois(location_prefix):
    """Scan W66 content under the given location prefix for type:poi files."""
    search_dir = CONTENT_DIR / location_prefix.replace("/", "/")
    if not search_dir.exists():
        search_dir = CONTENT_DIR
    pois = []
    for md in search_dir.rglob("*.md"):
        try:
            post = frontmatter.load(str(md))
        except Exception:
            continue
        if post.get("type") != "poi":
            continue
        lat = post.get("latitude") or post.get("lat")
        lng = post.get("longitude") or post.get("lng")
        if lat is None or lng is None:
            continue
        rel_path = str(md.relative_to(CONTENT_DIR).with_suffix(""))
        pois.append({
            "w66_path": rel_path,
            "title": post.get("title", md.stem),
            "lat": float(lat),
            "lng": float(lng),
        })
    return pois


def main():
    shadow_pois = load_shadow_pois()
    if not shadow_pois:
        print("No unclaimed shadow POIs found.")
        return

    print(f"Checking {len(shadow_pois)} shadow POI(s) against W66 content...\n")
    matches = []

    for shadow in shadow_pois:
        location = shadow["location"] or "europe"
        w66_pois = scan_w66_pois(location)
        if VERBOSE:
            print(f"  {shadow['slug']}: scanning {len(w66_pois)} W66 POIs under '{location}'")

        best = None
        best_score = 0
        for w66 in w66_pois:
            dist = haversine_m(shadow["lat"], shadow["lng"], w66["lat"], w66["lng"])
            if dist > 200:  # within 200m
                continue
            sim = title_similarity(shadow["title"], w66["title"])
            score = sim * (1 - dist / 200)
            if score > best_score:
                best_score = score
                best = {**w66, "distance_m": round(dist), "similarity": round(sim, 2)}

        if best and best_score > 0.3:
            matches.append((shadow, best))
            print(f"✓ MATCH: spacetime/{shadow['slug']}")
            print(f"    Shadow: {shadow['title']} ({shadow['lat']}, {shadow['lng']})")
            print(f"    W66:    {best['title']} → {best['w66_path']}")
            print(f"    Distance: {best['distance_m']}m  Title similarity: {best['similarity']}")
            print(f"    Action: set w66_path: {best['w66_path']} in pois/{shadow['slug']}.md")
            print()
        else:
            if VERBOSE:
                print(f"  ✗ No match: {shadow['slug']}")

    if not matches:
        print("No matches found — shadow POIs not yet in W66.")
    else:
        print(f"Found {len(matches)} match(es). See spacetime_app/todo/DELIST.md for next steps.")


if __name__ == "__main__":
    main()
