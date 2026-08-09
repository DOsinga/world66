#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
SCORES_FILE = DATA_DIR / "latent_label_scores.json"
LOCATIONS_FILE = DATA_DIR / "all_locations.json"
OUT_FILE = DATA_DIR / "steering_scores.json"
DIMENSIONS = ("heritage", "vibrancy", "nature", "off_the_beaten_track")

ALWAYS_INCLUDE = (
    "europe/france/paris",
    "northamerica/unitedstates/newyorkstate/newyork",
    "asia/japan/tokyo",
    "europe/unitedkingdom/england/london",
    "asia/thailand/bangkok",
    "asia/turkey/istanbul",
    "northamerica/mexico/mexicocity",
    "asia/india/maharashtra/mumbai",
    "asia/china/shanghai",
    "asia/china/beijing",
    "europe/germany/berlin",
    "northamerica/unitedstates/illinois/chicago",
    "europe/sweden/stockholm",
)


def load_json(path):
    return json.loads(path.read_text())


def display_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR)
    except ValueError:
        return resolved


def ranked_paths(scores, dimension):
    return [
        path
        for path, _ in sorted(
            scores.items(),
            key=lambda item: item[1][dimension],
            reverse=True,
        )
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=SCORES_FILE)
    parser.add_argument("--locations", type=Path, default=LOCATIONS_FILE)
    parser.add_argument("--out", type=Path, default=OUT_FILE)
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--target-top", type=int, default=50)
    args = parser.parse_args()

    scores = load_json(args.scores)
    locations = {item["path"]: item for item in load_json(args.locations)}

    ranks = {}
    selected = set()
    for dimension in DIMENSIONS:
        for index, path in enumerate(ranked_paths(scores, dimension), start=1):
            ranks.setdefault(path, {})[dimension] = index
            if index <= args.top_n:
                selected.add(path)

    for path in ALWAYS_INCLUDE:
        if path in scores:
            selected.add(path)

    candidates = []
    for path in sorted(selected):
        location = locations[path]
        target_top_50 = {}
        for dimension in DIMENSIONS:
            rank = ranks.get(path, {}).get(dimension)
            if rank is None or rank > args.top_n:
                target_top_50[dimension] = None
            else:
                target_top_50[dimension] = rank <= args.target_top

        candidates.append(
            {
                "path": path,
                "name": location["name"],
                "parent": location["parent"],
                "candidate_for": [
                    dimension
                    for dimension in DIMENSIONS
                    if ranks.get(path, {}).get(dimension, args.top_n + 1) <= args.top_n
                ],
                "model_rank": {
                    dimension: ranks.get(path, {}).get(dimension)
                    for dimension in DIMENSIONS
                },
                "model_scores": {
                    dimension: round(scores[path][dimension], 2)
                    for dimension in DIMENSIONS
                },
                "target_scores": {
                    dimension: round(scores[path][dimension], 1)
                    for dimension in DIMENSIONS
                },
                "target_top_50": target_top_50,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(candidates, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(candidates)} steering candidates to {display_path(args.out)}")


if __name__ == "__main__":
    main()
