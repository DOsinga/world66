# Task: Delist shadow POIs that now exist in W66

## When to run this

Run `check_w66.py` periodically to find shadow POIs that have been added to
World66. When a match is found, follow the steps below to migrate references
and remove the shadow file.

```bash
venv/bin/python spacetime_app/todo/check_w66.py
```

## Steps for each matched shadow POI

1. **Check the match is correct**
   Verify the W66 path and the shadow POI are truly the same venue.
   If uncertain, skip and note it in the PR.

2. **Create a branch**
   ```bash
   git fetch origin
   git checkout -b spacetime-delist-<slug> origin/main
   ```

3. **Set `w66_path` in the shadow file**
   Edit `spacetime_app/pois/<slug>.md` and set:
   ```yaml
   w66_path: europe/netherlands/utrecht/tivoli_vredenburg
   ```
   Commit: `Claim shadow POI: spacetime/<slug> → <w66_path>`

   At this point `load_venue()` already transparently redirects — events
   and sources keep working immediately without any other changes.

4. **Migrate event files**
   Find all event files that reference `spacetime/<slug>`:
   ```bash
   grep -rl "poi: spacetime/<slug>" spacetime_app/events/
   ```
   Update each one: change `poi: spacetime/<slug>` → `poi: <w66_path>`.
   Commit: `Migrate events: spacetime/<slug> → <w66_path>`

5. **Migrate source files**
   ```bash
   grep -rl "poi: spacetime/<slug>" spacetime_app/sources/
   ```
   Update each one similarly.
   Commit: `Migrate sources: spacetime/<slug> → <w66_path>`

6. **Delete the shadow file**
   ```bash
   rm spacetime_app/pois/<slug>.md
   ```
   Commit: `Delist shadow POI: <slug>`

7. **Push and open a PR**
   ```bash
   git push -u origin spacetime-delist-<slug>
   gh pr create --title "spacetime-delist-<slug>" --body "..."
   ```
   Body should list: shadow slug, W66 path, events migrated, sources migrated.

## Rules

- Always verify the match before delisting — wrong migrations are hard to undo.
- The `w66_path` redirect in `load_venue()` means the site works correctly
  as soon as step 3 is merged, even before events/sources are migrated.
- Do all migrations for one shadow POI in one PR.
