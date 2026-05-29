#!/usr/bin/env python3
"""Write the list of cities to todo/location_enrich/cities.txt.

A city is any page with `type: location` and `loc_type: city` in its
frontmatter — see LOCATIONS.md for the schema. The list is sorted by
total content size (largest first), so well-developed cities come first.
"""

from pathlib import Path

import frontmatter

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
OUTPUT = Path(__file__).resolve().parent.parent / "todo" / "location_enrich" / "cities.txt"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}


def total_text_size(md_path: Path) -> int:
    size = md_path.stat().st_size
    slug_dir = md_path.parent / md_path.stem
    if slug_dir.is_dir():
        for f in slug_dir.rglob("*"):
            if f.is_file():
                size += f.stat().st_size
    return size


def main():
    cities: list[tuple[str, int]] = []
    for md in CONTENT_DIR.rglob("*.md"):
        parts = md.relative_to(CONTENT_DIR).parts
        if parts[0] in SKIP_TOPLEVEL:
            continue
        if len(parts) == 1 and md.stem in SKIP_TOPLEVEL:
            continue
        try:
            post = frontmatter.load(md)
        except Exception:
            continue
        if post.metadata.get("type") != "location":
            continue
        if post.metadata.get("loc_type") != "city":
            continue
        rel = str(md.relative_to(CONTENT_DIR).with_suffix(""))
        cities.append((rel, total_text_size(md)))

    cities.sort(key=lambda x: x[1], reverse=True)
    print(f"Cities: {len(cities)}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        for rel, _ in cities:
            f.write(rel + "\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
