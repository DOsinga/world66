#!/usr/bin/env python3
"""Aggregate the per-country region-name files in /tmp/region_names_out/ into
one JSON override file, and apply it to regions_data.json + regions.geo.json.

Why a separate override file: build_regions.py regenerates the names from
locations + Voronoi each time, so we need a stable override layer that the
build can apply at the end.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path("/tmp/region_names_out")
OVERRIDES = ROOT / "tools" / "region_name_overrides.json"
GEO = ROOT / "static" / "geo" / "regions.geo.json"
DATA = ROOT / "static" / "geo" / "regions_data.json"


def main():
    overrides: dict[str, str] = {}
    for f in sorted(OUT_DIR.glob("*.txt")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or "|" not in line:
                continue
            rid, name = line.split("|", 1)
            rid = rid.strip()
            name = name.strip()
            # Normalise: some agents used hyphens where "&" or spaces were intended.
            # Keep as-is unless it's a clear all-hyphen replacement of spaces.
            if "-" in name and " " not in name and len(name.split("-")) <= 4:
                # e.g. "Rocky-Mountains" -> "Rocky Mountains", but keep
                # things like "Mid-Atlantic" which look right.
                if all(p[0].isupper() for p in name.split("-")):
                    name = name.replace("-", " ")
            overrides[rid] = name

    OVERRIDES.write_text(json.dumps(overrides, indent=1, sort_keys=True) + "\n")
    print(f"Wrote {len(overrides)} overrides to {OVERRIDES}")

    # Apply to data + geojson
    data = json.loads(DATA.read_text())
    geo = json.loads(GEO.read_text())

    n_data = 0
    for rid, new_name in overrides.items():
        if rid in data and data[rid]["name"] != new_name:
            data[rid]["name"] = new_name
            n_data += 1
    for feat in geo["features"]:
        rid = feat["properties"].get("id")
        if rid in overrides and feat["properties"]["name"] != overrides[rid]:
            feat["properties"]["name"] = overrides[rid]

    DATA.write_text(json.dumps(data, indent=1))
    GEO.write_text(json.dumps(geo))
    print(f"Updated {n_data} entries in regions_data.json")


if __name__ == "__main__":
    main()
