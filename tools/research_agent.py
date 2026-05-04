#!/usr/bin/env python3
"""
Tabbi Research Agent — enriches world66 content for a destination.

Given a city name and optional content path, the agent:
1. Reads existing POI content for the city (if path known)
2. Uses Claude with web_search to research and write missing POIs
3. Commits each POI file in a fresh git worktree
4. Opens a GitHub PR

Usage:
  python tools/research_agent.py --city-path europe/france/midi/cotedazur/marseille \
                                  --city-title Marseille

  # city-path is optional — agent will still run for unknown cities
  python tools/research_agent.py --city-title Dijon

Environment variables:
  ANTHROPIC_API_KEY   Required
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# Load .env from repo root
REPO = Path(__file__).resolve().parent.parent
_dotenv = REPO / ".env"
if _dotenv.exists():
    for _line in _dotenv.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

CONTENT_DIR = REPO / "content"
STYLE_MD = (REPO / "STYLE.md").read_text() if (REPO / "STYLE.md").exists() else ""
LOG_DIR = REPO / "logs"
LOG_DIR.mkdir(exist_ok=True)


def log(msg: str, logfile=None):
    line = f"[tabbi-research] {msg}"
    print(line, file=sys.stderr)
    if logfile:
        logfile.write(line + "\n")
        logfile.flush()


# ---------------------------------------------------------------------------
# Nominatim geocoding
# ---------------------------------------------------------------------------

def geocode(query: str, city: str) -> tuple[float, float] | None:
    full_query = f"{query}, {city}"
    url = (
        "https://nominatim.openstreetmap.org/search?"
        + urllib.parse.urlencode({"q": full_query, "format": "json", "limit": "1"})
    )
    req = urllib.request.Request(url, headers={"User-Agent": "world66-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            results = json.load(r)
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    time.sleep(0.3)
    return None


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# Read existing city content
# ---------------------------------------------------------------------------

def read_existing_pois(city_path: str) -> list[str]:
    """Return list of existing POI/location titles."""
    import frontmatter as fm
    city_dir = CONTENT_DIR / city_path
    if not city_dir.is_dir():
        return []
    titles = []
    for md_file in sorted(city_dir.rglob("*.md")):
        try:
            post = fm.load(str(md_file))
            title = post.metadata.get("title", "")
            if title:
                titles.append(title)
        except Exception:
            continue
    return titles


# ---------------------------------------------------------------------------
# Claude with web_search tool
# ---------------------------------------------------------------------------

def claude_research(city_title: str, city_path: str | None, existing_titles: list[str], logfile) -> list[dict]:
    """
    Ask Claude to research the city and return a list of POIs to write.
    Uses the web_search tool so Claude can look things up itself.
    Returns: [{"name", "category", "body", "latitude", "longitude"}, ...]
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    existing_str = "\n".join(f"- {t}" for t in existing_titles) or "(none yet)"

    system = f"""You are a travel editor for world66.ai, a restored open-content travel guide.

Writing style guide:
{STYLE_MD[:2000]}

Rules:
- No hotels or accommodation
- Write each POI description as 2-4 paragraphs of clean prose, no headings or bullets
- Start directly with the place — no "This is..." or "Located in..." openers
- Under 280 words per POI
- Be factual and specific, like a well-edited printed travel guide"""

    user_message = f"""Research {city_title} and identify up to 6 notable places missing from our travel guide.

Existing entries (do not duplicate):
{existing_str}

For each missing place:
1. Use web_search to look up accurate details
2. Write a complete POI entry

When you have researched and written all POIs, respond with a JSON array:
[
  {{
    "name": "Place Name",
    "category": "Landmark|Museum|Restaurant|Market|Park|Neighbourhood|Viewpoint|Bar|Gallery",
    "body": "Full prose description (2-4 paragraphs)...",
    "search_query": "what you searched for"
  }},
  ...
]

Only output the JSON array, nothing else."""

    messages = [{"role": "user", "content": user_message}]
    tools = [{
        "type": "web_search_20250305",
        "name": "web_search",
    }]

    # Agentic loop — Claude may call web_search multiple times
    max_iterations = 15
    for iteration in range(max_iterations):
        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 8192,
            "system": system,
            "tools": tools,
            "messages": messages,
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            response = json.load(r)

        stop_reason = response.get("stop_reason")
        content     = response.get("content", [])

        log(f"Iteration {iteration+1}: stop_reason={stop_reason}, blocks={len(content)}", logfile)

        if stop_reason == "end_turn":
            # Extract the final text block
            for block in content:
                if block.get("type") == "text":
                    text = block["text"].strip()
                    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        log(f"Failed to parse JSON response: {text[:200]}", logfile)
                        return []
            return []

        if stop_reason == "tool_use":
            # Add assistant message and tool results
            messages.append({"role": "assistant", "content": content})
            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_id   = block.get("id")
                    # web_search results come back in the response itself for server-side tools
                    # For client-side tool_use we'd need to call the API ourselves,
                    # but web_search_20250305 is a server-side tool — results are in the response
                    log(f"  Tool call: {tool_name} (id={tool_id})", logfile)
            # If stop_reason is tool_use but it's a server-side tool, the next turn
            # should already have the results — just continue
            if not tool_results:
                # Server-side tools: just re-send with the assistant turn appended
                continue
            messages.append({"role": "user", "content": tool_results})
            continue

        # Any other stop reason — try to parse what we have
        for block in content:
            if block.get("type") == "text":
                text = block["text"].strip()
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
        break

    log("Max iterations reached without a final response", logfile)
    return []


# ---------------------------------------------------------------------------
# Write a POI file
# ---------------------------------------------------------------------------

def write_poi(city_path: str, city_title: str, poi: dict, work_dir: Path, logfile) -> Path | None:
    import frontmatter as fm

    name     = poi.get("name", "").strip()
    category = poi.get("category", "Landmark")
    body     = poi.get("body", "").strip()

    if not name or not body:
        return None

    slug = slugify(name)
    city_dir = work_dir / "content" / city_path if city_path else work_dir / "content" / "uncategorised" / slugify(city_title)
    city_dir.mkdir(parents=True, exist_ok=True)
    out_path = city_dir / f"{slug}.md"

    if out_path.exists():
        log(f"  Skipping {slug}.md — already exists", logfile)
        return None

    # Geocode
    coords = geocode(name, city_title)
    time.sleep(0.3)

    meta = {"title": name, "type": "poi", "category": category}
    if coords:
        meta["latitude"]  = round(coords[0], 7)
        meta["longitude"] = round(coords[1], 7)

    post = fm.Post(content=body, **meta)
    out_path.write_text(fm.dumps(post))
    log(f"  Written: content/{city_path}/{slug}.md", logfile)
    return out_path


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(args: list[str], cwd: Path = REPO) -> str:
    result = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tabbi research agent")
    parser.add_argument("--city-path",  default="", help="Content path, e.g. europe/france/midi/cotedazur/marseille")
    parser.add_argument("--city-title", required=True, help="Human-readable city name, e.g. Marseille")
    args = parser.parse_args()

    city_path  = args.city_path.strip()
    city_title = args.city_title.strip()

    today     = date.today().strftime("%Y%m%d")
    branch    = f"tabbi-research-{slugify(city_title)}-{today}"
    log_path  = LOG_DIR / f"research-{slugify(city_title)}-{today}.log"

    with open(log_path, "w") as logfile:
        log(f"Starting for {city_title} (path={city_path or 'unknown'})", logfile)
        log(f"Log: {log_path}", logfile)

        # 1. Read existing content
        existing = read_existing_pois(city_path) if city_path else []
        log(f"Found {len(existing)} existing entries", logfile)

        # 2. Research with Claude + web_search
        log("Asking Claude to research missing places...", logfile)
        try:
            pois = claude_research(city_title, city_path or None, existing, logfile)
        except Exception as e:
            log(f"Claude research failed: {e}", logfile)
            sys.exit(1)

        if not pois:
            log("No POIs returned — done.", logfile)
            sys.exit(0)

        log(f"Got {len(pois)} POIs to write", logfile)

        # 3. Create a worktree branched off origin/main (safe — doesn't touch current branch)
        worktree_path = REPO / ".worktrees" / branch
        worktree_path.parent.mkdir(exist_ok=True)
        try:
            git(["fetch", "origin", "main"])
            git(["worktree", "add", "-b", branch, str(worktree_path), "origin/main"])
        except RuntimeError as e:
            log(f"Git worktree error: {e}", logfile)
            sys.exit(1)

        # 4. Write POI files into the worktree
        written = []
        for poi in pois:
            name = poi.get("name", "")
            if not name:
                continue
            log(f"Writing: {name}", logfile)
            path = write_poi(city_path, city_title, poi, worktree_path, logfile)
            if path:
                written.append(path)
                git(["add", str(path)], cwd=worktree_path)
                git(["commit", "-m", f"feat({slugify(city_title)}): add POI — {name}"], cwd=worktree_path)

        git(["worktree", "remove", "--force", str(worktree_path)])

        if not written:
            log("Nothing written — removing branch", logfile)
            git(["branch", "-D", branch])
            sys.exit(0)

        log(f"Done. {len(written)} POIs committed to local branch '{branch}'.", logfile)
        log("Run a review agent or 'git push' when ready to publish.", logfile)


if __name__ == "__main__":
    main()
