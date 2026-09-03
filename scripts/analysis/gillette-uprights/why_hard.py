"""Why is Gillette hard to kick at? Probes that have nothing to do with uprights."""
import warnings, re; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
pd.set_option("display.width",210)

K=pd.read_parquet("kicks_2002_2025.parquet")
P=pd.read_parquet("punts_2002_2025.parquet")
for df in (K,P):
    df["gillette"]=df.stadium_id.eq("BOS00")
    df["is_home_kick"]=df.posteam.eq(df.home_team)
def hdr(t): print("\n"+"="*80+f"\n{t}\n"+"="*80)

fg=K[K.field_goal_attempt.eq(1)&K.field_goal_result.notna()&K.kick_distance.between(15,75)].copy()
fg["made"]=fg.field_goal_result.eq("made").astype(int)
F=fg[fg.field_goal_result.ne("blocked")].copy()
F["xmake"]=smf.glm("made ~ bs(kick_distance,df=5)+C(season)",data=F[~F.gillette],
                   family=sm.families.Binomial()).fit().predict(F)
def oe(s):
    if len(s)==0: return 0,np.nan,np.nan,np.nan
    var=(s.xmake*(1-s.xmake)).sum()
    return len(s), s.made.mean(), s.made.mean()-s.xmake.mean(), (s.made.sum()-s.xmake.sum())/np.sqrt(var)

hdr("1. PUNTS - a pure air/aerodynamics probe. No uprights, no board, no aiming.")
pu=P[P.punt_attempt.eq(1)&P.kick_distance.notna()&P.kick_distance.between(15,80)
     &P.punt_blocked.ne(1)&P.yardline_100.notna()].copy()
pu["ylb"]=pd.cut(pu.yardline_100.astype(float),bins=range(0,101,5),include_lowest=True).astype(str)
pu["oob"]=pu.punt_out_of_bounds.eq(1).astype(int)
# gross punt distance, controlling for field position (punters shorten near the goal line)
pm=smf.ols("kick_distance ~ C(ylb)+C(season)",data=pu[~pu.gillette]).fit()
pu["xdist"]=pm.predict(pu)
print(f"sample {len(pu):,} punts ({pu.gillette.sum():,} at Gillette)")
rows=[]
for _,s in pu.groupby("stadium_id"):
    if len(s)<400: continue
    rows.append(dict(team=s.home_team.mode().iat[0],roof=s.roof.mode().iat[0],n=len(s),
                     gross=s.kick_distance.mean(),vs_exp=(s.kick_distance-s.xdist).mean()))
T=pd.DataFrame(rows).sort_values("vs_exp")
print("\nGROSS PUNT DISTANCE vs expectation, all venues (shortest = heaviest air / worst conditions):")
for i,(_,r) in enumerate(T.iterrows(),1):
    mark=" <<<< GILLETTE" if r.team=="NE" else ""
    if i<=8 or i>len(T)-4 or r.team=="NE":
        print(f"  {i:>2}. {r.team:<4} {r.roof:<9} n={int(r.n):>5}  gross {r.gross:.1f} yds  vs exp {r.vs_exp:+.2f}{mark}")
    elif i==9: print("      ...")
ne=T[T.team=='NE'].iloc[0]
print(f"\n  Gillette punt rank: {list(T.team).index('NE')+1} of {len(T)}  ({ne.vs_exp:+.2f} yds vs expectation)")
print(f"  spread across venues: sd {T.vs_exp.std():.2f} yds; Gillette is {(ne.vs_exp-T.vs_exp.mean())/T.vs_exp.std():+.1f} sd")
g=pu[pu.gillette]
print(f"  Gillette punts out of bounds {g.oob.mean():.1%} vs {pu[~pu.gillette].oob.mean():.1%} elsewhere "
      f"(a wind-fighting tell)")

hdr("2. KICKOFFS - the other pure ball-flight probe (2011-2023, 35-yd tee era)")
ko=P[P.kickoff_attempt.eq(1)&P.season.between(2011,2023)].copy()
ko["tb"]=ko.touchback.eq(1).astype(int)
rows=[]
for _,s in ko.groupby("stadium_id"):
    if len(s)<300: continue
    rows.append(dict(team=s.home_team.mode().iat[0],roof=s.roof.mode().iat[0],n=len(s),tb=s.tb.mean()))
T2=pd.DataFrame(rows).sort_values("tb")
print("TOUCHBACK RATE by venue (low = ball not carrying):")
for i,(_,r) in enumerate(T2.iterrows(),1):
    if i<=6 or r.team=="NE" or i>len(T2)-3:
        print(f"  {i:>2}. {r.team:<4} {r.roof:<9} n={int(r.n):>5}  TB {r.tb:.1%}"
              + ("  <<<< GILLETTE" if r.team=="NE" else ""))
    elif i==7: print("      ...")
print(f"\n  Gillette touchback rank: {list(T2.team).index('NE')+1} of {len(T2)} (1 = lowest)")

hdr("3. IS GILLETTE MORE WIND-SENSITIVE THAN OTHER STADIUMS?")
W=F.copy(); W["wnd"]=pd.to_numeric(W.wind,errors="coerce"); W["tmp"]=pd.to_numeric(W.temp,errors="coerce")
W=W.dropna(subset=["wnd"]); W=W[W.wnd.between(0,40)&W.roof.eq("outdoors")]
print("FG% vs expectation by recorded wind speed:")
print(f"  {'wind':<12}{'Gillette':>26}{'other outdoor venues':>28}")
for lo,hi,lab in [(0,5,"0-5 mph"),(6,9,"6-9 mph"),(10,14,"10-14 mph"),(15,40,"15+ mph")]:
    a=W[W.gillette&W.wnd.between(lo,hi)]; b=W[~W.gillette&W.wnd.between(lo,hi)]
    print(f"  {lab:<12}{oe(a)[2]:+.1%} (n={len(a):>3}){'':>10}{oe(b)[2]:+.1%} (n={len(b):>5})")
r=smf.glm("made ~ bs(kick_distance,df=5)+C(season)+wnd*gillette",data=W,
          family=sm.families.Binomial()).fit(cov_type="cluster",cov_kwds={"groups":W.game_id})
k=[t for t in r.params.index if "wnd" in t and "gillette" in t.lower()][0]
print(f"\n  wind x Gillette interaction: beta={r.params[k]:+.4f} per mph  p={r.pvalues[k]:.3f}")
print(f"  baseline wind effect: {r.params['wnd']:+.4f} per mph (p={r.pvalues['wnd']:.3f})")

hdr("4. SURFACE BREAK: Gillette was natural grass 2002-2005, FieldTurf from 2006")
print("  recorded surface at Gillette by season:")
sur=K[K.gillette].groupby("season").surface.agg(lambda s: s.mode().iat[0] if len(s.mode()) else "?")
print("   "+"  ".join(f"{i}:{v}" for i,v in sur.items()))
v=F[F.gillette&~F.is_home_kick]
for lo,hi,lab in [(2002,2005,"grass 2002-2005"),(2006,2025,"turf 2006-2025")]:
    n,a,dd,z=oe(v[v.season.between(lo,hi)])
    print(f"  visiting kickers, {lab:<20} n={n:>3}  act {a:6.1%}  vs exp {dd:+6.1%}  z={z:+.2f}")

hdr("5. GUST & WIND-DIRECTION DETAIL from the weather string")
wx=K[K.gillette].drop_duplicates("game_id")[["game_id","season","weather","wind","temp"]].copy()
wx["gust"]=wx.weather.str.extract(r"gusts? (?:to|up to) (\d+)",flags=re.I)[0].astype(float)
wx["dir"]=wx.weather.str.extract(r"Wind:?\s*([A-Za-z ]+?)\s*\d",flags=re.I)[0].str.strip().str.upper()
allwx=K.drop_duplicates("game_id")[["game_id","stadium_id","weather","roof"]].copy()
allwx["gust"]=allwx.weather.str.extract(r"gusts? (?:to|up to) (\d+)",flags=re.I)[0].astype(float)
out=allwx[allwx.roof.eq("outdoors")]
gr=out.groupby("stadium_id").apply(lambda s: pd.Series({
    "team":K[K.stadium_id.eq(s.name)].home_team.mode().iat[0],"games":len(s),
    "gust_mentioned":s.gust.notna().mean(),"mean_gust":s.gust.mean()}))
gr=gr[gr.games>=80].sort_values("gust_mentioned",ascending=False)
print("share of games whose weather string mentions GUSTS (outdoor venues, >=80 games):")
for i,(_,r) in enumerate(gr.iterrows(),1):
    if i<=6 or r.team=="NE" or i>len(gr)-2:
        print(f"  {i:>2}. {r.team:<4} {int(r.games):>4} games  gusts mentioned {r.gust_mentioned:.1%}  mean gust {r.mean_gust:.0f} mph"
              + ("  <<<< GILLETTE" if r.team=="NE" else ""))
    elif i==7: print("      ...")
print(f"\n  Gillette gust-mention rank: {list(gr.team).index('NE')+1} of {len(gr)}")
print(f"\n  wind direction at Gillette games: {wx.dir.value_counts().head(8).to_dict()}")

hdr("6. DOES THE PENALTY LAND ON ONE HALF OF THE GAME? (ends flip at the quarter)")
for q,lab in [([1,3],"Q1+Q3 (one direction)"),([2,4],"Q2+Q4 (the other)")]:
    n,a,dd,z=oe(v[v.qtr.isin(q)])
    print(f"  visitors, {lab:<26} n={n:>3}  act {a:6.1%}  vs exp {dd:+6.1%}  z={z:+.2f}")
h=F[F.gillette&F.is_home_kick]
for q,lab in [([1,3],"Q1+Q3"),([2,4],"Q2+Q4")]:
    n,a,dd,z=oe(h[h.qtr.isin(q)])
    print(f"  Patriots, {lab:<26} n={n:>3}  act {a:6.1%}  vs exp {dd:+6.1%}  z={z:+.2f}")
