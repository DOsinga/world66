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

This is read-only — no rename happens here.
"""

import re
import sys
import unicodedata
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
SKIP_TOPLEVEL = {"about", "contributing", "travelwise", "takeaway"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
TYPE_RE = re.compile(r"^type:\s*(\S+)\s*$", re.MULTILINE)


def fm(text: str) -> str | None:
    m = FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


def get_field(text: str, regex: re.Pattern) -> str | None:
    body = fm(text)
    if body is None:
        return None
    m = regex.search(body)
    if not m:
        return None
    v = m.group(1).strip()
    if (v.startswith('"') and v.endswith('"')) or \
       (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    return v


def slugify(title: str) -> str:
    # Strip accents via NFKD decomposition
    norm = unicodedata.normalize("NFKD", title)
    no_marks = "".join(c for c in norm if not unicodedata.combining(c))
    # Lowercase, replace separators with underscore, drop other punctuation
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
    # Truncation: stem is a strict prefix of expected, and stem is "long-ish"
    if expected.startswith(stem) and len(expected) > len(stem) and len(stem) >= 8:
        return "truncated"
    # Diacritic stripping: title has non-ASCII, and the stem is shorter than
    # expected because of missing transliterations
    if has_non_ascii(title) and stem != expected and len(stem) < len(expected):
        return "diacritic"
    # Any other mismatch — interesting but lower confidence
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
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        if get_field(text, TYPE_RE) != "location":
            continue
        title = get_field(text, TITLE_RE)
        if not title:
            continue
        expected = slugify(title)
        if not expected:
            continue
        category = classify(md.stem, expected, title)
        if category is None:
            continue
        rel = md.relative_to(CONTENT_DIR).with_suffix("")
        print(f"{rel}\t{md.stem}\t{expected}\t{category}\t{title}")


if __name__ == "__main__":
    sys.exit(main() or 0)
