#!/usr/bin/env python3
"""Search the obscura/<country>.json files for entries near a given city.

Atlas Obscura's flat JSON has a free-text `city` field that doesn't
always match World66 path slugs cleanly, so a small grep helper makes
it much more likely the obscura check actually happens during enrich.

Usage:
    python3 tools/grep_obscura.py <country> <city>

Country: filename stem under obscura/, e.g. "bhutan", "united-kingdom".
City: substring matched case-insensitively against the entry's city
      field, name, and address.

Prints one entry per match: name | city | address | description snippet.
"""

import json
import sys
from pathlib import Path

OBSCURA_DIR = Path(__file__).resolve().parent.parent / "obscura"


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <country> <city>", file=sys.stderr)
        sys.exit(1)
    country, needle = sys.argv[1].lower(), sys.argv[2].lower()
    path = OBSCURA_DIR / f"{country}.json"
    if not path.exists():
        print(f"No file: {path}", file=sys.stderr)
        candidates = sorted(p.stem for p in OBSCURA_DIR.glob("*.json"))
        for c in candidates:
            if country in c:
                print(f"  did you mean: {c}", file=sys.stderr)
        sys.exit(1)

    entries = json.loads(path.read_text(encoding="utf-8"))
    matches = []
    for e in entries:
        haystack = " ".join([
            str(e.get("name") or ""),
            str(e.get("city") or ""),
            str(e.get("address") or ""),
        ]).lower()
        if needle in haystack:
            matches.append(e)

    print(f"Found {len(matches)} match(es) for {needle!r} in {country}")
    for e in matches:
        name = e.get("name", "")
        city = e.get("city", "")
        addr = e.get("address", "")
        desc = (e.get("description") or "").strip().replace("\n", " ")
        if len(desc) > 200:
            desc = desc[:200] + "…"
        print()
        print(f"  {name}")
        if city:
            print(f"    city:    {city}")
        if addr:
            print(f"    address: {addr}")
        if desc:
            print(f"    {desc}")


if __name__ == "__main__":
    sys.exit(main() or 0)
