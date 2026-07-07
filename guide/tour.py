"""Walking-tour helpers: live route proxy to the Google Routes API.

The browser never holds a key — it asks the Django backend for a walking route
between two points, and the backend calls Google with server-side credentials.
Locally that credential is a gcloud application-default token; in production set
GOOGLE_APPLICATION_CREDENTIALS to a service account with the Routes API enabled.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
PROJECT = "audiotour-501517"

_token = {"value": None, "ts": 0.0}
_cache: dict[tuple, dict] = {}


def _access_token() -> str:
    # gcloud ADC tokens last ~1h; refresh every 50 min.
    if not _token["value"] or time.time() - _token["ts"] > 3000:
        _token["value"] = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, check=True).stdout.strip()
        _token["ts"] = time.time()
    return _token["value"]


def _decode_polyline(s: str) -> list[list[float]]:
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


def walking_route(fa: float, fo: float, ta: float, to: float) -> dict:
    """Return {coords, distance_m, duration_s} for a walk from (fa,fo) to (ta,to)."""
    key = (round(fa, 6), round(fo, 6), round(ta, 6), round(to, 6))
    if key in _cache:
        return _cache[key]
    body = json.dumps({
        "origin": {"location": {"latLng": {"latitude": fa, "longitude": fo}}},
        "destination": {"location": {"latLng": {"latitude": ta, "longitude": to}}},
        "travelMode": "WALK",
    }).encode()
    req = urllib.request.Request(ROUTES_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {_access_token()}",
        "x-goog-user-project": PROJECT,
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.distanceMeters,routes.duration",
    })
    routes = json.loads(urllib.request.urlopen(req, timeout=15).read()).get("routes", [])
    if not routes:
        # Fall back to a straight line so the UI still shows direction.
        return {"coords": [[fa, fo], [ta, to]], "distance_m": 0, "duration_s": 0}
    r = routes[0]
    out = {
        "coords": _decode_polyline(r["polyline"]["encodedPolyline"]),
        "distance_m": int(r.get("distanceMeters", 0)),
        "duration_s": int(str(r.get("duration", "0s")).rstrip("s") or 0),
    }
    _cache[key] = out
    return out
