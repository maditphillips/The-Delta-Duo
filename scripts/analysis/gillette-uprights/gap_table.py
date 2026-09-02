import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
pd.set_option("display.width",200)
d=pd.read_parquet("kicks_2002_2025.parquet")
d["gillette"]=d.stadium_id.eq("BOS00"); d["is_home_kick"]=d.posteam.eq(d.home_team)
fg=d[d.field_goal_attempt.eq(1)&d.field_goal_result.notna()&d.kick_distance.between(15,75)].copy()
fg["made"]=fg.field_goal_result.eq("made").astype(int)
F=fg[fg.field_goal_result.ne("blocked")].copy()
F["xmake"]=smf.glm("made ~ bs(kick_distance,df=5)+C(season)",data=F[~F.gillette],
                   family=sm.families.Binomial()).fit().predict(F)

print("BASELINE: fit on", (~F.gillette).sum(), "kicks at all 30 non-Gillette venues.")
print("  It contains distance + season ONLY - no home/away term, no venue term.")
print("  So 'expected' = league-average make rate from that distance in that season,")
print("  pooling home and road kicks. League-wide it is calibrated by construction:")
tr=F[~F.gillette]; print(f"  non-Gillette actual {tr.made.mean():.3%} vs expected {tr.xmake.mean():.3%}")

rows=[]
for _,s in F.groupby("stadium_id"):
    h,a=s[s.is_home_kick],s[~s.is_home_kick]
    if len(h)<200 or len(a)<200: continue
    dh=h.made.mean()-h.xmake.mean(); da=a.made.mean()-a.xmake.mean()
    vh=(h.xmake*(1-h.xmake)).sum()/len(h)**2; va=(a.xmake*(1-a.xmake)).sum()/len(a)**2
    rows.append(dict(team=s.home_team.mode().iat[0], roof=s.roof.mode().iat[0],
        n_home=len(h), n_vis=len(a), home_fg=h.made.mean(), vis_fg=a.made.mean(),
        raw_gap=h.made.mean()-a.made.mean(), adj_gap=dh-da, z=(dh-da)/np.sqrt(vh+va),
        vis_pen=da, vis_z=da/np.sqrt(va)))
T=pd.DataFrame(rows).sort_values("adj_gap",ascending=False).reset_index(drop=True)
S=T.copy()
for c,f in [("home_fg","{:.1%}"),("vis_fg","{:.1%}"),("raw_gap","{:+.1f}pp"),
            ("adj_gap","{:+.1f}pp"),("z","{:+.2f}"),("vis_pen","{:+.1f}pp"),("vis_z","{:+.2f}")]:
    S[c]=T[c].map(lambda v,f=f: f.format(v*100 if 'pp' in f else v))
print("\n"+"="*95)
print("HOME-minus-VISITOR FG% GAP, ALL 29 VENUES 2002-2025 (adj = each side vs its own expectation)")
print("="*95)
print(S.to_string(index=False))

print("\n" + "-"*95)
print(f"mean adjusted gap across venues: {T.adj_gap.mean():+.1%}   sd {T.adj_gap.std():.1%}")
print(f"venues with a gap >= +3pp: {(T.adj_gap>=0.03).sum()} of {len(T)}   "
      f"<= -3pp: {(T.adj_gap<=-0.03).sum()}   between -2 and +2pp: {T.adj_gap.abs().le(0.02).sum()}")
print(f"NE: adjusted gap {T.loc[T.team=='NE','adj_gap'].iat[0]:+.1%}, rank {T.index[T.team=='NE'][0]+1} of {len(T)}")

print("\nIS *ANY* VENUE'S GAP REAL, OR IS THE WHOLE SPREAD SAMPLING NOISE?")
Q=(T.z**2).sum(); df=len(T)
print(f"  if every venue's true gap were zero, the 29 z-scores should be ~N(0,1)")
print(f"  observed: mean {T.z.mean():+.2f}, sd {T.z.std():.2f}, min {T.z.min():+.2f}, max {T.z.max():+.2f}")
print(f"  overdispersion test  sum(z^2)={Q:.1f} on {df} df  ->  p={stats.chi2.sf(Q,df):.3f}"
      f"  {'=> real venue-level gaps' if stats.chi2.sf(Q,df)<0.05 else '=> indistinguishable from pure noise'}")
zne=T.loc[T.team=='NE','z'].iat[0]; raw=stats.norm.sf(zne)
print(f"  NE gap z={zne:+.2f} raw one-sided p={raw:.3f}; expected max of 29 N(0,1) draws is ~+2.0")
print(f"  P(at least one of 29 venues shows a gap this big by chance) = {1-(1-raw)**29:.2f}")

print("\nSAME TEST FOR THE VISITOR PENALTY (the statistic that DOES hold up):")
Qv=(T.vis_z**2).sum()
print(f"  observed: mean {T.vis_z.mean():+.2f}, sd {T.vis_z.std():.2f}, min {T.vis_z.min():+.2f}")
print(f"  overdispersion  sum(z^2)={Qv:.1f} on {df} df  ->  p={stats.chi2.sf(Qv,df):.4f}"
      f"  {'=> venues really do differ' if stats.chi2.sf(Qv,df)<0.05 else '=> noise'}")
zv=T.loc[T.team=='NE','vis_z'].iat[0]; rawv=stats.norm.cdf(zv)
print(f"  NE visitor-penalty z={zv:+.2f}; P(at least one of 29 this bad by chance) = {1-(1-rawv)**29:.4f}")
