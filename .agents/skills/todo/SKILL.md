---
name: todo
description: Pick up a random shard from a todo task folder, process all items per TASK.md, and create a PR. Use when the user wants to work through batched todo items.
argument-hint: <task-name>
---

Pick up a random shard from `todo/$ARGUMENTS/` and process it.

## Steps

1. **Check prerequisites**
   - Ensure `gh` (GitHub CLI) is installed. If not, install it with `brew install gh`.
   - Ensure you're on a clean `main` branch. If not, stash or commit first.

2. **Pick a shard**
   - Look in `todo/$ARGUMENTS/` for `.txt` batch files.
   - Pick one at random.
   - Read the shard file to get the list of items to process.

3. **Check for existing PRs**
   - Branch name convention: `todo-$ARGUMENTS-<shard>` (e.g., `todo-country_cleanup-batch_00`).
   - Use `gh pr list --state all --search "todo-$ARGUMENTS-<shard>"` to check if a PR already exists (open or merged).
   - If it does, pick a different shard. If all shards have PRs, report that the task is complete.

4. **Create a branch**
   - `git checkout -b todo-$ARGUMENTS-<shard>`

5. **Read the task description**
   - Read `todo/$ARGUMENTS/TASK.md` to understand what needs to be done for each item.

6. **Process each item in the shard**
   - Read the shard file line by line.
   - For each item, perform the task described in TASK.md.
   - Commit each item separately with the commit message format specified in TASK.md.
   - Do NOT push until all items are processed.

7. **Delete the shard file**
   - After all items are processed, delete the batch file.
   - Commit: "Complete: todo/$ARGUMENTS/<shard>"

8. **Push and create a PR**
   - `git push -u origin todo-$ARGUMENTS-<shard>`
   - Create PR with `gh pr create`:
     - Title: `todo-$ARGUMENTS-<shard>`
     - Body: list the items processed and a brief summary of changes
   - Return the PR URL.

## Rules

- Process ALL items in the shard before creating the PR. One shard = one PR.
- Each item within the shard gets its own commit.
- Read TASK.md carefully — it defines the specific work for each item.
- Don't push individual commits. Push once at the end, then create the PR.
- If an item fails or can't be processed, note it in the PR description and move on.
