#!/usr/bin/env python3
"""Generate batch files for POI cleanup.

Finds all type:poi markdown files, shuffles them, and writes batch files
of 50 POIs each.
"""

import random
import subprocess
from pathlib import Path

TODO_DIR = Path(__file__).parent
CONTENT_DIR = TODO_DIR.parent.parent / "content"

def find_pois():
    """Return list of POI content paths (relative to content/)."""
    result = subprocess.run(
        ["grep", "-rl", "^type: poi", str(CONTENT_DIR)],
        capture_output=True, text=True
    )
    paths = []
    for line in result.stdout.strip().splitlines():
        rel = Path(line).relative_to(CONTENT_DIR)
        # Strip .md extension for content path
        paths.append(str(rel.with_suffix("")))
    random.shuffle(paths)
    return paths


def main():
    pois = find_pois()
    batch_size = 50
    for i in range(0, len(pois), batch_size):
        batch = pois[i : i + batch_size]
        batch_num = i // batch_size + 1
        batch_file = TODO_DIR / f"batch_{batch_num:03d}.txt"
        batch_file.write_text("\n".join(batch) + "\n")
    print(f"Created {(len(pois) + batch_size - 1) // batch_size} batches from {len(pois)} POIs")


if __name__ == "__main__":
    main()
