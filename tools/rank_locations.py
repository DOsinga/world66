#!/usr/bin/env python3
"""
Rank World66 locations as travel destinations using the Claude API.

Maintains a TrueSkill-style Gaussian rating (mu, sigma) per location in a
JSON state file. Each round selects 12 locations via uncertainty sampling
(weighted by sigma^2), asks Claude to rank them from best to worst as
travel destinations, and updates ratings from the resulting ordering.

Usage:
    # Discover all locations and initialise the state file
    python tools/rank_locations.py discover

    # Run 50 ranking rounds (12 locations per round = 1 API call per round)
    python tools/rank_locations.py run --rounds 50

    # Show the current top / bottom locations
    python tools/rank_locations.py top 30
    python tools/rank_locations.py bottom 30

    # Show progress stats
    python tools/rank_locations.py stats

State is stored in tools/location_ratings.json and runs are resumable.
"""

import argparse
import datetime as dt
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import frontmatter
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = PROJECT_DIR / 'content'
STATE_FILE = PROJECT_DIR / 'location_ratings.json'
LOG_DIR = PROJECT_DIR / 'log_scoring'

# TrueSkill-inspired constants
INITIAL_MU = 25.0
INITIAL_SIGMA = 25.0 / 3.0
BETA = 25.0 / 6.0               # skill spread that produces ~76% win probability
DYNAMICS = 25.0 / 300.0         # small additive variance per update to avoid freezing

BATCH_SIZE = 24
DEFAULT_MODEL = 'claude-sonnet-4-6'

# How much of each location's page body to include in the prompt.
# ~900 chars ≈ 200-250 tokens → ~3k tokens of context per 12-item batch.
INTRO_CHARS = 900


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class Rating:
    path: str
    title: str
    mu: float = INITIAL_MU
    sigma: float = INITIAL_SIGMA
    comparisons: int = 0

    def conservative(self) -> float:
        """Lower-bound score (mu - 3*sigma), used for sorting 'top'."""
        return self.mu - 3 * self.sigma


@dataclass
class State:
    model: str = DEFAULT_MODEL
    rounds: int = 0
    api_calls: int = 0
    ratings: dict[str, Rating] = field(default_factory=dict)

    @classmethod
    def load(cls) -> 'State':
        if not STATE_FILE.exists():
            return cls()
        data = json.loads(STATE_FILE.read_text())
        state = cls(
            model=data.get('model', DEFAULT_MODEL),
            rounds=data.get('rounds', 0),
            api_calls=data.get('api_calls', 0),
        )
        for path, r in data.get('ratings', {}).items():
            state.ratings[path] = Rating(
                path=path,
                title=r['title'],
                mu=r['mu'],
                sigma=r['sigma'],
                comparisons=r.get('comparisons', 0),
            )
        return state

    def save(self) -> None:
        data = {
            'model': self.model,
            'rounds': self.rounds,
            'api_calls': self.api_calls,
            'ratings': {
                path: {
                    'title': r.title,
                    'mu': round(r.mu, 4),
                    'sigma': round(r.sigma, 4),
                    'comparisons': r.comparisons,
                }
                for path, r in self.ratings.items()
            },
        }
        tmp = STATE_FILE.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
        tmp.replace(STATE_FILE)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_locations() -> list[tuple[str, str]]:
    """Scan content/ for type: location pages.

    Returns a list of (content_path, title) tuples. content_path mirrors the
    URL-style path used elsewhere (e.g. 'europe/france/paris').
    """
    found = []
    for md_file in sorted(CONTENT_DIR.rglob('*.md')):
        try:
            meta = frontmatter.load(md_file).metadata
        except Exception:
            continue
        if meta.get('type') != 'location':
            continue
        rel = md_file.relative_to(CONTENT_DIR)
        if md_file.parent.name == md_file.stem:
            content_path = str(rel.parent)
        else:
            content_path = str(rel.with_suffix(''))
        title = meta.get('title') or content_path.rsplit('/', 1)[-1].replace('_', ' ').title()
        found.append((content_path, title))
    return found


def cmd_discover(args) -> None:
    state = State.load()
    existing = set(state.ratings.keys())

    locations = discover_locations()
    print(f'Found {len(locations)} location pages.')

    if args.sample is not None:
        if args.sample < BATCH_SIZE:
            print(f'--sample must be at least {BATCH_SIZE}', file=sys.stderr)
            sys.exit(2)
        # Refuse to resample if we already have ratings with real data,
        # unless --force: that would discard learned ratings.
        has_work = any(r.comparisons > 0 for r in state.ratings.values())
        if has_work and not args.force:
            print('State already contains rated locations '
                  f'({sum(1 for r in state.ratings.values() if r.comparisons > 0)} '
                  'with comparisons). Refusing to resample. '
                  'Use --force to discard and resample.', file=sys.stderr)
            sys.exit(2)
        rng = random.Random(args.seed)
        rng.shuffle(locations)
        locations = locations[:args.sample]
        print(f'Sampled {len(locations)} locations (seed={args.seed}).')

    # --sample --force means "throw away everything and start over with this
    # sample". Zero the round counters and rebuild ratings from scratch so
    # every location starts at the initial prior.
    if args.sample is not None and args.force:
        state.ratings = {}
        state.rounds = 0
        state.api_calls = 0

    added = 0
    updated = 0
    seen = set()
    for path, title in locations:
        seen.add(path)
        if path in state.ratings:
            if state.ratings[path].title != title:
                state.ratings[path].title = title
                updated += 1
        else:
            state.ratings[path] = Rating(path=path, title=title)
            added += 1

    removed = existing - seen
    for path in removed:
        del state.ratings[path]

    state.save()
    print(f'  added:   {added}')
    print(f'  updated: {updated}')
    print(f'  removed: {len(removed)}')
    print(f'  total:   {len(state.ratings)}')
    if args.sample is not None and args.force:
        print(f'  reset:   rounds and ratings zeroed')


# ---------------------------------------------------------------------------
# TrueSkill-lite update
# ---------------------------------------------------------------------------

_SQRT_2 = math.sqrt(2.0)
_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT_2))


def _v(t: float) -> float:
    """Mean of a truncated standard normal above t."""
    denom = _cdf(t)
    if denom < 1e-12:
        # Asymptotic expansion for the deep tail
        return -t
    return _pdf(t) / denom


def _w(t: float) -> float:
    """Variance shrinkage factor for the truncated normal above t."""
    vt = _v(t)
    return vt * (vt + t)


def update_pair(winner: Rating, loser: Rating) -> None:
    """TrueSkill update for a single win/loss event."""
    # Inject a small amount of dynamics variance so sigma never fully collapses.
    sw2 = winner.sigma * winner.sigma + DYNAMICS * DYNAMICS
    sl2 = loser.sigma * loser.sigma + DYNAMICS * DYNAMICS

    c2 = 2.0 * BETA * BETA + sw2 + sl2
    c = math.sqrt(c2)
    t = (winner.mu - loser.mu) / c

    v = _v(t)
    w = _w(t)

    winner.mu += (sw2 / c) * v
    loser.mu -= (sl2 / c) * v
    winner.sigma = math.sqrt(max(1e-6, sw2 * (1.0 - sw2 / c2 * w)))
    loser.sigma = math.sqrt(max(1e-6, sl2 * (1.0 - sl2 / c2 * w)))


def write_scoring_log(
    log_dir: Path,
    round_num: int,
    model: str,
    batch: list[Rating],
    ranking: list[int],
    prior: dict[str, tuple[float, float, int]],
) -> Path:
    """Write a JSON log of a single ranking round.

    `prior` is a snapshot of (mu, sigma, comparisons) for each batch member
    BEFORE the update, so the log shows what the model saw rather than the
    already-updated values.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f'round_{round_num:04d}.json'
    ts = dt.datetime.now().isoformat(timespec='seconds')

    ordered = []
    for rank_idx, batch_idx in enumerate(ranking, 1):
        r = batch[batch_idx]
        mu0, sigma0, n0 = prior[r.path]
        ordered.append({
            'rank': rank_idx,
            'title': r.title,
            'path': r.path,
            'prior_mu': round(mu0, 4),
            'prior_sigma': round(sigma0, 4),
            'prior_n': n0,
        })

    data = {
        'round': round_num,
        'timestamp': ts,
        'model': model,
        'batch_size': len(batch),
        'order': ordered,
    }
    path.write_text(json.dumps(data, indent=2))
    return path


def apply_ranking(ranked: list[Rating]) -> None:
    """Apply updates for a full ordered ranking (best first).

    Uses adjacent-pair updates, which is the standard TrueSkill treatment of
    a multi-competitor result.
    """
    for i in range(len(ranked) - 1):
        update_pair(ranked[i], ranked[i + 1])
    for r in ranked:
        r.comparisons += 1


# ---------------------------------------------------------------------------
# Active selection
# ---------------------------------------------------------------------------

def _country_key(path: str) -> str:
    """Extract continent/country from a content path."""
    parts = path.split('/')
    return '/'.join(parts[:2]) if len(parts) >= 2 else path


def _weighted_sample(candidates: list[Rating], size: int, rng) -> list[Rating]:
    """Efraimidis-Spirakis weighted reservoir sampling, weight ∝ sigma²."""
    if len(candidates) <= size:
        return candidates
    keys = []
    for r in candidates:
        w = r.sigma * r.sigma
        if w <= 0:
            w = 1e-9
        u = rng.random()
        key = math.log(u) / w if u > 0 else -math.inf
        keys.append((key, r))
    keys.sort(key=lambda kv: kv[0], reverse=True)
    return [r for _, r in keys[:size]]


def select_batch(state: State, size: int = BATCH_SIZE, rng: random.Random | None = None) -> list[Rating]:
    """Pick `size` locations to compare next.

    Strategy: weighted sampling without replacement, weight proportional to
    sigma^2. This is uncertainty sampling — it spends API budget reducing
    the posterior variance where it is largest. Brand new locations (still at
    INITIAL_SIGMA) dominate early rounds; as the field converges, the
    algorithm drifts toward locations whose ratings are still uncertain.
    """
    rng = rng or random
    return _weighted_sample(list(state.ratings.values()), size, rng)


def select_batch_by_country(state: State, size: int = BATCH_SIZE, rng: random.Random | None = None) -> list[Rating]:
    """Pick a country weighted by uncertainty, then sample locations from it.

    1. Group locations by country (continent/country prefix).
    2. Pick a country with weight = sum of sigma² across its locations.
    3. Sample up to `size` locations from that country by sigma².

    Countries with fewer than 2 locations are skipped (can't rank 1 item).
    """
    rng = rng or random

    # Group by country
    by_country: dict[str, list[Rating]] = {}
    for r in state.ratings.values():
        key = _country_key(r.path)
        by_country.setdefault(key, []).append(r)

    # Filter out countries with < 2 locations
    eligible = {k: v for k, v in by_country.items() if len(v) >= 2}
    if not eligible:
        return select_batch(state, size, rng)

    # Pick a country weighted by total sigma²
    countries = list(eligible.keys())
    weights = [sum(r.sigma ** 2 for r in eligible[c]) for c in countries]
    total = sum(weights)
    pick = rng.random() * total
    cumulative = 0.0
    chosen = countries[0]
    for c, w in zip(countries, weights):
        cumulative += w
        if cumulative >= pick:
            chosen = c
            break

    return _weighted_sample(eligible[chosen], size, rng)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

RANKING_SCHEMA = {
    'type': 'object',
    'properties': {
        'order': {
            'type': 'array',
            'description': (
                'The candidate IDs in order from best travel destination '
                '(first) to worst (last). Every ID supplied in the prompt '
                'must appear exactly once.'
            ),
            'items': {'type': 'integer'},
        },
    },
    'required': ['order'],
    'additionalProperties': False,
}


_parent_title_cache: dict[str, str] = {}


def _parent_context(path: str) -> str:
    """Return the parent page's title from frontmatter.

    For 'europe/spain/astorga' the parent is 'europe/spain' → 'Spain'.
    For 'northamerica/unitedstates/california/sanluisobispo' → 'California'.
    """
    if '/' not in path:
        return ''
    parent_path = path.rsplit('/', 1)[0]

    if parent_path in _parent_title_cache:
        return _parent_title_cache[parent_path]

    md_path = _resolve_md_path(parent_path)
    if md_path is not None:
        try:
            title = frontmatter.load(md_path).metadata.get('title', '')
            _parent_title_cache[parent_path] = title
            return title
        except Exception:
            pass

    # Fallback: titlecase the last slug
    fallback = parent_path.rsplit('/', 1)[-1].replace('_', ' ').title()
    _parent_title_cache[parent_path] = fallback
    return fallback


def build_prompt(batch: list[Rating]) -> str:
    """Match the minimal free-text prompt that produced the consensus
    ranking in the debug run, aside from 'rank' -> 'order' phrasing.
    Each candidate is shown with its country for disambiguation."""
    lines = [
        f'Order these {len(batch)} travel destinations from best to '
        'worst as places to visit for a tourist:',
        '',
    ]
    for i, r in enumerate(batch):
        parts = r.path.split('/')
        depth = len(parts)  # 1=continent, 2=country, 3+=sub-country
        parent = _parent_context(r.path)
        if depth <= 2 or not parent or parent.lower() == r.title.lower():
            # Continent or country: no extra context needed
            lines.append(f'- [{i}] {r.title}')
        else:
            # Sub-country location: show parent, plus country if different
            country_path = '/'.join(parts[:2])
            country = _parent_title_cache.get(country_path)
            if country is None:
                md = _resolve_md_path(country_path)
                if md:
                    try:
                        country = frontmatter.load(md).metadata.get('title', '')
                    except Exception:
                        country = ''
                else:
                    country = ''
                _parent_title_cache[country_path] = country
            if country and country.lower() != parent.lower():
                lines.append(f'- [{i}] {r.title}, {parent} ({country})')
            else:
                lines.append(f'- [{i}] {r.title}, {parent}')
    return '\n'.join(lines)


def rank_with_claude(client, model: str, batch: list[Rating]) -> list[int] | None:
    """Call Claude and return the ordering as a list of indices into `batch`.

    Uses the API's structured outputs feature (output_config.format) to
    guarantee the response is JSON matching RANKING_SCHEMA. Returns None
    if the response cannot be parsed into a valid permutation.
    """
    prompt = build_prompt(batch)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        output_config={
            'format': {
                'type': 'json_schema',
                'schema': RANKING_SCHEMA,
            },
        },
        messages=[{'role': 'user', 'content': prompt}],
    )

    text = next((b.text for b in response.content if getattr(b, 'type', None) == 'text'), None)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    order = data.get('order')
    if not isinstance(order, list):
        return None
    if sorted(order) != list(range(len(batch))):
        return None
    return order


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_run(args) -> None:
    import anthropic  # imported lazily so `discover`/`top` work without the SDK

    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)

    model = args.model or state.model
    state.model = model
    client = anthropic.Anthropic()
    rng = random.Random(args.seed) if args.seed is not None else random
    log_dir = Path(args.log_dir) if args.log_dir else LOG_DIR

    target_rounds = args.rounds
    print(f'Running {target_rounds} rounds against {model} '
          f'({len(state.ratings)} locations, {state.rounds} rounds so far).')
    print(f'Logging each round to {log_dir}/')

    try:
        for i in range(target_rounds):
            if args.by_country is True:
                batch = select_batch_by_country(state, BATCH_SIZE, rng)
            elif args.by_country:
                # Specific prefix: filter to that prefix and sample by uncertainty
                pool = [r for r in state.ratings.values()
                        if r.path.startswith(args.by_country.strip('/') + '/')
                        or r.path == args.by_country.strip('/')]
                batch = _weighted_sample(pool, BATCH_SIZE, rng)
            else:
                batch = select_batch(state, BATCH_SIZE, rng)
            # Snapshot priors BEFORE the update so logs show what the model saw.
            prior = {r.path: (r.mu, r.sigma, r.comparisons) for r in batch}

            try:
                ranking = rank_with_claude(client, model, batch)
            except anthropic.APIError as e:
                print(f'  round {state.rounds + 1}: API error ({e}); backing off 10s', file=sys.stderr)
                time.sleep(10)
                continue

            state.api_calls += 1
            if ranking is None:
                print(f'  round {state.rounds + 1}: invalid ranking response, skipped',
                      file=sys.stderr)
                continue

            ranked = [batch[idx] for idx in ranking]
            apply_ranking(ranked)
            state.rounds += 1
            write_scoring_log(log_dir, state.rounds, model, batch, ranking, prior)
            state.save()

            best = ranked[0]
            worst = ranked[-1]
            country_info = ''
            if args.by_country is True:
                country_info = f' [{_country_key(batch[0].path)}]'
            elif args.by_country:
                country_info = f' [{args.by_country}]'
            print(f'  round {state.rounds}{country_info}: '
                  f'best={best.title!r} (mu={best.mu:.2f}) '
                  f'worst={worst.title!r} (mu={worst.mu:.2f})')
    except KeyboardInterrupt:
        print('\nInterrupted. Progress saved.')
    finally:
        state.save()

    print(f'Done. {state.rounds} rounds, {state.api_calls} API calls.')


def _print_leaderboard(state: State, rows: list[Rating], reverse: bool) -> None:
    width = max((len(r.title) for r in rows), default=20)
    path_width = max((len(r.path) for r in rows), default=20)
    header = f'{"#":>4}  {"title":<{width}}  {"mu":>7}  {"sigma":>6}  {"n":>4}  path'
    print(header)
    print('-' * len(header))
    for i, r in enumerate(rows, 1):
        print(f'{i:>4}  {r.title:<{width}}  {r.mu:>7.2f}  {r.sigma:>6.2f}  '
              f'{r.comparisons:>4}  {r.path}')


def _filter_pool(state: State, args) -> list[Rating]:
    """Filter the rating pool by --min-n and --country."""
    pool = list(state.ratings.values())
    if hasattr(args, 'prefix') and args.prefix:
        prefix = args.prefix.strip('/')
        pool = [r for r in pool if r.path.startswith(prefix + '/') or r.path == prefix]
    if hasattr(args, 'min_n'):
        pool = [r for r in pool if r.comparisons >= args.min_n]
    return pool


def cmd_top(args) -> None:
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)
    pool = _filter_pool(state, args)
    rows = sorted(
        pool,
        key=lambda r: r.conservative() if args.conservative else r.mu,
        reverse=True,
    )[:args.n]
    _print_leaderboard(state, rows, reverse=True)


def cmd_bottom(args) -> None:
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)
    pool = _filter_pool(state, args)
    # Conservative sort for `bottom` uses the UPPER credible bound:
    # only locations whose best-case is still low are "confidently bad".
    rows = sorted(
        pool,
        key=lambda r: (r.mu + 3 * r.sigma) if args.conservative else r.mu,
    )[:args.n]
    _print_leaderboard(state, rows, reverse=False)


DEBUG_BATCH = [
    # (title, path) — path is used for parent-hierarchy disambiguation in the prompt
    ('Xalapa',          'northamerica/mexico/veracruz/xalapa'),
    ('Astorga',         'europe/spain/astorga'),
    ('Medan',           'asia/indonesia/sumatra/medan'),
    ('Durbuy',          'europe/belgium/durbuy'),
    ('Yaoundé',         'africa/cameroon/yaounde'),
    ('Kołobrzeg',       'europe/poland/kolobrzeg'),
    ('San Luis Obispo', 'northamerica/unitedstates/california/centralcoast/sanluisobispo'),
    ('Sonoma',          'northamerica/unitedstates/california/northcoast/sonoma'),
    ('Truckee',         'northamerica/unitedstates/california/highsierra/truckee'),
    ('Kawartha Lakes',  'northamerica/canada/ontario/kawarthalakes'),
    ('Sebastopol',      'northamerica/unitedstates/california/northcoast/sebastopol'),
    ('Malé',            'asia/maldives/maleatoll/male'),
]


def cmd_debug(args) -> None:
    """Run a single round against a fixed 12-location batch and print the result.

    Uses the same build_prompt() and rank_with_claude() code path that `run`
    uses, so if this produces a sensible ordering, run should too.
    """
    import anthropic

    client = anthropic.Anthropic()
    model = args.model or DEFAULT_MODEL

    batch = [Rating(path=path, title=title) for title, path in DEBUG_BATCH]

    print(f'=== PROMPT ({model}) ===')
    print(build_prompt(batch))
    print()
    print('=== STRUCTURED RESPONSE ===')
    order = rank_with_claude(client, model, batch)
    if order is None:
        print('(parse failed — response did not match schema)')
        return
    for rank_pos, batch_idx in enumerate(order, 1):
        r = batch[batch_idx]
        print(f'  {rank_pos:>2}. {r.title:<20}  [id={batch_idx}]  {r.path}')


def _load_log_rounds(log_dir: Path, ratings: dict[str, Rating]) -> list[list[str]]:
    """Load all round logs and return a list of path-lists (best-to-worst).

    Each element is a list of content paths in ranked order, with unknown
    paths already stripped out.
    """
    rounds = []
    for log_file in sorted(log_dir.glob('round_*.json')):
        data = json.loads(log_file.read_text())
        paths = [e['path'] for e in data['order'] if e['path'] in ratings]
        if len(paths) >= 2:
            rounds.append(paths)
    return rounds


def _replay_once(state: State, rounds: list[list[str]]) -> None:
    """Reset state to priors and replay all rounds in the given order."""
    for r in state.ratings.values():
        r.mu = INITIAL_MU
        r.sigma = INITIAL_SIGMA
        r.comparisons = 0
    state.rounds = 0
    state.api_calls = 0

    for paths in rounds:
        batch = [state.ratings[p] for p in paths]
        apply_ranking(batch)
        state.rounds += 1
        state.api_calls += 1


def cmd_replay(args) -> None:
    """Replay JSON log files to rebuild ratings from scratch.

    With --shuffle N, replays N times in random order and averages the
    mu values. This cancels out ordering noise from the sequential updates.
    """
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)

    log_dir = Path(args.log_dir) if args.log_dir else LOG_DIR
    rounds = _load_log_rounds(log_dir, state.ratings)
    if not rounds:
        print(f'No valid JSON log files in {log_dir}/', file=sys.stderr)
        sys.exit(2)

    n_shuffle = args.shuffle or 0
    if n_shuffle < 2:
        # Single deterministic replay (original order).
        _replay_once(state, rounds)
        state.save()
        print(f'Replayed {len(rounds)} rounds.')
        print(f'State: {state.rounds} rounds, {len(state.ratings)} locations.')
        return

    # Shuffle-and-average: replay N times in random order, average mu.
    rng = random.Random(42)
    mu_accum: dict[str, float] = {p: 0.0 for p in state.ratings}

    for i in range(n_shuffle):
        shuffled = list(rounds)
        rng.shuffle(shuffled)
        _replay_once(state, shuffled)
        for p, r in state.ratings.items():
            mu_accum[p] += r.mu
        if (i + 1) % 10 == 0 or i + 1 == n_shuffle:
            print(f'  shuffle {i + 1}/{n_shuffle} done')

    # Write averaged mu back; keep sigma and comparisons from last replay
    # (they're the same regardless of order).
    for p, r in state.ratings.items():
        r.mu = mu_accum[p] / n_shuffle

    state.save()
    print(f'Replayed {len(rounds)} rounds × {n_shuffle} shuffles, averaged.')
    print(f'State: {state.rounds} rounds, {len(state.ratings)} locations.')


def _resolve_md_path(content_path: str) -> Path | None:
    """Resolve a content path to its markdown file on disk."""
    slug = content_path.rsplit('/', 1)[-1] if '/' in content_path else content_path
    # Directory-style: content/europe/france/paris/paris.md
    candidate = CONTENT_DIR / content_path / f'{slug}.md'
    if candidate.is_file():
        return candidate
    # Flat-style: content/europe/france/paris.md
    candidate = CONTENT_DIR / f'{content_path}.md'
    if candidate.is_file():
        return candidate
    return None


def cmd_apply(args) -> None:
    """Write a normalized 0-1 score into each location's frontmatter.

    The normalization maps the current min/max mu across all rated
    locations (those with ≥ min_n comparisons) to 0.0 and 1.0,
    rounding to 2 decimal places.
    """
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)

    min_n = args.min_n
    rated = [r for r in state.ratings.values() if r.comparisons >= min_n]
    if not rated:
        print(f'No locations with >= {min_n} comparisons.', file=sys.stderr)
        sys.exit(2)

    mu_min = min(r.mu for r in rated)
    mu_max = max(r.mu for r in rated)
    mu_range = mu_max - mu_min
    if mu_range < 1e-9:
        print('All rated locations have the same mu — nothing to normalize.',
              file=sys.stderr)
        sys.exit(2)

    print(f'Normalizing mu [{mu_min:.2f}, {mu_max:.2f}] → [0.0, 1.0]')

    updated = 0
    skipped_n = 0
    skipped_file = 0

    for path, r in state.ratings.items():
        if r.comparisons < min_n:
            skipped_n += 1
            continue

        md_path = _resolve_md_path(path)
        if md_path is None:
            skipped_file += 1
            continue

        post = frontmatter.load(md_path)
        score = round((r.mu - mu_min) / mu_range, 2)

        if post.metadata.get('score') == score:
            continue

        post.metadata['score'] = score
        md_path.write_text(frontmatter.dumps(post, sort_keys=False) + '\n',
                           encoding='utf-8')
        updated += 1

    print(f'Updated:          {updated}')
    print(f'Skipped (low n):  {skipped_n}')
    print(f'Skipped (no file):{skipped_file}')


def cmd_stats(args) -> None:
    state = State.load()
    if not state.ratings:
        print('No locations in state.', file=sys.stderr)
        sys.exit(2)

    ratings = list(state.ratings.values())
    mus = [r.mu for r in ratings]
    sigmas = [r.sigma for r in ratings]
    comparisons = [r.comparisons for r in ratings]
    unseen = sum(1 for c in comparisons if c == 0)

    print(f'locations:       {len(ratings)}')
    print(f'rounds run:      {state.rounds}')
    print(f'api calls:       {state.api_calls}')
    print(f'model:           {state.model}')
    print(f'unseen:          {unseen}')
    print(f'mu  mean/min/max {sum(mus)/len(mus):.2f} / {min(mus):.2f} / {max(mus):.2f}')
    print(f'sig mean/min/max {sum(sigmas)/len(sigmas):.2f} / {min(sigmas):.2f} / {max(sigmas):.2f}')
    print(f'cmp mean/min/max {sum(comparisons)/len(comparisons):.2f} / '
          f'{min(comparisons)} / {max(comparisons)}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description='Rank World66 locations with the Claude API')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_disc = sub.add_parser('discover', help='Scan content/ and initialise the rating state')
    p_disc.add_argument('--sample', type=int,
                        help='Randomly sample N locations instead of including all of them')
    p_disc.add_argument('--seed', type=int, default=42,
                        help='Random seed for --sample (default: 42)')
    p_disc.add_argument('--force', action='store_true',
                        help='Allow --sample to discard existing ratings that have comparisons')
    p_disc.set_defaults(func=cmd_discover)

    p_run = sub.add_parser('run', help='Run N ranking rounds')
    p_run.add_argument('--rounds', type=int, required=True, help='Number of rounds to run')
    p_run.add_argument('--model', help=f'Claude model to use (default: {DEFAULT_MODEL})')
    p_run.add_argument('--seed', type=int, help='Random seed for batch selection')
    p_run.add_argument('--log-dir', help=f'Directory for per-round markdown logs (default: {LOG_DIR})')
    p_run.add_argument('--by-country', nargs='?', const=True, default=False, metavar='PREFIX',
                       help='Rank within countries. Omit value to auto-pick by uncertainty, '
                            'or specify a prefix (e.g. europe/belgium) to target one country')
    p_run.set_defaults(func=cmd_run)

    p_top = sub.add_parser('top', help='Show the top-ranked locations')
    p_top.add_argument('n', type=int, nargs='?', default=25)
    p_top.add_argument('--conservative', action='store_true',
                       help='Sort by mu - 3*sigma (penalise uncertain ratings)')
    p_top.add_argument('--min-n', type=int, default=0,
                       help='Only include locations with at least this many comparisons')
    p_top.add_argument('--prefix', help='Filter to a path prefix (e.g. europe, europe/belgium)')
    p_top.set_defaults(func=cmd_top)

    p_bot = sub.add_parser('bottom', help='Show the bottom-ranked locations')
    p_bot.add_argument('n', type=int, nargs='?', default=25)
    p_bot.add_argument('--conservative', action='store_true',
                       help='Sort by mu + 3*sigma (only confidently-bad locations)')
    p_bot.add_argument('--min-n', type=int, default=0,
                       help='Only include locations with at least this many comparisons')
    p_bot.add_argument('--prefix', help='Filter to a path prefix (e.g. europe, europe/belgium)')
    p_bot.set_defaults(func=cmd_bottom)

    p_stats = sub.add_parser('stats', help='Show rating state summary')
    p_stats.set_defaults(func=cmd_stats)

    p_debug = sub.add_parser('debug', help='Send a hardcoded 12-name list to Claude and print the raw answer')
    p_debug.add_argument('--model', help=f'Claude model to use (default: {DEFAULT_MODEL})')
    p_debug.set_defaults(func=cmd_debug)

    p_replay = sub.add_parser('replay', help='Replay JSON logs to rebuild ratings from scratch')
    p_replay.add_argument('--log-dir', help=f'Directory with JSON round logs (default: {LOG_DIR})')
    p_replay.add_argument('--shuffle', type=int, metavar='N',
                          help='Replay N times in random order and average mu (reduces ordering noise)')
    p_replay.set_defaults(func=cmd_replay)

    p_apply = sub.add_parser('apply', help='Write score field into each location\'s frontmatter')
    p_apply.add_argument('--min-n', type=int, default=0,
                         help='Only apply to locations with at least this many comparisons')
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
