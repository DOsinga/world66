#!/usr/bin/env python3
"""
Read locations.json and write lat/lng into markdown frontmatter.
Run this after geocode.py finishes.
"""

import json
import os
import re
from pathlib import Path

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

        text = filepath.read_text(encoding="utf-8", errors="replace")

        # Skip if already has coordinates
        if "latitude:" in text and "longitude:" in text:
            continue

        # Insert lat/lng into frontmatter
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                frontmatter = text[3:end]
                body = text[end + 4:]
                new_text = f"---{frontmatter}\nlatitude: {lat}\nlongitude: {lng}\n---{body}"
                filepath.write_text(new_text, encoding="utf-8")
                updated += 1

    print(f"Updated: {updated}, Skipped (no coords): {skipped}")


if __name__ == "__main__":
    run()
