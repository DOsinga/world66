#!/usr/bin/env python3
"""
Tabbi MCP Server — exposes world66 trip-planning tools to Claude, ChatGPT, and Gemini.

Usage (stdio transport, as required by MCP):
  python tools/mcp_server.py

Configuration (environment variables):
  W66_BASE_URL   Base URL of the world66 site (default: http://localhost:8066)
  W66_REPO_PATH  Absolute path to the world66 repo (default: inferred from this file)

To add to Claude Desktop, add to ~/Library/Application Support/Claude/claude_desktop_config.json:
  {
    "mcpServers": {
      "tabbi": {
        "command": "python",
        "args": ["/path/to/world66/tools/mcp_server.py"],
        "env": {
          "W66_BASE_URL": "https://world66.ai",
          "W66_REPO_PATH": "/path/to/world66"
        }
      }
    }
  }
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from repo root so secrets don't need to be in claude_desktop_config
# ---------------------------------------------------------------------------
REPO_PATH = Path(os.environ.get("W66_REPO_PATH", Path(__file__).resolve().parent.parent))

_dotenv = REPO_PATH / ".env"
if _dotenv.exists():
    for _line in _dotenv.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

# ---------------------------------------------------------------------------
# MCP protocol — minimal stdio implementation (no external SDK required)
# ---------------------------------------------------------------------------
# The MCP protocol is JSON-RPC 2.0 over stdio (newline-delimited).
# We handle: initialize, tools/list, tools/call

W66_BASE_URL = os.environ.get("W66_BASE_URL", "http://localhost:8066").rstrip("/")

TOOLS = [
    {
        "name": "plan_trip",
        "description": (
            "Create a tabbi trip plan on world66.ai. Supports single or multi-city trips. "
            "Returns a shareable plan URL and a passphrase. "
            "After creating the plan, call research_city for each stop."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Trip title (e.g. 'Summer in Germany'). Required for multi-city trips.",
                },
                "stops": {
                    "type": "array",
                    "description": "List of destinations. Use this for multi-city trips.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string", "description": "City name"},
                            "start_date":  {"type": "string", "description": "YYYY-MM-DD"},
                            "end_date":    {"type": "string", "description": "YYYY-MM-DD"},
                            "notes":       {"type": "string"},
                        },
                        "required": ["destination", "start_date", "end_date"],
                    },
                },
                "destination": {
                    "type": "string",
                    "description": "Single destination (shorthand for one-city trips)",
                },
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (single city)"},
                "end_date":   {"type": "string", "description": "End date YYYY-MM-DD (single city)"},
                "notes":      {"type": "string"},
            },
        },
    },
    {
        "name": "add_pois_to_plan",
        "description": (
            "Add existing world66 POI content paths directly to a trip plan. "
            "Call this with the paths returned by research_city before doing any external research."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_slug":  {"type": "string", "description": "Plan slug from plan_trip"},
                "passphrase": {"type": "string", "description": "Plan passphrase from plan_trip"},
                "city_slug":  {"type": "string", "description": "City slug from plan_trip"},
                "poi_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of w66 content paths (e.g. ['europe/france/brittany/rennes/old-town'])",
                },
            },
            "required": ["plan_slug", "passphrase", "city_slug", "poi_paths"],
        },
    },
    {
        "name": "research_city",
        "description": (
            "Returns existing world66 POIs for a city (with content paths) plus the writing style guide. "
            "Always call this before doing any external research — add existing POIs first, "
            "then research only what's missing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "city_path": {
                    "type": "string",
                    "description": "World66 content path for the city (e.g. 'europe/france/brittany/rennes'). "
                                   "Use the city_path returned by plan_trip.",
                },
                "city_title": {
                    "type": "string",
                    "description": "Human-readable city name (e.g. 'Rennes')",
                },
            },
            "required": ["city_title"],
        },
    },
    {
        "name": "submit_pois",
        "description": (
            "Submit researched POIs to the world66 server as drafts. "
            "They will appear as suggestions in the user's trip plan. "
            "Call this after research_city once you have written up the missing places."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "city_path": {
                    "type": "string",
                    "description": "World66 content path for the city (e.g. 'europe/france/brittany/rennes')",
                },
                "city_title": {
                    "type": "string",
                    "description": "Human-readable city name",
                },
                "intro": {
                    "type": "string",
                    "description": (
                        "A 2-4 sentence introduction to the city stop, written in your own words. "
                        "This will appear at the top of the stop page. "
                        "The pois array should be ordered to match the narrative order of this intro."
                    ),
                },
                "budget": {
                    "type": "object",
                    "description": (
                        "Estimated daily budget per person for this city stop. "
                        "All amounts in the same currency. Use realistic local prices."
                    ),
                    "properties": {
                        "hotel":      {"type": "number", "description": "Per night (accommodation)"},
                        "food":       {"type": "number", "description": "Per day (meals & drinks)"},
                        "activities": {"type": "number", "description": "Per day (entrance fees, tours)"},
                        "travel":     {"type": "number", "description": "Local transport per day"},
                        "currency":   {"type": "string", "description": "Currency code, e.g. EUR, USD, PEN"},
                        "notes":      {"type": "string", "description": "E.g. 'budget traveller' or 'mid-range'"},
                    },
                },
                "pois": {
                    "type": "array",
                    "description": "List of POIs and vibes to submit. Include at least one vibe per city. Order them to match the intro narrative.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":           {"type": "string", "description": "Place or activity name"},
                            "type":           {"type": "string", "description": "'poi' (default) or 'vibe' (multi-hour activity combining several spots)"},
                            "category":       {"type": "string", "description": "Landmark|Museum|Restaurant|Market|Park|Neighbourhood|Viewpoint|Bar|Gallery"},
                            "body":           {"type": "string", "description": "Prose description (2-4 paragraphs, under 280 words)"},
                            "latitude":       {"type": "number", "description": "For poi only"},
                            "longitude":      {"type": "number", "description": "For poi only"},
                            "duration_hours": {"type": "number", "description": "For vibe: approximate duration in hours"},
                            "stops":          {"type": "array", "items": {"type": "string"}, "description": "For vibe: list of included places (names or short descriptions)"},
                        },
                        "required": ["name", "body"],
                    },
                },
                "plan_slug": {
                    "type": "string",
                    "description": "Plan slug returned by plan_trip — used to add POIs directly to the plan",
                },
                "passphrase": {
                    "type": "string",
                    "description": "Plan passphrase returned by plan_trip — required to authorise writing to the plan",
                },
                "city_slug": {
                    "type": "string",
                    "description": "City slug returned by plan_trip — used to add POIs to the right city section",
                },
            },
            "required": ["city_title", "pois", "plan_slug", "passphrase"],
        },
    },
    {
        "name": "search_world66",
        "description": (
            "Search the world66 travel guide for a destination, attraction, or place. "
            "Returns matching content paths and titles."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'Marseille', 'Vieux Port', 'bouillabaisse')",
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _http_post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body}")


def _http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "tabbi-mcp/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def tool_plan_trip(stops=None, title="", destination="", start_date="", end_date="", notes="") -> str:
    # Normalise single-city shorthand into the stops list
    if not stops:
        if not destination:
            return "Error: provide either 'stops' (multi-city) or 'destination' (single city)."
        stops = [{"destination": destination, "start_date": start_date,
                  "end_date": end_date, "notes": notes}]

    try:
        result = _http_post(f"{W66_BASE_URL}/api/plans/create", {
            "title": title,
            "stops": stops,
        })
    except RuntimeError as e:
        return f"Failed to create plan: {e}"

    plan_url   = result["url"]
    passphrase = result["passphrase"]
    plan_slug  = result.get("slug", "")
    cities     = result.get("cities", [])

    lines = [
        f"**Trip plan created**",
        f"",
        f"**Plan URL:** {plan_url}",
        f"**Passphrase:** `{passphrase}`",
        f"",
        f"Share this URL and passphrase with anyone joining the trip.",
        f"",
        f"**Keep the passphrase** — you need it for add_pois_to_plan and submit_pois.",
        f"",
        f"Now call research_city for each stop, then add_pois_to_plan / submit_pois:",
    ]
    for city in cities:
        poi_count = _count_existing_pois(city.get("city_path", ""))
        lines.append(
            f"- **{city['city_title']}**: city_path={city['city_path']!r}, "
            f"city_slug={city['city_slug']!r}, {poi_count} existing w66 POI(s)"
        )
    return "\n".join(lines)


def tool_search_world66(query: str) -> str:
    try:
        url = f"{W66_BASE_URL}/api/search?q={urllib.parse.quote(query)}"
        result = _http_get(url)
    except Exception as e:
        return f"Search failed: {e}"

    results = result.get("results", [])
    if not results:
        return f"No results found for '{query}'."

    lines = [f"Search results for '{query}':"]
    for r in results[:10]:
        title     = r.get("title", "")
        url_path  = r.get("url_path", "")
        page_type = r.get("page_type", "")
        location  = r.get("location", "")
        lines.append(f"- **{title}** (`{url_path}`) — {page_type}" + (f", {location}" if location else ""))

    return "\n".join(lines)


import re as _re
import urllib.parse


def tool_research_city(city_title: str, city_path: str = "") -> str:
    """
    Return existing w66 POIs for a city (with their content paths) plus the
    writing style guide. Claude should:
    1. Add the existing POIs to the plan via add_pois_to_plan
    2. Research only what's still missing, then call submit_pois
    """
    # Style guide
    style_md = ""
    style_file = REPO_PATH / "STYLE.md"
    if style_file.exists():
        style_md = style_file.read_text()[:3000]

    # Existing POIs, vibes, and treks — collect title + path
    existing_pois = []
    existing_vibes = []
    existing_treks = []
    if city_path:
        city_dir = REPO_PATH / "content" / city_path
        if city_dir.is_dir():
            for md_file in sorted(city_dir.rglob("*.md")):
                try:
                    head = md_file.read_text(encoding="utf-8", errors="ignore")[:512]
                    title = ""
                    for line in head.splitlines():
                        if line.startswith("title:"):
                            title = line.split(":", 1)[1].strip().strip('"').strip("'")
                            break
                    rel_path = str(md_file.relative_to(REPO_PATH / "content").with_suffix(""))
                    if "type: poi" in head or 'type: "poi"' in head:
                        existing_pois.append({"title": title, "path": rel_path})
                    elif "type: vibe" in head or 'type: "vibe"' in head:
                        existing_vibes.append({"title": title, "path": rel_path})
                    elif "type: trek" in head or 'type: "trek"' in head:
                        existing_treks.append({"title": title, "path": rel_path})
                except Exception:
                    pass

    poi_lines   = "\n".join(f"- {p['title']} (`{p['path']}`)" for p in existing_pois) or "(none yet)"
    vibe_lines  = "\n".join(f"- {p['title']} (`{p['path']}`)" for p in existing_vibes)
    trek_lines  = "\n".join(f"- {p['title']} (`{p['path']}`)" for p in existing_treks)

    sections = [
        f"## world66 content already in the guide for {city_title}",
    ]
    if existing_treks:
        sections.append(f"### Treks ({len(existing_treks)})\n{trek_lines}")
    if existing_vibes:
        sections.append(f"### Vibes ({len(existing_vibes)})\n{vibe_lines}")
    sections.append(f"### Places ({len(existing_pois)})\n{poi_lines}")
    sections.append(
        "## Instructions\n"
        f"1. Call add_pois_to_plan with ALL paths above (both treks and places) to add them to the plan.\n"
        f"2. Use web search to find what's notable or worth doing in {city_title}.\n"
        f"3. Compose a good mix for the plan — **at least one vibe** plus individual POIs:\n"
        f"   - **Vibe** (type: 'vibe'): a 2–4 hour activity that combines a few spots, "
        f"e.g. 'Morning in the Old Town' or 'Street food crawl through the market district'. "
        f"Include duration_hours and a stops list of 3–5 places visited together.\n"
        f"   - **POI** (type: 'poi'): a single place with coordinates.\n"
        f"4. For each item write 2–4 paragraphs of clean prose per the style guide, under 280 words.\n"
        f"5. Assign one category: Landmark|Museum|Restaurant|Market|Park|Neighbourhood|Viewpoint|Bar|Gallery\n"
        f"6. Write a 2–4 sentence intro for the city that references the highlights in narrative order.\n"
        f"7. Estimate a realistic daily budget per person (hotel/night, food/day, activities/day, transport/day) with currency code.\n"
        f"8. Call submit_pois with: the intro, the budget, and the pois array ordered to match the intro narrative."
    )
    sections.append("## Writing style guide\n" + style_md)
    return "\n\n".join(sections)


def tool_add_pois_to_plan(plan_slug: str, passphrase: str, city_slug: str, poi_paths: list) -> str:
    """Add existing w66 POI paths directly to a plan."""
    payload = {
        "plan_slug":  plan_slug,
        "passphrase": passphrase,
        "city_slug":  city_slug,
        "poi_paths":  poi_paths,
    }
    try:
        result = _http_post(f"{W66_BASE_URL}/api/plan/add-pois", payload)
        added = result.get("added", 0)
        return f"Added {added} existing place(s) to the plan."
    except RuntimeError as e:
        return f"Failed to add POIs: {e}"


def tool_submit_pois(city_title: str, pois: list, plan_slug: str, passphrase: str,
                     city_path: str = "", city_slug: str = "", intro: str = "", budget: dict = None) -> str:
    """POST researched POIs to the server and add them directly to the plan."""
    payload = {
        "city_path":  city_path,
        "city_title": city_title,
        "passphrase": passphrase,
        "pois":       pois,
        "plan_slug":  plan_slug,
        "city_slug":  city_slug,
        "intro":      intro,
        "budget":     budget or {},
    }
    try:
        result = _http_post(f"{W66_BASE_URL}/api/research/submit", payload)
        written = result.get("written", 0)
        return (
            f"Submitted {len(pois)} POIs for {city_title}. "
            f"Server added {written} place(s) directly to the trip plan."
        )
    except RuntimeError as e:
        return f"Submit failed: {e}"


def _count_existing_pois(city_path: str) -> int:
    """Count POI markdown files in content/<city_path>/."""
    if not city_path:
        return 0
    city_dir = REPO_PATH / "content" / city_path
    if not city_dir.is_dir():
        return 0
    count = 0
    for md_file in city_dir.rglob("*.md"):
        # Quick check: look for 'type: poi' in the first 512 bytes
        try:
            head = md_file.read_text(encoding="utf-8", errors="ignore")[:512]
            if "type: poi" in head or 'type: "poi"' in head:
                count += 1
        except Exception:
            pass
    return count


# ---------------------------------------------------------------------------
# MCP JSON-RPC dispatch
# ---------------------------------------------------------------------------

def _handle(message: dict) -> dict | None:
    method = message.get("method", "")
    msg_id = message.get("id")

    def ok(result):
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def err(code, msg):
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": msg}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "tabbi", "version": "1.0.0"},
        })

    if method == "notifications/initialized":
        return None  # no response needed

    if method == "tools/list":
        return ok({"tools": TOOLS})

    if method == "tools/call":
        params = message.get("params", {})
        name   = params.get("name", "")
        args   = params.get("arguments", {})

        try:
            if name == "plan_trip":
                text = tool_plan_trip(
                    stops=args.get("stops"),
                    title=args.get("title", ""),
                    destination=args.get("destination", ""),
                    start_date=args.get("start_date", ""),
                    end_date=args.get("end_date", ""),
                    notes=args.get("notes", ""),
                )
            elif name == "add_pois_to_plan":
                text = tool_add_pois_to_plan(
                    plan_slug=args["plan_slug"],
                    passphrase=args["passphrase"],
                    city_slug=args["city_slug"],
                    poi_paths=args["poi_paths"],
                )
            elif name == "research_city":
                text = tool_research_city(
                    city_title=args["city_title"],
                    city_path=args.get("city_path", ""),
                )
            elif name == "submit_pois":
                text = tool_submit_pois(
                    city_title=args["city_title"],
                    pois=args["pois"],
                    plan_slug=args["plan_slug"],
                    passphrase=args["passphrase"],
                    city_path=args.get("city_path", ""),
                    city_slug=args.get("city_slug", ""),
                    intro=args.get("intro", ""),
                    budget=args.get("budget"),
                )
            elif name == "search_world66":
                text = tool_search_world66(query=args["query"])
            else:
                return err(-32601, f"Unknown tool: {name}")
        except KeyError as e:
            return err(-32602, f"Missing argument: {e}")
        except Exception as e:
            return err(-32603, f"Tool error: {e}")

        return ok({"content": [{"type": "text", "text": text}]})

    if method == "ping":
        return ok({})

    return err(-32601, f"Method not found: {method}")


def main():
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            message = json.loads(raw_line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }) + "\n")
            sys.stdout.flush()
            continue

        response = _handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
