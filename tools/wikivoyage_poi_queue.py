#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import frontmatter
import numpy as np
from scipy.spatial import cKDTree

from wikivoyage_neighborhood_pois import (
    API_URL,
    USER_AGENT,
    clean_text,
    distance_km,
    iter_templates,
    norm,
    split_template,
)


CONTENT_DIR = Path("content")


@dataclass
class W66Poi:
    path: str
    parent_path: str
    title: str
    norm_title: str
    lat: float
    lng: float
    tags: list[str]
    score: float | None
    sources: str


@dataclass
class W66Place:
    path: str
    parent_path: str
    title: str
    page_type: str
    lat: float
    lng: float


def api_query(params: dict[str, str]) -> dict:
    req = Request(f"{API_URL}?{urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def wikivoyage_pages(limit: int | None = None, start_title: str | None = None):
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": "0",
        "aplimit": "max",
        "format": "json",
    }
    if start_title:
        params["apfrom"] = start_title

    seen = 0
    while True:
        data = api_query(params)
        for page in data.get("query", {}).get("allpages", []):
            yield page["title"]
            seen += 1
            if limit and seen >= limit:
                return
        if "continue" not in data:
            return
        params.update(data["continue"])


def cache_path(cache_dir: Path, title: str) -> Path:
    safe = norm(title) or "root"
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:12]
    return cache_dir / f"{safe}-{digest}.wikitext"


def request_json(params: dict[str, str], retries: int, retry_sleep: float) -> dict:
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


def batched(rows, size: int):
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def fetch_wikitext_batch(
    titles: list[str],
    cache_dir: Path | None,
    retries: int,
    retry_sleep: float,
) -> dict[str, str]:
    texts = {}
    missing = []
    for title in titles:
        if cache_dir:
            path = cache_path(cache_dir, title)
            if path.exists():
                texts[title] = path.read_text(encoding="utf-8")
                continue
        missing.append(title)

    if missing:
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(missing),
            "format": "json",
            "redirects": "1",
        }
        data = request_json(params, retries, retry_sleep)
        by_title = {}
        for page in data.get("query", {}).get("pages", {}).values():
            if "missing" in page:
                continue
            revision = page.get("revisions", [{}])[0]
            slot = revision.get("slots", {}).get("main", {})
            text = slot.get("*") or slot.get("content") or revision.get("*") or ""
            by_title[page["title"]] = text

        redirects = {row["from"]: row["to"] for row in data.get("query", {}).get("redirects", [])}
        normalized = {row["from"]: row["to"] for row in data.get("query", {}).get("normalized", [])}
        for title in missing:
            resolved = redirects.get(normalized.get(title, title), normalized.get(title, title))
            text = by_title.get(resolved, by_title.get(title, ""))
            texts[title] = text
            if cache_dir and text:
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path(cache_dir, title).write_text(text, encoding="utf-8")
    return texts


def listings_from_text(source_page: str, text: str):
    for template in iter_templates(text):
        data = split_template(template)
        name = clean_text(data.get("name", ""))
        content = clean_text(data.get("content", ""))
        lat = data.get("lat") or data.get("latitude")
        lng = data.get("long") or data.get("lon") or data.get("longitude")
        if not name or not lat or not lng or len(content) < 40:
            continue
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except ValueError:
            continue
        yield {
            "source_page": source_page,
            "kind": data["kind"],
            "name": name,
            "lat": lat_f,
            "lng": lng_f,
            "content": content,
            "url": data.get("url", ""),
            "wikipedia": data.get("wikipedia", ""),
            "wikidata": data.get("wikidata", ""),
        }


def coord_to_xyz(lat: float, lng: float) -> tuple[float, float, float]:
    lat_rad = np.radians(lat)
    lng_rad = np.radians(lng)
    return (
        float(np.cos(lat_rad) * np.cos(lng_rad)),
        float(np.cos(lat_rad) * np.sin(lng_rad)),
        float(np.sin(lat_rad)),
    )


def metadata_float(post: frontmatter.Post, key: str) -> float | None:
    if key not in post.metadata:
        return None
    try:
        return float(post.metadata[key])
    except (TypeError, ValueError):
        return None


def source_text(value) -> str:
    if not value:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def w66_pois() -> list[W66Poi]:
    rows = []
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        post = frontmatter.load(path)
        if post.metadata.get("type") != "poi":
            continue
        lat = metadata_float(post, "latitude")
        lng = metadata_float(post, "longitude")
        if lat is None or lng is None:
            continue
        title = str(post.metadata.get("title", path.stem))
        score = metadata_float(post, "score")
        rows.append(
            W66Poi(
                path=str(path),
                parent_path=str(path.parent),
                title=title,
                norm_title=norm(title),
                lat=lat,
                lng=lng,
                tags=list(post.metadata.get("tags") or []),
                score=score,
                sources=source_text(post.metadata.get("sources")),
            )
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
        rows.append(
            W66Place(
                path=str(path),
                parent_path=str(path.parent),
                title=str(post.metadata.get("title", path.stem)),
                page_type=str(page_type),
                lat=lat,
                lng=lng,
            )
        )
    return rows


def neighbourhood_slugs() -> dict[str, set[str]]:
    rows: dict[str, set[str]] = {}
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        post = frontmatter.load(path)
        if post.metadata.get("type") != "neighbourhood":
            continue
        rows.setdefault(str(path.parent), set()).add(path.stem)
    return rows


class GeoIndex:
    def __init__(self, rows):
        self.rows = rows
        self.tree = cKDTree([coord_to_xyz(row.lat, row.lng) for row in rows])

    def nearest(self, lat: float, lng: float, k: int):
        k = min(k, len(self.rows))
        distances, indexes = self.tree.query(coord_to_xyz(lat, lng), k=k)
        if k == 1:
            indexes = [indexes]
        result = []
        for index in indexes:
            row = self.rows[int(index)]
            result.append((row, distance_km(lat, lng, row.lat, row.lng)))
        return sorted(result, key=lambda item: item[1])


def name_ratio(a: str, b: str) -> float:
    import difflib

    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def low_value_reasons(name: str, content: str) -> list[str]:
    text = f"{name} {content}".lower()
    patterns = {
        "accommodation": (" hotel", " hostel", " motel", " guesthouse", " resort", " apartment"),
        "transport": ("airport", " railway station", " train station", " bus station", " metro station"),
        "consular": ("embassy", "consulate", "high commission"),
        "generic_shop": ("shopping mall", "department store", "supermarket", "souvenir shop"),
    }
    reasons = []
    for reason, needles in patterns.items():
        if any(needle in text for needle in needles):
            reasons.append(reason)
    if len(content) < 80:
        reasons.append("thin_description")
    return reasons


def duplicate_flags(candidate, neighbours: list[tuple[W66Poi, float]]) -> tuple[list[str], list[str]]:
    hard = []
    soft = []
    candidate_norm = norm(candidate["name"])
    source_page = f"https://en.wikivoyage.org/wiki/{candidate['source_page'].replace(' ', '_')}"
    for poi, dist in neighbours:
        ratio = name_ratio(candidate["name"], poi.title)
        exact_name = candidate_norm == poi.norm_title
        contained_name = (
            min(len(candidate_norm), len(poi.norm_title)) >= 8
            and (candidate_norm in poi.norm_title or poi.norm_title in candidate_norm)
        )
        source_seen = source_page in poi.sources
        if exact_name and dist <= 10:
            hard.append(f"exact_name:{dist:.2f}km:{poi.path}")
        elif contained_name and dist <= 1:
            hard.append(f"contained_name:{dist:.2f}km:{poi.path}")
        elif source_seen and ratio >= 0.82:
            hard.append(f"same_wikivoyage_source:{dist:.2f}km:{poi.path}")
        elif ratio >= 0.94 and dist <= 0.35:
            hard.append(f"very_similar_name:{dist:.2f}km:{poi.path}")
        elif exact_name and dist <= 2.0:
            soft.append(f"same_name_nearby:{dist:.2f}km:{poi.path}")
        elif ratio >= 0.86 and dist <= 1.0:
            soft.append(f"similar_name_nearby:{dist:.2f}km:{poi.path}")
    return hard, soft


def proposed_assignment(
    neighbours: list[tuple[W66Poi, float]],
    place_neighbours: list[tuple[W66Place, float]],
    nbhds: dict[str, set[str]],
) -> tuple[str, str, str]:
    close = [(poi, dist) for poi, dist in neighbours if dist <= 5]
    if close:
        parent_counts = Counter(poi.parent_path for poi, _ in close[:10])
        parent_path = parent_counts.most_common(1)[0][0]
        tag_counts = Counter(
            tag
            for poi, _ in close[:10]
            if poi.parent_path == parent_path
            for tag in poi.tags
            if tag in nbhds.get(parent_path, set())
        )
        neighbourhood = tag_counts.most_common(1)[0][0] if tag_counts else ""
        return parent_path, neighbourhood, "nearest_poi_cluster"

    place, _dist = place_neighbours[0]
    if place.page_type == "neighbourhood":
        return place.parent_path, Path(place.path).stem, "nearest_neighbourhood_fallback"
    if place.page_type == "feature":
        return str(Path(place.path).with_suffix("")), "", "nearest_feature_fallback"
    return str(Path(place.path).with_suffix("")), "", "nearest_location_fallback"


def nearest_payload(neighbours: list[tuple[W66Poi, float]]) -> list[dict]:
    return [
        {
            "path": poi.path,
            "title": poi.title,
            "distance_km": round(dist, 3),
            "tags": poi.tags,
            "score": poi.score,
        }
        for poi, dist in neighbours
    ]


def candidate_rows(args):
    poi_rows = w66_pois()
    place_rows = w66_places()
    poi_index = GeoIndex(poi_rows)
    place_index = GeoIndex(place_rows)
    nbhds = neighbourhood_slugs()
    seen = set()

    pages = wikivoyage_pages(args.limit_pages, args.start_title)
    for page_batch in batched(pages, args.page_batch_size):
        try:
            texts = fetch_wikitext_batch(page_batch, args.cache_dir, args.retries, args.retry_sleep)
        except Exception as exc:
            print(f"warning: skipped page batch starting {page_batch[0]}: {exc}", file=__import__("sys").stderr)
            continue
        for source_page, text in texts.items():
            if not text:
                continue
            try:
                listings = listings_from_text(source_page, text)
                for listing in listings:
                    key = (norm(listing["name"]), round(listing["lat"], 5), round(listing["lng"], 5))
                    if key in seen:
                        continue
                    seen.add(key)
                    poi_neighbours = poi_index.nearest(listing["lat"], listing["lng"], args.nearest_pois)
                    place_neighbours = place_index.nearest(listing["lat"], listing["lng"], 3)
                    hard_dupes, soft_dupes = duplicate_flags(listing, poi_neighbours)
                    low_value = low_value_reasons(listing["name"], listing["content"])
                    parent_path, neighbourhood, assignment_basis = proposed_assignment(
                        poi_neighbours, place_neighbours, nbhds
                    )
                    if hard_dupes and not args.include_hard_duplicates:
                        continue
                    if low_value and args.skip_low_value:
                        continue
                    yield {
                        "source_page": source_page,
                        "source_url": f"https://en.wikivoyage.org/wiki/{source_page.replace(' ', '_')}",
                        "kind": listing["kind"],
                        "name": listing["name"],
                        "lat": listing["lat"],
                        "lng": listing["lng"],
                        "content": listing["content"],
                        "url": listing["url"],
                        "wikipedia": listing["wikipedia"],
                        "wikidata": listing["wikidata"],
                        "proposed_parent_path": parent_path,
                        "proposed_neighbourhood": neighbourhood,
                        "assignment_basis": assignment_basis,
                        "nearest_pois": nearest_payload(poi_neighbours),
                        "nearest_places": [
                            {
                                "path": place.path,
                                "title": place.title,
                                "type": place.page_type,
                                "distance_km": round(dist, 3),
                            }
                            for place, dist in place_neighbours
                        ],
                        "hard_duplicate_reasons": hard_dupes,
                        "soft_duplicate_reasons": soft_dupes,
                        "low_value_reasons": low_value,
                    }
            except Exception as exc:
                print(f"warning: skipped {source_page}: {exc}", file=__import__("sys").stderr)


def write_jsonl(rows, output: Path) -> None:
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(rows, output: Path) -> None:
    fields = [
        "source_page",
        "source_url",
        "kind",
        "name",
        "lat",
        "lng",
        "proposed_parent_path",
        "proposed_neighbourhood",
        "assignment_basis",
        "hard_duplicate_reasons",
        "soft_duplicate_reasons",
        "low_value_reasons",
        "nearest_pois",
        "nearest_places",
        "url",
        "wikipedia",
        "wikidata",
        "content",
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
    parser.add_argument("--nearest-pois", type=int, default=12)
    parser.add_argument("--page-batch-size", type=int, default=50)
    parser.add_argument("--cache-dir", type=Path, default=Path("tools/raw/wikivoyage_wikitext"))
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-sleep", type=float, default=30)
    parser.add_argument("--include-hard-duplicates", action="store_true")
    parser.add_argument("--skip-low-value", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = candidate_rows(args)
    if args.format == "csv":
        write_csv(rows, output)
    else:
        write_jsonl(rows, output)


if __name__ == "__main__":
    main()
