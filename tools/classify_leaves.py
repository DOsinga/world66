#!/usr/bin/env python3
"""Phase 2 of the loc_type rollout.

Reads tools/non_cities.tsv (a hand-curated list of leaf locations that are
not cities, with their target loc_type) and applies loc_type to every leaf:

  - paths listed in non_cities.tsv get the loc_type from that file
    (feature / region / neighbourhood)
  - every other leaf defaults to loc_type: city

A leaf is a `type: location` page with no child `type: location` files in
its directory. Continents, countries, and non-leaf regions are handled by
set_loc_type.py.

Surgical YAML edits — minimal diffs, no reordering, no reformatting.
"""

import argparse
import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
TSV = Path(__file__).resolve().parent / "non_cities.tsv"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}
VALID_LOC_TYPES = {"city", "region", "feature", "neighbourhood"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
LOC_TYPE_RE = re.compile(r"^loc_type:[ \t]*(\S+)[ \t]*$", re.MULTILINE)
TYPE_RE = re.compile(r"^type:[ \t]*(\S+)[ \t]*$", re.MULTILINE)


def read_frontmatter(text: str) -> str | None:
    m = FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


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


def all_leaf_locations():
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
        if file_type(text) != "location":
            continue
        if has_child_location(md):
            continue
        yield md, text


def load_overrides() -> dict[str, str]:
    overrides: dict[str, str] = {}
    for raw in TSV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        path, loc_type = parts[0].strip(), parts[1].strip()
        if loc_type not in VALID_LOC_TYPES:
            print(f"warning: ignoring invalid loc_type {loc_type!r} for {path}",
                  file=sys.stderr)
            continue
        overrides[path] = loc_type
    return overrides


def set_loc_type_in_text(text: str, value: str) -> str:
    m = FRONTMATTER_RE.match(text)
    assert m
    fm_body = m.group(1)
    if LOC_TYPE_RE.search(fm_body):
        new_fm = LOC_TYPE_RE.sub(f"loc_type: {value}", fm_body)
    else:
        new_fm = fm_body + f"loc_type: {value}\n"
    return f"---\n{new_fm}---\n" + text[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true",
                    help="Replace existing loc_type values where they differ")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    overrides = load_overrides()
    print(f"Loaded {len(overrides)} non-city overrides from {TSV.name}")

    counts = {"city": 0, "region": 0, "feature": 0, "neighbourhood": 0,
              "already_set": 0}
    missing_overrides = set(overrides.keys())

    for md, text in all_leaf_locations():
        rel = str(md.relative_to(CONTENT_DIR).with_suffix(""))
        target = overrides.get(rel, "city")
        missing_overrides.discard(rel)

        fm = read_frontmatter(text)
        existing = None
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

    print(f"Cities:        {counts['city']}")
    print(f"Regions:       {counts['region']}")
    print(f"Features:      {counts['feature']}")
    print(f"Neighbourhoods (loc_type only): {counts['neighbourhood']}")
    print(f"Already set:   {counts['already_set']}")
    if missing_overrides:
        print(f"\n{len(missing_overrides)} paths in non_cities.tsv didn't match any leaf:")
        for path in sorted(missing_overrides):
            print(f"  {path}")
    if args.dry_run:
        print("\n(dry run)")


if __name__ == "__main__":
    sys.exit(main() or 0)
