#!/usr/bin/env python3
"""Generate variant B: plunging one-point perspective down the street."""
from pathlib import Path

W, H = 1920, 1080
VPX, VPY = 1180, 596

INK, PAPER, NAVY, VERM = '#101820', '#F0E2C4', '#1F3A5F', '#D6402A'

# Near-edge geometry of each wall. Lines run from these to the vanishing point.
LEFT = dict(x=0, top=20, bot=1020)
RIGHT = dict(x=1920, top=-60, bot=1080)

# Bay divisions along the run, foreshortening as they recede.
TS = [0.0, 0.17, 0.32, 0.45, 0.56, 0.655, 0.735, 0.80, 0.855]

# Fraction of facade height given over to the shopfront.
SHOP = 0.72


def lerp(a, b, t):
    return a + (b - a) * t


def wall_pt(w, t, which):
    """Point at parameter t along the wall's top or bottom line."""
    x = lerp(w['x'], VPX, t)
    y = lerp(w[which], VPY, t)
    return x, y


def quad(pts, fill, opacity=None):
    d = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    o = f' opacity="{opacity}"' if opacity else ''
    return f'<polygon points="{d}" fill="{fill}"{o}/>'


def bilinear(A, B, C, D, u, v):
    """A,B top-left/right; D,C bottom-left/right. u across, v down."""
    tx = lerp(A[0], B[0], u), lerp(A[1], B[1], u)
    bx = lerp(D[0], C[0], u), lerp(D[1], C[1], u)
    return lerp(tx[0], bx[0], v), lerp(tx[1], bx[1], v)


def build_wall(w, side):
    """One receding row of buildings."""
    out = []
    # Alternate roof heights so the parapet line is not a single ruled edge.
    bumps = [0.0, 0.055, 0.02, 0.075, 0.03, 0.06, 0.015, 0.05]

    for i in range(len(TS) - 1):
        t0, t1 = TS[i], TS[i + 1]
        depth = i / (len(TS) - 2)

        # bay corners
        A = wall_pt(w, t0, 'top'); B = wall_pt(w, t1, 'top')
        D = wall_pt(w, t0, 'bot'); C = wall_pt(w, t1, 'bot')
        # push the roof of this bay up by its bump
        bump = bumps[i % len(bumps)]
        A = (A[0], A[1] - bump * (D[1] - A[1]))
        B = (B[0], B[1] - bump * (C[1] - B[1]))

        # facade, darker as it recedes
        shade = 0.30 + 0.42 * depth
        out.append(quad([A, B, C, D], NAVY))
        out.append(quad([A, B, C, D], INK, round(shade, 3)))

        # parapet cap
        cap = 0.035
        Ac = (A[0], A[1] - cap * (D[1] - A[1]))
        Bc = (B[0], B[1] - cap * (C[1] - B[1]))
        out.append(quad([Ac, Bc, B, A], INK, 0.85))

        # windows: two rows, three per bay, fading out with distance
        cols = 3 if depth < 0.75 else 2
        for r, (v0, v1) in enumerate([(0.16, 0.34), (0.44, 0.62)]):
            for c in range(cols):
                u0 = 0.14 + c * (0.72 / cols)
                u1 = u0 + (0.72 / cols) * 0.52
                pts = [bilinear(A, B, C, D, u0, v0), bilinear(A, B, C, D, u1, v0),
                       bilinear(A, B, C, D, u1, v1), bilinear(A, B, C, D, u0, v1)]
                lit = (i + c + r) % 5 == 0
                out.append(quad(pts, PAPER if lit else INK,
                                None if lit else round(0.55 + 0.2 * depth, 3)))

        # shopfront: fascia, awning, then lit glass -- a shallow stack, not a sail
        pts = [bilinear(A, B, C, D, 0.0, SHOP), bilinear(A, B, C, D, 1.0, SHOP),
               bilinear(A, B, C, D, 1.0, 1.0), bilinear(A, B, C, D, 0.0, 1.0)]
        out.append(quad(pts, INK, 0.94))

        # lit glass first, so the awning overlaps it
        pts = [bilinear(A, B, C, D, 0.10, SHOP + 0.13), bilinear(A, B, C, D, 0.90, SHOP + 0.13),
               bilinear(A, B, C, D, 0.90, 0.97), bilinear(A, B, C, D, 0.10, 0.97)]
        out.append(quad(pts, VERM if i % 3 == 1 else PAPER,
                        round(0.97 - 0.22 * depth, 3)))

        # fascia band
        pts = [bilinear(A, B, C, D, 0.0, SHOP), bilinear(A, B, C, D, 1.0, SHOP),
               bilinear(A, B, C, D, 1.0, SHOP + 0.055), bilinear(A, B, C, D, 0.0, SHOP + 0.055)]
        out.append(quad(pts, INK))

        # awning, alternating, the rhythm that carries the eye down the street
        aw0, aw1 = SHOP + 0.055, SHOP + 0.10
        pts = [bilinear(A, B, C, D, 0.03, aw0), bilinear(A, B, C, D, 0.97, aw0),
               bilinear(A, B, C, D, 0.90, aw1), bilinear(A, B, C, D, 0.10, aw1)]
        out.append(quad(pts, VERM if i % 3 == 0 else PAPER))

    return out


def main():
    L = build_wall(LEFT, 'L')
    R = build_wall(RIGHT, 'R')

    # ground: the wedge between the two bottom lines
    gl = [wall_pt(LEFT, t, 'bot') for t in TS]
    gr = [wall_pt(RIGHT, t, 'bot') for t in reversed(TS)]
    ground = [(0, 1080)] + gl + gr + [(1920, 1080)]

    # receding kerb lines
    kerbs = []
    for f in (0.30, 0.62):
        a = (lerp(0, VPX, 0), lerp(1020, VPY, 0))
        pass
    # kerb: a line from each near bottom corner toward the VP, inset
    def inset_line(w, frac):
        nx = lerp(w['x'], VPX, 0)
        ny = lerp(w['bot'], VPY, 0)
        px = lerp(nx, VPX, frac)
        py = lerp(ny, VPY, frac)
        return (nx, ny), (px, py)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
               f'viewBox="0 0 {W} {H}" role="img" '
               f'aria-label="Travel poster of Susannenstrasse, Hamburg — perspective idiom">')
    svg.append('  <title>Susannenstrasse — Hamburg (B: perspective)</title>')
    svg.append('''
  <!--
    Variant B. Cassandre idiom: steep one-point perspective driving down the
    street, awnings receding to the vanishing point, four inks only.
    Perspective points are computed, not hand-placed.
      INK #101820  PAPER #F0E2C4  NAVY #1F3A5F  VERM #D6402A
  -->''')
    svg.append('''
  <defs>
    <pattern id="b-dots" width="10" height="10" patternUnits="userSpaceOnUse">
      <circle cx="2.4" cy="2.4" r="1.7" fill="#101820"/>
    </pattern>
  </defs>''')

    # sky
    svg.append('  <g id="layer-sky">')
    svg.append(f'    <rect width="{W}" height="{H}" fill="{NAVY}"/>')
    svg.append(f'    <rect width="{W}" height="700" fill="url(#b-dots)" opacity="0.18"/>')
    svg.append(f'    <circle cx="{VPX}" cy="{VPY-232}" r="88" fill="{VERM}"/>')
    svg.append('  </g>')

    # far: the building closing the vista
    svg.append('  <g id="layer-far">')
    svg.append('    ' + quad([(VPX-112, VPY-96), (VPX+112, VPY-96),
                              (VPX+112, VPY+92), (VPX-112, VPY+92)], INK, 0.82))
    svg.append('    ' + quad([(VPX-124, VPY-96), (VPX, VPY-150),
                              (VPX+124, VPY-96)], INK, 0.9))
    svg.append(f'    <rect x="{VPX-72}" y="{VPY-62}" width="38" height="48" fill="{PAPER}" opacity="0.42"/>')
    svg.append(f'    <rect x="{VPX-19}" y="{VPY-62}" width="38" height="48" fill="{PAPER}" opacity="0.34"/>')
    svg.append(f'    <rect x="{VPX+34}" y="{VPY-62}" width="38" height="48" fill="{PAPER}" opacity="0.42"/>')
    svg.append('  </g>')

    # mid: ground
    svg.append('  <g id="layer-mid">')
    svg.append('    ' + quad(ground, PAPER))
    svg.append('    ' + quad(ground, INK, 0.12))
    for w in (LEFT, RIGHT):
        (nx, ny), (px, py) = inset_line(w, 0.86)
        dy = 70 if w is LEFT else 70
        svg.append(f'    <polygon points="{nx:.0f},{ny+dy:.0f} {px:.0f},{py+4:.0f} '
                   f'{px:.0f},{py-4:.0f} {nx:.0f},{ny+dy-26:.0f}" fill="{INK}" opacity="0.22"/>')
    # paving converging on the vanishing point
    for x in (140, 430, 720, 1010, 1300, 1590, 1880):
        svg.append(f'    <line x1="{x}" y1="1080" x2="{VPX}" y2="{VPY}" '
                   f'stroke="{INK}" stroke-width="3" opacity="0.10"/>')
    for t in (0.14, 0.30, 0.44, 0.56, 0.66):
        (lx, ly) = wall_pt(LEFT, t, 'bot'); (rx, ry) = wall_pt(RIGHT, t, 'bot')
        svg.append(f'    <line x1="{lx:.0f}" y1="{ly:.0f}" x2="{rx:.0f}" y2="{ry:.0f}" '
                   f'stroke="{INK}" stroke-width="3" opacity="0.09"/>')
    svg.append('  </g>')

    # near: the two walls
    svg.append('  <g id="layer-near">')
    svg.append('    <g id="wall-left">')
    svg += ['      ' + e for e in L]
    svg.append('    </g>')
    svg.append('    <g id="wall-right">')
    svg += ['      ' + e for e in R]
    svg.append('    </g>')
    # people down the street, sized by depth -- gives the perspective its scale
    people = []
    for t, f, stride in ((0.18, 0.28, 1), (0.18, 0.76, -1), (0.36, 0.50, 1),
                         (0.36, 0.18, -1), (0.50, 0.68, 1), (0.60, 0.38, -1),
                         (0.68, 0.56, 1)):
        (lx, ly) = wall_pt(LEFT, t, 'bot')
        (rx, ry) = wall_pt(RIGHT, t, 'bot')
        x = lerp(lx, rx, f)
        y = lerp(ly, ry, f)
        h = 250 * (1 - t) + 18
        w = h * 0.22
        op = round(0.92 - 0.22 * t, 2)
        people.append(
            f'<g fill="{INK}" opacity="{op}">'
            f'<circle cx="{x:.0f}" cy="{y - h * 0.88:.0f}" r="{h * 0.105:.0f}"/>'
            f'<path d="M{x - w * 0.5:.0f} {y - h * 0.36:.0f} '
            f'L{x - w * 0.5:.0f} {y - h * 0.72:.0f} '
            f'A{w * 0.5:.0f} {w * 0.5:.0f} 0 0 1 {x + w * 0.5:.0f} {y - h * 0.72:.0f} '
            f'L{x + w * 0.5:.0f} {y - h * 0.36:.0f} Z"/>'
            f'<path d="M{x - w * 0.46:.0f} {y - h * 0.38:.0f} '
            f'L{x - w * 0.04:.0f} {y - h * 0.38:.0f} '
            f'L{x - w * 0.10 + stride * w * 0.16:.0f} {y:.0f} '
            f'L{x - w * 0.48 + stride * w * 0.16:.0f} {y:.0f} Z"/>'
            f'<path d="M{x + w * 0.04:.0f} {y - h * 0.38:.0f} '
            f'L{x + w * 0.46:.0f} {y - h * 0.38:.0f} '
            f'L{x + w * 0.50 - stride * w * 0.16:.0f} {y:.0f} '
            f'L{x + w * 0.12 - stride * w * 0.16:.0f} {y:.0f} Z"/>'
            f'</g>')
    svg.append('      ' + '\n      '.join(people))
    svg.append('  </g>')

    # type
    svg.append(f'''  <g id="layer-type" font-family="Futura,'Century Gothic','Avenir Next',sans-serif">
    <text x="110" y="88" font-size="27" font-weight="bold" letter-spacing="13" fill="{VERM}">HAMBURG · SCHANZENVIERTEL</text>
    <rect x="112" y="106" width="470" height="4" fill="{VERM}"/>
    <rect x="0" y="950" width="{W}" height="130" fill="{INK}"/>
    <text x="110" y="1032" font-size="82" font-weight="bold" letter-spacing="16" fill="{PAPER}">SUSANNENSTRASSE</text>
    <text x="1810" y="1030" font-size="25" font-weight="bold" letter-spacing="7" fill="{VERM}" text-anchor="end">LEDER · VINYL · BLUMEN</text>
  </g>''')
    svg.append('</svg>')

    out = Path('/Users/richardosinga/Repos/world66-street-poster/prototypes/'
               'street-posters/susannenstrasse/variants/b-perspective.svg')
    out.write_text('\n'.join(svg) + '\n')
    print(out)


if __name__ == '__main__':
    main()
