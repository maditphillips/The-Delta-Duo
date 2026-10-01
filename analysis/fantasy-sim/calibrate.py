"""Out-of-sample check: simulate a finished season from the cutoff week using a
fit that never saw it, then compare the predicted tier odds to what happened.

    python3 fit.py 3 2024 && python3 calibrate.py 2025 params_2024.json
"""
import json, sys
from model import POSITIONS, load_weeks
from sim import TIERS, simulate

BINS = [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, .9), (.9, 1.01)]


def main():
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    params = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'params_2024.json'))
    rows = simulate(season, params, n_sims=int(sys.argv[3]) if len(sys.argv) > 3 else 5000)

    # actual finish: rank of full-season PPR among every player at the position
    full = load_weeks(season)
    actual = {}
    for pos in POSITIONS:
        pts = sorted(((sum(v[1] for v in p['weeks'].values()), pid)
                      for pid, p in full.items() if p['pos'] == pos), reverse=True)
        for rank, (_, pid) in enumerate(pts, 1):
            actual[pid] = rank
    in_pool = {r['id'] for r in rows}

    report = {'season': season, 'cutoff': params['cutoff'], 'fit_on': params['backtest'], 'pos': {}}
    for pos in POSITIONS:
        pr = [r for r in rows if r['pos'] == pos]
        out = {}
        for tier in TIERS[pos][1:]:
            preds = [(sum(1 for f in r['finishes'] if f <= tier) / len(r['finishes']),
                      actual[r['id']] <= tier) for r in pr]
            base = sum(hit for _, hit in preds) / len(preds)
            brier = sum((p - hit) ** 2 for p, hit in preds) / len(preds)
            brier0 = sum((base - hit) ** 2 for _, hit in preds) / len(preds)
            bins = []
            for lo, hi in BINS:
                b = [(p, hit) for p, hit in preds if lo <= p < hi]
                if b:
                    bins.append({'range': f'{lo:.0%}-{min(hi, 1):.0%}', 'n': len(b),
                                 'predicted': round(sum(p for p, _ in b) / len(b), 3),
                                 'actual': round(sum(h for _, h in b) / len(b), 3)})
            missed = sum(1 for pid, rk in actual.items()
                         if rk <= tier and full[pid]['pos'] == pos and pid not in in_pool)
            out[f'top{tier}'] = {'brier': round(brier, 4), 'skill': round(1 - brier / brier0, 3),
                                 'expected_hits': round(sum(p for p, _ in preds), 1),
                                 'outside_pool': missed, 'bins': bins}
            print(f'{pos} top{tier:<3} Brier {brier:.3f}  skill {1 - brier / brier0:+.2f}  '
                  f'expected {sum(p for p, _ in preds):.1f} of {tier}  outside pool {missed}')
            for b in bins:
                print(f"    {b['range']:>9}  n={b['n']:<4} predicted {b['predicted']:.0%}  actual {b['actual']:.0%}")
        report['pos'][pos] = out
    json.dump(report, open(f'calibration_{season}.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
