"""What the concierge costs and how far people get with it.

Numbers only. A line in these logs holds counts, tool names and the guide page
a conversation started on, never what anybody typed, nor a name, address or IP.

One JSON line per event in one file per day (UTC): there is no database on this
site, and one short line appended to a file is safe across the server's workers.
"""

import datetime
import json
from collections import Counter, defaultdict
from pathlib import Path

from django.conf import settings

# Dollars per million tokens, from Anthropic's price list of October 2026.
# Reading the cache costs a tenth of the input price, writing it a quarter more.
PRICES = {
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
# A model not listed above is costed high, so the daily cap errs towards closing.
UNKNOWN_MODEL_PRICE = (5.0, 25.0)


def _directory():
    return Path(settings.CONCIERGE_DATA_DIR) / "usage"


def _today():
    return datetime.datetime.now(datetime.timezone.utc).date()


def cost(model, tokens):
    """Estimated dollars for one turn's token counts."""
    input_price, output_price = PRICES.get(model, UNKNOWN_MODEL_PRICE)
    dollars = (
        tokens.get("input_tokens", 0) * input_price
        + tokens.get("cache_read_input_tokens", 0) * input_price * 0.1
        + tokens.get("cache_creation_input_tokens", 0) * input_price * 1.25
        + tokens.get("output_tokens", 0) * output_price
    )
    return round(dollars / 1_000_000, 6)


def record(event, **fields):
    """Add an event to today's log. A failure here must never break the chat."""
    now = datetime.datetime.now(datetime.timezone.utc)
    line = json.dumps({"at": now.isoformat(timespec="seconds"), "event": event, **fields})
    try:
        directory = _directory()
        directory.mkdir(parents=True, exist_ok=True)
        with open(directory / f"{now.date().isoformat()}.jsonl", "a", encoding="utf-8") as log:
            log.write(line + "\n")
    except OSError:
        pass


def _events(day):
    try:
        lines = (_directory() / f"{day.isoformat()}.jsonl").read_text(encoding="utf-8")
    except OSError:
        return []
    events = []
    for line in lines.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


def spent_today():
    return sum(e.get("cost", 0) for e in _events(_today()) if e.get("event") == "turn")


def over_budget():
    return spent_today() >= settings.CONCIERGE_DAILY_BUDGET


def _blank(day):
    return {
        "day": day, "conversations": 0, "turns": 0, "errors": 0, "limited": 0, "capped": 0,
        "input_tokens": 0, "output_tokens": 0, "cost": 0.0,
        "drafts": 0, "enquiries": 0, "sent": 0,
    }


def _add(row, event, pages):
    kind = event.get("event")
    if kind == "turn":
        if event.get("status") != "ok":
            row["errors"] += 1
            return
        row["turns"] += 1
        row["input_tokens"] += (
            event.get("input_tokens", 0)
            + event.get("cache_read_input_tokens", 0)
            + event.get("cache_creation_input_tokens", 0)
        )
        row["output_tokens"] += event.get("output_tokens", 0)
        row["cost"] += event.get("cost", 0)
        row["drafts"] += 1 if event.get("draft") else 0
        if event.get("turn") == 1:
            row["conversations"] += 1
            if event.get("path"):
                pages[event["path"]] += 1
    elif kind in ("limited", "capped"):
        row[kind] += 1
    elif kind == "enquiry":
        row["enquiries"] += 1
    elif kind == "sent":
        row["sent"] += event.get("providers", 0)


def summary(days=30):
    """Per-day figures, newest first, with totals and the most used pages."""
    today = _today()
    rows, pages, totals = [], Counter(), _blank(None)
    for back in range(days):
        day = today - datetime.timedelta(days=back)
        row = _blank(day)
        for event in _events(day):
            _add(row, event, pages)
        if back == 0 or any(row[k] for k in row if k != "day"):
            rows.append(row)
        for key, value in row.items():
            if key != "day":
                totals[key] += value
    return {
        "rows": rows,
        "totals": totals,
        "cost_per_conversation": totals["cost"] / totals["conversations"]
        if totals["conversations"] else 0,
        "turns_per_conversation": totals["turns"] / totals["conversations"]
        if totals["conversations"] else 0,
        "top_pages": pages.most_common(15),
        "days": days,
        "spent_today": rows[0]["cost"] if rows else 0,
        "budget": settings.CONCIERGE_DAILY_BUDGET,
    }
