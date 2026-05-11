#!/usr/bin/env python3
"""Convert `type: location` + `loc_type: neighbourhood` pages into proper
LOCATIONS.md-style neighbourhood POIs.

For each neighbourhood page (e.g. content/.../losangeles/beverlyhills.md):

  1. Find every POI in the neighbourhood's slug directory.
  2. Move each POI up to the parent city directory (flat — section
     membership comes from the POI's `tags` list, not from a subdir,
     per LOCATIONS.md). Ensure the POI has its section tag and the
     neighbourhood slug tag.
  3. Delete any other files (stub section overviews) and the slug dir.
  4. Rewrite the neighbourhood .md itself:
       type: location  -> type: neighbourhood
       drop loc_type
       ensure `tags: [neighbourhood, things_to_do]`

A few neighbourhoods are misplaced — they live under a state file rather
than under a city. RELOCATIONS handles that: move the .md file to the
correct city's directory before running the rest of the migration.
"""

import sys
from pathlib import Path

import frontmatter

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

# Canonical section names. The POI's first matching tag wins.
SECTION_TAGS = {"things_to_do", "eating_out", "bars_and_cafes", "shopping",
                "books", "day_trips", "beaches", "when_to_go",
                "getting_there", "getting_around"}

# Map legacy/category tags to a section. Used only when no canonical
# section tag is present.
CATEGORY_TO_SECTION = {
    "restaurants": "eating_out", "restaurant": "eating_out",
    "bars": "bars_and_cafes", "bar": "bars_and_cafes", "cafe": "bars_and_cafes",
    "nightlife": "bars_and_cafes",
    "shop": "shopping", "shops": "shopping", "market": "shopping",
    "sight": "things_to_do", "sights": "things_to_do",
    "museum": "things_to_do", "museums": "things_to_do",
    "landmark": "things_to_do", "monument": "things_to_do",
    "neighbourhood": "things_to_do", "architecture": "things_to_do",
    "book": "books", "books": "books",
}

# Misplaced neighbourhoods: move .md to the correct city first.
RELOCATIONS = {
    "australiaandpacific/australia/newsouthwales/surry_hills":
        "australiaandpacific/australia/newsouthwales/sydney/surry_hills",
    "northamerica/unitedstates/newyorkstate/statenisland":
        "northamerica/unitedstates/newyorkstate/newyork/statenisland",
    "northamerica/unitedstates/california/venice_beach":
        "northamerica/unitedstates/california/losangeles/venice_beach",
}


def section_for_post(post: frontmatter.Post) -> str:
    tags = list(post.metadata.get("tags", []))
    for t in tags:
        if t in SECTION_TAGS:
            return t
    for t in tags:
        if t in CATEGORY_TO_SECTION:
            return CATEGORY_TO_SECTION[t]
    return "things_to_do"


def ensure_tag(post: frontmatter.Post, tag: str) -> None:
    tags = list(post.metadata.get("tags") or [])
    if tag not in tags:
        tags.append(tag)
    post.metadata["tags"] = tags


def write_post(path: Path, post: frontmatter.Post) -> None:
    path.write_text(frontmatter.dumps(post, sort_keys=False) + "\n",
                    encoding="utf-8")


def find_pois(slug_dir: Path) -> list[tuple[Path, frontmatter.Post]]:
    out = []
    if not slug_dir.is_dir():
        return out
    for f in slug_dir.rglob("*.md"):
        try:
            post = frontmatter.load(f)
        except Exception:
            continue
        if post.metadata.get("type") == "poi":
            out.append((f, post))
    return out


def migrate_neighbourhood(nb_md: Path, slug: str, log: list[str]) -> None:
    parent_dir = nb_md.parent
    slug_dir = nb_md.parent / nb_md.stem

    pois = find_pois(slug_dir)

    moved, conflicts = 0, 0
    for poi_path, poi_post in pois:
        target = parent_dir / poi_path.name
        if target.exists():
            log.append(f"  CONFLICT skip: {target.relative_to(CONTENT_DIR)} exists")
            conflicts += 1
            continue
        ensure_tag(poi_post, slug)
        ensure_tag(poi_post, section_for_post(poi_post))
        write_post(target, poi_post)
        poi_path.unlink()
        moved += 1

    # Discard any remaining files (stub section overviews etc.) and the dir.
    discarded = 0
    if slug_dir.is_dir():
        for f in list(slug_dir.rglob("*")):
            if f.is_file():
                f.unlink()
                discarded += 1
        for d in sorted(slug_dir.rglob("*"), key=lambda p: -len(p.parts)):
            if d.is_dir():
                d.rmdir()
        slug_dir.rmdir()

    # Rewrite the neighbourhood .md itself.
    nb_post = frontmatter.load(nb_md)
    nb_post.metadata["type"] = "neighbourhood"
    nb_post.metadata.pop("loc_type", None)
    tags = list(nb_post.metadata.get("tags") or [])
    for required in ("things_to_do", "neighbourhood"):
        if required not in tags:
            tags.insert(0, required)
    nb_post.metadata["tags"] = tags
    write_post(nb_md, nb_post)

    log.append(f"  POIs moved: {moved}, conflicts: {conflicts}, "
               f"stub files discarded: {discarded}")


def find_neighbourhoods() -> list[Path]:
    out = []
    for md in CONTENT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(md)
        except Exception:
            continue
        if (post.metadata.get("type") == "location"
                and post.metadata.get("loc_type") == "neighbourhood"):
            out.append(md)
    return out


def relocate(old_rel: str, new_rel: str, log: list[str]) -> Path | None:
    old_md = CONTENT_DIR / f"{old_rel}.md"
    new_md = CONTENT_DIR / f"{new_rel}.md"
    if not old_md.exists():
        log.append(f"  RELOCATE skip: {old_md} not found")
        return None
    if new_md.exists():
        log.append(f"  RELOCATE skip: {new_md} already exists")
        return None
    new_md.parent.mkdir(parents=True, exist_ok=True)
    old_md.rename(new_md)
    old_dir = old_md.parent / old_md.stem
    new_dir = new_md.parent / new_md.stem
    if old_dir.is_dir():
        if new_dir.exists():
            log.append(f"  RELOCATE warn: target dir {new_dir} exists, skipping dir")
        else:
            old_dir.rename(new_dir)
    log.append(f"  relocated: {old_rel} -> {new_rel}")
    return new_md


def main():
    log: list[str] = []

    for old_rel, new_rel in RELOCATIONS.items():
        log.append(f"\n[RELOCATE] {old_rel}")
        relocate(old_rel, new_rel, log)

    nbs = find_neighbourhoods()
    log.append(f"\nFound {len(nbs)} neighbourhoods to migrate")
    for nb in sorted(nbs):
        slug = nb.stem
        rel = nb.relative_to(CONTENT_DIR).with_suffix("")
        log.append(f"\n[MIGRATE] {rel}  (slug={slug})")
        migrate_neighbourhood(nb, slug, log)

    print("\n".join(log))


if __name__ == "__main__":
    sys.exit(main() or 0)
