"""Download the nflverse release assets this study needs."""
import subprocess, os
B = "https://github.com/nflverse/nflverse-data/releases/download"
os.makedirs('pbp', exist_ok=True); os.makedirs('stats', exist_ok=True); os.makedirs('misc', exist_ok=True)
jobs = []
for y in range(2012, 2026):
    jobs.append((f"{B}/pbp/play_by_play_{y}.parquet", f"pbp/pbp_{y}.parquet"))
    jobs.append((f"{B}/stats_player/stats_player_week_{y}.parquet", f"stats/week_{y}.parquet"))
for name in ['players/players', 'draft_picks/draft_picks',
             'nextgen_stats/ngs_receiving', 'nextgen_stats/ngs_rushing', 'nextgen_stats/ngs_passing']:
    jobs.append((f"{B}/{name}.parquet", f"misc/{name.split('/')[1]}.parquet"))
procs = [subprocess.Popen(['curl', '-sS', '-m', '300', '-L', '-o', dst, url]) for url, dst in jobs]
for p in procs: p.wait()
print(f"fetched {len(jobs)} files")
