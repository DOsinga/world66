import sqlite3
import re
import hashlib
from pathlib import Path

import yaml

CONTENT_DIR = Path("content")
DB_PATH = Path("search.db")

def init_db(conn):
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(
            path UNINDEXED, title, body,
            page_type UNINDEXED, url_path UNINDEXED, location UNINDEXED
        );
        CREATE TABLE IF NOT EXISTS meta (path TEXT PRIMARY KEY, mtime REAL, hash TEXT);
    """)

def file_hash(path):
    return hashlib.md5(path.read_bytes()).hexdigest()

def _parse_frontmatter(text):
    if text.startswith("---"):
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if match:
            try:
                meta = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                meta = {}
            return meta, match.group(2)
    return {}, text

def _url_path(rel_path):
    """Derive URL path from a content-relative file path."""
    parts = list(rel_path.parts)
    stem = parts[-1][:-3]  # strip .md
    if len(parts) >= 2 and stem == parts[-2]:
        return "/".join(parts[:-1])
    return "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem

_SECTION_SLUGS = {
    "accommodation", "accommodations", "accommodationandfood", "accommocation",
    "activities", "bars_and_cafes", "beaches", "books", "day_trips",
    "eating_out", "festivals", "food", "getting_around", "getting_there",
    "highlights", "history", "landmarks", "museums", "nightlife",
    "nightlife_and_ente", "people", "placestostay", "practical_informat",
    "shopping", "sights", "things_to_do", "toursevents", "top_5_must_dos",
}

def _find_parent_location(path):
    """Walk up from path to find the nearest ancestor location title."""
    current = path.parent
    while current != CONTENT_DIR and current != CONTENT_DIR.parent:
        candidate = current / f"{current.name}.md"
        if candidate.is_file() and candidate != path:
            text = candidate.read_text(encoding="utf-8", errors="replace")
            meta, _ = _parse_frontmatter(text)
            if meta.get("type", "location") == "location":
                return meta.get("title", current.name)
            # It's a section dir — skip and keep walking up
        elif not candidate.is_file():
            # No dir/dir.md — check sibling .md or infer from name
            # Match section slugs including numbered variants like eating_out_1
            base = current.name.rstrip("0123456789").rstrip("_")
            if base in _SECTION_SLUGS:
                current = current.parent
                continue
            sibling = current.parent / f"{current.name}.md"
            if sibling.is_file():
                text = sibling.read_text(encoding="utf-8", errors="replace")
                meta, _ = _parse_frontmatter(text)
                if meta.get("type", "location") == "location":
                    return meta.get("title", current.name)
                # section — skip
            elif any(current.glob("*.md")):
                return current.name.replace("_", " ").title()
        current = current.parent
    return ""

def extract(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(text)
    title = meta.get("title", path.stem)
    page_type = meta.get("type", "location")
    return title, body, page_type

def index_file(conn, path):
    rel = str(path.relative_to(CONTENT_DIR))
    mtime = path.stat().st_mtime
    h = file_hash(path)

    row = conn.execute("SELECT mtime, hash FROM meta WHERE path=?", (rel,)).fetchone()
    if row and row[0] == mtime and row[1] == h:
        return

    title, body, page_type = extract(path)
    url_path = _url_path(path.relative_to(CONTENT_DIR))
    location = _find_parent_location(path)
    conn.execute("DELETE FROM docs WHERE path=?", (rel,))
    conn.execute("INSERT INTO docs(path, title, body, page_type, url_path, location) VALUES(?,?,?,?,?,?)",
                 (rel, title, body, page_type, url_path, location))
    conn.execute("INSERT OR REPLACE INTO meta(path, mtime, hash) VALUES(?,?,?)", (rel, mtime, h))

def remove_deleted(conn):
    indexed = {row[0] for row in conn.execute("SELECT path FROM meta")}
    current = {str(p.relative_to(CONTENT_DIR)) for p in CONTENT_DIR.rglob("*.md")}
    for path in indexed - current:
        conn.execute("DELETE FROM docs WHERE path=?", (path,))
        conn.execute("DELETE FROM meta WHERE path=?", (path,))

def run():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    for path in CONTENT_DIR.rglob("*.md"):
        index_file(conn, path)
    remove_deleted(conn)
    conn.commit()
    conn.close()
    print(f"Indexed {sum(1 for _ in CONTENT_DIR.rglob('*.md'))} files")

if __name__ == "__main__":
    run()
