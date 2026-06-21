#!/usr/bin/env python3
"""Update todo/location_enrich batch files after the region→city retag.

Three operations:
  1. Rewrite the 72 promoted paths (old → new) in place.
  2. Remove the 19 paths we deleted or converted to neighbourhoods.
  3. Distribute the 66 newly-retagged-as-city pages across the batches
     that had stale entries removed, so they enter the enrichment pipeline.

Run once. Idempotent on re-run because removed/rewritten paths won't be found.
"""

from __future__ import annotations

import itertools
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TODO_DIR = REPO / "todo" / "location_enrich"

# The 66 pages we retagged region → city (from apply_city_retag.py).
NEW_CITIES = [
    "africa/mauritius/souillac", "africa/morocco/marrakesh", "africa/morocco/rabat",
    "africa/nigeria/yola", "africa/southafrica/capetown", "asia/china/hongkong",
    "asia/china/macau", "asia/china/sichuanprovince/chengdu",
    "asia/india/orissa/berhampur", "asia/india/uttaranchal/karanprayag",
    "asia/iraq/arbil", "asia/japan/kyushu/kitakyushu", "asia/malaysia/melaka",
    "asia/pakistan/abbottabad", "asia/pakistan/azad_kashmir/kotli",
    "asia/pakistan/azad_kashmir/mirpur", "asia/pakistan/azad_kashmir/rawalacoat",
    "asia/pakistan/dera_ghazi_khan",
    "asia/pakistan/hunzavalley/gojal_valley/hussaini_sisuni",
    "asia/pakistan/peshawar", "asia/pakistan/sargodha", "asia/pakistan/skardu",
    "asia/philippines/manila", "asia/srilanka/tissamaharama",
    "asia/thailand/maehongson", "asia/turkey/canakkale", "asia/turkey/istanbul",
    "asia/vietnam/hue", "europe/albania/saranda",
    "europe/armenia/kotayk_marz/hrazdan", "europe/belgium/antwerp",
    "europe/finland/joensuu", "europe/france/nord/boulogne",
    "europe/georgia/tbilisi", "europe/germany/berlin", "europe/ireland/cork",
    "europe/ireland/dublin", "europe/ireland/sligo",
    "europe/italy/abruzzo/teramo", "europe/italy/calabria/catanzaro",
    "europe/italy/puglia/bari", "europe/italy/sicily/piazza_armerina",
    "europe/italy/veneto/padua", "europe/norway/oslo", "europe/poland/zakopane",
    "europe/russia/krasnodar", "europe/spain/catalonia/girona",
    "europe/unitedkingdom/england/south_east/southampton",
    "europe/unitedkingdom/scotland/edinburgh",
    "europe/unitedkingdom/scotland/glasgow",
    "northamerica/canada/britishcolumbia/vancouver",
    "northamerica/canada/britishcolumbia/victoria",
    "northamerica/mexico/guanajuato",
    "northamerica/unitedstates/california/centralcoast/monterey",
    "northamerica/unitedstates/california/losangeles",
    "northamerica/unitedstates/california/napa",
    "northamerica/unitedstates/california/sandiego",
    "northamerica/unitedstates/colorado/coloradosprings",
    "northamerica/unitedstates/florida/pensacola",
    "northamerica/unitedstates/nevada/reno",
    "northamerica/unitedstates/newyorkstate/newyork",
    "northamerica/unitedstates/texas/houston",
    "southamerica/peru/chachapoyas", "southamerica/peru/huanchaco",
    "southamerica/peru/san_ignacio", "southamerica/venezuela/maracaibo",
]

# 19 stale: 10 deleted + 9 became neighbourhoods.
REMOVES = {
    "asia/pakistan/abbottabad/pind_gali_abbottab",
    "asia/pakistan/azad_kashmir/mirpur/rajoa",
    "asia/pakistan/azad_kashmir/rawalacoat/khaigala",
    "asia/pakistan/dera_ghazi_khan/bahadur_garh",
    "asia/pakistan/dera_ghazi_khan/tibbi_qaisrani",
    "asia/pakistan/dera_ghazi_khan/tibbi_qaisranimia_1",
    "asia/pakistan/sargodha/bhagatawala__chak_1",
    "europe/finland/joensuu/polvijrvi",
    "europe/unitedkingdom/scotland/glasgow/renfrew",
    "northamerica/unitedstates/nevada/reno/bluestarcafe",
    "europe/germany/berlin/schoneberg",
    "northamerica/unitedstates/newyorkstate/newyork/brooklyn",
    "europe/unitedkingdom/scotland/edinburgh/stockbridge",
    "europe/italy/puglia/bari/mungivacca",
    "northamerica/unitedstates/california/sandiego/pacificbeach",
    "northamerica/unitedstates/texas/houston/museumdistrict",
    "northamerica/unitedstates/california/losangeles/centurycity",
    "europe/norway/oslo/holmekollen",
    "europe/ireland/cork/ballyvolane",
}

# 72 promoted: same logic as before — drop the second-to-last path element.
def promoted_pairs():
    import json
    triage = json.load(open("/tmp/child_triage.json"))
    pairs = {}
    for d in triage:
        if d.get("loc_type") != "city":
            continue
        p = d["path"]
        if p in REMOVES:
            continue
        parts = p.split("/")
        if len(parts) < 3:
            continue
        new = "/".join(parts[:-2] + parts[-1:])
        pairs[p] = new
    return pairs


def main():
    rewrites = promoted_pairs()
    print(f"Rewrites: {len(rewrites)}")
    print(f"Removes:  {len(REMOVES)}")
    print(f"To add:   {len(NEW_CITIES)}")

    # Pass 1: walk all batches, build dict batch->lines, apply rewrites + removals.
    batches: dict[Path, list[str]] = {}
    batches_with_removal: list[Path] = []
    n_rewrites = 0
    n_removed = 0
    for f in sorted(TODO_DIR.glob("*.txt")):
        original = [l for l in f.read_text().splitlines() if l.strip()]
        new_lines = []
        had_removal = False
        for line in original:
            if line in REMOVES:
                n_removed += 1
                had_removal = True
                continue
            if line in rewrites:
                new_lines.append(rewrites[line])
                n_rewrites += 1
            else:
                new_lines.append(line)
        batches[f] = new_lines
        if had_removal:
            batches_with_removal.append(f)

    print(f"Applied rewrites: {n_rewrites}")
    print(f"Applied removals: {n_removed}")
    print(f"Batches with removals: {len(batches_with_removal)}")

    # Pass 2: distribute NEW_CITIES round-robin across the batches that had
    # something removed. If we have more cities than gaps, just keep adding —
    # those batches will grow past the standard 5/batch.
    cycle = itertools.cycle(batches_with_removal)
    for city in NEW_CITIES:
        target = next(cycle)
        batches[target].append(city)

    # Write back any batch that changed.
    changed = 0
    for f, lines in batches.items():
        original = [l for l in f.read_text().splitlines() if l.strip()]
        if original != lines:
            f.write_text("\n".join(lines) + "\n")
            changed += 1
    print(f"Batches written: {changed}")


if __name__ == "__main__":
    main()
