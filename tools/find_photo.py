#!/usr/bin/env python3
"""
Find and assign copyright-free photos to World66 content pages.

Searches Wikimedia Commons and Flickr for landscape photos, uses an AI CLI
tool to pick the best match, and saves it next to the markdown file with
frontmatter updates.

Supports Gemini CLI, OpenAI Codex CLI, and Cline CLI. Auto-detects which
is installed, or use --cli to force one.

Usage:
    python tools/find_photo.py /europe/netherlands/amsterdam
    python tools/find_photo.py --batch --type location
    python tools/find_photo.py --batch --dry-run
    python tools/find_photo.py --cli codex /europe/france/paris
"""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import frontmatter
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

def _load_post(md_path: Path) -> tuple[dict, str]:
    """Load a markdown file. Returns (meta, body)."""
    post = frontmatter.load(md_path)
    return post.metadata, post.content


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
# AI CLI adapters for image classification
# ---------------------------------------------------------------------------

class CLIAdapter:
    """Base for AI CLI adapters that classify images."""

    name: str

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        """Send prompt + images to CLI, return text response."""
        raise NotImplementedError


class GeminiAdapter(CLIAdapter):
    """Gemini CLI — uses Google OAuth, no API key needed."""

    name = 'gemini'

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        file_refs = ' '.join(f'@{p}' for p in image_paths)
        result = subprocess.run(
            ['gemini', '-p', f'{prompt} {file_refs}'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f'gemini failed: {result.stderr}')
        return result.stdout.strip()


class CodexAdapter(CLIAdapter):
    """OpenAI Codex CLI — uses OpenAI login."""

    name = 'codex'

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        cmd = ['codex', 'exec', '--full-auto']
        for p in image_paths:
            cmd.extend(['-i', str(p)])
        cmd.append(prompt)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f'codex failed: {result.stderr}')
        return result.stdout.strip()


class ClineAdapter(CLIAdapter):
    """Cline CLI — configurable model provider."""

    name = 'cline'

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        cmd = ['cline', '-y']
        for p in image_paths:
            cmd.extend(['-i', str(p)])
        cmd.append(prompt)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f'cline failed: {result.stderr}')
        return result.stdout.strip()


CLI_ADAPTERS = [GeminiAdapter, CodexAdapter, ClineAdapter]


def get_cli_adapter(force: str = None) -> CLIAdapter:
    """Detect available CLI or use forced choice."""
    if force:
        for cls in CLI_ADAPTERS:
            if cls.name == force:
                if not shutil.which(force):
                    raise RuntimeError(f'{force} is not installed')
                return cls()
        raise RuntimeError(f'Unknown CLI: {force}. Choose from: {", ".join(c.name for c in CLI_ADAPTERS)}')
    for cls in CLI_ADAPTERS:
        if shutil.which(cls.name):
            return cls()
    raise RuntimeError('No supported AI CLI found. Install one of: gemini, codex, cline')


# ---------------------------------------------------------------------------
# Thumbnail creation and image evaluation
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


def pick_best_photo(candidates: list[Candidate], thumb_data: list[bytes], page_text: str, cli: CLIAdapter) -> int | None:
    """Use AI CLI to pick the best photo. Returns candidate index or None."""
    prompt = (
        f'You are selecting the best photo for a travel guide page. '
        f'Below are {len(thumb_data)} candidate photos numbered 0 to {len(thumb_data) - 1}.\n\n'
        f'Page content:\n{page_text[:1000]}\n\n'
        f'Pick the single best photo based on:\n'
        f'1. Relevance to this specific destination/topic\n'
        f'2. Visual quality and composition\n'
        f'3. How well it represents the place to a traveler\n\n'
        f'If NONE of the photos are suitable, respond with just "NONE".\n'
        f'Otherwise respond with just the number (0-{len(thumb_data) - 1}) of the best photo.'
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        image_paths = []
        for i, data in enumerate(thumb_data):
            path = Path(tmpdir) / f'photo_{i}.jpg'
            path.write_bytes(data)
            image_paths.append(path)

        try:
            answer = cli.run(prompt, image_paths)
        except Exception as e:
            print(f'  {cli.name} evaluation failed: {e}')
            return None

    if 'NONE' in answer.upper():
        return None

    match = re.search(r'\d+', answer)
    if match:
        idx = int(match.group())
        if 0 <= idx < len(thumb_data):
            return idx

    print(f'  {cli.name} returned unexpected answer: {answer}')
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


def update_frontmatter(md_path: Path, filename: str, source_url: str, license_str: str, attribution: str):
    """Update the markdown file's frontmatter with image fields."""
    post = frontmatter.load(md_path)
    post['image'] = filename
    post['image_source'] = source_url
    post['image_license'] = license_str
    post['image_attribution'] = attribution
    md_path.write_text(frontmatter.dumps(post, sort_keys=False) + '\n', encoding='utf-8')
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

def _search_candidates(content_path: str, meta: dict) -> tuple[list[Candidate], list[bytes], list[str]]:
    """Search for photo candidates, download thumbnails. Returns (valid_candidates, thumb_data, sources_searched)."""
    query = build_search_query(content_path, meta)
    print(f'  Search query: {query}', file=sys.stderr)

    sources_searched = ['wikimedia']
    if os.environ.get('FLICKR_API_KEY'):
        sources_searched.append('flickr')

    candidates = []
    for name, search_fn in [
        ('wikimedia', search_wikimedia),
        ('flickr', search_flickr),
    ]:
        results = search_fn(query)
        print(f'  {name}: {len(results)} candidates', file=sys.stderr)
        candidates.extend(results)
        time.sleep(0.5)

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

    return valid_candidates, thumb_data, sources_searched


def process_page_no_classify(content_path: str, force: bool = False) -> dict:
    """Search for candidates and return JSON-serializable result without AI classification."""
    md_path = resolve_md_path(content_path)
    if not md_path:
        return {'path': content_path, 'error': f'Not found: {content_path}'}

    meta, body = _load_post(md_path)

    if meta.get('image') and not force:
        return {'path': content_path, 'skipped': True, 'reason': 'already has image'}

    slug = md_path.stem
    print(f'Processing: {content_path}', file=sys.stderr)

    valid_candidates, thumb_data, sources_searched = _search_candidates(content_path, meta)

    if not thumb_data:
        return {
            'path': content_path,
            'md_file': str(md_path.relative_to(CONTENT_DIR.parent)),
            'title': meta.get('title', ''),
            'candidates': [],
            'sources_searched': sources_searched,
            'thumb_dir': None,
        }

    # Save thumbnails to deterministic temp dir
    thumb_dir = Path(tempfile.gettempdir()) / f'find_photo_{slug}'
    thumb_dir.mkdir(parents=True, exist_ok=True)

    candidate_list = []
    for i, (c, data) in enumerate(zip(valid_candidates, thumb_data)):
        thumb_path = thumb_dir / f'thumb_{i}.jpg'
        thumb_path.write_bytes(data)
        candidate_list.append({
            'index': i,
            'thumb_path': str(thumb_path),
            'url': c.url,
            'source': c.source,
            'width': c.width,
            'height': c.height,
            'license': c.license,
            'attribution': c.attribution,
            'source_page': c.source_page,
        })

    return {
        'path': content_path,
        'md_file': str(md_path.relative_to(CONTENT_DIR.parent)),
        'title': meta.get('title', ''),
        'candidates': candidate_list,
        'sources_searched': sources_searched,
        'thumb_dir': str(thumb_dir),
    }


def process_page_select(content_path: str, select_meta: dict) -> bool:
    """Download and save a pre-selected photo. Returns True on success."""
    md_path = resolve_md_path(content_path)
    if not md_path:
        print(f'  Not found: {content_path}', file=sys.stderr)
        return False

    slug = md_path.stem
    url = select_meta['url']
    print(f'Downloading selected photo: {url[:80]}...', file=sys.stderr)

    full_bytes = download_image(url)
    if not full_bytes:
        print(f'  Failed to download selected photo', file=sys.stderr)
        return False

    filename = save_photo(full_bytes, md_path, slug)
    update_frontmatter(
        md_path, filename,
        select_meta.get('source_page', ''),
        select_meta.get('license', ''),
        select_meta.get('attribution', ''),
    )
    return True


def process_page(content_path: str, cli: CLIAdapter, force: bool = False) -> bool:
    """Process a single page with AI classification. Returns True if a photo was saved."""
    md_path = resolve_md_path(content_path)
    if not md_path:
        print(f'  Not found: {content_path}')
        return False

    meta, body = _load_post(md_path)

    if meta.get('image') and not force:
        print(f'  Skipped (already has image): {content_path}')
        return False

    slug = md_path.stem
    print(f'Processing: {content_path}')

    valid_candidates, thumb_data, _ = _search_candidates(content_path, meta)

    if not thumb_data:
        print(f'  No valid candidates for: {content_path}')
        return False

    print(f'  Evaluating {len(thumb_data)} candidates with {cli.name}...')

    page_text = f'Title: {meta.get("title", "")}\n\n{body[:1500]}'
    best_idx = pick_best_photo(valid_candidates, thumb_data, page_text, cli)

    if best_idx is None:
        print(f'  {cli.name}: no suitable photo found')
        return False

    winner = valid_candidates[best_idx]
    print(f'  Winner: {winner.source} — {winner.source_page}')

    full_bytes = download_image(winner.url)
    if not full_bytes:
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

    filename = save_photo(full_bytes, md_path, slug)
    update_frontmatter(md_path, filename, winner.source_page, winner.license, winner.attribution)
    return True


def find_all_pages(page_type: str = 'location', prefix: str = None) -> list[str]:
    """Find all content pages of a given type, optionally filtered by path prefix."""
    pages = []
    for md_file in sorted(CONTENT_DIR.rglob('*.md')):
        try:
            meta = frontmatter.load(md_file).metadata
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

    if prefix:
        prefix = prefix.strip('/')
        pages = [p for p in pages if p.startswith(prefix)]
    return pages


def main():
    cli_names = [c.name for c in CLI_ADAPTERS]
    parser = argparse.ArgumentParser(description='Find photos for World66 content pages')
    parser.add_argument('path', nargs='?', help='Content path (e.g., /europe/netherlands/amsterdam)')
    parser.add_argument('--cli', choices=cli_names, help='Force a specific AI CLI (default: auto-detect)')
    parser.add_argument('--batch', action='store_true', help='Process all pages')
    parser.add_argument('--type', default='location', help='Page type filter for batch mode (default: location)')
    parser.add_argument('--prefix', help='Content path prefix for batch filtering (e.g., europe/netherlands)')
    parser.add_argument('--no-classify', action='store_true', help='Output JSON with candidates instead of AI classification')
    parser.add_argument('--select-meta', help='JSON metadata of chosen candidate (use with path)')
    parser.add_argument('--output', help='Write JSON output to file instead of stdout (use with --no-classify)')
    parser.add_argument('--force', action='store_true', help='Replace existing images')
    parser.add_argument('--dry-run', action='store_true', help='List pages without processing')
    args = parser.parse_args()

    if args.prefix and not args.batch:
        parser.error('--prefix requires --batch')
    if args.output and not args.no_classify:
        parser.error('--output requires --no-classify')

    # --select-meta mode: save a pre-selected photo
    if args.select_meta:
        if not args.path:
            parser.error('--select-meta requires a content path')
        try:
            meta = json.loads(args.select_meta)
        except json.JSONDecodeError as e:
            print(f'Invalid --select-meta JSON: {e}', file=sys.stderr)
            sys.exit(2)
        if process_page_select(args.path, meta):
            sys.exit(0)
        else:
            sys.exit(2)

    # Determine if we need a CLI adapter
    cli = None
    if not args.no_classify and not args.dry_run:
        cli = get_cli_adapter(args.cli)
        print(f'Using {cli.name} for image classification', file=sys.stderr)

    if args.batch:
        pages = find_all_pages(args.type, args.prefix)
        print(f'Found {len(pages)} {args.type} pages', file=sys.stderr)

        if args.dry_run:
            for p in pages:
                print(f'  {p}')
            return

        if args.no_classify:
            results = []
            for i, content_path in enumerate(pages):
                print(f'\n[{i + 1}/{len(pages)}]', file=sys.stderr)
                result = process_page_no_classify(content_path, args.force)
                results.append(result)
                time.sleep(1)

            output = json.dumps(results, indent=2)
            if args.output:
                Path(args.output).write_text(output)
                print(f'Written to {args.output}', file=sys.stderr)
            else:
                print(output)

            has_candidates = any(r.get('candidates') for r in results)
            sys.exit(0 if has_candidates else 1)

        processed = load_progress()
        success = 0
        skipped = 0

        try:
            for i, content_path in enumerate(pages):
                if content_path in processed and not args.force:
                    skipped += 1
                    continue

                print(f'\n[{i + 1}/{len(pages)}]')
                if process_page(content_path, cli, args.force):
                    success += 1

                processed.add(content_path)
                save_progress(processed)
                time.sleep(2)

        except KeyboardInterrupt:
            print('\n\nInterrupted. Progress saved.')
            save_progress(processed)

        print(f'\nDone: {success} photos saved, {skipped} skipped (already processed)')

    elif args.path:
        if args.no_classify:
            result = process_page_no_classify(args.path, args.force)
            output = json.dumps(result, indent=2)
            if args.output:
                Path(args.output).write_text(output)
                print(f'Written to {args.output}', file=sys.stderr)
            else:
                print(output)
            sys.exit(0 if result.get('candidates') else 1)
        else:
            success = process_page(args.path, cli, args.force)
            sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == '__main__':
    load_dotenv()
    main()
