#!/usr/bin/env python3
"""Find location files whose filename slug doesn't match the slugified title.

Two categories we care about:

  - Truncated names: stem is a strict prefix of the slugified title and
    the title is longer. e.g. `niagara_on_the_lak.md` whose title is
    "Niagara-on-the-Lake" -> expected slug `niagara_on_the_lake`.
  - Diacritic-stripped names: stem is missing characters present in the
    slugified title even though the title contains non-ASCII letters that
    should have been transliterated. e.g. `slen.md` whose title is
    "Sälen" -> expected slug `salen`.

Outputs a TSV to stdout:
  path<TAB>current_stem<TAB>expected_slug<TAB>category<TAB>title

Read-only — no renaming happens here.
"""

import re
import sys
import unicodedata
from pathlib import Path

import frontmatter

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}


def slugify(title: str) -> str:
    norm = unicodedata.normalize("NFKD", title)
    no_marks = "".join(c for c in norm if not unicodedata.combining(c))
    s = no_marks.lower()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def has_non_ascii(s: str) -> bool:
    return any(ord(c) > 127 for c in s)


def classify(stem: str, expected: str, title: str) -> str | None:
    if stem == expected:
        return None
    if expected.startswith(stem) and len(expected) > len(stem) and len(stem) >= 8:
        return "truncated"
    if has_non_ascii(title) and stem != expected and len(stem) < len(expected):
        return "diacritic"
    if stem != expected:
        return "mismatch"
    return None


def main():
    for md in CONTENT_DIR.rglob("*.md"):
        parts = md.relative_to(CONTENT_DIR).parts
        if parts[0] in SKIP_TOPLEVEL:
            continue
        if len(parts) == 1 and md.stem in SKIP_TOPLEVEL:
            continue
        try:
            post = frontmatter.load(md)
        except Exception:
            continue
        if post.metadata.get("type") != "location":
            continue
        title = post.metadata.get("title")
        if not title:
            continue
        expected = slugify(str(title))
        if not expected:
            continue
        category = classify(md.stem, expected, str(title))
        if category is None:
            continue
        rel = md.relative_to(CONTENT_DIR).with_suffix("")
        print(f"{rel}\t{md.stem}\t{expected}\t{category}\t{title}")


if __name__ == "__main__":
    sys.exit(main() or 0)
