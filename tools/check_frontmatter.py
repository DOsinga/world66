#!/usr/bin/env python3
"""
Validate YAML frontmatter across all content files.

Walks content/ and tries to parse each markdown file with python-frontmatter.
Reports any file that fails to parse, with the parser's error message.

With --fix, applies known mechanical repairs:
  1. image_attribution values containing HTML with unescaped inner double
     quotes — rewrites as single-quoted YAML (collapsing multi-line values
     to a single line).
  2. Duplicate image_* keys in the same frontmatter block — keeps the last
     occurrence of each image / image_source / image_license /
     image_attribution (the most recent find_photo write).
  3. Broken scalar values — rewrites any `key: value` whose value (joined
     with indented continuation lines) fails to parse, as a single-line
     double-quoted YAML scalar. Catches unquoted scalars containing ': ',
     unquoted scalars starting with '*' (mistaken for YAML aliases), and
     improperly single-quoted scalars with unescaped inner apostrophes.

Exits non-zero if any files remain broken.
"""

import argparse
import re
import sys
from pathlib import Path

import frontmatter
import yaml

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
IMAGE_KEYS = {"image", "image_source", "image_license", "image_attribution"}

FRONTMATTER_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n?)(.*)$", re.DOTALL)
ATTR_LINE_RE = re.compile(
    r'^image_attribution: "(.*?)"\s*$', re.MULTILINE
)
KEY_RE = re.compile(r"^([a-z_]+):")
KEY_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):(\s*)(.*)$")
BLOCK_SCALAR_MARKERS = {">", "|", ">-", "|-", ">+", "|+"}


def try_parse(path: Path) -> Exception | None:
    try:
        frontmatter.load(path)
    except Exception as e:
        return e
    return None


def fix_attribution_quotes(text: str) -> tuple[str, bool]:
    """Rewrite image_attribution with unescaped inner " as single-quoted YAML."""
    m = ATTR_LINE_RE.search(text)
    if not m:
        return text, False
    value = m.group(1)
    if '"' not in value and "\n" not in value:
        return text, False
    collapsed = re.sub(r"\s*\n\s*", " ", value).strip()
    escaped = collapsed.replace("'", "''")
    new_line = f"image_attribution: '{escaped}'"
    return text[:m.start()] + new_line + text[m.end():], True


def dedupe_image_keys(text: str) -> tuple[str, bool]:
    """Keep the last occurrence of each image_* key in the frontmatter block."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text, False
    start, fm, end, body = m.group(1), m.group(2), m.group(3), m.group(4)
    lines = fm.split("\n")
    counts = {}
    for line in lines:
        km = KEY_RE.match(line)
        if km and km.group(1) in IMAGE_KEYS:
            counts[km.group(1)] = counts.get(km.group(1), 0) + 1
    if not any(c > 1 for c in counts.values()):
        return text, False
    # Walk from end, keep first-seen (= last in file) occurrences of image_* keys.
    seen = set()
    kept_reverse = []
    for line in reversed(lines):
        km = KEY_RE.match(line)
        key = km.group(1) if km else None
        if key in IMAGE_KEYS:
            if key in seen:
                continue
            seen.add(key)
        kept_reverse.append(line)
    new_fm = "\n".join(reversed(kept_reverse))
    return start + new_fm + end + body, True


def _yaml_ok(text: str) -> bool:
    try:
        yaml.safe_load(text)
        return True
    except yaml.YAMLError:
        return False


def _double_quote(value: str) -> str:
    """Wrap value as a YAML double-quoted scalar."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _maybe_unwrap_single_quotes(value: str) -> str:
    """Strip `'...'` wrapping if both ends are single quotes.

    Lets `story: 'text with families' campaign.'` round-trip cleanly:
    the author meant single-quoted, but inner ' broke it; we unwrap and
    re-emit as double-quoted.
    """
    if len(value) >= 2 and value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def fix_broken_scalars(text: str) -> tuple[str, bool]:
    """Repair any `key: value` whose value won't parse.

    Walks the frontmatter top-down. For each top-level key whose value
    (joined with any indented continuation lines) fails to parse,
    rewrites it as a single-line double-quoted YAML scalar.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text, False
    start, fm, end, body = m.group(1), m.group(2), m.group(3), m.group(4)

    lines = fm.split("\n")
    out_lines = []
    fixes = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        km = KEY_LINE_RE.match(line)
        if not km or line.startswith((" ", "\t")):
            out_lines.append(line)
            i += 1
            continue

        key, _, value = km.group(1), km.group(2), km.group(3)
        if not value or value in BLOCK_SCALAR_MARKERS:
            out_lines.append(line)
            i += 1
            continue

        # Collect indented continuation lines.
        j = i + 1
        continuation = []
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                break
            if nxt.startswith((" ", "\t")):
                continuation.append(nxt)
                j += 1
            else:
                break

        snippet = f"{key}: {value}\n" + "\n".join(continuation) + "\n"
        if _yaml_ok(snippet):
            out_lines.append(line)
            i += 1
            continue

        full_value = value
        for c in continuation:
            full_value += " " + c.strip()
        cleaned = _maybe_unwrap_single_quotes(full_value.strip())
        new_line = f"{key}: {_double_quote(cleaned)}"
        if not _yaml_ok(new_line + "\n"):
            out_lines.append(line)
            i += 1
            continue

        out_lines.append(new_line)
        fixes += 1
        i = j

    if fixes == 0:
        return text, False
    return start + "\n".join(out_lines) + end + body, True


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changed = False
    text, c1 = dedupe_image_keys(text)
    changed |= c1
    text, c2 = fix_attribution_quotes(text)
    changed |= c2
    text, c3 = fix_broken_scalars(text)
    changed |= c3
    if not changed:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fix", action="store_true", help="Apply known mechanical fixes")
    args = ap.parse_args()

    broken_before = []
    for p in sorted(CONTENT_DIR.rglob("*.md")):
        err = try_parse(p)
        if err is not None:
            broken_before.append((p, err))

    if not broken_before:
        print("All content files parse cleanly.")
        return 0

    print(f"{len(broken_before)} files with invalid frontmatter:")
    for p, err in broken_before[:20]:
        rel = p.relative_to(CONTENT_DIR.parent)
        msg = str(err).split("\n")[0]
        print(f"  {rel}: {msg}")
    if len(broken_before) > 20:
        print(f"  ... and {len(broken_before) - 20} more")

    if not args.fix:
        print("\nRun with --fix to apply mechanical repairs.")
        return 1

    print("\nApplying fixes...")
    fixed = 0
    for p, _ in broken_before:
        if fix_file(p):
            if try_parse(p) is None:
                fixed += 1

    print(f"Fixed {fixed}/{len(broken_before)} files.")

    # Re-scan for remaining issues.
    still_broken = [p for p in CONTENT_DIR.rglob("*.md") if try_parse(p) is not None]
    if still_broken:
        print(f"\n{len(still_broken)} files still broken:")
        for p in still_broken:
            print(f"  {p.relative_to(CONTENT_DIR.parent)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
