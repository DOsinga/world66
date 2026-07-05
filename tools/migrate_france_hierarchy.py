#!/usr/bin/env python3
"""
Migrate France content hierarchy to one region level.

Changes:
1. Rename around_paris → ile_de_france
2. Dissolve east/ wrapper → promote alsace, burgundy, champagne, franchecomte, lorraine
3. Dissolve midi/ wrapper:
   - Promote cotedazur, languedoc, provence to france/ level
   - Convert ardeche, basqueregion, cevennes, dordogne, luberon, pyrenees, southern_alps to features
4. Dissolve centre/ wrapper → promote loirevalley, auvergne; keep centre for remainder
5. Move misplaced cities (cannes, frejus → cotedazur)
6. Fix midi/aquitaine slug (Poitiers)
7. Convert alpes/chartreuse and aquitaine/ile_de_r to features
"""

import re
import sys
import shutil
from pathlib import Path

import frontmatter

CONTENT = Path("content")
FRANCE = CONTENT / "europe" / "france"
DRY_RUN = "--dry-run" in sys.argv

moves = []   # (old_path, new_path)
tag_updates = {}  # path → list of tags to add
frontmatter_updates = {}  # path → {key: value}
link_replacements = []  # (old_url_prefix, new_url_prefix)


def plan_move(old_rel, new_rel):
    """Plan a content/ path move."""
    old = CONTENT / old_rel
    new = CONTENT / new_rel
    moves.append((old, new))


def plan_tag(content_path, *tags):
    """Plan adding tags to a file."""
    key = str(content_path)
    tag_updates.setdefault(key, []).extend(tags)


def plan_frontmatter(content_path, **kwargs):
    """Plan frontmatter field updates."""
    key = str(content_path)
    frontmatter_updates.setdefault(key, {}).update(kwargs)


def plan_link(old_prefix, new_prefix):
    """Plan a URL prefix replacement across all France content."""
    link_replacements.append((old_prefix, new_prefix))


# ─── 1. around_paris → ile_de_france ───────────────────────────────────────

plan_move("europe/france/around_paris.md", "europe/france/ile_de_france.md")
plan_move("europe/france/around_paris", "europe/france/ile_de_france")
plan_link("/europe/france/around_paris", "/europe/france/ile_de_france")

# Update frontmatter on new page
plan_frontmatter(FRANCE / "ile_de_france.md", title="Île-de-France")

# ─── 2. east/ → promote sub-regions ───────────────────────────────────────

for sub in ["alsace", "burgundy", "champagne", "franchecomte", "lorraine"]:
    plan_move(f"europe/france/east/{sub}.md", f"europe/france/{sub}.md")
    plan_move(f"europe/france/east/{sub}", f"europe/france/{sub}")
    plan_link(f"/europe/france/east/{sub}", f"/europe/france/{sub}")

# morvan stays inside burgundy, just at the shallower path now
# burgundy/morvan moves with burgundy, already handled above

# east.md gets deleted (it's a wrapper with no parent use after promotion)
plan_move("europe/france/east.md", "__DELETE__")
plan_move("europe/france/east", "__DELETE__")
plan_link("/europe/france/east", "/europe/france")  # catch any residual links

# ─── 3a. midi/ → promote major sub-regions ────────────────────────────────

for sub in ["cotedazur", "languedoc", "provence"]:
    plan_move(f"europe/france/midi/{sub}.md", f"europe/france/{sub}.md")
    plan_move(f"europe/france/midi/{sub}", f"europe/france/{sub}")
    plan_link(f"/europe/france/midi/{sub}", f"/europe/france/{sub}")

# languedoc sub-sub-regions: flatten hautlanguedoc_reg and the_land_of_the_cathars
# They become features at the languedoc level; their cities move up to languedoc
for city in ["fraissesuragout", "st_pons_de_thomieres"]:
    src = f"europe/france/midi/languedoc/hautlanguedoc_reg/{city}"
    plan_move(f"{src}.md", f"europe/france/languedoc/{city}.md")
    if (CONTENT / src).is_dir():
        plan_move(src, f"europe/france/languedoc/{city}")
    plan_tag(FRANCE / "languedoc" / f"{city}.md", "hautlanguedoc_reg")
    plan_link(f"/europe/france/midi/languedoc/hautlanguedoc_reg/{city}",
              f"/europe/france/languedoc/{city}")

# hautlanguedoc_reg itself → feature in languedoc (loc_type already region, change to feature)
plan_move("europe/france/midi/languedoc/hautlanguedoc_reg.md",
          "europe/france/languedoc/hautlanguedoc_reg.md")
plan_frontmatter(FRANCE / "languedoc/hautlanguedoc_reg.md", loc_type="feature")

# the_land_of_the_cathars → feature in languedoc
plan_move("europe/france/midi/languedoc/the_land_of_the_cathars.md",
          "europe/france/languedoc/the_land_of_the_cathars.md")
if (CONTENT / "europe/france/midi/languedoc/the_land_of_the_cathars").is_dir():
    plan_move("europe/france/midi/languedoc/the_land_of_the_cathars",
              "europe/france/languedoc/the_land_of_the_cathars")
plan_frontmatter(FRANCE / "languedoc/the_land_of_the_cathars.md", loc_type="feature")

# ─── 3b. midi/ → convert to features ─────────────────────────────────────

# ardeche → feature in languedoc (1 city: uzes)
plan_move("europe/france/midi/ardeche.md", "europe/france/languedoc/ardeche.md")
plan_frontmatter(FRANCE / "languedoc/ardeche.md", loc_type="feature")
for city in ["uzes"]:
    plan_move(f"europe/france/midi/ardeche/{city}.md", f"europe/france/languedoc/{city}.md")
    if (CONTENT / f"europe/france/midi/ardeche/{city}").is_dir():
        plan_move(f"europe/france/midi/ardeche/{city}", f"europe/france/languedoc/{city}")
    plan_tag(FRANCE / "languedoc" / f"{city}.md", "ardeche")
    plan_link(f"/europe/france/midi/ardeche/{city}", f"/europe/france/languedoc/{city}")
plan_link("/europe/france/midi/ardeche", "/europe/france/languedoc/ardeche")

# basqueregion → feature in aquitaine (4 cities)
plan_move("europe/france/midi/basqueregion.md", "europe/france/aquitaine/basqueregion.md")
plan_frontmatter(FRANCE / "aquitaine/basqueregion.md", loc_type="feature")
for city in ["bayonne", "biarritz", "hendaye", "stjeandeluz"]:
    plan_move(f"europe/france/midi/basqueregion/{city}.md",
              f"europe/france/aquitaine/{city}.md")
    if (CONTENT / f"europe/france/midi/basqueregion/{city}").is_dir():
        plan_move(f"europe/france/midi/basqueregion/{city}",
                  f"europe/france/aquitaine/{city}")
    plan_tag(FRANCE / "aquitaine" / f"{city}.md", "basqueregion")
    plan_link(f"/europe/france/midi/basqueregion/{city}", f"/europe/france/aquitaine/{city}")
plan_link("/europe/france/midi/basqueregion", "/europe/france/aquitaine/basqueregion")

# cevennes → feature in languedoc (3 cities)
plan_move("europe/france/midi/cevennes.md", "europe/france/languedoc/cevennes.md")
plan_frontmatter(FRANCE / "languedoc/cevennes.md", loc_type="feature")
for city in ["ales", "florac", "lepuyenvelay"]:
    plan_move(f"europe/france/midi/cevennes/{city}.md", f"europe/france/languedoc/{city}.md")
    if (CONTENT / f"europe/france/midi/cevennes/{city}").is_dir():
        plan_move(f"europe/france/midi/cevennes/{city}", f"europe/france/languedoc/{city}")
    plan_tag(FRANCE / "languedoc" / f"{city}.md", "cevennes")
    plan_link(f"/europe/france/midi/cevennes/{city}", f"/europe/france/languedoc/{city}")
plan_link("/europe/france/midi/cevennes", "/europe/france/languedoc/cevennes")

# dordogne → feature in aquitaine (11 cities)
plan_move("europe/france/midi/dordogne.md", "europe/france/aquitaine/dordogne.md")
plan_frontmatter(FRANCE / "aquitaine/dordogne.md", loc_type="feature")
for city in [
    "bergerac", "cahors", "domme", "laroquegageac", "les_eyzies_de_taya",
    "perigueux", "pujols", "saintcirqlapopie", "sarlat", "stlivrade", "villeneuvesurlot"
]:
    plan_move(f"europe/france/midi/dordogne/{city}.md",
              f"europe/france/aquitaine/{city}.md")
    if (CONTENT / f"europe/france/midi/dordogne/{city}").is_dir():
        plan_move(f"europe/france/midi/dordogne/{city}",
                  f"europe/france/aquitaine/{city}")
    plan_tag(FRANCE / "aquitaine" / f"{city}.md", "dordogne")
    plan_link(f"/europe/france/midi/dordogne/{city}", f"/europe/france/aquitaine/{city}")
plan_link("/europe/france/midi/dordogne", "/europe/france/aquitaine/dordogne")

# luberon → feature in provence (0 cities)
plan_move("europe/france/midi/luberon.md", "europe/france/provence/luberon.md")
plan_frontmatter(FRANCE / "provence/luberon.md", loc_type="feature")
if (CONTENT / "europe/france/midi/luberon").is_dir():
    plan_move("europe/france/midi/luberon", "europe/france/provence/luberon")
plan_link("/europe/france/midi/luberon", "/europe/france/provence/luberon")

# pyrenees → feature in languedoc (4 cities)
plan_move("europe/france/midi/pyrenees.md", "europe/france/languedoc/pyrenees.md")
plan_frontmatter(FRANCE / "languedoc/pyrenees.md", loc_type="feature")
for city in ["lourdes", "prades", "tarasconsurari", "vernet_les_bains"]:
    plan_move(f"europe/france/midi/pyrenees/{city}.md", f"europe/france/languedoc/{city}.md")
    if (CONTENT / f"europe/france/midi/pyrenees/{city}").is_dir():
        plan_move(f"europe/france/midi/pyrenees/{city}", f"europe/france/languedoc/{city}")
    plan_tag(FRANCE / "languedoc" / f"{city}.md", "pyrenees")
    plan_link(f"/europe/france/midi/pyrenees/{city}", f"/europe/france/languedoc/{city}")
plan_link("/europe/france/midi/pyrenees", "/europe/france/languedoc/pyrenees")

# southern_alps → feature in alpes (1 city: annot)
plan_move("europe/france/midi/southern_alps.md", "europe/france/alpes/southern_alps.md")
plan_frontmatter(FRANCE / "alpes/southern_alps.md", loc_type="feature")
for city in ["annot"]:
    plan_move(f"europe/france/midi/southern_alps/{city}.md", f"europe/france/alpes/{city}.md")
    if (CONTENT / f"europe/france/midi/southern_alps/{city}").is_dir():
        plan_move(f"europe/france/midi/southern_alps/{city}", f"europe/france/alpes/{city}")
    plan_tag(FRANCE / "alpes" / f"{city}.md", "southern_alps")
    plan_link(f"/europe/france/midi/southern_alps/{city}", f"/europe/france/alpes/{city}")
plan_link("/europe/france/midi/southern_alps", "/europe/france/alpes/southern_alps")

# ─── 3c. Direct midi cities ────────────────────────────────────────────────

# ceret → languedoc (Catalan town near Perpignan)
plan_move("europe/france/midi/ceret.md", "europe/france/languedoc/ceret.md")
if (CONTENT / "europe/france/midi/ceret").is_dir():
    plan_move("europe/france/midi/ceret", "europe/france/languedoc/ceret")
plan_link("/europe/france/midi/ceret", "/europe/france/languedoc/ceret")

# midi/aquitaine (slug "aquitaine", actually Poitiers) → france/centre/poitiers
plan_move("europe/france/midi/aquitaine.md", "europe/france/centre/poitiers.md")
plan_frontmatter(FRANCE / "centre/poitiers.md", title="Poitiers")
plan_link("/europe/france/midi/aquitaine", "/europe/france/centre/poitiers")

# ─── 3d. Delete midi wrapper ───────────────────────────────────────────────

plan_move("europe/france/midi.md", "__DELETE__")
# midi/ dir will be empty after all sub-moves; delete
plan_move("europe/france/midi", "__DELETE__")
plan_link("/europe/france/midi", "/europe/france")

# ─── 4. centre/ → promote loirevalley, auvergne ───────────────────────────

for sub in ["loirevalley", "auvergne"]:
    plan_move(f"europe/france/centre/{sub}.md", f"europe/france/{sub}.md")
    plan_move(f"europe/france/centre/{sub}", f"europe/france/{sub}")
    plan_link(f"/europe/france/centre/{sub}", f"/europe/france/{sub}")

# limousin → feature in centre (4 cities)
plan_frontmatter(FRANCE / "centre/limousin.md", loc_type="feature")
# limousin stays in centre — just change loc_type, no file move needed
# But cities inside limousin need to move up to centre
for city in ["chateaudeval", "limoges", "rochebrune", "tulle"]:
    plan_move(f"europe/france/centre/limousin/{city}.md",
              f"europe/france/centre/{city}.md")
    if (CONTENT / f"europe/france/centre/limousin/{city}").is_dir():
        plan_move(f"europe/france/centre/limousin/{city}",
                  f"europe/france/centre/{city}")
    plan_tag(FRANCE / "centre" / f"{city}.md", "limousin")
    plan_link(f"/europe/france/centre/limousin/{city}", f"/europe/france/centre/{city}")

# ─── 5. Misplaced cities: cannes, frejus → cotedazur ─────────────────────

for city, slug in [("Cannes", "cannes"), ("Fréjus", "frejus")]:
    plan_move(f"europe/france/{slug}.md", f"europe/france/cotedazur/{slug}.md")
    if (CONTENT / f"europe/france/{slug}").is_dir():
        plan_move(f"europe/france/{slug}", f"europe/france/cotedazur/{slug}")
    if (CONTENT / f"europe/france/{slug}.jpg").exists():
        plan_move(f"europe/france/{slug}.jpg", f"europe/france/cotedazur/{slug}.jpg")
    plan_link(f"/europe/france/{slug}", f"/europe/france/cotedazur/{slug}")

# ─── 6. alpes/chartreuse → feature ────────────────────────────────────────

plan_frontmatter(FRANCE / "alpes/chartreuse.md", loc_type="feature")
# No cities to move; chartreuse stays in alpes/ dir as a feature

# ─── 7. aquitaine/ile_de_r → feature ──────────────────────────────────────

plan_frontmatter(FRANCE / "aquitaine/ile_de_r.md", loc_type="feature")
# ars_en_r stays inside ile_de_r dir; it's on the island, correct location


# ════════════════════════════════════════════════════════════════════════════
# EXECUTE
# ════════════════════════════════════════════════════════════════════════════

def apply_moves():
    seen_deletes = set()
    for old, new in moves:
        if str(old) == str(new):
            continue  # no-op self-move
        if not old.exists():
            continue  # already moved or doesn't exist
        if str(new).endswith("__DELETE__"):
            if str(old) not in seen_deletes:
                if DRY_RUN:
                    print(f"  DELETE {old}")
                else:
                    if old.is_dir():
                        shutil.rmtree(old)
                    else:
                        old.unlink()
                seen_deletes.add(str(old))
        else:
            new.parent.mkdir(parents=True, exist_ok=True)
            if DRY_RUN:
                print(f"  MOVE {old} → {new}")
            else:
                old.rename(new)


def apply_tag_updates():
    for path_str, new_tags in tag_updates.items():
        path = Path(path_str)
        if not path.exists():
            if DRY_RUN:
                print(f"  TAG (file missing) {path}: +{new_tags}")
            continue
        post = frontmatter.load(str(path))
        existing = post.metadata.get("tags", [])
        if isinstance(existing, str):
            existing = [t.strip() for t in existing.split(",") if t.strip()]
        added = [t for t in new_tags if t not in existing]
        if not added:
            continue
        if DRY_RUN:
            print(f"  TAG {path}: +{added}")
        else:
            post.metadata["tags"] = existing + added
            with open(path, "wb") as f:
                frontmatter.dump(post, f)


def apply_frontmatter_updates():
    for path_str, updates in frontmatter_updates.items():
        path = Path(path_str)
        if not path.exists():
            if DRY_RUN:
                print(f"  FM (file missing) {path}: {updates}")
            continue
        post = frontmatter.load(str(path))
        changed = False
        for k, v in updates.items():
            if post.metadata.get(k) != v:
                if DRY_RUN:
                    print(f"  FM {path}: {k}={repr(v)}")
                post.metadata[k] = v
                changed = True
        if not DRY_RUN and changed:
            with open(path, "wb") as f:
                frontmatter.dump(post, f)


def apply_link_replacements():
    # Find all .md files in france tree and update internal links
    replacements = sorted(link_replacements, key=lambda x: -len(x[0]))
    count = 0
    for md_file in sorted(FRANCE.rglob("*.md")):
        text = md_file.read_text()
        new_text = text
        for old_prefix, new_prefix in replacements:
            new_text = re.sub(
                re.escape(old_prefix) + r'(?=[/\)\s"\'])',
                new_prefix,
                new_text
            )
        if new_text != text:
            count += 1
            if DRY_RUN:
                print(f"  LINKS {md_file}")
            else:
                md_file.write_text(new_text)
    return count


if DRY_RUN:
    print("=== DRY RUN ===\n")
    print("--- MOVES ---")
    apply_moves()
    print("\n--- FRONTMATTER ---")
    apply_frontmatter_updates()
    print("\n--- TAGS ---")
    apply_tag_updates()
    print("\n--- LINKS ---")
    n = apply_link_replacements()
    print(f"({n} files with link updates)")
else:
    print("Applying moves...")
    apply_moves()
    print("Applying frontmatter updates...")
    apply_frontmatter_updates()
    print("Applying tag updates...")
    apply_tag_updates()
    print("Updating links...")
    n = apply_link_replacements()
    print(f"Done. {n} files had link updates.")
    print("\nNext: git add -A content/europe/france && git status")
