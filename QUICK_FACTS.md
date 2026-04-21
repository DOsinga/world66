# Quick Facts

Quick facts are optional sidebar cards that give visitors a snapshot of a location. They appear as a 2x2 grid at the top of the sidebar, above the map.

## Frontmatter

Add a `quick_facts` field to the YAML frontmatter of major locations — countries and significant cities. Not every page needs quick facts; save them for places where visitors will actually benefit from the at-a-glance context.

```yaml
---
title: Netherlands
type: location
quick_facts:
  Population: "17.9 million"
  Capital: Amsterdam
  Below Sea Level: "26%"
  Bicycles: "23 million"
---
```

The keys are the labels (displayed above each value). Always use exactly 4 facts. Quote numeric values so YAML doesn't mangle them.

## What to pick

The four facts should be a mix of practical and surprising:

1. **One key demographic fact** — population, capital, or official language. The kind of thing a traveller looks up before a trip.
2. **One practical travel fact** — currency, time zone, driving side, voltage, or similar. Something useful to know on arrival.
3. **Two distinctive facts** — things that are genuinely telling about the place and ideally unexpected. These should make someone say "huh, I didn't know that" and give a feel for what makes the location different.

For the Netherlands, "Below Sea Level: 26%" and "Bicycles: 23 million" say more about the country than any generic statistic could. Every location has something like this — a ratio, a record, a quirk of geography or culture that captures its character in a single number.

Avoid generic or forgettable facts. "Area: 41,543 km²" tells you nothing interesting. "Below Sea Level: 26%" tells you everything.
