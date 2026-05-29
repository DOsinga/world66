---
name: find-photo
description: find and assign copyright-free photos to world66 content pages. invoke when the user asks to find, search, or add images/photos to destinations, cities, or content pages
argument-hint: <content-path or scope description>
---

Find copyright-free photos for World66 content pages using Wikimedia Commons and Flickr. If no argument is provided, ask the user which page or scope they want photos for.

## Steps

### Single page

1. **Determine the content path** from the user's request. Example: "find a photo for Hamburg" → `europe/germany/hamburg`. If unsure of the exact path, look in the `content/` directory.

2. **Search for candidates** without AI classification:
   ```bash
   python tools/find_photo.py --no-classify <content-path>
   ```
   This outputs JSON to stdout with candidate thumbnails. Status messages go to stderr.

3. **Review the candidates**. Parse the JSON output. If `candidates` is non-empty:
   - Read each thumbnail image file from the `thumb_path` fields
   - Pick the best photo based on relevance to the destination, visual quality, and how well it represents the place
   - Note the chosen candidate's `index`

4. **Save the chosen photo**:
   ```bash
   python tools/find_photo.py --select-meta '{"url":"...","source":"...","license":"...","attribution":"...","source_page":"..."}' <content-path>
   ```
   Pass the full candidate metadata as JSON. The script downloads the full-resolution image, resizes it, and updates the markdown frontmatter.

5. **If no candidates found** (empty `candidates` array), tell the user no suitable photos were found.

6. **If you cannot view images** (no vision capability), skip `--no-classify` and run:
   ```bash
   python tools/find_photo.py <content-path>
   ```
   This uses an installed AI CLI (gemini/codex/cline) to classify automatically.

### Batch (scoped)

1. **Determine the scope** from the user's request. Example: "all cities in the Netherlands" → prefix `europe/netherlands`, type `location`.

2. **Preview first** with dry-run:
   ```bash
   python tools/find_photo.py --batch --prefix <prefix> --type <type> --dry-run
   ```
   Show the user how many pages will be processed. Get confirmation before proceeding.

3. **For small scopes (< ~10 pages)**: loop single-page `--no-classify` calls so you can review each photo yourself. Process one at a time.

4. **For large scopes (10+ pages)**: use the batch mode with CLI adapter classification:
   ```bash
   python tools/find_photo.py --batch --prefix <prefix> --type <type>
   ```
   Or use `--no-classify --output candidates.json` to get all candidates in a file:
   ```bash
   python tools/find_photo.py --batch --prefix <prefix> --type <type> --no-classify --output candidates.json
   ```
   Then review and `--select-meta` for each page.

5. **Report results** — summarize how many pages were processed, how many got photos, and any that were skipped.

## Rules

- Never use `--force` unless the user explicitly asks to replace existing images.
- Always run `--dry-run` before large batch operations to preview the scope.
- `FLICKR_API_KEY` in `.env` is optional. Without it, only Wikimedia Commons is searched.
- Don't process hundreds of pages without user confirmation — check the count first.
- Exit codes: 0 = success/candidates found, 1 = no suitable photo found, 2 = error.
- Pages that already have an `image` field in frontmatter are automatically skipped (unless `--force`).
- The `--type` flag defaults to `location`. Other options: `section`, `poi`.
