import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
pd.set_option("display.width",210)
K=pd.read_parquet("kicks_2002_2025.parquet")
K["gillette"]=K.stadium_id.eq("BOS00"); K["is_home_kick"]=K.posteam.eq(K.home_team)
fg=K[K.field_goal_attempt.eq(1)&K.field_goal_result.notna()&K.kick_distance.between(15,75)].copy()
fg["made"]=fg.field_goal_result.eq("made").astype(int)
F=fg[fg.field_goal_result.ne("blocked")].copy()
F["xmake"]=smf.glm("made ~ bs(kick_distance,df=5)+C(season)",data=F[~F.gillette],
                   family=sm.families.Binomial()).fit().predict(F)
F["parity"]=np.where(F.qtr.isin([1,3]),"Q1+Q3","Q2+Q4")
F=F[F.qtr.le(4)]
def oe(s):
    if len(s)==0: return 0,np.nan,np.nan,np.nan
    var=(s.xmake*(1-s.xmake)).sum()
    return len(s), s.made.mean(), s.made.mean()-s.xmake.mean(), (s.made.sum()-s.xmake.sum())/np.sqrt(var)
def hdr(t): print("\n"+"="*80+f"\n{t}\n"+"="*80)

hdr("CONTROL: is Q2+Q4 harder EVERYWHERE, or only for visitors at Gillette?")
print(f"{'group':<40}{'Q1+Q3':>22}{'Q2+Q4':>22}   split")
for lab,s in [("Visitors at GILLETTE",F[F.gillette&~F.is_home_kick]),
              ("Patriots at GILLETTE",F[F.gillette&F.is_home_kick]),
              ("Visitors, all other stadiums",F[~F.gillette&~F.is_home_kick]),
              ("Home teams, all other stadiums",F[~F.gillette&F.is_home_kick]),
              ("Visitors, other cold outdoor (CHI/GB/BUF/CLE/PIT/NYJ/NYG/WAS)",
               F[~F.gillette&~F.is_home_kick&F.home_team.isin(['CHI','GB','BUF','CLE','PIT','NYJ','NYG','WAS'])])]:
    a=oe(s[s.parity.eq("Q1+Q3")]); b=oe(s[s.parity.eq("Q2+Q4")])
    print(f"{lab:<40}{a[2]:+7.1%} (n={a[0]:>4}){'':>4}{b[2]:+7.1%} (n={b[0]:>4}){'':>4}{b[2]-a[2]:+.1%}")

hdr("FORMAL: Gillette x visitor x quarter-parity, clustered by game")
F["G"]=F.gillette.astype(int); F["V"]=(~F.is_home_kick).astype(int); F["P24"]=F.parity.eq("Q2+Q4").astype(int)
r=smf.glm("made ~ bs(kick_distance,df=5)+C(season)+G*V*P24",data=F,
          family=sm.families.Binomial()).fit(cov_type="cluster",cov_kwds={"groups":F.game_id})
for t in [x for x in r.params.index if set(x.split(":"))<= {"G","V","P24"} and x!="Intercept"]:
    print(f"  {t:<16} beta={r.params[t]:+.3f}  se={r.bse[t]:.3f}  p={r.pvalues[t]:.3f}")
# visitor-at-Gillette in Q2+Q4 = G + G:V + G:P24 + G:V:P24
terms=["G","G:V","G:P24","G:V:P24"]
b=sum(r.params[t] for t in terms)
se=np.sqrt(r.cov_params().loc[terms,terms].values.sum())
print(f"\n  TOTAL visitor-at-Gillette-in-Q2+Q4 effect: beta={b:+.3f} se={se:.3f} p={2*(1-stats.norm.cdf(abs(b/se))):.4f}")
terms2=["G","G:V"]
b2=sum(r.params[t] for t in terms2); se2=np.sqrt(r.cov_params().loc[terms2,terms2].values.sum())
print(f"  TOTAL visitor-at-Gillette-in-Q1+Q3 effect: beta={b2:+.3f} se={se2:.3f} p={2*(1-stats.norm.cdf(abs(b2/se2))):.4f}")

hdr("QUARTER BY QUARTER, visitors at Gillette")
for q in [1,2,3,4]:
    n,a,dd,z=oe(F[F.gillette&~F.is_home_kick&F.qtr.eq(q)])
    print(f"  Q{q}  n={n:>3}  act {a:6.1%}  vs exp {dd:+6.1%}  z={z:+.2f}")

hdr("IS IT CLOCK PRESSURE? attempt profiles at Gillette by parity")
g=F[F.gillette]
for lab,s in [("Visitors",g[~g.is_home_kick]),("Patriots",g[g.is_home_kick])]:
    for p in ["Q1+Q3","Q2+Q4"]:
        x=s[s.parity.eq(p)]
        print(f"  {lab:<9} {p}  n={len(x):>3}  mean dist {x.kick_distance.mean():.1f}  "
              f"share 40+ {x.kick_distance.ge(40).mean():.0%}  "
              f"mean secs left in half {x.game_seconds_remaining.mean():.0f}")

hdr("DOES THE PARITY SPLIT HOLD ACROSS ERAS? (visitors at Gillette)")
for lo,hi,lab in [(2002,2009,"2002-09"),(2010,2022,"2010-22"),(2023,2025,"2023-25 new board")]:
    s=F[F.gillette&~F.is_home_kick&F.season.between(lo,hi)]
    a=oe(s[s.parity.eq("Q1+Q3")]); b=oe(s[s.parity.eq("Q2+Q4")])
    print(f"  {lab:<20} Q1+Q3 {a[2]:+6.1%} (n={a[0]:>3})   Q2+Q4 {b[2]:+6.1%} (n={b[0]:>3})   split {b[2]-a[2]:+.1%}")

hdr("SURFACE: the two later grass years")
v=F[F.gillette&~F.is_home_kick]
for yrs,lab in [([2002,2003,2004,2005],"grass 2002-05"),([2019,2020],"grass 2019-20"),
                (list(range(2006,2019))+list(range(2021,2026)),"fieldturf years")]:
    n,a,dd,z=oe(v[v.season.isin(yrs)])
    print(f"  {lab:<18} n={n:>3}  act {a:6.1%}  vs exp {dd:+6.1%}  z={z:+.2f}")

hdr("SAME-GAME PAIRED TEST: both kickers, same day, same weather")
rows=[]
for gid,s in F[F.gillette].groupby("game_id"):
    hh,aa=s[s.is_home_kick],s[~s.is_home_kick]
    if len(hh)==0 or len(aa)==0: continue
    rows.append(dict(game=gid,ne_oe=(hh.made-hh.xmake).mean(),vis=(aa.made-aa.xmake).mean(),
                     w=min(len(hh),len(aa))))
D=pd.DataFrame(rows); D["diff"]=D.ne_oe-D.vis
print(f"  {len(D)} Gillette games where both teams attempted a FG")
print(f"  mean(NE over/under) - mean(visitor over/under) = {D['diff'].mean():+.1%}")
t=stats.ttest_1samp(D['diff'],0); print(f"  paired t-test p={t.pvalue:.4f}")
print(f"  NE beat the visitor in {(D['diff']>0).sum()} games, lost in {(D['diff']<0).sum()}, tied {(D['diff']==0).sum()}")
