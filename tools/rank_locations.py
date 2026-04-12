#!/usr/bin/env python3
"""
Rank World66 locations as travel destinations using the Claude API.

Uses a Plackett-Luce model fitted via maximum likelihood to all observed
rankings. Each round selects locations via uncertainty sampling (weighted
by the inverse Hessian of the log-likelihood), asks Claude to order them,
and refits the model from all accumulated log data.

Usage:
    python tools/rank_locations.py discover
    python tools/rank_locations.py run --rounds 50
    python tools/rank_locations.py replay
    python tools/rank_locations.py top 30
    python tools/rank_locations.py bottom 30
    python tools/rank_locations.py stats

State is stored in location_ratings.json and runs are resumable.
Log files in log_scoring/ are the source of truth — scores can always
be rebuilt from them via `replay`.
"""

import argparse
import datetime as dt
import json
import math
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cmp_to_key
from pathlib import Path

import frontmatter
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = PROJECT_DIR / 'content'
STATE_FILE = PROJECT_DIR / 'location_ratings.json'
LOG_DIR = PROJECT_DIR / 'log_scoring'

BATCH_SIZE = 24
DEFAULT_MODEL = 'claude-sonnet-4-6'


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class Rating:
    path: str
    title: str
    rank: int = 0            # Global rank (1 = best), set by sort
    win_count: int = 0       # Total pairwise wins across all rounds
    comparisons: int = 0     # Number of rounds appeared in


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
                rank=r.get('rank', 0),
                win_count=r.get('win_count', 0),
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
                    'rank': r.rank,
                    'win_count': r.win_count,
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

CONTINENTS = {'africa', 'antarctica', 'asia', 'australiaandpacific', 'europe',
               'northamerica', 'southamerica'}


def discover_locations() -> list[tuple[str, str]]:
    """Scan content/ for type: location pages under known continents."""
    found = []
    for md_file in sorted(CONTENT_DIR.rglob('*.md')):
        # Only include pages under a known continent.
        rel = md_file.relative_to(CONTENT_DIR)
        if rel.parts[0] not in CONTINENTS:
            continue
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
        has_work = any(r.comparisons > 0 for r in state.ratings.values())
        if has_work and not args.force:
            print('State already contains rated locations. Use --force to discard.', file=sys.stderr)
            sys.exit(2)
        rng = random.Random(args.seed)
        rng.shuffle(locations)
        locations = locations[:args.sample]
        print(f'Sampled {len(locations)} locations (seed={args.seed}).')

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
# Pairwise sort from round logs
# ---------------------------------------------------------------------------

def sort_locations(state: State, log_dir: Path) -> None:
    """Sort all locations using directed transitivity from round logs.

    1. Build a directed graph (winner → loser) from all rounds.
    2. Find strongly connected components (cycles).
    3. Topological sort the condensed DAG.
    4. Within each SCC, sort by win rate.
    5. Assign global ranks.
    """
    known_paths = set(state.ratings.keys())
    paths = list(state.ratings.keys())
    path_to_idx = {p: i for i, p in enumerate(paths)}
    n = len(paths)

    # Build directed graph and collect stats.
    fwd: dict[int, set[int]] = {i: set() for i in range(n)}
    total_wins = [0] * n
    possible_wins = [0] * n
    comparisons = [0] * n

    for log_file in sorted(log_dir.glob('round_*.json')):
        data = json.loads(log_file.read_text())
        indices = [path_to_idx[e['path']] for e in data['order'] if e['path'] in known_paths]
        batch_size = len(indices)
        for pos, idx in enumerate(indices):
            comparisons[idx] += 1
            wins_this_round = batch_size - 1 - pos
            total_wins[idx] += wins_this_round
            possible_wins[idx] += batch_size - 1
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                fwd[indices[i]].add(indices[j])

    # Tarjan's SCC algorithm.
    index_counter = [0]
    stack = []
    on_stack = [False] * n
    indices_arr = [-1] * n
    lowlink = [0] * n
    sccs: list[list[int]] = []

    def strongconnect(v):
        indices_arr[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in fwd[v]:
            if indices_arr[w] == -1:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack[w]:
                lowlink[v] = min(lowlink[v], indices_arr[w])

        if lowlink[v] == indices_arr[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    sys.setrecursionlimit(max(n + 100, sys.getrecursionlimit()))
    for v in range(n):
        if indices_arr[v] == -1:
            strongconnect(v)

    # Map each node to its SCC id.
    scc_id = [0] * n
    for i, scc in enumerate(sccs):
        for v in scc:
            scc_id[v] = i

    # Build condensation DAG (edges between SCCs).
    scc_edges: dict[int, set[int]] = {i: set() for i in range(len(sccs))}
    for v in range(n):
        for w in fwd[v]:
            if scc_id[v] != scc_id[w]:
                scc_edges[scc_id[v]].add(scc_id[w])

    # Topological sort of condensation DAG (Kahn's algorithm).
    in_degree = [0] * len(sccs)
    for sid, targets in scc_edges.items():
        for t in targets:
            in_degree[t] += 1
    queue = [i for i in range(len(sccs)) if in_degree[i] == 0]
    topo_order = []
    head = 0
    while head < len(queue):
        sid = queue[head]
        head += 1
        topo_order.append(sid)
        for t in scc_edges[sid]:
            in_degree[t] -= 1
            if in_degree[t] == 0:
                queue.append(t)

    # Build final ordering: SCCs in topological order, within each SCC sort by win rate.
    sorted_indices = []
    for sid in topo_order:
        scc = sccs[sid]
        if len(scc) == 1:
            sorted_indices.extend(scc)
        else:
            scc.sort(key=lambda v: total_wins[v] / possible_wins[v]
                     if possible_wins[v] > 0 else 0, reverse=True)
            sorted_indices.extend(scc)

    # Assign ranks.
    for rank, idx in enumerate(sorted_indices, 1):
        r = state.ratings[paths[idx]]
        r.rank = rank
        r.win_count = total_wins[idx]
        r.comparisons = comparisons[idx]

    state.rounds = sum(1 for _ in log_dir.glob('round_*.json'))


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def write_scoring_log(
    log_dir: Path,
    round_num: int,
    model: str,
    batch: list[Rating],
    ranking: list[int],
    prior: dict[str, tuple[float, float, int]],
) -> Path:
    """Write a JSON log of a single ranking round."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f'round_{round_num:04d}.json'
    ts = dt.datetime.now().isoformat(timespec='seconds')

    ordered = []
    for rank_idx, batch_idx in enumerate(ranking, 1):
        r = batch[batch_idx]
        prior_rank, prior_wins, prior_n = prior[r.path]
        ordered.append({
            'rank': rank_idx,
            'title': r.title,
            'path': r.path,
            'prior_rank': prior_rank,
            'prior_wins': prior_wins,
            'prior_n': prior_n,
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


# ---------------------------------------------------------------------------
# Active selection
# ---------------------------------------------------------------------------

def _country_key(path: str) -> str:
    """Extract continent/country from a content path."""
    parts = path.split('/')
    return '/'.join(parts[:2]) if len(parts) >= 2 else path


def _build_directed_graph(log_dir: Path, path_to_idx: dict[str, int]) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    """Build directed adjacency lists from round logs.

    Returns (forward, reverse) where forward[a] contains items a beat,
    and reverse[a] contains items that beat a.
    """
    n = len(path_to_idx)
    fwd: dict[int, set[int]] = {i: set() for i in range(n)}
    rev: dict[int, set[int]] = {i: set() for i in range(n)}
    for log_file in log_dir.glob('round_*.json'):
        data = json.loads(log_file.read_text())
        indices = [path_to_idx[e['path']] for e in data['order'] if e['path'] in path_to_idx]
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                fwd[indices[i]].add(indices[j])  # i beat j
                rev[indices[j]].add(indices[i])   # j was beaten by i
    return fwd, rev


def _bfs_reachable(adj: dict[int, set[int]], sources: set[int]) -> set[int]:
    """BFS from sources following directed edges. Returns all reachable nodes."""
    visited = set(sources)
    queue = list(sources)
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        for nb in adj[node]:
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited


def select_batch_from_graph(
    fwd: dict[int, set[int]],
    rev: dict[int, set[int]],
    ratings: list[Rating],
    size: int = BATCH_SIZE,
    rng: random.Random | None = None,
) -> list[Rating]:
    """Pick `size` locations that are maximally incomparable in the directed graph.

    An item is "comparable" to the batch if there's a directed path from
    it to any batch member (it's better) or from any batch member to it
    (it's worse). Items with no directed path in either direction are
    incomparable — those are the most valuable to add.

    Greedy: start with the least-connected item, then repeatedly add the
    item that is comparable to the fewest batch members.
    """
    rng = rng or random
    n = len(ratings)
    if n <= size:
        return list(ratings)

    # Seed: item with smallest total reach (fewest items it can compare to).
    min_reach = n + 1
    seed_candidates = []
    for i in range(n):
        reach = len(fwd[i]) + len(rev[i])
        if reach < min_reach:
            min_reach = reach
            seed_candidates = [i]
        elif reach == min_reach:
            seed_candidates.append(i)
    seed = seed_candidates[rng.randint(0, len(seed_candidates) - 1)]

    batch_order = [seed]
    batch_set = {seed}
    # Track: items reachable FROM the batch (batch beats them) and
    # items that can REACH the batch (they beat the batch).
    fwd_reached = _bfs_reachable(fwd, {seed})
    rev_reached = _bfs_reachable(rev, {seed})

    for _ in range(size - 1):
        # Pick the item that is LEAST comparable to the batch,
        # penalizing items that have already been compared many times.
        best_score = -1
        candidates = []
        for i in range(n):
            if i in batch_set:
                continue
            # Incomparability: 2 if no directed path either way,
            # 1 if reachable in only one direction, 0 if both.
            in_fwd = i in fwd_reached
            in_rev = i in rev_reached
            incomp = (0 if in_fwd else 1) + (0 if in_rev else 1)
            # Penalize over-compared items: prefer items with few comparisons.
            # Score = incomparability * 1000 - comparisons, so incomparable
            # items with few comparisons are picked first.
            score = incomp * 1000 - ratings[i].comparisons
            if score > best_score:
                best_score = score
                candidates = [i]
            elif score == best_score:
                candidates.append(i)
        if not candidates:
            break
        chosen = candidates[rng.randint(0, len(candidates) - 1)]
        batch_order.append(chosen)
        batch_set.add(chosen)
        # Extend reachability with new member.
        fwd_reached |= _bfs_reachable(fwd, {chosen})
        rev_reached |= _bfs_reachable(rev, {chosen})

    return [ratings[i] for i in batch_order]


def update_directed_graph(fwd: dict[int, set[int]], rev: dict[int, set[int]],
                          indices: list[int]) -> None:
    """Add directed edges for a round result (indices in best-to-worst order)."""
    for i in range(len(indices)):
        for j in range(i + 1, len(indices)):
            fwd[indices[i]].add(indices[j])
            rev[indices[j]].add(indices[i])


def select_batch_by_country(state: State, size: int = BATCH_SIZE, rng: random.Random | None = None,
                            log_dir: Path | None = None) -> list[Rating]:
    """Pick a country with the most unseen/least-compared locations, then select within it."""
    rng = rng or random

    by_country: dict[str, list[Rating]] = {}
    for r in state.ratings.values():
        key = _country_key(r.path)
        by_country.setdefault(key, []).append(r)

    eligible = {k: v for k, v in by_country.items() if len(v) >= 2}
    if not eligible:
        return []

    # Pick country with the most unseen locations, tie-break by fewest total comparisons.
    def country_priority(locs):
        unseen = sum(1 for r in locs if r.comparisons == 0)
        total_cmp = sum(r.comparisons for r in locs)
        return (unseen, -total_cmp)

    chosen_key = max(eligible, key=lambda k: country_priority(eligible[k]))
    pool = eligible[chosen_key]

    if len(pool) <= size:
        return pool

    # Within the country, prefer least-compared locations.
    pool.sort(key=lambda r: r.comparisons)
    return pool[:size]


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


def _resolve_md_path(content_path: str) -> Path | None:
    """Resolve a content path to its markdown file on disk."""
    slug = content_path.rsplit('/', 1)[-1] if '/' in content_path else content_path
    candidate = CONTENT_DIR / content_path / f'{slug}.md'
    if candidate.is_file():
        return candidate
    candidate = CONTENT_DIR / f'{content_path}.md'
    if candidate.is_file():
        return candidate
    return None


def _parent_context(path: str) -> str:
    """Return the parent page's title from frontmatter."""
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

    fallback = parent_path.rsplit('/', 1)[-1].replace('_', ' ').title()
    _parent_title_cache[parent_path] = fallback
    return fallback


def build_prompt(batch: list[Rating]) -> str:
    """Build the ranking prompt for a batch of locations."""
    lines = [
        f'Order these {len(batch)} travel destinations from best to '
        'worst as places to visit for a tourist:',
        '',
    ]
    for i, r in enumerate(batch):
        parts = r.path.split('/')
        depth = len(parts)
        parent = _parent_context(r.path)
        if depth <= 2 or not parent or parent.lower() == r.title.lower():
            lines.append(f'- [{i}] {r.title}')
        else:
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
    """Call Claude and return the ordering as a list of indices into `batch`."""
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
    import anthropic

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

    # Build the directed comparison graph once; update incrementally after each round.
    ratings_list = list(state.ratings.values())
    path_to_idx = {r.path: i for i, r in enumerate(ratings_list)}
    fwd, rev = _build_directed_graph(log_dir, path_to_idx)
    print(f'Directed graph: {sum(len(v) for v in fwd.values())} edges')

    try:
        for i in range(target_rounds):
            if args.by_country is True:
                batch = select_batch_by_country(state, BATCH_SIZE, rng, log_dir)
            elif args.by_country:
                prefix = args.by_country.strip('/')
                pool = [r for r in state.ratings.values()
                        if r.path.startswith(prefix + '/') or r.path == prefix]
                if len(pool) <= BATCH_SIZE:
                    batch = pool
                else:
                    rng_local = rng or random
                    rng_local.shuffle(pool)
                    batch = pool[:BATCH_SIZE]
            else:
                batch = select_batch_from_graph(fwd, rev, ratings_list, BATCH_SIZE, rng)

            prior = {r.path: (r.rank, r.win_count, r.comparisons) for r in batch}

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
            state.rounds += 1
            write_scoring_log(log_dir, state.rounds, model, batch, ranking, prior)

            # Update the directed graph with the new round's edges.
            ranked_idx = [path_to_idx[batch[idx].path] for idx in ranking]
            update_directed_graph(fwd, rev, ranked_idx)

            # Re-sort periodically (every 10 rounds) and at the end.
            if (i + 1) % 10 == 0 or i + 1 == target_rounds:
                sort_locations(state, log_dir)
                state.save()

            best = ranked[0]
            worst = ranked[-1]
            country_info = ''
            if args.by_country is True:
                country_info = f' [{_country_key(batch[0].path)}]'
            elif args.by_country:
                country_info = f' [{args.by_country}]'
            print(f'  round {state.rounds}{country_info}: '
                  f'best={best.title!r} worst={worst.title!r}')
    except KeyboardInterrupt:
        print('\nInterrupted. Sorting and saving...')
        sort_locations(state, log_dir)
    finally:
        state.save()

    print(f'Done. {state.rounds} rounds, {state.api_calls} API calls.')


def _print_leaderboard(state: State, rows: list[Rating]) -> None:
    width = max((len(r.title) for r in rows), default=20)
    header = f'{"rank":>6}  {"title":<{width}}  {"wins":>6}  {"n":>4}  path'
    print(header)
    print('-' * len(header))
    for r in rows:
        print(f'{r.rank:>6}  {r.title:<{width}}  {r.win_count:>6}  '
              f'{r.comparisons:>4}  {r.path}')


def _filter_pool(state: State, args) -> list[Rating]:
    """Filter the rating pool by --min-n and --prefix."""
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
    rows = sorted(pool, key=lambda r: r.rank)[:args.n]
    _print_leaderboard(state, rows)


def cmd_bottom(args) -> None:
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)
    pool = _filter_pool(state, args)
    rows = sorted(pool, key=lambda r: -r.rank)[:args.n]
    _print_leaderboard(state, rows)


DEBUG_BATCH = [
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
    """Send a hardcoded list to Claude and print the result."""
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


def cmd_replay(args) -> None:
    """Sort all locations from round log data."""
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)

    log_dir = Path(args.log_dir) if args.log_dir else LOG_DIR
    sort_locations(state, log_dir)
    state.save()
    print(f'Sorted from {state.rounds} rounds across {len(state.ratings)} locations.')


def cmd_apply(args) -> None:
    """Write a normalized 0-1 score into each location's frontmatter.

    Score is derived from rank: rank 1 → 1.0, rank N → 0.0.
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

    max_rank = max(r.rank for r in rated)
    if max_rank <= 1:
        print('Not enough ranked locations to normalize.', file=sys.stderr)
        sys.exit(2)

    print(f'Normalizing rank [1, {max_rank}] → [1.0, 0.0]')

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
        score = round(1.0 - (r.rank - 1) / (max_rank - 1), 2)

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
    comparisons = [r.comparisons for r in ratings]
    win_counts = [r.win_count for r in ratings]
    unseen = sum(1 for c in comparisons if c == 0)

    print(f'locations:       {len(ratings)}')
    print(f'rounds run:      {state.rounds}')
    print(f'api calls:       {state.api_calls}')
    print(f'model:           {state.model}')
    print(f'unseen:          {unseen}')
    print(f'wins  mean/min/max {sum(win_counts)/len(win_counts):.1f} / {min(win_counts)} / {max(win_counts)}')
    print(f'cmp   mean/min/max {sum(comparisons)/len(comparisons):.2f} / '
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
    p_run.add_argument('--log-dir', help=f'Directory for per-round logs (default: {LOG_DIR})')
    p_run.add_argument('--by-country', nargs='?', const=True, default=False, metavar='PREFIX',
                       help='Rank within countries. Omit value to auto-pick by uncertainty, '
                            'or specify a prefix (e.g. europe/belgium) to target one country')
    p_run.set_defaults(func=cmd_run)

    p_top = sub.add_parser('top', help='Show the top-ranked locations')
    p_top.add_argument('n', type=int, nargs='?', default=25)
    p_top.add_argument('--min-n', type=int, default=0,
                       help='Only include locations with at least this many comparisons')
    p_top.add_argument('--prefix', help='Filter to a path prefix (e.g. europe, europe/belgium)')
    p_top.set_defaults(func=cmd_top)

    p_bot = sub.add_parser('bottom', help='Show the bottom-ranked locations')
    p_bot.add_argument('n', type=int, nargs='?', default=25)
    p_bot.add_argument('--min-n', type=int, default=0,
                       help='Only include locations with at least this many comparisons')
    p_bot.add_argument('--prefix', help='Filter to a path prefix (e.g. europe, europe/belgium)')
    p_bot.set_defaults(func=cmd_bottom)

    p_stats = sub.add_parser('stats', help='Show rating state summary')
    p_stats.set_defaults(func=cmd_stats)

    p_debug = sub.add_parser('debug', help='Send a hardcoded list to Claude and print the raw answer')
    p_debug.add_argument('--model', help=f'Claude model to use (default: {DEFAULT_MODEL})')
    p_debug.set_defaults(func=cmd_debug)

    p_replay = sub.add_parser('replay', help='Sort all locations from round log data')
    p_replay.add_argument('--log-dir', help=f'Directory with JSON round logs (default: {LOG_DIR})')
    p_replay.set_defaults(func=cmd_replay)

    p_apply = sub.add_parser('apply', help='Write score field into each location\'s frontmatter')
    p_apply.add_argument('--min-n', type=int, default=0,
                         help='Only apply to locations with at least this many comparisons')
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
