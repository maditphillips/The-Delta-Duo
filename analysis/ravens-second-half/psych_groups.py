"""Team groups for the sports-psychologist comparisons (see sports_psychologists.md). Value = first season counted.

CONFIDENT: clear performance-psychology staff with a known start year.
POSSIBLE: clinician-type, consultant, or weak/undated source. Start year used where a source gives one;
          undated entries are counted for all of 2020-2026 (so they have no before/after comparison).
NO: Steelers (confirmed) + 13 teams where no one was found.
"""
CONFIDENT = {'GB': 2020, 'DET': 2021, 'CHI': 2022, 'BUF': 2023, 'KC': 2022, 'TEN': 2026}
POSSIBLE = {'NYG': 2020,   # Lani Lawrence, 2020
            'WAS': 2021,   # Barbara Roberts, Jun 2021
            'CAR': 2023,   # Joanne Perry, 2023 info sheet
            'ATL': 2024,   # Sierra Dimberg, since 2024 (theorg.com)
            'LA': 2020, 'TB': 2020, 'JAX': 2020, 'MIN': 2020, 'ARI': 2020}   # undated
UNDATED = {'LA', 'TB', 'JAX', 'MIN', 'ARI'}
NO = ['PIT', 'CIN', 'CLE', 'HOU', 'IND', 'LV', 'LAC', 'DAL', 'NE', 'NYJ', 'NO', 'SF', 'DEN', 'MIA']

def has_group(variant):
    return dict(CONFIDENT) if variant == 'confident' else {**CONFIDENT, **POSSIBLE}
