# Audio Wander — hyperlocal audio-tour prototype

A walking audio-guide POC: you stand at a point of interest, an audio guide narrates its
story, and at the end you pick a nearby next story — walking a self-guided tour through a
dense cluster of hyperlocal POIs.

It combines two things from world66:

- **Curbside POIs** (e.g. the `curbside/marseille` branch) — hundreds of hyperlocal spots,
  each with `latitude`/`longitude` and a short prose story in the body. That story body *is*
  the narration script.
- **The proximity logic from the `/next` app** (PR #2061) — nearest-POI selection within a
  walking band, which drives "where to next".

This prototype ships a self-contained slice: **10 POIs clustered within ~95 m around Fort
Saint-Jean, Marseille**.

## What it does

- **Play a story** at each stop (pre-generated MP3, Google Cloud Neural2 voice).
- **Pick the next stop** from the nearest un-heard stories — tap a choice or any map pin.
- **Live walking route** to the chosen spot, drawn on the map (Google Routes API, walking),
  computed **on demand** so you can pick *any* POI.
- **GPS walk mode**: your live location follows on the map; within **70 m** of an un-heard
  story you get a "🔔 story nearby" alert (banner + chime + vibration); within **25 m** it
  auto-plays. A **Simulate** toggle lets you test by tapping the map without being on-site.

## Run it

```bash
cd prototypes/audio-tour
python3 server.py            # serves the page + proxies routing
# open http://localhost:8077
```

`server.py` is stdlib-only. It serves the static page and exposes `GET /route?from_lat=..
&from_lng=..&to_lat=..&to_lng=..`, which it fulfils by calling the Google Routes API
server-side (so the browser never holds a key).

### Testing hooks

- `?at=<lat>,<lng>` — drop a simulated walker at exact coords (starts walk + simulate mode).

## Design choices

- **Audio is pre-generated**, not synthesized live — pay once per POI, serve static MP3s
  like images. Cheap (~1.2k chars/story; a full city fits the free tier) and works offline
  with no key in the browser. Regenerate with `generate_audio_google.py`.
- **Routes are computed on demand**, not precomputed — precomputing is N² and would lock you
  out of picking arbitrary spots. The backend proxy is the shape of the real `/route`
  endpoint we'd add to the Django app.

## Google Cloud setup

Uses project `audiotour-501517` with **Text-to-Speech** and **Routes** APIs enabled, via
gcloud application-default credentials:

```bash
gcloud auth application-default login
gcloud config set project audiotour-501517
gcloud services enable texttospeech.googleapis.com routes.googleapis.com
python3 generate_audio_google.py --content-root /path/to/world66   # (re)build audio
```

## Status / next

Prototype only. Known follow-ups:

- **iOS**: real GPS needs HTTPS + a permission prompt; audio & `navigator.vibrate` have
  autoplay quirks on iPhone.
- **Tiles**: uses CARTO/OSM tiles from a CDN — fine locally, but a strict CSP (a shared
  artifact, or the app) would block them; swap for self-hosted tiles or an SVG mini-map.
- **Integration**: port into the world66 Django app as a real `/tour` view + `/route`
  endpoint over the full curbside POI set, reusing PR #2061's geo index.
