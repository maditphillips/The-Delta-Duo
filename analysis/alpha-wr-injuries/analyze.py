"""Do alpha WRs on bad teams get hurt more than alpha WRs on good teams?"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from scipy import stats

d = pd.read_csv("alpha_wrs.csv")
d["per17"] = d.inj_missed / d.team_games * 17
d["any"] = (d.inj_missed > 0).astype(int)
d["big"] = (d.inj_missed >= 4).astype(int)
d["irf"] = d.ir.astype(int)
d["late_per"] = d.inj_missed_late  # weeks 13+
d["early_per"] = d.inj_missed - d.inj_missed_late
rng = np.random.default_rng(0)


def table(col, labels=("bad", "middle", "good")):
    q = pd.qcut(d[col].rank(method="first"), 3, labels=labels)
    t = d.groupby(q, observed=True).agg(
        n=("per17", "size"), team_win_pct=("win_pct", "mean"),
        games_missed_per17=("per17", "mean"), missed_any=("any", "mean"), missed_4plus=("big", "mean"),
        on_ir=("irf", "mean"), injury_spells=("inj_spells", "mean"),
        missed_wk1_12=("early_per", "mean"), missed_wk13plus=("late_per", "mean"),
        tgt_per_game=("tgt_per_game", "mean"), age=("age", "mean"))
    bad, good = d.per17[q == "bad"], d.per17[q == "good"]
    diff = bad.mean() - good.mean()
    boots = [rng.choice(bad, len(bad)).mean() - rng.choice(good, len(good)).mean() for _ in range(5000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    p_mw = stats.mannwhitneyu(bad, good).pvalue
    keep = q != "middle"
    p_any = stats.fisher_exact(pd.crosstab(q[keep].astype(str), d["any"][keep]))[1]
    return t, diff, lo, hi, p_mw, p_any


pd.set_option("display.width", 200, "display.precision", 3)
print(f"{len(d)} alpha-WR seasons, {d.season.min()}-{d.season.max()} "
      f"(WR with most targets per game on his team, min 6 games)\n")
print("Overall: %.2f injury games missed per 17, %.0f%% missed at least one, %.0f%% missed 4+\n"
      % (d.per17.mean(), 100 * d["any"].mean(), 100 * d.big.mean()))

for col, label in [("win_pct", "final win %"),
                   ("early_spread", "Vegas spread, weeks 1-4 (set before most injuries)"),
                   ("prior_win_pct", "prior-season win %")]:
    t, diff, lo, hi, p_mw, p_any = table(col)
    print(f"=== Team quality by {label}, split in thirds ===")
    print(t.T.to_string())
    print(f"bad minus good, games missed per 17: {diff:+.2f} (95% CI {lo:+.2f} to {hi:+.2f}); "
          f"Mann-Whitney p = {p_mw:.2f}; missed-any Fisher p = {p_any:.2f}\n")

# continuous: negative binomial on injury games missed, exposure = team games
print("=== Negative binomial: injury games missed ~ team quality (+ age, targets/game) ===")
d["z_spread"] = (d.early_spread - d.early_spread.mean()) / d.early_spread.std()
d["z_win"] = (d.win_pct - d.win_pct.mean()) / d.win_pct.std()
for f in ["inj_missed ~ z_spread", "inj_missed ~ z_spread + age + tgt_per_game",
          "inj_missed ~ z_win + age + tgt_per_game"]:
    m = smf.glm(f, d.dropna(subset=["age"]), family=sm.families.NegativeBinomial(alpha=1.5),
                offset=np.log(d.dropna(subset=["age"]).team_games)).fit(
        cov_type="cluster", cov_kwds={"groups": d.dropna(subset=["age"]).player_id.astype("category").cat.codes})
    k = f.split("~")[1].split("+")[0].strip()
    print(f"{f:45s} rate ratio per +1 SD better team = {np.exp(m.params[k]):.2f} "
          f"(95% CI {np.exp(m.conf_int().loc[k, 0]):.2f}-{np.exp(m.conf_int().loc[k, 1]):.2f}), p = {m.pvalues[k]:.2f}")

# extremes: bottom vs top 25% by preseason-ish spread
q4 = pd.qcut(d.early_spread.rank(method="first"), 4, labels=False)
b, g = d[q4 == 0], d[q4 == 3]
print(f"\nExtremes by early spread: worst quarter {b.per17.mean():.2f} vs best quarter {g.per17.mean():.2f} "
      f"games missed per 17 (Mann-Whitney p = {stats.mannwhitneyu(b.per17, g.per17).pvalue:.2f})")

out = d.assign(group=pd.qcut(d.early_spread.rank(method="first"), 3, labels=["bad", "middle", "good"]))
out.groupby("group", observed=True)[["per17", "any", "big", "irf", "tgt_per_game"]].mean().to_csv("summary_by_spread.csv")

# where the gap comes from: early vs late season, and new injuries vs length of absence
print("\n=== Bad vs good by early spread: where the gap comes from ===")
q = pd.qcut(d.early_spread.rank(method="first"), 3, labels=["bad", "middle", "good"])
for c, lab in [("early_per", "games missed, weeks 1-12"), ("late_per", "games missed, weeks 13+"),
               ("inj_spells", "separate injury absences"), ("big", "missed 4+ games")]:
    b, g = d[c][q == "bad"], d[c][q == "good"]
    p = stats.mannwhitneyu(b, g).pvalue
    print(f"{lab:28s} bad {b.mean():.2f}  good {g.mean():.2f}  p = {p:.2f}")
spell_len = d[d.inj_spells > 0].assign(len_=lambda x: x.inj_missed / x.inj_spells)
print("avg games per absence:  bad %.2f  good %.2f" % (spell_len.len_[q == "bad"].mean(), spell_len.len_[q == "good"].mean()))
