#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
LATENT_LABEL_SCORES = DATA_DIR / "latent_label_scores.json"
LOCATIONS_FILE = DATA_DIR / "all_locations.json"
ANCHORS_OUT = DATA_DIR / "anchors.json"
DIMENSIONS = ("heritage", "vibrancy", "nature", "leisure", "adventure")

ANCHOR_PATHS = [
    "europe/france/paris",
    "northamerica/unitedstates/newyorkstate/newyork",
    "asia/japan/tokyo",
    "europe/unitedkingdom/england/london",
    "europe/italy/lazio/rome",
    "asia/turkey/istanbul",
    "africa/egypt/cairo",
    "asia/thailand/bangkok",
    "africa/nigeria/lagos",
    "northamerica/mexico/mexicocity",
    "europe/germany/berlin",
    "asia/india/maharashtra/mumbai",
    "asia/southkorea/seoul",
    "asia/japan/honshu/kyoto",
    "europe/italy/tuscany/florence",
    "asia/cambodia/angkorwat",
    "asia/uzbekistan/samarkand",
    "asia/india/uttarpradesh/varanasi",
    "northamerica/mexico/teotihuacan",
    "africa/tanzania/serengetinationalpark",
    "africa/uganda/bwindi",
    "northamerica/unitedstates/wyoming/yellowstone",
    "southamerica/ecuador/galapagosislands/theislands",
    "southamerica/argentina/patagonia/torresdelpaine",
    "asia/unitedarabemirates/dubai",
    "northamerica/unitedstates/florida/miami",
    "europe/france/cannes",
    "asia/maldives/male_atoll/male",
    "northamerica/unitedstates/nevada/lasvegas",
    "australiaandpacific/frenchpolynesia/borabora",
    "africa/algeria/djanet",
    "africa/niger/teneredesert",
    "asia/syria/damascus",
    "asia/china/tibet/everest_base_camp",
    "asia/saudiarabia/mecca",
    "northamerica/unitedstates/california/big_sur",
    "northamerica/unitedstates/alaska/denalipark",
    "northamerica/unitedstates/hawaii/maui",
    "europe/italy/veneto/venice",
]


def seeded_scores(scores):
    return {
        dimension: round(scores[dimension], 1)
        for dimension in DIMENSIONS
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-scores", type=Path, default=LATENT_LABEL_SCORES)
    parser.add_argument("--locations", type=Path, default=LOCATIONS_FILE)
    parser.add_argument("--out", type=Path, default=ANCHORS_OUT)
    args = parser.parse_args()

    latent_scores = json.loads(args.latent_scores.read_text())
    locations = json.loads(args.locations.read_text())
    location_by_path = {location["path"]: location for location in locations}

    anchors = []
    for path in ANCHOR_PATHS:
        if path not in latent_scores:
            raise ValueError(f"{path} is missing latent label scores")
        if path not in location_by_path:
            raise ValueError(f"{path} is missing widget metadata")
        location = location_by_path[path]
        anchors.append(
            {
                "path": path,
                "name": location["name"],
                "parent": location["parent"],
                "scores": seeded_scores(latent_scores[path]),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(anchors, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(anchors)} anchors to {args.out.resolve().relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
