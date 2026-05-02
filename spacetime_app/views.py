import json

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404

from .models import load_all_events, load_event, nearby_events, nearby_venue_pois, haversine_km, _events_dir


def map_view(request):
    """
    Main map view. On first load the browser requests location, then JS calls
    /timespace/api/nearby/ with lat/lng to get events + venues as GeoJSON.
    """
    return render(request, "spacetime/map.html")


def event_list(request):
    events = load_all_events(include_past=False)
    return render(request, "spacetime/event_list.html", {"events": events})


def event_detail(request, slug):
    path = _events_dir() / f"{slug}.md"
    if not path.exists():
        raise Http404
    from .models import load_event
    event = load_event(path)
    if event is None:
        raise Http404
    return render(request, "spacetime/event_detail.html", {"event": event})


def api_nearby(request):
    """
    JSON API: ?lat=53.55&lng=9.99&radius=25
    Returns events + venue POIs within radius as two GeoJSON feature collections.
    """
    try:
        lat = float(request.GET["lat"])
        lng = float(request.GET["lng"])
        radius_km = float(request.GET.get("radius", 25))
    except (KeyError, ValueError):
        return JsonResponse({"error": "lat and lng required"}, status=400)

    events = load_all_events(include_past=False)
    close_events = nearby_events(events, lat, lng, radius_km)

    # Event features
    event_features = []
    for e in close_events:
        v = e.venue
        event_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [v.lng, v.lat]},
            "properties": {
                "kind": "event",
                "slug": e.slug,
                "title": e.title,
                "venue": v.title,
                "date": e.date.isoformat(),
                "time_start": e.time_start,
                "category": e.category,
                "url": e.url,
                "detail_url": f"/timespace/events/{e.slug}/",
                "distance_km": round(haversine_km(lat, lng, v.lat, v.lng), 1),
            },
        })

    # Venue POI features (only if no events at that location)
    event_poi_paths = {e.poi_path for e in close_events}
    venues = nearby_venue_pois(lat, lng, radius_km)
    venue_features = []
    for v in venues:
        if v.path in event_poi_paths:
            continue  # already shown as event
        venue_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [v.lng, v.lat]},
            "properties": {
                "kind": "venue",
                "title": v.title,
                "snippet": v.snippet,
                "tags": v.tags,
                "w66_url": f"/{v.path}",
                "distance_km": round(haversine_km(lat, lng, v.lat, v.lng), 1),
            },
        })

    return JsonResponse({
        "events": {"type": "FeatureCollection", "features": event_features},
        "venues": {"type": "FeatureCollection", "features": venue_features},
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
    })
