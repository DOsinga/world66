#!/usr/bin/env python3
"""
Step 2: Download World66 pages and images from the Wayback Machine.

Resumable — tracks progress in a JSON file. Uses atomic writes to prevent
corruption on crash. Handles transient Wayback Machine failures gracefully.
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
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "inventory_filtered.jsonl")
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "download_progress.json")

# Rate limiting
REQUEST_DELAY = 1.0
IMAGE_DELAY = 0.3
MAX_RETRIES = 3
RETRY_DELAY = 10
BACKOFF_MULTIPLIER = 2  # Exponential backoff

SAVE_EVERY = 25

# Image patterns to find in HTML
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
    "logo_beta",
    "linea.gif",
    "/ad.gif",
    "/ads/",
    "spacer.gif",
    "googlesyndication",
    "doubleclick",
    "nedstat",
    "google_ad",
    "change-photo.gif",
    "upload.gif",
    "arrow",
    "bullet",
    "tab",
    "favicon",
    "icon",
    "/css/",
    "/js/",
    "files.world66.com/images/",
]


def url_to_filepath(url, normalized_path=None):
    if normalized_path:
        path = normalized_path.strip("/")
    else:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
    if not path:
        path = "index"
    path = path.replace("?", "_").replace("&", "_").replace("=", "_")
    return os.path.join(RAW_DIR, path + ".html")


def image_url_to_filepath(img_url):
    parsed = urlparse(img_url)
    path = parsed.path.strip("/")
    if not path:
        return None
    path = re.sub(r"^(?:www\.)?world66\.com/", "", path)
    return os.path.join(IMAGES_DIR, path)


def wayback_url(timestamp, original_url):
    return f"https://web.archive.org/web/{timestamp}id_/{original_url}"


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
        # Convert lists to sets for O(1) lookup
        return {
            "downloaded": set(data.get("downloaded", [])),
            "failed": set(data.get("failed", [])),
            "skipped": set(data.get("skipped", [])),
            "images_downloaded": set(data.get("images_downloaded", [])),
            "images_failed": set(data.get("images_failed", [])),
        }
    return {
        "downloaded": set(),
        "failed": set(),
        "skipped": set(),
        "images_downloaded": set(),
        "images_failed": set(),
    }


def save_progress(progress):
    """Atomic write — write to temp file then rename."""
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


def fetch_url(url, timeout=30):
    """Fetch a URL with retries and exponential backoff."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": "World66-Restore/1.0 (restoring open content travel guide)"
                },
            )
            response = urlopen(req, timeout=timeout)
            return response.read()
        except HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = RETRY_DELAY * BACKOFF_MULTIPLIER**attempt
                print(f"    Rate limited (429), waiting {wait:.0f}s...")
                time.sleep(wait)
            elif e.code in (404, 410):
                return None
            elif e.code in (503, 502, 500):
                wait = RETRY_DELAY * BACKOFF_MULTIPLIER**attempt
                print(f"    Server error ({e.code}), retrying in {wait:.0f}s...")
                time.sleep(wait)
            elif attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise
        except (URLError, TimeoutError, ConnectionError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAY * BACKOFF_MULTIPLIER**attempt
                print(f"    Connection error, retrying in {wait:.0f}s...")
                time.sleep(wait)
            else:
                raise
    return None


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


def download_image(img_url, timestamp, progress):
    if img_url in progress["images_downloaded"] or img_url in progress["images_failed"]:
        return

    filepath = image_url_to_filepath(img_url)
    if not filepath:
        return

    if os.path.exists(filepath):
        progress["images_downloaded"].add(img_url)
        return

    wb_url = wayback_url(timestamp, img_url)
    try:
        content = fetch_url(wb_url, timeout=15)
        if content and len(content) > 100:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(content)
            progress["images_downloaded"].add(img_url)
            print(f"    IMG OK ({len(content):,}b): {os.path.basename(filepath)}")
        else:
            progress["images_failed"].add(img_url)
    except Exception:
        # Don't let image failures slow us down
        progress["images_failed"].add(img_url)

    time.sleep(IMAGE_DELAY)


def run_download(start_from=0, limit=None):
    if not os.path.exists(INVENTORY_FILE):
        print(f"Error: {INVENTORY_FILE} not found. Run filter_inventory.py first.")
        sys.exit(1)

    entries = []
    with open(INVENTORY_FILE) as f:
        for line in f:
            entries.append(json.loads(line.strip()))

    print(f"Loaded {len(entries):,} entries from inventory")

    progress = load_progress()
    done_urls = progress["downloaded"] | progress["failed"] | progress["skipped"]
    print(
        f"Already processed: {len(done_urls):,} pages, "
        f"{len(progress['images_downloaded']):,} images"
    )

    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    remaining = [
        (i, e) for i, e in enumerate(entries) if e["original"] not in done_urls
    ]
    if start_from > 0:
        remaining = remaining[start_from:]
    if limit:
        remaining = remaining[:limit]

    print(f"Remaining: {len(remaining):,} pages to download")
    print()

    total_bytes = 0
    count = 0
    start_time = time.time()

    try:
        for idx, entry in remaining:
            url = entry["original"]
            timestamp = entry["timestamp"]
            norm_path = entry.get("normalized_path")
            filepath = url_to_filepath(url, norm_path)

            try:
                wb_url = wayback_url(timestamp, url)
                content = fetch_url(wb_url)

                if content is None:
                    progress["skipped"].add(url)
                    print(f"  [{idx+1}/{len(entries)}] SKIP: {norm_path or url}")
                elif len(content) > 0:
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(content)
                    progress["downloaded"].add(url)
                    total_bytes += len(content)
                    print(
                        f"  [{idx+1}/{len(entries)}] OK ({len(content):,}b): {norm_path or url}"
                    )

                    # Image downloading is done in a separate pass
                    # (see download_images.py)
                else:
                    progress["failed"].add(url)

            except Exception as e:
                progress["failed"].add(url)
                print(f"  [{idx+1}/{len(entries)}] ERROR: {norm_path or url} - {e}")

            count += 1
            if count % SAVE_EVERY == 0:
                save_progress(progress)
                elapsed = time.time() - start_time
                rate = count / elapsed if elapsed > 0 else 0
                eta_hours = (len(remaining) - count) / rate / 3600 if rate > 0 else 0
                n_imgs = len(progress["images_downloaded"])
                print(
                    f"  --- Saved. {total_bytes/1024/1024:.1f}MB, {n_imgs} imgs, "
                    f"{rate:.1f} pages/s, ETA {eta_hours:.1f}h ---"
                )

            time.sleep(REQUEST_DELAY)

    except KeyboardInterrupt:
        print(f"\n  Interrupted! Saving progress...")

    save_progress(progress)
    elapsed = time.time() - start_time
    n_imgs = len(progress["images_downloaded"])
    print(
        f"\nDone! {total_bytes/1024/1024:.1f}MB in {elapsed/3600:.1f}h, {n_imgs} images"
    )
    print(
        f"  {len(progress['downloaded']):,} ok, {len(progress['failed']):,} failed, "
        f"{len(progress['skipped']):,} skipped"
    )


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_download(start_from=start, limit=limit)
