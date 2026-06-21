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
from shapely.ops import unary_union, orient
from shapely.strtree import STRtree

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = PROJECT_DIR / "content"
SUBUNITS_PATH = SCRIPT_DIR / "raw" / "ne_50m_admin_0_map_subunits.geojson"
OUT_GEO = PROJECT_DIR / "static" / "geo" / "regions.geo.json"
OUT_DATA = PROJECT_DIR / "static" / "geo" / "regions_data.json"
NAME_OVERRIDES_PATH = SCRIPT_DIR / "region_name_overrides.json"
MANUAL_SPLITS_PATH = SCRIPT_DIR / "manual_splits.json"

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
    image_url: str | None = None

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
        image_url = None
        image_file = meta.get("image", "")
        if image_file:
            for candidate in [
                f"{path}/{image_file}",
                f"{path.rsplit('/', 1)[0]}/{image_file}" if "/" in path else image_file,
            ]:
                if (CONTENT_DIR / candidate).is_file():
                    image_url = f"/content-image/{candidate}"
                    break
        locs.append(Loc(path=path, title=title, snippet=snippet,
                        score=score, lat=lat, lon=lon, loc_type=loc_type,
                        image_url=image_url))
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


_manual_splits: dict[str, list[tuple[float, float]]] | None = None

def load_manual_splits() -> dict[str, list[tuple[float, float]]]:
    global _manual_splits
    if _manual_splits is None:
        if MANUAL_SPLITS_PATH.exists():
            raw = json.loads(MANUAL_SPLITS_PATH.read_text())
            _manual_splits = {k: [tuple(c) for c in v] for k, v in raw.items() if not k.startswith("_")}
        else:
            _manual_splits = {}
    return _manual_splits


def split_subunit(subunit: dict, locs: list[Loc], total_importance: float) -> list[dict]:
    """Split a high-importance subunit into K regions with organic borders.

    1. Importance-weighted k-means picks K centroids.
    2. Each location is labelled by its nearest centroid.
    3. We compute the Voronoi diagram over every location (not just the K
       centroids), then merge cells that share a label. The resulting
       boundaries wind through the actual city tessellation instead of running
       as straight lines between centroids.
    4. Clip the merged regions to the subunit polygon.

    Returns a list of region dicts. Each region has: name, parent, geom, locs.
    """
    manual = load_manual_splits().get(subunit["su_a3"])
    if manual:
        centroids = manual
        n_splits = len(centroids)
        print(f"  Using {n_splits} manual seeds for {subunit['name']}", file=sys.stderr)
    else:
        n_splits = min(MAX_SPLITS_PER_SUBUNIT, max(2, round(total_importance / BUDGET)))
        centroids = kmeans_seeds(locs, n_splits)
    if len(centroids) < 2:
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    # Label each location by its nearest centroid.
    labels: list[int] = []
    for loc in locs:
        best_i, best_d = 0, float("inf")
        for i, (cx, cy) in enumerate(centroids):
            d = (cx - loc.lon) ** 2 + (cy - loc.lat) ** 2
            if d < best_d:
                best_d, best_i = d, i
        labels.append(best_i)

    # Voronoi over every location, so cell borders track real density.
    # Deduplicate coincident points: Voronoi treats them as one cell, which
    # would desynchronise the cells/locs zip below.
    coord_keys: list[tuple[float, float]] = []
    seen_coords: dict[tuple[float, float], int] = {}
    unique_indices: list[int] = []
    dup_to_keeper: dict[int, int] = {}
    for i, l in enumerate(locs):
        key = (round(l.lon, 5), round(l.lat, 5))
        if key in seen_coords:
            dup_to_keeper[i] = seen_coords[key]
            continue
        seen_coords[key] = i
        unique_indices.append(i)
        coord_keys.append(key)

    unique_points = MultiPoint([(locs[i].lon, locs[i].lat) for i in unique_indices])
    envelope = subunit["geom"].buffer(5.0).envelope  # generous so cells extend past borders

    try:
        voronoi = shapely.voronoi_polygons(unique_points, extend_to=envelope, ordered=True)
        cells = list(voronoi.geoms)
    except Exception as e:
        print(f"voronoi failed for {subunit['name']}: {e}", file=sys.stderr)
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    if len(cells) != len(unique_indices):
        print(f"cell/loc mismatch in {subunit['name']}: {len(cells)} cells, {len(unique_indices)} unique points",
              file=sys.stderr)
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    # Group cells by which centroid label their seed location was assigned to,
    # then merge each group into a single (multi)polygon. Borders inside the
    # subunit then follow the Voronoi tessellation between actual locations.
    cells_by_label: dict[int, list] = defaultdict(list)
    for cell, loc_i in zip(cells, unique_indices):
        cells_by_label[labels[loc_i]].append(cell)

    regions = []
    for label, label_cells in cells_by_label.items():
        merged = unary_union(label_cells)
        clipped = merged.intersection(subunit["geom"])
        polys = safe_polygon_list(clipped)
        if not polys:
            continue
        merged_geom = polys[0] if len(polys) == 1 else MultiPolygon(polys)
        regions.append({
            "name": None,
            "parent": subunit["name"],
            "geom": merged_geom,
            "centroid": centroids[label],
            "label": label,
            "locs": [],
        })

    if not regions:
        return [{
            "name": subunit["name"],
            "parent": subunit["sovereign"] or subunit["name"],
            "geom": subunit["geom"],
            "locs": locs,
        }]

    # Fill any gaps left by Voronoi clipping. When location clusters are
    # concentrated in one part of a subunit, the clipped Voronoi cells may
    # not cover the entire subunit polygon (e.g. remote coastal areas with no
    # nearby cities). Assign each gap piece to the nearest region by boundary
    # distance so the subunit is fully tiled with no holes.
    regions_union = unary_union([r["geom"] for r in regions])
    gap = subunit["geom"].difference(regions_union)
    if not gap.is_empty:
        gap_polys = safe_polygon_list(gap)
        for gap_poly in gap_polys:
            if gap_poly.is_empty:
                continue
            nearest = min(regions, key=lambda r: r["geom"].distance(gap_poly))
            merged = unary_union([nearest["geom"], gap_poly])
            nearest["geom"] = merged

    # Re-assign every loc into the region matching its centroid label (the
    # same labels used above), keeping the loc-grouping deterministic.
    label_to_region = {r["label"]: r for r in regions}
    for i, loc in enumerate(locs):
        r = label_to_region.get(labels[i])
        if r is not None:
            r["locs"].append(loc)

    # Name each region after its highest-scoring city (centroids are mass
    # centres, not actual cities). Skip the country/continent page if it
    # happens to land in the cell — naming a sub-region "Iceland" because the
    # Iceland country page is in it would be confusing.
    for r in regions:
        named = False
        for cand in sorted(r["locs"], key=lambda l: -l.score):
            if cand.loc_type in ("country", "continent"):
                continue
            r["name"] = cand.title
            named = True
            break
        if not named:
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
            # Whole-subunit region: keep the Natural Earth subunit name.
            regions.append({
                "name": su["name"],
                "parent": su["sovereign"] or su["name"],
                "geom": su["geom"],
                "locs": su_locs,
                "is_split": False,
            })
        else:
            sub_regions = split_subunit(su, su_locs, total)
            for r in sub_regions:
                r["is_split"] = True
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
    # Apply human-curated name overrides from region_name_overrides.json
    # (produced by per-country naming agents + manual dedup fixes). This
    # makes overrides.json the single source of truth for region names —
    # build_regions can be re-run safely without losing them.
    overrides: dict[str, str] = {}
    if NAME_OVERRIDES_PATH.exists():
        overrides = json.loads(NAME_OVERRIDES_PATH.read_text())
        for r in regions:
            if r["id"] in overrides:
                r["name"] = overrides[r["id"]]
        print(f"Applied {sum(1 for r in regions if r['id'] in overrides)} name overrides",
              file=sys.stderr)

    geo = {
        "type": "FeatureCollection",
        "features": [],
    }
    data: dict[str, dict] = {}

    for r in regions:
        # Don't surface continent/country pages as "destinations in this
        # region" — they're whole-territory pages that happen to have their
        # centroid land in a particular cell.
        display_locs = [l for l in r["locs"]
                        if l.loc_type not in ("country", "continent")]
        top = sorted(display_locs, key=lambda l: -l.score)[:TOP_LOCATIONS_PER_REGION]
        feature = {
            "type": "Feature",
            "id": r["id"],
            "properties": {
                "id": r["id"],
                "name": r["name"],
                "parent": r["parent"],
                "n_locs": len(display_locs),
                "top": top[0].title if top else "",
            },
            "geometry": mapping(orient(r["geom"], sign=1.0)),
        }
        geo["features"].append(feature)
        data[r["id"]] = {
            "name": r["name"],
            "parent": r["parent"],
            "n_locs": len(display_locs),
            "is_split": r.get("is_split", False),
            "top_locations": [
                {
                    "title": l.title,
                    "snippet": l.snippet,
                    "path": l.path,
                    "score": l.score,
                    "lat": l.lat,
                    "lon": l.lon,
                    "image_url": l.image_url,
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
