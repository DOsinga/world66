#!/usr/bin/env python3
"""
Write the four travel-dimension scores into frontmatter for every scorable
location (loc_type in city/feature/island).

Scores come directly from static/widgets/scoring-explorer.json — this PR's
own widget data, already 0-10 per location, no regression/steering math
needed (see scoring/SCORING.md for how that file itself is produced).

Usage:
  scoring/backfill_dimension_scores.py [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

import frontmatter

from sample_locations import CONTENT_DIR, CONTINENTS, DIMENSIONS, SCORABLE_LOC_TYPES, content_path_for, load_meta

PROJECT_DIR = Path(__file__).resolve().parent.parent
WIDGET_DATA_FILE = PROJECT_DIR / "static" / "widgets" / "scoring-explorer.json"


def load_scores():
    with open(WIDGET_DATA_FILE) as f:
        data = json.load(f)
    return {loc["path"]: {dim: loc[dim] for dim in DIMENSIONS} for loc in data["locations"]}


def run(dry_run=False):
    scores_by_path = load_scores()

    updated = 0
    skipped_not_scorable = 0
    skipped_no_data = 0

    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        rel = md_file.relative_to(CONTENT_DIR)
        if not rel.parts or rel.parts[0] not in CONTINENTS:
            continue

        meta = load_meta(md_file)
        if meta.get("type") != "location" or meta.get("loc_type") not in SCORABLE_LOC_TYPES:
            skipped_not_scorable += 1
            continue

        path = content_path_for(md_file)
        scores = scores_by_path.get(path)
        if scores is None:
            skipped_no_data += 1
            print(f"no score data for {path}", file=sys.stderr)
            continue

        rounded = {dim: round(scores[dim], 1) for dim in DIMENSIONS}

        if dry_run:
            updated += 1
            continue

        post = frontmatter.load(md_file)
        post.metadata.update(rounded)
        md_file.write_text(frontmatter.dumps(post, sort_keys=False) + "\n", encoding="utf-8")
        updated += 1

    print(f"Updated: {updated}, skipped (not scorable): {skipped_not_scorable}, "
          f"skipped (no score data): {skipped_no_data}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
