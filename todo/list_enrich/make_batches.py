#!/usr/bin/env python3
"""Generate batch files for the list_enrich task.

Countries with too little existing content can't support genuinely good
cross-cutting lists yet (see LISTS.md's "every item must be real" rule), so
this only batches countries above a POI-count floor. The United Kingdom is
excluded — it's the pilot/reference implementation (see TASK.md), not a
fresh target.
"""

import random
import subprocess
from pathlib import Path

TODO_DIR = Path(__file__).parent
CONTENT_DIR = TODO_DIR.parent.parent / "content"
MIN_POIS = 200
BATCH_SIZE = 4
EXCLUDE = {"europe/unitedkingdom"}


def find_countries():
    result = subprocess.run(
        ["grep", "-rl", "^loc_type: country", str(CONTENT_DIR)],
        capture_output=True, text=True,
    )
    countries = []
    for line in result.stdout.strip().splitlines():
        country_path = Path(line).with_suffix("")
        rel = str(country_path.relative_to(CONTENT_DIR))
        if rel in EXCLUDE:
            continue
        poi_result = subprocess.run(
            ["grep", "-rl", "^type: poi", str(country_path)],
            capture_output=True, text=True,
        )
        poi_count = len(poi_result.stdout.strip().splitlines())
        if poi_count >= MIN_POIS:
            countries.append(rel)
    return countries


def main():
    countries = find_countries()
    random.shuffle(countries)
    for i in range(0, len(countries), BATCH_SIZE):
        batch = countries[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        batch_file = TODO_DIR / f"batch_{batch_num:03d}.txt"
        batch_file.write_text("\n".join(batch) + "\n")
    print(f"Created {(len(countries) + BATCH_SIZE - 1) // BATCH_SIZE} batches from {len(countries)} countries")


if __name__ == "__main__":
    main()
