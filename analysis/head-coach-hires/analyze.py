import csv, json, math, statistics as st
from collections import defaultdict, Counter

ts = json.load(open('team_seasons.json'))
S = {(o['season'], o['team']): o for o in ts}
labels = list(csv.DictReader(open('coach_labels.csv')))

BUCKET = {'OC':'OC','DC':'DC','NFL_HC':'Prev NFL HC','COLLEGE':'College','OTHER':'Other'}

def mean(x): return sum(x)/len(x) if x else float('nan')
def ci95(x):
    if len(x) < 2: return (float('nan'), float('nan'))
    m, se = mean(x), st.stdev(x)/math.sqrt(len(x))
    return (m - 1.96*se, m + 1.96*se)

# ---------- control model: expected change given prior-year quality ----------
# Fit on team-seasons with NO opening-coach change (n-1 -> n), 2000-2025.
hire_keys = {(int(r['season']), r['team']) for r in labels}
ctrl = []
for o in ts:
    k = (o['season'], o['team'])
    prev = S.get((o['season']-1, o['team']))
    if not prev or k in hire_keys or o['season'] < 2000: continue
    ctrl.append((prev['win_pct'], o['win_pct'], prev['net_pg'], o['net_pg'],
                 prev['pf_pg'], o['pf_pg'], prev['pa_pg'], o['pa_pg']))

def ols(xs, ys):
    n = len(xs); mx, my = mean(xs), mean(ys)
    b = sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / sum((x-mx)**2 for x in xs)
    return my - b*mx, b   # intercept, slope

MODELS = {}
for name, xi, yi in (('win_pct',0,1), ('net_pg',2,3), ('pf_pg',4,5), ('pa_pg',6,7)):
    MODELS[name] = ols([c[xi] for c in ctrl], [c[yi] for c in ctrl])
print(f"Control model fit on {len(ctrl)} no-change team-seasons (2000-2025)")
for k, (a, b) in MODELS.items():
    print(f"  {k}: next = {a:.4f} + {b:.4f} * prior   (mean-reversion pull = {1-b:.2f})")

def expected(metric, prior):
    a, b = MODELS[metric]; return a + b*prior

# ---------- build per-hire records ----------
recs = []
for r in labels:
    s, team = int(r['season']), r['team']
    y0 = S[(s-1, team)]
    rec = {'season': s, 'team': team, 'coach': r['coach'],
           'bucket': BUCKET[r['prior_role']], 'role': r['prior_role'],
           'prior_nfl_hc': r['prior_nfl_hc'] == '1',
           'ambiguous': r['ambiguous'] == '1',
           'exclude': r['exclude'] == '1',
           'y0': y0}
    for yr in (1, 2, 3):
        cur = S.get((s-1+yr, team))
        rec[f'y{yr}'] = cur
        if cur:
            rec[f'd_wins_y{yr}']  = cur['w'] - y0['w']
            rec[f'd_wpct_y{yr}']  = cur['win_pct'] - y0['win_pct']
            rec[f'd_w17_y{yr}']   = (cur['win_pct'] - y0['win_pct']) * 17
            rec[f'd_pf_y{yr}']    = cur['pf_pg'] - y0['pf_pg']
            rec[f'd_pa_y{yr}']    = cur['pa_pg'] - y0['pa_pg']
            rec[f'd_net_y{yr}']   = cur['net_pg'] - y0['net_pg']
            # residual vs. mean-reversion expectation (uses year-0 as anchor for all 3)
            rec[f'r_wpct_y{yr}']  = cur['win_pct'] - expected('win_pct', y0['win_pct'])
            rec[f'r_w17_y{yr}']   = rec[f'r_wpct_y{yr}'] * 17
            rec[f'r_net_y{yr}']   = cur['net_pg'] - expected('net_pg', y0['net_pg'])
            rec[f'r_pf_y{yr}']    = cur['pf_pg'] - expected('pf_pg', y0['pf_pg'])
            rec[f'r_pa_y{yr}']    = cur['pa_pg'] - expected('pa_pg', y0['pa_pg'])
            # did the hired coach open that season?
            rec[f'kept_y{yr}'] = cur['opening_coach'] == r['coach']
    recs.append(rec)

json.dump([{k: v for k, v in r.items() if not k.startswith('y')} for r in recs],
          open('hire_records.json','w'), indent=0, default=str)
ACTIVE = [r for r in recs if not r['exclude']]
print(f"\nHires analyzed: {len(ACTIVE)} (excluded {len(recs)-len(ACTIVE)} caretaker/suspension cases)")
print("Bucket counts:", Counter(r['bucket'] for r in ACTIVE))
print("Avg year-0 wins by bucket:")
for b in ('OC','DC','Prev NFL HC','College','Other'):
    g = [r for r in ACTIVE if r['bucket']==b]
    print(f"  {b:<12} n={len(g):>3}  prior-yr wins {mean([r['y0']['w'] for r in g]):.2f}"
          f"  prior-yr win% {mean([r['y0']['win_pct'] for r in g]):.3f}")

def row(g, yr, key):
    v = [r[f'{key}_y{yr}'] for r in g if r.get(f'y{yr}')]
    if not v: return None
    lo, hi = ci95(v)
    return len(v), mean(v), st.median(v), lo, hi, sum(1 for x in v if x > 0)/len(v)

def table(title, key, unit='', groups=None):
    print('\n' + '='*104); print(title); print('='*104)
    print(f"{'Group':<14}{'Yr':<4}{'n':>4}{'mean':>9}{'median':>9}{'95% CI':>20}{'% better':>10}")
    print('-'*104)
    for name, g in groups:
        for yr in (1,2,3):
            res = row(g, yr, key)
            if not res: continue
            n, m, md, lo, hi, pct = res
            star = ' *' if (lo>0 or hi<0) else ''
            print(f"{name:<14}{yr:<4}{n:>4}{m:>9.2f}{md:>9.2f}{('['+f'{lo:+.2f}'+', '+f'{hi:+.2f}'+']'):>20}{pct*100:>9.0f}%{star}")
        print('-'*104)

BUCKETS = ['OC','DC','Prev NFL HC','College','Other']
groups = [('ALL HIRES', ACTIVE)] + [(b, [r for r in ACTIVE if r['bucket']==b]) for b in BUCKETS]
groups_rare = groups[:3] + [('Rare (comb.)', [r for r in ACTIVE if r['bucket'] in ('Prev NFL HC','College','Other')])]

table('RAW WIN CHANGE vs. season before the hire (raw wins; 2021+ years have 17 games)',
      'd_wins', groups=groups)
table('PACE-ADJUSTED WIN CHANGE (win% delta x 17 games) vs. season before the hire',
      'd_w17', groups=groups)
table('RESIDUAL WINS vs. mean-reversion expectation (the actual coach signal, /17 games)',
      'r_w17', groups=groups)

table('POINTS FOR per game, change vs. season before the hire', 'd_pf', groups=groups)
table('POINTS AGAINST per game, change vs. season before the hire (negative = better D)', 'd_pa', groups=groups)
table('NET POINTS per game, change vs. season before the hire', 'd_net', groups=groups)
table('NET POINTS per game, RESIDUAL vs. mean-reversion expectation', 'r_net', groups=groups)

print('\n' + '='*104); print('DOES THE HIRE MATCH THE UNIT HE COACHED? (year-1 side-of-ball change, pts/gm)')
print('='*104)
print(f"{'Group':<14}{'n':>4}{'d PF/g':>10}{'d PA/g':>10}{'resid PF/g':>13}{'resid PA/g':>13}")
for name, g in groups:
    g1 = [r for r in g if r.get('y1')]
    print(f"{name:<14}{len(g1):>4}{mean([r['d_pf_y1'] for r in g1]):>10.2f}"
          f"{mean([r['d_pa_y1'] for r in g1]):>10.2f}"
          f"{mean([r['r_pf_y1'] for r in g1]):>13.2f}{mean([r['r_pa_y1'] for r in g1]):>13.2f}")

print('\n' + '='*104); print('COACH SURVIVAL: still the opening head coach in year N')
print('='*104)
for name, g in groups:
    parts = []
    for yr in (2,3,4,5):
        gg = [r for r in g if r.get(f'y{yr}')] if yr<=3 else None
        if yr <= 3:
            k = sum(r[f'kept_y{yr}'] for r in gg)
            parts.append(f"Y{yr}: {k}/{len(gg)} ({100*k/len(gg):.0f}%)")
    print(f"{name:<14}" + '   '.join(parts))

print('\n' + '='*104); print('OC vs DC HEAD-TO-HEAD (Welch t-test on year-1..3 residual wins/17)')
print('='*104)
def welch(a, b):
    if len(a)<2 or len(b)<2: return float('nan'), float('nan')
    ma, mb = mean(a), mean(b); va, vb = st.variance(a), st.variance(b)
    se = math.sqrt(va/len(a) + vb/len(b)); t = (ma-mb)/se
    df = (va/len(a)+vb/len(b))**2 / ((va/len(a))**2/(len(a)-1) + (vb/len(b))**2/(len(b)-1))
    # two-sided p via normal approx (df is large enough here)
    p = 2*(1 - 0.5*(1+math.erf(abs(t)/math.sqrt(2))))
    return t, p
OC = [r for r in ACTIVE if r['bucket']=='OC']; DC = [r for r in ACTIVE if r['bucket']=='DC']
for key, lbl in (('d_w17','raw win change (/17)'), ('r_w17','residual wins (/17)'),
                 ('d_net','net pts/gm change'), ('r_net','residual net pts/gm')):
    for yr in (1,2,3):
        a = [r[f'{key}_y{yr}'] for r in OC if r.get(f'y{yr}')]
        b = [r[f'{key}_y{yr}'] for r in DC if r.get(f'y{yr}')]
        t, p = welch(a, b)
        print(f"  {lbl:<24} Y{yr}: OC {mean(a):+.2f} vs DC {mean(b):+.2f}   diff {mean(a)-mean(b):+.2f}   t={t:+.2f}  p={p:.3f}"
              + ('  <-- significant' if p < 0.05 else ''))

print('\n' + '='*104); print('SENSITIVITY: drop the 15 ambiguous-label hires')
print('='*104)
CLEAN = [r for r in ACTIVE if not r['ambiguous']]
for b in BUCKETS:
    g = [r for r in CLEAN if r['bucket']==b and r.get('y1')]
    gg = [r for r in CLEAN if r['bucket']==b and r.get('y3')]
    print(f"  {b:<12} n={len(g):>3}  Y1 raw {mean([r['d_w17_y1'] for r in g]):+.2f}  "
          f"Y1 resid {mean([r['r_w17_y1'] for r in g]):+.2f}  |  "
          f"Y3 raw {mean([r['d_w17_y3'] for r in gg]):+.2f}  Y3 resid {mean([r['r_w17_y3'] for r in gg]):+.2f}")

print('\n' + '='*104); print('RETREAD SPLIT: had been an NFL head coach before, regardless of immediate prior job')
print('='*104)
for lbl, g in (('First-time HC', [r for r in ACTIVE if not r['prior_nfl_hc']]),
               ('Retread', [r for r in ACTIVE if r['prior_nfl_hc']])):
    g1 = [r for r in g if r.get('y1')]; g3 = [r for r in g if r.get('y3')]
    print(f"  {lbl:<14} n={len(g):>3}  prior-yr W {mean([r['y0']['w'] for r in g]):.2f}  "
          f"Y1 raw {mean([r['d_w17_y1'] for r in g1]):+.2f}  Y1 resid {mean([r['r_w17_y1'] for r in g1]):+.2f}  "
          f"Y3 raw {mean([r['d_w17_y3'] for r in g3]):+.2f}  Y3 resid {mean([r['r_w17_y3'] for r in g3]):+.2f}")

print('\n' + '='*104); print('ERA SPLIT: residual wins/17, year 1 (is the OC premium a recent thing?)')
print('='*104)
for lo, hi in ((2000,2008),(2009,2016),(2017,2025)):
    parts=[]
    for b in ('OC','DC'):
        g=[r for r in ACTIVE if r['bucket']==b and lo<=r['season']<=hi and r.get('y1')]
        parts.append(f"{b} n={len(g):>2} raw {mean([r['d_w17_y1'] for r in g]):+.2f} resid {mean([r['r_w17_y1'] for r in g]):+.2f}")
    print(f"  {lo}-{hi}:  " + '   |   '.join(parts))
