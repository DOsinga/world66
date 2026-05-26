#!/usr/bin/env python3
"""Flip `loc_type: region` -> `loc_type: city` on a fixed list of pages.

The list was produced by a five-agent audit of all loc_type:region pages
(see commit history). Each entry was independently judged a single populated
place rather than a multi-place region.

Edits the frontmatter line surgically without re-serialising YAML, so other
keys, comments and ordering are preserved.
"""

import re
import sys
from pathlib import Path

CONTENT = Path(__file__).resolve().parent.parent / "content"

PATHS = [
    "africa/mauritius/souillac",
    "africa/morocco/marrakesh",
    "africa/morocco/rabat",
    "africa/nigeria/yola",
    "africa/southafrica/capetown",
    "asia/china/hongkong",
    "asia/china/macau",
    "asia/china/sichuanprovince/chengdu",
    "asia/india/orissa/berhampur",
    "asia/india/uttaranchal/karanprayag",
    "asia/iraq/arbil",
    "asia/japan/kyushu/kitakyushu",
    "asia/malaysia/melaka",
    "asia/pakistan/abbottabad",
    "asia/pakistan/azad_kashmir/kotli",
    "asia/pakistan/azad_kashmir/mirpur",
    "asia/pakistan/azad_kashmir/rawalacoat",
    "asia/pakistan/dera_ghazi_khan",
    "asia/pakistan/hunzavalley/gojal_valley/hussaini_sisuni",
    "asia/pakistan/peshawar",
    "asia/pakistan/sargodha",
    "asia/pakistan/skardu",
    "asia/philippines/manila",
    "asia/srilanka/tissamaharama",
    "asia/thailand/maehongson",
    "asia/turkey/canakkale",
    "asia/turkey/istanbul",
    "asia/vietnam/hue",
    "europe/albania/saranda",
    "europe/armenia/kotayk_marz/hrazdan",
    "europe/belgium/antwerp",
    "europe/finland/joensuu",
    "europe/france/nord/boulogne",
    "europe/georgia/tbilisi",
    "europe/germany/berlin",
    "europe/ireland/cork",
    "europe/ireland/dublin",
    "europe/ireland/sligo",
    "europe/italy/abruzzo/teramo",
    "europe/italy/calabria/catanzaro",
    "europe/italy/puglia/bari",
    "europe/italy/sicily/piazza_armerina",
    "europe/italy/veneto/padua",
    "europe/norway/oslo",
    "europe/poland/zakopane",
    "europe/russia/krasnodar",
    "europe/spain/catalonia/girona",
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
    "southamerica/peru/chachapoyas",
    "southamerica/peru/huanchaco",
    "southamerica/peru/san_ignacio",
    "southamerica/venezuela/maracaibo",
]


def flip(md_path: Path) -> str:
    """Return 'flipped', 'already-city', 'no-loc_type', or 'no-match'."""
    text = md_path.read_text()
    if not text.startswith("---"):
        return "no-frontmatter"
    end = text.find("\n---", 3)
    if end == -1:
        return "no-frontmatter"
    fm = text[:end]

    if re.search(r"^loc_type:\s*city\s*$", fm, flags=re.MULTILINE):
        return "already-city"

    new_fm, n = re.subn(
        r"^(loc_type:\s*)region(\s*)$",
        r"\1city\2",
        fm,
        flags=re.MULTILINE,
    )
    if n == 0:
        if re.search(r"^loc_type:", fm, flags=re.MULTILINE):
            return "loc_type-not-region"
        return "no-loc_type"
    if n > 1:
        return "multiple-matches"

    md_path.write_text(new_fm + text[end:])
    return "flipped"


def main():
    counts = {}
    for p in PATHS:
        md = CONTENT / f"{p}.md"
        if not md.exists():
            r = "missing"
        else:
            r = flip(md)
        counts[r] = counts.get(r, 0) + 1
        marker = "✓" if r == "flipped" else "·"
        print(f"  {marker} {r:25} {p}")
    print()
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
