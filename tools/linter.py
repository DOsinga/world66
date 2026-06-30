#!/usr/bin/env python3
"""
Lint world66 content for structural and frontmatter issues.

Walks content/ and runs a battery of checks. Reports issues grouped by
check; some checks have mechanical fixes available via --fix.

Checks:
  markdown_newlines       markdown uses LF and final newline          [fixable]
  frontmatter_parse        YAML frontmatter fails to load            [fixable]
  duplicate_image_keys     image_* keys repeated in frontmatter      [fixable]
  bad_attribution_quotes   image_attribution with unescaped inner "  [fixable]
  md_inside_own_dir        location/poi file at <dir>/<dir>.md       [report]
  missing_loc_type         type=location without loc_type field      [report]
  missing_coordinates      type=location without latitude/longitude  [report]
  invalid_loc_type         loc_type not in allowed set               [report]
  invalid_page_type        type field not in allowed set             [report]
  missing_poi_fields       type=poi missing required frontmatter      [report]
  invalid_poi_score        type=poi score is not 1.0-10.0             [report]
  continent_misplaced      file at content/<X>.md but not continent  [report]
  country_misplaced        continent child but loc_type != country   [report]
  city_has_child_location  city contains a child location page        [report]
  non_canonical_section    section slug not in canonical set         [partial fix]
  broken_link              markdown link to /<path> doesn't resolve  [report]

Exits non-zero if any unfixable issues remain after fixes are applied.
"""

import argparse
import os
import re
import sys
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import frontmatter
import yaml

REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"

ALLOWED_PAGE_TYPES = {
    "location", "section", "section_group", "neighbourhood", "theme", "poi",
}
ALLOWED_LOC_TYPES = {
    "continent", "country", "region", "island", "feature", "city",
}
CANONICAL_SECTION_SLUGS = {
    "things_to_do", "getting_there", "when_to_go", "eating_out",
    "getting_around", "day_trips", "bars_and_cafes", "books", "shopping",
    "beaches", "practical_information", "people", "food", "highlights",
    "festivals", "sights", "top_5_must_dos", "museums", "health",
    "budget_travel_ideas", "family_travel_ideas",
    "nightlife_and_entertainment", "tours_and_excursions", "activities",
    "7_day_itinerary",
}
# Mechanical normalizations — keys are exact slug matches, values are the
# canonical replacement. Anything not in here gets reported but not fixed.
SLUG_NORMALIZATIONS = {
    "practical_info": "practical_information",
    "practicalinfo": "practical_information",
    "eatingout": "eating_out",
    "foodanddrink": "food_and_drink",
    "food_and_drink": "food",
    "outdooractivities": "activities",
    "backgroundinfo": "highlights",
    "eating_out_1": "eating_out",
    "beaches_section": "beaches",
    "shopping_section": "shopping",
    "daytripstours": "day_trips",
    "cycling_routes": "activities",
    "walking_routes": "activities",
    "city_walks": "activities",
}

# ---------------------------------------------------------------------------
# Issue dataclass
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    path: Path
    check: str
    message: str
    fixer: Optional[Callable[[], bool]] = field(default=None, repr=False)

    @property
    def rel(self) -> str:
        try:
            return str(self.path.relative_to(REPO))
        except ValueError:
            return str(self.path)


# ---------------------------------------------------------------------------
# Raw file checks
# ---------------------------------------------------------------------------

def _tracked_markdown_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "*.md"],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [
        REPO / os.fsdecode(name)
        for name in result.stdout.split(b"\0")
        if name
    ]


def check_markdown_newlines() -> list[Issue]:
    issues = []
    for path in _tracked_markdown_files():
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            # File is tracked in git but deleted from working tree (staged deletion pending)
            continue
        problems = []
        if b"\r\n" in data or b"\r" in data:
            problems.append("uses CRLF line endings")
        if data and not data.endswith(b"\n"):
            problems.append("missing final newline")
        if problems:
            issues.append(Issue(
                path=path,
                check="markdown_newlines",
                message=", ".join(problems),
                fixer=lambda p=path: fix_markdown_newlines(p),
            ))
    return issues


def fix_markdown_newlines(path: Path) -> bool:
    data = path.read_bytes()
    fixed = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if fixed and not fixed.endswith(b"\n"):
        fixed += b"\n"
    if fixed == data:
        return False
    path.write_bytes(fixed)
    return True


# ---------------------------------------------------------------------------
# Frontmatter fixers — work on file text directly (broken files can't be parsed)
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n?)(.*)$", re.DOTALL)
ATTR_LINE_RE = re.compile(r'^image_attribution: "(.*?)"\s*$', re.MULTILINE)
KEY_RE = re.compile(r"^([a-z_]+):")
KEY_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):(\s*)(.*)$")
BLOCK_SCALAR_MARKERS = {">", "|", ">-", "|-", ">+", "|+"}
IMAGE_KEYS = {"image", "image_source", "image_license", "image_attribution"}


def _yaml_ok(text: str) -> bool:
    try:
        yaml.safe_load(text)
        return True
    except yaml.YAMLError:
        return False


def _double_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _maybe_unwrap_single_quotes(value: str) -> str:
    if len(value) >= 2 and value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


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
    """Keep the last occurrence of each image_* key."""
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


def fix_broken_scalars(text: str) -> tuple[str, bool]:
    """Rewrite any unparseable `key: value` as a double-quoted scalar."""
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


def apply_frontmatter_fixes(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changed = False
    text, c1 = dedupe_image_keys(text)
    text, c2 = fix_attribution_quotes(text)
    text, c3 = fix_broken_scalars(text)
    changed = c1 or c2 or c3
    if not changed:
        return False
    path.write_text(text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Checks operating on already-parsed pages
# ---------------------------------------------------------------------------

@dataclass
class Page:
    path: Path
    page_type: str
    meta: dict
    body: str = ""


def check_md_inside_own_dir(pages: list[Page]) -> list[Issue]:
    issues = []
    for p in pages:
        if p.path.stem == p.path.parent.name:
            issues.append(Issue(
                path=p.path, check="md_inside_own_dir",
                message=f"file should be sibling {p.path.parent.name}.md, not inside dir",
            ))
    return issues


def check_missing_loc_type(pages: list[Page]) -> list[Issue]:
    issues = []
    for p in pages:
        if p.page_type == "location" and not p.meta.get("loc_type"):
            issues.append(Issue(
                path=p.path, check="missing_loc_type",
                message="type=location without loc_type field",
            ))
    return issues


def check_missing_coordinates(pages: list[Page]) -> list[Issue]:
    issues = []
    for p in pages:
        if p.page_type != "location" or p.meta.get("loc_type") == "continent":
            continue
        missing = [
            key for key in ("latitude", "longitude")
            if p.meta.get(key) in (None, "")
        ]
        if missing:
            issues.append(Issue(
                path=p.path, check="missing_coordinates",
                message=f"type=location without {', '.join(missing)}",
            ))
    return issues


def check_invalid_loc_type(pages: list[Page]) -> list[Issue]:
    issues = []
    for p in pages:
        lt = p.meta.get("loc_type")
        if lt and lt not in ALLOWED_LOC_TYPES:
            issues.append(Issue(
                path=p.path, check="invalid_loc_type",
                message=f"loc_type={lt!r} not in {sorted(ALLOWED_LOC_TYPES)}",
            ))
    return issues


def check_invalid_page_type(pages: list[Page]) -> list[Issue]:
    issues = []
    for p in pages:
        if p.page_type not in ALLOWED_PAGE_TYPES:
            issues.append(Issue(
                path=p.path, check="invalid_page_type",
                message=f"type={p.page_type!r} not in {sorted(ALLOWED_PAGE_TYPES)}",
            ))
    return issues


def check_missing_poi_fields(pages: list[Page]) -> list[Issue]:
    issues = []
    required = ("tags", "latitude", "longitude", "score")
    for p in pages:
        if p.page_type != "poi":
            continue
        missing = [
            key for key in required
            if p.meta.get(key) in (None, "")
        ]
        if missing:
            issues.append(Issue(
                path=p.path,
                check="missing_poi_fields",
                message=f"type=poi without {', '.join(missing)}",
            ))
    return issues


def check_invalid_poi_score(pages: list[Page]) -> list[Issue]:
    issues = []
    for p in pages:
        if p.page_type != "poi" or p.meta.get("score") in (None, ""):
            continue
        score = p.meta["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            issues.append(Issue(
                path=p.path,
                check="invalid_poi_score",
                message=f"score={score!r} is not numeric",
            ))
            continue
        if not 1.0 <= score <= 10.0:
            issues.append(Issue(
                path=p.path,
                check="invalid_poi_score",
                message=f"score={score!r} not in range 1.0-10.0",
            ))
    return issues


def check_continent_misplaced(pages: list[Page]) -> list[Issue]:
    """Files directly in content/ should be continent locations."""
    issues = []
    for p in pages:
        if p.path.parent != CONTENT_DIR:
            continue
        if p.page_type != "location" or p.meta.get("loc_type") != "continent":
            issues.append(Issue(
                path=p.path, check="continent_misplaced",
                message=f"top-level page must be type=location loc_type=continent "
                        f"(got type={p.page_type} loc_type={p.meta.get('loc_type')!r})",
            ))
    return issues


def check_country_misplaced(pages: list[Page]) -> list[Issue]:
    """Non-section children of a continent dir should be country locations.

    Section files at the continent root (`africa/books.md`, `asia/people.md`,
    etc.) are legitimate continent-wide sections per CONTINENTS.md and are
    skipped.
    """
    continent_dirs = set()
    for p in pages:
        if (p.page_type == "location"
                and p.meta.get("loc_type") == "continent"
                and p.path.parent == CONTENT_DIR):
            continent_dirs.add(CONTENT_DIR / p.path.stem)
    issues = []
    for p in pages:
        if p.path.parent not in continent_dirs:
            continue
        if p.path.parent.name == p.path.stem:
            continue
        if p.page_type == "section":
            continue
        if p.page_type != "location" or p.meta.get("loc_type") != "country":
            issues.append(Issue(
                path=p.path, check="country_misplaced",
                message=f"continent child must be type=location loc_type=country "
                        f"(got type={p.page_type} loc_type={p.meta.get('loc_type')!r})",
            ))
    return issues


def _content_path_key(path: Path) -> str:
    """Return the URL-style content key for a markdown file path."""
    return str(path.relative_to(CONTENT_DIR).with_suffix(""))


def check_city_has_child_location(pages: list[Page]) -> list[Issue]:
    """Location pages with loc_type=city must not contain child locations."""
    locations_by_key = {
        _content_path_key(p.path): p
        for p in pages
        if p.page_type == "location"
    }
    issues = []
    for p in pages:
        if p.page_type != "location":
            continue
        rel_parent = p.path.parent.relative_to(CONTENT_DIR)
        if not rel_parent.parts:
            continue
        parent = locations_by_key.get(str(rel_parent))
        if not parent or parent.meta.get("loc_type") != "city":
            continue
        issues.append(Issue(
            path=p.path,
            check="city_has_child_location",
            message=(
                f"city {parent.path.relative_to(CONTENT_DIR).with_suffix('')} "
                f"contains child location loc_type={p.meta.get('loc_type')!r}"
            ),
        ))
    return issues


def check_non_canonical_section(pages: list[Page]) -> list[Issue]:
    issues = []
    for p in pages:
        if p.page_type != "section":
            continue
        slug = p.path.stem
        if slug in CANONICAL_SECTION_SLUGS:
            continue
        if slug in SLUG_NORMALIZATIONS:
            target = SLUG_NORMALIZATIONS[slug]
            fixer = _make_slug_rename_fixer(p.path, target)
            issues.append(Issue(
                path=p.path, check="non_canonical_section",
                message=f"slug {slug!r} → {target!r} (fixable)",
                fixer=fixer,
            ))
        else:
            issues.append(Issue(
                path=p.path, check="non_canonical_section",
                message=f"slug {slug!r} not in canonical set",
            ))
    return issues


def _make_slug_rename_fixer(path: Path, new_slug: str) -> Callable[[], bool]:
    def do() -> bool:
        new_path = path.parent / f"{new_slug}.md"
        if new_path.exists():
            return False
        subprocess.run(
            ["git", "mv", str(path.relative_to(REPO)), str(new_path.relative_to(REPO))],
            check=True, cwd=REPO,
        )
        return True
    return do


# Markdown link: [text](url) — excludes images (![...]) via negative lookbehind
MD_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _nfc(s: str) -> str:
    """Normalize string to Unicode NFC.

    HFS+ on macOS stores filenames in NFD (combining accents); markdown URLs
    typically use NFC (precomposed chars). Same visual character, different
    bytes. Normalize both sides before comparison.
    """
    import unicodedata
    return unicodedata.normalize("NFC", s)


def _build_path_index() -> set[str]:
    """All real .md file paths under content/, as NFC-normalized strings."""
    return {_nfc(str(p)) for p in CONTENT_DIR.rglob("*.md")}


def _build_stem_index() -> dict[str, set[str]]:
    """For each dir under content/ (as NFC string), the set of .md stems
    anywhere beneath it."""
    idx: dict[str, set[str]] = {}
    for f in CONTENT_DIR.rglob("*.md"):
        d = f.parent
        stem = _nfc(f.stem)
        while d != CONTENT_DIR.parent:
            idx.setdefault(_nfc(str(d)), set()).add(stem)
            if d == CONTENT_DIR:
                break
            d = d.parent
    return idx


def _url_resolves(url: str, path_index: set[str],
                  stem_index: dict[str, set[str]]) -> bool:
    """Resolve a link the way guide/views.py does."""
    from urllib.parse import unquote
    url = url.split("#", 1)[0].split("?", 1)[0]
    url = _nfc(unquote(url)).lstrip("/")
    if not url:
        return False
    slug = url.rsplit("/", 1)[-1] if "/" in url else url
    if _nfc(str(CONTENT_DIR / f"{url}.md")) in path_index:
        return True
    if _nfc(str(CONTENT_DIR / url / f"{slug}.md")) in path_index:
        return True
    parts = url.split("/")
    if len(parts) < 3:
        return False
    poi_slug = parts[-1]
    for city_len in range(len(parts) - 2, 0, -1):
        city_dir = _nfc(str(CONTENT_DIR / "/".join(parts[:city_len])))
        if city_dir not in stem_index:
            continue
        if poi_slug in stem_index[city_dir]:
            return True
    return False


def check_broken_links(pages: list[Page]) -> list[Issue]:
    """Find internal markdown links to /<path> that don't resolve."""
    path_index = _build_path_index()
    stem_index = _build_stem_index()
    issues = []
    for p in pages:
        seen: set[str] = set()
        for m in MD_LINK_RE.finditer(p.body):
            url = m.group(1).strip()
            if not url.startswith("/"):
                continue
            if url in seen:
                continue
            seen.add(url)
            if not _url_resolves(url, path_index, stem_index):
                issues.append(Issue(
                    path=p.path, check="broken_link",
                    message=f"link to {url!r} does not resolve",
                ))
    return issues


CHECKS = [
    check_md_inside_own_dir,
    check_missing_loc_type,
    check_missing_coordinates,
    check_invalid_loc_type,
    check_invalid_page_type,
    check_missing_poi_fields,
    check_invalid_poi_score,
    check_continent_misplaced,
    check_country_misplaced,
    check_city_has_child_location,
    check_non_canonical_section,
    check_broken_links,
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_parse_issues() -> tuple[list[Issue], list[Page]]:
    """Try to parse every file. Return (parse_issues, parsed_pages)."""
    parse_issues = []
    pages = []
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        try:
            post = frontmatter.load(path)
        except Exception as e:
            msg = str(e).split("\n")[0]
            parse_issues.append(Issue(
                path=path, check="frontmatter_parse", message=msg,
                fixer=lambda p=path: apply_frontmatter_fixes(p),
            ))
            continue
        pages.append(Page(
            path=path,
            page_type=post.metadata.get("type", "location"),
            meta=post.metadata,
            body=post.content,
        ))
    return parse_issues, pages


def print_issues(issues: list[Issue], limit: int = 10):
    by_check = defaultdict(list)
    for issue in issues:
        by_check[issue.check].append(issue)
    for check in sorted(by_check):
        items = by_check[check]
        print(f"\n{check}: {len(items)} issues")
        for it in items[:limit]:
            print(f"  {it.rel}: {it.message}")
        if len(items) > limit:
            print(f"  ... and {len(items) - limit} more")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fix", action="store_true",
                    help="Apply mechanical fixes for fixable issues")
    ap.add_argument("--limit", type=int, default=10,
                    help="Max examples to print per check (default 10)")
    args = ap.parse_args()

    newline_issues = check_markdown_newlines()

    if args.fix and newline_issues:
        print(f"Applying markdown newline fixes to {len(newline_issues)} files...")
        for issue in newline_issues:
            if issue.fixer:
                issue.fixer()
        newline_issues = check_markdown_newlines()

    parse_issues, pages = collect_parse_issues()

    if args.fix and parse_issues:
        print(f"Applying frontmatter fixes to {len(parse_issues)} files...")
        for issue in parse_issues:
            if issue.fixer:
                issue.fixer()
        parse_issues, pages = collect_parse_issues()

    # Run structural checks on whatever parses
    structural_issues = []
    for check in CHECKS:
        structural_issues.extend(check(pages))

    if args.fix:
        fixable = [i for i in structural_issues if i.fixer]
        if fixable:
            print(f"Applying structural fixes to {len(fixable)} issues...")
            for issue in fixable:
                issue.fixer()
            # Re-scan after fixes
            parse_issues, pages = collect_parse_issues()
            structural_issues = []
            for check in CHECKS:
                structural_issues.extend(check(pages))

    all_issues = newline_issues + parse_issues + structural_issues
    if not all_issues:
        print("Clean — no issues found.")
        return 0

    print(f"\n{len(all_issues)} total issues across {len(set(i.check for i in all_issues))} checks:")
    print_issues(all_issues, limit=args.limit)
    return 1


if __name__ == "__main__":
    sys.exit(main())
