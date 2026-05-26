#!/usr/bin/env python3
"""Apply the neighbourhood / delete / promote decisions to the 91 city-children
of the recently-retagged cities.

Uses python-frontmatter for safe surgical edits and shutil for file moves.
After running, callers should rewrite any inbound markdown links that pointed
at the old promoted paths.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import frontmatter

CONTENT = Path(__file__).resolve().parent.parent / "content"

NEIGHBOURHOODS = [
    "europe/germany/berlin/schoneberg",
    "northamerica/unitedstates/newyorkstate/newyork/brooklyn",
    "europe/unitedkingdom/scotland/edinburgh/stockbridge",
    "europe/italy/puglia/bari/mungivacca",
    "northamerica/unitedstates/california/sandiego/pacificbeach",
    "northamerica/unitedstates/texas/houston/museumdistrict",
    "northamerica/unitedstates/california/losangeles/centurycity",
    "europe/norway/oslo/holmekollen",
    "europe/ireland/cork/ballyvolane",
]

DELETES = [
    "asia/pakistan/abbottabad/pind_gali_abbottab",
    "asia/pakistan/azad_kashmir/mirpur/rajoa",
    "asia/pakistan/azad_kashmir/rawalacoat/khaigala",
    "asia/pakistan/dera_ghazi_khan/bahadur_garh",
    "asia/pakistan/dera_ghazi_khan/tibbi_qaisrani",
    "asia/pakistan/dera_ghazi_khan/tibbi_qaisranimia_1",
    "asia/pakistan/sargodha/bhagatawala__chak_1",
    "europe/finland/joensuu/polvijrvi",
    "europe/unitedkingdom/scotland/glasgow/renfrew",
    "northamerica/unitedstates/nevada/reno/bluestarcafe",
]

# Everything else listed in PARENTS / triage that is loc_type:city.
# Filled in from /tmp/child_triage.json at runtime.


def load_post(path: Path):
    return frontmatter.load(path)


def save_post(path: Path, post):
    # frontmatter.dump can reflow lists; preserve original keys via surgical
    # writes when possible. Easiest safe path: re-serialise but with sort_keys=False.
    text = frontmatter.dumps(post)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text)


def surgical_type_to_neighbourhood(md: Path):
    """Replace `type: location` with `type: neighbourhood` and drop `loc_type`."""
    text = md.read_text()
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    fm = text[:end]
    new_fm, n1 = re.subn(r"^type:\s*location\s*$", "type: neighbourhood", fm,
                        flags=re.MULTILINE)
    if n1 != 1:
        print(f"  WARN: could not flip type:location on {md}")
        return False
    new_fm, _ = re.subn(r"^loc_type:.*\n", "", new_fm, flags=re.MULTILINE)
    md.write_text(new_fm + text[end:])
    return True


def add_tag(md: Path, tag: str):
    """Append `tag` to the YAML tags list of a POI frontmatter."""
    post = load_post(md)
    tags = post.metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if tag in tags:
        return False
    tags.append(tag)
    post.metadata["tags"] = tags
    save_post(md, post)
    return True


def do_neighbourhood(path: str):
    """Convert a page to a neighbourhood. If it has a subdir, move its POIs up
    to the parent city's directory and tag them with the neighbourhood slug.
    """
    print(f"  NB  {path}")
    md = CONTENT / f"{path}.md"
    subdir = CONTENT / path
    if not md.exists():
        print(f"    SKIP: file missing")
        return
    slug = md.stem
    parent_dir = md.parent

    if subdir.is_dir():
        # Move POI children up, add neighbourhood tag.
        for child in sorted(subdir.iterdir()):
            if not child.is_file() or child.suffix != ".md":
                continue
            try:
                post = frontmatter.load(child)
            except Exception:
                continue
            ctype = post.metadata.get("type")
            if ctype == "poi":
                dest = parent_dir / child.name
                if dest.exists():
                    print(f"    WARN: dest exists {dest}, skipping move")
                    continue
                shutil.move(str(child), str(dest))
                add_tag(dest, slug)
                print(f"    moved POI {child.name} -> parent, tagged with {slug}")
            elif ctype == "section":
                # Section stubs (things_to_do, when_to_go, ...) for the
                # neighbourhood itself — redundant once the page is a
                # neighbourhood. Drop them.
                child.unlink()
                print(f"    deleted section stub {child.name}")
            else:
                # Other types (sub-locations etc.) — leave in place under the
                # neighbourhood subdir so nothing is silently lost; user can
                # inspect later. But we still convert the page.
                print(f"    LEFT-IN-PLACE: {child.name} (type={ctype})")
        # Remove dir if empty.
        try:
            subdir.rmdir()
            print(f"    removed empty {subdir}")
        except OSError:
            print(f"    kept non-empty {subdir}")

    # Flip the page's frontmatter.
    if surgical_type_to_neighbourhood(md):
        print(f"    flipped to type: neighbourhood")


def do_delete(path: str):
    print(f"  DEL {path}")
    md = CONTENT / f"{path}.md"
    subdir = CONTENT / path
    if md.exists():
        md.unlink()
        print(f"    removed {md.name}")
    if subdir.is_dir():
        shutil.rmtree(subdir)
        print(f"    removed subdir {subdir.name}/")


def do_promote(path: str):
    md = CONTENT / f"{path}.md"
    subdir = CONTENT / path
    parts = path.split("/")
    if len(parts) < 3:
        print(f"  PROM SKIP {path}: too shallow")
        return
    # New path: drop the second-to-last element (the wrongly-grouped parent).
    new_parts = parts[:-2] + parts[-1:]
    new_path = "/".join(new_parts)
    new_md = CONTENT / f"{new_path}.md"
    new_subdir = CONTENT / new_path
    if new_md.exists():
        print(f"  PROM COLLISION: {new_md} already exists, SKIPPING {path}")
        return
    print(f"  PROM {path} -> {new_path}")
    shutil.move(str(md), str(new_md))
    if subdir.is_dir():
        if new_subdir.exists():
            print(f"    WARN: dir collision {new_subdir}, copying contents")
            for item in subdir.iterdir():
                shutil.move(str(item), str(new_subdir / item.name))
            subdir.rmdir()
        else:
            shutil.move(str(subdir), str(new_subdir))


def main():
    import json
    triage = json.load(open("/tmp/child_triage.json"))
    city_kids = [d for d in triage if d.get("loc_type") == "city"]

    nb_set = set(NEIGHBOURHOODS)
    del_set = set(DELETES)

    promotes = [d["path"] for d in city_kids
                if d["path"] not in nb_set and d["path"] not in del_set]

    print(f"NEIGHBOURHOODS: {len(NEIGHBOURHOODS)}")
    print(f"DELETES: {len(DELETES)}")
    print(f"PROMOTES: {len(promotes)}")
    print()

    print("Applying NEIGHBOURHOODs...")
    for p in NEIGHBOURHOODS:
        do_neighbourhood(p)

    print("\nApplying DELETEs...")
    for p in DELETES:
        do_delete(p)

    print("\nApplying PROMOTEs...")
    for p in promotes:
        do_promote(p)


if __name__ == "__main__":
    main()
