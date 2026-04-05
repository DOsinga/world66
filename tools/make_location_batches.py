#!/usr/bin/env python3
"""Generate batch files for location_cleanup from all locations below country level.

Locations are sorted by total text size (largest first), so locations with
the most existing content to clean up get picked up first. Output goes to
todo/location_cleanup/.
"""

import os
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
TODO_DIR = Path(__file__).resolve().parent.parent / "todo" / "location_cleanup"
BATCH_SIZE = 50
CONTINENTS = {
    "africa", "antarctica", "asia", "australiaandpacific",
    "europe", "northamerica", "southamerica",
}
# Non-guide directories at the top level
SKIP_TOPLEVEL = {"about", "contributing", "travelwise"}

# Depth 1 = continent, depth 2 = country. We want depth 3+.
MIN_DEPTH = 3


def is_location(md_path: Path) -> bool:
    """Check if a .md file has type: location in its frontmatter."""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            in_frontmatter = False
            for line in f:
                line = line.strip()
                if line == "---":
                    if in_frontmatter:
                        return False  # end of frontmatter, didn't find it
                    in_frontmatter = True
                    continue
                if in_frontmatter and line == "type: location":
                    return True
    except (OSError, UnicodeDecodeError):
        return False
    return False


def total_text_size(md_path: Path) -> int:
    """Total bytes of the location file plus everything in its directory."""
    size = md_path.stat().st_size
    # Check for a matching directory (slug/slug.md -> slug/)
    slug_dir = md_path.parent / md_path.stem
    if slug_dir.is_dir():
        for f in slug_dir.rglob("*"):
            if f.is_file():
                size += f.stat().st_size
    return size


def content_relative(md_path: Path) -> str:
    """Return the path relative to content/, without the .md extension."""
    rel = md_path.relative_to(CONTENT_DIR)
    return str(rel.with_suffix(""))


def depth(md_path: Path) -> int:
    """Depth relative to content/. continent=1, country=2, etc."""
    return len(md_path.relative_to(CONTENT_DIR).parts)


def find_locations():
    """Find all location files at depth 3+ and return (relative_path, size) pairs."""
    locations = []
    for md_path in CONTENT_DIR.rglob("*.md"):
        # Skip non-guide top-level dirs
        top = md_path.relative_to(CONTENT_DIR).parts[0]
        if top in SKIP_TOPLEVEL:
            continue

        if depth(md_path) < MIN_DEPTH:
            continue

        if is_location(md_path):
            rel = content_relative(md_path)
            size = total_text_size(md_path)
            locations.append((rel, size))

    # Sort by size (largest first)
    locations.sort(key=lambda x: x[1], reverse=True)
    return locations


def main():
    locations = find_locations()
    print(f"Found {len(locations)} locations below country level")

    if not locations:
        return

    # Show size distribution
    sizes = [s for _, s in locations]
    print(f"  Smallest: {sizes[0]:,} bytes")
    print(f"  Median:   {sizes[len(sizes)//2]:,} bytes")
    print(f"  Largest:  {sizes[-1]:,} bytes")

    # Check for existing batch files
    existing = list(TODO_DIR.glob("batch_*.txt"))
    if existing and "--force" not in sys.argv:
        print(f"\n{len(existing)} batch files already exist in {TODO_DIR}")
        print("Use --force to overwrite them.")
        return

    # Remove old batch files
    for f in existing:
        f.unlink()

    # Write batches
    n_batches = 0
    for i in range(0, len(locations), BATCH_SIZE):
        batch = locations[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE
        batch_file = TODO_DIR / f"batch_{batch_num:03d}.txt"
        with open(batch_file, "w") as f:
            for rel_path, _ in batch:
                f.write(rel_path + "\n")
        n_batches += 1

    print(f"\nWrote {n_batches} batch files ({BATCH_SIZE} locations each) to {TODO_DIR}")


if __name__ == "__main__":
    main()
