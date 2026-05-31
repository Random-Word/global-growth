#!/usr/bin/env python3
"""Analysis 24: Dynamic recurring-cost transfer model with price feedback.

WHY THIS SCRIPT EXISTS
----------------------
The report's affordability claim rests on a STATIC poverty-gap number: the
one-year cost of closing the gap to a line is sum(line - income) over the poor,
optionally times a delivery multiplier (see analysis/run_analysis_18.py and
data/processed/robustness_poverty_cost_sensitivity.csv -- e.g. the $6.85 gap is
~$965B nominal at 1x = ~0.87% of world GDP). That snapshot is honest as far as
it goes, but two things make the *sustained* burden larger:

  (1) RECURRING / DEMOGRAPHIC: it is an annual cost, not one-time, and the
      below-line population grows (demography) and is hit by shocks.
  (2) PRICE FEEDBACK (general equilibrium): in the EMPIRICAL central case this
      is SMALL. Egger et al. (2022, Econometrica) measured only ~0.1-0.2% local
      price-index inflation from large cash transfers, so the central price
      leakage is essentially zero (rho ~= 0.02). Higher rho values (0.1-0.4) are
      STRESS / adverse-supply-constraint cases, NOT empirically central: they
      are stylized worst cases in which sustained national gap-clearing strains
      non-tradable supply (Balassa-Samuelson logic) and a larger fraction of
      each dollar dissipates into inflation.

This is a STYLIZED, REDUCED-FORM POLICY SIMULATION -- not a calibrated CGE
model. Every parameter is labelled with its source/justification. The point is
to show the DIRECTION and rough MAGNITUDE by which the static snapshot
understates the honest sustained cost, and under what assumptions.

PV FRAMING (read this before quoting any "20x" number): the static figure is a
current ANNUAL FLOW. Sustaining ANY flat annual flow to 2050 has a present value
of many current-year flows simply because it recurs for 26 years. We therefore
report a NO-DYNAMICS STATIC-ANNUITY PV comparator (the unchanged static gap held
flat, discounted) BESIDE the dynamic PV multiple. The static estimate is NOT off
by 20-24x; most of the multiple is annuity math (a 26-year flow), not a hidden
dynamic cost.

Outputs:
- charts/110_dynamic_transfer_trajectory.png
- charts/111_static_vs_dynamic_decomposition.png
- data/processed/dynamic_transfer_model.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
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

# ---------------------------------------------------------------------------
# MODEL PARAMETERS  (every value is justified; all are stylized assumptions)
# ---------------------------------------------------------------------------
START_YEAR = 2025
END_YEAR = 2050
YEARS = np.arange(START_YEAR, END_YEAR + 1)
HORIZON = len(YEARS)

# Real world-GDP growth. IMF WEO long-run global real growth ~2.5-3%/yr. We use
# 2.5% as a slightly conservative central path. The whole model is run in
# constant START_YEAR prices, so this is REAL growth and the price-feedback term
# below is a REAL purchasing-power erosion (extra real resources required), which
# keeps the inflation bookkeeping clean.
G_WORLD_REAL = 0.025

# Poor-population growth by line. UN WPP 2024: Sub-Saharan Africa ~2.3%/yr
# (declining slowly), South Asia ~0.8%/yr. Poverty is increasingly SSA-
# concentrated at LOWER lines, so the eligible pool grows faster there. These
# are blended, line-specific assumptions, not measured series.
G_POP_BY_LINE = {3.65: 0.020, 6.85: 0.013, 10.0: 0.011}

# Organic "graduation" drift: real income growth of the poor shrinks the gap and
# moves some people across the line each year. Historical median real income
# growth for low-income economies is ~1.5%/yr (slower than fast-growers' 2-3%).
# We treat this as the annual proportional shrink of the real gap from growth.
G_GRADUATION = 0.015

# Price pass-through. rho = share of each transfer dollar dissipated into local
# price inflation; nominal cost-to-clear multiplier m = 1/(1-rho).
# EMPIRICAL CENTRAL CASE: Egger et al. (2022, Econometrica, "General Equilibrium
# Effects of Cash Transfers") found LOCAL price effects of even large cash
# transfers are SMALL (~0.1-0.2% price-index inflation). That is a tiny
# price-INDEX move, NOT 15% of each transfer dollar leaking away. So the
# empirically central pass-through is essentially zero; we set rho_central =
# 0.02 to reflect the small measured price-index effect.
# STRESS BAND (NOT empirically central): rho in {0.1, 0.2, 0.3, 0.4} are
# stylized ADVERSE-SUPPLY-CONSTRAINT scenarios. They are justified ONLY as
# worst cases in which sustained, economy-wide gap-clearing strains non-tradable
# supply (Balassa-Samuelson logic) far beyond the localized RCT settings Egger
# studied. They are deliberately pessimistic and should not be read as central.
RHO_CENTRAL = 0.02  # empirical central (Egger: price effects are small)
RHO_STRESS = [0.1, 0.2, 0.3, 0.4]  # adverse-supply-constraint stress cases
RHO_SWEEP = [RHO_CENTRAL] + RHO_STRESS  # full sweep for the stress band

# Stochastic shock overlay. Material global/regional poverty shocks (pandemics,
# food-price spikes, conflict clusters, climate disasters) hit roughly once per
# ~8 years -> Poisson rate ~0.12/yr. Each shock pushes an extra 5-20% onto the
# below-line population (COVID added ~70-90M extreme poor ~= +8-10%), decaying
# linearly over DECAY years.
SHOCK_LAMBDA = 0.12
SHOCK_UPLIFT_RANGE = (0.05, 0.20)
SHOCK_DECAY = 3
N_SIMS = 5000
RNG = np.random.default_rng(20260530)

# Discount-rate sweep for present-value comparison (social discount rate range
# commonly used in cost-benefit / public finance: 2% low, 4% higher).
DISCOUNT_SWEEP = [0.02, 0.04]

# Denominator-sensitivity sweep for the sustained avg %-of-GDP result. The
# headline %-of-GDP DECLINE is largely a DENOMINATOR effect: world GDP grows
# 2.5%/yr while the poor's real income grows only 1.5%/yr, so the gap shrinks as
# a SHARE of a faster-growing world. These scenarios isolate that mechanism:
#   base        : central (world 2.5%, graduation 1.5%)
#   low_world   : slow world growth (1.5%) -> denominator grows slower
#   no_grad     : poor income growth = 0  -> gap does not organically shrink
#   equal_growth: poor income grows at world rate -> share roughly flat
GDP_GRADUATION_SENSITIVITY = {
    "base": {"g_world": 0.025, "g_grad": 0.015},
    "low_world_growth": {"g_world": 0.015, "g_grad": 0.015},
    "no_graduation": {"g_world": 0.025, "g_grad": 0.000},
    "equal_poor_world_growth": {"g_world": 0.025, "g_grad": 0.025},
}

LINES = [3.65, 6.85, 10.0]


def latest_per_country(dataframe: pd.DataFrame, min_year: int = 2018) -> pd.DataFrame:
    return (
        dataframe[dataframe["reporting_year"] >= min_year]
        .sort_values("reporting_year")
        .drop_duplicates("country_code", keep="last")
    )


def static_baseline(line: float, wdi: pd.DataFrame) -> dict[str, float]:
    """Reproduce the analysis_18 static, 1x, nominal poverty-gap anchor at t=0.

    World gap in PPP = poverty_gap_index * line * world_pop * 365, converted to
    nominal USD via the gap-weighted country price-level ratio (nominal/PPP), per
    analysis/ppp_nominal_conversion.py. This matches the t=0 numbers in
    data/processed/robustness_poverty_cost_sensitivity.csv (overhead = 1).
    """
    wdi_latest = (
        wdi[wdi["year"] >= 2018]
        .sort_values("year")
        .drop_duplicates("country_code", keep="last")
    )
    price = wdi_latest[["country_code", "gdp_current_usd", "gdp_ppp_current"]].dropna()
    price["price_level_ratio"] = price["gdp_current_usd"] / price["gdp_ppp_current"]

    world_rows = wdi[(wdi["country_code"] == "WLD") & wdi["gdp_current_usd"].notna()]
    world_rows = world_rows.sort_values("year")
    world_gdp_nominal = float(world_rows["gdp_current_usd"].iloc[-1])
    latest_year = int(world_rows["year"].iloc[-1])

    regional = pd.read_csv(RAW / f"pip_regional_{line}.csv")
    wld = (
        regional[
            (regional["region_code"] == "WLD")
            & (regional["reporting_year"] <= latest_year)
        ]
        .sort_values("reporting_year")
        .iloc[-1]
    )
    world_gap_ppp = float(wld["poverty_gap"] * line * wld["reporting_pop"] * 365)
    if "pop_in_poverty" in wld.index and pd.notna(wld.get("pop_in_poverty")):
        people_below = float(wld["pop_in_poverty"])
    else:
        people_below = float(wld["headcount"] * wld["reporting_pop"])

    # Gap-weighted nominal/PPP ratio from the country panel (same as analysis 18).
    pip = latest_per_country(pd.read_csv(RAW / f"pip_country_{line}.csv"))
    pip["gap_ppp"] = pip["poverty_gap"] * line * pip["reporting_pop"] * 365
    merged = pip.merge(price[["country_code", "price_level_ratio"]], on="country_code")
    merged = merged[merged["gap_ppp"] > 0]
    weighted_ratio = float(
        (merged["gap_ppp"] * merged["price_level_ratio"]).sum()
        / merged["gap_ppp"].sum()
    )
    gap_nominal = world_gap_ppp * weighted_ratio
    return {
        "gap_nominal": gap_nominal,
        "people_below": people_below,
        "world_gdp_nominal": world_gdp_nominal,
        "pct_world_gdp": gap_nominal / world_gdp_nominal * 100,
    }


def real_gap_path(
    line: float,
    g0: float,
    *,
    demographics: bool,
    graduation: bool,
    g_grad: float | None = None,
) -> np.ndarray:
    """Real (constant-price) annual gap over the horizon, before price feedback.

    Two multiplicative drivers on the t=0 gap g0:
      demographic factor (1 + g_pop)^t  -> more eligible people
      graduation factor  (1 - g_grad)^t -> organic real growth shrinks the gap
    g_grad overrides G_GRADUATION for denominator-sensitivity scenarios.
    """
    t = np.arange(HORIZON)
    g_pop = G_POP_BY_LINE[line] if demographics else 0.0
    grad = (G_GRADUATION if g_grad is None else g_grad) if graduation else 0.0
    return g0 * (1 + g_pop) ** t * (1 - grad) ** t


def world_gdp_path(gdp0: float, g_world: float = G_WORLD_REAL) -> np.ndarray:
    """Real world-GDP path in constant START_YEAR prices."""
    return gdp0 * (1 + g_world) ** np.arange(HORIZON)


def passthrough_multiplier(rho: float) -> float:
    """Nominal cost-to-clear multiplier from price dissipation: m = 1/(1-rho)."""
    return 1.0 / (1.0 - rho)


def simulate_shocks(base_path: np.ndarray) -> np.ndarray:
    """Monte Carlo overlay: temporary below-line population bumps from shocks.

    Returns an (N_SIMS, HORIZON) array of shock multipliers applied to base_path.
    """
    mult = np.ones((N_SIMS, HORIZON))
    for s in range(N_SIMS):
        n_shocks = RNG.poisson(SHOCK_LAMBDA * HORIZON)
        for _ in range(n_shocks):
            start = RNG.integers(0, HORIZON)
            uplift = RNG.uniform(*SHOCK_UPLIFT_RANGE)
            for d in range(SHOCK_DECAY):
                idx = start + d
                if idx < HORIZON:
                    mult[s, idx] += uplift * (1 - d / SHOCK_DECAY)
    return mult * base_path


def present_value(stream: np.ndarray, rate: float) -> float:
    return float(np.sum(stream / (1 + rate) ** np.arange(HORIZON)))


def main() -> None:
    print("=" * 80)
    print("ANALYSIS 24: DYNAMIC RECURRING-COST TRANSFER MODEL (stylized simulation)")
    print("=" * 80)
    wdi = pd.read_csv(PROC / "wdi_combined.csv")

    baselines = {line: static_baseline(line, wdi) for line in LINES}
    for line in LINES:
        b = baselines[line]
        print(
            f"  ${line}/day static t=0: gap=${b['gap_nominal']/1e9:,.0f}B  "
            f"= {b['pct_world_gdp']:.3f}% world GDP  "
            f"({b['people_below']/1e9:.2f}B people)"
        )

    rows: list[dict[str, float]] = []
    summary: list[dict[str, object]] = []
    chart_data: dict[float, dict[str, np.ndarray]] = {}
    # ONE stored shock simulation per line, reused by BOTH the summary waterfall
    # and the fan chart so they cannot diverge (previously separate draws caused
    # a tiny 0.76794 vs 0.76763 inconsistency).
    stored_sims: dict[float, np.ndarray] = {}

    for line in LINES:
        b = baselines[line]
        g0, gdp0 = b["gap_nominal"], b["world_gdp_nominal"]
        gdp_path = world_gdp_path(gdp0)

        # Real gap path (demographics + graduation), pre-price-feedback.
        real_path = real_gap_path(line, g0, demographics=True, graduation=True)
        m_central = passthrough_multiplier(RHO_CENTRAL)  # rho=0.02 (empirical, small)
        central_path = real_path * m_central  # add SMALL central price feedback

        # Monte Carlo shock fan around the central (price-fed) path. Store once.
        sim_paths = simulate_shocks(central_path)
        stored_sims[line] = sim_paths
        sim_pct = sim_paths / gdp_path * 100
        p10 = np.percentile(sim_pct, 10, axis=0)
        p50 = np.percentile(sim_pct, 50, axis=0)
        p90 = np.percentile(sim_pct, 90, axis=0)

        # Price-feedback band as %GDP: from the SMALL empirical central rho
        # (0.02) up to the adverse-supply-constraint STRESS case (rho=0.4). The
        # central line uses the low rho; the band shows the stress envelope.
        band_low = real_path * passthrough_multiplier(RHO_CENTRAL) / gdp_path * 100
        band_high = real_path * passthrough_multiplier(RHO_STRESS[-1]) / gdp_path * 100

        chart_data[line] = {
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "band_low": band_low,
            "band_high": band_high,
            "central_pct": central_path / gdp_path * 100,
        }

        # ---- Long CSV: per-year, central scenario + sweep summaries ----
        for i, yr in enumerate(YEARS):
            rows.append(
                {
                    "year": int(yr),
                    "line": line,
                    "rho_central": RHO_CENTRAL,
                    "real_gap_nominal_billions": real_path[i] / 1e9,
                    "central_cost_billions": central_path[i] / 1e9,
                    "mc_mean_cost_billions": float(sim_paths[:, i].mean()) / 1e9,
                    "pct_world_gdp_central": central_path[i] / gdp_path[i] * 100,
                    "pct_world_gdp_p10": p10[i],
                    "pct_world_gdp_p50": p50[i],
                    "pct_world_gdp_p90": p90[i],
                    "world_gdp_real_billions": gdp_path[i] / 1e9,
                }
            )

        # ---- PV-as-multiple-of-static, by discount rate, with MC mean shocks ----
        # Static-annuity comparator: the UNCHANGED static gap held FLAT to 2050,
        # discounted. This isolates pure annuity math (a 26-yr recurring flow)
        # from any dynamic cost, so the reader sees that most of the dynamic PV
        # multiple is simply that the flow recurs -- NOT that the static estimate
        # was wrong.
        mc_mean_path = sim_paths.mean(axis=0)
        static_annuity_path = np.full(HORIZON, g0)
        for r in DISCOUNT_SWEEP:
            pv = present_value(mc_mean_path, r)
            pv_static_annuity = present_value(static_annuity_path, r)
            summary.append(
                {
                    "line": line,
                    "discount_rate": r,
                    "static_annual_billions": g0 / 1e9,
                    "static_pct_world_gdp": b["pct_world_gdp"],
                    "pv_static_annuity_billions": pv_static_annuity / 1e9,
                    "static_annuity_multiple": pv_static_annuity / g0,
                    "pv_dynamic_billions": pv / 1e9,
                    "pv_multiple_of_static": pv / g0,
                    "dynamic_vs_annuity_extra_multiple": (pv - pv_static_annuity) / g0,
                    "dynamic_avg_pct_gdp_per_yr": float(np.mean(sim_pct)),
                    "peak_pct_gdp_p90": float(p90.max()),
                }
            )

    # ---- Decomposition for $6.85: nested-scenario average %GDP/yr waterfall ----
    line = 6.85
    b = baselines[line]
    g0, gdp0 = b["gap_nominal"], b["world_gdp_nominal"]
    gdp_path = world_gdp_path(gdp0)

    def avg_pct(path: np.ndarray) -> float:
        return float(np.mean(path / gdp_path * 100))

    snapshot = b["pct_world_gdp"]  # static one-year number (t=0)
    base_const = real_gap_path(
        line, g0, demographics=False, graduation=True
    )  # GDP-dilution + graduation
    with_demo = real_gap_path(line, g0, demographics=True, graduation=True)
    with_price = with_demo * passthrough_multiplier(RHO_CENTRAL)
    # Reuse the ONE stored simulation for $6.85 (with_price == central_path here)
    # so the waterfall and fan chart use identical draws.
    with_shocks = stored_sims[line].mean(axis=0)

    decomp = {
        "static snapshot (t=0)": snapshot,
        "+ GDP growth / graduation (denominator)": avg_pct(base_const) - snapshot,
        "+ demographics": avg_pct(with_demo) - avg_pct(base_const),
        "+ price feedback (rho=0.02, central)": avg_pct(with_price)
        - avg_pct(with_demo),
        "+ shocks": avg_pct(with_shocks) - avg_pct(with_price),
    }
    dynamic_total = avg_pct(with_shocks)
    for k, v in decomp.items():
        summary.append(
            {
                "line": line,
                "discount_rate": np.nan,
                "decomposition_step": k,
                "pct_gdp_contribution": v,
            }
        )
    summary.append(
        {
            "line": line,
            "discount_rate": np.nan,
            "decomposition_step": "= dynamic sustained avg %GDP/yr",
            "pct_gdp_contribution": dynamic_total,
        }
    )

    # ---- Price-feedback STRESS band for $6.85: contribution at each rho ----
    # Central is rho=0.02 (small, empirical). The higher rho values are adverse-
    # supply-constraint STRESS cases, reported separately so they are not read as
    # central.
    for rho in RHO_SWEEP:
        path_rho = with_demo * passthrough_multiplier(rho)
        kind = "central" if rho == RHO_CENTRAL else "stress"
        summary.append(
            {
                "line": line,
                "discount_rate": np.nan,
                "price_feedback_rho": rho,
                "price_feedback_kind": kind,
                "price_feedback_contribution_pct_gdp": avg_pct(path_rho)
                - avg_pct(with_demo),
                "avg_pct_gdp_with_price": avg_pct(path_rho),
            }
        )

    # ---- Denominator sensitivity for $6.85: sustained avg %GDP/yr ----
    # The %-of-GDP DECLINE over 2025-2050 is largely a DENOMINATOR effect (world
    # GDP grows faster than the poor's income). These rows isolate that by
    # varying world-GDP growth and graduation (poor income growth).
    for name, params in GDP_GRADUATION_SENSITIVITY.items():
        sens_gdp_path = world_gdp_path(gdp0, g_world=params["g_world"])
        sens_gap = real_gap_path(
            line, g0, demographics=True, graduation=True, g_grad=params["g_grad"]
        ) * passthrough_multiplier(RHO_CENTRAL)
        sens_avg = float(np.mean(sens_gap / sens_gdp_path * 100))
        sens_end = float(sens_gap[-1] / sens_gdp_path[-1] * 100)
        summary.append(
            {
                "line": line,
                "discount_rate": np.nan,
                "denominator_scenario": name,
                "g_world": params["g_world"],
                "g_graduation": params["g_grad"],
                "sustained_avg_pct_gdp": sens_avg,
                "pct_gdp_2025": float(sens_gap[0] / sens_gdp_path[0] * 100),
                "pct_gdp_2050": sens_end,
            }
        )

    save = lambda df, name: (
        df.to_csv(PROC / name, index=False),
        print(f"  saved data/processed/{name} ({len(df):,} rows)"),
    )[1]
    long_df = pd.DataFrame(rows)
    save(long_df, "dynamic_transfer_model.csv")
    pd.DataFrame(summary).to_csv(
        PROC / "dynamic_transfer_model_summary.csv", index=False
    )
    print("  saved data/processed/dynamic_transfer_model_summary.csv")

    # ---------------------------------------------------------------------
    # CHART 110: dynamic trajectory with price band + shock fan
    # ---------------------------------------------------------------------
    fig, axis = plt.subplots(figsize=(12, 7))
    colors = {3.65: "#4c78a8", 6.85: "#f58518", 10.0: "#54a24b"}
    for line in LINES:
        d = chart_data[line]
        c = colors[line]
        axis.fill_between(YEARS, d["band_low"], d["band_high"], color=c, alpha=0.12)
        axis.fill_between(YEARS, d["p10"], d["p90"], color=c, alpha=0.20)
        axis.plot(YEARS, d["p50"], color=c, lw=2.2, label=f"${line}/day (median)")
        axis.scatter(
            [START_YEAR],
            [baselines[line]["pct_world_gdp"]],
            color=c,
            zorder=5,
            s=40,
            edgecolor="white",
        )
    axis.set_title(
        "Chart 110: Recurring transfer cost is a sustained, not one-time, burden\n"
        "(% of world GDP/yr; light band = price pass-through rho 0.02 central -> 0.4 "
        "stress, dark band = pointwise annual shock p10-p90 across simulations)",
        fontweight="bold",
    )
    axis.set_xlabel("Year")
    axis.set_ylabel("Annual transfer cost (% of world GDP)")
    axis.legend(loc="upper left", fontsize=9)
    plt.tight_layout()
    plt.savefig(CHARTS / "110_dynamic_transfer_trajectory.png")
    plt.close()

    # ---------------------------------------------------------------------
    # CHART 111: static -> dynamic waterfall decomposition for $6.85
    # ---------------------------------------------------------------------
    fig, axis = plt.subplots(figsize=(12, 7))
    steps = list(decomp.keys()) + ["= dynamic sustained"]
    values = list(decomp.values()) + [0.0]
    cumulative = np.concatenate([[0.0], np.cumsum(list(decomp.values()))[:-1], [0.0]])
    for i, (step, val) in enumerate(zip(steps, values)):
        if step.startswith("static") or step.startswith("="):
            height = snapshot if step.startswith("static") else dynamic_total
            axis.bar(i, height, color="#333333")
            axis.text(i, height, f"{height:.3f}", ha="center", va="bottom", fontsize=9)
        else:
            color = "#54a24b" if val >= 0 else "#e45756"
            axis.bar(i, val, bottom=cumulative[i], color=color)
            axis.text(
                i,
                cumulative[i] + val,
                f"{val:+.3f}",
                ha="center",
                va="bottom" if val >= 0 else "top",
                fontsize=9,
            )
    axis.set_xticks(range(len(steps)))
    axis.set_xticklabels(steps, rotation=20, ha="right", fontsize=9)
    axis.set_ylabel("Average annual cost (% of world GDP)")
    axis.set_title(
        "Chart 111: From static snapshot to dynamic sustained cost ($6.85/day)\n"
        "decomposing the honest recurring burden, 2025-2050 "
        "(price feedback at central rho=0.02; mostly a denominator effect)",
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(CHARTS / "111_static_vs_dynamic_decomposition.png")
    plt.close()

    # ---------------------------------------------------------------------
    # CONSOLE REPORT
    # ---------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("HEADLINE ($6.85/day):")
    print(f"  static annual snapshot      : {snapshot:.3f}% of world GDP")
    print(f"  dynamic sustained average   : {dynamic_total:.3f}% of world GDP/yr")
    print("  PV FRAMING -- the static number is a current ANNUAL FLOW; sustaining")
    print("  it to 2050 has a PV of ~X current annual gaps, MOST of which is simply")
    print("  that it recurs (annuity math), NOT that the static estimate was wrong:")
    for r in DISCOUNT_SWEEP:
        row = next(
            s for s in summary if s.get("discount_rate") == r and s["line"] == 6.85
        )
        print(
            f"    @ {r:.0%}: static-annuity PV = {row['static_annuity_multiple']:.1f}x "
            f"(pure recurrence) | dynamic PV = {row['pv_multiple_of_static']:.1f}x "
            f"(extra +{row['dynamic_vs_annuity_extra_multiple']:.1f}x from dynamics)"
        )
    print("  PRICE FEEDBACK (central rho=0.02, empirical, vs stress band):")
    for s in summary:
        if s.get("line") == 6.85 and "price_feedback_rho" in s:
            print(
                f"    rho={s['price_feedback_rho']:.2f} ({s['price_feedback_kind']:<7}): "
                f"{s['price_feedback_contribution_pct_gdp']:+.4f} pts of %GDP/yr"
            )
    print("  DENOMINATOR SENSITIVITY (sustained avg %GDP/yr; the decline is a")
    print("  denominator effect -- world GDP grows faster than poor income):")
    for s in summary:
        if s.get("line") == 6.85 and "denominator_scenario" in s:
            print(
                f"    {s['denominator_scenario']:<24}: avg {s['sustained_avg_pct_gdp']:.3f}% "
                f"(2025 {s['pct_gdp_2025']:.3f}% -> 2050 {s['pct_gdp_2050']:.3f}%)"
            )
    print("  decomposition of avg %GDP/yr:")
    for k, v in decomp.items():
        print(f"    {k:<40}: {v:+.3f} pts")
    print(f"    {'= dynamic sustained':<40}: {dynamic_total:.3f}% /yr")
    print(
        "\nCAVEATS: stylized reduced-form policy simulation (NOT a calibrated CGE "
        "model); price feedback is a single-parameter pass-through proxy with a "
        "SMALL empirical central (rho=0.02, Egger 2022) and a separate adverse-"
        "supply stress band (rho 0.1-0.4); demographic, graduation, shock, and "
        "GDP-growth paths are labelled assumptions, not forecasts. The dynamic "
        "PV multiple is mostly annuity math (a 26-year recurring flow), not a "
        "correction to the static estimate."
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
