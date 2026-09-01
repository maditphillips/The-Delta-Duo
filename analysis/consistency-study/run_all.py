"""Every number cited in REPORT.md. Run from the directory holding hppr_weekly.parquet."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from lib import season_table, scores_map, D
import sim as S
from sim import build_pairs, simulate, bootstrap

YRS = list(range(2012, 2026))
def rule(t): print(f"\n{'='*72}\n{t}\n{'='*72}")

# 1. sample recovery -------------------------------------------------------
rule("1. Recovering Reedy's 368 qualifying player-seasons")
t24 = season_table([2024, 2025])
print(f"  >=14 games in Wk1-17, 2024-25, QB/RB/WR/TE -> {len(t24)} player-seasons (Reedy: 368)")
print(t24.groupby(['season','position']).size().unstack())

# 2. CV is a quality proxy -------------------------------------------------
rule("2. CV is largely a proxy for being good")
for pos, g in t24.groupby('position'):
    print(f"  corr(CV, PPG) {pos}: {np.corrcoef(g.cv, g['mean'])[0,1]:+.3f}")
print(f"  corr(CV, PPG) pooled: {np.corrcoef(t24.cv, t24['mean'])[0,1]:+.3f}")
t24['gap'] = (t24['mean'] - t24['median']) / t24['mean']
print("\n  Right-skew tax by CV quartile (this is the real mechanism):")
print(t24.groupby(pd.qcut(t24.cv, 4, labels=['low CV','2','3','high CV'])).agg(
    n=('gap','size'), ppg=('mean','mean'), median=('median','mean'),
    mean_minus_median_pct=('gap','mean'), skew=('skew','mean')).round(3))

# 3. replicate the roster sim + honest error bars ---------------------------
rule("3. Roster simulation: replication, and the confidence interval he omitted")
for yrs in ([2024], [2025], [2024, 2025]):
    t = season_table(yrs); smap = scores_map(yrs); pairs = build_pairs(t)
    w, _, lo, hi = simulate(pairs, smap, n_sims=100_000, seed=1)
    bs = bootstrap(pairs, smap, B=300, n_sims=20_000, seed=7)
    c = np.percentile(bs, [2.5, 97.5])
    print(f"  {'+'.join(map(str,yrs)):10s} pairs={len(pairs):3d}  consistent wins {w*100:5.1f}%  "
          f"95% CI over players [{c[0]*100:.1f}%, {c[1]*100:.1f}%]")
    print(f"{'':13s}median {np.median(lo):.1f} vs {np.median(hi):.1f} | "
          f"90th pct {np.percentile(lo,90):.1f} vs {np.percentile(hi,90):.1f} | "
          f"10th pct {np.percentile(lo,10):.1f} vs {np.percentile(hi,10):.1f}")

# 4. out-of-sample across 14 seasons ---------------------------------------
rule("4. Out-of-sample: the same test on every season 2012-2025")
r = []
for y in YRS:
    t = season_table([y]); p = build_pairs(t)
    w = simulate(p, scores_map([y]), n_sims=100_000, seed=3)[0]
    r.append(w); print(f"  {y}  pairs={len(p):3d}  {w*100:5.1f}%  ({(w-0.5)*100:+.1f} pp)")
r = np.array(r); se = r.std(ddof=1)/np.sqrt(len(r))
print(f"  seasons>50%: {(r>0.5).sum()}/{len(r)}   mean edge {(r.mean()-0.5)*100:+.2f} pp   "
      f"95% CI [{((r.mean()-1.96*se)-0.5)*100:+.2f}, {((r.mean()+1.96*se)-0.5)*100:+.2f}]")

# 5. edge does NOT compound with lineup size -------------------------------
rule("5. Does the edge compound across more lineup slots? (no -- it dilutes)")
t = season_table(YRS); smap = scores_map(YRS); pairs = build_pairs(t)
for lu, lab in [({'QB':1,'RB':1,'WR':1,'TE':1},'4 starters'),
                ({'QB':1,'RB':2,'WR':2,'TE':1},'6 starters'),
                ({'QB':1,'RB':2,'WR':3,'TE':1},'7 starters'),
                ({'QB':1,'RB':3,'WR':4,'TE':2},'10 starters')]:
    S.LINEUP = lu
    print(f"  {lab:12s}: {simulate(pairs,smap,n_sims=150_000,seed=9)[0]*100:.2f}%")
S.LINEUP = {'QB':1,'RB':2,'WR':3,'TE':1}

# 6. year-to-year stability ------------------------------------------------
rule("6. Year-to-year stability: 13 transitions vs his 1")
a = t.copy(); a['nxt'] = a.season + 1
m = a.merge(t, left_on=['player_id','nxt'], right_on=['player_id','season'], suffixes=('_y1','_y2'))
rr = lambda x, y: np.corrcoef(x, y)[0,1]
def partial(x, y, c1, c2):
    X = np.column_stack([np.ones(len(x)), c1, c2])
    res = lambda v: v - X @ np.linalg.lstsq(X, v, rcond=None)[0]
    return rr(res(x), res(y))
one = m[m.season_y1 == 2024]
print(f"  {'metric':>20} {'2024->25 (his)':>16} {'13 transitions':>16}")
for lab, c in [('avg scoring','mean'),('coefficient of var','cv'),('boom rate','boom'),('bust rate','bust')]:
    print(f"  {lab:>20} {rr(one[c+'_y1'],one[c+'_y2']):>16.2f} {rr(m[c+'_y1'],m[c+'_y2']):>16.2f}")
print(f"\n  corr(CV_y1, CV_y2)      raw {rr(m.cv_y1,m.cv_y2):.2f}  ->  "
      f"partial on PPG {partial(m.cv_y1.values,m.cv_y2.values,m['mean_y1'].values,m['mean_y2'].values):.2f}")
print(f"  corr(boom_y1, boom_y2)  raw {rr(m.boom_y1,m.boom_y2):.2f}  ->  "
      f"partial on PPG {partial(m.boom_y1.values,m.boom_y2.values,m['mean_y1'].values,m['mean_y2'].values):.2f}")

# 7. ex-ante: the decision a manager actually faces -------------------------
rule("7. ORACLE vs EX-ANTE (label by prior-season CV, not same-season CV)")
prior = t.set_index(['player_id','season'])['cv'].to_dict()
def pairs_for(season, use_prior, mt=0.05, ct=0.10):
    out = []
    for pos, g in t[t.season == season].groupby('position'):
        g = g.sort_values('mean').reset_index(drop=True); used = set()
        for i in range(len(g)):
            if i in used: continue
            for j in range(i+1, len(g)):
                if j in used: continue
                a, b = g.loc[i], g.loc[j]
                if abs(a['mean']-b['mean'])/((a['mean']+b['mean'])/2) > mt: break
                if use_prior:
                    pa, pb = prior.get((a.player_id, season-1)), prior.get((b.player_id, season-1))
                    if pa is None or pb is None or abs(pa-pb) < ct: continue
                    lo, hi = (a, b) if pa < pb else (b, a)
                else:
                    if abs(a['cv']-b['cv']) < ct: continue
                    lo, hi = (a, b) if a['cv'] < b['cv'] else (b, a)
                out.append(dict(position=pos, season=season, lo_id=lo.player_id, hi_id=hi.player_id,
                                lo_mean=lo['mean'], hi_mean=hi['mean']))
                used.add(i); used.add(j); break
    return pd.DataFrame(out)
for lab, up, mt, ct in [("ORACLE  (same-season CV)", False, 0.05, 0.10),
                        ("EX-ANTE (prior-season CV)", True, 0.05, 0.10),
                        ("EX-ANTE (looser match)",    True, 0.08, 0.05),
                        ("EX-ANTE (loosest match)",   True, 0.10, 0.05)]:
    ws, tot = [], 0
    for y in range(2013, 2026):
        p = pairs_for(y, up, mt, ct)
        if len(p) < 10: continue
        res = simulate(p, smap, n_sims=60_000, seed=5)
        if res: ws.append(res[0]); tot += len(p)
    ws = np.array(ws); se = ws.std(ddof=1)/np.sqrt(len(ws))
    print(f"  {lab:26s} pairs={tot:4d}  edge {(ws.mean()-0.5)*100:+.2f} pp  "
          f"CI [{((ws.mean()-1.96*se)-0.5)*100:+.2f}, {((ws.mean()+1.96*se)-0.5)*100:+.2f}]  "
          f"seasons>50%: {(ws>0.5).sum()}/{len(ws)}")

# 8. survivorship ----------------------------------------------------------
rule("8. Survivorship: what the >=14-game filter removes")
full = season_table(YRS, mingames=1)
kept, drop = full[full.g >= 14], full[(full.g >= 8) & (full.g < 14)]
print(f"  >=1 game: {len(full)}   >=14 games: {len(kept)}  -> filter drops "
      f"{100*(1-len(kept)/len(full)):.0f}% of player-seasons")
print(f"  kept    : PPG {kept['mean'].mean():.2f}  CV {kept.cv.mean():.3f}  bust {kept.bust.mean():.3f}")
print(f"  dropped : PPG {drop['mean'].mean():.2f}  CV {drop.cv.mean():.3f}  bust {drop.bust.mean():.3f}")
z = season_table(YRS, mingames=14, zeros=True)
k = t.merge(z[['player_id','season','cv']], on=['player_id','season'], suffixes=('','_z'))
print(f"  counting missed games as 0: CV {k.cv.mean():.3f} -> {k.cv_z.mean():.3f}, "
      f"rank corr {np.corrcoef(k.cv.rank(), k.cv_z.rank())[0,1]:.2f} (little changes)")
