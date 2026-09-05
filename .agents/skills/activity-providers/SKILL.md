---
name: activity-providers
description: research and add bookable activity providers (tour operators, lodges, boat trips, surf schools, restaurants) to world66 locations, with verified WhatsApp numbers. invoke when the user asks to add providers, activities, or WhatsApp booking contacts for a country or region
argument-hint: <country or region>
---

Add bookable activity providers to `content/` as `commercial: true` POIs, so a location page shows an "Arrange your trip" panel with a tappable WhatsApp button.

**The whole value of this content is that the contact details are correct.** A wrong number sends a stranger's booking message to somebody's private phone. Everything below exists because of a mistake that was actually made.

If no country is given, ask which one.

## 1. Survey what exists

```bash
find content/<continent>/<country> -maxdepth 1 -name "*.md" | sort
```

List the locations and their `loc_type`. Note gaps: a famous attraction with no page (Orinduik Falls), a misspelled slug (`mabarumba` for Mabaruma), a lodge region with nowhere to hang. Ask the user before creating or renaming pages.

## 2. Find candidate operators

Search per location and per activity, **in the local language as well as English** — Dutch for Suriname, Spanish for Peru, French for France. Local-language searches surface operators the English ones miss entirely.

Look for an official register where one exists — Guyana's Tourism Authority publishes a licensed-operator PDF, Peru has MINCETUR/DIRCETUR listings and an official licensed Inca Trail operator list. Being on it is worth recording; not being on it is worth saying.

## 3. Verify every provider on its own site

**HTTP 200 is not proof of life.** Real cases found this way:

- a well-known Penang surf school → now a Namecheap parking page
- Bushmasters, a Guyanese jungle operator → now an online-casino review site
- Oasis Cafe Georgetown → domain redirects to a Chinese sports-streaming site
- METS, Suriname's oldest operator → serves a bare directory listing

Load the site and read it. Take the name, address, phone, email and what they sell **from the operator's own pages**, never from TripAdvisor, Viator or a directory. If you cannot verify something, leave it out and say so.

## 4. Detect WhatsApp — never infer it

**Only publish a number the business advertises.** Nearly every mobile is on WhatsApp; that is not consent to receive bookings there. If a provider shows a WhatsApp button and two phone numbers without saying which is which, publish neither — record it for outreach.

Use the detector:

```bash
python3 tools/wa_detect.py --cc <country-code> https://site1 https://site2 ...
```

It renders each page in headless Chrome and reports `LINK` / `TEXT` / `mention-only` / `none` / `UNREACHABLE`. Roughly 1-3 minutes per site, so batch it and run it in the background.

Then **check the results by hand**, because it has been wrong in all of these ways:

| Result | What to do |
|---|---|
| `mention-only` | Dig. The number is often in a "Click to Chat" (`ht_ctc`) plugin config as `"number":"…"`, or another chat-widget config, rather than an href. Grep the rendered DOM. |
| `LINK` | **Check whose number it is.** On one airline's site the only `wa.me` link belonged to the web design agency credited in the footer. |
| `TEXT` | Read the surrounding sentence. Two sites returned a landline that merely sat near the word "WhatsApp"; the real number was the next one along. |
| `none` | Not proof. Cloudflare interstitials defeat headless Chrome — try WebFetch as a second channel. And the number may live on `/contact`, `/about`, `/nosotros`, `/aboutus` rather than the homepage. |
| `UNREACHABLE` | The page did not load. This is **not** evidence about WhatsApp. Retry. |

Cross-check any number you find against the phone numbers the site publishes — a match with the owner's published mobile is good confirmation.

**Watch for share widgets.** WordPress social-sharing plugins list "whatsapp" beside Telegram and XING; that is a share button, not a contact. Searching raw HTML for "whatsapp" near a number once matched social-icon CSS and produced a confident, wrong number.

## 5. Write the content

One POI per **company**, at the address it actually publishes, tagged `activities` plus an activity kind:

```yaml
---
title: Jenny Tours
type: poi
commercial: true
latitude: 5.8225
longitude: -55.1508
score: 6.9
snippet: Paramaribo operator covering most of the country, answering WhatsApp around the clock
tags: [activities, guided_tours]
address: Waterkant 5c, Paramaribo
phone: "+597 885 8495"
whatsapp: "+597 885 8495"
email: jennytourssuriname@gmail.com
url: suriname-tour.com
---
```

Quote phone numbers: unquoted `+597885...` is parsed by YAML as an integer and loses the `+`.

Activity kinds are in `Page.ACTIVITY_KINDS` (`guide/models.py`); each needs a colour in `world66.css` and an icon in `guide/templates/guide/widgets/activity_icon.html`. Add new ones there rather than letting them fall back to grey.

Every location with providers needs an `activities.md` section (`type: section`) — without it they appear nowhere.

### Listing one company in several places

Capital-city operators sell trips to the whole country. Do **not** create one POI per tour: Suriname ended up with 18 POIs for 7 companies, and the outreach file asked Jenny Tours six times whether it used WhatsApp.

Keep one POI, and let each location name it in its `activities.md`:

```yaml
providers:
  - path: southamerica/suriname/paramaribo/jenny_tours
    note: Three days on the Coppename, with the dawn Voltzberg climb
```

The note keeps the copy specific to that place. Kaieteur Falls lists eight operators this way with no duplication.

## 6. Coordinates and images

POIs need `latitude`/`longitude`. Geocode the **published address** with Nominatim directly:

```bash
curl -sS -A "world66-guide/1.0 (contact: <email>)" \
  "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=<urlencoded address>"
```

If an operator publishes no street address, either leave it out or place it at the city coordinates and **say so in the page text** — never invent a street address. Providers with no premises at all (a guide who meets you at a landing) are better omitted than given a fake pin.

New location pages need a hero image: query Wikimedia Commons, prefer landscape, and record `image_source`, `image_license` and `image_attribution`.

## 7. Outreach

Regenerate the outreach file after adding providers:

```bash
python3 tools/activity_outreach.py           # rebuild the CSV
python3 tools/activity_outreach.py --emails  # draft the mails (needs W66_WHATSAPP)
```

It writes one row per company with a confirmation code. Confirmation works by the provider messaging **us** on WhatsApp with their code — not by click-tracking, because corporate mail scanners fetch every URL in an inbound message and would record confirmations nobody made.

## 8. Check and report

```bash
python3 tools/linter.py       # commercial_poi + activity_providers checks
python3 manage.py check
python3 manage.py runserver 8066   # look at a location page
```

Report honestly:
- how many providers, how many with a confirmed WhatsApp number
- **the base rate** — it varies enormously by country. France ran about 6%; Suriname and Guyana over 30%. If a sweep of a WhatsApp-heavy country returns almost nothing, suspect the detector, not the country.
- what you could not verify, and who you left out and why
- any provider that advertises WhatsApp without publishing a number — those are the highest-value outreach targets

## Don't

- Don't infer a WhatsApp number from a phone number, however likely it is.
- Don't take contact details from an aggregator, or from an AI answer — phone numbers are what those invent most confidently, and a plausible number leaves no trace to check.
- Don't invent coordinates for an operator with no address.
- Don't create one POI per tour for a company that sells many.
- Don't report "no WhatsApp" for a site that failed to load.
