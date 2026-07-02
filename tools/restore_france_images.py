#!/usr/bin/env python3
"""Restore image files deleted during the France hierarchy migration."""

import subprocess
import sys
from pathlib import Path

COMMIT = "7319033d7f"  # migration commit
FRANCE = Path("content/europe/france")

# (old path relative to content/, new path relative to content/)
# Derived from the same migration logic as migrate_france_hierarchy.py
IMAGE_MOVES = [
    # east/ sub-regions promoted
    ("europe/france/east/alsace.jpg",            "europe/france/alsace.jpg"),
    ("europe/france/east/burgundy.jpg",           "europe/france/burgundy.jpg"),
    ("europe/france/east/franchecomte.jpg",       "europe/france/franchecomte.jpg"),

    # midi/cotedazur promoted
    ("europe/france/midi/cotedazur.jpg",          "europe/france/cotedazur.jpg"),
    ("europe/france/midi/cotedazur/cannes.jpg",   "europe/france/cotedazur/cannes.jpg"),

    # midi/languedoc promoted
    ("europe/france/midi/languedoc.jpg",          "europe/france/languedoc.jpg"),

    # midi/provence promoted
    ("europe/france/midi/provence.jpg",           "europe/france/provence.jpg"),

    # ardeche → feature in languedoc
    ("europe/france/midi/ardeche.jpg",            "europe/france/languedoc/ardeche.jpg"),
    ("europe/france/midi/ardeche/uzes.jpg",       "europe/france/languedoc/uzes.jpg"),
    ("europe/france/midi/ardeche/gorgesdutarn.jpg", "europe/france/languedoc/gorgesdutarn.jpg"),

    # basqueregion → feature in aquitaine
    ("europe/france/midi/basqueregion.jpg",       "europe/france/aquitaine/basqueregion.jpg"),
    ("europe/france/midi/basqueregion/bayonne.jpg",    "europe/france/aquitaine/bayonne.jpg"),
    ("europe/france/midi/basqueregion/biarritz.jpg",   "europe/france/aquitaine/biarritz.jpg"),
    ("europe/france/midi/basqueregion/hendaye.jpg",    "europe/france/aquitaine/hendaye.jpg"),
    ("europe/france/midi/basqueregion/stjeandeluz.jpg","europe/france/aquitaine/stjeandeluz.jpg"),

    # cevennes → feature in languedoc
    ("europe/france/midi/cevennes.jpg",           "europe/france/languedoc/cevennes.jpg"),
    ("europe/france/midi/cevennes/ales.jpg",      "europe/france/languedoc/ales.jpg"),
    ("europe/france/midi/cevennes/florac.jpg",    "europe/france/languedoc/florac.jpg"),
    ("europe/france/midi/cevennes/lepuyenvelay.jpg", "europe/france/languedoc/lepuyenvelay.jpg"),

    # dordogne → feature in aquitaine
    ("europe/france/midi/dordogne.jpg",           "europe/france/aquitaine/dordogne.jpg"),
    ("europe/france/midi/dordogne/bergerac.jpg",  "europe/france/aquitaine/bergerac.jpg"),
    ("europe/france/midi/dordogne/cahors.jpg",    "europe/france/aquitaine/cahors.jpg"),
    ("europe/france/midi/dordogne/domme.jpg",     "europe/france/aquitaine/domme.jpg"),
    ("europe/france/midi/dordogne/laroquegageac.jpg", "europe/france/aquitaine/laroquegageac.jpg"),
    ("europe/france/midi/dordogne/les_eyzies_de_taya.jpg", "europe/france/aquitaine/les_eyzies_de_taya.jpg"),
    ("europe/france/midi/dordogne/perigueux.jpg", "europe/france/aquitaine/perigueux.jpg"),
    ("europe/france/midi/dordogne/pujols.jpg",    "europe/france/aquitaine/pujols.jpg"),
    ("europe/france/midi/dordogne/saintcirqlapopie.jpg", "europe/france/aquitaine/saintcirqlapopie.jpg"),
    ("europe/france/midi/dordogne/sarlat.jpg",    "europe/france/aquitaine/sarlat.jpg"),
    ("europe/france/midi/dordogne/villeneuvesurlot.jpg", "europe/france/aquitaine/villeneuvesurlot.jpg"),

    # luberon → feature in provence
    ("europe/france/midi/luberon.jpg",            "europe/france/provence/luberon.jpg"),

    # pyrenees → feature in languedoc
    ("europe/france/midi/pyrenees.jpg",           "europe/france/languedoc/pyrenees.jpg"),
    ("europe/france/midi/pyrenees/lourdes.jpg",   "europe/france/languedoc/lourdes.jpg"),
    ("europe/france/midi/pyrenees/tarasconsurari.jpg", "europe/france/languedoc/tarasconsurari.jpg"),
    ("europe/france/midi/pyrenees/picdumidi.jpg", "europe/france/languedoc/picdumidi.jpg"),

    # southern_alps → feature in alpes
    ("europe/france/midi/southern_alps/annot.jpg", "europe/france/alpes/annot.jpg"),

    # midi/ceret → languedoc
    ("europe/france/midi/ceret.jpg",              "europe/france/languedoc/ceret.jpg"),

    # midi/aquitaine (Poitiers) → centre
    ("europe/france/midi/aquitaine/poitiers.jpg", "europe/france/centre/poitiers.jpg"),

    # verdongorge — restore near provence (it's a Provence gorge POI)
    ("europe/france/midi/verdongorge.jpg",        "europe/france/provence/verdongorge.jpg"),

    # midi image (deleted, no longer needed) — skip
    # midi/camargue.jpg — skip (no camargue page)
]

dry_run = "--dry-run" in sys.argv
restored = 0
skipped = 0

for old_rel, new_rel in IMAGE_MOVES:
    new_path = Path("content") / new_rel

    if new_path.exists():
        print(f"  EXISTS  {new_rel}")
        skipped += 1
        continue

    # Restore from git history (old_rel is already relative to content/)
    git_path = f"content/{old_rel}"
    result = subprocess.run(
        ["git", "show", f"{COMMIT}^:{git_path}"],
        capture_output=True
    )
    if result.returncode != 0:
        print(f"  MISSING {old_rel} (not in git history)")
        skipped += 1
        continue

    if dry_run:
        print(f"  RESTORE {old_rel} → {new_rel}")
        restored += 1
    else:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_bytes(result.stdout)
        print(f"  RESTORED {old_rel} → {new_rel}")
        restored += 1

print(f"\n{'DRY RUN: ' if dry_run else ''}Restored {restored}, skipped {skipped}")
