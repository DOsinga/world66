#!/usr/bin/env python3
"""
Build a world region map for the "visited places" app.

Algorithm:
  1. Walk content/ for scored locations with coordinates.
  2. Transform raw score (≈0.3–1.0) into importance via a steep non-linear
     mapping so top destinations dominate: importance = 10 ** (score * IMPORTANCE_K).
  3. Start from Natural Earth admin-0 subunits (~308 polygons). These keep
     overseas territories (French Guiana, Réunion, Hawaii, Greenland, Cayman
     Islands, …) separate from their parent country.
  4. For each subunit whose total importance exceeds a budget, pick its top
     N cities by importance as Voronoi seeds, build the Voronoi diagram and
     clip each cell to the subunit polygon. Otherwise keep the subunit whole.
  5. Assign every scored location to its containing region (or the nearest one).
  6. Emit:
       static/geo/regions.geo.json   - polygons + id/name/parent
       static/geo/regions_data.json  - region_id -> {name, parent, top locations}
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import frontmatter
import shapely
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon, shape, mapping
from shapely.strtree import STRtree

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = PROJECT_DIR / "content"
SUBUNITS_PATH = SCRIPT_DIR / "raw" / "ne_50m_admin_0_map_subunits.geojson"
OUT_GEO = PROJECT_DIR / "static" / "geo" / "regions.geo.json"
OUT_DATA = PROJECT_DIR / "static" / "geo" / "regions_data.json"

# Tuning knobs.
#   IMPORTANCE_K: spread between bottom and top of score range.
#     k=4 makes 1.0 worth 100x a score of 0.5 (10**(1*4)=10000 vs 10**(0.5*4)=100).
#   BUDGET: max importance per region before subdivision. Smaller = more regions.
#   MAX_SPLITS_PER_SUBUNIT: hard cap so one huge country doesn't explode.
IMPORTANCE_K = 4.0
BUDGET = 6000.0
MAX_SPLITS_PER_SUBUNIT = 25
TOP_LOCATIONS_PER_REGION = 5


@dataclass
class Loc:
    path: str
    title: str
    snippet: str
    score: float
    lat: float
    lon: float
    loc_type: str

    @property
    def importance(self) -> float:
        return 10 ** (self.score * IMPORTANCE_K)


def first_paragraph(body: str) -> str:
    """Return the first non-empty paragraph, stripped of markdown links."""
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        # strip markdown links: [text](url) -> text
        chunk = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", chunk)
        # collapse whitespace
        chunk = re.sub(r"\s+", " ", chunk)
        return chunk
    return ""


def load_locations() -> list[Loc]:
    """Walk content/ and collect locations with a score and coordinates."""
    locs: list[Loc] = []
    for md in CONTENT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(md)
        except Exception:
            continue
        meta = post.metadata
        loc_type = meta.get("loc_type")
        if loc_type not in {"city", "country", "region"}:
            continue
        if "score" not in meta or "latitude" not in meta or "longitude" not in meta:
            continue
        try:
            score = float(meta["score"])
            lat = float(meta["latitude"])
            lon = float(meta["longitude"])
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        rel = md.relative_to(CONTENT_DIR).with_suffix("")
        path = str(rel)
        snippet = meta.get("snippet") or first_paragraph(post.content)
        if len(snippet) > 280:
            snippet = snippet[:277].rstrip() + "..."
        title = meta.get("title") or rel.name.replace("_", " ").title()
        locs.append(Loc(path=path, title=title, snippet=snippet,
                        score=score, lat=lat, lon=lon, loc_type=loc_type))
    return locs


def load_subunits() -> list[dict]:
    data = json.loads(SUBUNITS_PATH.read_text())
    features = []
    for f in data["features"]:
        p = f["properties"]
        # Drop weird overlays / military bases that aren't really places.
        if p.get("TYPE") in {"Overlay"}:
            continue
        # Antarctica subdivisions are messy; keep the main one only.
        try:
            geom = shape(f["geometry"])
        except Exception:
            continue
        if geom.is_empty:
            continue
        features.append({
            "su_a3": p.get("SU_A3"),
            "name": p.get("NAME") or p.get("NAME_LONG") or p.get("SU_A3"),
            "sovereign": p.get("SOVEREIGNT") or "",
            "geom": geom,
        })
    return features


def assign_locations_to_subunits(locs: list[Loc], subunits: list[dict]) -> dict[str, list[Loc]]:
    """Return su_a3 -> list of locs falling inside that subunit."""
    geoms = [s["geom"] for s in subunits]
    tree = STRtree(geoms)
    assigned: dict[str, list[Loc]] = defaultdict(list)

    for loc in locs:
        pt = Point(loc.lon, loc.lat)
        # Find candidates whose bbox contains the point, then refine.
        idxs = tree.query(pt)
        chosen = None
        for i in idxs:
            if geoms[i].contains(pt):
                chosen = subunits[i]
                break
        if chosen is None:
            # Fall back to nearest subunit (coastlines, geocoding offsets).
            nearest_i = tree.nearest(pt)
            chosen = subunits[nearest_i]
        assigned[chosen["su_a3"]].append(loc)

    return assigned


def safe_polygon_list(geom) -> list[Polygon]:
    """Flatten any geometry into a list of (possibly empty-filtered) Polygons."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [g for g in geom.geoms if not g.is_empty]
    # GeometryCollection: pick out polygons only
    out = []
    if hasattr(geom, "geoms"):
        for g in geom.geoms:
            if isinstance(g, (Polygon, MultiPolygon)):
                out.extend(safe_polygon_list(g))
    return out


def kmeans_seeds(locs: list[Loc], k: int, n_iters: int = 15) -> list[tuple[float, float]]:
    """Importance-weighted k-means. Initialise the K centroids with the top-K
    cities by importance (deterministic), then run Lloyd's iterations weighted
    by importance so the centroids drift toward the city-density mass.

    Returns a list of K (lon, lat) centroids. Cells that end up empty during
    iteration keep their previous position (rare with importance-weighted init).
    """
    # Initial centroids: prefer top-K cities; fall back to top-K of anything.
    cities = sorted([l for l in locs if l.loc_type == "city"],
                    key=lambda l: -l.importance)
    init = cities[:k] if len(cities) >= k else sorted(locs, key=lambda l: -l.importance)[:k]
    centroids: list[tuple[float, float]] = [(l.lon, l.lat) for l in init]

    # De-duplicate identical starts (very rare but breaks Voronoi later).
    seen = set()
    deduped = []
    for c in centroids:
        key = (round(c[0], 4), round(c[1], 4))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    centroids = deduped

    for _ in range(n_iters):
        # Assign each loc to nearest centroid (squared Euclidean is fine for
        # this — distances are local within one subunit).
        groups: list[list[Loc]] = [[] for _ in centroids]
        for l in locs:
            best_i, best_d = 0, float("inf")
            for i, (cx, cy) in enumerate(centroids):
                d = (cx - l.lon) ** 2 + (cy - l.lat) ** 2
                if d < best_d:
                    best_d, best_i = d, i
            groups[best_i].append(l)

        # Update each centroid to the importance-weighted mean of its group.
        new_centroids: list[tuple[float, float]] = []
        for i, group in enumerate(groups):
            if not group:
                new_centroids.append(centroids[i])
                continue
            total_w = sum(l.importance for l in group)
            cx = sum(l.lon * l.importance for l in group) / total_w
            cy = sum(l.lat * l.importance for l in group) / total_w
            new_centroids.append((cx, cy))

        if new_centroids == centroids:
            break
        centroids = new_centroids

    return centroids


def split_subunit(subunit: dict, locs: list[Loc], total_importance: float) -> list[dict]:
    """Split a high-importance subunit via Voronoi seeded by importance-weighted
    k-means centroids. Centroids drift toward where cities actually cluster,
    so dense areas with no single dominant city (northern Germany, the
    Randstad, …) get their own region centred on the cluster, not snapped to
    a far-away tourist hotspot.

    Returns a list of region dicts. Each region has: name, parent, geom, locs.
    """
    n_splits = min(MAX_SPLITS_PER_SUBUNIT, max(2, round(total_importance / BUDGET)))

    centroids = kmeans_seeds(locs, n_splits)
    if len(centroids) < 2:
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    points = MultiPoint(list(centroids))
    envelope = subunit["geom"].buffer(5.0).envelope  # generous so cells extend past borders

    try:
        voronoi = shapely.voronoi_polygons(points, extend_to=envelope, ordered=True)
        cells = list(voronoi.geoms)
    except Exception as e:
        print(f"voronoi failed for {subunit['name']}: {e}", file=sys.stderr)
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    if len(cells) != len(centroids):
        print(f"cell/seed mismatch in {subunit['name']}: {len(cells)} cells, {len(centroids)} centroids",
              file=sys.stderr)
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    # Clip each cell to the subunit polygon.
    regions = []
    for i, (centroid, cell) in enumerate(zip(centroids, cells)):
        clipped = cell.intersection(subunit["geom"])
        polys = safe_polygon_list(clipped)
        if not polys:
            continue
        clipped_geom = polys[0] if len(polys) == 1 else MultiPolygon(polys)
        regions.append({
            "name": None,  # set below from the cluster's top loc
            "parent": subunit["name"],
            "geom": clipped_geom,
            "centroid": centroid,
            "locs": [],
        })

    if not regions:
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    # Assign every loc to its nearest centroid (faster than point-in-polygon and
    # robust against floating-point gaps at cell boundaries).
    centroid_coords = [r["centroid"] for r in regions]
    for loc in locs:
        best_i = 0
        best_d = float("inf")
        for i, (lon, lat) in enumerate(centroid_coords):
            d = (lon - loc.lon) ** 2 + (lat - loc.lat) ** 2
            if d < best_d:
                best_d = d
                best_i = i
        regions[best_i]["locs"].append(loc)

    # Name each region after its highest-scoring location (centroids are mass
    # centres, not actual cities, so we can't name after the seed itself).
    for r in regions:
        if r["locs"]:
            top = max(r["locs"], key=lambda l: l.score)
            r["name"] = top.title
        else:
            r["name"] = subunit["name"]

    return regions


def build_regions() -> tuple[list[dict], dict[str, dict]]:
    print("Loading locations...", file=sys.stderr)
    locs = load_locations()
    print(f"  {len(locs)} scored locations with coordinates", file=sys.stderr)

    print("Loading subunits...", file=sys.stderr)
    subunits = load_subunits()
    print(f"  {len(subunits)} subunits", file=sys.stderr)

    print("Assigning locations to subunits...", file=sys.stderr)
    assigned = assign_locations_to_subunits(locs, subunits)

    total_world_importance = sum(l.importance for l in locs)
    print(f"World total importance: {total_world_importance:,.0f}", file=sys.stderr)
    print(f"Budget per region: {BUDGET:,.0f}", file=sys.stderr)

    print("Building regions...", file=sys.stderr)
    regions: list[dict] = []
    for su in subunits:
        su_locs = assigned.get(su["su_a3"], [])
        total = sum(l.importance for l in su_locs)
        if total <= BUDGET or len(su_locs) < 4:
            regions.append({
                "name": su["name"],
                "parent": su["sovereign"] or su["name"],
                "geom": su["geom"],
                "locs": su_locs,
            })
        else:
            sub_regions = split_subunit(su, su_locs, total)
            regions.extend(sub_regions)

    # Assign stable ids.
    used_ids: set[str] = set()
    def slugify(name: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        return s or "region"

    for i, r in enumerate(regions):
        base = slugify(r["name"])
        rid = base
        n = 2
        while rid in used_ids:
            rid = f"{base}_{n}"
            n += 1
        used_ids.add(rid)
        r["id"] = rid

    return regions, locs


def render_outputs(regions: list[dict]) -> None:
    OUT_GEO.parent.mkdir(parents=True, exist_ok=True)
    geo = {
        "type": "FeatureCollection",
        "features": [],
    }
    data: dict[str, dict] = {}

    for r in regions:
        top = sorted(r["locs"], key=lambda l: -l.score)[:TOP_LOCATIONS_PER_REGION]
        feature = {
            "type": "Feature",
            "id": r["id"],
            "properties": {
                "id": r["id"],
                "name": r["name"],
                "parent": r["parent"],
                "n_locs": len(r["locs"]),
                "top": top[0].title if top else "",
            },
            "geometry": mapping(r["geom"]),
        }
        geo["features"].append(feature)
        data[r["id"]] = {
            "name": r["name"],
            "parent": r["parent"],
            "n_locs": len(r["locs"]),
            "top_locations": [
                {
                    "title": l.title,
                    "snippet": l.snippet,
                    "path": l.path,
                    "score": l.score,
                    "lat": l.lat,
                    "lon": l.lon,
                }
                for l in top
            ],
        }

    OUT_GEO.write_text(json.dumps(geo))
    OUT_DATA.write_text(json.dumps(data, indent=1))
    print(f"Wrote {len(geo['features'])} regions to {OUT_GEO}", file=sys.stderr)
    print(f"Wrote region data to {OUT_DATA}", file=sys.stderr)


def main():
    regions, _ = build_regions()
    render_outputs(regions)


if __name__ == "__main__":
    main()
