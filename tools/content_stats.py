#!/usr/bin/env python3
"""Summary stats for world66 content/.

Counts locations, POIs, locations-with-images, and a histogram of section names.
"""

from collections import Counter
from pathlib import Path

import frontmatter

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def main():
    locs = 0
    pois = 0
    locs_with_image = 0
    sections = 0
    section_names = Counter()
    type_counts = Counter()

    for md in CONTENT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(md)
        except Exception as e:
            print(f"skip {md}: {e}")
            continue

        page_type = post.metadata.get("type", "location")
        type_counts[page_type] += 1

        if page_type == "location":
            locs += 1
            if post.metadata.get("image"):
                locs_with_image += 1
        elif page_type == "poi":
            pois += 1
        elif page_type == "section":
            sections += 1
            section_names[md.stem] += 1

    print(f"Locations:           {locs}")
    print(f"  with image:        {locs_with_image} ({100*locs_with_image/locs:.1f}%)")
    print(f"POIs:                {pois}")
    print(f"Sections:            {sections}")
    print()
    print("Page type breakdown:")
    for t, n in type_counts.most_common():
        print(f"  {t:20s} {n}")
    print()
    print("Section histogram (by slug):")
    width = max((len(name) for name, _ in section_names.most_common()), default=0)
    for name, count in section_names.most_common():
        bar = "#" * min(count, 60)
        print(f"  {name:<{width}}  {count:5d}  {bar}")


if __name__ == "__main__":
    main()
