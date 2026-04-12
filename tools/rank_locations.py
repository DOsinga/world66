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
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
import numpy as np
from dotenv import load_dotenv
from scipy.optimize import minimize

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = PROJECT_DIR / 'content'
STATE_FILE = PROJECT_DIR / 'location_ratings.json'
LOG_DIR = PROJECT_DIR / 'log_scoring'

BATCH_SIZE = 24
DEFAULT_MODEL = 'claude-sonnet-4-6'

# Prior: L2 regularization toward 0 (equivalent to Gaussian prior on scores).
# Larger = stronger pull toward 0, prevents scores from diverging.
REGULARIZATION = 0.01


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class Rating:
    path: str
    title: str
    score: float = 0.0       # Plackett-Luce MLE score (log-scale strength)
    variance: float = 1.0    # Uncertainty from inverse Hessian diagonal
    comparisons: int = 0

    def conservative(self) -> float:
        """Lower-bound score (score - 2*std), used for sorting 'top'."""
        return self.score - 2 * math.sqrt(self.variance)


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
                score=r.get('score', r.get('mu', 0.0)),
                variance=r.get('variance', r.get('sigma', 1.0) ** 2 if 'sigma' in r else 1.0),
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
                    'score': round(r.score, 4),
                    'variance': round(r.variance, 6),
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
# Plackett-Luce MLE
# ---------------------------------------------------------------------------

def fit_plackett_luce(
    rounds: list[list[int]],
    n_items: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit Plackett-Luce scores via maximum likelihood.

    Args:
        rounds: list of rankings, each a list of item indices in best-to-worst
                order. Not all items need to appear in every round.
        n_items: total number of items (some may not appear in any round).

    Returns:
        (scores, variances): arrays of length n_items.
        scores are log-scale strengths (higher = better).
        variances are diagonal of the inverse Hessian (uncertainty).
        Items with no observations get score=0, variance=1/REGULARIZATION.
    """
    if not rounds:
        return np.zeros(n_items), np.full(n_items, 1.0 / REGULARIZATION)

    def neg_log_likelihood(s):
        """Negative log-likelihood + L2 regularization."""
        nll = 0.5 * REGULARIZATION * np.dot(s, s)
        for ranking in rounds:
            # P(r1>r2>...>rk) = prod_i exp(s[ri]) / sum_{j>=i} exp(s[rj])
            # log P = sum_i (s[ri] - log(sum_{j>=i} exp(s[rj])))
            # Compute from the bottom up for numerical stability.
            exp_s = np.exp(s[ranking] - np.max(s[ranking]))  # shift for stability
            suffix_sum = np.cumsum(exp_s[::-1])[::-1]
            log_suffix = np.log(suffix_sum) + np.max(s[ranking])
            nll -= np.sum(s[ranking] - log_suffix)
        return nll

    def gradient(s):
        """Gradient of negative log-likelihood."""
        grad = REGULARIZATION * s.copy()
        for ranking in rounds:
            exp_s = np.exp(s[ranking])
            suffix_sum = np.cumsum(exp_s[::-1])[::-1]
            probs = exp_s / suffix_sum  # P(item i wins given remaining)
            n = len(ranking)
            for i in range(n):
                grad[ranking[i]] -= 1.0  # from the s[ri] term
                # Add back the probability contributions to the suffix sums
                for j in range(i + 1):
                    grad[ranking[i]] += probs[i] * (1.0 if j <= i else 0.0)
            # Cleaner: for each position i, item ranking[i] contributes
            # -1 + sum_{j<=i} exp(s[ri]) / suffix_sum[j]
            # Recompute more efficiently:
            grad_round = np.zeros(n)
            for i in range(n):
                grad_round[i] = -1.0
                for j in range(i + 1):
                    grad_round[i] += exp_s[i] / suffix_sum[j]
            for i, idx in enumerate(ranking):
                grad[idx] += grad_round[i]
            # Undo the double-counting from above
            grad[ranking] -= REGULARIZATION * s[ranking]
        # Recompute properly
        grad = REGULARIZATION * s.copy()
        for ranking in rounds:
            exp_s = np.exp(s[ranking])
            suffix_sum = np.cumsum(exp_s[::-1])[::-1]
            for i, idx in enumerate(ranking):
                grad[idx] -= 1.0
                for j in range(i + 1):
                    grad[idx] += exp_s[i] / suffix_sum[j]
        return grad

    s0 = np.zeros(n_items)

    result = minimize(
        neg_log_likelihood,
        s0,
        jac=gradient,
        method='L-BFGS-B',
        options={'maxiter': 500, 'ftol': 1e-8},
    )

    scores = result.x
    # Center scores (the model is invariant to a constant shift)
    scores -= np.mean(scores)

    # Variance from inverse Hessian diagonal (approximate).
    # H_ii = regularization + sum over rounds where i participates of
    #        sum_{j where i is in suffix} p_i_in_suffix * (1 - p_i_in_suffix)
    hess_diag = np.full(n_items, REGULARIZATION)
    for ranking in rounds:
        exp_s = np.exp(scores[ranking])
        suffix_sum = np.cumsum(exp_s[::-1])[::-1]
        for i, idx in enumerate(ranking):
            for j in range(i + 1):
                p = exp_s[i] / suffix_sum[j]
                hess_diag[idx] += p * (1.0 - p)

    variances = 1.0 / np.maximum(hess_diag, 1e-9)

    return scores, variances


# ---------------------------------------------------------------------------
# Log loading and scoring
# ---------------------------------------------------------------------------

def _load_log_rounds(log_dir: Path, path_to_idx: dict[str, int]) -> tuple[list[list[int]], np.ndarray]:
    """Load round logs and convert to index-based rankings.

    Returns (rounds_as_indices, comparisons_count).
    """
    n = len(path_to_idx)
    comparisons = np.zeros(n, dtype=int)
    rounds = []

    for log_file in sorted(log_dir.glob('round_*.json')):
        data = json.loads(log_file.read_text())
        indices = []
        for entry in data['order']:
            path = entry['path']
            if path in path_to_idx:
                indices.append(path_to_idx[path])
        if len(indices) >= 2:
            rounds.append(indices)
            for idx in indices:
                comparisons[idx] += 1

    return rounds, comparisons


def fit_from_logs(state: State, log_dir: Path) -> None:
    """Fit Plackett-Luce from all log files and update state."""
    paths = list(state.ratings.keys())
    path_to_idx = {p: i for i, p in enumerate(paths)}

    rounds, comparisons = _load_log_rounds(log_dir, path_to_idx)
    if not rounds:
        print('No valid rounds to fit.', file=sys.stderr)
        return

    scores, variances = fit_plackett_luce(rounds, len(paths))

    for i, path in enumerate(paths):
        r = state.ratings[path]
        r.score = float(scores[i])
        r.variance = float(variances[i])
        r.comparisons = int(comparisons[i])

    state.rounds = len(rounds)
    state.api_calls = len(rounds)


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
        s0, v0, n0 = prior[r.path]
        ordered.append({
            'rank': rank_idx,
            'title': r.title,
            'path': r.path,
            'prior_score': round(s0, 4),
            'prior_variance': round(v0, 6),
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


# ---------------------------------------------------------------------------
# Active selection
# ---------------------------------------------------------------------------

def _country_key(path: str) -> str:
    """Extract continent/country from a content path."""
    parts = path.split('/')
    return '/'.join(parts[:2]) if len(parts) >= 2 else path


def _build_comparison_graph(log_dir: Path, path_to_idx: dict[str, int]) -> dict[int, set[int]]:
    """Build an adjacency list from round logs.

    Two items are connected if they appeared in the same round.
    """
    adj: dict[int, set[int]] = {i: set() for i in range(len(path_to_idx))}
    for log_file in log_dir.glob('round_*.json'):
        data = json.loads(log_file.read_text())
        indices = [path_to_idx[e['path']] for e in data['order'] if e['path'] in path_to_idx]
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                adj[indices[i]].add(indices[j])
                adj[indices[j]].add(indices[i])
    return adj


def _bfs_distances(adj: dict[int, set[int]], sources: set[int], n: int) -> list[int]:
    """Multi-source BFS. Returns distance from nearest source for each node.

    Unreachable nodes get distance n (effectively infinity).
    """
    dist = [n] * n
    queue = []
    for s in sources:
        dist[s] = 0
        queue.append(s)
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        for neighbor in adj[node]:
            if dist[neighbor] > dist[node] + 1:
                dist[neighbor] = dist[node] + 1
                queue.append(neighbor)
    return dist


def select_batch_from_graph(
    adj: dict[int, set[int]],
    ratings: list[Rating],
    size: int = BATCH_SIZE,
    rng: random.Random | None = None,
) -> list[Rating]:
    """Pick `size` locations that maximize total pairwise graph distance.

    Greedy max-sum: start with an unseen/weakly-connected item, then
    repeatedly add the item that maximizes the sum of distances to all
    items already in the batch. This prefers items that are far from
    the batch on average, not just far from the nearest member.
    """
    rng = rng or random
    n = len(ratings)
    if n <= size:
        return list(ratings)

    # Seed: pick an unseen item (no edges), or the item with fewest connections.
    degrees = [(len(adj[i]), i) for i in range(n)]
    degrees.sort()
    seed = degrees[0][1]

    batch_order = [seed]
    batch_set = {seed}
    # sum_dist[i] = sum of distances from i to each item in the batch.
    sum_dist = _bfs_distances(adj, {seed}, n)

    for _ in range(size - 1):
        # Pick the item maximizing sum of distances to the batch.
        # Tie-break randomly.
        best_sum = -1
        candidates = []
        for i in range(n):
            if i in batch_set:
                continue
            if sum_dist[i] > best_sum:
                best_sum = sum_dist[i]
                candidates = [i]
            elif sum_dist[i] == best_sum:
                candidates.append(i)
        if not candidates:
            break
        chosen = candidates[rng.randint(0, len(candidates) - 1)]
        batch_order.append(chosen)
        batch_set.add(chosen)
        # Add distances from the new member to the running sum.
        new_dist = _bfs_distances(adj, {chosen}, n)
        for i in range(n):
            sum_dist[i] += new_dist[i]

    return [ratings[i] for i in batch_order]


def update_graph(adj: dict[int, set[int]], indices: list[int]) -> None:
    """Add edges for all pairs in a round (in-place graph update)."""
    for i in range(len(indices)):
        for j in range(i + 1, len(indices)):
            adj[indices[i]].add(indices[j])
            adj[indices[j]].add(indices[i])


def select_batch_by_country(state: State, size: int = BATCH_SIZE, rng: random.Random | None = None,
                            log_dir: Path | None = None) -> list[Rating]:
    """Pick a country with the most unseen/weakly-connected locations, then select within it."""
    rng = rng or random

    by_country: dict[str, list[Rating]] = {}
    for r in state.ratings.values():
        key = _country_key(r.path)
        by_country.setdefault(key, []).append(r)

    eligible = {k: v for k, v in by_country.items() if len(v) >= 2}
    if not eligible:
        return select_batch(state, size, rng, log_dir)

    # Pick country with the most unseen locations, tie-break by total variance.
    def country_priority(locs):
        unseen = sum(1 for r in locs if r.comparisons == 0)
        total_var = sum(r.variance for r in locs)
        return (unseen, total_var)

    chosen_key = max(eligible, key=lambda k: country_priority(eligible[k]))
    pool = eligible[chosen_key]

    if len(pool) <= size:
        return pool

    # Within the country, use variance-weighted sampling (graph-based
    # selection is less useful within a small pool).
    keys = []
    for r in pool:
        w = max(r.variance, 1e-9)
        u = rng.random()
        key = math.log(u) / w if u > 0 else -math.inf
        keys.append((key, r))
    keys.sort(key=lambda kv: kv[0], reverse=True)
    return [r for _, r in keys[:size]]


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

    # Build the comparison graph once; update incrementally after each round.
    ratings_list = list(state.ratings.values())
    path_to_idx = {r.path: i for i, r in enumerate(ratings_list)}
    adj = _build_comparison_graph(log_dir, path_to_idx)
    print(f'Comparison graph: {sum(len(v) for v in adj.values())//2} edges')

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
                batch = select_batch_from_graph(adj, ratings_list, BATCH_SIZE, rng)

            prior = {r.path: (r.score, r.variance, r.comparisons) for r in batch}

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

            # Update the comparison graph with the new round's edges.
            batch_idx = [path_to_idx[r.path] for r in batch]
            update_graph(adj, batch_idx)

            # Refit from all logs periodically (every 10 rounds) and at the end.
            if (i + 1) % 10 == 0 or i + 1 == target_rounds:
                fit_from_logs(state, log_dir)
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
        print('\nInterrupted. Refitting and saving...')
        fit_from_logs(state, log_dir)
    finally:
        state.save()

    print(f'Done. {state.rounds} rounds, {state.api_calls} API calls.')


def _print_leaderboard(state: State, rows: list[Rating], reverse: bool) -> None:
    width = max((len(r.title) for r in rows), default=20)
    header = f'{"#":>4}  {"title":<{width}}  {"score":>7}  {"var":>8}  {"n":>4}  path'
    print(header)
    print('-' * len(header))
    for i, r in enumerate(rows, 1):
        print(f'{i:>4}  {r.title:<{width}}  {r.score:>7.3f}  {r.variance:>8.4f}  '
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
    rows = sorted(
        pool,
        key=lambda r: r.conservative() if args.conservative else r.score,
        reverse=True,
    )[:args.n]
    _print_leaderboard(state, rows, reverse=True)


def cmd_bottom(args) -> None:
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)
    pool = _filter_pool(state, args)
    rows = sorted(
        pool,
        key=lambda r: (r.score + 2 * math.sqrt(r.variance)) if args.conservative else r.score,
    )[:args.n]
    _print_leaderboard(state, rows, reverse=False)


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
    """Refit Plackett-Luce model from all log files."""
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)

    log_dir = Path(args.log_dir) if args.log_dir else LOG_DIR
    fit_from_logs(state, log_dir)
    state.save()
    print(f'Fitted {state.rounds} rounds across {len(state.ratings)} locations.')


def cmd_apply(args) -> None:
    """Write a normalized 0-1 score into each location's frontmatter."""
    state = State.load()
    if not state.ratings:
        print('No locations in state. Run `discover` first.', file=sys.stderr)
        sys.exit(2)

    min_n = args.min_n
    rated = [r for r in state.ratings.values() if r.comparisons >= min_n]
    if not rated:
        print(f'No locations with >= {min_n} comparisons.', file=sys.stderr)
        sys.exit(2)

    s_min = min(r.score for r in rated)
    s_max = max(r.score for r in rated)
    s_range = s_max - s_min
    if s_range < 1e-9:
        print('All rated locations have the same score — nothing to normalize.',
              file=sys.stderr)
        sys.exit(2)

    print(f'Normalizing score [{s_min:.3f}, {s_max:.3f}] → [0.0, 1.0]')

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
        score = round((r.score - s_min) / s_range, 2)

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
    scores = [r.score for r in ratings]
    variances = [r.variance for r in ratings]
    comparisons = [r.comparisons for r in ratings]
    unseen = sum(1 for c in comparisons if c == 0)

    print(f'locations:       {len(ratings)}')
    print(f'rounds run:      {state.rounds}')
    print(f'api calls:       {state.api_calls}')
    print(f'model:           {state.model}')
    print(f'unseen:          {unseen}')
    print(f'score mean/min/max {sum(scores)/len(scores):.3f} / {min(scores):.3f} / {max(scores):.3f}')
    print(f'var   mean/min/max {sum(variances)/len(variances):.4f} / {min(variances):.4f} / {max(variances):.4f}')
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
    p_top.add_argument('--conservative', action='store_true',
                       help='Sort by score - 2*std (penalise uncertain ratings)')
    p_top.add_argument('--min-n', type=int, default=0,
                       help='Only include locations with at least this many comparisons')
    p_top.add_argument('--prefix', help='Filter to a path prefix (e.g. europe, europe/belgium)')
    p_top.set_defaults(func=cmd_top)

    p_bot = sub.add_parser('bottom', help='Show the bottom-ranked locations')
    p_bot.add_argument('n', type=int, nargs='?', default=25)
    p_bot.add_argument('--conservative', action='store_true',
                       help='Sort by score + 2*std (only confidently-bad locations)')
    p_bot.add_argument('--min-n', type=int, default=0,
                       help='Only include locations with at least this many comparisons')
    p_bot.add_argument('--prefix', help='Filter to a path prefix (e.g. europe, europe/belgium)')
    p_bot.set_defaults(func=cmd_bottom)

    p_stats = sub.add_parser('stats', help='Show rating state summary')
    p_stats.set_defaults(func=cmd_stats)

    p_debug = sub.add_parser('debug', help='Send a hardcoded list to Claude and print the raw answer')
    p_debug.add_argument('--model', help=f'Claude model to use (default: {DEFAULT_MODEL})')
    p_debug.set_defaults(func=cmd_debug)

    p_replay = sub.add_parser('replay', help='Refit Plackett-Luce from all log files')
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
