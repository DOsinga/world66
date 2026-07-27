---
name: street-poster
description: draw a 1950s-style travel poster of a shopping street as a layered SVG, with copy and animation beats. invoke when the user asks for a street poster, a city highlight reel, or poster art for a location
argument-hint: <street and city, e.g. "Susannenstrasse Hamburg">
---

Produce three files for one street: a 1920×1080 SVG poster drawn in mid-century
screenprint style, a `poster.json` of copy and animation beats, and a rendered
PNG. Ten of these make a city compilation reel.

If no street is given, ask which one.

**The photos are reference, not material.** You look at them to learn what the
street actually contains — the shape of the roofs, which awnings, what is out on
the pavement — and then you draw. No pixel of a photo ends up in the SVG, which
is why licence never comes up. Never commit the reference images.

Read `reference/poster-style.md` before drawing. It has the ink rules, the
composition geometry that works, and the layer contract.

## Steps

### 1. Research the street

WebSearch for the street plus the city, in English and in the local language.
You need two things:

- **Named shops** — five that are actually on this street, with what they sell.
  Search the local city-guide and tourism sites; they list shops by street.
- **Character** — what kind of street it is, who shops there, what it looks like.

Five real named shops is the bar. A poster of generic shopfronts is worthless;
the shop names are the reason a traveller reads it.

### 2. Fetch reference photos

WebSearch for photos of the street, then pull them down:

```bash
# image URLs you found directly
python3 tools/street_photos.py add --out /tmp/refs URL [URL ...]

# or let the tool pull every image off a page you found
python3 tools/street_photos.py scrape --out /tmp/refs PAGE_URL [PAGE_URL ...]

# fallback when you want direct image URLs without reading pages
python3 tools/street_photos.py search "<street> <city>" --out /tmp/refs
```

Use the session scratchpad for `--out`, never a path inside the repo.

Aim for 30–50 raw candidates. Vary the queries: the street name alone, the
street with the neighbourhood, the neighbourhood plus "Altbau"/"shopfront"/
"street", and the names of individual shops.

### 3. Curate, then extract the palette

**Curate before you extract, always.** Raw search results for a street are full
of things that are technically on it but visually irrelevant — memorial plaques,
protest photography, stock skylines. A palette taken from an uncurated set
describes those, not the street.

```bash
python3 tools/street_photos.py sheet --out /tmp/refs --cols 7   # one indexed image
```

Read the contact sheet. Keep only frames showing the street itself: facades,
shopfronts, awnings, pavement, signage, trees. Then prune and extract:

```bash
python3 tools/street_photos.py keep "10,12,15,21,27,28" --out /tmp/refs
python3 tools/street_photos.py palette --out /tmp/refs --colors 8
python3 tools/street_photos.py sheet --out /tmp/refs --cols 4   # review what survived
```

Read the curated sheet properly and write down the motifs before drawing —
roof shape, window rhythm, awning colours and profile, what sits on the
pavement, what the walls are covered in, what is visible above the roofline.
These specifics are the difference between this street and any street.

### 4. Turn the photo palette into ink

The extracted palette is a **hue guide, not the ink**. Real street photos come
back muted grey-brown; a screenprint of them would be mud. Take the dominant
hues and push each to full saturation, then commit to six inks and no more.
`reference/poster-style.md` shows how, with the Susannenstraße set worked
through as an example.

### 5. Draw the poster

Write the SVG by hand into
`prototypes/street-posters/<street-slug>/poster.svg`, following the layer
contract and composition recipe in `reference/poster-style.md`.

Start from `prototypes/street-posters/susannenstrasse/poster.svg` — the
geometry there is proven and re-deriving it wastes effort. Change the shops, the
inks, the motifs and the skyline; keep the bones.

### 6. Render and look at it

```bash
python3 tools/render_poster.py prototypes/street-posters/<slug>/poster.svg
```

Then **read the PNG**. The lint only checks structure — layer ids, the
viewBox, banned elements, ink count. It cannot tell you the poster is ugly or
that the shop names are missing. Every problem worth fixing in the Susannenstraße
build was found by looking, not by linting:

- text colliding with figures and props
- shop fascias left blank
- a claim in the copy that was never verified

Iterate until it looks like a poster you would print.

### 7. Write poster.json

Copy and animation beats, alongside the SVG. Use
`prototypes/street-posters/susannenstrasse/poster.json` as the schema. It
carries the headline, the deck, per-shop blurbs keyed to the SVG group ids,
the palette, and the beat list the compilation reads.

Write the prose in World66 voice — read STYLE.md. Specific, unhurried, no
brochure adjectives. Do not invent a street length, a founding date, or an
opening time you have not seen.

### 8. Report

Show the user the PNG and list the shops you put on it. Do not commit the
reference photos; only `poster.svg`, `poster.json` and `poster.png` belong in
the repo.

## Rules

- Six inks, flat. No gradients, no filters, no embedded raster, no drop shadows.
  The lint enforces this; do not work around it.
- Every shop is its own `<g id="shop-N" data-shop="...">`. The animation
  addresses them individually.
- Five named real shops, spelled as the street spells them.
- The reference directory lives in the scratchpad and stays there.
- Do not fabricate facts to fill the copy. A shorter true deck beats a longer
  invented one.
