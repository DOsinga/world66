#!/usr/bin/env python3
"""Set the `loc_type` field on every `type: location` page.

Phase 1 (mechanical, no judgement):
  depth 1 -> continent
  depth 2 -> country
  depth >=3 with at least one child `type: location` -> region

Phase 2 (leaves) is handled by classify_leaves.py, which reads a TSV of
known non-cities and defaults everything else to `city`.

The edit is done with a surgical text patch on the YAML frontmatter so the
file diff is minimal (one inserted/updated line). It will not reorder
existing keys, change quoting, or touch the trailing newline.

Idempotent — if `loc_type` is already set, the file is left alone unless
--overwrite is passed.
"""

import argparse
import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
LOC_TYPE_RE = re.compile(r"^loc_type:\s*(\S+)\s*$", re.MULTILINE)
TYPE_RE = re.compile(r"^type:\s*(\S+)\s*$", re.MULTILINE)


def read_frontmatter(text: str) -> str | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return m.group(1)


def file_type(text: str) -> str | None:
    fm = read_frontmatter(text)
    if fm is None:
        return None
    m = TYPE_RE.search(fm)
    return m.group(1) if m else None


def has_child_location(md_path: Path) -> bool:
    slug_dir = md_path.parent / md_path.stem
    if not slug_dir.is_dir():
        return False
    for child in slug_dir.rglob("*.md"):
        try:
            text = child.read_text(encoding="utf-8")
        except Exception:
            continue
        if file_type(text) == "location":
            return True
    return False


def all_location_files():
    for md in CONTENT_DIR.rglob("*.md"):
        parts = md.relative_to(CONTENT_DIR).parts
        if parts[0] in SKIP_TOPLEVEL:
            continue
        if len(parts) == 1 and md.stem in SKIP_TOPLEVEL:
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        if file_type(text) == "location":
            yield md, text


def mechanical_loc_type(md: Path) -> str | None:
    depth = len(md.relative_to(CONTENT_DIR).parts)
    if depth == 1:
        return "continent"
    if depth == 2:
        return "country"
    if has_child_location(md):
        return "region"
    return None  # leaf — phase 2


def set_loc_type_in_text(text: str, value: str) -> str:
    """Return new file text with loc_type set to value. Inserts or replaces."""
    m = FRONTMATTER_RE.match(text)
    assert m, "expected frontmatter"
    fm_body = m.group(1)
    if LOC_TYPE_RE.search(fm_body):
        new_fm = LOC_TYPE_RE.sub(f"loc_type: {value}", fm_body)
    else:
        # Append loc_type as the last frontmatter line. fm_body always ends with \n.
        new_fm = fm_body + f"loc_type: {value}\n"
    return f"---\n{new_fm}---\n" + text[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    counts = {"continent": 0, "country": 0, "region": 0, "skipped": 0,
              "already_set": 0}

    for md, text in all_location_files():
        target = mechanical_loc_type(md)
        if target is None:
            counts["skipped"] += 1
            continue

        existing = None
        fm = read_frontmatter(text)
        if fm:
            m = LOC_TYPE_RE.search(fm)
            if m:
                existing = m.group(1)
        if existing == target:
            counts["already_set"] += 1
            continue
        if existing and not args.overwrite:
            counts["already_set"] += 1
            continue

        new_text = set_loc_type_in_text(text, target)
        counts[target] += 1
        if not args.dry_run:
            md.write_text(new_text, encoding="utf-8")

    print(f"Continents:  {counts['continent']}")
    print(f"Countries:   {counts['country']}")
    print(f"Regions:     {counts['region']}")
    print(f"Already set: {counts['already_set']}")
    print(f"Leaves (phase 2): {counts['skipped']}")
    if args.dry_run:
        print("\n(dry run)")


if __name__ == "__main__":
    sys.exit(main() or 0)
