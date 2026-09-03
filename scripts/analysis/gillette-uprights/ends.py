import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
pd.set_option("display.width",210)
P=pd.read_parquet("punts_2002_2025.parquet"); K=pd.read_parquet("kicks_2002_2025.parquet")
for df in (P,K):
    df["gillette"]=df.stadium_id.eq("BOS00"); df["is_home_kick"]=df.posteam.eq(df.home_team)
    df["parity"]=np.where(df.qtr.isin([1,3]),"Q1+Q3","Q2+Q4")
def hdr(t): print("\n"+"="*82+f"\n{t}\n"+"="*82)

hdr("1. PUNT DISTANCE BY DIRECTION OF PLAY - 1,869 punts at Gillette")
pu=P[P.punt_attempt.eq(1)&P.kick_distance.notna()&P.kick_distance.between(15,80)
     &P.punt_blocked.ne(1)&P.yardline_100.notna()&P.qtr.le(4)].copy()
pu["ylb"]=pd.cut(pu.yardline_100.astype(float),bins=range(0,101,5),include_lowest=True).astype(str)
pu["xd"]=smf.ols("kick_distance ~ C(ylb)+C(season)",data=pu[~pu.gillette]).fit().predict(pu)
pu["oe"]=pu.kick_distance-pu.xd
def pline(s,lab):
    t=stats.ttest_1samp(s.oe,0) if len(s)>5 else None
    print(f"  {lab:<42} n={len(s):>5}  gross {s.kick_distance.mean():5.1f}  vs exp {s.oe.mean():+5.2f} yds"
          + (f"  p={t.pvalue:.3f}" if t is not None else ""))
for p in ["Q1+Q3","Q2+Q4"]:
    pline(pu[pu.gillette&pu.parity.eq(p)], f"GILLETTE, all punts, {p}")
print()
for who,mask in [("visiting punters",~pu.is_home_kick),("Patriots punters",pu.is_home_kick)]:
    for p in ["Q1+Q3","Q2+Q4"]:
        pline(pu[pu.gillette&mask&pu.parity.eq(p)], f"Gillette, {who}, {p}")
print()
for p in ["Q1+Q3","Q2+Q4"]:
    pline(pu[~pu.gillette&pu.roof.eq("outdoors")&pu.parity.eq(p)], f"ALL OTHER outdoor venues, {p}")
gA=pu[pu.gillette&pu.parity.eq("Q1+Q3")].oe; gB=pu[pu.gillette&pu.parity.eq("Q2+Q4")].oe
print(f"\n  Gillette Q1+Q3 minus Q2+Q4 = {gA.mean()-gB.mean():+.2f} yds  "
      f"(Welch p={stats.ttest_ind(gA,gB,equal_var=False).pvalue:.4f})")
oA=pu[~pu.gillette&pu.roof.eq('outdoors')&pu.parity.eq("Q1+Q3")].oe
oB=pu[~pu.gillette&pu.roof.eq('outdoors')&pu.parity.eq("Q2+Q4")].oe
print(f"  same split at other outdoor venues = {oA.mean()-oB.mean():+.2f} yds  "
      f"(p={stats.ttest_ind(oA,oB,equal_var=False).pvalue:.3f})")

hdr("2. IS THE PUNT PARITY GAP UNUSUAL? all outdoor venues ranked")
rows=[]
for sid,s in pu[pu.roof.eq("outdoors")].groupby("stadium_id"):
    a,b=s[s.parity.eq("Q1+Q3")].oe, s[s.parity.eq("Q2+Q4")].oe
    if len(a)<200 or len(b)<200: continue
    rows.append(dict(team=K[K.stadium_id.eq(sid)].home_team.mode().iat[0],n=len(s),
                     gap=a.mean()-b.mean(),p=stats.ttest_ind(a,b,equal_var=False).pvalue))
T=pd.DataFrame(rows).reindex(pd.DataFrame(rows).gap.abs().sort_values(ascending=False).index)
for i,(_,r) in enumerate(T.iterrows(),1):
    if i<=6 or r.team=="NE":
        print(f"  {i:>2}. {r.team:<4} n={int(r.n):>5}  |Q1+Q3 - Q2+Q4| = {r.gap:+.2f} yds  p={r.p:.3f}"
              + ("  <<<< GILLETTE" if r.team=="NE" else ""))
    elif i==7: print("      ...")
print(f"\n  Gillette rank by size of directional punt gap: {list(T.team).index('NE')+1} of {len(T)}")

hdr("3. KICKOFF DISTANCE BY DIRECTION (2011-2023, fixed 35-yd tee)")
ko=P[P.kickoff_attempt.eq(1)&P.season.between(2011,2023)&P.kick_distance.notna()
     &P.kick_distance.between(40,80)&P.qtr.le(4)].copy()
ko["xd"]=smf.ols("kick_distance ~ C(season)",data=ko[~ko.gillette]).fit().predict(ko)
ko["oe"]=ko.kick_distance-ko.xd
for p in ["Q1+Q3","Q2+Q4"]:
    s=ko[ko.gillette&ko.parity.eq(p)]
    print(f"  GILLETTE {p}  n={len(s):>4}  mean {s.kick_distance.mean():.1f} yds  vs exp {s.oe.mean():+.2f}")
for p in ["Q1+Q3","Q2+Q4"]:
    s=ko[~ko.gillette&ko.roof.eq("outdoors")&ko.parity.eq(p)]
    print(f"  other outdoor {p}  n={len(s):>5}  mean {s.kick_distance.mean():.1f} yds  vs exp {s.oe.mean():+.2f}")

hdr("4. EXTRA POINTS BY DIRECTION AT GILLETTE (33 yds, dead centre, 2015-2025)")
xp=K[K.extra_point_attempt.eq(1)&K.extra_point_result.isin(["good","failed"])&K.season.ge(2015)&K.qtr.le(4)].copy()
xp["made"]=xp.extra_point_result.eq("good").astype(int)
lg=xp[~xp.gillette].made.mean()
for who,mask in [("visitors",~xp.is_home_kick),("Patriots",xp.is_home_kick)]:
    for p in ["Q1+Q3","Q2+Q4"]:
        s=xp[xp.gillette&mask&xp.parity.eq(p)]
        print(f"  Gillette {who:<9} {p}  n={len(s):>4}  {s.made.mean():6.2%}  vs league {lg:.2%}  "
              f"diff {s.made.mean()-lg:+.2%}")

hdr("5. DID NEW ENGLAND SIMPLY TAKE SHORTER KICKS AT HOME?")
fg=K[K.field_goal_attempt.eq(1)&K.field_goal_result.notna()&K.kick_distance.between(15,75)
     &K.field_goal_result.ne("blocked")].copy()
ne=fg[fg.posteam.eq("NE")]
print(f"  NE attempts at Gillette      n={len(ne[ne.gillette]):>4}  mean {ne[ne.gillette].kick_distance.mean():.1f} yds"
      f"  share 40+ {ne[ne.gillette].kick_distance.ge(40).mean():.0%}")
print(f"  NE attempts on the road      n={len(ne[~ne.gillette]):>4}  mean {ne[~ne.gillette].kick_distance.mean():.1f} yds"
      f"  share 40+ {ne[~ne.gillette].kick_distance.ge(40).mean():.0%}")
oth=fg[~fg.posteam.eq("NE")]
oh,oa=oth[oth.is_home_kick],oth[~oth.is_home_kick]
print(f"  league, home attempts        n={len(oh):>5}  mean {oh.kick_distance.mean():.1f} yds  share 40+ {oh.kick_distance.ge(40).mean():.0%}")
print(f"  league, road attempts        n={len(oa):>5}  mean {oa.kick_distance.mean():.1f} yds  share 40+ {oa.kick_distance.ge(40).mean():.0%}")
vis=fg[fg.gillette&~fg.is_home_kick]
print(f"  visitors AT Gillette         n={len(vis):>4}  mean {vis.kick_distance.mean():.1f} yds  share 40+ {vis.kick_distance.ge(40).mean():.0%}")
print(f"\n  NE home-minus-road shift: {ne[ne.gillette].kick_distance.mean()-ne[~ne.gillette].kick_distance.mean():+.1f} yds")
print(f"  league home-minus-road shift: {oh.kick_distance.mean()-oa.kick_distance.mean():+.1f} yds")
