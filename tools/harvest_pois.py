#!/usr/bin/env python3
"""
Harvest draft POIs from the server and promote them into content/.

The server stores draft POIs under plans/<plan_slug>/<city_path>/<poi>.md.
This script fetches them via the authenticated API, reviews each one
(skips duplicates, warns on missing coords), writes approved ones to
content/, and opens a GitHub PR.

Usage:
  python tools/harvest_pois.py \
    --server https://world66.ai \
    --token <HARVEST_TOKEN>

  # Or put HARVEST_TOKEN and W66_SERVER in .env:
  python tools/harvest_pois.py

Environment variables (can also be passed as flags):
  HARVEST_TOKEN   Secret token set in server .env
  W66_SERVER      Base URL of the world66 server (default: http://localhost:8066)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

import frontmatter

REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"


def fetch_pois(server: str, token: str) -> list[dict]:
    url = f"{server.rstrip('/')}/api/plans/harvest-pois/?token={token}"
    req = urllib.request.Request(url, headers={"User-Agent": "harvest-pois/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def already_in_content(city_path: str, poi_slug: str) -> bool:
    """Return True if this POI already exists anywhere under content/<city_path>/."""
    city_dir = CONTENT_DIR / city_path
    if not city_dir.is_dir():
        return False
    return any(city_dir.rglob(f"{poi_slug}.md"))


def write_poi(poi: dict) -> Path | None:
    city_path = poi["city_path"]
    poi_slug  = poi["poi_slug"]

    if already_in_content(city_path, poi_slug):
        print(f"  skip (exists): {city_path}/{poi_slug}")
        return None

    if not poi.get("latitude") or not poi.get("longitude"):
        print(f"  skip (no coords): {city_path}/{poi_slug}")
        return None

    meta = {
        "title":     poi["title"],
        "type":      poi.get("type", "poi"),
        "category":  poi.get("category", ""),
        "latitude":  poi["latitude"],
        "longitude": poi["longitude"],
    }
    post = frontmatter.Post(content=poi["body"], **meta)

    dest_dir = CONTENT_DIR / city_path
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / f"{poi_slug}.md"
    out_path.write_text(frontmatter.dumps(post))
    print(f"  written: content/{city_path}/{poi_slug}.md")
    return out_path


def git(args: list[str]) -> str:
    result = subprocess.run(["git"] + args, cwd=str(REPO), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Harvest draft POIs from the server into content/")
    parser.add_argument("--server", default=os.environ.get("W66_SERVER", "http://localhost:8066"))
    parser.add_argument("--token",  default=os.environ.get("HARVEST_TOKEN", ""))
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print without writing")
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or HARVEST_TOKEN env var required", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching draft POIs from {args.server}...")
    try:
        pois = fetch_pois(args.server, args.token)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} — {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(pois)} draft POIs")
    if not pois:
        print("Nothing to harvest.")
        return

    if args.dry_run:
        for p in pois:
            coords = f"{p['latitude']}, {p['longitude']}" if p.get("latitude") else "NO COORDS"
            print(f"  {p['city_path']}/{p['poi_slug']}  [{p['category']}]  {coords}")
        return

    # Create branch
    branch = f"harvest-pois-{date.today().strftime('%Y%m%d')}"
    try:
        git(["checkout", "origin/main", "-b", branch])
    except RuntimeError:
        # Branch already exists — reuse it
        git(["checkout", branch])

    written = []
    for poi in pois:
        path = write_poi(poi)
        if path:
            written.append(path)
            git(["add", str(path)])
            git(["commit", "-m", f"feat({poi['city_path'].split('/')[-1]}): add POI — {poi['title']}"])

    if not written:
        print("Nothing new to write — all POIs already exist or lack coordinates.")
        git(["checkout", "main"])
        git(["branch", "-D", branch])
        return

    print(f"\nPushing {len(written)} POIs and opening PR...")
    git(["push", "-u", "origin", branch])

    filelist = "\n".join(f"- `content/{p.relative_to(CONTENT_DIR)}`" for p in written)
    body = f"""## Harvest draft POIs

Promoted {len(written)} draft POIs from user trip plans into the world66 guide.

### New files
{filelist}

### How to review
- Check coordinates are correct for each POI
- Check body text reads well and matches the place
- Merge when satisfied; re-run the script to pick up new drafts

🤖 Generated by `tools/harvest_pois.py`
"""
    result = subprocess.run(
        ["gh", "pr", "create",
         "--title", f"Harvest draft POIs — {date.today()}",
         "--body", body,
         "--base", "main",
         "--head", branch],
        cwd=str(REPO), capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"PR creation failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    print(f"PR: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
