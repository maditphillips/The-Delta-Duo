"""Monte Carlo the rest of a season and tally each player's positional finish.

Each simulated season, every player's rest-of-season points are
    (expected points per team game + a resampled error)  x  team games left,
where the error is drawn from how far off the estimate was for the 40 backtest
players with the closest expectation (missed games scoring zero). That one
draw carries injury, role change, and talent miss together. Points already
scored are kept as-is. Players are then ranked by season total within position.

    python3 sim.py [season] [params_file] [n_sims] [seed]   -> sim_<season>.csv
"""
import bisect, csv, json, random, sys
from collections import defaultdict
from model import POSITIONS, load_weeks, load_schedule, build_rows, predict

NEIGHBORS = 40
TIERS = {'QB': (1, 6, 12, 24), 'TE': (1, 6, 12, 24), 'RB': (1, 12, 24, 36), 'WR': (1, 12, 24, 36)}


def neighbors(pairs, x, k=NEIGHBORS):
    """Errors of the k backtest players whose prediction was closest to x.
    pairs is sorted by prediction, so the neighbors are a contiguous window."""
    preds = [p[0] for p in pairs]
    lo = max(0, min(bisect.bisect_left(preds, x) - k // 2, len(pairs) - k))
    hi = lo + k
    while lo > 0 and x - preds[lo - 1] < preds[hi - 1] - x:  # slide toward the closer side
        lo, hi = lo - 1, hi - 1
    while hi < len(pairs) and preds[hi] - x < x - preds[lo]:
        lo, hi = lo + 1, hi + 1
    return [p[1] for p in pairs[lo:hi]]


def simulate(season, params, n_sims=10000, seed=2026):
    cutoff = params['cutoff']
    sched = load_schedule()
    weeks = {s: load_weeks(s) for s in (season - 2, season - 1, season)}
    rows = build_rows(season, cutoff, weeks, sched)
    rng = random.Random(seed)

    by_pos = defaultdict(list)
    for r in rows:
        p = params['pos'][r['pos']]
        r['pred'] = predict(p['coef'], r, cutoff)
        r['errors'] = neighbors(p['pairs'], r['pred'])
        r['proj'] = r['pts0'] + r['pred'] * r['remaining']
        r['totals'], r['finishes'] = [], []
        by_pos[r['pos']].append(r)

    for _ in range(n_sims):
        for pos, pr in by_pos.items():
            totals = [r['pts0'] + max(0.0, r['pred'] + rng.choice(r['errors'])) * r['remaining'] for r in pr]
            order = sorted(range(len(pr)), key=lambda i: -totals[i])
            for rank, i in enumerate(order, 1):
                pr[i]['totals'].append(totals[i])
                pr[i]['finishes'].append(rank)
    return rows


def summarize(r):
    t, f = sorted(r['totals']), sorted(r['finishes'])
    n = len(t)
    q = lambda xs, p: xs[min(n - 1, int(p * n))]
    out = {'player': r['name'], 'pos': r['pos'], 'team': r['team'],
           'games_so_far': r['g0'], 'pts_so_far': round(r['pts0'], 1),
           'team_games_left': r['remaining'],
           'exp_ppg_rest': round(r['pred'], 2),
           'mean_pts': round(sum(t) / n, 1),
           'p10_pts': round(q(t, .1), 1), 'p50_pts': round(q(t, .5), 1), 'p90_pts': round(q(t, .9), 1),
           'median_finish': q(f, .5), 'p10_finish': q(f, .1), 'p90_finish': q(f, .9)}
    for tier in TIERS[r['pos']]:
        out[f'top{tier}'] = round(sum(1 for x in r['finishes'] if x <= tier) / n, 4)
    return out


def main():
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    params = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'params_2025.json'))
    n_sims = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else season
    rows = simulate(season, params, n_sims, seed)
    out = [summarize(r) for r in rows]
    out.sort(key=lambda o: (POSITIONS.index(o['pos']), o['median_finish'], -o['mean_pts']))
    fields = list(dict.fromkeys(k for o in out for k in o))
    path = f'sim_{season}.csv'
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f'{season}: {len(out)} players, {n_sims} sims, as of week {params["cutoff"]} -> {path}')
    for pos in POSITIONS:
        print(f'\n{pos}')
        for o in [o for o in out if o['pos'] == pos][:12]:
            tiers = '  '.join(f"top{t} {o[f'top{t}']:.0%}" for t in TIERS[pos])
            print(f"  {o['player']:<24}{o['team']:<4} med #{o['median_finish']:<3} "
                  f"{o['p10_pts']:>6}-{o['p90_pts']:<6} {tiers}")


if __name__ == '__main__':
    main()
