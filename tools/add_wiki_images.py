#!/usr/bin/env python3
"""
Find and download Wikipedia images for location pages that lack them.

For each scored location without an image:
  1. Query Wikipedia pageimages API using the location title (+ country hint).
  2. Fetch file info from Wikimedia Commons for license + download URL.
  3. Download the image at 1000px width.
  4. Save it alongside the markdown file and update frontmatter.

Usage:
  python3 tools/add_wiki_images.py [--top N] [--dry-run] [--start-after PATH]

Options:
  --top N          Process only the top N locations by score (default: 200)
  --dry-run        Show what would be done without writing files
  --start-after P  Skip locations until PATH is seen (for resuming)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import frontmatter

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = PROJECT_DIR / "content"

WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "World66ImageBot/1.0 (restoring open-content travel guide; r.osinga@ltp.nl)"
REQUEST_DELAY = 0.5  # seconds between API calls


def api_get(url: str, params: dict) -> dict | None:
    qs = urlencode(params)
    full_url = f"{url}?{qs}"
    try:
        req = Request(full_url, headers={"User-Agent": USER_AGENT})
        resp = urlopen(req, timeout=15)
        return json.loads(resp.read())
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as e:
        print(f"  API error: {e}", file=sys.stderr)
        return None


def get_wiki_image(title: str, country_hint: str = "") -> tuple[str, str, str, str] | None:
    """
    Returns (file_name, download_url, license_str, commons_url) or None.
    Tries the plain title first, then title + country_hint.
    """
    for search_title in ([title, f"{title} {country_hint}"] if country_hint else [title]):
        result = _fetch_pageimage(search_title)
        if result:
            return result
        time.sleep(REQUEST_DELAY)
    return None


SKIP_FILE_PATTERNS = re.compile(
    r"(?i)(flag|coat.of.arms|emblem|seal|locator.map|blank.map|administrative.map"
    r"|relief.map|topograph|satellite.photo|location.map|coa_|heraldry)",
)


def _fetch_pageimage(title: str) -> tuple[str, str, str, str] | None:
    """Query Wikipedia pageimages API for a page title, return image metadata."""
    data = api_get(WIKI_API, {
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "piprop": "name",
        "format": "json",
        "redirects": "1",
    })
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if page.get("ns") != 0:
            continue
        if "missing" in page:
            continue
        img_name = page.get("pageimage")
        if not img_name:
            continue
        page_title = page.get("title", title)
        if SKIP_FILE_PATTERNS.search(img_name):
            # Main image is a flag/map; search Commons for a landscape photo instead.
            time.sleep(REQUEST_DELAY)
            return _commons_search(page.get("title", title))
        # Normalise to File: prefix
        if not img_name.startswith("File:"):
            img_name = f"File:{img_name}"
        time.sleep(REQUEST_DELAY)
        return _fetch_file_info(img_name)
    return None


def _commons_search(location_title: str) -> tuple[str, str, str, str] | None:
    """
    Search Wikimedia Commons for a landscape photo of this location.
    Used as a fallback when pageimages returns a flag/map.
    """
    data = api_get(COMMONS_API, {
        "action": "query",
        "list": "search",
        "srsearch": location_title,
        "srnamespace": "6",  # File namespace
        "srlimit": "10",
        "format": "json",
    })
    if not data:
        return None
    results = data.get("query", {}).get("search", [])
    for item in results:
        name = item.get("title", "")
        if not name:
            continue
        lower = name.lower()
        if SKIP_FILE_PATTERNS.search(name):
            continue
        if not any(lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
            continue
        if any(word in lower for word in ("icon", "pictogram", "logo", "symbol", "button", "thumbnail")):
            continue
        time.sleep(REQUEST_DELAY)
        result = _fetch_file_info(name)
        if result:
            return result
    return None


def _fetch_file_info(file_name: str) -> tuple[str, str, str, str] | None:
    """Get download URL and license for a Wikimedia file."""
    data = api_get(COMMONS_API, {
        "action": "query",
        "titles": file_name,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "1000",
        "format": "json",
    })
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            # Try English Wikipedia instead
            data2 = api_get(WIKI_API, {
                "action": "query",
                "titles": file_name,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "iiurlwidth": "1000",
                "format": "json",
            })
            if not data2:
                return None
            pages2 = data2.get("query", {}).get("pages", {})
            for p2 in pages2.values():
                page = p2
            if "missing" in page:
                return None
        ii_list = page.get("imageinfo", [])
        if not ii_list:
            return None
        ii = ii_list[0]
        url = ii.get("thumburl") or ii.get("url")
        if not url:
            return None
        # Strip query string before checking extension (URLs may contain ?utm_source=...)
        ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            return None
        meta = ii.get("extmetadata", {})
        license_str = (
            meta.get("LicenseShortName", {}).get("value")
            or meta.get("License", {}).get("value")
            or "Unknown"
        )
        # Build commons URL
        desc_url = ii.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{quote(file_name.replace(' ', '_'))}"
        return (file_name, url, license_str, desc_url)
    return None


def download_file(url: str, dest: Path) -> bool:
    """Download url to dest. Returns True on success."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        resp = urlopen(req, timeout=30)
        data = resp.read()
        if len(data) < 5000:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except (HTTPError, URLError, OSError) as e:
        print(f"  Download error: {e}", file=sys.stderr)
        return False


def collect_locations_without_images() -> list[dict]:
    """
    Walk content/ for scored locations (city/region) without image frontmatter.
    Returns list of dicts sorted by score descending.
    """
    results = []
    for md_path in CONTENT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(md_path)
        except Exception:
            continue
        meta = post.metadata
        loc_type = meta.get("loc_type")
        if loc_type not in {"city", "region"}:
            continue
        if "score" not in meta:
            continue
        if meta.get("image"):
            continue
        try:
            score = float(meta["score"])
        except (TypeError, ValueError):
            continue
        rel = md_path.relative_to(CONTENT_DIR).with_suffix("")
        title = meta.get("title") or str(rel.name).replace("_", " ").title()
        # Country hint: the 3rd path component (e.g. content/europe/spain/... → Spain)
        parts = rel.parts
        country_hint = parts[1].replace("_", " ").title() if len(parts) > 1 else ""
        results.append({
            "path": md_path,
            "rel": str(rel),
            "title": title,
            "score": score,
            "country_hint": country_hint,
        })
    return sorted(results, key=lambda x: -x["score"])


def image_filename_for(rel_path: str) -> str:
    """Derive a short image filename from the location slug."""
    slug = rel_path.rsplit("/", 1)[-1]
    return f"{slug}.jpg"


def update_frontmatter(md_path: Path, image_name: str, source_url: str, license_str: str) -> None:
    post = frontmatter.load(md_path)
    post["image"] = image_name
    post["image_source"] = source_url
    post["image_license"] = license_str
    md_path.write_text(frontmatter.dumps(post))


def run(top: int, dry_run: bool, start_after: str | None) -> None:
    locs = collect_locations_without_images()
    print(f"Found {len(locs)} scored locations without images (processing top {top}).")
    locs = locs[:top]

    skipping = bool(start_after)
    ok = 0
    failed = 0

    for i, loc in enumerate(locs):
        if skipping:
            if loc["rel"] == start_after:
                skipping = False
            else:
                continue

        print(f"[{i+1}/{len(locs)}] {loc['title']} ({loc['rel']}, score={loc['score']:.3f})")

        result = get_wiki_image(loc["title"], loc["country_hint"])
        if not result:
            print(f"  No Wikipedia image found.")
            failed += 1
            time.sleep(REQUEST_DELAY)
            continue

        file_name, url, license_str, source_url = result
        img_filename = image_filename_for(loc["rel"])
        dest = loc["path"].parent / img_filename

        print(f"  Found: {file_name}")
        print(f"  License: {license_str}")
        print(f"  URL: {url[:80]}...")

        if dry_run:
            print(f"  [dry-run] Would save to {dest}")
            ok += 1
            continue

        if dest.exists():
            print(f"  Already exists, updating frontmatter only.")
            update_frontmatter(loc["path"], img_filename, source_url, license_str)
            ok += 1
            time.sleep(REQUEST_DELAY)
            continue

        if download_file(url, dest):
            print(f"  Saved {dest.stat().st_size:,}b → {dest}")
            update_frontmatter(loc["path"], img_filename, source_url, license_str)
            ok += 1
        else:
            print(f"  Download failed.")
            failed += 1

        time.sleep(REQUEST_DELAY)

    print(f"\nDone: {ok} added, {failed} failed/skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=200, help="Process top N locations by score")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--start-after", help="Skip until this rel path is seen")
    args = parser.parse_args()
    run(args.top, args.dry_run, args.start_after)
