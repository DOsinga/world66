#!/usr/bin/env python3
"""Pre-compute embeddings for the /next mood chips and store them in search.db.

Run once (or re-run whenever chip texts change):
  python3 tools/embed_moods.py
"""

from pathlib import Path

import apsw
import numpy as np
import sqlite_vec
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).resolve().parent.parent / "search.db"

MOODS = [
    "A slow morning with nowhere to be — coffee, a neighbourhood bakery, watching the city wake up",
    "Somewhere that earned its scars — old stones, half-forgotten stories, places that have outlived everyone who built them",
    "Hungry and curious — street food, a crowded market, eating something you can't pronounce",
    "Following the art — a gallery you almost walked past, a mural on a side street, something that makes you stop",
    "Out of the city noise — somewhere green, a path that goes nowhere in particular, birds instead of traffic",
    "When the sun goes down — a bar with no tourists, live music somewhere, staying out later than planned",
]


def main():
    from openai import OpenAI

    client = OpenAI()

    conn = apsw.Connection(str(DB_PATH))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)

    print(f"Embedding {len(MOODS)} mood texts with text-embedding-3-small (dim=512)…")
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=MOODS,
        dimensions=512,
    )

    for mood_text, emb_data in zip(MOODS, resp.data):
        vec = np.array(emb_data.embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm:
            vec /= norm
        path = f"mood:{mood_text}"
        conn.execute("DELETE FROM embeddings WHERE path=?", (path,))
        conn.execute(
            "INSERT INTO embeddings(path, embedding) VALUES (?, ?)",
            (path, sqlite_vec.serialize_float32(vec)),
        )
        print(f"  ✓ {path}")

    print("Done.")


if __name__ == "__main__":
    main()
