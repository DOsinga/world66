#!/usr/bin/env python3
"""
flatten_sections.py — Move POIs out of legacy section subdirectories.

Old structure (wrong):
  city/things_to_do/cafe.md
  city/eating_out/restaurant.md

Correct structure:
  city/cafe.md           (with tags: [things_to_do, bar])
  city/restaurant.md     (with tags: [eating_out, restaurant])

Usage:
  python3 tools/flatten_sections.py [--dry-run] [content_path]

  content_path  Optional subdirectory to limit scope (e.g. content/europe/france/paris)
  --dry-run     Print what would happen without writing files
"""

import argparse
import os
import sys
from pathlib import Path

import frontmatter

SECTION_DIRS = {
    "things_to_do",
    "eating_out",
    "bars_and_cafes",
    "shopping",
    "beaches",
    "sights",
    "museums",
    "nightlife",
    "books",
    "day_trips",
}

SECTION_DIR_TO_TAG = {
    "things_to_do": "things_to_do",
    "sights": "things_to_do",
    "museums": "things_to_do",
    "eating_out": "eating_out",
    "bars_and_cafes": "bars_and_cafes",
    "nightlife": "bars_and_cafes",
    "shopping": "shopping",
    "beaches": "beaches",
    "books": "books",
    "day_trips": "day_trips",
}

SECTION_TITLES = {
    "things_to_do": "Things to Do",
    "eating_out": "Eating Out",
    "bars_and_cafes": "Bars and Cafes",
    "shopping": "Shopping",
    "beaches": "Beaches",
    "books": "Books",
    "day_trips": "Day Trips",
}

stats = {
    "moved": 0,
    "skipped_exists": 0,
    "books_merged": 0,
    "section_files_created": 0,
    "dirs_removed": 0,
}

CONTENT_ROOT: Path = Path("content")  # set in main()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(CONTENT_ROOT))
    except ValueError:
        return str(path)


def write_pm(path: Path, pm: frontmatter.Post, dry_run: bool):
    if dry_run:
        return
    path.write_bytes(frontmatter.dumps(pm).encode())


def ensure_section_file(parent: Path, section_slug: str, dry_run: bool):
    """Create a minimal section .md if one doesn't already exist."""
    section_file = parent / f"{section_slug}.md"
    if section_file.exists():
        return
    canonical = SECTION_DIR_TO_TAG.get(section_slug, section_slug)
    title = SECTION_TITLES.get(canonical, section_slug.replace("_", " ").title())
    pm = frontmatter.Post("", title=title, type="section")
    print(f"  [create] {rel(section_file)}")
    write_pm(section_file, pm, dry_run)
    stats["section_files_created"] += 1


def merge_books(parent: Path, books_dir: Path, dry_run: bool):
    """Fold individual book files into books.md prose."""
    book_files = sorted(books_dir.glob("*.md"))
    if not book_files:
        return

    books_md = parent / "books.md"
    if books_md.exists():
        existing = frontmatter.load(books_md)
        existing_content = existing.content
    else:
        existing = frontmatter.Post("", title="Books", type="section")
        existing_content = ""

    additions = []
    for bf in book_files:
        pm = frontmatter.load(bf)
        title = pm.get("title") or bf.stem.replace("_", " ").title()
        body = pm.content.strip()
        if not body:
            continue
        # Only append if the book title isn't already in books.md
        if title not in existing_content:
            additions.append(f"**{title}** — {body}")
            stats["books_merged"] += 1
            print(f"  [book→prose] {title}")
        else:
            print(f"  [book skip, already present] {title}")

    if additions:
        new_content = existing_content.rstrip()
        if new_content:
            new_content += "\n\n"
        new_content += "\n\n".join(additions)
        existing.content = new_content
        print(f"  [write] {rel(books_md)}")
        write_pm(books_md, existing, dry_run)

    if not dry_run:
        for bf in book_files:
            bf.unlink()


def move_poi(src: Path, dest_dir: Path, section_tag: str, dry_run: bool):
    """Move src to dest_dir/<slug>.md, ensuring section_tag is in tags."""
    dest = dest_dir / src.name
    if dest.exists():
        print(f"  [skip, exists] {src.name}")
        stats["skipped_exists"] += 1
        return

    pm = frontmatter.load(src)
    tags = list(pm.get("tags") or [])
    if section_tag not in tags:
        tags.insert(0, section_tag)
        pm["tags"] = tags

    print(f"  [move] {src.parent.name}/{src.name} → {rel(dest)}")
    write_pm(dest, pm, dry_run)
    stats["moved"] += 1

    if not dry_run:
        src.unlink()


def flatten_location(location_dir: Path, dry_run: bool):
    """Process all section subdirs under a single location directory."""
    found_any = False
    for entry in sorted(location_dir.iterdir()):
        if not entry.is_dir() or entry.name not in SECTION_DIRS:
            continue

        section_slug = entry.name
        section_tag = SECTION_DIR_TO_TAG[section_slug]
        md_files = list(entry.glob("*.md"))
        if not md_files:
            if not dry_run:
                try:
                    entry.rmdir()
                    stats["dirs_removed"] += 1
                except OSError:
                    pass
            continue

        found_any = True
        print(f"\n{location_dir.name}/{section_slug}/  ({len(md_files)} files)")

        if section_slug == "books":
            merge_books(location_dir, entry, dry_run)
        else:
            for md in sorted(md_files):
                move_poi(md, location_dir, section_tag, dry_run)
            ensure_section_file(location_dir, section_tag, dry_run)

        if not dry_run:
            remaining = list(entry.iterdir())
            if not remaining:
                entry.rmdir()
                stats["dirs_removed"] += 1
            else:
                # Non-.md files (images etc.) — move them up too
                for f in remaining:
                    dest = location_dir / f.name
                    if not dest.exists():
                        f.rename(dest)
                try:
                    entry.rmdir()
                    stats["dirs_removed"] += 1
                except OSError:
                    print(f"  [warn] could not remove {entry} — not empty")

    return found_any


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("content_path", nargs="?", default="content", help="Content root or subtree")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    root = Path(args.content_path)
    if not root.exists():
        print(f"Error: {root} does not exist", file=sys.stderr)
        sys.exit(1)

    global CONTENT_ROOT
    CONTENT_ROOT = root

    if args.dry_run:
        print("DRY RUN — no files will be written\n")

    # Walk all directories, process any that have section subdirs
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        # Skip if this dir itself is a section subdir (we process them from their parent)
        if current.name in SECTION_DIRS:
            dirnames.clear()
            continue
        flatten_location(current, args.dry_run)

    print(f"\n{'DRY RUN ' if args.dry_run else ''}Done.")
    print(f"  Moved: {stats['moved']}")
    print(f"  Skipped (already exists at flat level): {stats['skipped_exists']}")
    print(f"  Books merged to prose: {stats['books_merged']}")
    print(f"  Section files created: {stats['section_files_created']}")
    print(f"  Subdirectories removed: {stats['dirs_removed']}")


if __name__ == "__main__":
    main()
