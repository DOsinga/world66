#!/usr/bin/env python3
"""Apply round 5 audit findings."""

import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
LOC_TYPE_RE = re.compile(r"^loc_type:[ \t]*(\S+)[ \t]*$", re.MULTILINE)

CHANGES: list[tuple[str, str]] = [
    # --- Features ---
    ("northamerica/unitedstates/california/centralcoast/monterey/bigsur", "feature"),
    ("northamerica/unitedstates/nevada/blackrockcity", "feature"),
    ("europe/spain/galicia/cies_islands", "feature"),
    ("asia/indonesia/java/borobudur", "feature"),
    ("asia/india/maharashtra/ellora", "feature"),
    ("europe/greece/crete/knossos", "feature"),
    ("europe/greece/mistra", "feature"),
    ("europe/france/normandybrittany/montsaintmichel", "feature"),
    ("europe/russia/karelia/kizhi", "feature"),
    ("asia/indonesia/komodo", "feature"),
    ("asia/mongolia/terelj", "feature"),
    ("asia/saudiarabia/madainsalih", "feature"),
    ("asia/iraq/nimrod", "feature"),
    ("europe/croatia/krka_national_park_1", "feature"),
    ("northamerica/costarica/arenal", "feature"),
    ("africa/southafrica/capetown/robbenisland", "feature"),
    ("northamerica/nicaragua/laguna_de_apoyo", "feature"),
    ("africa/morocco/dadesgorge", "feature"),
    ("asia/india/rajasthan/sariskanationalpark", "feature"),
    ("asia/japan/hokkaido/daisetsuzan", "feature"),
    ("europe/spain/canaryislands/lanzarote/miradordelrio", "feature"),
    ("europe/unitedkingdom/england/eastern_england/broads", "feature"),
    ("asia/indonesia/wakatobi", "feature"),
    ("europe/malta/comino", "feature"),
    ("australiaandpacific/tuvalu/nukufetauatoll", "feature"),
    ("australiaandpacific/tuvalu/nukulaelaeatoll", "feature"),
    ("australiaandpacific/tonga/haapaigroup/uoleva", "feature"),
    # --- Regions ---
    ("northamerica/canada/ontario/prince_edward_county", "region"),
    ("europe/croatia/island_solta", "region"),
    ("europe/spain/galicia/o__ribeiro_valley", "region"),
    ("europe/unitedkingdom/wales/pembrokeshire_coast_national_park", "region"),
    ("northamerica/greenland/diskobay", "region"),
    ("northamerica/unitedstates/newyorkstate/niagara_frontier", "region"),
    ("southamerica/chile/valle_de_elqui", "region"),
    ("australiaandpacific/australia/tasmania/westcoast", "region"),
    ("africa/southafrica/winelands", "region"),
    ("europe/romania/blackseacoast", "region"),
    ("asia/vietnam/mekongdelta", "region"),
    ("europe/unitedkingdom/england/leeds_sheffield_and_yorkshire/yorkshire_dales/wharfedale", "region"),
    ("europe/spain/galicia/o_rosal_valley", "region"),
    ("europe/unitedkingdom/wales/gower", "region"),
    ("europe/belgium/east_belgium", "region"),
    ("africa/morocco/dadesvalley", "region"),
    ("australiaandpacific/newzealand/south_island/otago/central_otago", "region"),
    ("australiaandpacific/fiji/vitilevu/coral_coast", "region"),
    ("europe/spain/gipuzkoa", "region"),
    ("europe/spain/costa_brava", "region"),
    ("northamerica/unitedstates/northcarolina/mcdowell_county", "region"),
]


def patch_loc_type(md: Path, target: str) -> str | None:
    text = md.read_text(encoding="utf-8")
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return "no frontmatter"
    body = fm.group(1)
    m = LOC_TYPE_RE.search(body)
    if not m:
        return "no loc_type"
    current = m.group(1)
    if current == target:
        return "already"
    new_body = LOC_TYPE_RE.sub(f"loc_type: {target}", body)
    new_text = f"---\n{new_body}---\n" + text[fm.end():]
    md.write_text(new_text, encoding="utf-8")
    return current


def main():
    counts = {"updated": 0, "already": 0, "missing": 0, "other": 0}
    for path, target in CHANGES:
        md = CONTENT_DIR / f"{path}.md"
        if not md.exists():
            print(f"MISSING {path}", file=sys.stderr)
            counts["missing"] += 1
            continue
        r = patch_loc_type(md, target)
        if r == "already":
            counts["already"] += 1
        elif r in ("no frontmatter", "no loc_type"):
            print(f"SKIP   {path} ({r})", file=sys.stderr)
            counts["other"] += 1
        else:
            counts["updated"] += 1
            print(f"  {path}: {r} -> {target}")
    print()
    for k, v in counts.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    sys.exit(main() or 0)
