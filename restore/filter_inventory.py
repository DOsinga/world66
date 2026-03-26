#!/usr/bin/env python3
"""
Filter the raw inventory to content pages we want, normalize section names,
and skip unwanted sections.
"""

import json
from urllib.parse import urlparse
from collections import Counter

INVENTORY_IN = "inventory.jsonl"
INVENTORY_OUT = "inventory_filtered.jsonl"

GEO_SEGMENTS = {
    "europe",
    "asia",
    "northamerica",
    "africa",
    "southamerica",
    "australiaandpacific",
    "centralamericathecaribbean",
    "antarctica",
    "world",
}

# Sections to skip entirely
SKIP_SECTIONS = {
    "accommodation",
    "hotels",
    "internetcafes",
    "cybercafes",
    "internet_cafes",
    "webcams__360_degr",
    "links",
    "cruises",
    "senior_travel",
    "eating_out_intro",
    "economy",
    "addnew",
    "imagechange",
    "imageupload",
    "epoz_blank_iframe.html",
    "byair",
    "..",
    "day_trips_intro",
}

# Normalize section names to use underscores consistently
NORMALIZE = {
    "eatingout": "eating_out",
    "gettingthere": "getting_there",
    "gettingaround": "getting_around",
    "thingstodo": "things_to_do",
    "daytrips": "day_trips",
    "practicalthings": "practical_informat",
    "practicalinformat": "practical_informat",
    "barsandcafes": "bars_and_cafes",
    "toursandexcursions": "tours_and_excursio",
}

# Path parts to skip (tooling, not content)
SKIP_PATH_PARTS = {
    "lib",
    "upload",
    "change",
    "sanitycheck",
    "gallery",
    "flights",
    "map",
    "modify",
    "edit",
    "create",
    "delete",
    "history",
}


def normalize_path(path):
    """Normalize a URL path — fix section names."""
    parts = path.strip("/").split("/")
    if parts:
        last = parts[-1]
        if last.lower() in NORMALIZE:
            parts[-1] = NORMALIZE[last.lower()]
    return "/".join(parts)


def should_keep(url):
    """Decide whether to keep this URL."""
    parsed = urlparse(url)

    # Skip URLs with query strings
    if parsed.query:
        return False

    path = parsed.path.strip("/")
    parts = [p for p in path.split("/") if p]

    # Must start with a geographic segment
    if not parts or parts[0] not in GEO_SEGMENTS:
        return False

    # Skip paths with weird characters
    if any(c in path for c in ["%", "+", "<", ">", "?", "&", "=", ";", ","]):
        return False

    # Skip if any path part is in the skip list
    parts_lower = [p.lower() for p in parts]
    if any(p in SKIP_PATH_PARTS for p in parts_lower):
        return False

    # Skip if the last segment (section name) is in skip list
    if parts_lower[-1] in SKIP_SECTIONS:
        return False

    # Also skip if any intermediate part is a skipped section
    # (e.g. /africa/algeria/algiers/accommodation/some_hotel)
    for p in parts_lower[:-1]:
        if p in SKIP_SECTIONS:
            return False

    return True


def run():
    entries = []
    with open(INVENTORY_IN) as f:
        for line in f:
            entries.append(json.loads(line))

    print(f"Input: {len(entries):,} entries")

    clean = []
    seen_paths = set()
    skip_reasons = Counter()

    for e in entries:
        url = e["original"]

        if not should_keep(url):
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            parts = path.split("/")
            if parts:
                last = parts[-1].lower()
                if last in SKIP_SECTIONS:
                    skip_reasons[f"section:{last}"] += 1
                elif any(p.lower() in SKIP_PATH_PARTS for p in parts):
                    skip_reasons["path_part"] += 1
                elif parsed.query:
                    skip_reasons["query_string"] += 1
                else:
                    skip_reasons["other"] += 1
            continue

        # Normalize the path
        parsed = urlparse(url)
        norm_path = normalize_path(parsed.path).lower()

        if norm_path in seen_paths:
            skip_reasons["duplicate"] += 1
            continue
        seen_paths.add(norm_path)

        # Store normalized path for later use
        e["normalized_path"] = normalize_path(parsed.path)
        clean.append(e)

    with open(INVENTORY_OUT, "w") as f:
        for e in clean:
            f.write(json.dumps(e) + "\n")

    print(f"Output: {len(clean):,} content pages")
    print(f"\nSkip reasons:")
    for reason, count in skip_reasons.most_common(20):
        print(f"  {reason}: {count:,}")

    # Show section distribution
    sections = Counter()
    for e in clean:
        parts = e["normalized_path"].strip("/").split("/")
        if len(parts) >= 3:  # has a section
            sections[parts[-1]] += 1
        else:
            sections["[location page]"] += 1

    print(f"\nSection distribution:")
    for sec, count in sections.most_common(30):
        print(f"  {sec}: {count:,}")

    # Continent breakdown
    continents = Counter()
    for e in clean:
        parts = e["normalized_path"].strip("/").split("/")
        continents[parts[0]] += 1

    print(f"\nBy continent:")
    for cont, count in continents.most_common():
        print(f"  {cont}: {count:,}")


if __name__ == "__main__":
    run()
