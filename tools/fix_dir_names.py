#!/usr/bin/env python3
"""Rename directories that don't match their section .md file.

Legacy data has mismatches like eating_out.md with an eatingout/ directory.
This script renames the directories to match the .md filenames.
"""

import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def find_mismatches(content_dir):
    """Find directories whose name sans underscores matches an .md file stem."""
    renames = []
    for md_file in sorted(content_dir.rglob("*.md")):
        stem = md_file.stem
        parent = md_file.parent
        no_underscores = stem.replace("_", "")
        if no_underscores == stem:
            continue
        candidate = parent / no_underscores
        correct = parent / stem
        if candidate.is_dir() and not correct.is_dir():
            renames.append((candidate, correct))
    return renames


def main():
    dry_run = "--dry-run" in sys.argv
    renames = find_mismatches(CONTENT_DIR)

    if not renames:
        print("No mismatched directories found.")
        return

    for old, new in renames:
        old_rel = old.relative_to(CONTENT_DIR)
        new_rel = new.relative_to(CONTENT_DIR)
        if dry_run:
            print(f"  {old_rel} -> {new_rel}")
        else:
            old.rename(new)
            print(f"  renamed {old_rel} -> {new_rel}")

    print(f"\n{'Would rename' if dry_run else 'Renamed'} {len(renames)} directories.")


if __name__ == "__main__":
    main()
