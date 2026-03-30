import sqlite3
import os
import hashlib
from pathlib import Path

CONTENT_DIR = Path("content")
DB_PATH = Path("search.db")

def init_db(conn):
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path UNINDEXED, title, body);
        CREATE TABLE IF NOT EXISTS meta (path TEXT PRIMARY KEY, mtime REAL, hash TEXT);
    """)

def file_hash(path):
    return hashlib.md5(path.read_bytes()).hexdigest()

def extract(path):
    lines = path.read_text(errors="ignore").splitlines()
    title = lines[0].lstrip("# ").strip() if lines else path.stem
    body = "\n".join(lines[1:])
    return title, body

def index_file(conn, path):
    rel = str(path.relative_to(CONTENT_DIR))
    mtime = path.stat().st_mtime
    h = file_hash(path)

    row = conn.execute("SELECT mtime, hash FROM meta WHERE path=?", (rel,)).fetchone()
    if row and row[0] == mtime and row[1] == h:
        return

    title, body = extract(path)
    conn.execute("DELETE FROM docs WHERE path=?", (rel,))
    conn.execute("INSERT INTO docs(path, title, body) VALUES(?,?,?)", (rel, title, body))
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
