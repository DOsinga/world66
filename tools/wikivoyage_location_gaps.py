#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import frontmatter
from scipy.spatial import cKDTree

from wikivoyage_neighborhood_pois import API_URL, USER_AGENT, distance_km, norm
from wikivoyage_poi_queue import batched, coord_to_xyz, metadata_float


CONTENT_DIR = Path("content")


@dataclass
class W66Place:
    path: str
    title: str
    page_type: str
    loc_type: str
    lat: float
    lng: float
    names: set[str]


def request_json(params: dict[str, str], retries: int = 4, retry_sleep: float = 30) -> dict:
    req = Request(f"{API_URL}?{urlencode(params)}", headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code != 429 or attempt >= retries:
                raise
            time.sleep(retry_sleep * (attempt + 1))
    raise RuntimeError("unreachable retry loop")


def wikivoyage_pages(
    limit: int | None = None,
    start_title: str | None = None,
    include_subpages: bool = False,
):
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": "0",
        "apfilterredir": "nonredirects",
        "aplimit": "max",
        "format": "json",
    }
    if start_title:
        params["apfrom"] = start_title

    seen = 0
    while True:
        data = request_json(params)
        for page in data.get("query", {}).get("allpages", []):
            title = page["title"]
            if "/" in title and not include_subpages:
                continue
            yield title
            seen += 1
            if limit and seen >= limit:
                return
        if "continue" not in data:
            return
        params.update(data["continue"])


def fetch_page_coordinates(titles: list[str]) -> list[dict]:
    data = request_json(
        {
            "action": "query",
            "prop": "coordinates|pageprops|categories",
            "colimit": "max",
            "cllimit": "max",
            "ppprop": "wikibase_item",
            "titles": "|".join(titles),
            "format": "json",
            "redirects": "1",
        }
    )
    rows = []
    for page in data.get("query", {}).get("pages", {}).values():
        coords = page.get("coordinates") or []
        if not coords:
            continue
        primary = next((coord for coord in coords if coord.get("primary") == ""), coords[0])
        rows.append(
            {
                "title": page["title"],
                "lat": float(primary["lat"]),
                "lng": float(primary["lon"]),
                "wikidata": page.get("pageprops", {}).get("wikibase_item", ""),
                "categories": sorted(category["title"] for category in page.get("categories", [])),
            }
        )
    return rows


def w66_places() -> list[W66Place]:
    rows = []
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        post = frontmatter.load(path)
        page_type = post.metadata.get("type")
        if page_type not in {"location", "feature", "neighbourhood"}:
            continue
        lat = metadata_float(post, "latitude")
        lng = metadata_float(post, "longitude")
        if lat is None or lng is None:
            continue
        title = str(post.metadata.get("title", path.stem))
        names = {norm(title), norm(path.stem)}
        for source in post.metadata.get("sources") or []:
            if isinstance(source, str) and "wikivoyage.org/wiki/" in source:
                names.add(norm(source.rsplit("/", 1)[-1].replace("_", " ")))
            elif isinstance(source, dict):
                url = source.get("url", "")
                if "wikivoyage.org/wiki/" in url:
                    names.add(norm(url.rsplit("/", 1)[-1].replace("_", " ")))
        rows.append(
            W66Place(
                path=str(path),
                title=title,
                page_type=str(page_type),
                loc_type=str(post.metadata.get("loc_type", "")),
                lat=lat,
                lng=lng,
                names={name for name in names if name},
            )
        )
    return rows


class PlaceIndex:
    def __init__(self, rows: list[W66Place]):
        self.rows = rows
        self.tree = cKDTree([coord_to_xyz(row.lat, row.lng) for row in rows])

    def nearest(self, lat: float, lng: float, k: int) -> list[tuple[W66Place, float]]:
        k = min(k, len(self.rows))
        _distances, indexes = self.tree.query(coord_to_xyz(lat, lng), k=k)
        if k == 1:
            indexes = [indexes]
        result = []
        for index in indexes:
            row = self.rows[int(index)]
            result.append((row, distance_km(lat, lng, row.lat, row.lng)))
        return sorted(result, key=lambda item: item[1])


def continent_path(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 2 and parts[0] == "content":
        return "/".join(parts[:2])
    return ""


def same_name_match(title: str, places: list[W66Place]) -> str:
    title_norm = norm(title.split("(", 1)[0])
    for place in places:
        if title_norm in place.names:
            return place.path
    return ""


def confidence(title: str, nearest: list[tuple[W66Place, float]], exact_match: str) -> str:
    if exact_match:
        return "matched"
    place, dist = nearest[0]
    if place.loc_type in {"continent", "country", "region", "state", "province"}:
        return "high"
    if dist > 25:
        return "high"
    if dist > 8:
        return "medium"
    if norm(title) in place.names:
        return "matched"
    return "low"


def wikivoyage_status(categories: list[str]) -> str:
    text = " ".join(categories)
    for status in ("Star", "Guide", "Usable", "Outline"):
        if f"Category:{status} " in text or f"Category:{status} articles" in text:
            return status.lower()
    return ""


def wikivoyage_kind(categories: list[str]) -> str:
    kinds = [
        ("city", "Category:City articles"),
        ("region", "Category:Region articles"),
        ("country", "Category:Country articles"),
        ("park", "Category:Park articles"),
        ("rural_area", "Category:Rural area articles"),
        ("airport", "Category:Airport articles"),
        ("district", "Category:District articles"),
    ]
    category_set = set(categories)
    for kind, category in kinds:
        if category in category_set:
            return kind
    return ""


def row_payload(row: dict, nearest: list[tuple[W66Place, float]], exact_match: str) -> dict:
    return {
        "title": row["title"],
        "source_url": f"https://en.wikivoyage.org/wiki/{row['title'].replace(' ', '_')}",
        "lat": row["lat"],
        "lng": row["lng"],
        "wikidata": row["wikidata"],
        "categories": row["categories"],
        "wikivoyage_status": wikivoyage_status(row["categories"]),
        "wikivoyage_kind": wikivoyage_kind(row["categories"]),
        "exact_w66_match": exact_match,
        "confidence": confidence(row["title"], nearest, exact_match),
        "nearest_w66": [
            {
                "path": place.path,
                "title": place.title,
                "type": place.page_type,
                "loc_type": place.loc_type,
                "distance_km": round(dist, 3),
            }
            for place, dist in nearest
        ],
        "nearest_continent": continent_path(nearest[0][0].path),
    }


def gap_rows(args):
    places = w66_places()
    index = PlaceIndex(places)
    titles = wikivoyage_pages(args.limit_pages, args.start_title, args.include_subpages)
    for title_batch in batched(titles, args.page_batch_size):
        for row in fetch_page_coordinates(title_batch):
            categories = set(row["categories"])
            if args.destination_only and "Category:All destination articles" not in categories:
                continue
            if categories.intersection(
                {
                    "Category:Itineraries",
                    "Category:Phrasebooks",
                    "Category:Travel topics",
                    "Category:Travel topic articles",
                }
            ):
                continue
            nearest = index.nearest(row["lat"], row["lng"], args.nearest_places)
            exact_match = same_name_match(row["title"], places)
            payload = row_payload(row, nearest, exact_match)
            if args.only_missing and payload["confidence"] == "matched":
                continue
            if args.min_confidence == "high" and payload["confidence"] != "high":
                continue
            if args.min_confidence == "medium" and payload["confidence"] not in {"high", "medium"}:
                continue
            yield payload


def write_jsonl(rows, output: Path) -> None:
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(rows, output: Path) -> None:
    fields = [
        "title",
        "source_url",
        "lat",
        "lng",
        "wikidata",
        "wikivoyage_status",
        "wikivoyage_kind",
        "categories",
        "confidence",
        "exact_w66_match",
        "nearest_continent",
        "nearest_w66",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: json.dumps(row[field], ensure_ascii=False)
                    if isinstance(row.get(field), (list, dict))
                    else row.get(field, "")
                    for field in fields
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    parser.add_argument("--limit-pages", type=int)
    parser.add_argument("--start-title")
    parser.add_argument("--include-subpages", action="store_true")
    parser.add_argument("--destination-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--min-confidence", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--nearest-places", type=int, default=5)
    parser.add_argument("--page-batch-size", type=int, default=50)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = gap_rows(args)
    if args.format == "csv":
        write_csv(rows, output)
    else:
        write_jsonl(rows, output)


if __name__ == "__main__":
    main()
