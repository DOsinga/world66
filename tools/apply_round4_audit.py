#!/usr/bin/env python3
"""Apply round 4 audit findings."""

import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
LOC_TYPE_RE = re.compile(r"^loc_type:[ \t]*(\S+)[ \t]*$", re.MULTILINE)

CHANGES: list[tuple[str, str]] = [
    # Features
    ("africa/algeria/tipasa", "feature"),
    ("asia/iran/pasargadae", "feature"),
    ("asia/indonesia/sulawesi/togian_islands", "feature"),
    ("southamerica/venezuela/angelfalls", "feature"),
    ("africa/kenya/nationalparksandreserves/mountkenyanp", "feature"),
    ("europe/sweden/gotska_sandn", "feature"),
    ("asia/indonesia/komodo_island", "feature"),
    ("europe/iceland/kjolurroute", "feature"),
    ("asia/india/gujarat/wildlife/girnationalpark", "feature"),
    ("australiaandpacific/newzealand/north_island/northland/te_paki_stream", "feature"),
    ("southamerica/suriname/galibireserve", "feature"),
    ("europe/unitedkingdom/scotland/rattray_head", "feature"),
    ("africa/kenya/lakes/laketurkana", "feature"),
    ("asia/china/sichuanprovince/mount_emei", "feature"),
    ("europe/france/midi/ardeche/gorgesdutarn", "feature"),
    ("africa/centralafricanrepublic/boali", "feature"),
    ("southamerica/suriname/raleighvallen", "feature"),
    ("asia/iraq/ur", "feature"),
    ("europe/netherlands/dezaanseschans", "feature"),
    ("northamerica/unitedstates/michigan/sleepingbear", "feature"),
    ("africa/botswana/tsodilohills", "feature"),
    ("africa/seychelles/arideisland", "feature"),
    ("africa/botswana/lakengami", "feature"),
    ("asia/china/yunnanprovince/lugu_lake", "feature"),
    ("asia/philippines/mindoroisland/sabangbeach", "feature"),
    ("asia/singapore/islands/lazarusisland", "feature"),
    ("southamerica/venezuela/isla_la_blanquilla", "feature"),
    ("europe/hungary/pilis_hills", "feature"),
    ("africa/libya/leptismagna", "feature"),
    ("asia/philippines/bohol/balicasag", "feature"),
    ("europe/iceland/dimmuborgir", "feature"),
    ("africa/egypt/abusimbel", "feature"),
    ("africa/morocco/ouzoud", "feature"),
    ("southamerica/peru/chanchan", "feature"),
    ("europe/unitedkingdom/england/norfolk/the_norfolk_broads", "feature"),
    ("asia/indonesia/tengger_massif", "feature"),
    ("northamerica/unitedstates/nevada/reno/bluelamp", "feature"),
    ("australiaandpacific/newzealand/south_island/otago/milford_sound", "feature"),
    # Regions
    ("australiaandpacific/newzealand/north_island/waikato/coromandel", "region"),
    ("europe/serbiaandmontenegro/bayofkotor", "region"),
    ("australiaandpacific/australia/tasmania/southwest", "region"),
    ("asia/mongolia/arkhangai", "region"),
    ("northamerica/honduras/lamosquitia", "region"),
    ("europe/italy/veneto/valpolicella", "region"),
    ("northamerica/unitedstates/southdakota/blackhills", "region"),
    ("asia/philippines/quezonprovince", "region"),
    ("africa/centralafricanrepublic/dzanga_sangha", "region"),
    ("northamerica/unitedstates/michigan/isle_royale", "feature"),
    ("northamerica/thecaribbean/cuba/cayo_coco", "region"),
    ("northamerica/nicaragua/solentiname_islands", "region"),
    ("australiaandpacific/tuvalu/nuiatoll", "region"),
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
