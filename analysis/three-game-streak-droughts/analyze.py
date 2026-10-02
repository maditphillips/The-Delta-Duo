"""Gaps between 3-game win streaks, 1999-present (nflverse games.csv).

Usage: python3 analyze.py path/to/games.csv  ->  writes plot.csv
Gap = games from the last win of one 3+ win streak to the 3rd win of the next.
Ties end a streak. Playoffs included. Relocated franchises combined.
"""
import sys
import pandas as pd

g = pd.read_csv(sys.argv[1])
# Browns beat Steelers Oct 1, 2026; not yet in the dataset when this was built.
g.loc[(g.game_id == '2026_04_PIT_CLE') & g.home_score.isna(), ['home_score', 'away_score']] = [1, 0]
g = g[g.home_score.notna()]
moved = {'STL': 'LA', 'SD': 'LAC', 'OAK': 'LV'}
t = pd.concat([
    pd.DataFrame({'team': g[s + '_team'].replace(moved), 'date': g.gameday,
                  'pf': g[s + '_score'], 'pa': g[o + '_score']})
    for s, o in (('home', 'away'), ('away', 'home'))
]).sort_values(['team', 'date'])

ended, ongoing = [], []
for team, df in t.groupby('team'):
    run, last_end, since = 0, None, 0
    for r in df.itertuples():
        since += 1
        run = run + 1 if r.pf > r.pa else 0
        if run == 3 and last_end is not None:
            ended.append((team, last_end, r.date, since - 3))
        if run >= 3:
            last_end, since = r.date, 0
    ongoing.append((team, last_end, since))

ended = pd.DataFrame(ended, columns=['team', 'start', 'end', 'games'])
ongoing = pd.DataFrame(ongoing, columns=['team', 'start', 'games'])
out = pd.concat([
    ended.nlargest(10, 'games').assign(kind='done'),
    ongoing.nlargest(5, 'games').assign(kind='ongoing'),
])
out.to_csv('plot.csv', index=False)
print(out.to_string(index=False))
