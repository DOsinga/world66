#!/usr/bin/env python3
"""Set the `loc_type` field on every `type: location` page.

Phase 1 (mechanical, no judgement):
  depth 1 -> continent
  depth 2 -> country
  depth >=3 with at least one child `type: location` -> region

Phase 2 (leaves) is handled by classify_leaves.py, which reads a TSV of
known non-cities and defaults everything else to `city`.

Idempotent — if `loc_type` is already set, the file is left alone unless
--overwrite is passed.
"""

import argparse
import sys
from pathlib import Path

import frontmatter

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}


def has_child_location(md_path: Path) -> bool:
    slug_dir = md_path.parent / md_path.stem
    if not slug_dir.is_dir():
        return False
    for child in slug_dir.rglob("*.md"):
        try:
            post = frontmatter.load(child)
        except Exception:
            continue
        if post.metadata.get("type") == "location":
            return True
    return False


def iter_location_files():
    for md in CONTENT_DIR.rglob("*.md"):
        parts = md.relative_to(CONTENT_DIR).parts
        if parts[0] in SKIP_TOPLEVEL:
            continue
        if len(parts) == 1 and md.stem in SKIP_TOPLEVEL:
            continue
        try:
            post = frontmatter.load(md)
        except Exception:
            continue
        if post.metadata.get("type") == "location":
            yield md, post


def mechanical_loc_type(md: Path) -> str | None:
    depth = len(md.relative_to(CONTENT_DIR).parts)
    if depth == 1:
        return "continent"
    if depth == 2:
        return "country"
    if has_child_location(md):
        return "region"
    return None  # leaf — phase 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    counts = {"continent": 0, "country": 0, "region": 0, "skipped": 0,
              "already_set": 0}

    for md, post in iter_location_files():
        target = mechanical_loc_type(md)
        if target is None:
            counts["skipped"] += 1
            continue

        existing = post.metadata.get("loc_type")
        if existing == target:
            counts["already_set"] += 1
            continue
        if existing and not args.overwrite:
            counts["already_set"] += 1
            continue

        post.metadata["loc_type"] = target
        counts[target] += 1
        if not args.dry_run:
            md.write_text(frontmatter.dumps(post, sort_keys=False) + "\n",
                          encoding="utf-8")

    print(f"Continents:  {counts['continent']}")
    print(f"Countries:   {counts['country']}")
    print(f"Regions:     {counts['region']}")
    print(f"Already set: {counts['already_set']}")
    print(f"Leaves (phase 2): {counts['skipped']}")
    if args.dry_run:
        print("\n(dry run)")


if __name__ == "__main__":
    sys.exit(main() or 0)
