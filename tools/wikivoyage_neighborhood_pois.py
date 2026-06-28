#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import difflib
import html
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import frontmatter


CONTENT_DIR = Path("content")
API_URL = "https://en.wikivoyage.org/w/api.php"
USER_AGENT = "World66 neighbourhood POI tooling (https://world66.ai/)"

CITY_PAGES = {
    "content/europe/germany/berlin": [
        "Berlin/Mitte",
        "Berlin/City West",
        "Berlin/East Central",
    ],
    "content/europe/france/paris": [
        "Paris/1st arrondissement",
        "Paris/2nd arrondissement",
        "Paris/3rd arrondissement",
        "Paris/4th arrondissement",
        "Paris/5th arrondissement",
        "Paris/6th arrondissement",
        "Paris/9th arrondissement",
        "Paris/10th arrondissement",
        "Paris/11th arrondissement",
        "Paris/18th arrondissement",
    ],
    "content/europe/unitedkingdom/england/london": [
        "London/Westminster",
        "London/Soho",
        "London/South Bank",
        "London/Camden",
        "London/Islington",
        "London/East End",
        "London/South",
    ],
}


@dataclass
class Neighbourhood:
    parent_path: str
    slug: str
    title: str
    lat: float
    lng: float
    anchors: list[tuple[float, float]]


@dataclass
class Listing:
    source_page: str
    kind: str
    name: str
    lat: float
    lng: float
    content: str
    url: str
    wikipedia: str
    wikidata: str
    neighbourhood: Neighbourhood
    distance_km: float
    duplicate: str


def fetch_wikitext(title: str) -> str:
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "redirects": "1",
    }
    req = Request(f"{API_URL}?{urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as response:
        data = response.read().decode("utf-8")
    import json

    parsed = json.loads(data)
    return parsed["parse"]["wikitext"]["*"]


def api_query(params: dict[str, str]) -> dict:
    req = Request(f"{API_URL}?{urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as response:
        data = response.read().decode("utf-8")
    import json

    return json.loads(data)


def wikivoyage_subpages(limit: int | None = None):
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": "0",
        "aplimit": "max",
        "format": "json",
    }
    seen = 0
    while True:
        data = api_query(params)
        for page in data.get("query", {}).get("allpages", []):
            title = page["title"]
            if "/" not in title:
                continue
            yield title
            seen += 1
            if limit and seen >= limit:
                return
        if "continue" not in data:
            return
        params.update(data["continue"])


def iter_templates(text: str):
    i = 0
    while True:
        match = re.search(r"\{\{(see|do)\b", text[i:], re.I)
        if not match:
            return
        start = i + match.start()
        pos = start
        depth = 0
        while pos < len(text) - 1:
            pair = text[pos : pos + 2]
            if pair == "{{":
                depth += 1
                pos += 2
                continue
            if pair == "}}":
                depth -= 1
                pos += 2
                if depth == 0:
                    yield text[start:pos]
                    i = pos
                    break
                continue
            pos += 1
        else:
            return


def split_template(template: str) -> dict[str, str]:
    inner = template[2:-2]
    parts = []
    current = []
    depth = 0
    i = 0
    while i < len(inner):
        pair = inner[i : i + 2]
        if pair == "{{":
            depth += 1
            current.append(pair)
            i += 2
            continue
        if pair == "}}":
            depth -= 1
            current.append(pair)
            i += 2
            continue
        if inner[i] == "|" and depth == 0:
            parts.append("".join(current))
            current = []
            i += 1
            continue
        current.append(inner[i])
        i += 1
    parts.append("".join(current))

    data = {"kind": parts[0].strip().lower()}
    for part in parts[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            data[key.strip().lower()] = value.strip()
    return data


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", value)
    value = re.sub(r"'{2,5}", "", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def distance_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371.0
    lat1 = math.radians(a_lat)
    lat2 = math.radians(b_lat)
    dlat = math.radians(b_lat - a_lat)
    dlng = math.radians(b_lng - a_lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def neighbourhoods(city_dir: Path) -> list[Neighbourhood]:
    rows = []
    tagged: dict[str, list[tuple[float, float]]] = {}
    for path in sorted(city_dir.glob("*.md")):
        post = frontmatter.load(path)
        if post.metadata.get("type") != "poi":
            continue
        tags = post.metadata.get("tags") or []
        if "latitude" not in post.metadata or "longitude" not in post.metadata:
            continue
        point = (float(post.metadata["latitude"]), float(post.metadata["longitude"]))
        for tag in tags:
            tagged.setdefault(tag, []).append(point)

    for path in sorted(city_dir.glob("*.md")):
        post = frontmatter.load(path)
        if post.metadata.get("type") != "neighbourhood":
            continue
        if "latitude" not in post.metadata or "longitude" not in post.metadata:
            continue
        rows.append(
            Neighbourhood(
                parent_path=str(city_dir),
                slug=path.stem,
                title=post.metadata.get("title", path.stem),
                lat=float(post.metadata["latitude"]),
                lng=float(post.metadata["longitude"]),
                anchors=[(float(post.metadata["latitude"]), float(post.metadata["longitude"]))]
                + tagged.get(path.stem, []),
            )
        )
    return rows


def existing_names(city_dir: Path) -> dict[str, str]:
    names = {}
    for path in city_dir.glob("*.md"):
        post = frontmatter.load(path)
        title = post.metadata.get("title", path.stem)
        names[norm(title)] = str(path)
        names[norm(path.stem)] = str(path)
    return names


def neighbourhood_index() -> list[Neighbourhood]:
    rows = []
    parents = {path.parent for path in CONTENT_DIR.rglob("*.md")}
    for parent in sorted(parents):
        rows.extend(neighbourhoods(parent))
    return rows


def find_duplicate(name: str, names: dict[str, str]) -> str:
    key = norm(name)
    if key in names:
        return names[key]
    for existing, path in names.items():
        if len(existing) < 8 or len(key) < 8:
            continue
        if existing in key or key in existing:
            return path
        if difflib.SequenceMatcher(None, key, existing).ratio() >= 0.86:
            return path
    return ""


def nearest_neighbourhood(rows: list[Neighbourhood], lat: float, lng: float) -> tuple[Neighbourhood, float]:
    distances = [
        (min(distance_km(lat, lng, anchor_lat, anchor_lng) for anchor_lat, anchor_lng in row.anchors), row)
        for row in rows
    ]
    distance, row = min(distances, key=lambda item: item[0])
    return row, distance


def collect(city_path: str, max_distance: float) -> list[Listing]:
    city_dir = Path(city_path)
    names = existing_names(city_dir)
    hoods = neighbourhoods(city_dir)
    listings = {}

    for source_page in CITY_PAGES[city_path]:
        text = fetch_wikitext(source_page)
        for template in iter_templates(text):
            data = split_template(template)
            name = clean_text(data.get("name", ""))
            content = clean_text(data.get("content", ""))
            lat = data.get("lat") or data.get("latitude")
            lng = data.get("long") or data.get("lon") or data.get("longitude")
            if not name or not lat or not lng or len(content) < 40:
                continue
            if re.search(r"embassy|consulate|hotel|hostel|apartment|airport|station", name, re.I):
                continue
            try:
                lat_f = float(lat)
                lng_f = float(lng)
            except ValueError:
                continue
            hood, dist = nearest_neighbourhood(hoods, lat_f, lng_f)
            if dist > max_distance:
                continue
            key = norm(name)
            duplicate = find_duplicate(name, names)
            if key in listings:
                continue
            listings[key] = Listing(
                source_page=source_page,
                kind=data["kind"],
                name=name,
                lat=lat_f,
                lng=lng_f,
                content=content,
                url=data.get("url", ""),
                wikipedia=data.get("wikipedia", ""),
                wikidata=data.get("wikidata", ""),
                neighbourhood=hood,
                distance_km=dist,
                duplicate=duplicate,
            )
    return sorted(listings.values(), key=lambda row: (row.neighbourhood.slug, row.distance_km, row.name))


def listings_from_page(source_page: str):
    text = fetch_wikitext(source_page)
    for template in iter_templates(text):
        data = split_template(template)
        name = clean_text(data.get("name", ""))
        content = clean_text(data.get("content", ""))
        lat = data.get("lat") or data.get("latitude")
        lng = data.get("long") or data.get("lon") or data.get("longitude")
        if not name or not lat or not lng or len(content) < 40:
            continue
        if re.search(r"embassy|consulate|hotel|hostel|apartment|airport|station", name, re.I):
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


def scan_wikivoyage_subpages(max_distance: float, limit_pages: int | None = None):
    hoods = neighbourhood_index()
    names_by_parent: dict[str, dict[str, str]] = {}
    seen = set()
    for source_page in wikivoyage_subpages(limit_pages):
        try:
            rows = listings_from_page(source_page)
            for row in rows:
                key = (norm(row["name"]), round(row["lat"], 5), round(row["lng"], 5))
                if key in seen:
                    continue
                seen.add(key)
                hood, dist = nearest_neighbourhood(hoods, row["lat"], row["lng"])
                if dist > max_distance:
                    continue
                if hood.parent_path not in names_by_parent:
                    names_by_parent[hood.parent_path] = existing_names(Path(hood.parent_path))
                duplicate = find_duplicate(row["name"], names_by_parent[hood.parent_path])
                yield Listing(
                    source_page=row["source_page"],
                    kind=row["kind"],
                    name=row["name"],
                    lat=row["lat"],
                    lng=row["lng"],
                    content=row["content"],
                    url=row["url"],
                    wikipedia=row["wikipedia"],
                    wikidata=row["wikidata"],
                    neighbourhood=hood,
                    distance_km=dist,
                    duplicate=duplicate,
                )
        except Exception as exc:
            print(f"warning: skipped {source_page}: {exc}", file=__import__("sys").stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("city_path", nargs="?", choices=sorted(CITY_PAGES))
    parser.add_argument("--scan-wikivoyage-subpages", action="store_true")
    parser.add_argument("--limit-pages", type=int)
    parser.add_argument("--max-distance-km", type=float, default=2.5)
    parser.add_argument("--include-duplicates", action="store_true")
    args = parser.parse_args()

    if args.scan_wikivoyage_subpages:
        rows = scan_wikivoyage_subpages(args.max_distance_km, args.limit_pages)
    else:
        if not args.city_path:
            parser.error("city_path is required unless --scan-wikivoyage-subpages is used")
        rows = collect(args.city_path, args.max_distance_km)
    writer = csv.writer(__import__("sys").stdout)
    writer.writerow(
        [
            "parent_path",
            "neighbourhood",
            "distance_km",
            "name",
            "kind",
            "lat",
            "lng",
            "duplicate",
            "wikipedia",
            "wikidata",
            "url",
            "source_page",
            "content",
        ]
    )
    for row in rows:
        if row.duplicate and not args.include_duplicates:
            continue
        writer.writerow(
            [
                row.neighbourhood.parent_path,
                row.neighbourhood.slug,
                f"{row.distance_km:.2f}",
                row.name,
                row.kind,
                row.lat,
                row.lng,
                row.duplicate,
                row.wikipedia,
                row.wikidata,
                row.url,
                row.source_page,
                row.content,
            ]
        )


if __name__ == "__main__":
    main()
