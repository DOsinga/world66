#!/usr/bin/env python3
"""Remove inner duplicate location files (e.g. algeria/algeria.md).

The canonical pattern is slug.md next to slug/ directory.
Some locations have an extra slug/slug.md inside. This script
keeps the parent-level file, merging in any richer content or
missing frontmatter from the inner duplicate, then deletes it.
"""

import re
import sys
from pathlib import Path

import yaml

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def parse(p):
    text = p.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if m:
            try:
                meta = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                meta = {}
            return meta, m.group(2).strip()
    return {}, text.strip()


def serialize(meta, body):
    front = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()
    return f"---\n{front}\n---\n\n{body}\n"


def find_pairs(content_dir):
    pairs = []
    for f in sorted(content_dir.rglob("*.md")):
        parent_dir = f.parent
        if parent_dir.name == f.stem:
            grandparent = parent_dir.parent
            sibling = grandparent / f"{f.stem}.md"
            if sibling.is_file():
                pairs.append((sibling, f))
    return pairs


def main():
    dry_run = "--dry-run" in sys.argv
    pairs = find_pairs(CONTENT_DIR)

    if not pairs:
        print("No inner duplicates found.")
        return

    for parent_file, inner_file in pairs:
        parent_meta, parent_body = parse(parent_file)
        inner_meta, inner_body = parse(inner_file)

        # Both should be locations; skip if not
        if parent_meta.get("type") != "location" or inner_meta.get("type") != "location":
            continue

        rel_parent = parent_file.relative_to(CONTENT_DIR)
        rel_inner = inner_file.relative_to(CONTENT_DIR)

        # Use the longer body
        use_inner_body = len(inner_body) > len(parent_body)

        # Merge frontmatter: start with parent, add any keys from inner that parent lacks
        merged_meta = dict(parent_meta)
        added_keys = []
        for k, v in inner_meta.items():
            if k not in merged_meta and v:
                merged_meta[k] = v
                added_keys.append(k)

        changed = use_inner_body or added_keys

        if dry_run:
            status = []
            if use_inner_body:
                status.append(f"body: inner ({len(inner_body)}) > parent ({len(parent_body)})")
            if added_keys:
                status.append(f"added keys: {', '.join(added_keys)}")
            detail = "; ".join(status) if status else "no merge needed"
            print(f"  {rel_inner} -> delete ({detail})")
        else:
            if changed:
                best_body = inner_body if use_inner_body else parent_body
                parent_file.write_text(serialize(merged_meta, best_body), encoding="utf-8")
            inner_file.unlink()
            print(f"  deleted {rel_inner}" + (" (merged)" if changed else ""))

    print(f"\n{'Would process' if dry_run else 'Processed'} {len(pairs)} duplicates.")


if __name__ == "__main__":
    main()
