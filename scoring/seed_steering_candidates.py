#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
SCORES_FILE = DATA_DIR / "latent_label_scores.json"
LOCATIONS_FILE = DATA_DIR / "all_locations.json"
OUT_DIR = DATA_DIR / "steering"
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


def line_for(path, location, scores, dimension, rank):
    return "\t".join(
        [
            path,
            f"{scores[path][dimension]:.3f}",
            str(rank),
            location["name"],
            location["parent"],
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=SCORES_FILE)
    parser.add_argument("--locations", type=Path, default=LOCATIONS_FILE)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()

    scores = load_json(args.scores)
    locations = {item["path"]: item for item in load_json(args.locations)}
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for dimension in DIMENSIONS:
        ranked = ranked_paths(scores, dimension)
        selected = ranked[: args.top_n]
        for path in ALWAYS_INCLUDE:
            if path in scores and path not in selected:
                selected.append(path)

        lines = [
            "# Copy this file to "
            f"{dimension}_out.txt, then reorder/delete/add rows to express the desired top list.",
            "# Format: path<TAB>model_score<TAB>model_rank<TAB>name<TAB>parent",
            "# Only the path is read from *_out.txt; the other columns are for humans.",
            "",
        ]
        rank_by_path = {path: index for index, path in enumerate(ranked, start=1)}
        for path in selected:
            lines.append(line_for(path, locations[path], scores, dimension, rank_by_path[path]))

        out = args.out_dir / f"{dimension}_in.txt"
        out.write_text("\n".join(lines) + "\n")
        print(f"Wrote {len(selected)} {dimension} candidates to {display_path(out)}")


if __name__ == "__main__":
    main()
