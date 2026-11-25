"""Step 19: read every NFL team's staff pages and pull mental-health / psychology / player-wellness titles.

Usage: python3 scrape_staff.py OUT_DIR  ->  saves the HTML pages in OUT_DIR, writes staff_titles.csv here.
Pages: /team/front-office-roster/ and /team/coaches-roster/ on each team site (a few teams use other paths).
A staff page reflects who is employed when it was read (November 2026), not past seasons.
"""
import os, re, sys, html, subprocess
import pandas as pd

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
SITES = {'ARI': 'www.azcardinals.com', 'ATL': 'www.atlantafalcons.com', 'BAL': 'www.baltimoreravens.com', 'BUF': 'www.buffalobills.com',
         'CAR': 'www.panthers.com', 'CHI': 'www.chicagobears.com', 'CIN': 'www.bengals.com', 'CLE': 'www.clevelandbrowns.com',
         'DAL': 'www.dallascowboys.com', 'DEN': 'www.denverbroncos.com', 'DET': 'www.detroitlions.com', 'GB': 'www.packers.com',
         'HOU': 'www.houstontexans.com', 'IND': 'www.colts.com', 'JAX': 'www.jaguars.com', 'KC': 'www.chiefs.com',
         'LV': 'www.raiders.com', 'LAC': 'www.chargers.com', 'LA': 'www.therams.com', 'MIA': 'www.miamidolphins.com',
         'MIN': 'www.vikings.com', 'NE': 'www.patriots.com', 'NO': 'www.neworleanssaints.com', 'NYG': 'www.giants.com',
         'NYJ': 'www.newyorkjets.com', 'PHI': 'www.philadelphiaeagles.com', 'PIT': 'www.steelers.com', 'SF': 'www.49ers.com',
         'SEA': 'www.seahawks.com', 'TB': 'www.buccaneers.com', 'TEN': 'www.tennesseetitans.com', 'WAS': 'www.commanders.com'}
PATHS = {'front': '/team/front-office-roster/', 'coaches': '/team/coaches-roster/'}
OVERRIDE = {('PHI', 'front'): '/team/front-office/', ('CAR', 'front'): '/team/ownership_business/',
            ('CHI', 'front'): '/team/front-office/', ('CHI', 'coaches'): '/team/coaches/'}
# Titles that count as mental health / psychology / player wellness staff
KEEP = re.compile(r'psycholog|psychiatr|\bmental|clinician|behavioral|counselor\b|wellness|player engagement|player development|'
                  r'player care|player resource|chaplain|team dynamics', re.I)
DROP = re.compile(r'counsel\b|general counsel|associate counsel|nutrition|dietitian|environmental|alumni relations$|scout', re.I)

rows = []
for team, site in SITES.items():
    for page, path in PATHS.items():
        url = f'https://{site}{OVERRIDE.get((team, page), path)}'
        f = f'{OUT}/{team}_{page}.html'
        subprocess.run(['curl', '-s', '-L', '--max-time', '40', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', '-o', f, url])
        s = open(f, encoding='utf-8', errors='ignore').read()
        t = re.sub(r'<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<footer.*?</footer>', '', s, flags=re.S)
        lines = [l.strip() for l in html.unescape(re.sub(r'<[^>]+>', '\n', t)).split('\n') if l.strip()]
        full = bool(re.search(r'athletic trainer|team physician', s, re.I))
        found = 0
        for i, l in enumerate(lines):
            if len(l) < 120 and KEEP.search(l) and not DROP.search(l):
                name = lines[i - 1]
                if KEEP.search(name) or re.search(r'Coordinator|Manager|Assistant|Director|Fellow|Engineer|Intern|Therapist|^Staff$', name):
                    continue  # section header or a title, not a person's name
                rows.append({'team': team, 'page': page, 'url': url, 'name': name, 'title': l})
                found += 1
        rows.append({'team': team, 'page': page, 'url': url, 'name': '(page check)',
                     'title': f'lists medical staff: {full}; matching titles: {found}'})
df = pd.DataFrame(rows).drop_duplicates(['team', 'name', 'title'])
df.to_csv(f'{here}/staff_titles.csv', index=False)
print(df[df.name != '(page check)'].to_string(index=False))
