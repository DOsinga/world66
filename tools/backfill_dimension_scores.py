#!/usr/bin/env python3
"""
Write the five travel-dimension scores into frontmatter for every scorable
location (loc_type in city/feature/island).

culture/nature/leisure/adventure are computed from static/widgets/
score-composer.json's per-location 12-dim hidden vector and the model's
default linear+clamp regression (the same one the score-composer widget
uses at its default slider positions) — real model output, just applied
once and persisted instead of recomputed client-side on every visit.

city_culture and historic_culture are both set to the culture score.
There is no trained regression that separates them yet (see SCORING.md);
this is a deliberate placeholder until that split exists, not a bug —
re-running this script with a real split formula is all a future fix
needs to do downstream code doesn't know the difference.

Usage:
  tools/backfill_dimension_scores.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

import frontmatter

from scoring_dataset import CONTENT_DIR, CONTINENTS, SCORABLE_LOC_TYPES, content_path_for, load_meta

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCORE_COMPOSER_FILE = PROJECT_DIR / "static" / "widgets" / "score-composer.json"

DIMENSIONS = ("culture", "nature", "leisure", "adventure")


def load_score_data():
    import json

    with open(SCORE_COMPOSER_FILE) as f:
        data = json.load(f)
    defaults = data["defaults"]
    by_path = {loc["path"]: loc["hidden"] for loc in data["locations"]}
    return defaults, by_path


def predict(defaults, hidden):
    scores = {}
    for dim in DIMENSIONS:
        model = defaults[dim]
        value = model["bias"] + sum(w * h for w, h in zip(model["weights"], hidden))
        scores[dim] = round(max(0.0, min(10.0, value)), 1)
    return scores


def run(dry_run=False):
    defaults, hidden_by_path = load_score_data()

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
        hidden = hidden_by_path.get(path)
        if hidden is None:
            skipped_no_data += 1
            print(f"no score data for {path}", file=sys.stderr)
            continue

        scores = predict(defaults, hidden)
        scores["city_culture"] = scores["culture"]
        scores["historic_culture"] = scores["culture"]
        del scores["culture"]

        if dry_run:
            updated += 1
            continue

        post = frontmatter.load(md_file)
        post.metadata.update(scores)
        md_file.write_text(frontmatter.dumps(post, sort_keys=False) + "\n", encoding="utf-8")
        updated += 1

    print(f"Updated: {updated}, skipped (not scorable): {skipped_not_scorable}, "
          f"skipped (no score data): {skipped_no_data}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
