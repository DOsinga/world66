#!/usr/bin/env python3
"""Delete POI files inside section directories that shadow the section itself.

e.g. sights/sights.md (type: poi) shadows sights.md (type: section).
"""

import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def get_type(p):
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^type:\s*[\"']?(\w+)", text, re.MULTILINE)
    return m.group(1) if m else "unknown"


def find_shadows(content_dir):
    shadows = []
    for f in sorted(content_dir.rglob("*.md")):
        parent_dir = f.parent
        if parent_dir.name == f.stem:
            grandparent = parent_dir.parent
            sibling = grandparent / f"{f.stem}.md"
            if sibling.is_file() and get_type(sibling) == "section":
                shadows.append(f)
    return shadows


def main():
    dry_run = "--dry-run" in sys.argv
    shadows = find_shadows(CONTENT_DIR)

    if not shadows:
        print("No shadow files found.")
        return

    for f in shadows:
        rel = f.relative_to(CONTENT_DIR)
        if dry_run:
            print(f"  would delete {rel}")
        else:
            f.unlink()
            print(f"  deleted {rel}")

    print(f"\n{'Would delete' if dry_run else 'Deleted'} {len(shadows)} files.")


if __name__ == "__main__":
    main()
