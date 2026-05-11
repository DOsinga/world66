#!/usr/bin/env python3
"""Find all leaf locations (cities) and write them to todo/location_enrich/cities.txt.

A leaf location is a location whose directory contains no child of type: location.
Children may still be sections, POIs, or neighbourhoods. The result is sorted by
total content size (largest first), matching the convention used by
make_location_batches.py.
"""

from pathlib import Path

import frontmatter

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
OUTPUT = Path(__file__).resolve().parent.parent / "todo" / "location_enrich" / "cities.txt"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}


def load_locations():
    """Return dict of relative-path-without-ext -> md_path for every type: location."""
    out = {}
    for md in CONTENT_DIR.rglob("*.md"):
        parts = md.relative_to(CONTENT_DIR).parts
        if parts[0] in SKIP_TOPLEVEL:
            continue
        if len(parts) == 1 and md.stem in SKIP_TOPLEVEL:
            continue
        try:
            meta = frontmatter.load(md).metadata
        except Exception:
            continue
        if meta.get("type") == "location":
            rel = str(md.relative_to(CONTENT_DIR).with_suffix(""))
            out[rel] = md
    return out


def has_child_location(md_path: Path) -> bool:
    slug_dir = md_path.parent / md_path.stem
    if not slug_dir.is_dir():
        return False
    for child in slug_dir.rglob("*.md"):
        try:
            meta = frontmatter.load(child).metadata
        except Exception:
            continue
        if meta.get("type") == "location":
            return True
    return False


def total_text_size(md_path: Path) -> int:
    size = md_path.stat().st_size
    slug_dir = md_path.parent / md_path.stem
    if slug_dir.is_dir():
        for f in slug_dir.rglob("*"):
            if f.is_file():
                size += f.stat().st_size
    return size


def main():
    locations = load_locations()
    print(f"Total locations: {len(locations)}")

    leaves = []
    for rel, md in locations.items():
        if not has_child_location(md):
            leaves.append((rel, total_text_size(md)))

    leaves.sort(key=lambda x: x[1], reverse=True)
    print(f"Leaf locations (cities): {len(leaves)}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        for rel, _ in leaves:
            f.write(rel + "\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
