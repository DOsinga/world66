#!/usr/bin/env python3
"""
POC server: serves the static audio-tour page AND proxies Google Routes API on demand.

This mirrors how the real world66 app would work — the browser never holds a Maps
key; it asks this backend "walking route from A to B" and the server calls Google
with server-side credentials, so you can route to ANY POI you pick, computed live.

    GET /route?from_lat=..&from_lng=..&to_lat=..&to_lng=..
        -> {"coords": [[lat,lng],...], "distance_m": int, "duration_s": int}

Routes are cached in-memory by rounded coordinate pair. Run:  python3 server.py
"""
import json, subprocess, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PROJECT = "audiotour-501517"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

_token = {"value": None, "ts": 0}
_cache = {}


def token() -> str:
    # gcloud ADC tokens last ~1h; refresh every 50 min.
    if not _token["value"] or time.time() - _token["ts"] > 3000:
        _token["value"] = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, check=True).stdout.strip()
        _token["ts"] = time.time()
    return _token["value"]


def decode_polyline(s: str):
    coords, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        for is_lat in (True, False):
            shift = result = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                result |= (b & 0x1f) << shift; shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lat: lat += d
            else:      lng += d
        coords.append([lat * 1e-5, lng * 1e-5])
    return coords


def compute_route(fa, fo, ta, to):
    key = (round(fa, 6), round(fo, 6), round(ta, 6), round(to, 6))
    if key in _cache:
        return _cache[key]
    body = json.dumps({
        "origin": {"location": {"latLng": {"latitude": fa, "longitude": fo}}},
        "destination": {"location": {"latLng": {"latitude": ta, "longitude": to}}},
        "travelMode": "WALK",
    }).encode()
    req = urllib.request.Request(ROUTES_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token()}",
        "x-goog-user-project": PROJECT,
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.distanceMeters,routes.duration",
    })
    routes = json.loads(urllib.request.urlopen(req, timeout=15).read()).get("routes", [])
    if not routes:
        return {"coords": [[fa, fo], [ta, to]], "distance_m": 0, "duration_s": 0}
    r = routes[0]
    out = {
        "coords": decode_polyline(r["polyline"]["encodedPolyline"]),
        "distance_m": int(r.get("distanceMeters", 0)),
        "duration_s": int(str(r.get("duration", "0s")).rstrip("s") or 0),
    }
    _cache[key] = out
    return out


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path == "/route":
            self.handle_route()
        else:
            super().do_GET()

    def handle_route(self):
        q = parse_qs(urlparse(self.path).query)
        try:
            fa, fo = float(q["from_lat"][0]), float(q["from_lng"][0])
            ta, to = float(q["to_lat"][0]), float(q["to_lng"][0])
            data = compute_route(fa, fo, ta, to)
            payload = json.dumps(data).encode()
        except urllib.error.HTTPError as e:
            self.send_error(502, f"Routes API: {e.read().decode()[:200]}"); return
        except Exception as e:
            self.send_error(400, str(e)); return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("audio-tour POC on http://localhost:8077  (Ctrl-C to stop)")
    ThreadingHTTPServer(("", 8077), Handler).serve_forever()
