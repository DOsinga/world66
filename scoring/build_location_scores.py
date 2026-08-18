#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
FINAL_SCORES_FILE = DATA_DIR / "final_scores.json"
LOCATION_SCORES_OUT = DATA_DIR / "location_scores.json"
RECIPE_OUT = DATA_DIR / "score_recipe.json"
DIMENSIONS = ("heritage", "vibrancy", "nature", "off_the_beaten_track")
COMPONENT_WEIGHTS = {
    "heritage": 1.0,
    "vibrancy": 1.14,
    "nature": 1.02,
    "off_the_beaten_track": 0.72,
}
TOP_COMPONENT_WEIGHT = 3.7
SECOND_COMPONENT_WEIGHT = 1.6


def load_json(path):
    return json.loads(path.read_text())


def display_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR)
    except ValueError:
        return resolved


def raw_score(row):
    weighted = sorted(
        (row[dimension] * COMPONENT_WEIGHTS[dimension] for dimension in DIMENSIONS),
        reverse=True,
    )
    return TOP_COMPONENT_WEIGHT * weighted[0] + SECOND_COMPONENT_WEIGHT * weighted[1]


def max_raw_score():
    weights = sorted(COMPONENT_WEIGHTS.values(), reverse=True)
    return 10 * (TOP_COMPONENT_WEIGHT * weights[0] + SECOND_COMPONENT_WEIGHT * weights[1])


def normalized_score(row):
    return raw_score(row) / max_raw_score() * 10


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=FINAL_SCORES_FILE)
    parser.add_argument("--out", type=Path, default=LOCATION_SCORES_OUT)
    parser.add_argument("--recipe-out", type=Path, default=RECIPE_OUT)
    args = parser.parse_args()

    scores = load_json(args.scores)
    location_scores = {
        path: {
            "score": round(float(normalized_score(row)), 3),
            **{dimension: round(float(row[dimension]), 3) for dimension in DIMENSIONS},
        }
        for path, row in scores.items()
    }
    recipe = {
        "description": "Weighted top-two component score, normalized to 0..10.",
        "source": str(display_path(args.scores)),
        "dimensions": list(DIMENSIONS),
        "component_weights": COMPONENT_WEIGHTS,
        "top_component_weight": TOP_COMPONENT_WEIGHT,
        "second_component_weight": SECOND_COMPONENT_WEIGHT,
        "max_raw_score": round(float(max_raw_score()), 6),
    }

    args.out.write_text(json.dumps(location_scores, indent=2, sort_keys=True) + "\n")
    args.recipe_out.write_text(json.dumps(recipe, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(location_scores)} location scores to {display_path(args.out)}")
    print(f"Wrote score recipe to {display_path(args.recipe_out)}")


if __name__ == "__main__":
    main()
