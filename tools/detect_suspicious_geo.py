#!/usr/bin/env python3
"""
Detect suspicious coordinates in World66 content using sibling-cluster outliers.

For each directory in content/, collect the lat/lon of every markdown page
directly in it, compute the median location, and flag any sibling whose
distance to the median is much larger than its peers'.

Output: tools/suspicious.txt — one line per flagged page:
    path/to/file.md  lat  lon  distance_km  cluster_size
"""

import math
import sys
from collections import defaultdict
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
CONTENT_DIR = SCRIPT_DIR.parent / "content"
OUTPUT_FILE = SCRIPT_DIR / "suspicious.txt"

# A cluster must have at least this many siblings with coords to be checked.
MIN_CLUSTER = 3
# Flag a point if its distance from the cluster median exceeds
# max(OUTLIER_MULT * median_sibling_distance, DISTANCE_FLOOR_KM).
OUTLIER_MULT = 6.0
DISTANCE_FLOOR_KM = 5.0


def parse_frontmatter(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            first = f.readline()
            if first.strip() != "---":
                return None
            buf = []
            for line in f:
                if line.strip() == "---":
                    break
                buf.append(line)
            return yaml.safe_load("".join(buf)) or {}
    except Exception:
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    m = n // 2
    if n % 2:
        return s[m]
    return (s[m - 1] + s[m]) / 2


def main():
    # Collect every page with coords.
    all_pages: list[tuple[Path, float, float]] = []
    for md in CONTENT_DIR.rglob("*.md"):
        fm = parse_frontmatter(md)
        if not fm:
            continue
        lat = fm.get("latitude")
        lon = fm.get("longitude")
        if lat is None or lon is None:
            continue
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            continue
        all_pages.append((md, lat, lon))

    total_pages = len(all_pages)

    # For each directory under content/, build a list of every descendant page
    # with coords (recursive members). A page in germany/beaches/ with no
    # siblings will fall back to germany/ or europe/.
    recursive_members: dict[Path, list[tuple[Path, float, float]]] = defaultdict(list)
    for entry in all_pages:
        md = entry[0]
        d = md.parent
        while True:
            recursive_members[d].append(entry)
            if d == CONTENT_DIR:
                break
            d = d.parent

    # Cache cluster stats per directory so we only compute median once.
    cluster_stats: dict[Path, tuple[float, float, float]] = {}

    def stats_for(d: Path) -> tuple[float, float, float]:
        cached = cluster_stats.get(d)
        if cached is not None:
            return cached
        members = recursive_members[d]
        mlat = median([m[1] for m in members])
        mlon = median([m[2] for m in members])
        mdist = median([haversine_km(la, lo, mlat, mlon) for _, la, lo in members])
        cluster_stats[d] = (mlat, mlon, mdist)
        return cluster_stats[d]

    flagged: list[tuple[Path, float, float, float, int, Path]] = []
    seen: set[Path] = set()

    for path, lat, lon in all_pages:
        # Walk up from the page's own directory to the deepest ancestor whose
        # recursive cluster has at least MIN_CLUSTER members.
        d = path.parent
        while True:
            if len(recursive_members[d]) >= MIN_CLUSTER:
                break
            if d == CONTENT_DIR:
                d = None
                break
            d = d.parent
        if d is None:
            continue

        mlat, mlon, mdist = stats_for(d)
        dist = haversine_km(lat, lon, mlat, mlon)
        threshold = max(OUTLIER_MULT * mdist, DISTANCE_FLOOR_KM)
        if dist > threshold and path not in seen:
            seen.add(path)
            flagged.append((path, lat, lon, dist, len(recursive_members[d]), d))

    # Stable sort: biggest outliers first.
    flagged.sort(key=lambda x: x[3], reverse=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for path, lat, lon, d, n, ref in flagged:
            rel = path.relative_to(SCRIPT_DIR.parent)
            ref_rel = ref.relative_to(SCRIPT_DIR.parent)
            f.write(f"{rel}\t{lat:.6f}\t{lon:.6f}\t{d:.0f}km\tref={ref_rel} cluster={n}\n")

    print(f"Scanned {total_pages} pages with coordinates.")
    print(f"Flagged {len(flagged)} suspicious pages -> {OUTPUT_FILE}")


if __name__ == "__main__":
    sys.exit(main())
