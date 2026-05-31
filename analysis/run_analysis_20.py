#!/usr/bin/env python3
"""Analysis 20: Within-country vs. between-country decomposition of the good-life gap.

The report's central tension is that the remaining poverty/good-life gap is
*fiscally* small but *politically* hard to close, because closing it appears to
require cross-border transfers and "there is no sovereign authority to guarantee
it." That framing implicitly assumes the gap is mostly a *between-country*
problem (poor countries vs. rich countries). But a large share of the shortfall
may sit *within* countries — i.e. poor people inside middle- and high-income
states — which is exactly the kind of redistribution that domestic fiscal
authorities (France collects 45% of GDP) demonstrably *can* perform.

This script decomposes the aggregate good-life gap into:
  * a BETWEEN-country component (everyone collapsed to their country mean), and
  * a WITHIN-country component (the residual due to internal dispersion),
using World Bank PIP survey-year decile shares (which carry true distributional
information, unlike the gap-filled series used elsewhere in this repo).

It also reports, at each threshold, whether enough income exists in covered
countries to lift everyone to the line by pure redistribution (surplus/gap).

Outputs:
- charts/102_within_between_gap_decomposition.png
- charts/103_redistribution_feasibility.png
- data/processed/within_between_decomposition.csv
- data/processed/within_between_country_detail.csv
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns

sns.set_theme(style="whitegrid", palette="colorblind")

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
for d in (RAW, PROC, CHARTS):
    d.mkdir(parents=True, exist_ok=True)

# Thresholds in 2017-PPP $/day. The report's good-life band is $15-$25/day PIP
# median welfare; lower lines are included for continuity with the gap series.
THRESHOLDS = [3.65, 6.85, 10.0, 15.0, 20.0, 25.0]
DAYS = 365.0
DECILE_COLS = [f"decile{i}" for i in range(1, 11)]


def load_pip_deciles() -> pd.DataFrame:
    """Load survey-year PIP data (with decile shares) for all countries.

    Uses fill_gaps=false because gap-filled/interpolated rows drop the decile
    distribution. The mean and decile shares are independent of the poverty
    line, so a single fetch at $2.15 suffices.
    """
    cache = RAW / "pip_country_deciles.csv"
    if cache.exists() and cache.stat().st_size > 1000:
        return pd.read_csv(cache)

    url = (
        "https://api.worldbank.org/pip/v1/pip?country=all&year=all"
        "&povline=2.15&fill_gaps=false&format=csv"
    )
    print(f"Fetching PIP survey deciles: {url}")
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.to_csv(cache, index=False)
    print(f"  -> cached {len(df)} rows to {cache.name}")
    return df


def latest_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Latest survey per country carrying full decile shares.

    The national-coverage preference is applied *per country* (not globally), so
    a country with only urban/rural rows is still retained rather than dropped.
    """
    d = df.copy()
    d = d.dropna(subset=DECILE_COLS + ["mean", "reporting_pop"])
    # Decile shares should sum to ~1.
    d = d[np.isclose(d[DECILE_COLS].sum(axis=1), 1.0, atol=0.02)]
    # Prefer national rows per country, then the most recent survey year.
    if "reporting_level" in d.columns:
        d["_natpref"] = (d["reporting_level"] == "national").astype(int)
    else:
        d["_natpref"] = 0
    d = d.sort_values(["_natpref", "reporting_year"])
    d = d.groupby("country_code", as_index=False).tail(1).drop(columns="_natpref")
    return d.reset_index(drop=True)


def decile_incomes(row: pd.Series) -> np.ndarray:
    """Mean daily income of each decile = country_mean * share * 10."""
    shares = row[DECILE_COLS].to_numpy(dtype=float)
    return row["mean"] * shares * 10.0


def decompose(dist: pd.DataFrame) -> pd.DataFrame:
    """Decompose the aggregate good-life gap at each threshold."""
    pop = dist["reporting_pop"].to_numpy(dtype=float)
    mean = dist["mean"].to_numpy(dtype=float)
    total_pop = pop.sum()
    world_mean = float((pop * mean).sum() / total_pop)

    # Decile-level matrix: rows = countries, cols = 10 deciles.
    inc = np.vstack([decile_incomes(r) for _, r in dist.iterrows()])
    pop_decile = pop[:, None] / 10.0  # equal tenths of each country's population

    records = []
    for T in THRESHOLDS:
        # Actual gap: true within-country distribution.
        gap_actual = (pop_decile * np.maximum(T - inc, 0.0)).sum() * DAYS
        # Between gap: collapse internal inequality to the country mean.
        gap_between = (pop * np.maximum(T - mean, 0.0)).sum() * DAYS
        gap_within = gap_actual - gap_between
        # Surplus available above the line (pure-redistribution feasibility).
        surplus = (pop_decile * np.maximum(inc - T, 0.0)).sum() * DAYS
        # Equal-world counterfactual: everyone at the covered world mean.
        gap_equal_world = total_pop * max(T - world_mean, 0.0) * DAYS
        records.append(
            {
                "threshold_day": T,
                "gap_actual_usd_yr": gap_actual,
                "gap_between_usd_yr": gap_between,
                "gap_within_usd_yr": gap_within,
                "between_share": gap_between / gap_actual if gap_actual else np.nan,
                "within_share": gap_within / gap_actual if gap_actual else np.nan,
                "surplus_above_usd_yr": surplus,
                "surplus_to_gap_ratio": surplus / gap_actual if gap_actual else np.nan,
                "gap_equal_world_usd_yr": gap_equal_world,
                "world_mean_day": world_mean,
                "covered_pop": total_pop,
            }
        )
    return pd.DataFrame(records)


def country_detail(dist: pd.DataFrame, T: float) -> pd.DataFrame:
    """Per-country between/within split at a reference threshold."""
    rows = []
    for _, r in dist.iterrows():
        inc = decile_incomes(r)
        pop = float(r["reporting_pop"])
        gap_actual = (pop / 10.0 * np.maximum(T - inc, 0.0)).sum() * DAYS
        gap_between = pop * max(T - r["mean"], 0.0) * DAYS
        rec = {
            "country_code": r["country_code"],
            "country_name": r["country_name"],
            "survey_year": int(r["reporting_year"]),
            "mean_day": r["mean"],
            "pop": pop,
            "gap_actual_usd_yr": gap_actual,
            "gap_between_usd_yr": gap_between,
            "gap_within_usd_yr": gap_actual - gap_between,
        }
        # Comparability diagnostics so the artifact is auditable.
        for col in (
            "welfare_type",
            "reporting_level",
            "distribution_type",
            "survey_acronym",
            "is_interpolated",
        ):
            if col in r.index:
                rec[col] = r[col]
        rows.append(rec)
    out = pd.DataFrame(rows).sort_values("gap_actual_usd_yr", ascending=False)
    return out.reset_index(drop=True)


def main() -> None:
    raw = load_pip_deciles()
    dist = latest_distribution(raw)
    world_pop = 7.95e9  # approx 2022-2024 world population
    covered = dist["reporting_pop"].sum()
    print(
        f"Coverage: {dist.country_code.nunique()} countries, "
        f"{covered / 1e9:.2f}B people ({100 * covered / world_pop:.0f}% of world)"
    )

    # Validation: decile-grouped gap vs PIP's own analytic poverty gap at $2.15
    # (the fetched line). PIP poverty_gap = FGT(1) = mean(max(1 - y/z, 0)), so the
    # aggregate $/yr gap = poverty_gap * line * pop * 365. The convex max() means
    # the decile-step estimate is a LOWER BOUND on the true gap.
    if "poverty_gap" in dist.columns:
        z = 2.15
        inc = np.vstack([decile_incomes(r) for _, r in dist.iterrows()])
        pop = dist["reporting_pop"].to_numpy(float)
        grouped = (pop[:, None] / 10.0 * np.maximum(z - inc, 0.0)).sum() * DAYS
        analytic = (dist["poverty_gap"].to_numpy(float) * z * pop).sum() * DAYS
        print(
            f"Validation @ $2.15: decile-grouped ${grouped/1e9:.1f}B vs "
            f"PIP-analytic ${analytic/1e9:.1f}B "
            f"(ratio {grouped/analytic:.2f}; <1 confirms grouped lower bound)"
        )

    dec = decompose(dist)
    dec.to_csv(PROC / "within_between_decomposition.csv", index=False)
    detail = country_detail(dist, T=10.0)
    detail.to_csv(PROC / "within_between_country_detail.csv", index=False)

    print("\nGood-life gap decomposition (USD/yr, 2017 PPP):")
    for _, r in dec.iterrows():
        print(
            f"  ${r.threshold_day:>5.2f}/day: total ${r.gap_actual_usd_yr/1e12:5.2f}T  "
            f"between {100*r.between_share:4.0f}%  within {100*r.within_share:4.0f}%  "
            f"surplus/gap {r.surplus_to_gap_ratio:6.1f}x"
        )

    # ── Chart 102: stacked between/within decomposition ──────────────────────
    fig, ax = plt.subplots(figsize=(12, 7))
    x = np.arange(len(dec))
    between_t = dec["gap_between_usd_yr"] / 1e12
    within_t = dec["gap_within_usd_yr"] / 1e12
    ax.bar(x, between_t, label="Between-country (poor countries)", color="#d1495b")
    ax.bar(
        x,
        within_t,
        bottom=between_t,
        label="Within-country (poor people in richer countries)",
        color="#3a7ca5",
    )
    for i, r in dec.iterrows():
        total = r.gap_actual_usd_yr / 1e12
        ax.text(
            i,
            total + 0.15,
            f"${total:.1f}T\nbtwn {100*r.between_share:.0f}%",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_xticks(x)
    ax.set_xticklabels([f"${t:g}/day" for t in dec["threshold_day"]])
    ax.set_ylabel("Annual good-life gap (US$ trillion, 2017 PPP)")
    ax.set_title(
        "Chart 102: Low lines are a within-country problem; good-life lines are\n"
        "a between-country problem (decile-grouped lower bound on the within share)",
        fontweight="bold",
    )
    ax.legend(loc="upper left")
    ax.margins(y=0.15)
    fig.tight_layout()
    fig.savefig(CHARTS / "102_within_between_gap_decomposition.png", dpi=150)
    plt.close(fig)
    print("  -> chart 102 saved")

    # ── Chart 103: redistribution feasibility ────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    wm = dec["world_mean_day"].iloc[0]
    ax1.axhline(wm, color="#2e7d32", lw=2, label=f"Covered world mean ${wm:.1f}/day")
    ax1.bar(
        [f"${t:g}" for t in dec["threshold_day"]],
        dec["threshold_day"],
        color="#bbbbbb",
        label="Threshold",
    )
    ax1.set_ylabel("Income ($/day, 2017 PPP)")
    ax1.set_title(
        "Is there enough income to clear each line\nif perfectly redistributed?",
        fontweight="bold",
    )
    ax1.legend()

    ratio = dec["surplus_to_gap_ratio"]
    colors = ["#3a7ca5" if v >= 1 else "#d1495b" for v in ratio]
    ax2.bar([f"${t:g}" for t in dec["threshold_day"]], ratio, color=colors)
    ax2.axhline(1.0, color="black", ls="--", lw=1)
    for i, v in enumerate(ratio):
        ax2.text(i, v + 0.3, f"{v:.1f}x", ha="center", fontsize=9, fontweight="bold")
    ax2.set_ylabel("PIP welfare above line ÷ shortfall below line")
    ax2.set_title(
        "Redistribution headroom in PIP welfare\n"
        "(>1 = covered survey welfare could clear the line; NOT fiscal capacity)",
        fontweight="bold",
    )
    fig.suptitle(
        "Chart 103: Redistribution headroom within covered PIP welfare\n"
        "(survey welfare, not national-account income or taxable capacity)",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "103_redistribution_feasibility.png", dpi=150)
    plt.close(fig)
    print("  -> chart 103 saved")


if __name__ == "__main__":
    main()
