"""4th-down plays 2002-2025: lets us ask whether New England declined kicks
at Gillette that other teams attempted."""
import os, subprocess, sys
import pandas as pd, pyarrow.parquet as pq
WANT=['game_id','season','week','home_team','away_team','posteam','defteam','stadium_id','roof',
      'qtr','down','ydstogo','yardline_100','play_type','field_goal_attempt','punt_attempt',
      'game_seconds_remaining','score_differential','wp','desc']
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"fourth_2002_2025.parquet")
TMP="/tmp/nflverse3"; os.makedirs(TMP,exist_ok=True)
fr=[]
for yr in range(2002,2026):
    p=f"{TMP}/pbp_{yr}.parquet"
    if not os.path.exists(p):
        u=f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{yr}.parquet"
        if subprocess.run(["curl","-sSL","--retry","4","--retry-delay","2","-o",p,u]).returncode!=0:
            sys.exit(f"fail {yr}")
    pf=pq.ParquetFile(p); df=pf.read(columns=[c for c in WANT if c in pf.schema_arrow.names]).to_pandas()
    df=df[df.down.eq(4)].copy()
    for c in WANT:
        if c not in df.columns: df[c]=pd.NA
    fr.append(df[WANT]); os.remove(p); print(yr,len(df),flush=True)
pd.concat(fr,ignore_index=True).to_parquet(OUT,index=False)
print("wrote",OUT)
