---
title: "feat: Multi-CLI image classification for find_photo.py"
type: feat
status: completed
date: 2026-03-30
---

# Multi-CLI Image Classification for find_photo.py

## Overview

Replace the `google.genai` Python SDK in `tools/find_photo.py` with CLI-based image classification. The script auto-detects which AI CLI is installed on the user's system and uses that — no API keys required. CLIs authenticate via OAuth or local credentials.

## Problem Statement

Currently `find_photo.py` requires a `GEMINI_API_KEY` to use the `google.genai` SDK. CLI tools like Gemini CLI authenticate via OAuth (browser login), eliminating the need for API keys. Different users will have different CLIs installed — the script should detect what's available and use it.

## Research Findings: Which CLIs Support Image Classification?

Seven CLI tools were evaluated. The requirement: accept image files + text prompt in non-interactive mode, return text output.

### Usable for image classification

| CLI | Command syntax | Auth method |
|-----|---------------|-------------|
| **Gemini CLI** | `gemini -p "prompt @file.jpg"` | Google OAuth |
| **OpenAI Codex CLI** | `codex exec -i file.jpg "prompt"` | OpenAI login |
| **Cline CLI** | `cline -y -i file.jpg "prompt"` | Configurable per model |

### Not usable

| CLI | Why not |
|-----|---------|
| **Claude Code** | CLI cannot accept image input ([GitHub #618](https://github.com/anthropics/claude-code/issues/618)) |
| **Goose** | No image flag in CLI mode ([GitHub #1591](https://github.com/block/goose/issues/1591)) |
| **Aider** | Designed for code editing, not classification tasks |
| **OpenCode** | CLI cannot accept image files |

## Proposed Solution

### Architecture

```
find_photo.py
  └── pick_best_photo()
        └── _get_cli_adapter()
              ├── Detect: shutil.which('gemini') → GeminiAdapter
              ├── Detect: shutil.which('codex')  → CodexAdapter
              ├── Detect: shutil.which('cline')  → ClineAdapter
              └── None found → raise error
```

Each adapter is a simple class that:
1. Writes thumbnail bytes to temp files
2. Builds the CLI-specific command
3. Runs via `subprocess.run` with timeout
4. Returns stdout text

### CLI detection order

1. `gemini` — most common, free tier, Google OAuth
2. `codex` — OpenAI's CLI
3. `cline` — open-source, multi-provider

User can override with `--cli gemini|codex|cline`.

## Acceptance Criteria

- [ ] `pick_best_photo()` calls CLI tools instead of `google.genai` SDK
- [ ] Remove `google.genai` import, `gemini_key` parameter, `GEMINI_API_KEY` requirement
- [ ] Auto-detect installed CLI via `shutil.which()`
- [ ] Support `--cli` arg to force a specific CLI
- [ ] Adapters for Gemini CLI, Codex CLI, Cline CLI
- [ ] All existing functionality preserved (thumbnail comparison, NONE detection, index parsing)
- [ ] Remove `google-genai` from `pyproject.toml`

## MVP Implementation

### Step 1: CLI adapter base pattern

**`tools/find_photo.py`**:

```python
class CLIAdapter:
    """Base for AI CLI adapters that classify images."""

    name: str

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        """Send prompt + images to CLI, return text response."""
        raise NotImplementedError


class GeminiAdapter(CLIAdapter):
    name = 'gemini'

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        file_refs = ' '.join(f'@{p}' for p in image_paths)
        result = subprocess.run(
            ['gemini', '-p', f'{prompt} {file_refs}'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f'gemini failed: {result.stderr}')
        return result.stdout.strip()


class CodexAdapter(CLIAdapter):
    name = 'codex'

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        cmd = ['codex', 'exec', '--full-auto']
        for p in image_paths:
            cmd.extend(['-i', str(p)])
        cmd.append(prompt)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f'codex failed: {result.stderr}')
        return result.stdout.strip()


class ClineAdapter(CLIAdapter):
    name = 'cline'

    def run(self, prompt: str, image_paths: list[Path]) -> str:
        cmd = ['cline', '-y']
        for p in image_paths:
            cmd.extend(['-i', str(p)])
        cmd.append(prompt)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f'cline failed: {result.stderr}')
        return result.stdout.strip()


CLI_ADAPTERS = [GeminiAdapter, CodexAdapter, ClineAdapter]


def _get_cli_adapter(force: str = None) -> CLIAdapter:
    """Detect available CLI or use forced choice."""
    if force:
        for cls in CLI_ADAPTERS:
            if cls.name == force:
                if not shutil.which(force):
                    raise RuntimeError(f'{force} is not installed')
                return cls()
        raise RuntimeError(f'Unknown CLI: {force}')
    for cls in CLI_ADAPTERS:
        if shutil.which(cls.name):
            return cls()
    raise RuntimeError(
        'No supported AI CLI found. Install one of: gemini, codex, cline'
    )
```

### Step 2: Update `pick_best_photo()`

```python
def pick_best_photo(candidates: list[Candidate], thumb_data: list[bytes],
                    page_text: str, cli: CLIAdapter) -> int | None:
    """Use AI CLI to pick the best photo. Returns candidate index or None."""
    prompt = (
        f'You are selecting the best photo for a travel guide page. '
        f'Below are {len(thumb_data)} candidate photos numbered 0 to {len(thumb_data) - 1}.\n\n'
        f'Page content:\n{page_text[:1000]}\n\n'
        f'Pick the single best photo based on:\n'
        f'1. Relevance to this specific destination/topic\n'
        f'2. Visual quality and composition\n'
        f'3. How well it represents the place to a traveler\n\n'
        f'If NONE of the photos are suitable, respond with just "NONE".\n'
        f'Otherwise respond with just the number (0-{len(thumb_data) - 1}) of the best photo.'
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        image_paths = []
        for i, data in enumerate(thumb_data):
            path = Path(tmpdir) / f'photo_{i}.jpg'
            path.write_bytes(data)
            image_paths.append(path)

        try:
            answer = cli.run(prompt, image_paths)
        except Exception as e:
            print(f'  {cli.name} evaluation failed: {e}')
            return None

    if 'NONE' in answer.upper():
        return None
    match = re.search(r'\d+', answer)
    if match:
        idx = int(match.group())
        if 0 <= idx < len(thumb_data):
            return idx
    print(f'  {cli.name} returned unexpected answer: {answer}')
    return None
```

### Step 3: Update `main()` and `process_page()`

- Remove `--gemini-key` argument and `GEMINI_API_KEY` env var check
- Add `--cli` argument (optional, choices: gemini, codex, cline)
- Detect CLI once at startup: `cli = _get_cli_adapter(args.cli)`
- Pass `cli` to `process_page()` → `pick_best_photo()`
- Print which CLI is being used: `Using {cli.name} for image classification`

### Step 4: Update imports and dependencies

- Add: `import subprocess, tempfile, shutil`
- Remove: `from google import genai` and `from google.genai import types`
- **`pyproject.toml`**: Remove `google-genai` dependency (no new deps needed — only stdlib)

## Files to Modify

| File | Change |
|------|--------|
| `tools/find_photo.py` | Replace google.genai with CLI adapters, add detection logic |
| `pyproject.toml` | Remove `google-genai` dependency |

## Dependencies & Risks

- **CLI output parsing** — CLIs may include extra text besides the number/NONE. The existing regex extraction (`re.search(r'\d+', answer)`) handles this gracefully.
- **Temp file cleanup** — `TemporaryDirectory` context manager guarantees cleanup.
- **Timeout** — 120s timeout prevents hanging on slow responses.
- **New CLIs** — Adding support for a new CLI is one small class. When Claude Code or Goose add image support, adding an adapter is trivial.

## Sources

- [Gemini CLI](https://github.com/google-gemini/gemini-cli) — `-p` flag + `@file` syntax for images
- [Codex CLI](https://developers.openai.com/codex/cli/reference) — `exec -i` for non-interactive image input
- [Cline CLI](https://docs.cline.bot/cline-cli/cli-reference) — `-y -i` for batch image classification
- [Claude Code #618](https://github.com/anthropics/claude-code/issues/618) — CLI image input not supported
- [Goose #1591](https://github.com/block/goose/issues/1591) — CLI image support requested
