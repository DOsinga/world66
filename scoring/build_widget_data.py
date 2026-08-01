#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
SCORES_FILE = DATA_DIR / "latent_label_scores.json"
REGRESSION_FILE = DATA_DIR / "anchor_score_regression.json"
LOCATIONS_FILE = DATA_DIR / "all_locations.json"
HIDDEN_FILE = DATA_DIR / "all_location_hidden_12.npz"
SCORING_EXPLORER_OUT = PROJECT_DIR / "static" / "widgets" / "scoring-explorer.json"
SCORE_COMPOSER_OUT = PROJECT_DIR / "static" / "widgets" / "score-composer.json"
DIMENSIONS = ("heritage", "vibrancy", "nature", "adventure")


def load_json(path):
    return json.loads(path.read_text())


def composer_defaults(regression):
    coef = regression["coef"]
    defaults = {}
    for index, dimension in enumerate(regression["dimensions"]):
        defaults[dimension] = {
            "bias": round(float(coef[0][index]), 6),
            "weights": [round(float(row[index]), 6) for row in coef[1:]],
            "activation": "linear_clamped",
        }
    return defaults


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=SCORES_FILE)
    parser.add_argument("--regression", type=Path, default=REGRESSION_FILE)
    parser.add_argument("--locations", type=Path, default=LOCATIONS_FILE)
    parser.add_argument("--hidden", type=Path, default=HIDDEN_FILE)
    parser.add_argument("--scoring-explorer-out", type=Path, default=SCORING_EXPLORER_OUT)
    parser.add_argument("--score-composer-out", type=Path, default=SCORE_COMPOSER_OUT)
    args = parser.parse_args()

    scores = load_json(args.scores)
    all_locations = load_json(args.locations)
    first_scores = next(iter(scores.values()))
    dimensions = [dimension for dimension in DIMENSIONS if dimension in first_scores]

    locations = []
    for location in all_locations:
        path = location["path"]
        if path not in scores:
            continue
        score_row = scores[path]
        locations.append(
            {
                "path": path,
                "name": location["name"],
                "parent": location["parent"],
                "url": location["url"],
                "lat": location["lat"],
                "lng": location["lng"],
                **{dimension: score_row[dimension] for dimension in dimensions},
            }
        )

    args.scoring_explorer_out.write_text(
        json.dumps(
            {
                "source": str(args.scores),
                "dimensions": dimensions,
                "locations": locations,
            },
            separators=(",", ":"),
        )
        + "\n"
    )

    if args.regression.exists() and args.hidden.exists():
        regression = load_json(args.regression)
        hidden_data = np.load(args.hidden, allow_pickle=True)
        hidden_by_path = {
            path: row.tolist()
            for path, row in zip(hidden_data["paths"].tolist(), hidden_data["hidden"])
        }
        composer_locations = []
        for location in all_locations:
            path = location["path"]
            if path not in scores or path not in hidden_by_path:
                continue
            composer_locations.append(
                {
                    "path": path,
                    "name": location["name"],
                    "parent": location["parent"],
                    "url": location["url"],
                    "lat": location["lat"],
                    "lng": location["lng"],
                    "hidden": hidden_by_path[path],
                }
            )

        args.score_composer_out.write_text(
            json.dumps(
                {
                    "source": str(args.hidden),
                    "model": str(args.regression),
                    "dimensions": regression["dimensions"],
                    "latentLabels": [f"Latent {index + 1}" for index in range(len(regression["features"]))],
                    "defaults": composer_defaults(regression),
                    "locations": composer_locations,
                },
                separators=(",", ":"),
            )
            + "\n"
        )

    print(f"Wrote {len(locations)} locations to {args.scoring_explorer_out.resolve().relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
