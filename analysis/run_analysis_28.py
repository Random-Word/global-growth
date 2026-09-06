#!/usr/bin/env python3
"""Analysis 28: Independent audit of four headline claims.

This analysis targets four places where the report's existing presentation can
be mistaken for stronger evidence than it is:

1. Historical poverty-gap affordability must put the poverty gap and world GDP
   on the same price basis. The World Bank's 2021-PPP poverty lines are divided
   by constant-2021-PPP world GDP, then the decline is decomposed into absolute
   gap contraction and growth of the GDP denominator.
2. The original development-recipe base rate waits until an entire continuous
   high-investment spell ends before starting its outcome window. That censors
   Korea, China, India, Vietnam, Bangladesh, and other continuing spells. Here a
   spell is scored after its first eight qualifying years, whether investment
   subsequently remains high or not. Symmetric low/medium-investment regimes
   provide a descriptive baseline. This is still association, not causality.
3. The legacy joint-scenario result and its assumption range are WITHDRAWN:
    the nitrogen marginal used incompatible flows and boundary definitions.
    Chart 121 and its CSV contain withdrawal notices, not probability estimates.
    Use --corrections-only to refresh these without running the other analyses.
4. The 5% growth-incidence statistic is a global-distribution result for one
    historical window, not a universal within-country pass-through rate. PIP
    decile data provide a direct descriptive check of the latter estimand.

Outputs:
- charts/118_same_basis_poverty_gap.png
- charts/119_affordability_decline_decomposition.png
- charts/120_fixed_window_investment_base_rate.png
- charts/121_joint_probability_assumption_range.png
- charts/122_pip_growth_incidence.png
- data/processed/poverty_gap_same_basis.csv
- data/processed/poverty_gap_same_basis_summary.csv
- data/processed/investment_fixed_window_events.csv
- data/processed/investment_fixed_window_summary.csv
- data/processed/joint_probability_audit.csv
- data/processed/pip_growth_incidence_spells.csv
- data/processed/pip_growth_incidence_summary.csv
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import cast

from ecological_safeguards import JOINT_REASON, withdrawal_chart, withdrawn_table

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from statsmodels.stats.proportion import proportion_confint

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

DAYS = 365.0
PPP_LINES = [3.0, 4.2, 8.3, 25.0]
MIN_REGIME_YEARS = 8
OUTCOME_HORIZON = 10
GROWTH_SUCCESS_PCT = 3.0
GAP_CLOSE_SUCCESS = 0.05


def load_world_constant_ppp() -> pd.Series:
    """World GDP in constant 2021 international dollars."""
    payload = json.loads((RAW / "wdi_gdp_ppp_constant_2021.json").read_text())
    rows = payload[1]
    values = {
        int(r["date"]): float(r["value"])
        for r in rows
        if r.get("countryiso3code") == "WLD" and r.get("value") is not None
    }
    return pd.Series(values, name="world_gdp_constant_2021_ppp").sort_index()


def same_basis_poverty_gap() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate poverty-gap/GDP with numerator and denominator in 2021 PPP."""
    world_gdp = load_world_constant_ppp()
    records: list[pd.DataFrame] = []
    summaries: list[dict] = []

    for line in PPP_LINES:
        d = pd.read_csv(RAW / f"pip_2021ppp_{line}_world.csv")
        code_col = "region_code" if "region_code" in d.columns else "country_code"
        d = d[d[code_col] == "WLD"].sort_values("reporting_year").copy()
        d["gap_2021_ppp_usd_yr"] = d["poverty_gap"] * line * d["reporting_pop"] * DAYS
        d["world_gdp_constant_2021_ppp"] = d["reporting_year"].map(world_gdp)
        d = d.dropna(subset=["world_gdp_constant_2021_ppp"])
        d["gap_pct_world_gdp_same_basis"] = (
            100 * d["gap_2021_ppp_usd_yr"] / d["world_gdp_constant_2021_ppp"]
        )
        d["poverty_line_2021_ppp"] = line
        records.append(
            d[
                [
                    "reporting_year",
                    "poverty_line_2021_ppp",
                    "reporting_pop",
                    "headcount",
                    "poverty_gap",
                    "gap_2021_ppp_usd_yr",
                    "world_gdp_constant_2021_ppp",
                    "gap_pct_world_gdp_same_basis",
                ]
            ]
        )

        first, last = d.iloc[0], d.iloc[-1]
        log_gap = float(
            np.log(last["gap_2021_ppp_usd_yr"] / first["gap_2021_ppp_usd_yr"])
        )
        log_gdp = float(
            np.log(
                last["world_gdp_constant_2021_ppp"]
                / first["world_gdp_constant_2021_ppp"]
            )
        )
        log_ratio = log_gap - log_gdp
        decline = -log_ratio
        summaries.append(
            {
                "poverty_line_2021_ppp": line,
                "start_year": int(first["reporting_year"]),
                "end_year": int(last["reporting_year"]),
                "start_gap_trillion_2021_ppp": first["gap_2021_ppp_usd_yr"] / 1e12,
                "end_gap_trillion_2021_ppp": last["gap_2021_ppp_usd_yr"] / 1e12,
                "start_gap_pct_world_gdp": first["gap_pct_world_gdp_same_basis"],
                "end_gap_pct_world_gdp": last["gap_pct_world_gdp_same_basis"],
                "log_ratio_decline": decline,
                "share_due_absolute_gap_contraction": -log_gap / decline,
                "share_due_world_gdp_growth": log_gdp / decline,
            }
        )

    panel = pd.concat(records, ignore_index=True)
    summary = pd.DataFrame(summaries)
    panel.to_csv(PROC / "poverty_gap_same_basis.csv", index=False)
    summary.to_csv(PROC / "poverty_gap_same_basis_summary.csv", index=False)
    return panel, summary


def chart_same_basis_gap(panel: pd.DataFrame, summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 7))
    for line, d in panel.groupby("poverty_line_2021_ppp"):
        ax.plot(
            d["reporting_year"],
            d["gap_pct_world_gdp_same_basis"],
            lw=2.2,
            label=f"${line:g}/day",
        )
    ax.set_yscale("log")
    ax.set_xlabel("Year")
    ax.set_ylabel("Poverty gap (% of world GDP, both in constant 2021 PPP)")
    ax.set_title(
        "Chart 118: The poverty gap became more affordable, but less dramatically\n"
        "when numerator and denominator use the same price basis",
        fontweight="bold",
    )
    ax.legend(title="2021-PPP line")
    ax.text(
        0.01,
        0.01,
        "World Bank PIP 2021-PPP gaps / WDI constant-2021-PPP world GDP. Log scale.",
        transform=ax.transAxes,
        fontsize=9,
        color="dimgray",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "118_same_basis_poverty_gap.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 7))
    x = np.arange(len(summary))
    gap_share = 100 * summary["share_due_absolute_gap_contraction"]
    gdp_share = 100 * summary["share_due_world_gdp_growth"]
    ax.bar(x, gdp_share, label="World-GDP denominator growth", color="#3a7ca5")
    ax.bar(
        x,
        gap_share,
        bottom=gdp_share,
        label="Absolute poverty-gap contraction",
        color="#f2b134",
    )
    ax.axhline(100, color="black", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels([f"${v:g}/day" for v in summary["poverty_line_2021_ppp"]])
    ax.set_ylabel("Share of log decline in gap/GDP (%)")
    ax.set_title(
        "Chart 119: Most affordability improvement at higher lines came from\n"
        "growth of world GDP, not contraction of the absolute shortfall",
        fontweight="bold",
    )
    ax.legend()
    ax.text(
        0.01,
        0.01,
        "At $25/day the absolute shortfall grew, so GDP growth accounts for >100% of the ratio decline.",
        transform=ax.transAxes,
        fontsize=9,
        color="dimgray",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "119_affordability_decline_decomposition.png")
    plt.close(fig)


def investment_bucket(value: float) -> str:
    if value < 15:
        return "low (<15%)"
    if value <= 25:
        return "medium (15-25%)"
    return "high (>25%)"


def contiguous_regimes(inv: pd.Series) -> list[tuple[str, list[int]]]:
    """Return contiguous runs in one of three annual investment buckets."""
    valid = inv.dropna().sort_index()
    runs: list[tuple[str, list[int]]] = []
    current_bucket: str | None = None
    current_years: list[int] = []
    previous_year: int | None = None

    for raw_year, value in valid.items():
        year = int(cast(int, raw_year))
        bucket = investment_bucket(float(value))
        same_run = (
            current_bucket == bucket
            and previous_year is not None
            and year == previous_year + 1
        )
        if not same_run and current_years:
            runs.append((current_bucket or "", current_years))
            current_years = []
        if not same_run:
            current_bucket = bucket
        current_years.append(year)
        previous_year = year
    if current_years:
        runs.append((current_bucket or "", current_years))
    return runs


def cagr(start: float, end: float, years: int) -> float:
    if pd.isna(start) or pd.isna(end) or start <= 0 or end <= 0:
        return np.nan
    return 100 * ((end / start) ** (1 / years) - 1)


def fixed_window_investment_events() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score regimes after the first eight qualifying years, not after run end."""
    panel = pd.read_csv(PROC / "wdi_combined.csv")
    regions = pd.read_csv(RAW / "wb_country_regions.csv")
    panel = panel.merge(
        regions[["country_code", "region"]], on="country_code", how="inner"
    )
    us_ppp = panel[panel["country_code"] == "USA"].set_index("year")[
        "gdppc_ppp_current"
    ]
    us_const = panel[panel["country_code"] == "USA"].set_index("year")[
        "gdppc_constant_2015usd"
    ]

    rows: list[dict] = []
    for cc, g in panel.groupby("country_code"):
        g = g.sort_values("year")
        by_year = g.set_index("year")
        inv = by_year["gross_capital_formation_pct"]
        gdppc = by_year["gdppc_constant_2015usd"]
        ppp = by_year["gdppc_ppp_current"]

        for bucket, run in contiguous_regimes(inv):
            if len(run) < MIN_REGIME_YEARS:
                continue
            exposure = run[:MIN_REGIME_YEARS]
            start, exposure_end = exposure[0], exposure[-1]
            outcome_end = exposure_end + OUTCOME_HORIZON
            growth = cagr(
                gdppc.get(exposure_end, np.nan),
                gdppc.get(outcome_end, np.nan),
                OUTCOME_HORIZON,
            )
            rel0 = np.nan
            rel1 = np.nan
            if (
                pd.notna(ppp.get(exposure_end, np.nan))
                and pd.notna(us_ppp.get(exposure_end, np.nan))
                and us_ppp.get(exposure_end, 0) > 0
            ):
                rel0 = cast(float, ppp.at[exposure_end]) / cast(
                    float, us_ppp.at[exposure_end]
                )
            if (
                pd.notna(ppp.get(outcome_end, np.nan))
                and pd.notna(us_ppp.get(outcome_end, np.nan))
                and us_ppp.get(outcome_end, 0) > 0
            ):
                rel1 = cast(float, ppp.at[outcome_end]) / cast(
                    float, us_ppp.at[outcome_end]
                )
            gap_close = rel1 - rel0 if pd.notna(rel0) and pd.notna(rel1) else np.nan

            start_ppp = ppp.get(start, np.nan)
            us_start_ppp = us_ppp.get(start, np.nan)
            if pd.notna(start_ppp) and pd.notna(us_start_ppp) and us_start_ppp > 0:
                start_rel_us = start_ppp / us_start_ppp
                rel_method = "ppp"
            else:
                start_const = gdppc.get(start, np.nan)
                us_start_const = us_const.get(start, np.nan)
                start_rel_us = (
                    start_const / us_start_const
                    if pd.notna(start_const)
                    and pd.notna(us_start_const)
                    and us_start_const > 0
                    else np.nan
                )
                rel_method = "constant_usd_fallback"

            scorable = pd.notna(growth) or pd.notna(gap_close)
            success = (
                (pd.notna(growth) and growth >= GROWTH_SUCCESS_PCT)
                or (pd.notna(gap_close) and gap_close >= GAP_CLOSE_SUCCESS)
                if scorable
                else np.nan
            )
            rows.append(
                {
                    "country_code": cc,
                    "country": g["country"].iloc[0],
                    "region": g["region"].iloc[0],
                    "investment_bucket": bucket,
                    "regime_start": start,
                    "minimum_qualification_end": exposure_end,
                    "full_regime_end": run[-1],
                    "full_regime_years": len(run),
                    "mean_investment_first_8y": float(inv.loc[exposure].mean()),
                    "outcome_end": outcome_end,
                    "subsequent_growth_pct": growth,
                    "frontier_gap_close": gap_close,
                    "start_rel_us": start_rel_us,
                    "start_rel_method": rel_method,
                    "developing_below_50pct_us": bool(
                        pd.notna(start_rel_us) and start_rel_us < 0.50
                    ),
                    "scorable": scorable,
                    "success": float(success) if pd.notna(success) else np.nan,
                }
            )

    events = pd.DataFrame(rows)
    events.to_csv(PROC / "investment_fixed_window_events.csv", index=False)
    scored = events[events["scorable"] & events["developing_below_50pct_us"]].copy()

    summary_rows: list[dict] = []
    order = ["low (<15%)", "medium (15-25%)", "high (>25%)"]
    samples = [
        ("All scorable events", scored),
        ("PPP-classified events", scored[scored["start_rel_method"].eq("ppp")]),
    ]
    for sample, sample_events in samples:
        for bucket in order:
            d = sample_events[sample_events["investment_bucket"] == bucket]
            n = len(d)
            k = int(d["success"].sum())
            if n:
                lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
            else:
                lo, hi = np.nan, np.nan
            summary_rows.append(
                {
                    "sample": sample,
                    "investment_bucket": bucket,
                    "n_events": n,
                    "n_success": k,
                    "success_rate": k / n if n else np.nan,
                    "success_ci_low": lo,
                    "success_ci_high": hi,
                    "mean_subsequent_growth_pct": d["subsequent_growth_pct"].mean(),
                    "median_subsequent_growth_pct": d["subsequent_growth_pct"].median(),
                    "n_countries": d["country_code"].nunique(),
                }
            )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(PROC / "investment_fixed_window_summary.csv", index=False)
    return events, summary


def chart_investment_base_rate(summary: pd.DataFrame) -> None:
    summary = summary[summary["sample"].eq("All scorable events")].copy()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    x = np.arange(len(summary))
    rate = 100 * summary["success_rate"]
    lo = 100 * (summary["success_rate"] - summary["success_ci_low"])
    hi = 100 * (summary["success_ci_high"] - summary["success_rate"])
    ax1.bar(x, rate, color=["#d1495b", "#f2b134", "#3a7ca5"])
    ax1.errorbar(x, rate, yerr=[lo, hi], fmt="none", color="black", capsize=5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(summary["investment_bucket"], rotation=15)
    ax1.set_ylabel("Success rate (%)")
    ax1.set_title("Development success after 8-year investment regimes")
    for i, r in summary.iterrows():
        ax1.text(i, 2, f"{int(r.n_success)}/{int(r.n_events)}", ha="center")

    ax2.bar(
        x,
        summary["mean_subsequent_growth_pct"],
        color=["#d1495b", "#f2b134", "#3a7ca5"],
    )
    ax2.axhline(0, color="black", lw=1)
    ax2.set_xticks(x)
    ax2.set_xticklabels(summary["investment_bucket"], rotation=15)
    ax2.set_ylabel("Mean subsequent real GDP/cap growth (%/yr)")
    ax2.set_title("Mean growth in the following 10 years")
    fig.suptitle(
        "Chart 120: Fixed-window scoring removes the censoring of continuing\n"
        "high-investment successes—but remains descriptive, not causal",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "120_fixed_window_investment_base_rate.png")
    plt.close(fig)


def joint_probability_audit() -> pd.DataFrame:
    """Retire the inherited range even if stale upstream numeric files exist."""
    PROC.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    out = withdrawn_table(JOINT_REASON)
    out.to_csv(PROC / "joint_probability_audit.csv", index=False)
    withdrawal_chart(
        CHARTS / "121_joint_probability_assumption_range.png",
        "Chart 121: Joint-probability assumption range withdrawn",
        JOINT_REASON,
    )
    return out


def pip_growth_incidence() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Estimate bottom-60 capture in comparable, positive-growth PIP spells.

    The Lakner-Milanovic 5% statistic is a share of the *global* income
    increment in one historical window. It is not the incidence of growth
    within a typical developing country. PIP decile shares let us calculate the
    latter directly: for each comparable survey pair, divide the change in the
    bottom 60%'s aggregate welfare by the change in mean welfare.
    """
    deciles = [f"decile{i}" for i in range(1, 11)]
    bottom60 = [f"decile{i}" for i in range(1, 7)]
    d = pd.read_csv(RAW / "pip_country_deciles.csv")
    d = d[
        d["reporting_level"].eq("national")
        & d["distribution_type"].isin(["micro", "group"])
    ].dropna(
        subset=[
            "mean",
            "reporting_pop",
            "comparable_spell",
            "welfare_type",
        ]
        + deciles
    )
    d = d[np.isclose(d[deciles].sum(axis=1), 1.0, atol=0.02)].copy()
    keys = ["country_code", "welfare_type", "comparable_spell"]
    d = d.sort_values(keys + ["reporting_year"]).drop_duplicates(
        keys + ["reporting_year"], keep="last"
    )

    rows: list[dict] = []
    for (country_code, welfare_type, comparable_spell), g in d.groupby(keys):
        g = g.sort_values("reporting_year")
        for i in range(1, len(g)):
            first, last = g.iloc[i - 1], g.iloc[i]
            years = int(last["reporting_year"] - first["reporting_year"])
            if years < 2 or years > 15:
                continue
            delta_mean = float(last["mean"] - first["mean"])
            if delta_mean <= 0:
                continue
            first_bottom = float(first["mean"] * first[bottom60].sum())
            last_bottom = float(last["mean"] * last[bottom60].sum())
            delta_bottom = last_bottom - first_bottom
            average_pop = float((first["reporting_pop"] + last["reporting_pop"]) / 2)
            annual_total_increment = delta_mean * average_pop / years
            annual_bottom_increment = delta_bottom * average_pop / years
            rows.append(
                {
                    "country_code": country_code,
                    "country": first["country_name"],
                    "welfare_type": welfare_type,
                    "comparable_spell": comparable_spell,
                    "start_year": int(first["reporting_year"]),
                    "end_year": int(last["reporting_year"]),
                    "years": years,
                    "delta_mean_daily_2017_ppp": delta_mean,
                    "delta_bottom60_daily_2017_ppp": delta_bottom,
                    "bottom60_capture_share": delta_bottom / delta_mean,
                    "average_reporting_pop": average_pop,
                    "annual_total_increment_weight": annual_total_increment,
                    "annual_bottom60_increment_weight": annual_bottom_increment,
                }
            )
    spells = pd.DataFrame(rows)
    spells.to_csv(PROC / "pip_growth_incidence_spells.csv", index=False)

    def summarize(label: str, sub: pd.DataFrame) -> dict:
        weighted_capture = (
            sub["annual_bottom60_increment_weight"].sum()
            / sub["annual_total_increment_weight"].sum()
        )
        by_country = sub.groupby("country_code")[
            [
                "annual_total_increment_weight",
                "annual_bottom60_increment_weight",
            ]
        ].sum()
        rng = np.random.default_rng(28)
        draws = np.empty(2_000)
        for i in range(len(draws)):
            sampled = by_country.iloc[
                rng.integers(0, len(by_country), size=len(by_country))
            ]
            draws[i] = (
                sampled["annual_bottom60_increment_weight"].sum()
                / sampled["annual_total_increment_weight"].sum()
            )
        return {
            "sample": label,
            "n_spells": len(sub),
            "n_countries": sub["country_code"].nunique(),
            "increment_weighted_bottom60_capture": weighted_capture,
            "cluster_bootstrap_ci_low": np.quantile(draws, 0.025),
            "cluster_bootstrap_ci_high": np.quantile(draws, 0.975),
            "median_bottom60_capture": sub["bottom60_capture_share"].median(),
            "p25_bottom60_capture": sub["bottom60_capture_share"].quantile(0.25),
            "p75_bottom60_capture": sub["bottom60_capture_share"].quantile(0.75),
            "share_spells_below_5pct": (sub["bottom60_capture_share"] < 0.05).mean(),
        }

    summary_rows: list[dict] = []
    for label, start_year in [
        ("All comparable spells", -np.inf),
        ("Start year >=1990", 1990),
        ("Start year >=2000", 2000),
        ("Start year >=2010", 2010),
    ]:
        sub = spells[spells["start_year"] >= start_year]
        summary_rows.append(summarize(label, sub))
    for welfare_type in ["income", "consumption"]:
        sub = spells[spells["welfare_type"].eq(welfare_type)]
        summary_rows.append(summarize(f"{welfare_type.title()} surveys", sub))
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(PROC / "pip_growth_incidence_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 7))
    plot_summary = summary.iloc[:4]
    x = np.arange(len(plot_summary))
    weighted = 100 * plot_summary["increment_weighted_bottom60_capture"]
    median = 100 * plot_summary["median_bottom60_capture"]
    ax.bar(x - 0.18, weighted, width=0.36, label="Increment-weighted", color="#3a7ca5")
    ax.bar(x + 0.18, median, width=0.36, label="Median country-spell", color="#f2b134")
    ax.errorbar(
        x - 0.18,
        weighted,
        yerr=[
            weighted - 100 * plot_summary["cluster_bootstrap_ci_low"],
            100 * plot_summary["cluster_bootstrap_ci_high"] - weighted,
        ],
        fmt="none",
        color="black",
        capsize=4,
        label="95% country-cluster bootstrap interval",
    )
    ax.axhline(
        5,
        color="#d1495b",
        ls="--",
        lw=2,
        label="5% global-window benchmark (1988-2008)",
    )
    ax.axhline(
        60,
        color="gray",
        ls=":",
        lw=1.5,
        label="Equal absolute per-person increments (60%)",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(plot_summary["sample"], rotation=12)
    ax.set_ylabel("Share of positive welfare increment reaching bottom 60% (%)")
    ax.set_title(
        "Chart 122: Within-country growth incidence is far less skewed than\n"
        "the report's 5% global-window benchmark",
        fontweight="bold",
    )
    ax.legend(fontsize=9)
    ax.text(
        0.01,
        0.01,
        "Comparable national PIP survey pairs; positive mean-growth spells only. Survey welfare, not GDP.",
        transform=ax.transAxes,
        fontsize=9,
        color="dimgray",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "122_pip_growth_incidence.png")
    plt.close(fig)
    return spells, summary


def main() -> None:
    panel, gap_summary = same_basis_poverty_gap()
    chart_same_basis_gap(panel, gap_summary)
    events, investment_summary = fixed_window_investment_events()
    chart_investment_base_rate(investment_summary)
    joint_audit = joint_probability_audit()
    _incidence_spells, incidence_summary = pip_growth_incidence()

    print("\nSame-basis poverty-gap summary:")
    print(gap_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nFixed-window investment summary (developing economies):")
    print(investment_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(
        "\nContinuing high-investment cases now scorable:",
        ", ".join(
            sorted(
                set(
                    events.loc[
                        events["investment_bucket"].eq("high (>25%)")
                        & events["country_code"].isin(
                            ["KOR", "CHN", "IND", "VNM", "BGD", "ETH"]
                        )
                        & events["scorable"],
                        "country",
                    ]
                )
            )
        ),
    )
    print("\nJoint-probability assumption audit — WITHDRAWN:")
    print(joint_audit.to_string(index=False))
    print("\nPIP bottom-60 growth-incidence audit:")
    print(incidence_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nSaved charts 118-122 and seven processed CSV artifacts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corrections-only",
        action="store_true",
        help="Refresh only the withdrawn joint-probability CSV and chart 121.",
    )
    args = parser.parse_args()
    if args.corrections_only:
        print(joint_probability_audit().to_string(index=False))
    else:
        main()
