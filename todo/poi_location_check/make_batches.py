#!/usr/bin/env python3
"""Generate batch files for POI location check.

Finds all type:poi markdown files, shuffles them, and writes batch files
of 50 POIs each.
"""

import random
import subprocess
from pathlib import Path

TODO_DIR = Path(__file__).parent
CONTENT_DIR = TODO_DIR.parent.parent / "content"
BATCH_SIZE = 50


def find_pois():
    """Return list of POI content paths (relative to content/, without .md)."""
    result = subprocess.run(
        ["grep", "-rl", "^type: poi", str(CONTENT_DIR)],
        capture_output=True, text=True
    )
    paths = []
    for line in result.stdout.strip().splitlines():
        rel = Path(line).relative_to(CONTENT_DIR)
        paths.append(str(rel.with_suffix("")))
    random.shuffle(paths)
    return paths


def main():
    pois = find_pois()
    num_batches = (len(pois) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(pois), BATCH_SIZE):
        batch = pois[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        batch_file = TODO_DIR / f"batch_{batch_num:04d}.txt"
        batch_file.write_text("\n".join(batch) + "\n")
    print(f"Created {num_batches} batches from {len(pois)} POIs")


if __name__ == "__main__":
    main()
