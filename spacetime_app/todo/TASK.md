# Task: Check event sources and add events

## What you're doing

Each file in `spacetime_app/sources/` describes a URL to monitor for events.
Your job is to pick overdue sources, fetch them, extract events, and write
event files into `spacetime_app/events/`.

## Steps

1. **Find overdue sources**
   Run the helper to list sources due for a check:
   ```bash
   venv/bin/python spacetime_app/todo/list_due.py
   ```
   This prints source slugs that are overdue based on `last_checked` + `interval_days`.
   Pick one (or a small batch of the same city).

2. **Check for an existing PR**
   Branch name: `spacetime-source-<slug>` (e.g. `spacetime-source-tivoli-utrecht`).
   ```bash
   gh pr list --state all --search "spacetime-source-<slug>"
   ```
   If one exists, skip to the next source.

3. **Create a branch**
   Always branch off `origin/main`:
   ```bash
   git fetch origin
   git checkout -b spacetime-source-<slug> origin/main
   ```

4. **Read the source file**
   `spacetime_app/sources/<slug>.md` — read the frontmatter and the notes
   section carefully. The notes tell you what to look for on that page.

5. **Fetch and parse the URL**
   Use the `url` from frontmatter. Look for events in the next 60 days.
   Cross-reference the `poi` field: events at this source belong to that venue.

6. **For each event found**
   - Check if an event file already exists in `spacetime_app/events/` with the
     same date and venue (avoid duplicates).
   - Write a new file: `spacetime_app/events/YYYY-MM-DD-<slug>.md`
   - Frontmatter: `title`, `poi`, `date`, `time_start`, `time_end` (if known),
     `category`, `url` (direct link to event if available, else source url).
   - Body: 1–3 sentence description of the event.
   - Commit: `Add event: <title> (<date>)`

7. **Update `last_checked` in the source file**
   Set `last_checked` to today's date (ISO format: `YYYY-MM-DD`).
   Commit: `Update last_checked: sources/<slug>.md`

8. **Push and open a PR**
   ```bash
   git push -u origin spacetime-source-<slug>
   gh pr create --title "spacetime-source-<slug>" --body "..."
   ```
   Body should list the events added and note any skipped (already exist, too far out, etc.).

## Rules

- Only add events in the **next 60 days** from today.
- Skip events that already have a matching file (same date + same poi).
- If the page is unavailable or has no upcoming events, still update
  `last_checked` and note it in the PR description.
- Do not add events you are not confident about — it is better to skip than
  to hallucinate an event.
- One PR per source slug.

## Event file format

See `spacetime_app/events/README.md` for the full format reference.
