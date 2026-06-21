#!/usr/bin/env python3
"""Inspect the flagged region pages and dump structural info per path.

For each path: parent frontmatter (loc_type/title), list of children .md files
with their `type:` and `loc_type:` (and title). Used to decide which children
should be retagged as neighbourhoods.
"""

import json
import sys
from pathlib import Path

import frontmatter

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


def safe_load(p: Path):
    try:
        return frontmatter.load(p)
    except Exception as e:
        return None


def info_for(path: str) -> dict:
    md = CONTENT / f"{path}.md"
    if not md.exists():
        return {"path": path, "exists": False}
    post = safe_load(md)
    parent = {
        "title": (post.metadata.get("title") if post else None),
        "loc_type": (post.metadata.get("loc_type") if post else None),
        "type": (post.metadata.get("type") if post else None),
    }
    children = []
    direct_pois = 0
    direct_locations = 0
    nested_dirs = 0
    child_dir = CONTENT / path
    if child_dir.is_dir():
        for child in sorted(child_dir.iterdir()):
            if child.is_file() and child.suffix == ".md":
                if child.stem == md.stem:
                    continue
                cp = safe_load(child)
                if not cp:
                    continue
                ct = cp.metadata.get("type", "")
                clt = cp.metadata.get("loc_type", "")
                title = cp.metadata.get("title", child.stem)
                has_dir = (child.parent / child.stem).is_dir()
                children.append({
                    "name": child.stem,
                    "title": title,
                    "type": ct,
                    "loc_type": clt,
                    "has_subdir": has_dir,
                })
                if ct == "location":
                    direct_locations += 1
                elif ct == "poi":
                    direct_pois += 1
                if has_dir:
                    nested_dirs += 1
    return {
        "path": path,
        "exists": True,
        "parent": parent,
        "n_children": len(children),
        "n_direct_locations": direct_locations,
        "n_direct_pois": direct_pois,
        "n_nested_dirs": nested_dirs,
        "children": children,
    }


def main():
    out = [info_for(p) for p in PATHS]
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
