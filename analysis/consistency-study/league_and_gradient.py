"""Sections 5 (matchup gradient) and 9 (full-league title simulation) of REPORT.md."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from lib import season_table, scores_map
from sim import build_pairs

YRS = list(range(2012, 2026))
t = season_table(YRS); smap = scores_map(YRS)
t['key'] = list(zip(t.player_id, t.season))
pairs = build_pairs(t)

# ---- 5. effect of one swap, by projected margin --------------------------
wr = pairs[pairs.position == 'WR'].reset_index(drop=True)
rng = np.random.default_rng(11)
by_pos = {p: t[t.position == p].reset_index(drop=True) for p in ['QB','RB','WR','TE']}
def draw(pos, n):
    r = by_pos[pos].iloc[rng.integers(0, len(by_pos[pos]), n)]
    return np.array([rng.choice(smap[k]) for k in r.key]), r['mean'].values

N = 120_000
base_s = base_m = opp_s = opp_m = 0
for pos, k in [('QB',1),('RB',2),('WR',2),('TE',1)]:
    for _ in range(k): s, m = draw(pos, N); base_s = base_s + s; base_m = base_m + m
for pos, k in [('QB',1),('RB',2),('WR',3),('TE',1)]:
    for _ in range(k): s, m = draw(pos, N); opp_s = opp_s + s; opp_m = opp_m + m
pr = wr.iloc[rng.integers(0, len(wr), N)]
lo_s = np.array([rng.choice(smap[k]) for k in zip(pr.lo_id, pr.season)])
hi_s = np.array([rng.choice(smap[k]) for k in zip(pr.hi_id, pr.season)])
margin = base_m + (pr.lo_mean.values + pr.hi_mean.values)/2 - opp_m
win_lo, win_hi = (base_s+lo_s) > opp_s, (base_s+hi_s) > opp_s
print("=== Swapping ONE volatile WR for an equal-PPG consistent WR ===")
edges = [-100,-20,-12,-6,-2,2,6,12,20,100]
labs = ['<-20 (big dog)','-20..-12','-12..-6','-6..-2','-2..+2 (even)','+2..+6','+6..+12','+12..+20','>+20 (big fav)']
for i, l in enumerate(labs):
    m = (margin >= edges[i]) & (margin < edges[i+1])
    if m.sum() < 800: continue
    a, b = win_hi[m].mean(), win_lo[m].mean()
    print(f"  {l:>16} n={m.sum():>6}  volatile {a*100:5.1f}%  consistent {b*100:5.1f}%  delta {(b-a)*100:+.2f} pp")

# ---- 9. full 12-team leagues: weekly wins vs titles -----------------------
pools = {pos: pairs[pairs.position == pos].reset_index(drop=True) for pos in ['QB','RB','WR','TE']}
LINEUP = [('QB',1),('RB',2),('WR',3),('TE',1)]
rng = np.random.default_rng(42)
NL, NT, WK = 4000, 12, 14
sides = np.array(['lo']*6 + ['hi']*6)
def build_team(side):
    out = []
    for pos, k in LINEUP:
        for _ in range(k):
            r = pools[pos].iloc[rng.integers(0, len(pools[pos]))]
            out.append(smap[(r[f'{side}_id'], r['season'])])
    return out
arrs = [[build_team(s) for s in sides] for _ in range(NL)]
TW = WK + 3
scores = np.zeros((NL, NT, TW))
for li in range(NL):
    for ti in range(NT):
        scores[li, ti] = sum(rng.choice(a, TW) for a in arrs[li][ti])
def rr_sched(n):
    ids = list(range(n)); out = []
    for _ in range(n-1):
        out.append([(ids[i], ids[n-1-i]) for i in range(n//2)])
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]
    return out
base_sched = rr_sched(NT); sched = [base_sched[w % len(base_sched)] for w in range(WK)]
wins = np.zeros((NL, NT)); pf = scores[:, :, :WK].sum(axis=2); h2h = h2h_lo = 0
for w, mus in enumerate(sched):
    for a, b in mus:
        wins[:, a] += scores[:, a, w] > scores[:, b, w]; wins[:, b] += scores[:, b, w] > scores[:, a, w]
        if sides[a] != sides[b]:
            i, j = (a, b) if sides[a] == 'lo' else (b, a)
            h2h += NL; h2h_lo += (scores[:, i, w] > scores[:, j, w]).sum()
rank = np.lexsort((-pf, -wins), axis=1)
champ = np.zeros(NT); playoff = np.zeros(NT)
for li in range(NL):
    s = rank[li]; playoff[s[:6]] += 1
    w1 = s[2] if scores[li, s[2], WK]   > scores[li, s[5], WK]   else s[5]
    w2 = s[3] if scores[li, s[3], WK]   > scores[li, s[4], WK]   else s[4]
    f1 = s[0] if scores[li, s[0], WK+1] > scores[li, w2,   WK+1] else w2
    f2 = s[1] if scores[li, s[1], WK+1] > scores[li, w1,   WK+1] else w1
    champ[f1 if scores[li, f1, WK+2] > scores[li, f2, WK+2] else f2] += 1
lo, hi = sides == 'lo', sides == 'hi'; n = NL*6
print(f"\n=== {NL} twelve-team leagues (6 consistent vs 6 boom/bust, mean-matched) ===")
print(f"  weekly H2H win rate      consistent {h2h_lo/h2h*100:.2f}%")
print(f"  regular-season wins      {wins[:,lo].mean():.2f} vs {wins[:,hi].mean():.2f}")
print(f"  points for               {pf[:,lo].mean():.1f} vs {pf[:,hi].mean():.1f}")
for lab, arr in [('made playoffs', playoff), ('WON THE TITLE', champ)]:
    p1, p2 = arr[lo].sum()/n, arr[hi].sum()/n
    se = np.sqrt(p1*(1-p1)/n + p2*(1-p2)/n)
    print(f"  {lab:24s} {p1*100:.2f}% vs {p2*100:.2f}%   gap {(p1-p2)*100:+.2f} pp "
          f"[{((p1-p2)-1.96*se)*100:+.2f}, {((p1-p2)+1.96*se)*100:+.2f}]")
