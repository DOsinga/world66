#!/usr/bin/env python3
"""
Train per-tag Ridge regression models on labeled POI data.

Labels come from tools/labels.csv (path, tag, rating, title).
Embeddings come from search.db.
Trained weights are saved to tools/scorer_weights.json.

Usage:
  tools/train_scorer.py              # train and save
  tools/train_scorer.py --evaluate   # show per-tag cross-val scores
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import apsw
import numpy as np
import sqlite_vec

DB_PATH = Path(__file__).resolve().parent.parent / "search.db"
LABELS_PATH = Path(__file__).resolve().parent / "labels.csv"
WEIGHTS_PATH = Path(__file__).resolve().parent / "scorer_weights.json"

# Only train ML models for the nav-level tags.
# Fine-grained tags (museum, sight, restaurant, bar, etc.) use cosine similarity.
TRAIN_TAGS = {"eating_out", "bars_and_cafes"}

# Tags with too few labels fall back to cosine similarity (see score_pois.py).
MIN_LABELS = 10


def open_db():
    if not DB_PATH.is_file():
        sys.exit(f"search.db not found at {DB_PATH}")
    conn = apsw.Connection(str(DB_PATH), flags=apsw.SQLITE_OPEN_READONLY)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    return conn


def load_labels():
    """Return {tag: [(path, rating), ...]} from labels.csv."""
    import csv
    by_tag = defaultdict(list)
    with LABELS_PATH.open() as f:
        for row in csv.DictReader(f):
            by_tag[row["tag"]].append((row["path"], float(row["rating"])))
    return by_tag


def load_embedding(conn, path):
    row = conn.execute("SELECT embedding FROM embeddings WHERE path=?", (path,)).fetchone()
    if not row:
        return None
    return np.frombuffer(row[0], dtype=np.float32).copy()


def build_xy(conn, label_pairs):
    """Return (X, y) arrays for a list of (path, rating) pairs."""
    X, y = [], []
    for path, rating in label_pairs:
        emb = load_embedding(conn, path)
        if emb is None:
            continue
        X.append(emb)
        y.append((rating - 1) / 4.0)  # normalise 1-5 → 0-1
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def train_ridge(X, y, alpha=1.0):
    """Fit Ridge regression; return (weights, bias) as plain numpy arrays."""
    from sklearn.linear_model import Ridge
    model = Ridge(alpha=alpha)
    model.fit(X, y)
    return model.coef_.tolist(), float(model.intercept_)


def cross_val_score(X, y, alpha=1.0, cv=5):
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import cross_val_score as _cvs
    model = Ridge(alpha=alpha)
    scores = _cvs(model, X, y, cv=min(cv, len(y)), scoring="r2")
    return float(scores.mean()), float(scores.std())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluate", action="store_true", help="Show cross-val R² per tag")
    parser.add_argument("--alpha", type=float, default=1.0, help="Ridge regularisation (default: 1.0)")
    args = parser.parse_args()

    conn = open_db()
    by_tag = load_labels()

    weights = {}
    for tag, pairs in sorted(by_tag.items()):
        if tag not in TRAIN_TAGS:
            continue
        X, y = build_xy(conn, pairs)
        n = len(X)
        if n < MIN_LABELS:
            print(f"  {tag}: {n} labels — skipping (< {MIN_LABELS}), will use cosine fallback")
            continue

        if args.evaluate:
            r2_mean, r2_std = cross_val_score(X, y, alpha=args.alpha)
            print(f"  {tag}: {n} labels  R²={r2_mean:.3f} ±{r2_std:.3f}")
        else:
            coef, intercept = train_ridge(X, y, alpha=args.alpha)
            weights[tag] = {"coef": coef, "intercept": intercept, "n_labels": n}
            print(f"  {tag}: trained on {n} labels")

    if not args.evaluate:
        WEIGHTS_PATH.write_text(json.dumps(weights, separators=(",", ":")))
        print(f"\nWeights saved to {WEIGHTS_PATH}")
        print(f"Trained tags: {sorted(weights)}")


if __name__ == "__main__":
    main()
