#!/usr/bin/env python3
"""Crawl Atlas Obscura destinations and places."""

import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://www.atlasobscura.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
OUT_DIR = Path(__file__).parent / "obscura"
DELAY = 10.0  # seconds between requests
MAX_RETRIES = 8


def fetch(url):
    """Fetch a URL with retry and exponential backoff on 429."""
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=30)
            return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (2 ** attempt)
                print(f"\n  rate limited, waiting {wait}s...", end=" ", flush=True)
                time.sleep(wait)
                continue
            raise
        except (TimeoutError, OSError) as e:
            wait = 10 * (2 ** attempt)
            print(f"\n  {e.__class__.__name__}, retrying in {wait}s...", end=" ", flush=True)
            time.sleep(wait)
            continue
    raise Exception(f"Failed after {MAX_RETRIES} retries: {url}")


def get_destinations():
    """Get all destination slugs from the destinations page."""
    html = fetch(f"{BASE}/destinations")
    slugs = sorted(set(re.findall(r'href="/things-to-do/([a-z][a-z0-9-]*)"', html)))
    return slugs


def get_places_page(slug, page=1):
    """Fetch one page of places for a destination. Returns (places, has_next)."""
    url = f"{BASE}/things-to-do/{slug}/places"
    if page > 1:
        url += f"?page={page}"
    try:
        html = fetch(url)
    except urllib.error.HTTPError as e:
        if e.code in (404, 500):
            return [], False
        raise

    # Extract full card blocks (from <a class="Card --content-card... to </a>)
    card_blocks = re.findall(
        r'<a\s+class="Card --content-card[^"]*"(.*?)</a>', html, re.DOTALL
    )
    places = []
    for block in card_blocks:
        # Data attributes and href from the opening tag
        href_m = re.search(r'href="([^"]+)"', block)
        if not href_m:
            continue
        place = {"url": href_m.group(1)}
        for key, val in re.findall(r'data-([\w-]+)="([^"]+)"', block):
            place[key] = val
        # Place name from <h3><span>...</span></h3>
        name_m = re.search(r'js-title-content[^>]*>\s*<span>([^<]+)</span>', block)
        if name_m:
            place["name"] = name_m.group(1).strip()
        # Description from Card__content
        desc_m = re.search(r'js-subtitle-content[^>]*>\s*(.+?)\s*</div>', block, re.DOTALL)
        if desc_m:
            place["description"] = desc_m.group(1).strip()
        places.append(place)

    # Check if there's a next page
    next_pages = re.findall(
        rf"things-to-do/{re.escape(slug)}/places\?page=(\d+)", html
    )
    max_page = max((int(p) for p in next_pages), default=0)
    has_next = page < max_page

    return places, has_next


def crawl_destination(slug):
    """Crawl all place pages for a destination."""
    all_places = []
    page = 1
    while True:
        places, has_next = get_places_page(slug, page)
        all_places.extend(places)
        if not has_next or not places:
            break
        page += 1
        time.sleep(DELAY)
    return all_places


def main():
    OUT_DIR.mkdir(exist_ok=True)

    # Step 1: Get all destinations
    countries_file = OUT_DIR / "countries.txt"
    if countries_file.exists():
        print(f"Loading destinations from {countries_file}")
        slugs = countries_file.read_text().strip().splitlines()
    else:
        print("Fetching destinations...")
        slugs = get_destinations()
        countries_file.write_text("\n".join(slugs) + "\n")
        print(f"Saved {len(slugs)} destinations to {countries_file}")

    # Step 2: Crawl places for each destination
    for i, slug in enumerate(slugs):
        out_file = OUT_DIR / f"{slug}.json"
        if out_file.exists():
            print(f"[{i+1}/{len(slugs)}] {slug} — already done, skipping")
            continue

        print(f"[{i+1}/{len(slugs)}] {slug}...", end=" ", flush=True)
        time.sleep(DELAY)
        places = crawl_destination(slug)
        out_file.write_text(json.dumps(places, indent=2) + "\n")
        print(f"{len(places)} places")


if __name__ == "__main__":
    main()
