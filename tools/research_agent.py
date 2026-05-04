#!/usr/bin/env python3
"""
Tabbi Research Agent — enriches world66 content for a destination.

Given a city path (e.g. europe/france/midi/cotedazur/marseille), the agent:
1. Reads existing POI content for the city
2. Uses the Anthropic API (Claude) to identify notable missing places
3. Web-searches for each missing place to gather facts
4. Writes new POI .md files following STYLE.md conventions
5. Opens a GitHub PR

Usage:
  python tools/research_agent.py --city-path europe/france/midi/cotedazur/marseille \
                                  --city-title Marseille

Environment variables:
  ANTHROPIC_API_KEY   Required — Claude API key
  GITHUB_TOKEN        Required — for opening the PR (uses gh CLI if not set)
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

import frontmatter

REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"
STYLE_MD = (REPO / "STYLE.md").read_text() if (REPO / "STYLE.md").exists() else ""


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
    time.sleep(0.5)
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

def read_existing_pois(city_path: str) -> list[dict]:
    city_dir = CONTENT_DIR / city_path
    pois = []
    if not city_dir.is_dir():
        # Try the .md file in parent + sibling dir
        parts = city_path.rsplit("/", 1)
        if len(parts) == 2:
            city_dir = CONTENT_DIR / parts[0] / parts[1]
    if not city_dir.is_dir():
        return []

    for md_file in sorted(city_dir.rglob("*.md")):
        try:
            post = frontmatter.load(str(md_file))
            if post.metadata.get("type") in ("poi", "section", "location"):
                pois.append({
                    "title": post.metadata.get("title", md_file.stem),
                    "type":  post.metadata.get("type"),
                    "path":  str(md_file.relative_to(CONTENT_DIR).with_suffix("")),
                    "category": post.metadata.get("category", ""),
                })
        except Exception:
            continue
    return pois


# ---------------------------------------------------------------------------
# Claude API helpers
# ---------------------------------------------------------------------------

def claude_complete(messages: list[dict], system: str = "", model: str = "claude-sonnet-4-6") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": messages,
    }
    if system:
        payload["system"] = system

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
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    return data["content"][0]["text"]


# ---------------------------------------------------------------------------
# Web search (uses DuckDuckGo HTML scrape — no API key required)
# ---------------------------------------------------------------------------

def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Simple DuckDuckGo search returning titles + snippets."""
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; world66-research/1.0)",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    results = []
    # Extract result titles and snippets from DDG HTML
    for m in re.finditer(
        r'class="result__title"[^>]*>.*?href="([^"]+)"[^>]*>([^<]+)</a>.*?class="result__snippet"[^>]*>(.*?)</span>',
        html, re.DOTALL
    ):
        href    = m.group(1)
        title   = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        snippet = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        if href.startswith("http"):
            results.append({"url": href, "title": title, "snippet": snippet})
        if len(results) >= num_results:
            break
    return results


# ---------------------------------------------------------------------------
# Core: identify missing places
# ---------------------------------------------------------------------------

def find_missing_places(city_title: str, city_path: str, existing_pois: list[dict]) -> list[dict]:
    existing_titles = [p["title"] for p in existing_pois]
    existing_str = "\n".join(f"- {t}" for t in existing_titles) or "(none yet)"

    prompt = f"""You are a knowledgeable travel editor for world66.ai, a restored open-content travel guide.

City: {city_title}
Content path: {city_path}

Existing entries in the guide for this city:
{existing_str}

Your task: identify up to 8 notable places, attractions, or experiences that are NOT yet in the guide and would genuinely interest a traveller visiting {city_title}.

Rules:
- No hotels or accommodation
- Focus on things with real cultural, historical, or culinary significance
- Include a mix of categories: landmark, museum, restaurant/food, neighbourhood, market, park, viewpoint
- Be specific — name the actual place, not generic categories
- Only suggest places that actually exist and are well-known enough to find reliable information about

Respond with a JSON array of objects:
[
  {{
    "name": "Place Name",
    "category": "Landmark|Museum|Restaurant|Market|Park|Neighbourhood|Viewpoint|Bar|Gallery|Other",
    "why": "One sentence on why it matters and what makes it distinctive"
  }},
  ...
]

Only JSON, no other text."""

    response = claude_complete([{"role": "user", "content": prompt}])

    try:
        # Strip any markdown fences
        response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip())
        return json.loads(response)
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Core: write a POI file
# ---------------------------------------------------------------------------

def write_poi(
    city_path: str,
    city_title: str,
    place: dict,
    search_results: list[dict],
) -> Path | None:
    name     = place["name"]
    category = place.get("category", "Landmark")
    why      = place.get("why", "")

    # Geocode
    coords = geocode(name, city_title)
    time.sleep(0.3)

    # Use Claude to write the POI description
    search_context = "\n\n".join(
        f"Source: {r['url']}\nTitle: {r['title']}\n{r['snippet']}"
        for r in search_results
    ) or f"No search results found — write based on general knowledge of {name} in {city_title}."

    system_prompt = f"""You are a travel writer for world66.ai. Write in the voice described below.

{STYLE_MD[:3000]}"""

    user_prompt = f"""Write a POI entry for "{name}" in {city_title}.

Category: {category}
Editorial note: {why}

Research gathered from web:
{search_context}

Write 2–4 paragraphs of clean, factual prose. No headings, no bullet points, no markdown formatting inside the body text. Start directly with the place — no "This is..." or "Located in..." openers. Write as if for a well-edited printed travel guide.

Keep it under 300 words."""

    try:
        body = claude_complete(
            [{"role": "user", "content": user_prompt}],
            system=system_prompt,
        )
    except Exception as e:
        print(f"  Claude error for {name}: {e}", file=sys.stderr)
        return None

    # Build frontmatter
    slug = slugify(name)
    meta = {
        "title": name,
        "type": "poi",
        "category": category,
    }
    if coords:
        meta["latitude"]  = round(coords[0], 7)
        meta["longitude"] = round(coords[1], 7)

    post = frontmatter.Post(content=body.strip(), **meta)

    # Write file
    city_dir = CONTENT_DIR / city_path
    city_dir.mkdir(parents=True, exist_ok=True)
    out_path = city_dir / f"{slug}.md"

    if out_path.exists():
        print(f"  Skipping {slug}.md — already exists", file=sys.stderr)
        return None

    out_path.write_text(frontmatter.dumps(post))
    print(f"  Written: {out_path.relative_to(REPO)}", file=sys.stderr)
    return out_path


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(args: list[str], cwd: Path = REPO) -> str:
    result = subprocess.run(
        ["git"] + args, cwd=str(cwd), capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def create_pr(branch: str, city_title: str, written: list[Path]) -> str:
    filelist = "\n".join(f"- `{p.relative_to(REPO)}`" for p in written)
    body = f"""## Tabbi Research: {city_title}

Added {len(written)} new POI entries identified as missing from the world66 guide.

### New files
{filelist}

### How these were generated
1. Existing world66 content for {city_title} was read
2. Claude identified notable missing places
3. Web search gathered facts for each place
4. Claude wrote descriptions following STYLE.md conventions
5. Nominatim geocoded each location

🤖 Generated by the Tabbi research agent
"""
    result = subprocess.run(
        ["gh", "pr", "create",
         "--title", f"tabbi-research: enrich {city_title}",
         "--body", body,
         "--base", "main",
         "--head", branch],
        cwd=str(REPO), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh pr create failed: {result.stderr.strip()}")
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tabbi research agent")
    parser.add_argument("--city-path",  required=True, help="Content path, e.g. europe/france/midi/cotedazur/marseille")
    parser.add_argument("--city-title", required=True, help="Human-readable city name, e.g. Marseille")
    args = parser.parse_args()

    city_path  = args.city_path
    city_title = args.city_title

    print(f"[tabbi-research] Starting for {city_title} ({city_path})", file=sys.stderr)

    # 1. Read existing content
    existing = read_existing_pois(city_path)
    print(f"[tabbi-research] Found {len(existing)} existing entries", file=sys.stderr)

    # 2. Identify missing places
    print("[tabbi-research] Asking Claude for missing places...", file=sys.stderr)
    try:
        missing = find_missing_places(city_title, city_path, existing)
    except Exception as e:
        print(f"[tabbi-research] Failed to identify missing places: {e}", file=sys.stderr)
        sys.exit(1)

    if not missing:
        print("[tabbi-research] No missing places identified — done.", file=sys.stderr)
        sys.exit(0)

    print(f"[tabbi-research] Found {len(missing)} missing places to add", file=sys.stderr)

    # 3. Create branch
    today = date.today().strftime("%Y%m%d")
    branch = f"tabbi-research-{slugify(city_title)}-{today}"
    try:
        git(["checkout", "main"])
        git(["pull", "--ff-only"])
        git(["checkout", "-b", branch])
    except RuntimeError as e:
        print(f"[tabbi-research] Git branch error: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Write each POI
    written = []
    for place in missing:
        name = place.get("name", "")
        if not name:
            continue
        print(f"[tabbi-research] Researching: {name}", file=sys.stderr)

        search_results = web_search(f"{name} {city_title} travel guide")
        time.sleep(0.5)

        path = write_poi(city_path, city_title, place, search_results)
        if path:
            written.append(path)
            git(["add", str(path)])
            git(["commit", "-m", f"feat({slugify(city_title)}): add POI — {name}"])

        time.sleep(0.5)

    if not written:
        print("[tabbi-research] Nothing written — cleaning up branch", file=sys.stderr)
        git(["checkout", "main"])
        git(["branch", "-D", branch])
        sys.exit(0)

    # 5. Push and open PR
    print(f"[tabbi-research] Pushing {len(written)} files and opening PR...", file=sys.stderr)
    try:
        git(["push", "-u", "origin", branch])
        pr_url = create_pr(branch, city_title, written)
        print(f"[tabbi-research] PR opened: {pr_url}", file=sys.stderr)
    except RuntimeError as e:
        print(f"[tabbi-research] PR creation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[tabbi-research] Done. {len(written)} POIs added for {city_title}.", file=sys.stderr)


if __name__ == "__main__":
    main()
