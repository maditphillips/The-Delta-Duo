"""Backtest the rest-of-season estimator on finished seasons and fit it.

For every finished season S in BACKTEST, stand at the same cutoff week the
current season is at, and regress what each player actually scored per
remaining team game (missed games count as zero) on what was knowable then.
Store the coefficients and every backtest (prediction, actual - prediction) pair;
the simulator resamples errors from each player's nearest neighbors.

    python3 fit.py [cutoff] [last_backtest_season]   -> params_<last>.json
"""
import json, sys
from model import POSITIONS, FEATURE_NAMES, load_weeks, load_schedule, build_rows, features, solve, predict

CUTOFF = int(sys.argv[1]) if len(sys.argv) > 1 else 3
LAST = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
BACKTEST = list(range(2022, LAST + 1))


def rmse(pairs):
    return (sum((a - b) ** 2 for a, b in pairs) / len(pairs)) ** 0.5


def main():
    sched = load_schedule()
    weeks = {s: load_weeks(s) for s in range(BACKTEST[0] - 2, LAST + 1)}
    rows = []
    for s in BACKTEST:
        for r in build_rows(s, CUTOFF, weeks, sched):
            if r['remaining']:
                r['season'] = s
                r['y'] = r['ros_pts'] / r['remaining']
                rows.append(r)

    params = {'cutoff': CUTOFF, 'backtest': BACKTEST, 'features': FEATURE_NAMES, 'pos': {}}
    for pos in POSITIONS:
        pr = [r for r in rows if r['pos'] == pos]
        coef = solve([features(r, CUTOFF) for r in pr], [r['y'] for r in pr])
        for r in pr:
            r['pred'] = predict(coef, r, CUTOFF)
        naive = rmse([(r['y'], r['pts0'] / r['g0']) for r in pr])  # "keep scoring like this"
        model = rmse([(r['y'], r['pred']) for r in pr])

        pr.sort(key=lambda r: r['pred'])
        pairs = [[round(r['pred'], 4), round(r['y'] - r['pred'], 4)] for r in pr]
        params['pos'][pos] = {'coef': [round(c, 5) for c in coef], 'n': len(pr),
                              'rmse': round(model, 3), 'rmse_naive': round(naive, 3),
                              'pairs': pairs}
        print(f"{pos}: n={len(pr)}  RMSE {model:.2f} vs naive {naive:.2f}  "
              + ' '.join(f'{n}={c:.2f}' for n, c in zip(FEATURE_NAMES, coef)))
    out = f'params_{LAST}.json'
    json.dump(params, open(out, 'w'))
    print('->', out)


if __name__ == '__main__':
    main()
