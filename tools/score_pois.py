#!/usr/bin/env python3
"""
Score POIs by how well their embedding matches an ideal description for their tag type.

Reads embeddings from search.db (built by indexer.py) and writes a `score` field
back into each POI's frontmatter. Scores are cosine similarities in [0, 1].

Usage:
  # Score all POIs
  tools/score_pois.py

  # Score only POIs under a specific destination (for testing)
  tools/score_pois.py --path europe/france/paris

  # Dry-run: print scores without writing
  tools/score_pois.py --path europe/france/paris --dry-run
"""

import argparse
import sys
from pathlib import Path

import apsw
import frontmatter
import numpy as np
import sqlite_vec

DB_PATH = Path(__file__).resolve().parent.parent / "search.db"
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

# Scoring tags and their ideal descriptions.
# A POI's score is its cosine similarity to the ideal for its primary scoring tag.
TAG_IDEALS = {
    "museum": (
        "world-renowned museum with outstanding permanent collections, "
        "major exhibitions, and deep cultural or scientific significance"
    ),
    "sight": (
        "iconic landmark or attraction of great historical, architectural, "
        "or natural significance, visited by travellers from around the world"
    ),
    "architecture": (
        "extraordinary building or structure celebrated for its architectural "
        "design, engineering, or historical importance"
    ),
    "restaurant": (
        "exceptional restaurant with distinctive local cuisine, outstanding "
        "quality, and a strong reputation among food lovers"
    ),
    "bar": (
        "legendary bar, pub, or cocktail lounge with a unique atmosphere, "
        "excellent drinks, and strong local or international following"
    ),
    "market": (
        "vibrant food or flea market that is a genuine local institution, "
        "known for fresh produce, street food, or unique goods"
    ),
    "neighbourhood": (
        "fascinating urban neighbourhood with a distinct character, rich history, "
        "lively street life, and things to see and do"
    ),
    "park": (
        "beautiful park, garden, or green space that is a major attraction "
        "in its own right, loved by locals and visitors alike"
    ),
    "church": (
        "magnificent church, cathedral, mosque, or religious building of great "
        "architectural beauty or spiritual and historical significance"
    ),
    "historic": (
        "historic site, monument, or place with deep historical significance "
        "and compelling stories worth exploring"
    ),
    "nature": (
        "stunning natural attraction — beach, waterfall, canyon, forest, or "
        "coastline — that draws visitors for its scenic beauty"
    ),
}

# Order in which to pick a scoring tag from a POI's tag list.
# First match wins.
SCORING_TAG_PRIORITY = [
    "museum", "church", "architecture", "sight", "historic",
    "restaurant", "bar", "market", "neighbourhood", "park", "nature",
]


def open_db():
    if not DB_PATH.is_file():
        sys.exit(f"search.db not found at {DB_PATH}; run indexer.py first")
    conn = apsw.Connection(str(DB_PATH), flags=apsw.SQLITE_OPEN_READONLY)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    return conn


def get_embedding_config(conn):
    """Read model name and dimension from the DB config table."""
    model = conn.execute("SELECT value FROM config WHERE key='embedding_model'").fetchone()
    dim = conn.execute("SELECT value FROM config WHERE key='embedding_dim'").fetchone()
    return (model[0] if model else "openai:text-embedding-3-small",
            int(dim[0]) if dim else 512)


def embed_texts(texts, model, dim):
    """Embed a list of texts using the same model and dimension as the index."""
    from openai import OpenAI
    client = OpenAI()
    model_name = model[len("openai:"):] if model.startswith("openai:") else model
    resp = client.embeddings.create(model=model_name, input=texts, dimensions=dim)
    vecs = [np.array(d.embedding, dtype=np.float32) for d in resp.data]
    return [v / np.linalg.norm(v) for v in vecs]


def load_ideal_embeddings(conn):
    """Return {tag: unit_vector} for each scoring tag."""
    model, dim = get_embedding_config(conn)
    tags = list(TAG_IDEALS.keys())
    texts = [TAG_IDEALS[t] for t in tags]
    print(f"Embedding {len(tags)} ideal descriptions (model={model}, dim={dim})...")
    vecs = embed_texts(texts, model, dim)
    return dict(zip(tags, vecs))


def pick_scoring_tag(poi_tags):
    """Pick the first tag in SCORING_TAG_PRIORITY that the POI carries, or None."""
    tag_set = set(poi_tags)
    for t in SCORING_TAG_PRIORITY:
        if t in tag_set:
            return t
    return None


def find_poi_paths(conn, path_prefix=None):
    """Return list of (db_path, file_path) for POIs under path_prefix."""
    if path_prefix:
        norm = path_prefix.rstrip("/")
        rows = conn.execute(
            "SELECT path FROM docs WHERE page_type='poi' AND (path=? OR path LIKE ?)",
            (norm + ".md", norm + "/%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT path FROM docs WHERE page_type='poi'").fetchall()
    return [r[0] for r in rows]


def load_embedding(conn, db_path):
    """Return the stored embedding as a numpy unit vector, or None."""
    row = conn.execute("SELECT embedding FROM embeddings WHERE path=?", (db_path,)).fetchone()
    if not row:
        return None
    return np.frombuffer(row[0], dtype=np.float32).copy()


def score_poi_all_tags(poi_embedding, poi_tags, ideal_embeddings):
    """Return {tag: score} for every scoring tag the POI carries."""
    scores = {}
    for tag in poi_tags:
        ideal = ideal_embeddings.get(tag)
        if ideal is not None:
            scores[tag] = round(float(np.dot(poi_embedding, ideal)), 4)
    return scores


def resolve_file_path(db_path):
    """Convert a DB path (e.g. europe/france/paris/eiffel_tower.md) to a filesystem path."""
    return CONTENT_DIR / db_path


def load_poi_tags(file_path):
    """Read frontmatter tags from a POI file."""
    if not file_path.is_file():
        return []
    post = frontmatter.load(file_path)
    raw = post.metadata.get("tags", [])
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return []


def write_scores(file_path, scores):
    """Write (or update) the scores dict in a POI's frontmatter."""
    post = frontmatter.load(file_path)
    post.metadata["scores"] = scores
    with open(file_path, "wb") as f:
        frontmatter.dump(post, f)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", help="Limit to POIs under this content path (e.g. europe/france/paris)")
    parser.add_argument("--dry-run", action="store_true", help="Print scores without writing to files")
    args = parser.parse_args()

    conn = open_db()

    # Check embeddings table exists
    has_emb = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'"
    ).fetchone()
    if not has_emb:
        sys.exit("embeddings table not found in search.db — run indexer.py first")

    ideal_embeddings = load_ideal_embeddings(conn)

    db_paths = find_poi_paths(conn, args.path)
    if not db_paths:
        sys.exit(f"No POIs found{' under ' + args.path if args.path else ''}")
    print(f"Found {len(db_paths)} POIs to score")

    scored = skipped_no_emb = skipped_no_tag = 0
    for db_path in db_paths:
        file_path = resolve_file_path(db_path)
        tags = load_poi_tags(file_path)
        scores = {}
        if tags:
            poi_emb = load_embedding(conn, db_path)
            if poi_emb is None:
                skipped_no_emb += 1
                continue
            scores = score_poi_all_tags(poi_emb, tags, ideal_embeddings)

        if not scores:
            skipped_no_tag += 1
            continue

        if args.dry_run:
            title = frontmatter.load(file_path).metadata.get("title", db_path)
            scores_str = "  ".join(f"{t}={s:.4f}" for t, s in sorted(scores.items()))
            print(f"  {title}: {scores_str}")
        else:
            write_scores(file_path, scores)
            scored += 1

    if not args.dry_run:
        print(f"Done. scored={scored}  skipped(no embedding)={skipped_no_emb}  skipped(no tag)={skipped_no_tag}")


if __name__ == "__main__":
    main()
