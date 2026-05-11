# POI Cleanup Task

Quick pass over every POI to catch spam, misplaced entries, bad coordinates, and missing snippets. The batches are sized 50 but aren't too much work, so use 5 agents for each batch.

## For each POI in the batch

1. **Spam check** — read the file. If the content is spam, gibberish, SEO filler, or otherwise worthless, delete the file and move on. Anything that is esentially an advertisement for an external blog, travel agency or that sort of thing also needs to be deleted.

2. **Right location?** — verify the POI is filed under the correct parent location. A restaurant in Paris should not live under `content/europe/france/lyon/eating_out/`. If it's in the wrong place, move it to the correct directory (create the directory if needed). If you can't tell where it belongs, delete it.

3. **Coordinates** — if the POI has `latitude` and `longitude`, sanity-check they are in the right country/city. Off-by-a-continent coordinates are common in the old data. Fix obviously wrong ones. If coordinates are missing, add them.

4. **Content** - if the content is missing (no information yet type of thing) or thin, rewrite and add more. Most of the time it should be fine though. In cases where there is a story to be told (use sparingly) add a story tag.

5. **Snippet** — every POI should have a `snippet` field in its frontmatter: a ~8-word phrase used in overview listings. It should capture what makes this place notable or what kind of place it is. Examples:
   - `snippet: "Largest collection of Impressionist art in the world"`
   - `snippet: "Historic covered market with local produce and flowers"`
   - `snippet: "Panoramic city views from a hilltop fortress"`

   If a snippet already exists and is good, leave it. Otherwise, write one based on the body text.
