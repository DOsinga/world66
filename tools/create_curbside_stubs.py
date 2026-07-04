#!/usr/bin/env python3
"""
Create stub curbside POI files from OSM candidates JSON.
Frontmatter (including exact OSM coordinates) is written by this script.
Body text is left empty — agents fill that in separately.
"""
import json, os, sys
import frontmatter
from io import BytesIO

CANDIDATES_FILE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/barcelona_candidates.json"
CONTENT_DIR = "content/europe/spain/catalonia/barcelona"
SKIP_EXISTING = True

candidates = json.load(open(CANDIDATES_FILE))

created = []
skipped = []

for c in candidates:
    slug = c["slug"]
    path = os.path.join(CONTENT_DIR, slug + ".md")

    if SKIP_EXISTING and os.path.exists(path):
        skipped.append(slug)
        continue

    post = frontmatter.Post("")
    post["title"] = c["name"]
    post["type"] = "poi"
    post["latitude"] = c["lat"]
    post["longitude"] = c["lon"]
    post["tags"] = ["curbside"]
    post["score"] = 1

    with open(path, "wb") as f:
        frontmatter.dump(post, f)

    created.append((slug, c["name"], c["lat"], c["lon"]))

print(f"Created {len(created)} stubs, skipped {len(skipped)} existing")
for slug, name, lat, lon in created[:10]:
    print(f"  {slug}: {name} ({lat}, {lon})")
if len(created) > 10:
    print(f"  ... and {len(created)-10} more")
