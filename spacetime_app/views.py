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
    from datetime import date, timedelta
    from .models import city_display
    all_events = load_all_events(include_past=False)

    # Date filter — default 7 days
    try:
        days = int(request.GET.get("days", 7))
    except ValueError:
        days = 7
    if days > 0:
        cutoff = date.today() + timedelta(days=days)
        all_events = [e for e in all_events if e.date <= cutoff]

    # Build city list from venue city slugs
    city_slugs = sorted({e.venue.city_slug for e in all_events if e.venue and e.venue.city_slug})
    cities = [{"slug": s, "label": city_display(s)} for s in city_slugs]

    active_city = request.GET.get("city", "")
    active_venue = request.GET.get("venue", "")

    events = all_events
    venues_in_city = []

    if active_city:
        events = [e for e in events if e.venue and e.venue.city_slug == active_city]
        seen = {}
        for e in events:
            if e.venue and e.venue.title not in seen:
                seen[e.venue.title] = e.venue
        venues_in_city = sorted(seen.values(), key=lambda v: v.title)

    if active_venue:
        events = [e for e in events if e.venue and e.venue.title == active_venue]

    date_options = [
        {"days": 7,  "label": "Next 7 days"},
        {"days": 14, "label": "Next 2 weeks"},
        {"days": 30, "label": "Next month"},
        {"days": 0,  "label": "All upcoming"},
    ]

    return render(request, "spacetime/event_list.html", {
        "events": events,
        "cities": cities,
        "active_city": active_city,
        "active_city_label": city_display(active_city) if active_city else "",
        "venues_in_city": venues_in_city,
        "active_venue": active_venue,
        "active_days": days,
        "date_options": date_options,
    })


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
