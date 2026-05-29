#!/usr/bin/env python3
"""Find batch entries that are regions (3+ child locations).

Writes regions to regions.txt and removes them from the batch files."""

import os
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"
BATCH_DIR = Path(__file__).resolve().parent


def count_children(content_path):
    """Count subdirectories that represent child locations."""
    full = CONTENT_DIR / content_path
    if not full.is_dir():
        return 0
    return sum(1 for d in full.iterdir() if d.is_dir())


def main():
    regions = []
    batch_changes = {}  # batch_file -> list of lines to keep

    for batch_file in sorted(BATCH_DIR.glob("batch_*.txt")):
        keep = []
        for line in batch_file.read_text().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            n = count_children(stripped)
            if n >= 3:
                regions.append((stripped, n, batch_file.name))
            else:
                keep.append(stripped)
        batch_changes[batch_file] = keep

    # Write regions.txt
    regions.sort(key=lambda x: -x[1])
    out = BATCH_DIR / "regions.txt"
    with open(out, "w") as f:
        for path, n, batch in regions:
            f.write(f"{path}  # {n} children, from {batch}\n")

    # Update batch files
    removed_total = 0
    for batch_file, keep in batch_changes.items():
        original = [l.strip() for l in batch_file.read_text().splitlines() if l.strip()]
        removed = len(original) - len(keep)
        removed_total += removed
        if removed > 0:
            if keep:
                batch_file.write_text("\n".join(keep) + "\n")
            else:
                batch_file.unlink()
                print(f"  Deleted {batch_file.name} (all {len(original)} entries were regions)")
                continue
            print(f"  {batch_file.name}: removed {removed}, {len(keep)} remaining")

    print(f"\nMoved {len(regions)} regions to regions.txt, removed from {removed_total} batch entries")


if __name__ == "__main__":
    main()
