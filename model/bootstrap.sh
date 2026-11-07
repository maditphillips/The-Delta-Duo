#!/usr/bin/env bash
# Everything a fresh cloud container is missing, rebuilt from GitHub and the
# public data sources. The code and the hand files (returning.csv, role.csv,
# ruled-out.csv, added.csv) live in git and survive a reset; the packages, the
# website checkout and the downloaded data do not.
#
#   bash model/bootstrap.sh                 packages, website checkout, data
#   bash model/bootstrap.sh --packages-only packages and website checkout only
#
# The environment's setup script runs the --packages-only form at session
# start. The data step takes 30-60 minutes (2019-2026 play-by-play plus the
# training panel) and is run by hand, or by the first weekly run that needs it.
set -euo pipefail

REPO="${REPO:-/home/user/The-Delta-Duo}"
SITE="${SITE:-/tmp/site}"
SITE_BRANCH="claude/delta-duo-fantasy-dashboard-9wxjld"

python3 -m pip install -q -r "$REPO/model/requirements.txt"

# The website lives on its own branch; it is checked out beside the model.
git -C "$REPO" fetch -q origin "$SITE_BRANCH" || true
if [ ! -d "$SITE/.git" ] && [ ! -f "$SITE/.git" ]; then
  git -C "$REPO" worktree add -f "$SITE" "$SITE_BRANCH"
fi
(cd "$SITE" && npm ci --silent --no-audit --no-fund)

[ "${1:-}" = "--packages-only" ] && { echo "bootstrap: packages and website checkout ready"; exit 0; }

cd "$REPO/model"
python3 -m dd.cli ingest
python3 - <<'EOF'
import sys
sys.path.insert(0, ".")
from dd import defense, inseason
inseason.build(refresh=True)
defense.build(refresh=True)
inseason.training_panel()
print("bootstrap: data and training panel ready")
EOF
