#!/usr/bin/env python3
"""
Analysis 18: Robustness Checks and Unresolved Questions
=======================================================

This script turns several caveats in the README into explicit sensitivity
tables and charts. It does not pretend to settle questions that are
institutional, normative, or technology-forecasting questions. Instead, it
separates issues that can be narrowed with available data from issues that
remain scenario assumptions.

Outputs:
- charts/91_good_life_threshold_sensitivity.png
- charts/92_poverty_cost_sensitivity.png
- charts/93_growth_share_sensitivity.png
- charts/94_nitrogen_uncertainty.png
- charts/95_material_footprint_uncertainty.png
- charts/96_development_correlates.png
- data/processed/robustness_*.csv
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

try:
    import statsmodels.formula.api as smf
except Exception:  # pragma: no cover - optional dependency in some environments
    smf = None


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


def save_table(dataframe: pd.DataFrame, name: str) -> Path:
    path = PROC / name
    dataframe.to_csv(path, index=False)
    print(f"  saved {path.relative_to(BASE)} ({len(dataframe):,} rows)")
    return path


def latest_per_country(dataframe: pd.DataFrame, min_year: int = 2018) -> pd.DataFrame:
    return (
        dataframe[dataframe["reporting_year"] >= min_year]
        .sort_values("reporting_year")
        .drop_duplicates("country_code", keep="last")
    )


def main() -> None:
    print("=" * 80)
    print("ANALYSIS 18: ROBUSTNESS CHECKS AND UNRESOLVED QUESTIONS")
    print("=" * 80)

    wdi = pd.read_csv(PROC / "wdi_combined.csv")

    # ---------------------------------------------------------------------
    # 0. Claim confidence table
    # ---------------------------------------------------------------------
    claim_confidence = pd.DataFrame(
        [
            {
                "claim": "Growth alone is too slow at meaningful poverty thresholds",
                "evidence_type": "External literature plus PIP/WDI replication",
                "status": "High confidence",
                "what_data_can_resolve": "Direction and order of magnitude are testable across poverty lines and regions.",
                "what_remains_unresolved": "Future growth incidence can change under different policy regimes.",
            },
            {
                "claim": "Growth reduced the $6.85 poverty gap as share of world GDP",
                "evidence_type": "Direct PIP/WDI calculation",
                "status": "High confidence",
                "what_data_can_resolve": "Trend is robust; level depends on PPP/GDP denominator choices.",
                "what_remains_unresolved": "Political feasibility of sustained transfers at this scale.",
            },
            {
                "claim": "$15k GDP/capita is a good-life threshold",
                "evidence_type": "Local threshold sensitivity over WDI country-years",
                "status": "Medium confidence heuristic",
                "what_data_can_resolve": "The threshold is a bracket, not a point estimate; most criteria saturate between about $10k and $20k depending on metric.",
                "what_remains_unresolved": "Causality, institutional quality, and non-market welfare not captured by GDP.",
            },
            {
                "claim": "Post-transition rich-world material footprint can fall toward 9-11 t/cap",
                "evidence_type": "Illustrative category scenario with uncertainty ranges",
                "status": "Medium confidence for 10-12 t/cap mass range; low confidence for 9 t/cap",
                "what_data_can_resolve": "Mass-budget plausibility can be bounded; the 5.9 t/cap naive mass target is hard to hit, and 9 t/cap requires optimistic category assumptions.",
                "what_remains_unresolved": "Damage-weighted ecological impact requires a formal LCA or boundary-specific model.",
            },
            {
                "claim": "Nitrogen can be brought near the boundary through a technology stack",
                "evidence_type": "Scenario uncertainty model",
                "status": "Low-to-medium confidence scenario",
                "what_data_can_resolve": "Partial measures are insufficient; meeting even the relaxed boundary depends heavily on Tier 3 interventions.",
                "what_remains_unresolved": "Breakthrough probability, adoption speed, governance, and regional runoff dynamics.",
            },
            {
                "claim": "Development successes share common ingredients",
                "evidence_type": "Panel correlations and historical case evidence",
                "status": "Medium confidence pattern, low causal certainty",
                "what_data_can_resolve": "Investment, fertility, trade, and schooling associations can be tested across growth spells.",
                "what_remains_unresolved": "Causal identification and institutional mechanisms.",
            },
            {
                "claim": "Capitalism will or will not reliably self-contain ecological damage",
                "evidence_type": "Political-economy interpretation",
                "status": "Unresolved by data alone",
                "what_data_can_resolve": "Historical track records and institutional variation can be documented.",
                "what_remains_unresolved": "Counterfactual institutional evolution and normative system choice.",
            },
        ]
    )
    save_table(claim_confidence, "robustness_claim_confidence.csv")

    # ---------------------------------------------------------------------
    # 1. Good-life threshold sensitivity
    # ---------------------------------------------------------------------
    print("\n[91] Good-life threshold sensitivity")
    recent = wdi[wdi["year"] >= 2010].copy()
    thresholds = [5000, 7500, 10000, 12500, 15000, 17500, 20000, 25000, 30000]
    criteria = {
        "life_exp_70": ("life_expectancy", lambda values: values >= 70),
        "life_exp_75": ("life_expectancy", lambda values: values >= 75),
        "under5_25": ("under5_mortality", lambda values: values <= 25),
        "electricity_90": ("electricity_access_pct", lambda values: values >= 90),
        "water_90": ("basic_water_access_pct", lambda values: values >= 90),
    }
    gdp_measures = {
        "gdppc_ppp_current": "Current PPP GDP/cap",
        "gdppc_constant_2015usd": "Constant 2015 USD GDP/cap",
    }

    good_life_rows: list[dict[str, float | int | str]] = []
    for gdp_column, gdp_label in gdp_measures.items():
        usable = recent[recent[gdp_column].notna() & (recent[gdp_column] > 0)].copy()
        for threshold in thresholds:
            above = usable[usable[gdp_column] >= threshold]
            threshold_row: dict[str, float | int | str] = {
                "gdp_measure": gdp_column,
                "gdp_label": gdp_label,
                "threshold": threshold,
                "country_years": int(len(above)),
            }
            for criterion_name, (value_column, predicate) in criteria.items():
                values = above[value_column].dropna()
                threshold_row[f"{criterion_name}_pct"] = (
                    float(predicate(values).mean() * 100) if len(values) else np.nan
                )
                threshold_row[f"{criterion_name}_n"] = int(len(values))
            combined = above.dropna(subset=["life_expectancy", "under5_mortality"])
            threshold_row["life70_under5_25_pct"] = (
                float(
                    (
                        (combined["life_expectancy"] >= 70)
                        & (combined["under5_mortality"] <= 25)
                    ).mean()
                    * 100
                )
                if len(combined)
                else np.nan
            )
            threshold_row["life70_under5_25_n"] = int(len(combined))
            good_life_rows.append(threshold_row)

    good_life = pd.DataFrame(good_life_rows)
    save_table(good_life, "robustness_good_life_thresholds.csv")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for axis, (gdp_column, gdp_label) in zip(axes, gdp_measures.items()):
        plot_data = good_life[good_life["gdp_measure"] == gdp_column]
        axis.plot(
            plot_data["threshold"] / 1000,
            plot_data["life_exp_70_pct"],
            marker="o",
            label="Life expectancy >= 70",
        )
        axis.plot(
            plot_data["threshold"] / 1000,
            plot_data["under5_25_pct"],
            marker="s",
            label="Under-5 mortality <= 25/1000",
        )
        axis.plot(
            plot_data["threshold"] / 1000,
            plot_data["life70_under5_25_pct"],
            marker="^",
            label="Both criteria",
        )
        axis.axhline(90, color="gray", linestyle="--", linewidth=1)
        axis.axvline(15, color="red", linestyle=":", linewidth=1)
        axis.set_title(gdp_label)
        axis.set_xlabel("GDP/cap threshold ($k)")
        axis.set_ylim(50, 101)
        axis.grid(True, alpha=0.3)
    axes[0].set_ylabel("Share of country-years meeting criterion (%)")
    axes[0].legend(loc="lower right", fontsize=9)
    plt.suptitle(
        "Chart 91: The good-life threshold is a bracket, not a point estimate",
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(CHARTS / "91_good_life_threshold_sensitivity.png")
    plt.close()

    # ---------------------------------------------------------------------
    # 2. Poverty cost sensitivity to line and delivery overhead
    # ---------------------------------------------------------------------
    print("\n[92] Poverty-cost sensitivity")
    wdi_latest = (
        wdi[wdi["year"] >= 2018]
        .sort_values("year")
        .drop_duplicates("country_code", keep="last")
    )
    price_levels = wdi_latest[
        ["country_code", "gdp_current_usd", "gdp_ppp_current"]
    ].dropna()
    price_levels["price_level_ratio"] = (
        price_levels["gdp_current_usd"] / price_levels["gdp_ppp_current"]
    )
    world_gdp_nominal_rows = wdi[
        (wdi["country_code"] == "WLD") & wdi["gdp_current_usd"].notna()
    ].sort_values("year")
    world_gdp_nominal = float(world_gdp_nominal_rows["gdp_current_usd"].iloc[-1])
    latest_world_gdp_year = int(world_gdp_nominal_rows["year"].iloc[-1])
    oda_nominal = 224e9
    overheads = [1, 2, 3, 5]
    poverty_cost_rows: list[dict[str, float | int]] = []
    for poverty_line in [2.15, 3.65, 6.85, 10.0]:
        regional = pd.read_csv(RAW / f"pip_regional_{poverty_line}.csv")
        world_rows = regional[
            (regional["region_code"] == "WLD")
            & (regional["reporting_year"] <= latest_world_gdp_year)
        ].copy()
        latest_world_poverty = world_rows.sort_values("reporting_year").iloc[-1]
        world_gap_ppp = float(
            latest_world_poverty["poverty_gap"]
            * poverty_line
            * latest_world_poverty["reporting_pop"]
            * 365
        )
        if "pop_in_poverty" in latest_world_poverty.index:
            world_people_below = float(latest_world_poverty["pop_in_poverty"])
        else:
            world_people_below = float(
                latest_world_poverty["headcount"]
                * latest_world_poverty["reporting_pop"]
            )

        pip_path = RAW / f"pip_country_{poverty_line}.csv"
        pip_data = latest_per_country(pd.read_csv(pip_path))
        pip_data["gap_ppp"] = (
            pip_data["poverty_gap"] * poverty_line * pip_data["reporting_pop"] * 365
        )
        pip_data["people_below"] = pip_data["headcount"] * pip_data["reporting_pop"]
        merged = pip_data.merge(
            price_levels[["country_code", "price_level_ratio"]],
            on="country_code",
            how="inner",
        )
        with_gap = merged[merged["gap_ppp"] > 0].copy()
        country_gap_ppp = float(with_gap["gap_ppp"].sum())
        country_gap_nominal = float(
            (with_gap["gap_ppp"] * with_gap["price_level_ratio"]).sum()
        )
        weighted_price_ratio = country_gap_nominal / country_gap_ppp
        gap_ppp = world_gap_ppp
        gap_nominal = world_gap_ppp * weighted_price_ratio
        people_below = world_people_below
        for overhead in overheads:
            cost_nominal = gap_nominal * overhead
            poverty_cost_rows.append(
                {
                    "poverty_line": poverty_line,
                    "overhead_multiplier": overhead,
                    "people_below_billions": people_below / 1e9,
                    "gap_ppp_billions": gap_ppp / 1e9,
                    "gap_nominal_billions": gap_nominal / 1e9,
                    "cost_nominal_billions": cost_nominal / 1e9,
                    "cost_pct_world_gdp": cost_nominal / world_gdp_nominal * 100,
                    "oda_coverage_ratio": oda_nominal / cost_nominal,
                }
            )
    poverty_cost = pd.DataFrame(poverty_cost_rows)
    save_table(poverty_cost, "robustness_poverty_cost_sensitivity.csv")

    fig, axis = plt.subplots(figsize=(12, 6))
    base_cost = poverty_cost[poverty_cost["overhead_multiplier"] == 3]
    bars = axis.bar(
        [str(value) for value in base_cost["poverty_line"]],
        base_cost["cost_pct_world_gdp"],
        color="#4c78a8",
    )
    axis.axhline(0.7, color="gray", linestyle="--", label="0.7% GNI aid target")
    for bar, value in zip(bars, base_cost["cost_pct_world_gdp"]):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    axis.set_xlabel("Poverty line ($/day, PPP)")
    axis.set_ylabel("3x delivery cost (% of world GDP, nominal)")
    axis.set_title(
        "Chart 92: Poverty-gap affordability is robust at low lines, hard at high lines"
    )
    axis.legend()
    plt.tight_layout()
    plt.savefig(CHARTS / "92_poverty_cost_sensitivity.png")
    plt.close()

    # ---------------------------------------------------------------------
    # 3. Growth-distribution sensitivity
    # ---------------------------------------------------------------------
    print("\n[93] Growth share sensitivity")
    wdi_world = wdi[wdi["country_code"] == "WLD"].copy()
    gdp_by_year = wdi_world.set_index("year")["gdp_constant_2015usd"].dropna().to_dict()
    growth_share_rows: list[dict[str, float | int]] = []
    for poverty_line in [2.15, 3.65, 6.85, 10.0]:
        regional = pd.read_csv(RAW / f"pip_regional_{poverty_line}.csv")
        world_rows = regional[regional["region_code"] == "WLD"].copy()
        world_rows = world_rows[world_rows["reporting_year"].isin(gdp_by_year.keys())]
        latest_world = world_rows.sort_values("reporting_year").iloc[-1]
        reporting_year = int(latest_world["reporting_year"])
        gap_ppp = (
            latest_world["poverty_gap"]
            * poverty_line
            * latest_world["reporting_pop"]
            * 365
        )
        gap_pct_gdp = float(gap_ppp / gdp_by_year[reporting_year] * 100)
        for poor_share_pct in [1, 2.5, 5, 10, 20]:
            required_gdp_increase_pct = gap_pct_gdp / (poor_share_pct / 100)
            required_multiple = 1 + required_gdp_increase_pct / 100
            growth_share_rows.append(
                {
                    "poverty_line": poverty_line,
                    "reporting_year": reporting_year,
                    "gap_pct_gdp": gap_pct_gdp,
                    "poor_share_of_new_income_pct": poor_share_pct,
                    "one_time_gdp_increase_pct": required_gdp_increase_pct,
                    "years_at_3pct_growth": math.log(required_multiple)
                    / math.log(1.03),
                    "years_at_5pct_growth": math.log(required_multiple)
                    / math.log(1.05),
                }
            )
    growth_share = pd.DataFrame(growth_share_rows)
    save_table(growth_share, "robustness_growth_share_sensitivity.csv")

    fig, axis = plt.subplots(figsize=(12, 6))
    for poverty_line in [2.15, 3.65, 6.85, 10.0]:
        plot_data = growth_share[growth_share["poverty_line"] == poverty_line]
        axis.plot(
            plot_data["poor_share_of_new_income_pct"],
            plot_data["one_time_gdp_increase_pct"],
            marker="o",
            label=f"${poverty_line}/day",
        )
    axis.set_yscale("log")
    axis.set_xlabel("Share of new income reaching people below line (%)")
    axis.set_ylabel("One-time GDP increase needed to fill current gap (%)")
    axis.set_title("Chart 93: The growth arithmetic is mostly distribution arithmetic")
    axis.legend(title="Poverty line")
    axis.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(CHARTS / "93_growth_share_sensitivity.png")
    plt.close()

    # ---------------------------------------------------------------------
    # 4. Nitrogen uncertainty: partial vs full intervention stack
    # ---------------------------------------------------------------------
    print("\n[94] Nitrogen pathway uncertainty")
    rng = np.random.default_rng(42)
    nitrogen_current = 150.0
    safe_bounds = {"Rockstrom_35": 35.0, "intermediate_44": 44.0, "Richardson_62": 62.0}
    interventions = {
        "combustion_nox": (5.0, 10.0, 15.0, "Tier 1/2"),
        "precision_ag": (15.0, 25.0, 40.0, "Tier 2"),
        "nitrification_inhibitors": (5.0, 12.0, 20.0, "Tier 2"),
        "cultivated_meat_feed": (0.0, 10.0, 20.0, "Tier 3"),
        "n_fixing_cereals": (0.0, 20.0, 40.0, "Tier 3"),
        "runoff_denitrification": (2.0, 8.0, 15.0, "Tier 3"),
    }
    draw_count = 50_000
    intervention_draws: dict[str, np.ndarray] = {}
    for intervention_name, (low, mode, high, _tier) in interventions.items():
        intervention_draws[intervention_name] = rng.triangular(
            low, mode, high, draw_count
        )

    tier2_reductions = (
        intervention_draws["combustion_nox"]
        + intervention_draws["precision_ag"]
        + intervention_draws["nitrification_inhibitors"]
    )
    full_reductions = tier2_reductions + sum(
        intervention_draws[name]
        for name in [
            "cultivated_meat_feed",
            "n_fixing_cereals",
            "runoff_denitrification",
        ]
    )
    tier2_final = np.maximum(nitrogen_current - tier2_reductions, 0)
    full_final = np.maximum(nitrogen_current - full_reductions, 0)
    nitrogen_rows: list[dict[str, float | str]] = []
    for scenario_name, final_values in [
        ("Tier 1-2 only", tier2_final),
        ("Full stack including Tier 3", full_final),
    ]:
        row: dict[str, float | str] = {
            "scenario": scenario_name,
            "median_final_tg_n": float(np.median(final_values)),
            "p10_final_tg_n": float(np.percentile(final_values, 10)),
            "p90_final_tg_n": float(np.percentile(final_values, 90)),
        }
        for bound_name, safe_value in safe_bounds.items():
            row[f"prob_at_or_below_{bound_name}"] = float(
                (final_values <= safe_value).mean()
            )
        nitrogen_rows.append(row)
    nitrogen_summary = pd.DataFrame(nitrogen_rows)
    save_table(nitrogen_summary, "robustness_nitrogen_uncertainty.csv")

    fig, axis = plt.subplots(figsize=(12, 6))
    axis.hist(tier2_final, bins=60, alpha=0.55, label="Tier 1-2 only")
    axis.hist(full_final, bins=60, alpha=0.55, label="Full stack including Tier 3")
    for label, safe_value in safe_bounds.items():
        axis.axvline(
            safe_value, linestyle="--", linewidth=1.5, label=label.replace("_", " ")
        )
    axis.set_xlabel("Final human nitrogen fixation after interventions (Tg N/yr)")
    axis.set_ylabel("Monte Carlo draws")
    axis.set_title(
        "Chart 94: Nitrogen closure depends on speculative Tier 3 interventions"
    )
    axis.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(CHARTS / "94_nitrogen_uncertainty.png")
    plt.close()

    # ---------------------------------------------------------------------
    # 5. Material footprint uncertainty for the 9 t/cap scenario
    # ---------------------------------------------------------------------
    print("\n[95] Material-footprint scenario uncertainty")
    material_categories = {
        "fossil_fuels": (0.0, 0.1, 0.5),
        "construction": (3.5, 4.0, 5.5),
        "biomass_food": (2.0, 2.5, 3.8),
        "metals": (1.2, 1.8, 2.8),
        "other_imports": (1.2, 1.8, 2.7),
    }
    material_draws = {
        category: rng.triangular(low, mode, high, draw_count)
        for category, (low, mode, high) in material_categories.items()
    }
    material_total = np.asarray(list(material_draws.values())).sum(axis=0)
    material_rows = [
        {
            "metric": "median_total_t_per_cap",
            "value": float(np.median(material_total)),
        },
        {
            "metric": "p10_total_t_per_cap",
            "value": float(np.percentile(material_total, 10)),
        },
        {
            "metric": "p90_total_t_per_cap",
            "value": float(np.percentile(material_total, 90)),
        },
        {"metric": "prob_below_5_9_t", "value": float(np.mean(material_total <= 5.9))},
        {"metric": "prob_below_9_0_t", "value": float(np.mean(material_total <= 9.0))},
        {
            "metric": "prob_below_11_0_t",
            "value": float(np.mean(material_total <= 11.0)),
        },
    ]
    material_summary = pd.DataFrame(material_rows)
    save_table(material_summary, "robustness_material_uncertainty.csv")

    fig, axis = plt.subplots(figsize=(12, 6))
    axis.hist(material_total, bins=70, color="#59a14f", alpha=0.75)
    axis.axvline(
        5.9, color="red", linestyle="--", label="Naive 50 Gt / 8.5B = 5.9 t/cap"
    )
    axis.axvline(
        9.0, color="black", linestyle=":", label="README illustrative target = 9 t/cap"
    )
    axis.set_xlabel("Post-transition material footprint (t/cap)")
    axis.set_ylabel("Monte Carlo draws")
    axis.set_title(
        "Chart 95: The 9 t/cap target is plausible as mass, not proven as impact"
    )
    axis.legend()
    plt.tight_layout()
    plt.savefig(CHARTS / "95_material_footprint_uncertainty.png")
    plt.close()

    # ---------------------------------------------------------------------
    # 6. Development correlates: simple growth-spell panel
    # ---------------------------------------------------------------------
    print("\n[96] Development correlates panel")
    countries = wdi[
        (wdi["country_code"].str.len() == 3)
        & ~wdi["country_code"].isin(
            [
                "WLD",
                "LIC",
                "MIC",
                "HIC",
                "LMC",
                "UMC",
                "LMY",
                "UMY",
                "EAS",
                "ECS",
                "LCN",
                "MEA",
                "SAS",
                "SSA",
                "NAC",
                "ARB",
                "CSS",
                "EMU",
                "FCS",
                "HPC",
                "IBD",
                "IBT",
                "IDA",
                "IDB",
                "IDX",
                "LDC",
                "OED",
                "PRE",
                "PST",
                "SSF",
                "SST",
            ]
        )
    ].copy()
    spell_rows: list[dict[str, float | int | str]] = []
    predictor_columns = [
        "gross_capital_formation_pct",
        "fertility_rate",
        "trade_pct_gdp",
        "fdi_pct_gdp",
        "primary_completion_pct",
        "tax_revenue_pct_gdp",
    ]
    for country_code, group in countries.groupby("country_code"):
        group = group.sort_values("year").drop_duplicates("year").set_index("year")
        for start_year in [1990, 1995, 2000, 2005, 2010]:
            end_year = start_year + 10
            if start_year not in group.index or end_year not in group.index:
                continue
            start_gdp = float(
                pd.to_numeric(
                    pd.Series([group.at[start_year, "gdppc_constant_2015usd"]]),
                    errors="coerce",
                ).iloc[0]
            )
            end_gdp = float(
                pd.to_numeric(
                    pd.Series([group.at[end_year, "gdppc_constant_2015usd"]]),
                    errors="coerce",
                ).iloc[0]
            )
            if (
                math.isnan(start_gdp)
                or math.isnan(end_gdp)
                or start_gdp <= 0
                or end_gdp <= 0
            ):
                continue
            spell_row: dict[str, float | int | str] = {
                "country_code": str(country_code),
                "country": str(group.at[start_year, "country"]),
                "start_year": start_year,
                "annual_growth": (end_gdp / start_gdp) ** (1 / 10) - 1,
            }
            window = group.loc[start_year : start_year + 4]
            for predictor in predictor_columns:
                spell_row[predictor] = float(window[predictor].mean())
            spell_rows.append(spell_row)
    spells = pd.DataFrame(spell_rows).dropna(
        subset=["annual_growth"] + predictor_columns
    )

    if smf is not None and len(spells) >= 50:
        model_data = spells.copy()
        for predictor in predictor_columns:
            std = model_data[predictor].std()
            if std and not pd.isna(std):
                model_data[f"z_{predictor}"] = (
                    model_data[predictor] - model_data[predictor].mean()
                ) / std
        formula = (
            "annual_growth ~ z_gross_capital_formation_pct + z_fertility_rate + "
            "z_trade_pct_gdp + z_fdi_pct_gdp + z_primary_completion_pct + "
            "z_tax_revenue_pct_gdp + C(start_year)"
        )
        model = smf.ols(formula, data=model_data).fit(cov_type="HC3")
        coefficient_rows = []
        for predictor in predictor_columns:
            term = f"z_{predictor}"
            coefficient_rows.append(
                {
                    "term": predictor,
                    "std_coeff_annual_growth_pct_points": model.params[term] * 100,
                    "ci_low": (model.params[term] - 1.96 * model.bse[term]) * 100,
                    "ci_high": (model.params[term] + 1.96 * model.bse[term]) * 100,
                    "p_value": model.pvalues[term],
                    "n_spells": int(model.nobs),
                    "r_squared": float(model.rsquared),
                }
            )
        development_coefficients = pd.DataFrame(coefficient_rows)
    else:
        development_coefficients = pd.DataFrame(
            columns=[
                "term",
                "std_coeff_annual_growth_pct_points",
                "ci_low",
                "ci_high",
                "p_value",
                "n_spells",
                "r_squared",
            ]
        )
    save_table(spells, "robustness_development_growth_spells.csv")
    save_table(development_coefficients, "robustness_development_correlates.csv")

    fig, axis = plt.subplots(figsize=(12, 6))
    if len(development_coefficients):
        plot_data = development_coefficients.sort_values(
            "std_coeff_annual_growth_pct_points"
        )
        positions = np.arange(len(plot_data))
        axis.errorbar(
            plot_data["std_coeff_annual_growth_pct_points"],
            positions,
            xerr=[
                plot_data["std_coeff_annual_growth_pct_points"] - plot_data["ci_low"],
                plot_data["ci_high"] - plot_data["std_coeff_annual_growth_pct_points"],
            ],
            fmt="o",
            color="#4c78a8",
            ecolor="#999999",
            capsize=4,
        )
        axis.axvline(0, color="black", linewidth=1)
        axis.set_yticks(positions)
        axis.set_yticklabels(
            [label.replace("_pct", "").replace("_", " ") for label in plot_data["term"]]
        )
        n_spells = int(plot_data["n_spells"].iloc[0])
        r_squared = float(plot_data["r_squared"].iloc[0])
        axis.set_title(
            f"Chart 96: Development ingredients are correlates, not causal proof\n"
            f"10-year growth spells, period fixed effects, n={n_spells}, R2={r_squared:.2f}"
        )
        axis.set_xlabel(
            "Standardized association with annual GDP/cap growth (percentage points)"
        )
    else:
        axis.text(0.5, 0.5, "statsmodels unavailable or insufficient data", ha="center")
        axis.set_axis_off()
    plt.tight_layout()
    plt.savefig(CHARTS / "96_development_correlates.png")
    plt.close()

    print("\nKey outputs to reference in README:")
    print("  - data/processed/robustness_claim_confidence.csv")
    print("  - data/processed/robustness_good_life_thresholds.csv")
    print("  - data/processed/robustness_nitrogen_uncertainty.csv")
    print("  - data/processed/robustness_material_uncertainty.csv")
    print("  - data/processed/robustness_development_correlates.csv")


if __name__ == "__main__":
    main()
