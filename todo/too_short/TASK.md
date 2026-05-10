# Too Short Task

These are location pages identified as having insufficient content. For each one, make a judgement call and either expand it meaningfully or delete it.

## For each location

0. **Read** the existing file (and any child files) to understand what's there.

1. **Decide: keep or delete?**
   - If it's not a location at all (a bar, restaurant, venue tagged `type: location`): change `type` to `poi`, add appropriate tags (e.g. `bars_and_cafes`), add coordinates, and move it to the right section directory. Delete if the content is trivial or outdated.
   - If it's a real location but a genuine stub ("X is a village in Y" with nothing else): delete it unless you can write a real page about it.
   - If it's a real location with some content worth building on: expand it (see below).

2. **If keeping and expanding:**
   - Write a proper overview per STYLE.md — what makes this place distinctive, why someone would go there
   - Add `latitude` and `longitude` if missing
   - Add hero image using the `find-photo` skill if no `image` field
   - Don't force sections on a small town — a good overview alone is fine
   - Do not add `done: location_cleanup` — these items skip straight to a minimal usable state

3. **Check coordinates** — wrong-country coordinates are common in old World66 data. Fix or delete.

4. **Commit each item separately:**
   - If expanded: `"Expand: Location Name"`
   - If deleted: `"Delete: Location Name (stub/misclassified)"`
   - If converted to POI: `"Convert to POI: Name"`

## Voice and style

See STYLE.md. Use web search to research — never invent details. Short and honest beats long and vague.
