#!/usr/bin/env python3
from __future__ import annotations
"""
Render a street poster SVG to PNG and check it against the house style.

Rendering goes through headless Chrome, which every macOS dev box already has;
there is no cairo/rsvg dependency to install. Render after every edit and
actually look at the PNG -- the lint below catches structure, not ugliness.

Usage:
    python3 tools/render_poster.py poster.svg
    python3 tools/render_poster.py poster.svg --out preview.png --scale 2
    python3 tools/render_poster.py poster.svg --lint-only
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
WIDTH, HEIGHT = 1920, 1080

# Layers an animator addresses. Ordered back to front.
REQUIRED_LAYERS = [
    'layer-sky',
    'layer-far',
    'layer-mid',
    'layer-near',
    'layer-type',
]

# A 1950s screenprint has none of these. Flat spot colours only.
BANNED = {
    'linearGradient': 'gradients -- screenprints lay down flat ink',
    'radialGradient': 'gradients -- screenprints lay down flat ink',
    'filter': 'filters (blur/shadow) -- not achievable on press',
    'feGaussianBlur': 'blur -- not achievable on press',
    'image': 'embedded raster -- the poster must be pure vector',
}

# Six screens was already an expensive poster. Tints come from opacity, not
# from a seventh ink.
MAX_COLORS = 6


def find_chrome() -> str:
    if Path(CHROME).exists():
        return CHROME
    for alt in ('/Applications/Chromium.app/Contents/MacOS/Chromium',
                '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'):
        if Path(alt).exists():
            return alt
    print('error: no Chrome/Chromium found for rendering', file=sys.stderr)
    sys.exit(2)


def render(svg_path: Path, out_path: Path, scale: int) -> bool:
    """Render via an HTML wrapper so margins and scaling are deterministic."""
    svg = svg_path.read_text()
    html = (
        '<!doctype html><meta charset="utf-8">'
        '<style>html,body{margin:0;padding:0;overflow:hidden;'
        f'width:{WIDTH}px;height:{HEIGHT}px}}'
        f'svg{{display:block;width:{WIDTH}px;height:{HEIGHT}px}}</style>'
        + svg
    )

    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False,
                                     encoding='utf-8') as f:
        f.write(html)
        wrapper = f.name

    cmd = [
        find_chrome(), '--headless', '--disable-gpu', '--hide-scrollbars',
        '--no-sandbox', '--default-background-color=00000000',
        f'--force-device-scale-factor={scale}',
        f'--window-size={WIDTH},{HEIGHT}',
        f'--screenshot={out_path}',
        f'file://{wrapper}',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    Path(wrapper).unlink(missing_ok=True)

    if not out_path.exists():
        print(proc.stderr[-800:], file=sys.stderr)
        return False
    return True


def lint(svg_path: Path) -> list[str]:
    """Structural checks. Returns a list of problems."""
    svg = svg_path.read_text()
    problems = []

    m = re.search(r'<svg[^>]*viewBox=["\']([^"\']+)["\']', svg)
    if not m:
        problems.append('no viewBox on <svg>')
    elif m.group(1).split() != ['0', '0', str(WIDTH), str(HEIGHT)]:
        problems.append(f'viewBox is "{m.group(1)}", expected "0 0 {WIDTH} {HEIGHT}"')

    for layer in REQUIRED_LAYERS:
        if f'id="{layer}"' not in svg:
            problems.append(f'missing layer id="{layer}"')

    for tag, why in BANNED.items():
        if re.search(rf'<{tag}[\s>]', svg):
            problems.append(f'uses <{tag}>: {why}')

    colors = {c.upper() for c in re.findall(r'#[0-9a-fA-F]{6}', svg)}
    if len(colors) > MAX_COLORS:
        problems.append(
            f'{len(colors)} distinct colours (max {MAX_COLORS}): '
            f'{", ".join(sorted(colors))}'
        )

    if 'font-family' in svg and not re.search(r'<text|<tspan', svg):
        problems.append('font-family set but no <text> -- type layer empty?')

    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('svg')
    ap.add_argument('--out', help='PNG path (default: alongside the SVG)')
    ap.add_argument('--scale', type=int, default=1, help='device scale factor')
    ap.add_argument('--lint-only', action='store_true')
    args = ap.parse_args()

    svg_path = Path(args.svg)
    if not svg_path.exists():
        print(f'error: {svg_path} not found', file=sys.stderr)
        return 2

    problems = lint(svg_path)
    if problems:
        print('LINT:', file=sys.stderr)
        for p in problems:
            print(f'  - {p}', file=sys.stderr)
    else:
        print('LINT: clean', file=sys.stderr)

    if args.lint_only:
        return 1 if problems else 0

    out_path = Path(args.out) if args.out else svg_path.with_suffix('.png')
    if not render(svg_path, out_path, args.scale):
        print('error: render failed', file=sys.stderr)
        return 2

    print(f'{out_path}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
