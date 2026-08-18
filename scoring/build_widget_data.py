#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
SCORES_FILE = DATA_DIR / "location_scores.json"
FALLBACK_SCORES_FILE = DATA_DIR / "latent_label_scores.json"
REGRESSION_FILE = DATA_DIR / "steering_layer.json"
LOCATIONS_FILE = DATA_DIR / "all_locations.json"
HIDDEN_FILE = DATA_DIR / "all_location_hidden_12.npz"
SCORING_EXPLORER_OUT = PROJECT_DIR / "static" / "widgets" / "scoring-explorer.json"
SCORE_COMPOSER_OUT = PROJECT_DIR / "static" / "widgets" / "score-composer.json"
DIMENSIONS = ("heritage", "vibrancy", "nature", "off_the_beaten_track")


def load_json(path):
    return json.loads(path.read_text())


def display_path(path):
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_DIR))
    except ValueError:
        return str(resolved)


def composer_defaults(regression):
    weights = regression["weight"]
    bias = regression["bias"]
    defaults = {}
    for index, dimension in enumerate(regression["dimensions"]):
        defaults[dimension] = {
            "bias": round(float(bias[index]), 6),
            "weights": [round(float(row[index]), 6) for row in weights],
            "activation": "sigmoid_0_10",
        }
    return defaults


def fit_ridge(x, y, alpha=25.0):
    x_aug = np.concatenate([np.ones((x.shape[0], 1)), x], axis=1)
    penalty = np.eye(x_aug.shape[1]) * alpha
    penalty[0, 0] = 0
    return np.linalg.solve(x_aug.T @ x_aug + penalty, x_aug.T @ y)


def linear_defaults_from_hidden(hidden_by_path, scores, dimensions):
    paths = [path for path in scores if path in hidden_by_path]
    x = np.array([hidden_by_path[path] for path in paths], dtype=np.float64)
    defaults = {}
    for dimension in dimensions:
        y = np.array([scores[path][dimension] for path in paths], dtype=np.float64)
        coef = fit_ridge(x, y)
        defaults[dimension] = {
            "bias": round(float(coef[0]), 6),
            "weights": [round(float(value), 6) for value in coef[1:]],
            "activation": "linear_clamped",
        }
    return defaults


def write_composer(path, source, model, dimensions, defaults, locations):
    path.write_text(
        json.dumps(
            {
                "source": source,
                "model": model,
                "dimensions": dimensions,
                "latentLabels": [f"Latent {index + 1}" for index in range(12)],
                "defaults": defaults,
                "locations": locations,
            },
            separators=(",", ":"),
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=SCORES_FILE)
    parser.add_argument("--fallback-scores", type=Path, default=FALLBACK_SCORES_FILE)
    parser.add_argument("--regression", type=Path, default=REGRESSION_FILE)
    parser.add_argument("--locations", type=Path, default=LOCATIONS_FILE)
    parser.add_argument("--hidden", type=Path, default=HIDDEN_FILE)
    parser.add_argument("--scoring-explorer-out", type=Path, default=SCORING_EXPLORER_OUT)
    parser.add_argument("--score-composer-out", type=Path, default=SCORE_COMPOSER_OUT)
    args = parser.parse_args()

    scores_path = args.scores if args.scores.exists() else args.fallback_scores
    scores = load_json(scores_path)
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
                **({"score": score_row["score"]} if "score" in score_row else {}),
                **{dimension: score_row[dimension] for dimension in dimensions},
            }
        )

    args.scoring_explorer_out.write_text(
        json.dumps(
            {
                "source": display_path(scores_path),
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

        if "weight" in regression and "bias" in regression:
            defaults = composer_defaults(regression)
            source = display_path(args.hidden)
            model = display_path(args.regression)
        else:
            defaults = linear_defaults_from_hidden(hidden_by_path, scores, regression["dimensions"])
            source = f"linear approximation of {display_path(scores_path)}"
            model = display_path(args.regression)

        write_composer(
            args.score_composer_out,
            source,
            model,
            regression["dimensions"],
            defaults,
            composer_locations,
        )
        print(f"Wrote {len(composer_locations)} locations to {args.score_composer_out.resolve().relative_to(PROJECT_DIR)}")

    print(f"Wrote {len(locations)} locations to {args.scoring_explorer_out.resolve().relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
