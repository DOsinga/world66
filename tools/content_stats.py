#!/usr/bin/env python3
"""Summary stats for world66 content/.

Counts locations, POIs, locations-with-images, and a histogram of section
names. With --loc-type <kind>, filters every count to entries whose nearest
location ancestor has that loc_type (continent, country, region, island,
feature, city).
"""

import argparse
from collections import Counter
from pathlib import Path

import frontmatter

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
LOC_TYPES = ("continent", "country", "region", "island", "feature", "city")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--loc-type", choices=LOC_TYPES,
        help="Only include entries under a location of this loc_type",
    )
    args = ap.parse_args()

    # First pass: classify every page, and record where each location lives so
    # we can resolve the parent loc_type of any other file. Per CLAUDE.md, the
    # location file lives at content/<path>.md with children in content/<path>/
    # (sibling-style). A handful of legacy files break this with the file
    # inside its own dir (content/<path>/<slug>.md) — handle both.
    pages = []                  # list of (path, page_type, meta)
    loc_type_by_dir = {}        # dir Path -> loc_type (or "")
    for md in CONTENT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(md)
        except Exception as e:
            print(f"skip {md}: {e}")
            continue
        page_type = post.metadata.get("type", "location")
        pages.append((md, page_type, post.metadata))
        if page_type == "location":
            lt = post.metadata.get("loc_type", "")
            if md.stem == md.parent.name:
                loc_type_by_dir[md.parent] = lt
            else:
                sibling = md.parent / md.stem
                if sibling.is_dir():
                    loc_type_by_dir[sibling] = lt

    def parent_loc_type(md: Path) -> str:
        d = md.parent
        while d != CONTENT_DIR.parent:
            if d in loc_type_by_dir:
                return loc_type_by_dir[d]
            d = d.parent
        return ""

    locs = pois = sections = locs_with_image = 0
    section_names = Counter()
    type_counts = Counter()
    loc_type_counts = Counter()
    locs_missing_loc_type = 0

    for md, page_type, meta in pages:
        if args.loc_type:
            if page_type == "location":
                if meta.get("loc_type", "") != args.loc_type:
                    continue
            elif parent_loc_type(md) != args.loc_type:
                continue

        type_counts[page_type] += 1
        if page_type == "location":
            locs += 1
            lt = meta.get("loc_type", "")
            if lt:
                loc_type_counts[lt] += 1
            else:
                locs_missing_loc_type += 1
            if meta.get("image"):
                locs_with_image += 1
        elif page_type == "poi":
            pois += 1
        elif page_type == "section":
            sections += 1
            section_names[md.stem] += 1

    label = f" (loc_type={args.loc_type})" if args.loc_type else ""
    print(f"Locations:           {locs}{label}")
    if locs:
        print(f"  with image:        {locs_with_image} ({100*locs_with_image/locs:.1f}%)")
    print(f"POIs:                {pois}")
    print(f"Sections:            {sections}")
    print()

    print("Locations by loc_type:")
    for lt in LOC_TYPES:
        n = loc_type_counts.get(lt, 0)
        if n:
            print(f"  {lt:12s} {n}")
    if locs_missing_loc_type:
        print(f"  (missing)    {locs_missing_loc_type}")
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
