import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
pd.set_option("display.width",210)
D=pd.read_parquet("fourth_2002_2025.parquet")
D["gillette"]=D.stadium_id.eq("BOS00"); D["is_home"]=D.posteam.eq(D.home_team)
D["parity"]=np.where(D.qtr.isin([1,3]),"Q1+Q3","Q2+Q4")
D=D[D.yardline_100.notna()&D.play_type.notna()&D.qtr.le(4)].copy()
D["fga"]=D.field_goal_attempt.eq(1).astype(int)
D["fg_dist"]=D.yardline_100+17
# "kickable but optional": 4th down, FG would be 40-59 yds, not garbage time
S=D[D.fg_dist.between(40,59)&D.ydstogo.between(1,10)&D.wp.between(0.05,0.95)].copy()
def hdr(t): print("\n"+"="*80+f"\n{t}\n"+"="*80)
hdr("FG ATTEMPT RATE ON 4th DOWN FROM 40-59 YD FG RANGE (competitive situations)")
def row(s,lab):
    print(f"  {lab:<44} n={len(s):>5}  kicked {s.fga.mean():6.1%}  mean FG dist if kicked "
          f"{s[s.fga.eq(1)].fg_dist.mean():.1f}")
row(S[S.gillette&S.is_home],"New England at Gillette")
row(S[S.gillette&~S.is_home],"Visitors at Gillette")
row(S[~S.gillette&S.posteam.eq('NE')],"New England on the road")
row(S[~S.gillette&S.is_home],"All home teams, other stadiums")
row(S[~S.gillette&~S.is_home],"All road teams, other stadiums")
a=S[S.gillette&S.is_home].fga; b=S[~S.gillette&S.posteam.eq('NE')].fga
print(f"\n  NE home vs NE road attempt rate: {a.mean():.1%} vs {b.mean():.1%}  "
      f"diff {a.mean()-b.mean():+.1%}  (chi2 p={stats.chi2_contingency([[a.sum(),len(a)-a.sum()],[b.sum(),len(b)-b.sum()]])[1]:.3f})")
c=S[S.gillette&~S.is_home].fga
print(f"  At Gillette, NE kicked {a.mean():.1%} of these vs visitors {c.mean():.1%}  "
      f"(chi2 p={stats.chi2_contingency([[a.sum(),len(a)-a.sum()],[c.sum(),len(c)-c.sum()]])[1]:.3f})")

hdr("BY DIRECTION OF PLAY AT GILLETTE - did NE avoid kicking one way?")
for who,mask in [("New England",S.is_home),("Visitors",~S.is_home)]:
    for p in ["Q1+Q3","Q2+Q4"]:
        s=S[S.gillette&mask&S.parity.eq(p)]
        print(f"  {who:<12} {p}  n={len(s):>4}  kicked {s.fga.mean():6.1%}")
for p in ["Q1+Q3","Q2+Q4"]:
    s=S[~S.gillette&S.parity.eq(p)]
    print(f"  {'league':<12} {p}  n={len(s):>5}  kicked {s.fga.mean():6.1%}")

hdr("THE LONG END OF THE RANGE: 4th down, FG would be 50+ yds")
L=D[D.fg_dist.between(50,62)&D.ydstogo.between(1,10)&D.wp.between(0.05,0.95)]
row(L[L.gillette&L.is_home],"New England at Gillette")
row(L[L.gillette&~L.is_home],"Visitors at Gillette")
row(L[~L.gillette&L.posteam.eq('NE')],"New England on the road")
row(L[~L.gillette&L.is_home],"All home teams, other stadiums")

hdr("SIGNIFICANCE OF THE 50+ DECISION GAP (within-team controls)")
def cmp(a,b,la,lb):
    ta=[a.fga.sum(),len(a)-a.fga.sum()]; tb=[b.fga.sum(),len(b)-b.fga.sum()]
    p=stats.fisher_exact([ta,tb])[1]
    print(f"  {la:<34} {a.fga.mean():5.1%} (n={len(a):>4})  vs  {lb:<30} {b.fga.mean():5.1%} (n={len(b):>4})   Fisher p={p:.4f}")
neH=L[L.gillette&L.is_home]; neR=L[~L.gillette&L.posteam.eq('NE')]
visG=L[L.gillette&~L.is_home]; lgH=L[~L.gillette&L.is_home]
cmp(neH,neR,"NE at Gillette, 50+ available","NE on the road")
cmp(neH,visG,"NE at Gillette","visitors at Gillette")
cmp(neH,lgH,"NE at Gillette","all home teams elsewhere")
cmp(visG,lgH,"visitors at Gillette","all home teams elsewhere")
T=L[L.gillette&L.is_home&L.score_differential.abs().le(8)]
T2=L[~L.gillette&L.posteam.eq('NE')&L.score_differential.abs().le(8)]
cmp(T,T2,"NE at Gillette (within 8 pts)","NE on road (within 8)")
