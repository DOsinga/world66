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
import json
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
        "A world-class museum housing extraordinary permanent collections of art, history, "
        "science, or culture. Drawing millions of visitors annually, it is one of the great "
        "cultural institutions of its city or country — with blockbuster temporary exhibitions, "
        "deep scholarly collections, and works or artefacts of global renown. Visiting is a "
        "highlight of any trip and an experience that stays with you long after."
    ),
    "sight": (
        "An iconic, unmissable landmark that defines the city and appears on every traveller's "
        "list. Whether a great monument, a famous square, a celebrated viewpoint, or a historic "
        "district, it carries deep historical or cultural meaning and offers an experience — a "
        "view, a moment, a sense of place — that cannot be found anywhere else. Instantly "
        "recognisable, visited by millions, yet still capable of leaving a strong impression."
    ),
    "architecture": (
        "A building or structure of outstanding architectural significance — celebrated for its "
        "design, construction, or historical importance. It may be a cathedral, a palace, a "
        "modernist landmark, or an engineering marvel, but in every case it is a work that "
        "architects, historians, and curious travellers seek out specifically for what it "
        "represents in the story of human building."
    ),
    "restaurant": (
        "A restaurant that serious food lovers make a point of visiting — not just good for the "
        "neighbourhood, but genuinely outstanding: a kitchen with a clear point of view, "
        "ingredients handled with skill and care, dishes that are memorable long after the meal. "
        "It may be a celebrated fine-dining address, a beloved neighbourhood bistro, or a "
        "specialist spot doing one thing exceptionally well. Booking ahead is usually necessary."
    ),
    "bar": (
        "A bar, pub, or drinks venue with a genuine identity — the kind of place that earns "
        "loyal regulars and draws visitors who care about what they drink. Whether it is a "
        "storied wine bar, a creative cocktail lounge, a neighbourhood tavern with exceptional "
        "natural wines, or a beer institution, it is known for quality, character, and "
        "atmosphere. A destination in its own right, not just somewhere to pass the time."
    ),
    "market": (
        "A market that is a genuine institution — a place where locals actually shop, eat, and "
        "meet, not a tourist replica. It may be a covered food hall with outstanding produce "
        "stalls and lunch counters, a sprawling flea market famous for antiques and brocante, "
        "or a street market that has anchored a neighbourhood for generations. The energy, "
        "smells, and variety make it one of the most vivid experiences a city offers."
    ),
    "neighbourhood": (
        "A neighbourhood with a strong, distinct identity that rewards exploration on foot — "
        "its own architecture, history, street life, cafés, and independent shops. It may be "
        "an old artisan quarter, a bohemian district, a former immigrant neighbourhood that "
        "shaped the city's culture, or a waterfront area undergoing reinvention. Spending a "
        "half-day wandering here gives a truer sense of the city than most tourist sights."
    ),
    "park": (
        "A park, garden, or green space that is a significant destination in its own right — "
        "not just a place to sit, but somewhere with character, history, and things to discover. "
        "It might be a formal royal garden, a wild urban forest, a botanical garden with "
        "exceptional collections, or a beloved public park that defines a neighbourhood's "
        "identity. Locals treat it as an extension of their living room."
    ),
    "church": (
        "A church, cathedral, basilica, or religious building of major architectural or "
        "spiritual significance — one of the great sacred spaces of its city or tradition. "
        "Its scale, decoration, stained glass, or history set it apart from the hundreds of "
        "other churches in the region. Whether Gothic, Baroque, Byzantine, or Modernist, "
        "it is a building that demands time and attention."
    ),
    "historic": (
        "A historic site, monument, or place where something of lasting importance happened — "
        "a battlefield, a palace, a revolutionary square, an ancient ruin, a place of memory. "
        "Its significance goes beyond architecture: it is somewhere the past feels close, "
        "where the stories are compelling, and where understanding what happened here changes "
        "how you see the present."
    ),
    "landmark": (
        "One of the world's great landmarks — a palace, monument, or iconic site of such "
        "extraordinary fame and cultural significance that it is a primary reason to visit the "
        "city or country. It may be a royal palace of breathtaking scale and grandeur, a "
        "triumphal arch, a world-famous tower, or a historic royal residence. Millions visit "
        "each year, and it is listed among the most important cultural heritage sites on earth. "
        "No serious visit to the destination is complete without seeing it."
    ),
    "nature": (
        "A natural feature or landscape of outstanding scenic beauty — a beach, coastline, "
        "waterfall, gorge, forest, volcanic landscape, or wildlife habitat that draws visitors "
        "specifically for its natural qualities. It may be famous worldwide or a local treasure, "
        "but in either case it offers an encounter with the natural world that is genuinely "
        "moving, beautiful, or adventurous."
    ),
    "things_to_do": (
        "An unmissable attraction — a museum, monument, historic site, viewpoint, or experience "
        "that any visitor to this destination should prioritise. It carries real cultural weight, "
        "historical significance, or a wow factor that makes it a highlight of the trip. From "
        "world-famous landmarks to hidden gems only locals know, it is something you would "
        "actively regret missing and enthusiastically recommend to others."
    ),
    "eating_out": (
        "An outstanding restaurant or dining experience that serious food lovers seek out. "
        "Not just serviceable for the neighbourhood, but genuinely memorable: a kitchen with a "
        "clear identity, ingredients handled with skill, and dishes that linger in the memory "
        "long after the meal. It may be a celebrated fine-dining address, a beloved local bistro, "
        "or a hole-in-the-wall known only to regulars — what matters is that the food is "
        "exceptional and the experience is worth going out of your way for."
    ),
    "bars_and_cafes": (
        "A bar or café worth making a detour for — not just a place to get a drink, but somewhere "
        "with genuine character, a loyal local following, or a drink worth travelling for. It may "
        "be a storied grand café, a neighbourhood wine bar, a craft beer specialist, or a coffee "
        "shop with outstanding espresso. The atmosphere is right, the drinks are good, and it "
        "is somewhere you would happily return to and readily recommend."
    ),
}

# Order in which to pick a scoring tag from a POI's tag list.
# First match wins.
SCORING_TAG_PRIORITY = [
    "things_to_do", "eating_out", "bars_and_cafes",
    "landmark", "museum", "church", "architecture", "sight", "historic",
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
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv()
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


WEIGHTS_PATH = Path(__file__).resolve().parent / "scorer_weights.json"


def load_trained_weights():
    """Return {tag: (coef_array, intercept)} if scorer_weights.json exists, else {}."""
    if not WEIGHTS_PATH.is_file():
        return {}
    data = json.loads(WEIGHTS_PATH.read_text())
    return {tag: (np.array(v["coef"], dtype=np.float32), v["intercept"])
            for tag, v in data.items()}


def score_poi_all_tags(poi_embedding, poi_tags, ideal_embeddings, trained_weights=None):
    """Return {tag: score} for every scoring tag the POI carries.

    Uses trained Ridge regression weights when available for a tag,
    falling back to cosine similarity against the ideal description.
    Scores are normalised to [0, 1].
    """
    if trained_weights is None:
        trained_weights = {}
    scores = {}
    for tag in poi_tags:
        if tag in trained_weights:
            coef, intercept = trained_weights[tag]
            raw = float(np.dot(poi_embedding, coef) + intercept)
            scores[tag] = round(float(np.clip(raw, 0.0, 1.0)), 4)
        elif tag in ideal_embeddings:
            ideal = ideal_embeddings[tag]
            # cosine similarity is in roughly [-1, 1]; shift to [0, 1]
            cos = float(np.dot(poi_embedding, ideal))
            scores[tag] = round(float(np.clip((cos + 1) / 2, 0.0, 1.0)), 4)
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
    trained_weights = load_trained_weights()
    if trained_weights:
        print(f"Loaded trained weights for tags: {sorted(trained_weights)}")

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
            scores = score_poi_all_tags(poi_emb, tags, ideal_embeddings, trained_weights)

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
