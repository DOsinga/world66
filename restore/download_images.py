#!/usr/bin/env python3
"""
Separate pass: extract image URLs from downloaded HTML pages and download them
from the Wayback Machine. Run this after download_pages.py finishes.
"""

import json
import os
import re
import sys
import time
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, urljoin

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "inventory_filtered.jsonl")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "image_progress.json")

IMAGE_DELAY = 0.3
MAX_RETRIES = 2
RETRY_DELAY = 5
SAVE_EVERY = 50

IMAGE_PATTERNS = [
    re.compile(r'<img[^>]*class="?locationImage"?[^>]*src="([^"]+)"', re.IGNORECASE),
    re.compile(
        r'<div[^>]*class="?photoBox"?[^>]*>.*?<img[^>]*src="([^"]+)"',
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r'<img[^>]*src="((?:https?://)?(?:www\.)?world66\.com/[^"]*\.(?:jpg|jpeg|png|gif))"',
        re.IGNORECASE,
    ),
    re.compile(
        r'<img[^>]*src="(/(?!world/images/(?:ad|logo|linea|tab|arrow|bullet|spacer))[^"]*\.(?:jpg|jpeg|png|gif))"',
        re.IGNORECASE,
    ),
]

SKIP_IMAGE_PATTERNS = [
    "logo_beta", "linea.gif", "/ad.gif", "/ads/", "spacer.gif",
    "googlesyndication", "doubleclick", "nedstat", "google_ad",
    "change-photo.gif", "upload.gif", "arrow", "bullet", "tab",
    "favicon", "icon", "/css/", "/js/",
    "files.world66.com/images/",
]


def image_url_to_filepath(img_url):
    parsed = urlparse(img_url)
    path = parsed.path.strip("/")
    if not path:
        return None
    path = re.sub(r"^(?:www\.)?world66\.com/", "", path)
    return os.path.join(IMAGES_DIR, path)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
        return {
            "downloaded": set(data.get("downloaded", [])),
            "failed": set(data.get("failed", [])),
            "scanned": set(data.get("scanned", [])),
        }
    return {"downloaded": set(), "failed": set(), "scanned": set()}


def save_progress(progress):
    data = {k: sorted(v) if isinstance(v, set) else v for k, v in progress.items()}
    fd, tmp_path = tempfile.mkstemp(dir=SCRIPT_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, PROGRESS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def extract_image_urls(html, page_url):
    images = set()
    for pattern in IMAGE_PATTERNS:
        for m in pattern.finditer(html):
            img_url = m.group(1)
            if img_url.startswith("/"):
                img_url = f"http://www.world66.com{img_url}"
            elif not img_url.startswith("http"):
                img_url = urljoin(page_url, img_url)
            skip = any(sp in img_url.lower() for sp in SKIP_IMAGE_PATTERNS)
            if not skip:
                images.add(img_url)
    return images


def fetch_url(url, timeout=15):
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers={
                "User-Agent": "World66-Restore/1.0 (restoring open content travel guide)"
            })
            response = urlopen(req, timeout=timeout)
            return response.read()
        except HTTPError as e:
            if e.code in (404, 410):
                return None
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None
        except (URLError, TimeoutError, ConnectionError, OSError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None
    return None


def run():
    # Build a mapping of original URL -> timestamp from inventory
    url_timestamps = {}
    with open(INVENTORY_FILE) as f:
        for line in f:
            e = json.loads(line)
            url_timestamps[e["original"]] = e["timestamp"]

    progress = load_progress()
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # Scan all HTML files for images
    html_files = []
    for root, dirs, files in os.walk(RAW_DIR):
        for fname in files:
            if fname.endswith(".html"):
                html_files.append(os.path.join(root, fname))

    print(f"Scanning {len(html_files)} HTML files for images...")

    all_images = {}  # img_url -> timestamp
    scanned = 0
    for filepath in sorted(html_files):
        if filepath in progress["scanned"]:
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
            # Find a matching timestamp (use a generic recent one)
            images = extract_image_urls(html, "http://www.world66.com/")
            for img_url in images:
                if img_url not in all_images:
                    all_images[img_url] = "20180601000000"
            progress["scanned"].add(filepath)
        except Exception:
            pass
        scanned += 1

    # Filter out already done
    to_download = [
        url for url in all_images
        if url not in progress["downloaded"] and url not in progress["failed"]
    ]

    print(f"Found {len(all_images)} unique images, {len(to_download)} to download")
    print(f"Already: {len(progress['downloaded'])} downloaded, {len(progress['failed'])} failed")
    print()

    count = 0
    ok = 0
    start_time = time.time()

    try:
        for img_url in to_download:
            filepath = image_url_to_filepath(img_url)
            if not filepath:
                progress["failed"].add(img_url)
                continue

            if os.path.exists(filepath):
                progress["downloaded"].add(img_url)
                continue

            timestamp = all_images[img_url]
            wb_url = f"https://web.archive.org/web/{timestamp}id_/{img_url}"
            content = fetch_url(wb_url)

            if content and len(content) > 100:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(content)
                progress["downloaded"].add(img_url)
                ok += 1
                print(f"  [{count+1}/{len(to_download)}] OK ({len(content):,}b): {os.path.basename(filepath)}")
            else:
                progress["failed"].add(img_url)

            count += 1
            if count % SAVE_EVERY == 0:
                save_progress(progress)
                elapsed = time.time() - start_time
                rate = count / elapsed if elapsed > 0 else 0
                print(f"  --- {ok} ok, {count - ok} failed, {rate:.1f} imgs/s ---")

            time.sleep(IMAGE_DELAY)

    except KeyboardInterrupt:
        print("\nInterrupted!")

    save_progress(progress)
    print(f"\nDone! {ok} downloaded, {count - ok} failed")


if __name__ == "__main__":
    run()
