#!/usr/bin/env python3
"""Sweep content/ for markdown links pointing at old paths that were promoted
up one directory level, and rewrite them to the new paths.

Derives the (old, new) map by inspecting the git diff: any file currently
git-rm'd at /A/B/C/D.md AND now-present at /A/B/D.md is a promote.
"""

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"


def promote_pairs():
    """Use the snapshot of city-children that were originally classified
    against the live filesystem to derive (old, new) URL pairs for promoted
    items."""
    triage = json.load(open("/tmp/child_triage.json"))
    NEIGHBOURHOODS = {
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
    DELETES = {
        "asia/pakistan/abbottabad/pind_gali",
        "asia/pakistan/azad_kashmir/mirpur/rajoa",
        "asia/pakistan/azad_kashmir/rawalacoat/khaigala",
        "asia/pakistan/dera_ghazi_khan/bahadur_garh",
        "asia/pakistan/dera_ghazi_khan/tibbi_qaisrani",
        "asia/pakistan/dera_ghazi_khan/tibbi_qaisrani_miana",
        "asia/pakistan/sargodha/bhagatawala",
        "europe/finland/joensuu/polvijarvi",
        "europe/unitedkingdom/scotland/glasgow/renfrew",
        "northamerica/unitedstates/nevada/reno/blue_star_cafe",
    }
    pairs = []
    for d in triage:
        if d.get("loc_type") != "city":
            continue
        p = d["path"]
        if p in NEIGHBOURHOODS or p in DELETES:
            continue
        parts = p.split("/")
        if len(parts) < 3:
            continue
        new_parts = parts[:-2] + parts[-1:]
        new_path = "/".join(new_parts)
        old_url = "/" + p
        new_url = "/" + new_path
        # Sanity check: new file should exist on disk after migration
        if (CONTENT / f"{new_path}.md").exists():
            pairs.append((old_url, new_url))
    return pairs


def rewrite_links(pairs):
    if not pairs:
        return 0, 0
    by_old = dict(pairs)
    olds = sorted(by_old.keys(), key=len, reverse=True)
    # Match the old URL as a whole, allowing `/` after for nested links like
    # /losangeles/longbeach/things_to_do/queen_mary -> /longbeach/things_to_do/queen_mary
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(o) for o in olds) + r")(?=/|[^A-Za-z0-9_/])"
    )
    n_files = 0
    n_replacements = 0
    examples = []
    for md in CONTENT.rglob("*.md"):
        text = md.read_text()
        replaced = [0]
        def sub(m):
            replaced[0] += 1
            if len(examples) < 5:
                examples.append((str(md.relative_to(CONTENT)), m.group(0), by_old[m.group(1)]))
            return by_old[m.group(1)]
        new = pattern.sub(sub, text)
        if replaced[0]:
            md.write_text(new)
            n_files += 1
            n_replacements += replaced[0]
    return n_files, n_replacements, examples


def main():
    pairs = promote_pairs()
    print(f"Promote pairs: {len(pairs)}")
    for old, new in pairs[:8]:
        print(f"  {old}  ->  {new}")
    if len(pairs) > 8:
        print(f"  ... and {len(pairs)-8} more")
    n_files, n_repl, ex = rewrite_links(pairs)
    print(f"\nRewrote {n_repl} link occurrences across {n_files} files.")
    for f, before, after in ex:
        print(f"  e.g. {f}: {before!r} -> {after!r}")


if __name__ == "__main__":
    main()
