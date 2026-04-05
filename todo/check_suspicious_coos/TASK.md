# Check Suspicious Coordinates

A sibling-cluster outlier detector (`tools/detect_suspicious_geo.py`) flagged
pages whose coordinates sit far from their neighbours. Most are genuine bugs —
wrong country, wrong continent, legacy spam with random coords — but some will
be false positives (real POIs in suburbs on the edge of a cluster).

Each batch lists paths relative to `content/`. For every entry, read the file
and consider whether the coordinate is reasonable.

## For each entry

Open the file. Look at `latitude` / `longitude` in the frontmatter and compare
against the title, body, and the position of the file in the tree.

Pick one of the following actions:

1. **Coordinate is fine** — leave the file alone. False positives are expected
   (suburbs, outlying museums, etc.). Just move on.

2. **Spam / junk entry** — if the page is clearly garbage (gibberish text,
   myspace/aim contact info, obviously fake content, wrong-country spam),
   delete the file.

3. **Filed in the wrong place** — if the content is a real POI but sits under
   the wrong country/city (e.g. a Paris restaurant under `germany/`), move the
   file to the correct location in the tree. Check `LOCATIONS.md` for where
   things belong.

4. **Shouldn't have a coordinate at all** — if the "page" is actually a
   section-level overview (e.g. a generic `sightseeing.md`, `museums.md`,
   `nightlife.md`, a category index), remove the `latitude` and `longitude`
   lines from the frontmatter. Sections don't need coordinates.

5. **Coordinate is wrong** — if it's a real POI in the right place but the
   coordinates are wrong, fix them. Do a quick search (Wikipedia, OSM,
   official site) to find the correct lat/lon and update the frontmatter.

## Committing

Commit each entry separately where practical, with a short message describing
what you did (`delete spam POI foo`, `fix coords for bar`, `move baz to
correct country`, `remove coords from section page`).

## After the batch

Delete the batch file and open a PR per the todo skill workflow.
