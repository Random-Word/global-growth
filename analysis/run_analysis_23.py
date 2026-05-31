#!/usr/bin/env python3
"""Analysis 23: The Development Recipe's Base Rate (survivorship correction).

run_analysis_13 studies ~41 hand-picked countries and infers a "development
recipe" (high investment + trade openness + fertility decline + education).
That sample is survivorship-biased: it over-represents successes. This script
supplies the missing DENOMINATOR.

Question: of ALL country-spells in a broad panel that actually had the recipe
ingredients (sustained high investment, optionally + trade openness + falling
fertility), what fraction went on to achieve sustained convergence? That is the
base rate, and it directly tests whether the recipe is SUFFICIENT.

What this establishes (and what it does NOT):
- It tests SUFFICIENCY: among spells that HAD sustained high investment, how
  often did takeoff follow? A low base rate => high investment is NOT SUFFICIENT.
- It cannot establish NECESSITY. A base rate computed *among recipe-havers*
  says nothing about whether takeoff ever happens without the recipe. So the
  conclusion is narrowed to "NOT SUFFICIENT", not "necessary-not-sufficient".

Two review-driven corrections to the headline number:
1. DEVELOPING-ONLY subsample. The recipe's success target ("3%/yr growth or
   close the US gap by 5 pts") is a *development takeoff* target. Frontier/rich
   economies (Australia, Japan, Switzerland, Austria, France) that invest >25%
   of GDP are not trying to "take off"; including them biases the base rate.
   We classify each spell by its START-year GDP per capita (PPP) relative to
   the US and report the base rate for (a) ALL economies, (b) below 50% of US
   gdppc at spell start = the HEADLINE developing rate, (c) below 25% of US.
2. CENSORING transparency. Spells without a full follow-up horizon are
   UNSCORABLE, not failures. Success fields are NaN (not False) when unscorable,
   and base rates use only scorable spells. A representativeness table shows how
   the scored sample tilts (ongoing likely-successes such as Korea/Vietnam/
   China/India/Bangladesh/Ethiopia are censored out).

Malawi is featured as a counter-case: decades of aid dependence but investment
that never sustained the takeoff threshold -> a recipe-absent, no-takeoff story.

Outputs:
- charts/108_recipe_base_rate.png
- charts/109_investment_without_takeoff.png
- data/processed/recipe_base_rate.csv             (per-spell detail, new columns)
- data/processed/recipe_base_rate_summary.csv     (base rates by variant)
- data/processed/recipe_base_rate_sensitivity.csv (threshold-grid robustness)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import itertools

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", palette="colorblind")
plt.rcParams.update(
    {
        "figure.figsize": (12, 7),
        "font.size": 11,
        "axes.titlesize": 13,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)

# ── Recipe / success thresholds (explicit defaults; varied in the grid below) ──
INVEST_THRESHOLD = 25.0  # gross capital formation > 25% of GDP
MIN_SPELL_YEARS = 8  # sustained for >= 8 consecutive years
HORIZON = 10  # success measured over the following 10 years
GROWTH_SUCCESS = 3.0  # real gdppc CAGR >= 3%/yr = "sustained convergence"
GAP_CLOSE_SUCCESS = 0.05  # OR frontier gap (vs US) closes by >= 5 pts

# Development (initial-income) cut-offs: spell-start gdppc PPP as a share of US.
DEV_50 = 0.50
DEV_25 = 0.25

# ══════════════════════════════════════════════════════════════════════════════
# LOAD broad panel (261 economies) + region map; drop WB aggregates
# ══════════════════════════════════════════════════════════════════════════════
df = pd.read_csv(PROC / "wdi_combined.csv")
reg = pd.read_csv(RAW / "wb_country_regions.csv")
df = df.merge(reg[["country_code", "region"]], on="country_code", how="inner")
df["region"] = df["region"].str.strip()
print(f"Loaded panel: {len(df)} rows, {df.country_code.nunique()} economies")

# US frontier benchmarks. PPP per-capita (preferred) only begins ~1990 in WDI, so
# we also keep the constant-2015-USD per-capita series as a FALLBACK for pre-1990
# spell starts. Frontier economies (Japan, Switzerland, Austria, France) sit well
# above 50% of the US on BOTH measures, so the "developing" filter is robust to
# which one is used; the fallback only rescues early developing spells (Korea-74,
# Thailand-77, etc.) that would otherwise be unclassifiable.
us = df[df.country_code == "USA"].set_index("year")["gdppc_ppp_current"]
us_const = df[df.country_code == "USA"].set_index("year")["gdppc_constant_2015usd"]


def cagr(start_val: float, end_val: float, years: int) -> float:
    if start_val is None or end_val is None or start_val <= 0 or end_val <= 0:
        return np.nan
    return (end_val / start_val) ** (1 / years) - 1.0


# ══════════════════════════════════════════════════════════════════════════════
# Spell builder (parameterised so the sensitivity grid can reuse it).
# Returns one row per sustained high-investment spell with the raw follow-up
# observations (subsequent_growth, gap_close) and the spell's START-year income
# relative to the US. Success scoring is applied separately so growth cut-offs
# can be varied without re-scanning.
# ══════════════════════════════════════════════════════════════════════════════
def build_spells(invest_threshold: float, min_years: int, horizon: int) -> pd.DataFrame:
    out = []
    for cc, g in df.groupby("country_code"):
        g = g.sort_values("year")
        inv = g.set_index("year")["gross_capital_formation_pct"]
        gdppc = g.set_index("year")["gdppc_constant_2015usd"]
        trade = g.set_index("year")["trade_pct_gdp"]
        fert = g.set_index("year")["fertility_rate"]
        ppp = g.set_index("year")["gdppc_ppp_current"]
        yrs = [
            y
            for y in inv.index
            if pd.notna(inv.loc[y]) and inv.loc[y] > invest_threshold
        ]
        if not yrs:
            continue
        runs, cur = [], [yrs[0]]
        for y in yrs[1:]:
            if y == cur[-1] + 1:
                cur.append(y)
            else:
                runs.append(cur)
                cur = [y]
        runs.append(cur)

        for run in runs:
            if len(run) < min_years:
                continue
            s0, s1 = run[0], run[-1]
            mean_inv = float(inv.loc[run].mean())

            # subsequent real per-capita growth over `horizon` years after spell
            end_gdppc = gdppc.get(s1, np.nan)
            fut_gdppc = gdppc.get(s1 + horizon, np.nan)
            sub_growth = (
                cagr(end_gdppc, fut_gdppc, horizon) * 100
                if pd.notna(end_gdppc) and pd.notna(fut_gdppc)
                else np.nan
            )

            # frontier gap closure (vs US), PPP terms
            gap0 = (
                ppp.get(s1, np.nan) / us.get(s1, np.nan) if s1 in us.index else np.nan
            )
            gap1 = (
                ppp.get(s1 + horizon, np.nan) / us.get(s1 + horizon, np.nan)
                if (s1 + horizon) in us.index
                else np.nan
            )
            gap_close = (gap1 - gap0) if pd.notna(gap0) and pd.notna(gap1) else np.nan

            # START-year income relative to the US (the development filter).
            # Prefer PPP; fall back to constant-2015-USD per-capita ratio when
            # start-year PPP is missing (pre-~1990 spells), recording the method.
            start_ppp = ppp.get(s0, np.nan)
            us_start = us.get(s0, np.nan) if s0 in us.index else np.nan
            if pd.notna(start_ppp) and pd.notna(us_start) and us_start > 0:
                start_rel_us = start_ppp / us_start
                rel_method = "ppp"
            else:
                c0 = gdppc.get(s0, np.nan)
                uc0 = us_const.get(s0, np.nan) if s0 in us_const.index else np.nan
                if pd.notna(c0) and pd.notna(uc0) and uc0 > 0:
                    start_rel_us = c0 / uc0
                    rel_method = "constant_usd_fallback"
                else:
                    start_rel_us = np.nan
                    rel_method = "none"

            # recipe variant flags
            trade_open = (
                float(trade.loc[run].mean()) if trade.loc[run].notna().any() else np.nan
            )
            f0, f1 = fert.get(s0, np.nan), fert.get(s1, np.nan)
            fert_decline = bool(pd.notna(f0) and pd.notna(f1) and f1 < f0)

            out.append(
                {
                    "country_code": cc,
                    "country": g["country"].iloc[0],
                    "region": g["region"].iloc[0],
                    "spell_start": int(s0),
                    "spell_end": int(s1),
                    "spell_years": len(run),
                    "mean_investment": round(mean_inv, 2),
                    "mean_trade": (
                        round(trade_open, 2) if pd.notna(trade_open) else np.nan
                    ),
                    "fert_decline": fert_decline,
                    "start_gdppc_ppp": (
                        round(start_ppp, 1) if pd.notna(start_ppp) else np.nan
                    ),
                    "us_gdppc_ppp_start": (
                        round(us_start, 1) if pd.notna(us_start) else np.nan
                    ),
                    "start_rel_us": (
                        round(start_rel_us, 4) if pd.notna(start_rel_us) else np.nan
                    ),
                    "start_rel_method": rel_method,
                    "subsequent_growth": (
                        round(sub_growth, 2) if pd.notna(sub_growth) else np.nan
                    ),
                    "gap_close": round(gap_close, 4) if pd.notna(gap_close) else np.nan,
                }
            )
    return pd.DataFrame(out)


def score_spells(
    sp: pd.DataFrame, growth_cutoff: float, gap_cutoff: float = GAP_CLOSE_SUCCESS
) -> pd.DataFrame:
    """Add explicit CENSORING + success columns.

    Unscorable spells (no follow-up horizon observed) get NaN success fields and
    a censor_reason, so they are never silently miscounted as failures.
    """
    sp = sp.copy()
    sp["scorable_growth"] = sp["subsequent_growth"].notna()
    sp["scorable_gap"] = sp["gap_close"].notna()
    sp["scorable_any"] = sp["scorable_growth"] | sp["scorable_gap"]
    sp["censor_reason"] = np.where(
        sp["scorable_any"], "", "ongoing/insufficient_followup"
    )

    # success = NaN when the relevant dimension is unscorable (NOT False)
    sp["success_growth"] = np.where(
        sp["scorable_growth"], sp["subsequent_growth"] >= growth_cutoff, np.nan
    ).astype("float")
    sp["success_gap"] = np.where(
        sp["scorable_gap"], sp["gap_close"] >= gap_cutoff, np.nan
    ).astype("float")
    # OR definition: True if either scorable dimension succeeds; NaN only if both unscorable
    or_true = (sp["success_growth"] == 1.0) | (sp["success_gap"] == 1.0)
    sp["success_flag"] = np.where(sp["scorable_any"], or_true, np.nan).astype("float")
    return sp


def rate(frame: pd.DataFrame, col: str, scorable_col: str) -> tuple[int, int, float]:
    """k successes / n scorable for a given success column."""
    sub = frame[frame[scorable_col]]
    n = len(sub)
    k = int((sub[col] == 1.0).sum())
    return n, k, (round(100 * k / n, 1) if n else np.nan)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN spell set at default thresholds
# ══════════════════════════════════════════════════════════════════════════════
sp = build_spells(INVEST_THRESHOLD, MIN_SPELL_YEARS, HORIZON)
trade_median = df.groupby("country_code")["trade_pct_gdp"].mean().median()
sp["recipe_A"] = True  # investment-only (already filtered)
sp["recipe_B"] = sp["recipe_A"] & (sp["mean_trade"] > trade_median) & sp["fert_decline"]
sp["recipe_met"] = sp["recipe_A"]
sp = score_spells(sp, GROWTH_SUCCESS)

# development bucket at spell start
sp["start_income_bucket"] = np.select(
    [
        sp["start_rel_us"] < DEV_25,
        sp["start_rel_us"] < DEV_50,
        sp["start_rel_us"].notna(),
    ],
    ["<25% US", "25-50% US", ">=50% US"],
    default="unknown",
)

scored = sp[sp["scorable_any"]].copy()
print(
    f"\nHigh-investment spells found: {len(sp)}  |  scorable (have follow-up): {len(scored)}"
)

# subsamples by initial development level
dev50 = scored[scored["start_rel_us"] < DEV_50]
dev25 = scored[scored["start_rel_us"] < DEV_25]


# ══════════════════════════════════════════════════════════════════════════════
# BASE RATES — developing-only headline + all-economies cross-check + by def
# ══════════════════════════════════════════════════════════════════════════════
def block(frame: pd.DataFrame, label: str) -> list[dict]:
    rows = []
    for defn, col, scol in [
        ("OR (growth>=3% OR gap+5pt)", "success_flag", "scorable_any"),
        ("growth-only (>=3%/yr)", "success_growth", "scorable_growth"),
        ("gap-only (+5pt vs US)", "success_gap", "scorable_gap"),
    ]:
        n, k, r = rate(frame, col, scol)
        rows.append(
            {
                "subsample": label,
                "success_def": defn,
                "n_spells": n,
                "n_success": k,
                "base_rate_pct": r,
            }
        )
    return rows


summary_rows = []
summary_rows += block(scored, "ALL economies (cross-check)")
summary_rows += block(dev50, "DEVELOPING <50% US start (HEADLINE)")
summary_rows += block(dev25, "DEVELOPING <25% US start")
# recipe B (invest + trade-open + fertility-down) on developing subsample
summary_rows += block(dev50[dev50["recipe_B"]], "DEVELOPING <50% US + recipe-B")

summary_df = pd.DataFrame(summary_rows)
print("\n── BASE RATES (success among SCORABLE spells) ──")
print(summary_df.to_string(index=False))

# headline numbers
hl = {
    r["success_def"]: r
    for r in summary_rows
    if r["subsample"].startswith("DEVELOPING <50% US start")
}
print(
    f"\nHEADLINE (developing, <50% US at start): "
    f"OR={hl['OR (growth>=3% OR gap+5pt)']['base_rate_pct']}%  "
    f"growth-only={hl['growth-only (>=3%/yr)']['base_rate_pct']}%  "
    f"gap-only={hl['gap-only (+5pt vs US)']['base_rate_pct']}%"
)

sp.to_csv(PROC / "recipe_base_rate.csv", index=False)
summary_df.to_csv(PROC / "recipe_base_rate_summary.csv", index=False)

# ══════════════════════════════════════════════════════════════════════════════
# SCORED-vs-CENSORED representativeness (censoring tilt)
# ══════════════════════════════════════════════════════════════════════════════
sp["scored_status"] = np.where(sp["scorable_any"], "scored", "censored (ongoing)")
sp["era"] = pd.cut(
    sp["spell_start"],
    [1959, 1979, 1999, 2009, 2030],
    labels=["pre-1980", "1980-1999", "2000-2009", "2010+"],
)
print("\n── SCORED vs CENSORED representativeness ──")
for dim in ["era", "region", "start_income_bucket"]:
    tab = sp.groupby([dim, "scored_status"], observed=True).size().unstack(fill_value=0)
    for c in ["scored", "censored (ongoing)"]:
        if c not in tab.columns:
            tab[c] = 0
    tab = tab[["scored", "censored (ongoing)"]]
    tab["pct_censored"] = (100 * tab["censored (ongoing)"] / tab.sum(axis=1)).round(0)
    print(f"\nby {dim}:")
    print(tab.to_string())

ongoing = sp[~sp["scorable_any"]]
watch = {"KOR", "VNM", "CHN", "IND", "BGD", "ETH"}
ongoing_watch = ongoing[ongoing.country_code.isin(watch)]
print(
    "\nNote: ongoing/likely-successful spells censored out of the base rate "
    "(no full follow-up horizon yet):"
)
if len(ongoing_watch):
    print(
        ongoing_watch[
            [
                "country",
                "spell_start",
                "spell_end",
                "mean_investment",
                "start_income_bucket",
            ]
        ].to_string(index=False)
    )
else:
    print(
        "  (none of the watch-list countries have a censored qualifying spell at default thresholds)"
    )
print(
    "  These are disproportionately recent Asian/African takeoffs; excluding them "
    "biases the SCORED base rate DOWNWARD relative to the true sufficiency rate."
)

# investment-without-takeoff cases (recipe present, scorable, no convergence)
no_takeoff = scored[scored["success_flag"] == 0.0].sort_values(
    "mean_investment", ascending=False
)
print(
    f"\nInvestment-WITHOUT-takeoff spells (all economies): {len(no_takeoff)} "
    f"({100*len(no_takeoff)/len(scored):.0f}% of scorable)"
)
print(
    no_takeoff[
        [
            "country",
            "region",
            "spell_start",
            "spell_end",
            "start_income_bucket",
            "mean_investment",
            "subsequent_growth",
        ]
    ]
    .head(15)
    .to_string(index=False)
)

# region / era breakdown on DEVELOPING headline subsample
by_region = dev50.groupby("region")["success_flag"].agg(["size", "sum"])
by_region["rate"] = 100 * by_region["sum"] / by_region["size"]
dev50_era = dev50.copy()
dev50_era["era"] = pd.cut(
    dev50_era["spell_start"],
    [1959, 1979, 1999, 2030],
    labels=["pre-1980", "1980-1999", "2000+"],
)
by_era = dev50_era.groupby("era", observed=True)["success_flag"].agg(["size", "sum"])
by_era["rate"] = 100 * by_era["sum"] / by_era["size"]

# ══════════════════════════════════════════════════════════════════════════════
# THRESHOLD-GRID ROBUSTNESS — distribution of the DEVELOPING (<50% US) base rate
# ══════════════════════════════════════════════════════════════════════════════
print("\n── THRESHOLD-GRID ROBUSTNESS (developing <50% US, OR success) ──")
grid_rows = []
INV_GRID = [20, 25, 30]
DUR_GRID = [5, 8, 10]
HOR_GRID = [10, 15]
GROW_GRID = [2, 3, 4]
spell_cache: dict[tuple, pd.DataFrame] = {}
for inv_t, dur, hor, gcut in itertools.product(INV_GRID, DUR_GRID, HOR_GRID, GROW_GRID):
    key = (inv_t, dur, hor)
    if key not in spell_cache:
        spell_cache[key] = build_spells(inv_t, dur, hor)
    g = score_spells(spell_cache[key], gcut)
    g = g[g["scorable_any"]]
    gdev = g[g["start_rel_us"] < DEV_50]
    n, k, r = rate(gdev, "success_flag", "scorable_any")
    grid_rows.append(
        {
            "invest_threshold": inv_t,
            "min_duration": dur,
            "horizon": hor,
            "growth_cutoff": gcut,
            "n_spells": n,
            "n_success": k,
            "base_rate_pct": r,
        }
    )

grid_df = pd.DataFrame(grid_rows)
grid_df.to_csv(PROC / "recipe_base_rate_sensitivity.csv", index=False)
valid = grid_df["base_rate_pct"].dropna()
print(
    f"developing base rate across {len(grid_df)} specifications: "
    f"min {valid.min():.1f}%  median {valid.median():.1f}%  max {valid.max():.1f}%"
)
print(f"saved data/processed/recipe_base_rate_sensitivity.csv ({len(grid_df)} specs)")

# ══════════════════════════════════════════════════════════════════════════════
# MALAWI feature: investment never sustained the threshold (recipe-absent)
# ══════════════════════════════════════════════════════════════════════════════
mwi = df[df.country_code == "MWI"].sort_values("year")
mwi_inv = mwi.dropna(subset=["gross_capital_formation_pct"])
gdp_usd = mwi.set_index("year")["gdp_current_usd"]
dev = pd.read_csv(RAW / "wdi_development_theories.csv")
oda = dev[(dev.cc == "MWI") & (dev.indicator == "oda_net_current_usd")].set_index(
    "year"
)["value"]
mwi_oda_pct = (oda / gdp_usd * 100).dropna()
mwi_fert = mwi.dropna(subset=["fertility_rate"]).set_index("year")["fertility_rate"]
mwi_gdppc = mwi.dropna(subset=["gdppc_constant_2015usd"]).set_index("year")[
    "gdppc_constant_2015usd"
]

print("\n── MALAWI (counter-case) ──")
if len(mwi_inv):
    print(
        f"  investment %GDP: max {mwi_inv['gross_capital_formation_pct'].max():.1f} "
        f"(yr {int(mwi_inv.loc[mwi_inv['gross_capital_formation_pct'].idxmax(),'year'])}), "
        f"recent {mwi_inv['gross_capital_formation_pct'].iloc[-1]:.1f}; "
        f"NEVER sustained >{INVEST_THRESHOLD:.0f}% -> no qualifying spell"
    )
if len(mwi_oda_pct):
    print(
        f"  ODA/GDP: peak {mwi_oda_pct.max():.1f}% (yr {int(mwi_oda_pct.idxmax())}), "
        f"recent {mwi_oda_pct.iloc[-1]:.1f}%"
    )
print(
    f"  fertility: {mwi_fert.iloc[0]:.1f} ({mwi_fert.index[0]}) -> {mwi_fert.iloc[-1]:.1f} ({mwi_fert.index[-1]})"
)
print(
    f"  real gdppc: {mwi_gdppc.iloc[0]:.0f} ({mwi_gdppc.index[0]}) -> {mwi_gdppc.iloc[-1]:.0f} ({mwi_gdppc.index[-1]}); "
    f"CAGR {cagr(mwi_gdppc.iloc[0], mwi_gdppc.iloc[-1], mwi_gdppc.index[-1]-mwi_gdppc.index[0])*100:.2f}%/yr"
)
print(
    f"  -> Malawi in panel as MWI: {'MWI' in set(sp.country_code)} (no spell == recipe-absent)"
)

# ══════════════════════════════════════════════════════════════════════════════
# CHART 108: developing-only headline + all-economies cross-check
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# left: base-rate comparison across subsamples (OR / growth-only / gap-only)
ax = axes[0]
subs = [
    "ALL economies (cross-check)",
    "DEVELOPING <50% US start (HEADLINE)",
    "DEVELOPING <25% US start",
]
short = ["All\neconomies", "Developing\n<50% US\n(HEADLINE)", "Developing\n<25% US"]
defs = ["OR (growth>=3% OR gap+5pt)", "growth-only (>=3%/yr)", "gap-only (+5pt vs US)"]
colors = {
    "OR (growth>=3% OR gap+5pt)": "#2980b9",
    "growth-only (>=3%/yr)": "#27ae60",
    "gap-only (+5pt vs US)": "#e67e22",
}
x = np.arange(len(subs))
w = 0.26
lut = {(r["subsample"], r["success_def"]): r for r in summary_rows}
for j, d in enumerate(defs):
    vals = [lut[(s, d)]["base_rate_pct"] for s in subs]
    ns = [lut[(s, d)]["n_spells"] for s in subs]
    bars = ax.bar(x + (j - 1) * w, vals, w, color=colors[d], label=d)
    for b, v, nn in zip(bars, vals, ns):
        if pd.notna(v):
            ax.text(
                b.get_x() + b.get_width() / 2,
                v + 1,
                f"{v:.0f}%\n(n={nn})",
                ha="center",
                fontsize=8,
            )
ax.set_xticks(x)
ax.set_xticklabels(short)
ax.set_ylabel("base rate of success (%)")
ax.set_ylim(0, 100)
ax.set_title(
    "Base rate by initial-income subsample & success definition\n"
    "developing = spell-start gdppc (PPP) below threshold share of US"
)
ax.legend(fontsize=8, loc="upper right")

# right: developing headline by era
ax = axes[1]
eg = by_era.dropna()
ax.bar(
    eg.index.astype(str), eg["size"], color="#d0d0d0", label="developing recipe spells"
)
ax.bar(eg.index.astype(str), eg["sum"], color="#27ae60", label="converged")
for i, (idx, row) in enumerate(eg.iterrows()):
    ax.text(
        i,
        row["size"] + 0.3,
        f"{row['rate']:.0f}%",
        ha="center",
        fontsize=10,
        weight="bold",
    )
ax.set_ylabel("number of spells")
hl_or = hl["OR (growth>=3% OR gap+5pt)"]["base_rate_pct"]
ax.set_title(
    f"Developing (<50% US) base rate by era\n"
    f"(headline OR rate {hl_or:.0f}% of developing recipe spells succeeded)"
)
ax.legend(fontsize=9)

fig.suptitle(
    "The development 'recipe' is NOT SUFFICIENT: base rate of takeoff among "
    f"sustained high-investment spells\n"
    f"recipe = investment>{INVEST_THRESHOLD:.0f}% of GDP for >={MIN_SPELL_YEARS}yr; "
    f"success = real gdppc growth>={GROWTH_SUCCESS:.0f}%/yr over next {HORIZON}yr OR closing the US gap "
    f">={GAP_CLOSE_SUCCESS*100:.0f}pt",
    fontsize=11,
)
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(CHARTS / "108_recipe_base_rate.png")
plt.close(fig)
print("\nsaved charts/108_recipe_base_rate.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 109: investment vs subsequent growth, colored by takeoff; Malawi flagged
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(12, 7))
plot = scored.dropna(subset=["subsequent_growth", "success_flag"])
ok = plot[plot["success_flag"] == 1.0]
no = plot[plot["success_flag"] == 0.0]
ax.scatter(
    no["mean_investment"],
    no["subsequent_growth"],
    s=60,
    c="#e74c3c",
    alpha=0.75,
    label=f"no takeoff (n={len(no)})",
    edgecolor="white",
)
ax.scatter(
    ok["mean_investment"],
    ok["subsequent_growth"],
    s=60,
    c="#27ae60",
    alpha=0.75,
    label=f"converged (n={len(ok)})",
    edgecolor="white",
)
ax.axhline(GROWTH_SUCCESS, color="gray", ls="--", lw=1)
ax.text(
    plot["mean_investment"].max(),
    GROWTH_SUCCESS + 0.1,
    f"success line ({GROWTH_SUCCESS:.0f}%/yr)",
    ha="right",
    fontsize=9,
    color="gray",
)

for _, r in no.sort_values("mean_investment", ascending=False).head(8).iterrows():
    ax.annotate(
        r["country"],
        (r["mean_investment"], r["subsequent_growth"]),
        fontsize=8,
        xytext=(4, 4),
        textcoords="offset points",
    )

mwi_peak = mwi_inv["gross_capital_formation_pct"].max() if len(mwi_inv) else np.nan
mwi_growth = (
    cagr(
        mwi_gdppc.iloc[0], mwi_gdppc.iloc[-1], mwi_gdppc.index[-1] - mwi_gdppc.index[0]
    )
    * 100
)
if pd.notna(mwi_peak):
    ax.scatter(
        [mwi_peak],
        [mwi_growth],
        marker="*",
        s=420,
        c="#8e44ad",
        edgecolor="black",
        zorder=5,
        label="Malawi (peak invest., never sustained 25%)",
    )
    ax.annotate(
        "Malawi: aid-dependent,\ninvestment never sustained 25%",
        (mwi_peak, mwi_growth),
        fontsize=9,
        color="#8e44ad",
        xytext=(10, -28),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="#8e44ad"),
    )
ax.axvline(INVEST_THRESHOLD, color="#8e44ad", ls=":", lw=1.2)
ax.text(
    INVEST_THRESHOLD + 0.2,
    ax.get_ylim()[0] + 0.3,
    "recipe threshold",
    color="#8e44ad",
    fontsize=8,
)
ax.set_xlabel("mean gross capital formation during spell (% of GDP)")
ax.set_ylabel(f"subsequent real gdppc growth, next {HORIZON}yr (%/yr CAGR)")
ax.set_title(
    "High investment without takeoff: the recipe's failures\n"
    "each point = one sustained high-investment country-spell"
)
ax.legend(loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(CHARTS / "109_investment_without_takeoff.png")
plt.close(fig)
print("saved charts/109_investment_without_takeoff.png")
print("\nDone!")
