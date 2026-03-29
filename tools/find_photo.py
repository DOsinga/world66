#!/usr/bin/env python3
"""
Find and assign copyright-free photos to World66 content pages.

Searches Wikimedia Commons, Unsplash, Pexels, and Pixabay for landscape
photos, uses Gemini Vision to pick the best match, and saves it next to
the markdown file with frontmatter updates.

Usage:
    python tools/find_photo.py /europe/netherlands/amsterdam
    python tools/find_photo.py --batch --type location
    python tools/find_photo.py --batch --dry-run
"""

import argparse
import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
CONTENT_DIR = SCRIPT_DIR.parent / 'content'
PROGRESS_FILE = SCRIPT_DIR / 'photo_progress.json'

MIN_WIDTH = 780
TARGET_WIDTH = 780
THUMB_SIZE = (320, 240)
JPEG_QUALITY = 85
MAX_PER_SOURCE = 3

USER_AGENT = 'World66PhotoFinder/1.0 (https://world66.ai)'


@dataclass
class Candidate:
    """A candidate photo from an image source."""
    url: str
    thumb_url: str
    source: str
    width: int
    height: int
    license: str
    attribution: str
    source_page: str


# ---------------------------------------------------------------------------
# Path resolution (mirrors guide/models.py logic)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from markdown text."""
    if text.startswith('---'):
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', text, re.DOTALL)
        if match:
            import yaml
            try:
                meta = yaml.safe_load(match.group(1)) or {}
            except Exception:
                meta = {}
            return meta, match.group(2)
    return {}, text


def resolve_md_path(content_path: str) -> Path | None:
    """Resolve a URL-style content path to a markdown file."""
    content_path = content_path.strip('/')
    slug = content_path.rsplit('/', 1)[-1] if '/' in content_path else content_path

    for md_file in [
        CONTENT_DIR / content_path / f'{slug}.md',
        CONTENT_DIR / f'{content_path}.md',
    ]:
        if md_file.is_file():
            return md_file

    if '/' in content_path:
        parent_path, slug = content_path.rsplit('/', 1)
        md_file = CONTENT_DIR / parent_path / f'{slug}.md'
        if md_file.is_file():
            return md_file

    return None


def build_search_query(content_path: str, meta: dict) -> str:
    """Build a search query from page title and path context."""
    title = meta.get('title', '')
    page_type = meta.get('type', 'location')

    if page_type in ('section', 'poi'):
        # Combine with parent location name from path
        parts = content_path.strip('/').split('/')
        if page_type == 'poi' and len(parts) >= 3:
            location_name = parts[-3].replace('_', ' ')
        elif len(parts) >= 2:
            location_name = parts[-2].replace('_', ' ')
        else:
            location_name = ''
        return f'{location_name} {title}'.strip()

    return title


# ---------------------------------------------------------------------------
# Image source adapters
# ---------------------------------------------------------------------------

def search_wikimedia(query: str) -> list[Candidate]:
    """Search Wikimedia Commons for photos."""
    try:
        resp = httpx.get(
            'https://commons.wikimedia.org/w/api.php',
            params={
                'action': 'query',
                'generator': 'search',
                'gsrnamespace': 6,
                'gsrsearch': f'{query} filetype:jpg|jpeg|png',
                'gsrlimit': 10,
                'prop': 'imageinfo',
                'iiprop': 'url|extmetadata|size|mime',
                'iiurlwidth': 800,
                'format': 'json',
            },
            headers={'User-Agent': USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'  Wikimedia search failed: {e}')
        return []

    pages = data.get('query', {}).get('pages', {})
    candidates = []
    for page in pages.values():
        info = (page.get('imageinfo') or [{}])[0]
        width = info.get('width', 0)
        height = info.get('height', 0)
        if width < MIN_WIDTH or height == 0 or width / height < 1.2:
            continue  # skip non-landscape or too small

        mime = info.get('mime', '')
        if 'svg' in mime or 'gif' in mime:
            continue

        ext = info.get('extmetadata', {})
        license_short = ext.get('LicenseShortName', {}).get('value', 'Unknown')
        artist = ext.get('Artist', {}).get('value', 'Unknown')
        # Strip HTML from artist
        artist = re.sub(r'<[^>]+>', '', artist).strip()

        candidates.append(Candidate(
            url=info.get('url', ''),
            thumb_url=info.get('thumburl', info.get('url', '')),
            source='wikimedia',
            width=width,
            height=height,
            license=license_short,
            attribution=artist,
            source_page=info.get('descriptionurl', ''),
        ))
        if len(candidates) >= MAX_PER_SOURCE:
            break

    return candidates


def search_flickr(query: str) -> list[Candidate]:
    """Search Flickr for CC-licensed photos."""
    key = os.environ.get('FLICKR_API_KEY')
    if not key:
        return []

    # License IDs: 4=CC-BY, 5=CC-BY-SA, 7=No known copyright, 9=CC0, 10=Public Domain
    try:
        resp = httpx.get(
            'https://api.flickr.com/services/rest/',
            params={
                'method': 'flickr.photos.search',
                'api_key': key,
                'text': query,
                'license': '4,5,7,9,10',
                'sort': 'relevance',
                'content_type': 1,
                'media': 'photos',
                'extras': 'url_l,url_o,url_z,license,owner_name,o_dims',
                'per_page': 10,
                'format': 'json',
                'nojsoncallback': 1,
            },
            headers={'User-Agent': USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'  Flickr search failed: {e}')
        return []

    license_names = {
        '4': 'CC BY 2.0', '5': 'CC BY-SA 2.0',
        '7': 'No known copyright', '9': 'CC0 1.0', '10': 'Public Domain',
    }

    candidates = []
    for photo in data.get('photos', {}).get('photo', []):
        # Prefer url_l (1024px), fallback to url_o (original) or url_z (640px)
        url = photo.get('url_l') or photo.get('url_o') or photo.get('url_z')
        thumb_url = photo.get('url_z') or photo.get('url_l') or url
        if not url:
            continue

        width = int(photo.get('width_l') or photo.get('o_width') or photo.get('width_z') or 0)
        height = int(photo.get('height_l') or photo.get('o_height') or photo.get('height_z') or 0)
        if width < MIN_WIDTH or height == 0 or width / height < 1.2:
            continue

        lic = str(photo.get('license', ''))
        candidates.append(Candidate(
            url=url,
            thumb_url=thumb_url,
            source='flickr',
            width=width,
            height=height,
            license=license_names.get(lic, f'Flickr License {lic}'),
            attribution=f'{photo.get("ownername", "Unknown")} on Flickr',
            source_page=f'https://www.flickr.com/photos/{photo.get("owner")}/{photo.get("id")}',
        ))
        if len(candidates) >= MAX_PER_SOURCE:
            break

    return candidates


# ---------------------------------------------------------------------------
# Thumbnail creation and Gemini evaluation
# ---------------------------------------------------------------------------

def download_image(url: str) -> bytes | None:
    """Download an image, return bytes or None on failure."""
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True, headers={'User-Agent': USER_AGENT})
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f'  Download failed ({url[:60]}...): {e}')
        return None


def make_thumbnail(image_bytes: bytes) -> bytes | None:
    """Resize image to thumbnail, return JPEG bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGB')
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=70)
        return buf.getvalue()
    except Exception as e:
        print(f'  Thumbnail creation failed: {e}')
        return None


def pick_best_photo(candidates: list[Candidate], thumb_data: list[bytes], page_text: str, gemini_key: str) -> int | None:
    """Use Gemini Vision to pick the best photo. Returns candidate index or None."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=gemini_key)

    parts = [
        f'You are selecting the best photo for a travel guide page. '
        f'Below are {len(thumb_data)} candidate photos numbered 0 to {len(thumb_data) - 1}.\n\n'
        f'Page content:\n{page_text[:1000]}\n\n'
        f'Pick the single best photo based on:\n'
        f'1. Relevance to this specific destination/topic\n'
        f'2. Visual quality and composition\n'
        f'3. How well it represents the place to a traveler\n\n'
        f'If NONE of the photos are suitable, respond with just "NONE".\n'
        f'Otherwise respond with just the number (0-{len(thumb_data) - 1}) of the best photo.'
    ]

    for i, thumb in enumerate(thumb_data):
        parts.append(f'\nPhoto {i}:')
        parts.append(types.Part.from_bytes(data=thumb, mime_type='image/jpeg'))

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=parts,
        )
        answer = response.text.strip()

        if 'NONE' in answer.upper():
            return None

        # Extract first number from response
        match = re.search(r'\d+', answer)
        if match:
            idx = int(match.group())
            if 0 <= idx < len(thumb_data):
                return idx

        print(f'  Gemini returned unexpected answer: {answer}')
        return None

    except Exception as e:
        print(f'  Gemini evaluation failed: {e}')
        return None


# ---------------------------------------------------------------------------
# Save photo and update frontmatter
# ---------------------------------------------------------------------------

def save_photo(image_bytes: bytes, md_path: Path, slug: str) -> str:
    """Resize to target width and save as JPEG next to the markdown file."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert('RGB')

    # Resize to TARGET_WIDTH maintaining aspect ratio
    ratio = TARGET_WIDTH / img.width
    new_height = int(img.height * ratio)
    img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)

    filename = f'{slug}.jpg'
    out_path = md_path.parent / filename
    img.save(out_path, format='JPEG', quality=JPEG_QUALITY)
    print(f'  Saved: {out_path}')
    return filename


def update_frontmatter(md_path: Path, filename: str, source_url: str, license_str: str, attribution: str, force: bool = False):
    """Update the markdown file's frontmatter with image fields."""
    text = md_path.read_text(encoding='utf-8', errors='replace')

    if not text.startswith('---'):
        print(f'  Warning: no frontmatter in {md_path}')
        return

    end = text.find('\n---', 3)
    if end == -1:
        print(f'  Warning: malformed frontmatter in {md_path}')
        return

    frontmatter = text[3:end]
    body = text[end + 4:]

    # Remove old image fields if --force
    if force:
        for field in ('image:', 'image_source:', 'image_license:', 'image_attribution:'):
            frontmatter = re.sub(rf'\n{re.escape(field)}[^\n]*', '', frontmatter)

    # Add new fields
    new_fields = (
        f'\nimage: {filename}'
        f'\nimage_source: "{source_url}"'
        f'\nimage_license: "{license_str}"'
        f'\nimage_attribution: "{attribution}"'
    )
    new_text = f'---{frontmatter}{new_fields}\n---{body}'
    md_path.write_text(new_text, encoding='utf-8')
    print(f'  Updated frontmatter: {md_path}')


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def load_progress() -> set:
    """Load set of already-processed content paths."""
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text())
        return set(data.get('processed', []))
    return set()


def save_progress(processed: set):
    """Save processed paths to progress file."""
    PROGRESS_FILE.write_text(json.dumps({'processed': sorted(processed)}, indent=2))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_page(content_path: str, gemini_key: str, force: bool = False) -> bool:
    """Process a single page. Returns True if a photo was saved."""
    md_path = resolve_md_path(content_path)
    if not md_path:
        print(f'  Not found: {content_path}')
        return False

    text = md_path.read_text(encoding='utf-8', errors='replace')
    meta, body = _parse_frontmatter(text)

    # Skip if already has image (unless force)
    if meta.get('image') and not force:
        print(f'  Skipped (already has image): {content_path}')
        return False

    slug = md_path.stem
    print(f'Processing: {content_path}')

    # Build search query
    query = build_search_query(content_path, meta)
    print(f'  Search query: {query}')

    # Search all sources
    candidates = []
    for name, search_fn in [
        ('Wikimedia', search_wikimedia),
        ('Flickr', search_flickr),
    ]:
        results = search_fn(query)
        print(f'  {name}: {len(results)} candidates')
        candidates.extend(results)
        time.sleep(0.5)  # brief pause between sources

    if not candidates:
        print(f'  No candidates found for: {content_path}')
        return False

    # Download and create thumbnails
    thumb_data = []
    valid_candidates = []
    for c in candidates:
        img_bytes = download_image(c.thumb_url)
        if not img_bytes:
            continue
        thumb = make_thumbnail(img_bytes)
        if thumb:
            thumb_data.append(thumb)
            valid_candidates.append(c)

    if not thumb_data:
        print(f'  No valid thumbnails for: {content_path}')
        return False

    print(f'  Evaluating {len(thumb_data)} candidates with Gemini...')

    # Ask Gemini to pick the best
    page_text = f'Title: {meta.get("title", "")}\n\n{body[:1500]}'
    best_idx = pick_best_photo(valid_candidates, thumb_data, page_text, gemini_key)

    if best_idx is None:
        print(f'  Gemini: no suitable photo found')
        return False

    winner = valid_candidates[best_idx]
    print(f'  Winner: {winner.source} — {winner.source_page}')

    # Download full resolution
    full_bytes = download_image(winner.url)
    if not full_bytes:
        # Try other candidates as fallback
        for i, c in enumerate(valid_candidates):
            if i == best_idx:
                continue
            full_bytes = download_image(c.url)
            if full_bytes:
                winner = c
                print(f'  Fallback to: {winner.source} — {winner.source_page}')
                break

    if not full_bytes:
        print(f'  Failed to download winning photo')
        return False

    # Save and update
    filename = save_photo(full_bytes, md_path, slug)
    update_frontmatter(md_path, filename, winner.source_page, winner.license, winner.attribution, force)
    return True


def find_all_pages(page_type: str = 'location') -> list[str]:
    """Find all content pages of a given type, return as content paths."""
    import yaml

    pages = []
    for md_file in sorted(CONTENT_DIR.rglob('*.md')):
        text = md_file.read_text(encoding='utf-8', errors='replace')
        if not text.startswith('---'):
            continue
        match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
        if not match:
            continue
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except Exception:
            continue
        if meta.get('type') != page_type:
            continue

        # Convert filesystem path to content path
        rel = md_file.relative_to(CONTENT_DIR)
        # For locations: content/europe/netherlands/amsterdam/amsterdam.md → europe/netherlands/amsterdam
        # For sections: content/europe/netherlands/amsterdam/sights.md → europe/netherlands/amsterdam/sights
        if md_file.parent.name == md_file.stem:
            content_path = str(rel.parent)
        else:
            content_path = str(rel.with_suffix(''))
        pages.append(content_path)

    return pages


def main():
    parser = argparse.ArgumentParser(description='Find photos for World66 content pages')
    parser.add_argument('path', nargs='?', help='Content path (e.g., /europe/netherlands/amsterdam)')
    parser.add_argument('--gemini-key', help='Gemini API key (default: GEMINI_API_KEY env var)')
    parser.add_argument('--batch', action='store_true', help='Process all pages')
    parser.add_argument('--type', default='location', help='Page type filter for batch mode (default: location)')
    parser.add_argument('--force', action='store_true', help='Replace existing images')
    parser.add_argument('--dry-run', action='store_true', help='List pages without processing')
    args = parser.parse_args()

    gemini_key = args.gemini_key or os.environ.get('GEMINI_API_KEY')
    if not gemini_key:
        print('Error: Gemini API key required. Set GEMINI_API_KEY or use --gemini-key')
        sys.exit(1)

    if args.batch:
        pages = find_all_pages(args.type)
        print(f'Found {len(pages)} {args.type} pages')

        if args.dry_run:
            for p in pages:
                print(f'  {p}')
            return

        processed = load_progress()
        success = 0
        skipped = 0

        try:
            for i, content_path in enumerate(pages):
                if content_path in processed and not args.force:
                    skipped += 1
                    continue

                print(f'\n[{i + 1}/{len(pages)}]')
                if process_page(content_path, gemini_key, args.force):
                    success += 1

                processed.add(content_path)
                save_progress(processed)
                time.sleep(2)  # rate limit between pages

        except KeyboardInterrupt:
            print(f'\n\nInterrupted. Progress saved.')
            save_progress(processed)

        print(f'\nDone: {success} photos saved, {skipped} skipped (already processed)')

    elif args.path:
        process_page(args.path, gemini_key, args.force)

    else:
        parser.print_help()


if __name__ == '__main__':
    load_dotenv()
    main()
