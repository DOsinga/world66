#!/usr/bin/env python3
"""Write the list of cities to todo/location_enrich/cities.txt.

A city is any page with `type: location` and `loc_type: city` in its
frontmatter — see LOCATIONS.md for the schema. The list is sorted by
total content size (largest first), so well-developed cities come first.
"""

import re
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
OUTPUT = Path(__file__).resolve().parent.parent / "todo" / "location_enrich" / "cities.txt"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
TYPE_RE = re.compile(r"^type:\s*(\S+)\s*$", re.MULTILINE)
LOC_TYPE_RE = re.compile(r"^loc_type:\s*(\S+)\s*$", re.MULTILINE)


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
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = FRONTMATTER_RE.match(text)
        if not fm:
            continue
        body = fm.group(1)
        t = TYPE_RE.search(body)
        if not t or t.group(1) != "location":
            continue
        lt = LOC_TYPE_RE.search(body)
        if not lt or lt.group(1) != "city":
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
