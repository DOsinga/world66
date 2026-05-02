# TimeSpace Events

Events are plain markdown files. One file = one event.

## File naming

```
YYYY-MM-DD-slug-of-event.md
```

## Frontmatter fields

| Field        | Required | Description |
|---|---|---|
| `title`      | yes | Event name |
| `poi`        | yes | World66 content path for the venue (e.g. `europe/germany/hamburg/elbphilharmonie`) |
| `date`       | yes | ISO date: `2026-06-15` |
| `time_start` | no  | 24h time: `"19:30"` |
| `time_end`   | no  | 24h time: `"22:00"` |
| `category`   | no  | `concert` · `festival` · `market` · `museum` · `exhibition` · `food` · `sport` · `other` |
| `url`        | no  | Tickets or info link |

## Example

```markdown
---
title: Summer Jazz at the Elbe
poi: europe/germany/hamburg/hamburg_harbour
date: 2026-07-12
time_start: "20:00"
time_end: "23:00"
category: concert
url: https://example.com/tickets
---
Live jazz on the water's edge as the sun sets over the Elbe. Free entry, drinks available.
```

## How to add an event

1. Fork this repo
2. Add a `.md` file in `spacetime_app/events/`
3. Open a pull request
