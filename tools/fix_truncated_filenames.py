#!/usr/bin/env python3
"""Phase 4: rename location files whose filenames were truncated.

Reads the output of find_filename_mismatches.py (TSV on stdin or a path),
selects the high-confidence truncation cases, and:

  1. Renames the .md file (and its sibling slug directory if one exists)
  2. Updates references in every other .md file: markdown links
     `(/path/to/old)` -> `(/path/to/new)`, frontmatter linked_locations,
     and bare path mentions
  3. Updates tools/non_cities.tsv to use the new paths

A "high-confidence truncation" is:
  - Category "truncated" from the mismatch scan
  - Stem contains at least one underscore (so we don't touch the
    World66 "smashed lowercase" convention for continent/country names)
  - Stem is >= 14 chars (catches the 17/18-char import-truncation bug)
  - Stem is a strict prefix of the slugified title

The list is printed to stdout before any changes happen. Pass --apply to
actually rename; otherwise it's a dry run.
"""

import argparse
import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
TSV = Path(__file__).resolve().parent / "non_cities.tsv"
MISMATCH_TSV = Path("/tmp/fname_mismatches.tsv")

# Skip cases where the "expected" slug is awkward in context. These pages
# kept their existing names by choice and the title is just verbose.
SKIP_PATHS = {
    # Parent already has /tibet/, no need to repeat it in the slug
    "asia/china/tibet/everest_base_camp",
    # Title is a long parenthetical list ("Hilltowns of the Savuto
    # (Grimaldi, Malito, Aiello, etc.)") that doesn't belong in a URL
    "europe/italy/calabria/hilltowns_of_the",
}


def load_renames(source: Path) -> list[tuple[str, str]]:
    """Return list of (old_rel_path, new_rel_path) without .md suffix."""
    renames: list[tuple[str, str]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        rel_path, stem, expected, category, title = parts
        if category != "truncated":
            continue
        if "_" not in stem:
            continue
        if len(stem) < 14:
            continue
        if not expected.startswith(stem) or len(expected) <= len(stem):
            continue
        if rel_path in SKIP_PATHS:
            continue
        # Build new relative path = parent + expected
        old = rel_path
        new = str(Path(rel_path).with_name(expected))
        renames.append((old, new))
    return renames


def apply_renames(renames: list[tuple[str, str]], dry_run: bool):
    # Process deepest paths first so parent renames don't pull children with
    # them mid-flight via the directory rename.
    renames_sorted = sorted(renames, key=lambda r: r[0].count("/"), reverse=True)
    for old, new in renames_sorted:
        old_md = CONTENT_DIR / f"{old}.md"
        new_md = CONTENT_DIR / f"{new}.md"
        old_dir = CONTENT_DIR / old
        new_dir = CONTENT_DIR / new
        actions = []
        if old_md.exists():
            actions.append(f"  mv {old_md.relative_to(CONTENT_DIR)} -> {new_md.relative_to(CONTENT_DIR)}")
            if not dry_run:
                new_md.parent.mkdir(parents=True, exist_ok=True)
                old_md.rename(new_md)
        if old_dir.is_dir():
            actions.append(f"  mv {old_dir.relative_to(CONTENT_DIR)}/ -> {new_dir.relative_to(CONTENT_DIR)}/")
            if not dry_run:
                old_dir.rename(new_dir)
        if not actions:
            print(f"[!] {old} -- nothing found to rename", file=sys.stderr)


def update_references(renames: list[tuple[str, str]], dry_run: bool) -> int:
    """Replace every occurrence of an old path with the new one across all .md files.

    Apply longest old-path first so partial-prefix matches don't shadow longer ones.
    """
    sorted_renames = sorted(renames, key=lambda r: len(r[0]), reverse=True)
    count = 0
    for md in CONTENT_DIR.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        original = text
        for old, new in sorted_renames:
            if old in text:
                text = text.replace(old, new)
        if text != original:
            count += 1
            if not dry_run:
                md.write_text(text, encoding="utf-8")
    return count


def update_tsv(renames: list[tuple[str, str]], dry_run: bool):
    if not TSV.exists():
        return
    text = TSV.read_text(encoding="utf-8")
    original = text
    for old, new in sorted(renames, key=lambda r: len(r[0]), reverse=True):
        text = text.replace(old, new)
    if text != original and not dry_run:
        TSV.write_text(text, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mismatches", default=str(MISMATCH_TSV),
                    help="TSV from find_filename_mismatches.py")
    ap.add_argument("--apply", action="store_true",
                    help="Actually rename files; default is dry run")
    args = ap.parse_args()

    source = Path(args.mismatches)
    renames = load_renames(source)
    print(f"Found {len(renames)} renames")
    for old, new in renames:
        print(f"  {old}  ->  {Path(new).name}")

    if not args.apply:
        print("\n(dry run — pass --apply to perform renames)")
        return

    print("\nRenaming files...")
    apply_renames(renames, dry_run=False)
    print("\nUpdating references...")
    updated = update_references(renames, dry_run=False)
    print(f"  updated {updated} files")
    print("\nUpdating non_cities.tsv...")
    update_tsv(renames, dry_run=False)
    print("Done.")


if __name__ == "__main__":
    sys.exit(main() or 0)
