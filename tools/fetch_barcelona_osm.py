#!/usr/bin/env python3
"""
Fetch named POI candidates for Barcelona from Overpass API.
Outputs a JSON file of candidates with exact OSM coordinates.
The bounding box covers the central districts: Gòtic, Eixample, Gràcia, Raval,
Born, Barceloneta, and Montjuïc.
"""
import json, sys, urllib.request, urllib.parse, time

# Central Barcelona bounding box (south, west, north, east)
BBOX = "41.340, 2.140, 41.430, 2.210"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL — fetch nodes/ways/relations that are likely curbside-worthy:
# artworks, historic sites, memorials, notable named buildings, fountains,
# churches, cathedrals, and any named building with historic/cultural significance
QUERY = f"""
[out:json][timeout:120];
(
  node["tourism"="artwork"]["name"]({BBOX});
  way["tourism"="artwork"]["name"]({BBOX});
  node["historic"]["name"]({BBOX});
  way["historic"]["name"]({BBOX});
  node["memorial"]["name"]({BBOX});
  way["memorial"]["name"]({BBOX});
  node["amenity"="fountain"]["name"]({BBOX});
  way["amenity"="fountain"]["name"]({BBOX});
  node["tourism"="attraction"]["name"]({BBOX});
  way["tourism"="attraction"]["name"]({BBOX});
  node["man_made"]["name"]["historic"]({BBOX});
  way["man_made"]["name"]["historic"]({BBOX});
  node["amenity"="place_of_worship"]["name"]["wikipedia"]({BBOX});
  way["amenity"="place_of_worship"]["name"]["wikipedia"]({BBOX});
  node["amenity"="place_of_worship"]["name"]["wikidata"]({BBOX});
  way["amenity"="place_of_worship"]["name"]["wikidata"]({BBOX});
  node["building"="church"]["name"]({BBOX});
  way["building"="church"]["name"]({BBOX});
  node["building"="cathedral"]["name"]({BBOX});
  way["building"="cathedral"]["name"]({BBOX});
  node["building"="chapel"]["name"]({BBOX});
  way["building"="chapel"]["name"]({BBOX});
  way["building"]["name"]["wikipedia"]({BBOX});
  way["building"]["name"]["wikidata"]({BBOX});
  node["building"]["name"]["wikipedia"]({BBOX});
  node["building"]["name"]["wikidata"]({BBOX});
);
out center;
"""


def run_query(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data,
                                 headers={"User-Agent": "world66-content/1.0",
                                          "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def centre(element):
    if element["type"] == "node":
        return element["lat"], element["lon"]
    # way/relation with centre
    c = element.get("center")
    if c:
        return c["lat"], c["lon"]
    return None, None


def main():
    print("Querying Overpass...", file=sys.stderr, flush=True)
    result = run_query(QUERY)
    elements = result.get("elements", [])
    print(f"  Got {len(elements)} raw elements", file=sys.stderr)

    # Deduplicate by name (keep first occurrence)
    seen = set()
    candidates = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name or name in seen:
            continue
        lat, lon = centre(el)
        if lat is None:
            continue
        seen.add(name)
        candidates.append({
            "osm_id": el.get("id"),
            "osm_type": el["type"],
            "name": name,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "tags": {k: v for k, v in tags.items() if k in (
                "tourism", "historic", "memorial", "amenity", "man_made",
                "artwork_type", "description", "wikipedia", "wikidata",
                "architect", "start_date", "heritage",
            )},
        })

    # Sort by name for easy review
    candidates.sort(key=lambda c: c["name"])
    print(f"  {len(candidates)} unique named candidates", file=sys.stderr)
    print(json.dumps(candidates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
