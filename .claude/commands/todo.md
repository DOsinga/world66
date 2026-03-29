# /todo — Process a todo batch

Pick up a random shard from a todo task folder and process it.

## Usage

```
/todo <task>
```

Example: `/todo country_cleanup`

## What this command does

1. **Check prerequisites**
   - Ensure `gh` (GitHub CLI) is installed. If not, install it with `brew install gh`.
   - Ensure you're on a clean `main` branch. If not, stash or commit first.

2. **Pick a shard**
   - Look in `todo/<task>/` for `.txt` batch files (e.g., `batch_00.txt`, `batch_01.txt`).
   - Pick one at random.
   - Read the shard file to get the list of items to process.

3. **Check for existing PRs**
   - The PR branch name convention is `todo-<task>-<shard>` (e.g., `todo-country_cleanup-batch_00`).
   - Use `gh pr list --search "todo-<task>-<shard>"` to check if a PR already exists (open or merged).
   - If it does, pick a different shard. If all shards have PRs, report that the task is complete.

4. **Create a branch**
   - Create and switch to branch `todo-<task>-<shard>`.

5. **Read the task description**
   - Read `todo/<task>/TASK.md` to understand what needs to be done.

6. **Process each item in the shard**
   - Read the shard file line by line.
   - For each item, perform the task described in TASK.md.
   - Commit each item separately with the commit message format specified in TASK.md.
   - Do NOT push until all items are processed.

7. **Delete the shard file**
   - After all items are processed, delete the batch file (e.g., `batch_00.txt`).
   - Commit the deletion: "Complete: todo/<task>/<shard>"

8. **Push and create a PR**
   - Push the branch: `git push -u origin todo-<task>-<shard>`
   - Create a PR using `gh pr create`:
     - Title: `todo-<task>-<shard>` (e.g., `todo-country_cleanup-batch_00`)
     - Body: list the items processed and a brief summary of changes
   - Return the PR URL.

## Important

- Process ALL items in the shard before creating the PR. One shard = one PR.
- Each item within the shard gets its own commit.
- Read TASK.md carefully — it defines the specific work for each item.
- Don't push individual commits. Push once at the end, then create the PR.
- If an item fails or can't be processed, note it in the PR description and move on.
