#!/usr/bin/env python3
"""Build a travel-source coverage map from Wikivoyage listings.

This tool does not import Wikivoyage content into World66. It builds a local
SQLite database for coverage analysis:

  1. index World66 locations and POIs from content/
  2. extract destination pages and listing templates from a Wikivoyage XML dump
  3. match Wikivoyage destination pages to World66 locations
  4. report Wikivoyage listings that appear missing from World66

Wikivoyage dumps are available from Wikimedia, for example:

  https://dumps.wikimedia.org/enwikivoyage/latest/enwikivoyage-latest-pages-articles.xml.bz2

Examples:

  python tools/wikivoyage_coverage.py init
  python tools/wikivoyage_coverage.py index-world66
  python tools/wikivoyage_coverage.py import-wikivoyage ~/Downloads/enwikivoyage.xml.bz2
  python tools/wikivoyage_coverage.py match-destinations
  python tools/wikivoyage_coverage.py missing --destination Paris
  python tools/wikivoyage_coverage.py destination-report --csv > coverage.csv
"""

from __future__ import annotations

import argparse
import bz2
import csv
import html
import math
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Iterator
from urllib.request import Request, urlopen
from urllib.parse import quote

import frontmatter


REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"
DEFAULT_DB = REPO / "tools" / "wikivoyage_coverage.sqlite"
WIKIVOYAGE_BASE_URL = "https://en.wikivoyage.org/wiki/"
DEFAULT_DUMP_URL = (
    "https://dumps.wikimedia.org/enwikivoyage/latest/"
    "enwikivoyage-latest-pages-articles.xml.bz2"
)

LISTING_TEMPLATES = {
    "see",
    "do",
    "buy",
    "eat",
    "drink",
    "listing",
    "marker",
    "vicinity",
}
SKIPPED_LISTING_TYPES = {"sleep"}
ALLOWED_LISTING_TYPES = {"see", "do", "buy", "eat", "drink", "go"}
SECTION_TO_TYPE = {
    "see": "see",
    "sights": "see",
    "museums": "see",
    "do": "do",
    "buy": "buy",
    "eat": "eat",
    "drink": "drink",
    "bars": "drink",
    "cafes": "drink",
    "restaurant": "eat",
    "restaurants": "eat",
    "cafe": "drink",
    "bar": "drink",
    "pub": "drink",
    "shop": "buy",
    "shopping": "buy",
    "market": "buy",
    "museum": "see",
    "sight": "see",
    "attraction": "see",
    "activity": "do",
    "tour": "do",
    "go": "go",
    "getting there": "go",
}
WORLD66_TYPE_TO_WIKIVOYAGE = {
    "things_to_do": "see",
    "sight": "see",
    "museum": "see",
    "architecture": "see",
    "neighbourhood": "see",
    "activities": "do",
    "eating_out": "eat",
    "restaurant": "eat",
    "bars_and_cafes": "drink",
    "bar": "drink",
    "shopping": "buy",
    "market": "buy",
}


@dataclass
class Template:
    name: str
    fields: dict[str, str]
    raw: str
    start: int


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS world66_pages (
            path TEXT PRIMARY KEY,
            parent_path TEXT,
            title TEXT NOT NULL,
            normalized_title TEXT NOT NULL,
            page_type TEXT NOT NULL,
            loc_type TEXT,
            tags TEXT,
            latitude REAL,
            longitude REAL,
            snippet TEXT,
            source_file TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_world66_pages_type
            ON world66_pages(page_type, loc_type);
        CREATE INDEX IF NOT EXISTS idx_world66_pages_parent
            ON world66_pages(parent_path);
        CREATE INDEX IF NOT EXISTS idx_world66_pages_title
            ON world66_pages(normalized_title);

        CREATE TABLE IF NOT EXISTS wikivoyage_pages (
            title TEXT PRIMARY KEY,
            normalized_title TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            url TEXT NOT NULL,
            has_geo INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_wikivoyage_pages_title
            ON wikivoyage_pages(normalized_title);

        CREATE TABLE IF NOT EXISTS wikivoyage_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_title TEXT NOT NULL,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            listing_type TEXT NOT NULL,
            section TEXT,
            latitude REAL,
            longitude REAL,
            description TEXT,
            url TEXT,
            source_url TEXT NOT NULL,
            raw_template TEXT,
            UNIQUE(page_title, normalized_name, listing_type, latitude, longitude)
        );

        CREATE INDEX IF NOT EXISTS idx_wikivoyage_listings_page
            ON wikivoyage_listings(page_title);
        CREATE INDEX IF NOT EXISTS idx_wikivoyage_listings_name
            ON wikivoyage_listings(normalized_name);
        CREATE INDEX IF NOT EXISTS idx_wikivoyage_listings_type
            ON wikivoyage_listings(listing_type);

        CREATE TABLE IF NOT EXISTS destination_matches (
            world66_path TEXT PRIMARY KEY,
            wikivoyage_title TEXT NOT NULL,
            match_method TEXT NOT NULL,
            score REAL NOT NULL,
            distance_km REAL,
            FOREIGN KEY(world66_path) REFERENCES world66_pages(path)
                ON DELETE CASCADE,
            FOREIGN KEY(wikivoyage_title) REFERENCES wikivoyage_pages(title)
                ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def reset_tables(conn: sqlite3.Connection, table_names: Iterable[str]) -> None:
    for table in table_names:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def normalize_name(value: str) -> str:
    value = html.unescape(value or "")
    value = value.lower()
    value = re.sub(r"&", " and ", value)
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\b(the|a|an|le|la|les|el|los|las|de|del|du|des)\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_wikitext(value: str) -> str:
    value = value or ""
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.DOTALL)
    value = re.sub(r"<ref\b[^>]*>.*?</ref>", " ", value, flags=re.DOTALL | re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\{\{[^{}]*\}\}", " ", value)
    value = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[(https?://\S+)\s+([^\]]+)\]", r"\2", value)
    value = re.sub(r"\[(https?://\S+)\]", r"\1", value)
    value = value.replace("'''", "").replace("''", "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def first_float(*values: object) -> float | None:
    for value in values:
        parsed = parse_float(value)
        if parsed is not None:
            return parsed
    return None


def haversine_km(
    lat1: float | None,
    lon1: float | None,
    lat2: float | None,
    lon2: float | None,
) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6371.0088
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lon2) - float(lon1))
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def split_top_level(value: str, separator: str = "|") -> list[str]:
    parts: list[str] = []
    start = 0
    brace = bracket = 0
    i = 0
    while i < len(value):
        two = value[i : i + 2]
        if two == "{{":
            brace += 1
            i += 2
            continue
        if two == "}}" and brace:
            brace -= 1
            i += 2
            continue
        if two == "[[":
            bracket += 1
            i += 2
            continue
        if two == "]]" and bracket:
            bracket -= 1
            i += 2
            continue
        if value[i] == separator and brace == 0 and bracket == 0:
            parts.append(value[start:i])
            start = i + 1
        i += 1
    parts.append(value[start:])
    return parts


def iter_templates(wikitext: str) -> Iterator[tuple[int, str]]:
    i = 0
    while i < len(wikitext) - 1:
        if wikitext[i : i + 2] != "{{":
            i += 1
            continue
        start = i
        depth = 1
        i += 2
        while i < len(wikitext) - 1 and depth:
            two = wikitext[i : i + 2]
            if two == "{{":
                depth += 1
                i += 2
            elif two == "}}":
                depth -= 1
                i += 2
            else:
                i += 1
        if depth == 0:
            yield start, wikitext[start:i]
        else:
            break


def parse_template(start: int, raw: str) -> Template | None:
    inner = raw[2:-2].strip()
    if not inner:
        return None
    parts = split_top_level(inner)
    name = normalize_template_name(parts[0])
    if not name:
        return None
    fields: dict[str, str] = {}
    positional = 1
    for part in parts[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            key = normalize_template_key(key)
            if key:
                fields[key] = value.strip()
        else:
            fields[str(positional)] = part.strip()
            positional += 1
    return Template(name=name, fields=fields, raw=raw, start=start)


def normalize_template_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("_", " "))


def normalize_template_key(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().lower().replace("-", "_"))


def extract_heading_before(wikitext: str, index: int) -> str | None:
    heading = None
    for match in re.finditer(r"(?m)^\s*={2,6}\s*(.*?)\s*={2,6}\s*$", wikitext[:index]):
        heading = clean_wikitext(match.group(1)).lower()
    return heading


def wikivoyage_url(title: str) -> str:
    return WIKIVOYAGE_BASE_URL + quote(title.replace(" ", "_"), safe="/:_")


def extract_geo(template: Template) -> tuple[float | None, float | None]:
    fields = template.fields
    lat = first_float(fields.get("lat"), fields.get("latitude"), fields.get("1"))
    lon = first_float(
        fields.get("long"),
        fields.get("lon"),
        fields.get("lng"),
        fields.get("longitude"),
        fields.get("2"),
    )
    return lat, lon


def listing_from_template(template: Template, page_title: str, wikitext: str) -> dict | None:
    if template.name not in LISTING_TEMPLATES:
        return None
    fields = template.fields
    listing_type = clean_wikitext(fields.get("type", "")).lower() if template.name in {"listing", "marker"} else template.name
    section = extract_heading_before(wikitext, template.start)
    if not listing_type:
        listing_type = SECTION_TO_TYPE.get(section or "", "see")
    listing_type = SECTION_TO_TYPE.get(listing_type, listing_type)
    if listing_type in SKIPPED_LISTING_TYPES or listing_type not in ALLOWED_LISTING_TYPES:
        return None

    name = clean_wikitext(
        fields.get("name")
        or fields.get("alt")
        or fields.get("1")
        or fields.get("title")
        or ""
    )
    if not name:
        return None

    lat, lon = extract_geo(template)
    description = clean_wikitext(
        fields.get("content")
        or fields.get("description")
        or fields.get("desc")
        or fields.get("directions")
        or ""
    )
    url = clean_wikitext(fields.get("url") or fields.get("website") or "")
    return {
        "page_title": page_title,
        "name": name,
        "normalized_name": normalize_name(name),
        "listing_type": listing_type,
        "section": section,
        "latitude": lat,
        "longitude": lon,
        "description": description,
        "url": url,
        "source_url": wikivoyage_url(page_title),
        "raw_template": template.raw,
    }


def extract_page_geo(wikitext: str) -> tuple[float | None, float | None]:
    for start, raw in iter_templates(wikitext):
        template = parse_template(start, raw)
        if template and template.name == "geo":
            return extract_geo(template)
    return None, None


def extract_listings(page_title: str, wikitext: str) -> Iterator[dict]:
    for start, raw in iter_templates(wikitext):
        template = parse_template(start, raw)
        if not template:
            continue
        listing = listing_from_template(template, page_title, wikitext)
        if listing:
            yield listing


def xml_open(path: Path):
    if path.suffix == ".bz2":
        return bz2.open(path, "rb")
    return path.open("rb")


def iter_wikivoyage_pages(path: Path) -> Iterator[tuple[str, str]]:
    with xml_open(path) as handle:
        context = ET.iterparse(handle, events=("end",))
        for _, elem in context:
            tag = elem.tag.rsplit("}", 1)[-1]
            if tag != "page":
                continue
            title = elem.findtext("./{*}title") or ""
            ns = elem.findtext("./{*}ns") or ""
            redirect = elem.find("./{*}redirect")
            text = elem.findtext("./{*}revision/{*}text") or ""
            if ns == "0" and redirect is None and title and text:
                yield title, text
            elem.clear()


def path_without_suffix(md_path: Path) -> str:
    return str(md_path.relative_to(CONTENT_DIR).with_suffix(""))


def location_dir_for(md_path: Path) -> Path:
    if md_path.stem == md_path.parent.name:
        return md_path.parent
    sibling = md_path.parent / md_path.stem
    return sibling if sibling.is_dir() else md_path.parent


def parent_location_path(md_path: Path, location_dirs: dict[Path, str]) -> str | None:
    current = md_path.parent
    while current != CONTENT_DIR.parent:
        if current in location_dirs:
            return location_dirs[current]
        current = current.parent
    return None


def tags_to_text(tags: object) -> str:
    if isinstance(tags, list):
        return ",".join(str(tag) for tag in tags)
    if tags is None:
        return ""
    return str(tags)


def index_world66(conn: sqlite3.Connection) -> None:
    reset_tables(conn, ["destination_matches", "world66_pages"])
    pages: list[tuple[Path, dict, str]] = []
    location_dirs: dict[Path, str] = {}

    for md_path in CONTENT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(md_path)
        except Exception as exc:
            print(f"skip {md_path.relative_to(REPO)}: {exc}", file=sys.stderr)
            continue
        meta = post.metadata
        page_type = meta.get("type", "location")
        rel_path = path_without_suffix(md_path)
        pages.append((md_path, meta, page_type))
        if page_type == "location":
            location_dirs[location_dir_for(md_path)] = rel_path

    rows = []
    for md_path, meta, page_type in pages:
        rel_path = path_without_suffix(md_path)
        title = str(meta.get("title") or md_path.stem.replace("_", " ").title())
        parent_path = None if page_type == "location" else parent_location_path(md_path, location_dirs)
        rows.append(
            (
                rel_path,
                parent_path,
                title,
                normalize_name(title),
                page_type,
                meta.get("loc_type"),
                tags_to_text(meta.get("tags")),
                parse_float(meta.get("latitude")),
                parse_float(meta.get("longitude")),
                str(meta.get("snippet") or ""),
                str(md_path.relative_to(REPO)),
            )
        )

    conn.executemany(
        """
        INSERT INTO world66_pages (
            path, parent_path, title, normalized_title, page_type, loc_type,
            tags, latitude, longitude, snippet, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    print(f"Indexed {len(rows)} World66 pages")


def import_wikivoyage(conn: sqlite3.Connection, dump_path: Path, limit: int | None) -> None:
    reset_tables(conn, ["destination_matches", "wikivoyage_listings", "wikivoyage_pages"])
    page_rows = []
    listing_rows = []
    page_count = 0
    listing_count = 0

    for title, text in iter_wikivoyage_pages(dump_path):
        page_count += 1
        lat, lon = extract_page_geo(text)
        page_rows.append((title, normalize_name(title), lat, lon, wikivoyage_url(title), 1 if lat is not None and lon is not None else 0))
        for listing in extract_listings(title, text):
            listing_rows.append(
                (
                    listing["page_title"],
                    listing["name"],
                    listing["normalized_name"],
                    listing["listing_type"],
                    listing["section"],
                    listing["latitude"],
                    listing["longitude"],
                    listing["description"],
                    listing["url"],
                    listing["source_url"],
                    listing["raw_template"],
                )
            )
            listing_count += 1

        if len(page_rows) >= 1000:
            flush_wikivoyage(conn, page_rows, listing_rows)
            page_rows.clear()
            listing_rows.clear()
            print(f"  imported {page_count} pages, {listing_count} listings", file=sys.stderr)

        if limit and page_count >= limit:
            break

    flush_wikivoyage(conn, page_rows, listing_rows)
    print(f"Imported {page_count} Wikivoyage pages and {listing_count} listings")


def flush_wikivoyage(conn: sqlite3.Connection, page_rows: list[tuple], listing_rows: list[tuple]) -> None:
    if page_rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO wikivoyage_pages (
                title, normalized_title, latitude, longitude, url, has_geo
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            page_rows,
        )
    if listing_rows:
        conn.executemany(
            """
            INSERT OR IGNORE INTO wikivoyage_listings (
                page_title, name, normalized_name, listing_type, section,
                latitude, longitude, description, url, source_url, raw_template
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            listing_rows,
        )
    conn.commit()


def score_destination_match(world66: sqlite3.Row, wikivoyage: sqlite3.Row) -> tuple[str, float, float | None] | None:
    if world66["normalized_title"] != wikivoyage["normalized_title"]:
        return None
    distance = haversine_km(
        world66["latitude"],
        world66["longitude"],
        wikivoyage["latitude"],
        wikivoyage["longitude"],
    )
    if distance is None:
        return "title", 0.80, None
    if distance <= 25:
        return "title+geo", 1.0, distance
    if distance <= 100:
        return "title+near_geo", 0.90, distance
    return None


def match_destinations(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM destination_matches")
    world66_locs = conn.execute(
        """
        SELECT * FROM world66_pages
        WHERE page_type = 'location'
          AND loc_type IN ('city', 'feature', 'island', 'region', 'country')
        """
    ).fetchall()
    rows = []
    for loc in world66_locs:
        candidates = conn.execute(
            "SELECT * FROM wikivoyage_pages WHERE normalized_title = ?",
            (loc["normalized_title"],),
        ).fetchall()
        scored = []
        for candidate in candidates:
            score = score_destination_match(loc, candidate)
            if score:
                method, value, distance = score
                scored.append((value, distance if distance is not None else 999999, method, candidate["title"]))
        if not scored:
            scored = fuzzy_destination_candidates(conn, loc)
        if not scored:
            continue
        value, distance_sort, method, title = sorted(scored, key=lambda item: (-item[0], item[1]))[0]
        distance = None if distance_sort == 999999 else distance_sort
        rows.append((loc["path"], title, method, value, distance))

    conn.executemany(
        """
        INSERT OR REPLACE INTO destination_matches (
            world66_path, wikivoyage_title, match_method, score, distance_km
        ) VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    print(f"Matched {len(rows)} Wikivoyage destinations to World66 locations")


def fuzzy_destination_candidates(conn: sqlite3.Connection, loc: sqlite3.Row) -> list[tuple[float, float, str, str]]:
    if loc["latitude"] is None or loc["longitude"] is None:
        return []
    candidates = conn.execute(
        """
        SELECT * FROM wikivoyage_pages
        WHERE has_geo = 1
          AND latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        """,
        (
            loc["latitude"] - 0.5,
            loc["latitude"] + 0.5,
            loc["longitude"] - 0.5,
            loc["longitude"] + 0.5,
        ),
    ).fetchall()
    scored = []
    for candidate in candidates:
        ratio = SequenceMatcher(None, loc["normalized_title"], candidate["normalized_title"]).ratio()
        if ratio < 0.90:
            continue
        distance = haversine_km(loc["latitude"], loc["longitude"], candidate["latitude"], candidate["longitude"])
        if distance is None or distance > 50:
            continue
        scored.append((0.70 + (ratio * 0.15), distance, "fuzzy_title+geo", candidate["title"]))
    return scored


def world66_pois_for(conn: sqlite3.Connection, world66_path: str) -> list[sqlite3.Row]:
    prefix = world66_path + "/%"
    return conn.execute(
        """
        SELECT * FROM world66_pages
        WHERE (parent_path = ? OR path LIKE ?)
          AND page_type IN ('poi', 'neighbourhood')
        """,
        (world66_path, prefix),
    ).fetchall()


def wikivoyage_listings_for(conn: sqlite3.Connection, title: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM wikivoyage_listings
        WHERE page_title = ?
          AND listing_type NOT IN ('sleep')
        ORDER BY listing_type, name
        """,
        (title,),
    ).fetchall()


def world66_wikivoyage_type(page: sqlite3.Row) -> str | None:
    tags = {tag.strip() for tag in (page["tags"] or "").split(",") if tag.strip()}
    for tag in tags:
        if tag in WORLD66_TYPE_TO_WIKIVOYAGE:
            return WORLD66_TYPE_TO_WIKIVOYAGE[tag]
    return None


def poi_matches_listing(poi: sqlite3.Row, listing: sqlite3.Row, radius_m: float) -> tuple[bool, str, float]:
    if poi["normalized_title"] and poi["normalized_title"] == listing["normalized_name"]:
        return True, "name", 1.0
    distance = haversine_km(poi["latitude"], poi["longitude"], listing["latitude"], listing["longitude"])
    if distance is not None and distance * 1000 <= radius_m:
        return True, "geo", 1.0 - min(distance / (radius_m / 1000), 1.0) * 0.25
    ratio = SequenceMatcher(None, poi["normalized_title"], listing["normalized_name"]).ratio()
    if ratio >= 0.88:
        return True, "fuzzy_name", ratio
    poi_type = world66_wikivoyage_type(poi)
    if poi_type and poi_type == listing["listing_type"] and ratio >= 0.78:
        return True, "type+fuzzy_name", ratio
    return False, "", 0.0


def missing_listings(
    conn: sqlite3.Connection,
    match: sqlite3.Row,
    radius_m: float,
) -> tuple[list[sqlite3.Row], int]:
    pois = world66_pois_for(conn, match["world66_path"])
    listings = wikivoyage_listings_for(conn, match["wikivoyage_title"])
    return missing_listings_from_rows(pois, listings, radius_m)


def missing_listings_from_rows(
    pois: list[sqlite3.Row],
    listings: list[sqlite3.Row],
    radius_m: float,
) -> tuple[list[sqlite3.Row], int]:
    matched_listing_ids = set()
    poi_names = {poi["normalized_title"] for poi in pois if poi["normalized_title"]}
    poi_coords = [
        poi for poi in pois
        if poi["latitude"] is not None and poi["longitude"] is not None
    ]
    for listing in listings:
        if listing["normalized_name"] in poi_names:
            matched_listing_ids.add(listing["id"])
            continue
        if listing["latitude"] is not None and listing["longitude"] is not None:
            for poi in poi_coords:
                distance = haversine_km(
                    poi["latitude"],
                    poi["longitude"],
                    listing["latitude"],
                    listing["longitude"],
                )
                if distance is not None and distance * 1000 <= radius_m:
                    matched_listing_ids.add(listing["id"])
                    break
            if listing["id"] in matched_listing_ids:
                continue
        for poi in pois:
            ok, _, _ = poi_matches_listing(poi, listing, radius_m)
            if ok:
                matched_listing_ids.add(listing["id"])
                break
    missing = [listing for listing in listings if listing["id"] not in matched_listing_ids]
    return missing, len(matched_listing_ids)


def grouped_report_rows(
    conn: sqlite3.Connection,
    matches: list[sqlite3.Row],
    radius_m: float,
) -> Iterator[dict]:
    world66_paths = {match["world66_path"] for match in matches}
    wikivoyage_titles = {match["wikivoyage_title"] for match in matches}
    pois_by_parent: dict[str, list[sqlite3.Row]] = {path: [] for path in world66_paths}
    listings_by_page: dict[str, list[sqlite3.Row]] = {title: [] for title in wikivoyage_titles}

    for poi in conn.execute(
        """
        SELECT * FROM world66_pages
        WHERE page_type IN ('poi', 'neighbourhood')
          AND parent_path IS NOT NULL
        """
    ):
        parent = poi["parent_path"]
        if parent in pois_by_parent:
            pois_by_parent[parent].append(poi)

    for listing in conn.execute("SELECT * FROM wikivoyage_listings"):
        page_title = listing["page_title"]
        if page_title in listings_by_page:
            listings_by_page[page_title].append(listing)

    for match in matches:
        pois = pois_by_parent.get(match["world66_path"], [])
        listings = listings_by_page.get(match["wikivoyage_title"], [])
        missing, matched_count = missing_listings_from_rows(pois, listings, radius_m)
        wv_count = len(listings)
        yield {
            "world66_path": match["world66_path"],
            "world66_title": match["world66_title"],
            "loc_type": match["loc_type"],
            "wikivoyage_title": match["wikivoyage_title"],
            "world66_pois": len(pois),
            "wikivoyage_listings": wv_count,
            "matched_listings": matched_count,
            "missing_listings": len(missing),
            "coverage": round(matched_count / wv_count, 3) if wv_count else 0,
            "match_method": match["match_method"],
            "distance_km": match["distance_km"],
        }


def find_destination_match(conn: sqlite3.Connection, destination: str) -> sqlite3.Row | None:
    norm = normalize_name(destination)
    return conn.execute(
        """
        SELECT dm.*, w.title, w.loc_type, w.latitude, w.longitude
        FROM destination_matches dm
        JOIN world66_pages w ON w.path = dm.world66_path
        WHERE w.normalized_title = ? OR w.path = ? OR dm.wikivoyage_title = ?
        ORDER BY dm.score DESC
        LIMIT 1
        """,
        (norm, destination, destination),
    ).fetchone()


def print_missing(
    conn: sqlite3.Connection,
    destination: str,
    limit: int,
    radius_m: float,
    csv_output: bool,
) -> None:
    match = find_destination_match(conn, destination)
    if not match:
        raise SystemExit(f"No matched Wikivoyage destination found for {destination!r}. Run match-destinations first.")
    missing, matched_count = missing_listings(conn, match, radius_m)
    world66_count = len(world66_pois_for(conn, match["world66_path"]))
    wikivoyage_count = len(wikivoyage_listings_for(conn, match["wikivoyage_title"]))

    if csv_output:
        writer = csv.writer(sys.stdout)
        writer.writerow(["world66_path", "wikivoyage_title", "type", "name", "latitude", "longitude", "url", "description"])
        for listing in missing[:limit]:
            writer.writerow(
                [
                    match["world66_path"],
                    match["wikivoyage_title"],
                    listing["listing_type"],
                    listing["name"],
                    listing["latitude"],
                    listing["longitude"],
                    listing["source_url"],
                    listing["description"],
                ]
            )
        return

    print(f"World66:     {match['world66_path']} ({world66_count} POIs)")
    print(f"Wikivoyage:  {match['wikivoyage_title']} ({wikivoyage_count} listings)")
    print(f"Matched:     {matched_count}")
    print(f"Missing:     {len(missing)}")
    print()
    for listing in missing[:limit]:
        coords = ""
        if listing["latitude"] is not None and listing["longitude"] is not None:
            coords = f" ({listing['latitude']:.5f}, {listing['longitude']:.5f})"
        print(f"- [{listing['listing_type']}] {listing['name']}{coords}")
        if listing["description"]:
            print(f"  {listing['description'][:220]}")
        print(f"  {listing['source_url']}")


def destination_report(
    conn: sqlite3.Connection,
    min_wikivoyage: int,
    radius_m: float,
    csv_output: bool,
    loc_types: set[str],
) -> None:
    placeholders = ",".join("?" for _ in loc_types)
    matches = conn.execute(
        f"""
        SELECT dm.*, w.title AS world66_title, w.loc_type
        FROM destination_matches dm
        JOIN world66_pages w ON w.path = dm.world66_path
        WHERE w.loc_type IN ({placeholders})
        ORDER BY w.path
        """,
        tuple(sorted(loc_types)),
    ).fetchall()
    rows = [
        row for row in grouped_report_rows(conn, matches, radius_m)
        if row["wikivoyage_listings"] >= min_wikivoyage
    ]
    rows.sort(key=lambda row: (row["coverage"], -row["wikivoyage_listings"], row["world66_path"]))

    if csv_output:
        fieldnames = [
            "world66_path",
            "world66_title",
            "loc_type",
            "wikivoyage_title",
            "world66_pois",
            "wikivoyage_listings",
            "matched_listings",
            "missing_listings",
            "coverage",
            "match_method",
            "distance_km",
        ]
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return

    for row in rows[:100]:
        print(
            f"{row['coverage']:.0%}  WV {row['wikivoyage_listings']:>3}  "
            f"W66 {row['world66_pois']:>3}  missing {row['missing_listings']:>3}  "
            f"{row['world66_path']} -> {row['wikivoyage_title']}"
        )


def stats(conn: sqlite3.Connection) -> None:
    queries = [
        ("World66 locations", "SELECT COUNT(*) FROM world66_pages WHERE page_type = 'location'"),
        ("World66 POIs", "SELECT COUNT(*) FROM world66_pages WHERE page_type IN ('poi', 'neighbourhood')"),
        ("Wikivoyage pages", "SELECT COUNT(*) FROM wikivoyage_pages"),
        ("Wikivoyage listings", "SELECT COUNT(*) FROM wikivoyage_listings"),
        ("Destination matches", "SELECT COUNT(*) FROM destination_matches"),
    ]
    for label, query in queries:
        value = conn.execute(query).fetchone()[0]
        print(f"{label:24s} {value}")


def download_dump(output: Path, url: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "World66Coverage/1.0"})
    with urlopen(req, timeout=60) as response, output.open("wb") as handle:
        total = response.headers.get("Content-Length")
        total_bytes = int(total) if total and total.isdigit() else None
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if total_bytes:
                pct = downloaded / total_bytes * 100
                print(f"\rDownloaded {downloaded / 1024 / 1024:.1f} MB ({pct:.1f}%)", end="", file=sys.stderr)
            else:
                print(f"\rDownloaded {downloaded / 1024 / 1024:.1f} MB", end="", file=sys.stderr)
    print(file=sys.stderr)
    print(f"Wrote {output}")


def add_common_db_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"SQLite database path (default: {DEFAULT_DB})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create the SQLite schema")
    add_common_db_arg(p_init)

    p_world66 = sub.add_parser("index-world66", help="Index World66 content pages")
    add_common_db_arg(p_world66)

    p_import = sub.add_parser("import-wikivoyage", help="Import Wikivoyage pages/listings from XML or XML.BZ2")
    add_common_db_arg(p_import)
    p_import.add_argument("dump", type=Path, help="Wikivoyage pages-articles XML dump")
    p_import.add_argument("--limit", type=int, help="Import only the first N pages for testing")

    p_download = sub.add_parser("download-dump", help="Download the latest English Wikivoyage XML dump")
    p_download.add_argument(
        "--output",
        type=Path,
        default=REPO / "tools" / "enwikivoyage-latest-pages-articles.xml.bz2",
    )
    p_download.add_argument("--url", default=DEFAULT_DUMP_URL)

    p_match = sub.add_parser("match-destinations", help="Match Wikivoyage pages to World66 locations")
    add_common_db_arg(p_match)

    p_missing = sub.add_parser("missing", help="Show Wikivoyage listings missing from one destination")
    add_common_db_arg(p_missing)
    p_missing.add_argument("--destination", required=True, help="World66 path/title or Wikivoyage page title")
    p_missing.add_argument("--limit", type=int, default=50)
    p_missing.add_argument("--radius-m", type=float, default=150)
    p_missing.add_argument("--csv", action="store_true")

    p_report = sub.add_parser("destination-report", help="Summarize coverage for all matched destinations")
    add_common_db_arg(p_report)
    p_report.add_argument("--min-wikivoyage", type=int, default=5)
    p_report.add_argument("--radius-m", type=float, default=150)
    p_report.add_argument(
        "--loc-types",
        default="city,feature,island",
        help="Comma-separated World66 loc_type values to include (default: city,feature,island)",
    )
    p_report.add_argument("--csv", action="store_true")

    p_stats = sub.add_parser("stats", help="Print database counts")
    add_common_db_arg(p_stats)

    args = parser.parse_args()

    if args.command == "download-dump":
        download_dump(args.output, args.url)
        return

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(args.db)
    init_db(conn)

    if args.command == "init":
        print(f"Initialized {args.db}")
    elif args.command == "index-world66":
        index_world66(conn)
    elif args.command == "import-wikivoyage":
        import_wikivoyage(conn, args.dump, args.limit)
    elif args.command == "match-destinations":
        match_destinations(conn)
    elif args.command == "missing":
        print_missing(conn, args.destination, args.limit, args.radius_m, args.csv)
    elif args.command == "destination-report":
        loc_types = {value.strip() for value in args.loc_types.split(",") if value.strip()}
        destination_report(conn, args.min_wikivoyage, args.radius_m, args.csv, loc_types)
    elif args.command == "stats":
        stats(conn)


if __name__ == "__main__":
    main()
