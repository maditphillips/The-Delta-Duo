import pandas as pd, numpy as np
from lib import season_table, scores_map

LINEUP = {'QB':1,'RB':2,'WR':3,'TE':1}   # 7 starters

def build_pairs(t, max_mean_gap=0.05, min_cv_gap=0.10):
    """Within position+season, pair players with near-identical PPG but different CV."""
    pairs=[]
    for (pos,season), g in t.groupby(['position','season']):
        g = g.sort_values('mean').reset_index(drop=True)
        used=set()
        for i in range(len(g)):
            if i in used: continue
            for j in range(i+1, len(g)):
                if j in used: continue
                a,b = g.loc[i], g.loc[j]
                if abs(a['mean']-b['mean'])/((a['mean']+b['mean'])/2) > max_mean_gap: break
                if abs(a['cv']-b['cv']) < min_cv_gap: continue
                lo, hi = (a,b) if a['cv']<b['cv'] else (b,a)
                pairs.append(dict(position=pos, season=season,
                    lo_id=lo['player_id'], hi_id=hi['player_id'],
                    lo_name=lo['name'], hi_name=hi['name'],
                    lo_cv=lo['cv'], hi_cv=hi['cv'], lo_mean=lo['mean'], hi_mean=hi['mean']))
                used.add(i); used.add(j); break
    return pd.DataFrame(pairs)

def simulate(pairs, smap, n_sims=100_000, seed=0, aligned=False, tilt=0.0):
    """Consistent roster (low-CV of each pair) vs boom/bust roster (high-CV).
       tilt: points added to the boom/bust side each week (to make consistent side favored/underdog)."""
    rng = np.random.default_rng(seed)
    pools = {pos: pairs[pairs.position==pos] for pos in LINEUP}
    if any(len(pools[p]) < LINEUP[p] for p in LINEUP): return None
    lo_tot = np.zeros(n_sims); hi_tot = np.zeros(n_sims)
    for pos, k in LINEUP.items():
        pool = pools[pos]
        idx = rng.integers(0, len(pool), size=(n_sims, k))
        for slot in range(k):
            rows = pool.iloc[idx[:, slot]]
            for side, tot in (('lo', lo_tot), ('hi', hi_tot)):
                ids = rows[f'{side}_id'].values; seasons = rows['season'].values
                draws = np.empty(n_sims)
                # group identical players to vectorise the weekly draw
                key = pd.Series(list(zip(ids, seasons)))
                for k2, pos_idx in key.groupby(key).groups.items():
                    arr = smap[k2]; pi = np.asarray(pos_idx)
                    draws[pi] = rng.choice(arr, size=len(pi), replace=True)
                tot += draws
    hi_tot = hi_tot + tilt
    return float((lo_tot > hi_tot).mean()), float((hi_tot > lo_tot).mean()), lo_tot, hi_tot

def bootstrap(pairs, smap, B=300, n_sims=20_000, seed=0, tilt=0.0):
    rng = np.random.default_rng(seed); out=[]
    for b in range(B):
        parts=[]
        for pos, g in pairs.groupby('position'):
            parts.append(g.sample(len(g), replace=True, random_state=int(rng.integers(1e9))))
        bs = pd.concat(parts, ignore_index=True)
        r = simulate(bs, smap, n_sims=n_sims, seed=int(rng.integers(1e9)), tilt=tilt)
        if r: out.append(r[0])
    return np.array(out)
