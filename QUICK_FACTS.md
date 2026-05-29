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

## How to write them

Each fact must read as a complete, self-contained statement when you see the label and value together. The label is the subject, the value is the fact. Bad: `Largest Landlocked: in the world` (not a fact by itself). Good: `Largest Landlocked Country: Yes` or better, pick a different fact entirely like `Area: 9× the size of UK`.

Similarly, avoid values that require context to understand. Bad: `Issyk-Kul: 2nd largest alpine lake` (the label is just a name — meaningless to someone who hasn't been there). Good: `Alpine Lake Issyk-Kul: Never freezes` (now both label and value tell you something).

Avoid generic or forgettable facts. "Area: 41,543 km²" tells you nothing interesting. "Below Sea Level: 26%" tells you everything. "Official Language: Portuguese" is equally flat — every country has an official language. Pick something that makes the place *different*.
