"""Download the nflverse draft-pick table (PFR-derived). Gitignored output."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
       "draft_picks/draft_picks.parquet")

if __name__ == "__main__":
    out = os.path.join(HERE, "draft_picks.parquet")
    rc = subprocess.run(["curl", "-sSL", "--retry", "4", "--retry-delay", "2",
                         "-o", out, URL]).returncode
    sys.exit(rc or print("wrote", out))
