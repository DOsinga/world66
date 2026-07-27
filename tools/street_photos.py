#!/usr/bin/env python3
from __future__ import annotations
"""
Fetch reference photos for a street poster and pull a palette out of them.

These images are *reference material* for drawing a poster by hand. They are
never committed, never published, and never shipped in the SVG -- so licence is
not a filter here (unlike tools/find_photo.py, which picks images the site
actually serves). Keep the output directory in a scratch path.

Primary route is WebSearch: search for the street, then feed the image URLs or
the pages that contain them to `add` / `scrape`. `search` is a fallback for when
you want direct image URLs without reading pages first.

Usage:
    # download image URLs found via WebSearch
    python3 tools/street_photos.py add --out /tmp/refs URL [URL ...]

    # pull the big images off a page found via WebSearch
    python3 tools/street_photos.py scrape --out /tmp/refs PAGE_URL [PAGE_URL ...]

    # fallback: keyword search that returns direct image URLs
    python3 tools/street_photos.py search "Susannenstrasse Hamburg" --out /tmp/refs

    # dominant colours across everything downloaded so far
    python3 tools/street_photos.py palette --out /tmp/refs --colors 8
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

USER_AGENT = 'World66StreetPoster/1.0 (https://world66.ai)'
TIMEOUT = 20
MIN_WIDTH = 500
MIN_HEIGHT = 350
MANIFEST_NAME = 'manifest.json'


def log(msg: str):
    """Progress goes to stderr so stdout stays clean JSON."""
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def search_openverse(query: str, limit: int) -> list[dict]:
    """Search Openverse (Flickr, Wikimedia, museums, ...). No API key needed."""
    try:
        resp = httpx.get(
            'https://api.openverse.org/v1/images/',
            params={'q': query, 'page_size': limit},
            headers={'User-Agent': USER_AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get('results', [])
    except Exception as e:
        log(f'  openverse search failed: {e}')
        return []

    out = []
    for r in results:
        url = r.get('url')
        if not url:
            continue
        out.append({
            'url': url,
            'title': r.get('title') or '',
            'source': 'openverse',
            'provider': r.get('provider') or '',
            'creator': r.get('creator') or '',
            'license': f"{r.get('license', '')} {r.get('license_version', '')}".strip(),
            'source_page': r.get('foreign_landing_url') or '',
        })
    return out


def search_commons(query: str, limit: int) -> list[dict]:
    """Search Wikimedia Commons for landscape photos."""
    try:
        resp = httpx.get(
            'https://commons.wikimedia.org/w/api.php',
            params={
                'action': 'query',
                'generator': 'search',
                'gsrnamespace': 6,
                'gsrsearch': f'{query} filetype:jpg|jpeg|png',
                'gsrlimit': limit,
                'prop': 'imageinfo',
                'iiprop': 'url|extmetadata|size|mime',
                'iiurlwidth': 1200,
                'format': 'json',
            },
            headers={'User-Agent': USER_AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        pages = resp.json().get('query', {}).get('pages', {})
    except Exception as e:
        log(f'  commons search failed: {e}')
        return []

    out = []
    for page in pages.values():
        info = (page.get('imageinfo') or [{}])[0]
        if 'svg' in info.get('mime', '') or 'gif' in info.get('mime', ''):
            continue
        ext = info.get('extmetadata', {})
        artist = re.sub(r'<[^>]+>', '', ext.get('Artist', {}).get('value', '')).strip()
        out.append({
            'url': info.get('thumburl') or info.get('url', ''),
            'title': page.get('title', ''),
            'source': 'commons',
            'provider': 'wikimedia',
            'creator': artist,
            'license': ext.get('LicenseShortName', {}).get('value', ''),
            'source_page': info.get('descriptionurl', ''),
        })
    return [c for c in out if c['url']]


def scrape_page(page_url: str) -> list[dict]:
    """Pull image URLs out of a page. Use with pages found via WebSearch."""
    try:
        resp = httpx.get(page_url, headers={'User-Agent': USER_AGENT},
                         timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        log(f'  scrape failed {page_url[:60]}: {e}')
        return []

    urls = []
    # src, data-src (lazy loading), and og:image
    for pat in (r'<img[^>]+(?:data-)?src=["\']([^"\']+)["\']',
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']'):
        urls += re.findall(pat, html, flags=re.I)

    out, seen = [], set()
    for u in urls:
        u = httpx.URL(page_url).join(u).__str__()
        if u in seen or not re.search(r'\.(jpe?g|png|webp)', u, flags=re.I):
            continue
        # Skip obvious chrome: icons, logos, avatars, tracking pixels.
        if re.search(r'(icon|logo|avatar|sprite|pixel|badge|thumb_?\d{1,2}x)', u, flags=re.I):
            continue
        seen.add(u)
        out.append({
            'url': u, 'title': '', 'source': 'scrape',
            'provider': httpx.URL(page_url).host, 'creator': '',
            'license': 'unknown (reference only)', 'source_page': page_url,
        })
    log(f'  {page_url[:60]}: {len(out)} image urls')
    return out


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download(candidate: dict, out_dir: Path) -> dict | None:
    """Fetch one image, reject anything too small to read detail from."""
    url = candidate['url']
    name = hashlib.sha1(url.encode()).hexdigest()[:12] + '.jpg'
    path = out_dir / name

    if path.exists():
        candidate['path'] = str(path)
        return candidate

    try:
        resp = httpx.get(url, headers={'User-Agent': USER_AGENT},
                         timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        img = Image.open(__import__('io').BytesIO(resp.content))
    except Exception as e:
        log(f'  skip {url[:60]}: {e}')
        return None

    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
        log(f'  skip {url[:60]}: too small ({img.width}x{img.height})')
        return None

    img = img.convert('RGB')
    img.thumbnail((1400, 1400))
    img.save(path, 'JPEG', quality=88)

    candidate['path'] = str(path)
    candidate['width'] = img.width
    candidate['height'] = img.height
    return candidate


def load_manifest(out_dir: Path) -> list[dict]:
    f = out_dir / MANIFEST_NAME
    if f.exists():
        return json.loads(f.read_text())
    return []


def save_manifest(out_dir: Path, items: list[dict]):
    (out_dir / MANIFEST_NAME).write_text(json.dumps(items, indent=2))


def merge(existing: list[dict], new: list[dict]) -> list[dict]:
    """Append new items, skipping URLs already in the manifest."""
    seen = {i['url'] for i in existing}
    return existing + [n for n in new if n['url'] not in seen]


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

def reference_images(out_dir: Path) -> list[Path]:
    """The reference set, in stable index order."""
    return sorted(p for p in out_dir.glob('*.jpg') if p.name != 'contact_sheet.jpg')


def contact_sheet(out_dir: Path, cols: int = 5, cell: int = 380) -> Path | None:
    """Tile every reference into one image, index-labelled, for `keep`."""
    images = reference_images(out_dir)
    if not images:
        return None

    rows = (len(images) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cell, rows * cell), '#202020')
    draw = ImageDraw.Draw(sheet)

    for i, p in enumerate(images):
        try:
            img = Image.open(p).convert('RGB')
        except Exception:
            continue
        img.thumbnail((cell - 8, cell - 30))
        ox, oy = (i % cols) * cell, (i // cols) * cell
        sheet.paste(img, (ox + (cell - img.width) // 2, oy + 26))
        # Index label -- `keep` takes these numbers.
        draw.rectangle([ox + 4, oy + 4, ox + 44, oy + 24], fill='#E8C86A')
        draw.text((ox + 12, oy + 8), str(i), fill='#101010')

    path = out_dir / 'contact_sheet.jpg'
    sheet.save(path, 'JPEG', quality=82)
    return path


def keep(out_dir: Path, indices: list[int]) -> tuple[int, int]:
    """Delete every reference except the given indices. Curate before palette."""
    images = reference_images(out_dir)
    wanted = {i for i in indices if 0 <= i < len(images)}
    kept_urls = []

    manifest = {m.get('path'): m for m in load_manifest(out_dir)}
    removed = 0
    for i, p in enumerate(images):
        if i in wanted:
            if str(p) in manifest:
                kept_urls.append(manifest[str(p)])
            continue
        p.unlink()
        removed += 1

    if kept_urls:
        save_manifest(out_dir, kept_urls)
    (out_dir / 'contact_sheet.jpg').unlink(missing_ok=True)
    return len(wanted), removed


def palette(out_dir: Path, n_colors: int) -> list[dict]:
    """Dominant colours across every downloaded image, most common first."""
    images = reference_images(out_dir)
    if not images:
        return []

    # Stack all references into one strip so quantisation sees them together.
    tiles = []
    for p in images:
        try:
            img = Image.open(p).convert('RGB').resize((160, 160))
        except Exception:
            continue
        tiles.append(img)
    if not tiles:
        return []

    strip = Image.new('RGB', (160 * len(tiles), 160))
    for i, t in enumerate(tiles):
        strip.paste(t, (i * 160, 0))

    quant = strip.quantize(colors=n_colors, method=Image.MEDIANCUT)
    pal = quant.getpalette()
    counts = sorted(quant.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)

    out = []
    for count, idx in counts:
        r, g, b = pal[idx * 3:idx * 3 + 3]
        out.append({
            'hex': f'#{r:02X}{g:02X}{b:02X}',
            'share': round(count / total, 3),
        })
    return out


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add', help='download specific image URLs (primary route)')
    a.add_argument('urls', nargs='+')
    a.add_argument('--out', required=True, help='scratch directory for references')

    sc = sub.add_parser('scrape', help='pull images off pages found via WebSearch')
    sc.add_argument('pages', nargs='+')
    sc.add_argument('--out', required=True)
    sc.add_argument('--limit', type=int, default=12, help='max images per page')

    s = sub.add_parser('search', help='fallback keyword search for direct image URLs')
    s.add_argument('query')
    s.add_argument('--out', required=True)
    s.add_argument('--limit', type=int, default=8, help='results per source')

    p = sub.add_parser('palette', help='dominant colours of downloaded references')
    p.add_argument('--out', required=True)
    p.add_argument('--colors', type=int, default=8)

    cs = sub.add_parser('sheet', help='tile references into one reviewable image')
    cs.add_argument('--out', required=True)
    cs.add_argument('--cols', type=int, default=5)

    k = sub.add_parser('keep', help='delete all references except these sheet indices')
    k.add_argument('indices', help='comma-separated, e.g. 3,7,12')
    k.add_argument('--out', required=True)

    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.cmd == 'palette':
        print(json.dumps({'palette': palette(out_dir, args.colors)}, indent=2))
        return 0

    if args.cmd == 'keep':
        idx = [int(i) for i in args.indices.replace(' ', '').split(',') if i]
        kept, removed = keep(out_dir, idx)
        log(f'kept {kept}, removed {removed}')
        print(json.dumps({'kept': kept, 'removed': removed}))
        return 0

    if args.cmd == 'sheet':
        path = contact_sheet(out_dir, args.cols)
        if not path:
            log('no images to tile')
            return 1
        print(path)
        return 0

    if args.cmd == 'search':
        log(f'searching: {args.query}')
        candidates = search_openverse(args.query, args.limit) + \
            search_commons(args.query, args.limit)
    elif args.cmd == 'scrape':
        candidates = []
        for page in args.pages:
            candidates += scrape_page(page)[:args.limit]
    else:
        candidates = [{'url': u, 'title': '', 'source': 'manual', 'provider': '',
                       'creator': '', 'license': 'unknown (reference only)',
                       'source_page': u} for u in args.urls]

    log(f'{len(candidates)} candidates, downloading...')
    got = [c for c in (download(c, out_dir) for c in candidates) if c]

    items = merge(load_manifest(out_dir), got)
    save_manifest(out_dir, items)

    log(f'{len(got)} downloaded, {len(items)} total in {out_dir}')
    print(json.dumps({'downloaded': got, 'total': len(items),
                      'dir': str(out_dir)}, indent=2))
    return 0 if got else 1


if __name__ == '__main__':
    sys.exit(main())
