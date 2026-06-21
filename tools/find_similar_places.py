#!/usr/bin/env python3
"""
Find POIs similar to a given POI, ranked by embedding distance.

Usage:
  tools/find_similar_places.py <path-or-substring> [--k N]

The argument can be a content-relative path (e.g. europe/italy/lazio/rome/thecolosseum.md),
a URL path (e.g. europe/italy/lazio/rome/thecolosseum), or a case-insensitive
substring of the title (e.g. "colosseum"). The first matching POI is used.
"""

import argparse
import sys
from pathlib import Path

import apsw
import sqlite_vec

DB_PATH = Path(__file__).resolve().parent.parent / "search.db"


def open_db():
    if not DB_PATH.is_file():
        sys.exit(f"search.db not found at {DB_PATH}; run indexer.py first")
    conn = apsw.Connection(str(DB_PATH), flags=apsw.SQLITE_OPEN_READONLY)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    return conn


def resolve_page(conn, query):
    """Resolve query to a single page row. Returns (path, title, location, page_type) or None."""
    norm = query
    if norm.startswith("content/"):
        norm = norm[len("content/"):]
    if norm.endswith(".md"):
        norm = norm[:-3]
    md_path = norm + ".md"
    row = conn.execute(
        "SELECT path, title, location, page_type FROM docs WHERE path=? LIMIT 1",
        (md_path,),
    ).fetchone()
    if row:
        return row
    row = conn.execute(
        "SELECT path, title, location, page_type FROM docs WHERE url_path=? LIMIT 1",
        (norm,),
    ).fetchone()
    if row:
        return row
    return conn.execute(
        "SELECT path, title, location, page_type FROM docs WHERE lower(title) LIKE ? LIMIT 1",
        (f"%{query.lower()}%",),
    ).fetchone()


def find_similar(conn, path, k=10, prefix=None, page_type=None):
    """Return list of (distance, path, title, location) for the k nearest pages, excluding self.

    Done as two separate queries because joining the vec0 virtual table with the FTS5
    docs virtual table produces a pathological query plan that scans every doc per
    candidate.

    When prefix is set, only pages whose path starts with it are considered.
    When page_type is set, only pages of that type are considered.
    Filtering happens after the vector search because vec0 doesn't expose those columns.
    """
    emb = conn.execute("SELECT embedding FROM embeddings WHERE path=?", (path,)).fetchone()
    if not emb:
        return []

    if prefix and prefix.startswith("content/"):
        prefix = prefix[len("content/"):]

    needs_filter = bool(prefix) or bool(page_type)
    if needs_filter:
        total = conn.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        knn_k = min(total, 4096)  # sqlite-vec hard cap
    else:
        knn_k = k + 1

    rows = conn.execute(
        "SELECT path, distance FROM embeddings WHERE embedding MATCH ? AND k = ? ORDER BY distance",
        (emb[0], knn_k),
    ).fetchall()

    type_by_path = {}
    if page_type:
        candidate_paths = [p for p, _ in rows if p != path]
        if candidate_paths:
            placeholders = ",".join("?" * len(candidate_paths))
            type_by_path = {
                r[0]: r[1]
                for r in conn.execute(
                    f"SELECT path, page_type FROM docs WHERE path IN ({placeholders})",
                    candidate_paths,
                )
            }

    neighbours = []
    for p, d in rows:
        if p == path:
            continue
        if prefix and not p.startswith(prefix):
            continue
        if page_type and type_by_path.get(p) != page_type:
            continue
        neighbours.append((p, d))
        if len(neighbours) >= k:
            break

    if not neighbours:
        return []
    paths = [p for p, _ in neighbours]
    placeholders = ",".join("?" * len(paths))
    meta = {
        row[0]: (row[1], row[2])
        for row in conn.execute(
            f"SELECT path, title, location FROM docs WHERE path IN ({placeholders})", paths,
        )
    }
    return [(distance, p, *meta.get(p, ("?", ""))) for p, distance in neighbours]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Page path, URL path, or title substring")
    parser.add_argument("-n", type=int, default=10, help="Number of neighbours to return")
    parser.add_argument("--prefix", help="Restrict results to pages whose path starts with this prefix "
                                          "(e.g. northamerica/unitedstates/florida/miami)")
    parser.add_argument("--type", dest="page_type",
                        help="Restrict results to this page type. Defaults to the seed's type. "
                             "Pass 'any' to disable type filtering.")
    args = parser.parse_args()

    conn = open_db()
    seed = resolve_page(conn, args.query)
    if not seed:
        sys.exit(f"no page matches {args.query!r}")
    path, title, location, seed_type = seed
    print(f"{title} ({location or 'unknown'}) [{seed_type}] [{path}]")
    print()

    if args.page_type is None:
        page_type = seed_type
    elif args.page_type.lower() == "any":
        page_type = None
    else:
        page_type = args.page_type
    results = find_similar(conn, path, k=args.n, prefix=args.prefix, page_type=page_type)
    if not results:
        sys.exit("no embedding stored for this POI")
    for distance, p, t, loc in results:
        print(f"  {distance:.3f}  {t}  ({loc or '—'})  [{p}]")


if __name__ == "__main__":
    main()
