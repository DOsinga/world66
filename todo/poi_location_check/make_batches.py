#!/usr/bin/env python3
"""Generate batch files for POI location check.

Finds all city directories that contain POIs, shuffles them, and writes
batch files of 35 cities each. Each line in a batch file is a city path
(relative to content/) — the agent processes all POIs in that city.
"""

import random
import subprocess
from pathlib import Path

TODO_DIR = Path(__file__).parent
CONTENT_DIR = TODO_DIR.parent.parent / "content"
BATCH_SIZE = 35


def find_cities():
    """Return list of city dirs (relative to content/) that contain POIs."""
    result = subprocess.run(
        ["grep", "-rl", "^type: poi", str(CONTENT_DIR)],
        capture_output=True, text=True
    )
    cities = set()
    for line in result.stdout.strip().splitlines():
        parent = Path(line).parent
        cities.add(str(parent.relative_to(CONTENT_DIR)))
    cities = sorted(cities)
    random.shuffle(cities)
    return cities


def main():
    cities = find_cities()
    num_batches = (len(cities) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(cities), BATCH_SIZE):
        batch = cities[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        batch_file = TODO_DIR / f"batch_{batch_num:04d}.txt"
        batch_file.write_text("\n".join(batch) + "\n")
    print(f"Created {num_batches} batches from {len(cities)} cities")


if __name__ == "__main__":
    main()
