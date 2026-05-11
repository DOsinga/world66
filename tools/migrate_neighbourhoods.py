#!/usr/bin/env python3
"""Convert `type: location` + `loc_type: neighbourhood` pages into proper
LOCATIONS.md-style neighbourhood POIs.

For each neighbourhood page (e.g. content/.../losangeles/beverlyhills.md):

  1. Find every POI in the neighbourhood's slug directory.
  2. Move each POI up to the parent city's matching section directory
     (losangeles/things_to_do/<poi>.md, etc.), and add the neighbourhood
     slug as a tag so the POI surfaces on the neighbourhood page.
  3. Delete any other files (stub section overviews) and the slug dir.
  4. Rewrite the neighbourhood .md itself:
       type: location  -> type: neighbourhood
       drop loc_type
       ensure `tags: [things_to_do]` (and `neighbourhood` filter tag)

A few neighbourhoods are misplaced — they live under a state file rather
than under a city. RELOCATIONS handles that: move the .md file to the
correct city's directory before running the rest of the migration.

After this script runs, run reclassify_parents.py to flip parents whose
only type: location children were these neighbourhoods (they should now
be loc_type: city instead of region).
"""

import re
import shutil
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
TYPE_RE = re.compile(r"^type:\s*(\S+)\s*$", re.MULTILINE)
LOC_TYPE_LINE_RE = re.compile(r"^loc_type:\s*\S+\s*\n", re.MULTILINE)
TAGS_BLOCK_RE = re.compile(r"^tags:\s*\n((?:- .*\n)+)", re.MULTILINE)
TAGS_INLINE_RE = re.compile(r"^tags:\s*\[(.*?)\]\s*$", re.MULTILINE)

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


def parse_tags(body: str) -> list[str]:
    block = TAGS_BLOCK_RE.search(body)
    if block:
        return [l[2:].strip() for l in block.group(1).splitlines() if l.startswith("- ")]
    inline = TAGS_INLINE_RE.search(body)
    if inline:
        return [s.strip() for s in inline.group(1).split(",") if s.strip()]
    return []


def section_for_poi(text: str) -> str:
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return "things_to_do"
    tags = parse_tags(fm.group(1))
    for t in tags:
        if t in SECTION_TAGS:
            return t
    for t in tags:
        if t in CATEGORY_TO_SECTION:
            return CATEGORY_TO_SECTION[t]
    return "things_to_do"

# Misplaced neighbourhoods: move .md to the correct city first.
RELOCATIONS = {
    "australiaandpacific/australia/newsouthwales/surry_hills":
        "australiaandpacific/australia/newsouthwales/sydney/surry_hills",
    "northamerica/unitedstates/newyorkstate/statenisland":
        "northamerica/unitedstates/newyorkstate/newyork/statenisland",
    "northamerica/unitedstates/california/venice_beach":
        "northamerica/unitedstates/california/losangeles/venice_beach",
}


def file_type(text: str) -> str | None:
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return None
    m = TYPE_RE.search(fm.group(1))
    return m.group(1) if m else None


def add_tag_to_text(text: str, tag: str) -> str:
    """Add tag to a POI's frontmatter `tags:` list. Idempotent."""
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return text
    body = fm.group(1)

    block = TAGS_BLOCK_RE.search(body)
    if block:
        existing = [l[2:].strip() for l in block.group(1).splitlines() if l.startswith("- ")]
        if tag in existing:
            return text
        new_block = block.group(0).rstrip() + f"\n- {tag}\n"
        new_body = body[:block.start()] + new_block + body[block.end():]
        return f"---\n{new_body}---\n" + text[fm.end():]

    inline = TAGS_INLINE_RE.search(body)
    if inline:
        items = [s.strip() for s in inline.group(1).split(",") if s.strip()]
        if tag in items:
            return text
        items.append(tag)
        new_line = f"tags: [{', '.join(items)}]"
        new_body = body[:inline.start()] + new_line + body[inline.end():]
        return f"---\n{new_body}---\n" + text[fm.end():]

    # No tags field — insert before closing ---
    new_body = body + f"tags:\n- {tag}\n"
    return f"---\n{new_body}---\n" + text[fm.end():]


def ensure_neighbourhood_frontmatter(text: str) -> str:
    """Rewrite the neighbourhood's own .md: type -> neighbourhood, drop loc_type,
    ensure tags contain `things_to_do` and `neighbourhood`."""
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return text
    body = fm.group(1)

    body = TYPE_RE.sub("type: neighbourhood", body, count=1)
    body = LOC_TYPE_LINE_RE.sub("", body)

    # Build replacement that has both required tags
    def merge_tag_list(items: list[str]) -> list[str]:
        # Keep existing tags, add the two required ones at the front if absent
        seen = list(items)
        for required in ("neighbourhood", "things_to_do"):
            if required not in seen:
                seen.insert(0, required)
        return seen

    block = TAGS_BLOCK_RE.search(body)
    if block:
        items = [l[2:].strip() for l in block.group(1).splitlines() if l.startswith("- ")]
        items = merge_tag_list(items)
        new_block = "tags:\n" + "".join(f"- {t}\n" for t in items)
        body = body[:block.start()] + new_block + body[block.end():]
    else:
        inline = TAGS_INLINE_RE.search(body)
        if inline:
            items = [s.strip() for s in inline.group(1).split(",") if s.strip()]
            items = merge_tag_list(items)
            new_line = f"tags: [{', '.join(items)}]"
            body = body[:inline.start()] + new_line + body[inline.end():]
        else:
            body = body + "tags:\n- neighbourhood\n- things_to_do\n"

    return f"---\n{body}---\n" + text[fm.end():]


def find_pois(slug_dir: Path) -> list[Path]:
    out: list[Path] = []
    if not slug_dir.is_dir():
        return out
    for f in slug_dir.rglob("*.md"):
        try:
            t = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if file_type(t) == "poi":
            out.append(f)
    return out


def migrate_neighbourhood(nb_md: Path, slug: str, log: list[str]) -> None:
    parent_dir = nb_md.parent  # e.g. content/.../losangeles
    slug_dir = nb_md.parent / nb_md.stem  # e.g. .../losangeles/beverlyhills

    pois = find_pois(slug_dir)

    # 1) Move POIs to parent
    moved, conflicts = 0, 0
    for poi in pois:
        rel = poi.relative_to(slug_dir)  # e.g. things_to_do/somepoi.md or just somepoi.md
        text = poi.read_text(encoding="utf-8")
        if len(rel.parts) >= 2 and rel.parts[0] in SECTION_TAGS:
            # POI is already under a canonical section subdir
            target = parent_dir / rel
        else:
            section = section_for_poi(text)
            target = parent_dir / section / poi.name
        if target.exists():
            log.append(f"  CONFLICT skip: {target.relative_to(CONTENT_DIR)} exists")
            conflicts += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        text = add_tag_to_text(text, slug)
        target.write_text(text, encoding="utf-8")
        poi.unlink()
        moved += 1

    # 2) Remove remaining files in slug_dir (stub section overviews etc.)
    discarded = 0
    if slug_dir.is_dir():
        for f in list(slug_dir.rglob("*")):
            if f.is_file():
                f.unlink()
                discarded += 1
        # Remove empty directories from deepest to shallowest
        for d in sorted(slug_dir.rglob("*"), key=lambda p: -len(p.parts)):
            if d.is_dir():
                d.rmdir()
        slug_dir.rmdir()

    # 3) Rewrite the neighbourhood .md
    text = nb_md.read_text(encoding="utf-8")
    new_text = ensure_neighbourhood_frontmatter(text)
    nb_md.write_text(new_text, encoding="utf-8")

    log.append(f"  POIs moved: {moved}, conflicts: {conflicts}, "
               f"stub files discarded: {discarded}")


def find_neighbourhoods() -> list[Path]:
    out = []
    for md in CONTENT_DIR.rglob("*.md"):
        try:
            t = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = FRONTMATTER_RE.match(t)
        if not fm:
            continue
        body = fm.group(1)
        if "loc_type: neighbourhood" in body and "type: location" in body:
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
    # Also move sibling dir if present
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

    # Step 1: relocate misplaced neighbourhoods to their proper city parent
    relocated_paths: dict[str, Path] = {}
    for old_rel, new_rel in RELOCATIONS.items():
        log.append(f"\n[RELOCATE] {old_rel}")
        new_md = relocate(old_rel, new_rel, log)
        if new_md:
            relocated_paths[old_rel] = new_md

    # Step 2: process every neighbourhood file
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
