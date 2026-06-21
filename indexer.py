import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import apsw
import frontmatter
import numpy as np
import sqlite_vec
import yaml

CONTENT_DIR = Path("content")
DB_PATH = Path("search.db")

DEFAULT_LOCAL_MODEL = "mlx-community/Qwen3-Embedding-4B-4bit-DWQ"
DEFAULT_OPENAI_MODEL = "openai:text-embedding-3-small"

# Set by run() based on CLI args.
EMBEDDING_MODEL = DEFAULT_LOCAL_MODEL
EMBEDDING_DIM = 512
EMBEDDING_MAX_TOKENS = 1024
OPENAI_BATCH_SIZE = 100


def is_openai(model):
    return model.startswith("openai:")


# ----- Local (MLX) backend ---------------------------------------------------

_local_model = None
_local_tokenizer = None


def _get_local_embedder():
    global _local_model, _local_tokenizer
    if _local_model is None:
        from mlx_lm import load
        print(f"Loading embedding model {EMBEDDING_MODEL}...")
        t0 = time.time()
        _local_model, _local_tokenizer = load(EMBEDDING_MODEL)
        print(f"  loaded in {time.time()-t0:.1f}s")
    return _local_model, _local_tokenizer


def _hidden_states(model, input_ids):
    h = model.model.embed_tokens(input_ids)
    for layer in model.model.layers:
        h = layer(h, mask=None, cache=None)
    return model.model.norm(h)


def _embed_local(text):
    import mlx.core as mx
    model, tokenizer = _get_local_embedder()
    tokens = tokenizer.encode(text)[:EMBEDDING_MAX_TOKENS]
    input_ids = mx.array([tokens])
    h = _hidden_states(model, input_ids)
    pooled = mx.mean(h, axis=1)
    mx.eval(pooled)
    vec = np.array(pooled.astype(mx.float32))[0]
    return _truncate_normalize(vec)


# ----- OpenAI backend --------------------------------------------------------

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from dotenv import load_dotenv
        from openai import OpenAI
        load_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY not set")
        _openai_client = OpenAI()
    return _openai_client


def _openai_model_name():
    return EMBEDDING_MODEL[len("openai:"):]


def _embed_openai_batch(texts):
    """Embed a batch of texts via OpenAI. Returns list of unit vectors of EMBEDDING_DIM."""
    client = _get_openai_client()
    # text-embedding-3-* support Matryoshka via the `dimensions` parameter.
    resp = client.embeddings.create(
        model=_openai_model_name(),
        input=texts,
        dimensions=EMBEDDING_DIM,
    )
    return [np.array(d.embedding, dtype=np.float32) for d in resp.data]


# ----- Shared ----------------------------------------------------------------

def _truncate_normalize(vec):
    vec = vec[:EMBEDDING_DIM]
    n = np.linalg.norm(vec)
    return vec / n if n else vec


def make_embed_text(title, body):
    body = (body or "").strip()
    if not body:
        return title
    return f"{title}. {body[:2000]}"


def init_db(conn):
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(
            path UNINDEXED, title, body,
            page_type UNINDEXED, url_path UNINDEXED, location UNINDEXED
        )
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS meta (path TEXT PRIMARY KEY, mtime REAL, hash TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
            path TEXT PRIMARY KEY,
            embedding float[{EMBEDDING_DIM}]
        )
    """)

    prev_model = conn.execute("SELECT value FROM config WHERE key = 'embedding_model'").fetchone()
    prev_dim = conn.execute("SELECT value FROM config WHERE key = 'embedding_dim'").fetchone()
    if (prev_model and prev_model[0] != EMBEDDING_MODEL) or \
       (prev_dim and prev_dim[0] != str(EMBEDDING_DIM)):
        msg = f"Embedding config changed (model {prev_model and prev_model[0]} -> {EMBEDDING_MODEL}, "
        msg += f"dim {prev_dim and prev_dim[0]} -> {EMBEDDING_DIM}); dropping stale vectors"
        print(msg)
        conn.execute("DROP TABLE embeddings")
        conn.execute(f"""
            CREATE VIRTUAL TABLE embeddings USING vec0(
                path TEXT PRIMARY KEY,
                embedding float[{EMBEDDING_DIM}]
            )
        """)
    conn.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?, ?)",
                 ("embedding_model", EMBEDDING_MODEL))
    conn.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?, ?)",
                 ("embedding_dim", str(EMBEDDING_DIM)))


def file_hash(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def _load(path):
    """Load frontmatter; returns ({}, '') on invalid YAML so callers can continue."""
    try:
        post = frontmatter.load(path)
        return post.metadata, post.content
    except yaml.YAMLError:
        return {}, ''


def _url_path(rel_path):
    parts = list(rel_path.parts)
    stem = parts[-1][:-3]
    if len(parts) >= 2 and stem == parts[-2]:
        return "/".join(parts[:-1])
    return "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem


def _is_location_dir(directory):
    candidate = directory / f"{directory.name}.md"
    if candidate.is_file():
        meta, _ = _load(candidate)
        return meta.get("type", "location") == "location", meta.get("title", directory.name)
    sibling = directory.parent / f"{directory.name}.md"
    if sibling.is_file():
        meta, _ = _load(sibling)
        return meta.get("type", "location") == "location", meta.get("title", directory.name)
    return None, None


def _find_parent_location(path):
    current = path.parent
    while current != CONTENT_DIR and current != CONTENT_DIR.parent:
        is_loc, title = _is_location_dir(current)
        if is_loc is True:
            if current / f"{current.name}.md" != path:
                return title
        current = current.parent
    return ""


def extract(path):
    meta, body = _load(path)
    title = meta.get("title", path.stem)
    page_type = meta.get("type", "location")
    return title, body, page_type


def index_file(conn, path):
    rel = str(path.relative_to(CONTENT_DIR))
    mtime = path.stat().st_mtime
    h = file_hash(path)

    row = conn.execute("SELECT mtime, hash FROM meta WHERE path=?", (rel,)).fetchone()
    content_changed = not row or row[0] != mtime or row[1] != h

    title = body = page_type = None
    if content_changed:
        title, body, page_type = extract(path)
        url_path = _url_path(path.relative_to(CONTENT_DIR))
        location = _find_parent_location(path)
        conn.execute("DELETE FROM docs WHERE path=?", (rel,))
        conn.execute(
            "INSERT INTO docs(path, title, body, page_type, url_path, location) VALUES(?,?,?,?,?,?)",
            (rel, title, body, page_type, url_path, location),
        )
        conn.execute("INSERT OR REPLACE INTO meta(path, mtime, hash) VALUES(?,?,?)", (rel, mtime, h))

    if not content_changed:
        has_embedding = conn.execute("SELECT 1 FROM embeddings WHERE path=?", (rel,)).fetchone()
        if has_embedding:
            return None
        title, body, _ = extract(path)

    return (rel, make_embed_text(title, body))


def _store_embedding(conn, path, vec):
    conn.execute("DELETE FROM embeddings WHERE path=?", (path,))
    conn.execute(
        "INSERT INTO embeddings(path, embedding) VALUES (?, ?)",
        (path, json.dumps(vec.tolist())),
    )


def _log_progress(i, total, t0, last_log):
    now = time.time()
    if now - last_log >= 5 or i == total:
        elapsed = now - t0
        rate = i / elapsed if elapsed else 0
        eta = (total - i) / rate if rate else 0
        print(f"  {i}/{total}  ({rate:.1f}/s, eta {eta/60:.1f} min)")
        return now
    return last_log


def embed_pending(conn, pending):
    if not pending:
        return
    print(f"Embedding {len(pending)} files via {EMBEDDING_MODEL}...")
    t0 = time.time()
    last_log = t0

    if is_openai(EMBEDDING_MODEL):
        for i in range(0, len(pending), OPENAI_BATCH_SIZE):
            chunk = pending[i:i + OPENAI_BATCH_SIZE]
            paths = [p for p, _ in chunk]
            texts = [t for _, t in chunk]
            vectors = _embed_openai_batch(texts)
            for path, vec in zip(paths, vectors):
                _store_embedding(conn, path, _truncate_normalize(vec))
            done = min(i + OPENAI_BATCH_SIZE, len(pending))
            last_log = _log_progress(done, len(pending), t0, last_log)
    else:
        for i, (path, text) in enumerate(pending, 1):
            vec = _embed_local(text)
            _store_embedding(conn, path, vec)
            last_log = _log_progress(i, len(pending), t0, last_log)


def remove_deleted(conn):
    indexed = {row[0] for row in conn.execute("SELECT path FROM meta")}
    current = {str(p.relative_to(CONTENT_DIR)) for p in CONTENT_DIR.rglob("*.md")}
    for path in indexed - current:
        conn.execute("DELETE FROM docs WHERE path=?", (path,))
        conn.execute("DELETE FROM meta WHERE path=?", (path,))
        conn.execute("DELETE FROM embeddings WHERE path=?", (path,))


def run():
    conn = apsw.Connection(str(DB_PATH))
    init_db(conn)

    pending = []
    total = 0
    conn.execute("BEGIN")
    try:
        for path in CONTENT_DIR.rglob("*.md"):
            total += 1
            result = index_file(conn, path)
            if result:
                pending.append(result)
        remove_deleted(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    if pending:
        conn.execute("BEGIN")
        try:
            embed_pending(conn, pending)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    conn.close()
    print(f"Indexed {total} files; {len(pending)} (re)embedded")


def main():
    parser = argparse.ArgumentParser(description="Build search.db: FTS5 docs index + POI embeddings")
    parser.add_argument(
        "--model",
        default=DEFAULT_LOCAL_MODEL,
        help=(f"Embedding model. Local MLX repo (default: {DEFAULT_LOCAL_MODEL}) "
              f"or 'openai:<model>' (e.g. {DEFAULT_OPENAI_MODEL})"),
    )
    parser.add_argument("--dim", type=int, default=512, help="Embedding dimension (Matryoshka truncation)")
    args = parser.parse_args()

    global EMBEDDING_MODEL, EMBEDDING_DIM
    EMBEDDING_MODEL = args.model
    EMBEDDING_DIM = args.dim
    run()


if __name__ == "__main__":
    main()
