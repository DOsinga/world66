#!/usr/bin/env python3
"""For each location-child of the 66 newly-retagged cities, gather the info
needed to classify it as neighbourhood / promote / delete:

  - title
  - score (or None)
  - first paragraph (200 chars)
  - has_subdir (means the child has its own children)
  - n_grandchildren (.md files inside its subdir)
  - n_grandchild_pois, n_grandchild_locations, n_grandchild_features

Output: JSON list to stdout.
"""

import json
import re
import sys
from pathlib import Path

import frontmatter

CONTENT = Path(__file__).resolve().parent.parent / "content"

# The 66 cities we just retagged, taken from apply_city_retag.py.
PARENTS = [
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


def first_para(body: str) -> str:
    body = body.strip()
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        chunk = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", chunk)
        chunk = re.sub(r"\s+", " ", chunk)
        if len(chunk) > 240:
            chunk = chunk[:237].rstrip() + "..."
        return chunk
    return ""


def grandchild_summary(grand_dir: Path) -> dict:
    if not grand_dir.is_dir():
        return {"total": 0, "pois": 0, "locations": 0, "features": 0}
    pois = locs = feats = total = 0
    for f in grand_dir.iterdir():
        if not f.is_file() or f.suffix != ".md":
            continue
        try:
            p = frontmatter.load(f)
        except Exception:
            continue
        total += 1
        t = p.metadata.get("type")
        lt = p.metadata.get("loc_type")
        if t == "poi":
            pois += 1
        elif t == "location":
            if lt == "feature":
                feats += 1
            else:
                locs += 1
    return {"total": total, "pois": pois, "locations": locs, "features": feats}


def main():
    out = []
    for parent_path in PARENTS:
        parent_dir = CONTENT / parent_path
        if not parent_dir.is_dir():
            continue
        for f in sorted(parent_dir.iterdir()):
            if not f.is_file() or f.suffix != ".md":
                continue
            if f.stem == parent_dir.name:
                continue
            try:
                post = frontmatter.load(f)
            except Exception:
                continue
            if post.metadata.get("type") != "location":
                continue
            rel = str(f.relative_to(CONTENT).with_suffix(""))
            grand = grandchild_summary(parent_dir / f.stem)
            out.append({
                "parent": parent_path,
                "path": rel,
                "title": post.metadata.get("title", f.stem),
                "loc_type": post.metadata.get("loc_type"),
                "score": post.metadata.get("score"),
                "snippet": post.metadata.get("snippet") or first_para(post.content),
                "has_subdir": (parent_dir / f.stem).is_dir(),
                "grandchildren": grand,
                "body_len": len(post.content),
            })
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
