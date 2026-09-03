"""Run the Gillette battery against any venue.

    python3 venue_profile.py NYC01     # MetLife Stadium
    python3 venue_profile.py BOS00     # Gillette

The expected-make baseline is refit each time EXCLUDING the target venue, so
the venue is always scored against the rest of the league.
"""
import sys, re, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
pd.set_option("display.width",210)

SID = sys.argv[1] if len(sys.argv)>1 else "NYC01"
K=pd.read_parquet("kicks_2002_2025.parquet"); P=pd.read_parquet("punts_2002_2025.parquet")
D=pd.read_parquet("fourth_2002_2025.parquet")
for df in (K,P,D):
    df["tgt"]=df.stadium_id.eq(SID); df["is_home_kick"]=df.posteam.eq(df.home_team)
    df["parity"]=np.where(df.qtr.isin([1,3]),"Q1+Q3","Q2+Q4")
NAME=K[K.tgt].stadium.mode().iat[0]; HOSTS=sorted(K[K.tgt].home_team.unique())
YRS=(K[K.tgt].season.min(),K[K.tgt].season.max())
# the venue's resident team(s): hosts with >=20 home games there
cnt=K[K.tgt].drop_duplicates("game_id").home_team.value_counts()
RES=sorted(cnt[cnt>=20].index)
def hdr(t): print("\n"+"="*82+f"\n{t}\n"+"="*82)
print(f"VENUE PROFILE: {NAME} ({SID}), {YRS[0]}-{YRS[1]}, resident team(s) {RES}")

fg=K[K.field_goal_attempt.eq(1)&K.field_goal_result.notna()&K.kick_distance.between(15,75)].copy()
fg["made"]=fg.field_goal_result.eq("made").astype(int)
F=fg[fg.field_goal_result.ne("blocked")].copy()
F["xmake"]=smf.glm("made ~ bs(kick_distance,df=5)+C(season)",data=F[~F.tgt],
                   family=sm.families.Binomial()).fit().predict(F)
def oe(s):
    if len(s)==0: return 0,np.nan,np.nan,np.nan
    v=(s.xmake*(1-s.xmake)).sum()
    return len(s), s.made.mean(), s.made.mean()-s.xmake.mean(), (s.made.sum()-s.xmake.sum())/np.sqrt(v)
def line(s,lab):
    n,a,d,z=oe(s); p=2*(1-stats.norm.cdf(abs(z))) if n else np.nan
    print(f"  {lab:<40} n={n:>5}  act {a:6.2%}  exp {a-d:6.2%}  diff {d:+6.2%}  z={z:+5.2f}  p={p:.3f}")

hdr("1. HEADLINE")
line(F[F.tgt&~F.is_home_kick], "Visiting kickers")
line(F[F.tgt&F.is_home_kick],  "Home kickers")
for t in RES:
    line(F[F.tgt&F.posteam.eq(t)], f"  {t} kickers here")
    line(F[~F.tgt&F.posteam.eq(t)], f"  {t} kickers everywhere else")

hdr("2. RANK AMONG VENUES (2002-2025, >=200 visiting-kicker FGs)")
rows=[]
for sid,s in F.groupby("stadium_id"):
    h,a=s[s.is_home_kick],s[~s.is_home_kick]
    if len(h)<200 or len(a)<200: continue
    dh,da=h.made.mean()-h.xmake.mean(), a.made.mean()-a.xmake.mean()
    vh=(h.xmake*(1-h.xmake)).sum()/len(h)**2; va=(a.xmake*(1-a.xmake)).sum()/len(a)**2
    rows.append(dict(sid=sid,team=s.stadium.mode().iat[0][:22],
                     roof=s.roof.mode().iat[0],n=len(a),vis=da,vz=oe(a)[3],gap=dh-da,gz=(dh-da)/np.sqrt(vh+va)))
T=pd.DataFrame(rows).sort_values("vis")
print("  hardest venues for VISITING kickers:")
for i,(_,r) in enumerate(T.iterrows(),1):
    if i<=8 or r.sid==SID:
        print(f"   {i:>2}. {r.team:<24} {r.roof:<9} n={int(r.n):>4}  {r.vis:+.1%}  z={r.vz:+.2f}"
              + ("   <<<< THIS VENUE" if r.sid==SID else ""))
    elif i==9: print("       ...")
tgt=T[T.sid.eq(SID)]
if len(tgt):
    r=tgt.iloc[0]
    print(f"\n  visiting-kicker penalty: rank {list(T.sid).index(SID)+1} of {len(T)}   ({r.vis:+.1%}, z={r.vz:+.2f})")
    G=T.sort_values("gap",ascending=False)
    print(f"  home-minus-visitor gap:  rank {list(G.sid).index(SID)+1} of {len(G)}   ({r.gap:+.1%}, z={r.gz:+.2f})")
    raw=stats.norm.sf(abs(r.vz))*2
    print(f"  Bonferroni across {len(T)} venues: p={min(1,raw*len(T)):.3f}"
          f"  {'SURVIVES' if raw*len(T)<0.05 else 'does not survive'}")

hdr("3. DIRECTION OF PLAY (ends flip each quarter)")
print(f"  {'group':<38}{'Q1+Q3':>20}{'Q2+Q4':>20}   split")
for lab,s in [("Visitors here",F[F.tgt&~F.is_home_kick]),("Home kickers here",F[F.tgt&F.is_home_kick]),
              ("Visitors, all other stadiums",F[~F.tgt&~F.is_home_kick])]:
    a=oe(s[s.parity.eq("Q1+Q3")]); b=oe(s[s.parity.eq("Q2+Q4")])
    print(f"  {lab:<38}{a[2]:+7.1%} (n={a[0]:>4}){'':>2}{b[2]:+7.1%} (n={b[0]:>4}){'':>2}{b[2]-a[2]:+.1%}")

hdr("4. PUNTS - pure ball-flight probe")
pu=P[P.punt_attempt.eq(1)&P.kick_distance.between(15,80)&P.punt_blocked.ne(1)
     &P.yardline_100.notna()&P.qtr.le(4)].copy()
pu["ylb"]=pd.cut(pu.yardline_100.astype(float),bins=range(0,101,5),include_lowest=True).astype(str)
pu["oe"]=pu.kick_distance-smf.ols("kick_distance ~ C(ylb)+C(season)",data=pu[~pu.tgt]).fit().predict(pu)
rows=[]
for sid,s in pu.groupby("stadium_id"):
    if len(s)<400: continue
    rows.append(dict(sid=sid,team=s.stadium.mode().iat[0][:22],
                     roof=s.roof.mode().iat[0],n=len(s),oe=s.oe.mean()))
TP=pd.DataFrame(rows).sort_values("oe")
for i,(_,r) in enumerate(TP.iterrows(),1):
    if i<=6 or r.sid==SID:
        print(f"   {i:>2}. {r.team:<24} {r.roof:<9} n={int(r.n):>5}  {r.oe:+.2f} yds vs exp"
              + ("   <<<< THIS VENUE" if r.sid==SID else ""))
    elif i==7: print("       ...")
if SID in set(TP.sid): print(f"\n  punt rank: {list(TP.sid).index(SID)+1} of {len(TP)} (1 = shortest punts)")
for p in ["Q1+Q3","Q2+Q4"]:
    s=pu[pu.tgt&pu.parity.eq(p)]
    print(f"  here, {p}: n={len(s):>5}  {s.oe.mean():+.2f} yds  (p={stats.ttest_1samp(s.oe,0).pvalue:.3f})")

hdr("5. KICKOFF TOUCHBACK RATE (2011-2023, fixed 35-yd tee)")
ko=P[P.kickoff_attempt.eq(1)&P.season.between(2011,2023)].copy(); ko["tb"]=ko.touchback.eq(1).astype(int)
rows=[dict(sid=sid,team=s.stadium.mode().iat[0][:22],
           roof=s.roof.mode().iat[0],n=len(s),tb=s.tb.mean())
      for sid,s in ko.groupby("stadium_id") if len(s)>=300]
TK=pd.DataFrame(rows).sort_values("tb")
for i,(_,r) in enumerate(TK.iterrows(),1):
    if i<=5 or r.sid==SID:
        print(f"   {i:>2}. {r.team:<24} {r.roof:<9} n={int(r.n):>5}  TB {r.tb:.1%}"
              + ("   <<<< THIS VENUE" if r.sid==SID else ""))
    elif i==6: print("       ...")
if SID in set(TK.sid): print(f"\n  touchback rank: {list(TK.sid).index(SID)+1} of {len(TK)} (1 = ball carrying least)")

hdr("6. WIND SENSITIVITY (visiting kickers)")
W=F.copy(); W["wnd"]=pd.to_numeric(W.wind,errors="coerce")
W=W.dropna(subset=["wnd"]); W=W[W.wnd.between(0,40)&W.roof.eq("outdoors")]
for lo,hi,lab in [(0,5,"0-5 mph"),(6,9,"6-9 mph"),(10,14,"10-14 mph"),(15,40,"15+ mph")]:
    a=W[W.tgt&W.wnd.between(lo,hi)&~W.is_home_kick]; b=W[~W.tgt&W.wnd.between(lo,hi)&~W.is_home_kick]
    print(f"  {lab:<10} here {oe(a)[2]:+6.1%} (n={len(a):>3})    other outdoor {oe(b)[2]:+6.1%} (n={len(b):>5})")
if W.tgt.any():
    r=smf.glm("made ~ bs(kick_distance,df=5)+C(season)+wnd*tgt",data=W,family=sm.families.Binomial()).fit(
        cov_type="cluster",cov_kwds={"groups":W.game_id})
    k=[t for t in r.params.index if "wnd" in t and "tgt" in t][0]
    print(f"\n  wind x venue interaction: {r.params[k]:+.4f} per mph (p={r.pvalues[k]:.3f});"
          f" league wind effect {r.params['wnd']:+.4f}/mph")

hdr("7. HOW THEY MISS")
miss=F[F.made.eq(0)].copy()
tail=miss.desc.str.extract(r"No Good,\s*([^.]*?),\s*(?:Center|Holder)",flags=re.I)[0].fillna("")
miss["wl"]=tail.str.contains("Wide Left",case=False); miss["wr"]=tail.str.contains("Wide Right",case=False)
miss["short"]=tail.str.contains("Short",case=False); miss["wide"]=miss.wl|miss.wr
c=miss[tail.str.len().gt(0)]
for lab,s in [("Visitors here",c[c.tgt&~c.is_home_kick]),("Home kickers here",c[c.tgt&c.is_home_kick]),
              ("Visitors elsewhere",c[~c.tgt&~c.is_home_kick])]:
    w=s[s.wide]
    print(f"  {lab:<24} n={len(s):>4}  wide-only {(s.wide&~s.short).mean():6.1%}  short-involved {s.short.mean():6.1%}"
          f"  |  wide: {w.wl.mean():5.1%}L / {w.wr.mean():5.1%}R")

hdr("8. 4th-DOWN DECISIONS: does the home team decline kicks here?")
D2=D[D.yardline_100.notna()&D.play_type.notna()&D.qtr.le(4)].copy()
D2["fga"]=D2.field_goal_attempt.eq(1).astype(int); D2["fgd"]=D2.yardline_100+17
L=D2[D2.fgd.between(50,62)&D2.ydstogo.between(1,10)&D2.wp.between(0.05,0.95)]
def row(s,lab): print(f"  {lab:<42} n={len(s):>5}  kicked {s.fga.mean():6.1%}")
row(L[L.tgt&L.is_home_kick],"Home team here, 50+ available")
row(L[L.tgt&~L.is_home_kick],"Visitors here")
for t in RES: row(L[~L.tgt&L.posteam.eq(t)],f"  {t} on the road")
row(L[~L.tgt&L.is_home_kick],"All home teams, other stadiums")
a=L[L.tgt&L.is_home_kick].fga; b=L[~L.tgt&L.is_home_kick].fga
print(f"\n  home-here vs home-elsewhere: Fisher p="
      f"{stats.fisher_exact([[a.sum(),len(a)-a.sum()],[b.sum(),len(b)-b.sum()]])[1]:.4f}")

hdr("9. SEASON BY SEASON (visiting kickers)")
v=F[F.tgt&~F.is_home_kick]
ss=v.groupby("season").apply(lambda s: s.made.mean()-s.xmake.mean()); cn=v.groupby("season").size()
print("  "+"  ".join(f"{i}:{x*100:+.0f}({cn[i]})" for i,x in ss.items()))
print(f"  seasons below expectation: {(ss<0).sum()} of {len(ss)}")

hdr("10. SAME SITE, DIFFERENT BUILDING: Giants Stadium (2002-09) vs MetLife (2010-25)")
for sid,lab in [("NYC00","Giants Stadium 2002-09"),("NYC01","MetLife 2010-25")]:
    a=F[F.stadium_id.eq(sid)&~F.is_home_kick]; h=F[F.stadium_id.eq(sid)&F.is_home_kick]
    pa=pu[pu.stadium_id.eq(sid)]
    ka=ko[ko.stadium_id.eq(sid)]
    print(f"  {lab:<26} visitors {oe(a)[1]:6.1%} ({oe(a)[2]:+.1%} vs exp, n={oe(a)[0]:>3})   "
          f"home {oe(h)[2]:+.1%}   punts {pa.oe.mean():+.2f} yds (n={len(pa):>4})"
          + (f"   TB {ka.tb.mean():.1%}" if len(ka)>100 else ""))
