#!/usr/bin/env python3
"""Generate batch files for location_enrich from todo/location_enrich/cities.txt.

cities.txt is produced by tools/find_leaf_locations.py and lists every page
with `loc_type: city`. We shuffle that list with a fixed seed (so re-runs
group the same cities together) and split it into batches of 5, written
to todo/location_enrich/batch_NNNN.txt.

Five per batch keeps each PR scoped to roughly one session of work —
enrich is significantly heavier than the cleanup pass (POI generation,
web research, image hunting, neighbourhood POIs, story fields).
"""

import argparse
import random
import sys
from pathlib import Path

TODO_DIR = Path(__file__).resolve().parent.parent / "todo" / "location_enrich"
CITIES = TODO_DIR / "cities.txt"
BATCH_SIZE = 5
SEED = 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing batch files")
    args = ap.parse_args()

    cities = [line.strip() for line in CITIES.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(cities)} cities from {CITIES.name}")

    existing = sorted(TODO_DIR.glob("batch_*.txt"))
    if existing and not args.force:
        print(f"\n{len(existing)} batch files already exist. Use --force to overwrite.")
        return

    rng = random.Random(SEED)
    rng.shuffle(cities)

    for f in existing:
        f.unlink()

    n_batches = 0
    for i in range(0, len(cities), BATCH_SIZE):
        batch = cities[i:i + BATCH_SIZE]
        batch_file = TODO_DIR / f"batch_{i // BATCH_SIZE:04d}.txt"
        batch_file.write_text("\n".join(batch) + "\n", encoding="utf-8")
        n_batches += 1

    print(f"Wrote {n_batches} batch files ({BATCH_SIZE} cities each) to {TODO_DIR}")


if __name__ == "__main__":
    sys.exit(main() or 0)
