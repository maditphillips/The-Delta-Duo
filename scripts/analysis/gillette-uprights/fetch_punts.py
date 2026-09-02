"""Pull punts and kickoffs 2002-2025 - aerodynamic probes that have nothing
to do with uprights or video boards."""
import os, subprocess, sys
import pandas as pd, pyarrow.parquet as pq
WANT=['game_id','season','season_type','week','home_team','away_team','posteam','defteam',
      'stadium','stadium_id','roof','surface','wind','temp','weather','qtr',
      'punt_attempt','kickoff_attempt','kick_distance','return_yards','touchback',
      'punt_blocked','punt_inside_twenty','punt_out_of_bounds','punt_fair_catch',
      'kickoff_in_endzone','kicker_player_id','kicker_player_name','yardline_100','desc']
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"punts_2002_2025.parquet")
TMP=os.environ.get("NFLVERSE_TMP","/tmp/nflverse2"); os.makedirs(TMP,exist_ok=True)
frames=[]
for yr in range(2002,2026):
    p=f"{TMP}/pbp_{yr}.parquet"
    if not os.path.exists(p):
        u=f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{yr}.parquet"
        if subprocess.run(["curl","-sSL","--retry","4","--retry-delay","2","-o",p,u]).returncode!=0:
            sys.exit(f"fail {yr}")
    pf=pq.ParquetFile(p); df=pf.read(columns=[c for c in WANT if c in pf.schema_arrow.names]).to_pandas()
    df=df[(df.punt_attempt==1)|(df.kickoff_attempt==1)].copy()
    for c in WANT:
        if c not in df.columns: df[c]=pd.NA
    frames.append(df[WANT]); os.remove(p); print(yr,len(df),flush=True)
pd.concat(frames,ignore_index=True).to_parquet(OUT,index=False)
print("wrote",OUT)
