#!/usr/bin/env python3
"""
Read locations.json and write lat/lng into markdown frontmatter.
Run this after geocode.py finishes.
"""

import json
from pathlib import Path

import frontmatter

SCRIPT_DIR = Path(__file__).parent
CONTENT_DIR = SCRIPT_DIR.parent / "content"
LOCATIONS_FILE = SCRIPT_DIR / "locations.json"


def run():
    with open(LOCATIONS_FILE) as f:
        locations = json.load(f)

    updated = 0
    skipped = 0

    for rel_path, info in locations.items():
        lat = info.get("lat")
        lng = info.get("lng")
        if not lat or not lng:
            skipped += 1
            continue

        filepath = CONTENT_DIR / rel_path
        if not filepath.exists():
            continue

        try:
            post = frontmatter.load(filepath)
        except Exception as e:
            print(f"Warning: skipping {filepath}: {e}")
            continue
        if "latitude" in post.metadata and "longitude" in post.metadata:
            continue

        post["latitude"] = lat
        post["longitude"] = lng
        filepath.write_text(frontmatter.dumps(post, sort_keys=False) + "\n", encoding="utf-8")
        updated += 1

    print(f"Updated: {updated}, Skipped (no coords): {skipped}")


if __name__ == "__main__":
    run()
