# Poster style

How to draw the thing. Read before writing any SVG.

## The look

Mid-century travel poster — the screenprinted railway and airline posters of the
1940s–60s. What that means concretely:

- **Flat colour only.** A screen lays down one opaque ink at a time. No
  gradients, no soft shadows, no blur, no bevels.
- **Few inks.** Six, because six screens was already an expensive poster.
- **Shapes, not outlines.** Build from filled rectangles, triangles, circles and
  simple paths. Use a stroke for window frames and ironwork, not for everything.
- **Confident geometry.** Windows on a grid, awnings on a rhythm, a horizon you
  can point at. Wonkiness reads as a mistake, not as charm.
- **Heavy condensed caps** for the street name, letterspaced small caps for the
  city line. The type is part of the composition, not a label stuck on top.
- **One warm light source.** A sun disc, a few lit windows. That is the whole
  lighting model.

Overprint tints are allowed: the same ink at `opacity="0.2"` gives you a
seventh and eighth value without a seventh screen. Use them for facade
variation, paving, and distance — that is how the reference poster gets five
differently-coloured houses out of six inks.

## Inks

Six, named in a comment at the top of the SVG. Derive them like this:

1. Run `street_photos.py palette` on the **curated** references.
2. Read off the dominant hues, ignoring how drab they are. A typical European
   street returns: a cool sky grey, a warm stucco grey, a near-black, a cream,
   a brick brown, and a grey-green.
3. Push each to the saturation a printer would use, and assign a role.

Worked through for Susannenstraße:

| Extracted   | →   | Ink            | Role                                    |
|-------------|-----|----------------|-----------------------------------------|
| `#99B0B7`   | →   | TEAL `#4E8A93` | sky, window glass                       |
| `#151415`   | →   | INK `#1E2A2E`  | roofs, outlines, type, silhouettes      |
| `#D7D4D1`   | →   | PAPER `#F2E6CD`| facades, awning stripes, reversed type  |
| `#54413D`   | →   | BRICK `#C25A3C`| awnings, crates, accents                |
| (signage)   | →   | OCHRE `#E0A32E`| sun, lit windows, the one hot accent    |
| `#667A7C`   | →   | LEAF `#4F7A52` | trees, green awnings, stems             |

Keep INK and PAPER roughly where they are — the near-black and the cream are
the poster's structure. Push the three or four hues hard. Pick the accent
(OCHRE above) from the street's own signage if it has a signature colour.

## Layer contract

Five groups, back to front. The lint requires all five, and the animation
addresses them by id.

| Layer         | Holds                                                      | Parallax |
|---------------|------------------------------------------------------------|----------|
| `layer-sky`   | sky field, sun, flat clouds                                  | 0.05     |
| `layer-far`   | distant landmark, roofs behind the roofline                  | 0.20     |
| `layer-mid`   | the building row: facades, roofs, windows, balconies         | 0.55     |
| `layer-near`  | shopfronts, awnings, pavement, trees, props, figures         | 1.00     |
| `layer-type`  | street name, city line, deck                                 | 0.00     |

Inside `layer-near`, each shop is `<g id="shop-N" data-shop="Name">` containing
its own glass, fascia, sign text, awning and pavement goods — so a beat can
push in on one shop and dim the rest.

## Composition

A **frontal row of shopfronts**, not a receding perspective. The brief is what
the street offers; a flat elevation shows five shops at once and reads at any
size. Perspective hides four of them behind the first.

Proven geometry at 1920×1080:

```
    0 ┌──────────────────────────────────────────┐
      │  sky — title sits here, disc opposite    │
  250 ├──────────────────────────────────────────┤  rooflines, chimneys
  300 ├──────────────────────────────────────────┤  cornice
      │  facades: 3 window rows at 330/450/570   │
      │  balconies on the middle row             │
  690 ├──────────────────────────────────────────┤  fascia band (SHOP NAME)
  750 ├──────────────────────────────────────────┤  awning, scalloped at 806
      │  shop glass + goods                      │
  892 ├──────────────────────────────────────────┤  kerb
      │  pavement — deck copy left, props right  │
 1080 └──────────────────────────────────────────┘
```

Five bays of uneven width across the frame (380/400/360/400/380 works) with an
8px ink party wall between them. Uneven widths stop it reading as wallpaper.

Balance: heavy type in one top corner, sun disc in the other. Trees break the
roofline and overlap two bays, which is what stops the row feeling like a
stage flat.

### Non-negotiable details

- **Put the shop name on every fascia.** This is the single highest-value
  element on the poster and the easiest to forget. Reversed out of a dark
  fascia, or dark on the one coloured fascia.
- **Put goods on the pavement.** Crates, rails, buckets, hanging bags. An empty
  pavement reads as a closed street.
- **Give each shop a different frontage.** Awning vs no awning, stripe colour,
  what is in the window. Five identical bays with different words on them is
  not a street.
- **One local landmark** on the far layer if the street has a view of one.
- **Vary the facades** with tint overlays, and light three or four windows.

### Checks the lint cannot do

Read the rendered PNG every time. Specifically look for:

- type colliding with props or figures — the pavement fills up fast
- fascia text too long for its bay
- a tree trunk landing on a shop sign
- claims in the copy you did not verify

## Type

Condensed grotesque, e.g.
`font-family="'Arial Narrow','Helvetica Neue',Helvetica,sans-serif"` with
`font-weight="bold"`.

- Street name ~104px, `letter-spacing="1"`, in PAPER over the sky.
- A 5px rule in the accent ink under it.
- City · neighbourhood ~29px, `letter-spacing="11"`, in the accent ink.
- Fascia signs ~31px, `letter-spacing="3"`, centred in the bay. Drop to 27px
  for a long name.
- Deck ~27px over the pavement, two lines, in INK.

Text stays as `<text>` so the copy can be edited and localised. The fonts are
macOS-standard; if a poster must render on an unknown machine, convert the type
to paths in an export, not in the source.
