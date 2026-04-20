#!/usr/bin/env python3
"""Search Wikipedia for articles near a given latitude/longitude.

Uses the MediaWiki API geosearch to find articles with coordinates
within a given radius of a point. Results are sorted by distance.

Usage:
    python tools/wiki_geosearch.py LAT LNG [--radius METERS] [--limit N]

Examples:
    python tools/wiki_geosearch.py 25.7742 -80.1936              # Miami, default 10km
    python tools/wiki_geosearch.py 25.7742 -80.1936 --radius 5000  # 5km radius
    python tools/wiki_geosearch.py 48.8566 2.3522 --limit 100     # Paris, up to 100
"""

import argparse
import json
import sys
import urllib.request
import urllib.parse


API_URL = "https://en.wikipedia.org/w/api.php"
MAX_RADIUS = 10000  # Wikipedia API max is 10km


def geosearch(lat: float, lng: float, radius: int = 10000, limit: int = 500) -> list[dict]:
    """Return Wikipedia articles near (lat, lng).

    Each result is a dict with keys: title, pageid, lat, lon, dist (meters),
    description, url.
    """
    results = []
    gs_continue = None

    while True:
        params = {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat}|{lng}",
            "gsradius": min(radius, MAX_RADIUS),
            "gslimit": min(limit - len(results), 50),  # API max per request is 50
            "format": "json",
        }
        if gs_continue:
            params["gsoffset"] = gs_continue

        url = f"{API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "World66Bot/1.0"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        for item in data.get("query", {}).get("geosearch", []):
            results.append({
                "title": item["title"],
                "pageid": item["pageid"],
                "lat": item["lat"],
                "lon": item["lon"],
                "dist": item["dist"],
            })

        if len(results) >= limit:
            break
        # Check for continuation
        if "continue" in data and "gsoffset" in data["continue"]:
            gs_continue = data["continue"]["gsoffset"]
        else:
            break

    # Now batch-fetch short descriptions via page extracts
    if results:
        pageids = [str(r["pageid"]) for r in results]
        # Fetch in batches of 50
        descriptions = {}
        for i in range(0, len(pageids), 50):
            batch = pageids[i:i+50]
            params = {
                "action": "query",
                "pageids": "|".join(batch),
                "prop": "extracts|info",
                "exintro": "1",
                "exsentences": "1",
                "explaintext": "1",
                "inprop": "url",
                "format": "json",
            }
            url = f"{API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "World66Bot/1.0"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
            for pid, page in data.get("query", {}).get("pages", {}).items():
                descriptions[int(pid)] = {
                    "extract": page.get("extract", ""),
                    "url": page.get("fullurl", ""),
                }

        for r in results:
            info = descriptions.get(r["pageid"], {})
            r["description"] = info.get("extract", "")
            r["url"] = info.get("url", "")

    results.sort(key=lambda x: x["dist"])
    return results


def main():
    parser = argparse.ArgumentParser(description="Search Wikipedia articles near a location")
    parser.add_argument("lat", type=float, help="Latitude")
    parser.add_argument("lng", type=float, help="Longitude")
    parser.add_argument("--radius", type=int, default=10000, help="Search radius in meters (max 10000)")
    parser.add_argument("--limit", type=int, default=500, help="Max results to return")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = geosearch(args.lat, args.lng, args.radius, args.limit)

    if args.json:
        json.dump(results, sys.stdout, indent=2)
        print()
    else:
        for r in results:
            desc = r["description"][:100] + "..." if len(r["description"]) > 100 else r["description"]
            print(f"{r['dist']:>6.0f}m  {r['title']}")
            if desc:
                print(f"         {desc}")
            print(f"         {r['url']}")
            print()


if __name__ == "__main__":
    main()
