#!/usr/bin/env python3
"""
Migrate Italy content hierarchy to one region level (Issue #2083).

Italy keeps exactly the 20 official regions. Tourist areas that were nested
sub-regions become features (loc_type: feature); their cities move up into
the region directory and link back via a tag equal to the feature slug.
Pure administrative wrappers (Florence Province and its sub-areas) dissolve
without a feature. Cross-region lakes move to the italy/ top level so the
tag scan (which is scoped to the feature's parent directory) can see cities
in every region.

Duplicates resolved: lake_garda/lagodigarda, the two rivieradellepalme,
padua/padova, the two Cilento park pages, Amalfi (region -> city, coast
feature from amalfi_coast_excur).

Run with --dry-run first. Prose merges for deleted duplicate pages are done
by hand afterwards (the old text stays available via git show).
"""

import re
import sys
import shutil
from pathlib import Path

import frontmatter

CONTENT = Path("content")
ITALY = CONTENT / "europe" / "italy"
DRY_RUN = "--dry-run" in sys.argv

moves = []  # (old_path, new_path) applied in order
deletes = []  # paths to delete (files or, for dirs, must be empty by then)
tag_updates = {}  # path -> list of tags to add (applied after moves)
frontmatter_updates = {}  # path -> {key: value} (applied after moves)
frontmatter_removals = {}  # path -> [keys] (applied after moves)
link_replacements = []  # (old_url_prefix, new_url_prefix)


def plan_move(old_rel, new_rel):
    moves.append((CONTENT / old_rel, CONTENT / new_rel))


def plan_delete(rel):
    deletes.append(CONTENT / rel)


def plan_tag(content_path, *tags):
    tag_updates.setdefault(str(content_path), []).extend(tags)


def plan_frontmatter(content_path, **kwargs):
    frontmatter_updates.setdefault(str(content_path), {}).update(kwargs)


def plan_frontmatter_remove(content_path, *keys):
    frontmatter_removals.setdefault(str(content_path), []).extend(keys)


def plan_link(old_prefix, new_prefix):
    link_replacements.append((old_prefix, new_prefix))


def write_page(post, path):
    """Write a frontmatter page with the project-standard final newline."""
    path.write_text(frontmatter.dumps(post) + "\n")


def move_page(old_rel, new_rel):
    """Move a page: .md plus its same-slug directory and hero image."""
    plan_move(f"{old_rel}.md", f"{new_rel}.md")
    if (CONTENT / old_rel).is_dir():
        plan_move(old_rel, new_rel)
    if (CONTENT / f"{old_rel}.jpg").exists():
        plan_move(f"{old_rel}.jpg", f"{new_rel}.jpg")
    plan_link(f"/{old_rel}", f"/{new_rel}")


def location_children(wrapper_rel, exclude=()):
    """Slugs of type: location children (.md) of a wrapper dir, at plan time."""
    result = []
    for md in sorted((CONTENT / wrapper_rel).glob("*.md")):
        if md.stem in exclude:
            continue
        post = frontmatter.load(str(md))
        if post.metadata.get("type") == "location":
            result.append(md.stem)
    return result


def promote_children(wrapper_rel, dest_rel, tag=None, exclude=()):
    """Move every location child of wrapper_rel up to dest_rel, tagging it."""
    for slug in location_children(wrapper_rel, exclude):
        move_page(f"{wrapper_rel}/{slug}", f"{dest_rel}/{slug}")
        if tag:
            plan_tag(CONTENT / dest_rel / f"{slug}.md", tag)


IT = "europe/italy"

# ─── Liguria ────────────────────────────────────────────────────────────────

# Cinque Terre: thecinqueterre wrapper -> liguria/cinque_terre feature
CT_OLD = f"{IT}/liguria/italianriviera/thecinqueterre"
promote_children(CT_OLD, f"{IT}/liguria", tag="cinque_terre")  # monterosso, riomaggiore
# corniglia/manarola already exist as city pages at liguria level; the copies
# inside thecinqueterre are POIs -> delete (post-rename paths: deletes run
# after the directory has moved), tag the real pages instead
plan_delete(f"{IT}/liguria/cinque_terre/corniglia.md")
plan_delete(f"{IT}/liguria/cinque_terre/manarola.md")
# vernazza POI is promoted to a city page (frontmatter rewritten by hand after)
plan_move(f"{CT_OLD}/vernazza.md", f"{IT}/liguria/vernazza.md")
for village in ["corniglia", "manarola", "monterosso", "riomaggiore", "vernazza"]:
    plan_tag(ITALY / "liguria" / f"{village}.md", "cinque_terre")
plan_link(f"/{CT_OLD}/corniglia", f"/{IT}/liguria/corniglia")
plan_link(f"/{CT_OLD}/manarola", f"/{IT}/liguria/manarola")
plan_link(f"/{CT_OLD}/vernazza", f"/{IT}/liguria/vernazza")
move_page(CT_OLD, f"{IT}/liguria/cinque_terre")
plan_frontmatter(ITALY / "liguria/cinque_terre.md", loc_type="feature",
                 title="Cinque Terre", image="cinque_terre.jpg")

# Tigullio: wrapper -> liguria/tigullio feature
TIG_OLD = f"{IT}/liguria/italianriviera/tigullio"
promote_children(TIG_OLD, f"{IT}/liguria", tag="tigullio")  # chiavari, lavagna, rapallo
move_page(TIG_OLD, f"{IT}/liguria/tigullio")
plan_frontmatter(ITALY / "liguria/tigullio.md", loc_type="feature")
for city in ["portofino", "sestri_levante"]:
    plan_tag(ITALY / "liguria" / f"{city}.md", "tigullio")

# Paradise Gulf: wrapper -> liguria/paradisegulf feature
PG_OLD = f"{IT}/liguria/italianriviera/paradisegulf"
promote_children(PG_OLD, f"{IT}/liguria", tag="paradisegulf")  # camogli, recco
move_page(PG_OLD, f"{IT}/liguria/paradisegulf")
plan_frontmatter(ITALY / "liguria/paradisegulf.md", loc_type="feature")

# Riviera delle Palme: two duplicate pages. The top-level liguria copy stays
# as the feature; the nested copy's towns and section POIs merge into it.
RP_OLD = f"{IT}/liguria/italianriviera/rivieradellepalme"
RP_NEW = f"{IT}/liguria/rivieradellepalme"
promote_children(RP_OLD, f"{IT}/liguria", tag="rivieradellepalme")
promote_children(RP_NEW, f"{IT}/liguria", tag="rivieradellepalme")
# remaining non-location files in the nested dir join the surviving feature dir
for md in sorted((CONTENT / RP_OLD).glob("*.md")):
    post = frontmatter.load(str(md))
    if post.metadata.get("type") == "location":
        continue
    if (CONTENT / RP_NEW / md.name).exists():
        plan_delete(f"{RP_OLD}/{md.name}")  # food.md, museums.md: keep top-level copy
    else:
        plan_move(f"{RP_OLD}/{md.name}", f"{RP_NEW}/{md.name}")
plan_delete(f"{RP_OLD}.md")  # prose merged by hand into the surviving page
plan_delete(RP_OLD)
plan_link(f"/{RP_OLD}", f"/{RP_NEW}")
plan_frontmatter(ITALY / "liguria/rivieradellepalme.md", loc_type="feature")

# Italian Riviera itself: promote its direct city children, keep the page as
# a feature in place (its dir keeps only section files). The sub-wrappers are
# type: location too and are handled above — exclude them.
promote_children(f"{IT}/liguria/italianriviera", f"{IT}/liguria", tag="italianriviera",
                 exclude=("thecinqueterre", "tigullio", "paradisegulf",
                          "rivieradellepalme"))
plan_frontmatter(ITALY / "liguria/italianriviera.md", loc_type="feature")
for city in ["dianomarina", "imperia"]:
    plan_tag(ITALY / "liguria" / f"{city}.md", "italianriviera")

# Ligurian valleys: features in place
promote_children(f"{IT}/liguria/nerviavalley", f"{IT}/liguria", tag="nerviavalley")
for slug in ["nerviavalley", "trebbiavalley", "varatellavalley", "finalevalley",
             "imperovalley", "scriviavalley", "varavalley"]:
    plan_frontmatter(ITALY / "liguria" / f"{slug}.md", loc_type="feature")

# ─── Tuscany ────────────────────────────────────────────────────────────────

FP = f"{IT}/tuscany/florenceprovince"

# Chianti: chiantiregion -> tuscany/chianti feature
promote_children(f"{FP}/chiantiregion", f"{IT}/tuscany", tag="chianti")
move_page(f"{FP}/chiantiregion", f"{IT}/tuscany/chianti")
plan_frontmatter(ITALY / "tuscany/chianti.md", loc_type="feature", title="Chianti",
                 image="chianti.jpg")

# Mugello: merge mugelloarea + altomugelloarea -> tuscany/mugello feature
promote_children(f"{FP}/mugelloarea", f"{IT}/tuscany", tag="mugello")
promote_children(f"{FP}/altomugelloarea", f"{IT}/tuscany", tag="mugello")
move_page(f"{FP}/mugelloarea", f"{IT}/tuscany/mugello")
plan_frontmatter(ITALY / "tuscany/mugello.md", loc_type="feature", title="Mugello",
                 image="mugello.jpg")
plan_delete(f"{FP}/altomugelloarea.md")  # prose merged by hand into mugello.md
plan_delete(f"{FP}/altomugelloarea")
plan_link(f"/{FP}/altomugelloarea", f"/{IT}/tuscany/mugello")

# Administrative wrappers: dissolve, cities move up untagged
for wrapper in ["florentinearea", "empolesevaldelsa", "sievevalley", "valdarnosuperiore"]:
    promote_children(f"{FP}/{wrapper}", f"{IT}/tuscany")
    plan_delete(f"{FP}/{wrapper}.md")
    if (CONTENT / FP / wrapper).is_dir():
        plan_delete(f"{FP}/{wrapper}")
    if (CONTENT / FP / f"{wrapper}.jpg").exists():
        plan_delete(f"{FP}/{wrapper}.jpg")
    plan_link(f"/{FP}/{wrapper}", f"/{IT}/tuscany")
plan_delete(f"{FP}.md")
plan_delete(FP)
plan_link(f"/{FP}", f"/{IT}/tuscany")

# Elba and Lunigiana: features in place
promote_children(f"{IT}/tuscany/elba", f"{IT}/tuscany", tag="elba")
plan_frontmatter(ITALY / "tuscany/elba.md", loc_type="feature")
plan_frontmatter(ITALY / "tuscany/lunigiana.md", loc_type="feature")

# ─── Lakes (cross-region -> italy/ top level) ───────────────────────────────

# Lake Garda: lagodigarda region dissolves into the enriched lake_garda feature
LG_OLD = f"{IT}/lombardia/lagodigarda"
for city, region in [("sirmione", "lombardia"), ("gardone", "lombardia"),
                     ("salo", "lombardia"), ("lazise", "veneto"),
                     ("peschiera", "veneto")]:
    move_page(f"{LG_OLD}/{city}", f"{IT}/{region}/{city}")
    plan_tag(ITALY / region / f"{city}.md", "lake_garda")
# duplicates of POIs that already live under the city pages
plan_delete(f"{LG_OLD}/scaligero_castle_sirmione.md")
plan_delete(f"{LG_OLD}/vittoriale.md")
plan_delete(f"{LG_OLD}/things_to_do.md")
plan_delete(f"{LG_OLD}.md")  # prose merged by hand into lake_garda.md
plan_delete(f"{LG_OLD}.jpg")
plan_delete(LG_OLD)
plan_link(f"/{LG_OLD}", f"/{IT}/lake_garda")

move_page(f"{IT}/lombardia/lake_garda/riva_del_garda", f"{IT}/trentinoaltoadige/riva_del_garda")
plan_tag(ITALY / "trentinoaltoadige/riva_del_garda.md", "lake_garda")
move_page(f"{IT}/lombardia/lake_garda", f"{IT}/lake_garda")
# POI duplicates of pages under the town dirs (post-rename paths); links to
# them are pointed at the surviving copies
for poi in ["sirmione.md", "scaligero_castle_sirmione.md", "grotte_di_catullo.md",
            "vittoriale_degli_italiani.md"]:
    plan_delete(f"{IT}/lake_garda/{poi}")
for dup_dir in ["lombardia/lake_garda", "lombardia/lagodigarda"]:
    plan_link(f"/{IT}/{dup_dir}/scaligero_castle_sirmione",
              f"/{IT}/lombardia/sirmione/rocca_scaligera")
plan_link(f"/{IT}/lombardia/lake_garda/grotte_di_catullo",
          f"/{IT}/lombardia/sirmione/grotte_di_catullo")
plan_link(f"/{IT}/lombardia/lake_garda/vittoriale_degli_italiani",
          f"/{IT}/lombardia/gardone/vittoriale_degli_italiani")
plan_link(f"/{IT}/lombardia/lagodigarda/vittoriale",
          f"/{IT}/lombardia/gardone/vittoriale_degli_italiani")
plan_link(f"/{IT}/lombardia/lake_garda/sirmione", f"/{IT}/lombardia/sirmione")

# Lake Maggiore: rename to the English slug, feature at top level
move_page(f"{IT}/lombardia/lagomaggiore", f"{IT}/lake_maggiore")
plan_frontmatter(ITALY / "lake_maggiore.md", loc_type="feature", title="Lake Maggiore",
                 image="lake_maggiore.jpg")
plan_tag(ITALY / "piemonte/stresa.md", "lake_maggiore")

# Dolomites: feature already exists at top level; attach the obvious towns
for region, city in [("veneto", "cortina_dampezzo"), ("veneto", "san_vito_di_cadore"),
                     ("veneto", "borca_di_cadore"), ("veneto", "vodo_di_cadore")]:
    plan_tag(ITALY / region / f"{city}.md", "dolomites")

# ─── Campania ───────────────────────────────────────────────────────────────

# Amalfi Coast feature from the old excursion page
move_page(f"{IT}/amalfi_coast_excur", f"{IT}/campania/amalfi_coast")
plan_frontmatter(ITALY / "campania/amalfi_coast.md", title="Amalfi Coast")
plan_frontmatter_remove(ITALY / "campania/amalfi_coast.md", "tags")

AM = f"{IT}/campania/amalfi"
# coast-wide POIs move to the feature dir; town/villa duplicates are deleted
for poi in ["amalfi_drive.md", "atrani.md", "path_of_the_gods.md",
            "santa_maria_del_bando.md"]:
    plan_move(f"{AM}/{poi}", f"{IT}/campania/amalfi_coast/{poi}")
    plan_link(f"/{AM}/{poi[:-3]}", f"/{IT}/campania/amalfi_coast/{poi[:-3]}")
for dup in ["positano.md", "ravello.md", "villa_cimbrone.md", "villa_rufolo.md"]:
    plan_delete(f"{AM}/{dup}")
plan_link(f"/{AM}/villa_cimbrone", f"/{IT}/campania/ravello/villa_cimbrone")
plan_link(f"/{AM}/villa_rufolo", f"/{IT}/campania/ravello/villa_rufolo")
plan_link(f"/{AM}/positano", f"/{IT}/campania/positano")
plan_link(f"/{AM}/ravello", f"/{IT}/campania/ravello")
move_page(f"{AM}/furore", f"{IT}/campania/furore")
plan_tag(ITALY / "campania/furore.md", "amalfi_coast")
plan_frontmatter(ITALY / "campania/amalfi.md", loc_type="city")
for city in ["amalfi", "positano", "ravello"]:
    plan_tag(ITALY / "campania" / f"{city}.md", "amalfi_coast")

# Ischia: feature in place
promote_children(f"{IT}/campania/ischia", f"{IT}/campania", tag="ischia")
plan_frontmatter(ITALY / "campania/ischia.md", loc_type="feature")

# Cilento park duplicate: keep the legacy slug
plan_delete(f"{IT}/campania/parco_nazionale_del_cilento_e_del_vallo_di_diano.md")
plan_link(f"/{IT}/campania/parco_nazionale_del_cilento_e_del_vallo_di_diano",
          f"/{IT}/campania/parcodelcilento")

# ─── Sardinia, Sicily, Trentino, Veneto, Calabria ───────────────────────────

for wrapper, region in [("costasmeralda", "sardinia"), ("isoladisanpietro", "sardinia"),
                        ("aeolianislands", "sicily"), ("pelagianislands", "sicily")]:
    promote_children(f"{IT}/{region}/{wrapper}", f"{IT}/{region}", tag=wrapper)
    plan_frontmatter(ITALY / region / f"{wrapper}.md", loc_type="feature")

promote_children(f"{IT}/trentinoaltoadige/val_di_fassa", f"{IT}/trentinoaltoadige",
                 tag="val_di_fassa")
plan_frontmatter(ITALY / "trentinoaltoadige/val_di_fassa.md", loc_type="feature")
plan_tag(ITALY / "trentinoaltoadige/canazei.md", "dolomites")

for slug in ["valpolicella", "lessinia", "bassoveronese"]:
    plan_frontmatter(ITALY / "veneto" / f"{slug}.md", loc_type="feature")

# Hilltowns of the Savuto: fix the truncated slug, convert to feature
move_page(f"{IT}/calabria/hilltowns_of_the", f"{IT}/calabria/hilltowns_of_the_savuto")
plan_frontmatter(ITALY / "calabria/hilltowns_of_the_savuto.md", loc_type="feature",
                 title="Hilltowns of the Savuto")

# ─── Padua/Padova duplicate ─────────────────────────────────────────────────

PADOVA = f"{IT}/veneto/padova"
for poi in ["museo_civico.md", "palazzo_zuckermann.md"]:
    plan_move(f"{PADOVA}/{poi}", f"{IT}/veneto/padua/{poi}")
for md in sorted((CONTENT / PADOVA).glob("*.md")):
    if md.name not in ("museo_civico.md", "palazzo_zuckermann.md"):
        plan_delete(f"{PADOVA}/{md.name}")
plan_delete(f"{PADOVA}.md")
plan_delete(f"{PADOVA}.jpg")
plan_delete(PADOVA)
# POIs whose slug differs between the two trees
for old, new in [("scrovegni_chapel", "scrovegnichapel"),
                 ("basilica_santantonio", "basilica_di_sant_antonio"),
                 ("eremitani_church", "eremitani"),
                 ("padova_cathedral", "padua_cathedral")]:
    plan_link(f"/{PADOVA}/{old}", f"/{IT}/veneto/padua/{new}")
plan_link(f"/{PADOVA}", f"/{IT}/veneto/padua")


# ════════════════════════════════════════════════════════════════════════════
# EXECUTE
# ════════════════════════════════════════════════════════════════════════════

def count_md():
    return sum(1 for _ in ITALY.rglob("*.md"))


def apply_moves():
    for old, new in moves:
        if not old.exists():
            print(f"  WARNING missing source: {old}")
            continue
        if new.exists():
            raise SystemExit(f"COLLISION: {old} -> {new} (destination exists)")
        new.parent.mkdir(parents=True, exist_ok=True)
        if DRY_RUN:
            print(f"  MOVE {old} -> {new}")
        else:
            old.rename(new)


def apply_deletes():
    # Deletes run after moves and may reference post-move paths, so existence
    # and dir-emptiness can only be validated on a real run.
    n = 0
    for path in deletes:
        if path.suffix == ".md":
            n += 1
        if DRY_RUN:
            print(f"  DELETE {path}")
            continue
        if not path.exists():
            raise SystemExit(f"MISSING DELETE TARGET: {path}")
        if path.is_dir():
            leftover = list(path.rglob("*"))
            if leftover:
                raise SystemExit(f"DIR NOT EMPTY: {path} still has {leftover[:5]}")
            path.rmdir()
        else:
            path.unlink()
    return n


def apply_tag_updates():
    for path_str, new_tags in tag_updates.items():
        path = Path(path_str)
        if not path.exists():
            print(f"  WARNING tag target missing: {path} +{new_tags}")
            continue
        post = frontmatter.load(str(path))
        existing = post.metadata.get("tags", [])
        if isinstance(existing, str):
            existing = [t.strip() for t in existing.split(",") if t.strip()]
        added = [t for t in dict.fromkeys(new_tags) if t not in existing]
        if not added:
            continue
        if DRY_RUN:
            print(f"  TAG {path}: +{added}")
        else:
            post.metadata["tags"] = existing + added
            write_page(post, path)


def apply_frontmatter_updates():
    for path_str, updates in frontmatter_updates.items():
        path = Path(path_str)
        if not path.exists():
            print(f"  WARNING fm target missing: {path} {updates}")
            continue
        post = frontmatter.load(str(path))
        changed = False
        for k, v in updates.items():
            if post.metadata.get(k) != v:
                if DRY_RUN:
                    print(f"  FM {path}: {k}={v!r}")
                post.metadata[k] = v
                changed = True
        for k in frontmatter_removals.get(path_str, []):
            if k in post.metadata:
                if DRY_RUN:
                    print(f"  FM {path}: -{k}")
                del post.metadata[k]
                changed = True
        if not DRY_RUN and changed:
            write_page(post, path)


def apply_link_replacements():
    replacements = sorted(link_replacements, key=lambda x: -len(x[0]))
    count = 0
    for md_file in sorted(CONTENT.rglob("*.md")):
        text = md_file.read_text()
        new_text = text
        for old_prefix, new_prefix in replacements:
            new_text = re.sub(
                re.escape(old_prefix) + r'(?=[/\)\s"\'])',
                new_prefix,
                new_text,
            )
            # linked_locations entries in section frontmatter use the same
            # paths without the leading slash
            new_text = re.sub(
                r'(?<=[\s"\'])' + re.escape(old_prefix[1:]) + r'(?=[/\)\s"\'])',
                new_prefix[1:],
                new_text,
            )
        if new_text != text:
            count += 1
            if DRY_RUN:
                print(f"  LINKS {md_file}")
            else:
                md_file.write_text(new_text)
    return count


def audit_regions():
    region_files = []
    for md in ITALY.rglob("*.md"):
        post = frontmatter.load(str(md))
        if post.metadata.get("loc_type") == "region":
            region_files.append(md)
    print(f"\nloc_type: region files under italy: {len(region_files)}")
    nested = [p for p in region_files if p.parent != ITALY]
    for p in nested:
        print(f"  STILL NESTED: {p}")
    return len(region_files), len(nested)


before = count_md()
planned_md_deletes = sum(1 for p in deletes if p.suffix == ".md")
print(f"{'DRY RUN' if DRY_RUN else 'APPLYING'}: {len(moves)} moves, "
      f"{len(deletes)} deletes ({planned_md_deletes} .md), "
      f"{len(tag_updates)} tag targets, {len(frontmatter_updates)} fm targets, "
      f"{len(link_replacements)} link rules")

print("\n--- MOVES ---"); apply_moves()
print("\n--- DELETES ---"); deleted_md = apply_deletes()
print("\n--- FRONTMATTER ---"); apply_frontmatter_updates()
print("\n--- TAGS ---"); apply_tag_updates()
print("\n--- LINKS ---"); n = apply_link_replacements()
print(f"({n} files with link updates)")

if not DRY_RUN:
    after = count_md()
    # amalfi_coast_excur.md moved out of italy/ scope? no — stays under italy/
    print(f"\n.md accounting: before={before} after={after} deleted={deleted_md}")
    if before != after + deleted_md:
        raise SystemExit("FILE COUNT MISMATCH — investigate before committing!")
    # remove wrapper dirs that emptied out entirely (feature pages need no dir)
    for d in sorted(ITALY.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            print(f"  RMDIR (emptied) {d}")
            d.rmdir()
    total, nested = audit_regions()
    if total != 20 or nested:
        raise SystemExit("REGION AUDIT FAILED — expected exactly 20 top-level regions")
    print("OK: 20 top-level regions, no nested regions, file count consistent.")
