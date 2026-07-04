#!/usr/bin/env python3
"""
Batch-geocode curbside POIs via Nominatim and update coordinates.
Flags items that can't be found or are suspiciously far from expected location.
"""
import os, sys, time, json, urllib.request, urllib.parse
import frontmatter

CITY = "Barcelona"
COUNTRY = "Spain"
# Centre of Barcelona — flag anything more than ~5km away
CENTRE_LAT, CENTRE_LON = 41.385, 2.173
MAX_DIST_DEG = 0.08  # ~6km


def nominatim_search(query):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "es",
    })
    req = urllib.request.Request(url, headers={"User-Agent": "world66-content/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def dist(lat1, lon1, lat2, lon2):
    return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5


def main():
    directory = "content/europe/spain/catalonia/barcelona"
    results = {"updated": [], "not_found": [], "too_far": [], "unchanged": []}

    files = sorted([
        f for f in os.listdir(directory)
        if f.endswith(".md") and f not in ("index.md",)
    ])

    # Only process curbside POIs added by this branch
    curbside_files = []
    for fname in files:
        path = os.path.join(directory, fname)
        post = frontmatter.load(path)
        if "curbside" in (post.get("tags") or []):
            curbside_files.append((fname, path, post))

    print(f"Processing {len(curbside_files)} curbside POIs...", flush=True)

    for fname, path, post in curbside_files:
        title = post.get("title", fname.replace("_", " ").replace(".md", ""))
        old_lat = float(post.get("latitude", 0))
        old_lon = float(post.get("longitude", 0))

        # Try title + city, then title + city + country
        result = None
        for query in [f"{title}, {CITY}", f"{title}, {CITY}, {COUNTRY}"]:
            try:
                hits = nominatim_search(query)
                if hits:
                    result = hits[0]
                    break
            except Exception as e:
                print(f"  ERROR querying {fname}: {e}", flush=True)
            time.sleep(1.1)

        if not result:
            print(f"  NOT FOUND: {fname} ({title})", flush=True)
            results["not_found"].append(fname)
            continue

        new_lat = round(float(result["lat"]), 5)
        new_lon = round(float(result["lon"]), 5)

        # Sanity check: must be within ~6km of Barcelona centre
        d = dist(new_lat, new_lon, CENTRE_LAT, CENTRE_LON)
        if d > MAX_DIST_DEG:
            print(f"  TOO FAR: {fname} ({title}) → {new_lat},{new_lon} (dist={d:.3f}°)", flush=True)
            results["too_far"].append((fname, new_lat, new_lon))
            continue

        if abs(new_lat - old_lat) < 0.0001 and abs(new_lon - old_lon) < 0.0001:
            results["unchanged"].append(fname)
            continue

        print(f"  UPDATE: {fname}: ({old_lat},{old_lon}) → ({new_lat},{new_lon})", flush=True)
        post["latitude"] = new_lat
        post["longitude"] = new_lon
        with open(path, "wb") as f:
            frontmatter.dump(post, f)
        results["updated"].append(fname)

    print(f"\nDone.")
    print(f"  Updated:   {len(results['updated'])}")
    print(f"  Unchanged: {len(results['unchanged'])}")
    print(f"  Not found: {len(results['not_found'])}")
    print(f"  Too far:   {len(results['too_far'])}")
    if results["not_found"]:
        print(f"\nNot found (review and possibly delete):")
        for f in results["not_found"]:
            print(f"  {f}")
    if results["too_far"]:
        print(f"\nToo far from Barcelona centre (review):")
        for f, lat, lon in results["too_far"]:
            print(f"  {f} → {lat},{lon}")


if __name__ == "__main__":
    main()
