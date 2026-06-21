#!/usr/bin/env python3
"""Apply round 3 audit findings: flip leaf loc_type values directly."""

import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
LOC_TYPE_RE = re.compile(r"^loc_type:[ \t]*(\S+)[ \t]*$", re.MULTILINE)


CHANGES: list[tuple[str, str]] = [
    # --- chunk 01 ---
    ("asia/india/jammuandkashmir/kashmir", "region"),
    ("asia/turkey/ephesus", "feature"),
    ("northamerica/guatemala/tikal", "feature"),
    ("africa/egypt/sinaidesert", "region"),
    ("europe/italy/campania/pompeii", "feature"),
    ("australiaandpacific/newcaledonia/iledespins", "feature"),
    ("northamerica/unitedstates/northcarolina/outerbanks", "region"),
    ("asia/japan/tokyo/shibuya", "neighbourhood"),
    ("asia/japan/tokyo/roppongi", "neighbourhood"),
    # --- chunk 02 ---
    ("europe/norway/hurtigruten", "feature"),
    # --- chunk 03 ---
    ("asia/israel/golanheights", "region"),
    # --- chunk 04 ---
    ("asia/japan/tokyo/ueno", "neighbourhood"),
    ("europe/italy/liguria/gallinarapark", "feature"),
    ("northamerica/guatemala/pacaya_volcano", "feature"),
    # --- chunk 05 ---
    ("southamerica/chile/cape_horn", "feature"),
    ("northamerica/mexico/yucatan/chichen_itza", "feature"),
    ("europe/montenegro/dormitor", "feature"),
    ("africa/niger/airmountains", "feature"),
    ("southamerica/argentina/patagonia/valdespeninsula", "feature"),
    ("europe/greece/argolis", "region"),
    # --- chunk 06 ---
    ("asia/pakistan/khyberpass", "feature"),
    ("europe/greece/dodona", "feature"),
    ("asia/taiwan/torokogorge", "feature"),
    ("northamerica/unitedstates/montana/bighorncanyon", "feature"),
    ("europe/italy/lazio/ostiaantica", "feature"),
    ("asia/oman/masirahisland", "region"),
    # --- chunk 07 ---
    ("northamerica/panama/panamacanal", "feature"),
    ("australiaandpacific/palau/rockislands", "feature"),
    ("asia/china/hongkong/outlyingislands", "region"),
    # --- chunk 08 ---
    ("southamerica/peru/san_ignacio/santuario_nacional_tabaconas_namballe", "feature"),
    ("europe/netherlands/dehogeveluwe", "feature"),
    ("europe/norway/southernnorways/agder", "region"),
    ("europe/armenia/khorvirap", "feature"),
    ("asia/india/kerala/silent_valley_national_park", "feature"),
    ("northamerica/costarica/cur_national_par", "feature"),
    # --- chunk 09 ---
    ("europe/germany/bavaria/neuschwanstein", "feature"),
    ("africa/reunion/cirquedesalazie", "feature"),
    ("northamerica/unitedstates/pennsylvania/livermore", "feature"),
    ("asia/malaysia/redang", "feature"),
    # --- chunk 10 ---
    ("northamerica/unitedstates/virginia/old_rag_mountain", "feature"),
    ("northamerica/unitedstates/utah/henry_mountains", "feature"),
    ("asia/china/tibet/namtso_lake", "feature"),
    ("northamerica/unitedstates/arkansas/buffaloriver", "feature"),
    ("northamerica/unitedstates/virginia/shenandoah", "region"),
    # --- chunk 11 ---
    ("africa/libya/idehan_murzuq_mur/wadi_matkhandoush", "feature"),
    ("northamerica/unitedstates/oregon/mounthood", "feature"),
    ("europe/iceland/landmannalaugar", "feature"),
    # --- chunk 12 ---
    ("europe/spain/galicia/ria_of_pontevedra", "region"),
    ("europe/ireland/skelligs", "feature"),
    ("africa/southafrica/drakensberg/giants_castle", "feature"),
    ("northamerica/unitedstates/california/sandiego/lajolla", "neighbourhood"),
    ("southamerica/colombia/ciudadperdida", "feature"),
    ("northamerica/unitedstates/alaska/denalipark", "feature"),
    ("europe/unitedkingdom/england/gloucestershire/cotswolds", "region"),
    # --- chunk 14 ---
    ("asia/kazakhstan/sharyn_canyon", "feature"),
    ("asia/china/xinjiangprovince/khunjerabpass", "feature"),
    ("northamerica/unitedstates/colorado/coloradosprings/pikespeak", "feature"),
    ("europe/germany/mecklenburgwesternpomerania/fischland_darss_zingst", "region"),
    ("africa/kenya/nationalparksandreserves/nairobinp", "feature"),
    # --- chunk 17 ---
    ("southamerica/chile/antillanca", "feature"),
    ("northamerica/unitedstates/wyoming/little_america", "feature"),
    ("europe/faroeislands/vidoy", "region"),
    ("northamerica/unitedstates/rhodeisland/block_island", "region"),
    ("europe/faroeislands/eysturoy/elduvik", "neighbourhood"),
    # --- chunk 18 ---
    ("europe/france/midi/southern_alps/train_des_pignes", "feature"),
    # --- chunk 19 ---
    ("northamerica/unitedstates/arizona/knoll_lake", "feature"),
    ("europe/unitedkingdom/wales/anglesey/din_lligwy", "feature"),
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
