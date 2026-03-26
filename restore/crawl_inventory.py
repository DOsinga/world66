#!/usr/bin/env python3
"""
Step 1: Build an inventory of all World66 content pages archived in the Wayback Machine.

Uses the CDX API to find unique URLs and their last good snapshot (before the site went dark).
Filters to only content pages (travel guide articles), skipping images, CSS, JS, etc.
"""

import json
import time
import csv
import sys
import os
from urllib.request import urlopen, Request
from urllib.parse import quote

CDX_API = "https://web.archive.org/cdx/search/cdx"
DOMAIN = "world66.com"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "inventory.jsonl")
STATS_FILE = os.path.join(OUTPUT_DIR, "inventory_stats.json")

# We want the last good snapshot before the site died (mid-2018)
# Filter to status 200 and text/html only
PARAMS = {
    "url": f"{DOMAIN}/*",
    "output": "json",
    "fl": "timestamp,original,statuscode,mimetype,length",
    "filter": ["statuscode:200", "mimetype:text/html"],
    "to": "20180701000000",  # Before the site went 410
    "collapse": "urlkey",  # Deduplicate by URL (keeps last snapshot)
    "limit": 50000,  # Process in batches
}

# URL patterns to skip (not content pages)
SKIP_PATTERNS = [
    "/images/",
    "/css/",
    "/js/",
    "/static/",
    "/login",
    "/register",
    "/logout",
    "/search",
    "/modify",
    "/edit",
    "/create",
    "/delete",
    "/user/",
    "/member/",
    "/profile/",
    ".css",
    ".js",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".ico",
    ".xml",
    ".pdf",
    ".zip",
    ".swf",
    "/devl/",
    "/editor/",
    "robots.txt",
    "favicon",
    "/rss",
    "/feed",
    "/atom",
    "DoubleClick",
    "doubleclick",
    "googlesyndication",
    "/ad/",
    "/ads/",
]


def is_content_url(url):
    """Check if a URL looks like a content page."""
    url_lower = url.lower()
    for pattern in SKIP_PATTERNS:
        if pattern.lower() in url_lower:
            return False
    return True


def fetch_cdx_page(resume_key=None, page=0):
    """Fetch a page of CDX results."""
    params = []
    for key, val in PARAMS.items():
        if isinstance(val, list):
            for v in val:
                params.append(f"{key}={quote(str(v))}")
        else:
            params.append(f"{key}={quote(str(val))}")

    if resume_key:
        params.append(f"resumeKey={quote(resume_key)}")
    params.append("showResumeKey=true")

    url = f"{CDX_API}?{'&'.join(params)}"
    print(f"  Fetching: page {page}...")

    req = Request(
        url,
        headers={
            "User-Agent": "World66-Restore/1.0 (restoring open content travel guide)"
        },
    )
    try:
        response = urlopen(req, timeout=120)
        data = response.read().decode("utf-8")
        return json.loads(data)
    except Exception as e:
        print(f"  Error: {e}")
        return None


def run_inventory():
    """Build the full inventory of content pages."""
    all_entries = []
    resume_key = None
    page = 0
    total_skipped = 0

    print(f"Building inventory of World66 content pages from Wayback Machine...")
    print(f"Domain: {DOMAIN}")
    print(f"Date range: up to 2018-07-01")
    print()

    while True:
        result = fetch_cdx_page(resume_key=resume_key, page=page)

        if result is None:
            print("  Failed to fetch, retrying in 10s...")
            time.sleep(10)
            result = fetch_cdx_page(resume_key=resume_key, page=page)
            if result is None:
                print("  Failed again, stopping.")
                break

        # The CDX API returns JSON array: first row is headers, rest is data
        # With showResumeKey, the last two entries are ["", "resumeKey"]
        if len(result) <= 1:
            print("  No more results.")
            break

        headers = result[0]

        # Check for resume key at the end
        new_resume_key = None
        data_rows = result[1:]
        if len(data_rows) >= 2 and data_rows[-2] == []:
            new_resume_key = data_rows[-1][0] if data_rows[-1] else None
            data_rows = data_rows[:-2]

        page_count = 0
        page_skipped = 0
        for row in data_rows:
            entry = dict(zip(headers, row))
            url = entry.get("original", "")

            if is_content_url(url):
                all_entries.append(entry)
                page_count += 1
            else:
                page_skipped += 1
                total_skipped += 1

        print(f"  Page {page}: {page_count} content pages, {page_skipped} skipped")

        if new_resume_key:
            resume_key = new_resume_key
            page += 1
            time.sleep(2)  # Be polite to the API
        else:
            break

    # Write inventory
    print(
        f"\nWriting inventory: {len(all_entries)} content pages ({total_skipped} non-content skipped)"
    )

    with open(OUTPUT_FILE, "w") as f:
        for entry in all_entries:
            f.write(json.dumps(entry) + "\n")

    # Write stats
    stats = {
        "total_content_pages": len(all_entries),
        "total_skipped": total_skipped,
        "pages_fetched": page + 1,
    }
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"Inventory saved to: {OUTPUT_FILE}")
    print(f"Stats saved to: {STATS_FILE}")

    # Show some sample URLs
    print(f"\nSample content URLs:")
    for entry in all_entries[:20]:
        print(f"  {entry['original']}")


if __name__ == "__main__":
    run_inventory()
