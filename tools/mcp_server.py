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
import subprocess
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
            "Create a tabbi trip plan on world66.ai and start a background research agent "
            "that enriches world66 content for the destination. "
            "Returns a shareable plan URL and a passphrase to access it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destination city or region (e.g. 'Marseille', 'Tuscany', 'Tokyo')",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO 8601 format (YYYY-MM-DD)",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO 8601 format (YYYY-MM-DD)",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes or interests for the trip (e.g. 'focus on food and markets')",
                },
            },
            "required": ["destination", "start_date", "end_date"],
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


def tool_plan_trip(destination: str, start_date: str, end_date: str, notes: str = "") -> str:
    # 1. Create the plan via the world66 API
    try:
        result = _http_post(f"{W66_BASE_URL}/api/plans/create", {
            "destination": destination,
            "start_date":  start_date,
            "end_date":    end_date,
            "notes":       notes,
        })
    except RuntimeError as e:
        return f"Failed to create plan: {e}"

    plan_url   = result["url"]
    passphrase = result["passphrase"]
    city_path  = result.get("city_path")
    city_title = result.get("city_title", destination)

    # 2. Launch research agent in background (non-blocking) — always, even if city_path unknown
    _launch_research_agent(city_path or "", city_title)

    # 3. Format response
    lines = [
        f"**Trip plan created: {city_title}**",
        f"",
        f"**Plan URL:** {plan_url}",
        f"**Passphrase:** `{passphrase}`",
        f"",
        f"Share this URL and passphrase with anyone joining the trip.",
        f"",
        f"A research agent is running in the background to find missing places for {city_title} "
        f"and open a pull request to world66. Check logs/ in the repo for progress.",
    ]

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


import urllib.parse


def _launch_research_agent(city_path: str, city_title: str) -> None:
    """Launch the research agent as a background subprocess."""
    from pathlib import Path as _Path
    import time as _time
    python = sys.executable
    agent_script = str(REPO_PATH / "tools" / "research_agent.py")
    if not _Path(agent_script).exists():
        return
    log_dir = REPO_PATH / "logs"
    log_dir.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", city_title.lower()).strip("-")
    log_file = log_dir / f"research-{slug}-{int(_time.time())}.log"
    cmd = [python, agent_script, "--city-title", city_title]
    if city_path:
        cmd += ["--city-path", city_path]
    with open(log_file, "w") as lf:
        subprocess.Popen(
            cmd,
            cwd=str(REPO_PATH),
            stdout=lf,
            stderr=lf,
            start_new_session=True,
        )


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
                    destination=args["destination"],
                    start_date=args["start_date"],
                    end_date=args["end_date"],
                    notes=args.get("notes", ""),
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
