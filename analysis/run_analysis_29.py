#!/usr/bin/env python3
# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false
"""Analysis 29: Dynamic transfer/growth strategies and growth-incidence heterogeneity.

This analysis pools the repository's PIP survey distributions and WDI panel for
two related, deliberately descriptive exercises:

1. A 26-year present-value simulation compares (a) a permanent transfer with no
   assumed market-welfare growth, (b) inclusive survey-welfare growth without a
   transfer, and (c) inclusive growth plus a transfer that immediately fills the
   remaining $6.85/day gap. Transfer outlays include delivery, behavioral-offset,
   and local-price sensitivities. Domestic capacity is the outlay divided by WDI
   tax revenue; it is an accounting ratio, not a claim that the tax can be raised.
   The investment/resource cost needed to produce growth is not observed and is
   therefore not assigned a fictitious zero cost: only targeted-transfer outlays
   are monetized.
2. Country-clustered observational regressions describe how bottom-60 capture in
   comparable PIP survey spells covaries with initial PIP inequality, WDI GDP per
   capita and growth, welfare type, region, structural shares, tax revenue, and
   basic-service coverage. No coefficient is interpreted causally.

The PIP decile cache was fetched by analysis 20 at the 2017-PPP $2.15 line;
means, shares, GDP, and deciles are line-invariant. WDI names and indicator codes
are verified in analysis/download_data.py. No institutional, commodity-export,
or labor-force variable with a verified definition exists in the pooled files,
so those requested dimensions are reported as data gaps rather than proxied.

The scenario starts in 2025, NOT an observed common-year baseline: latest
eligible 2010+ survey distributions, their PIP population/GDP values, and prior
WDI tax rates retain mixed vintages. Nothing is nowcast or rebased to 2025.
Every decile is represented by its mean. Poverty gaps and headcounts (including
the modeled closure after transfers) are decile-mean approximations, not PIP
distribution-integrated estimates. A verified subset of a local $6.85 PIP cache
may be reconciled for diagnostics only; it never calibrates the scenario.

Outputs (refreshed from local caches only):
- data/processed/dynamic_transfer_country_year.csv
- data/processed/dynamic_transfer_strategy_summary.csv
- data/processed/dynamic_transfer_sensitivity.csv
- data/processed/dynamic_transfer_baseline_countries.csv
- data/processed/dynamic_transfer_baseline_summary.csv
- data/processed/dynamic_transfer_pip_reconciliation.csv
- data/processed/dynamic_transfer_method_limits.csv
- data/processed/growth_incidence_heterogeneity_data.csv
- data/processed/growth_incidence_heterogeneity_coefficients.csv
- data/processed/growth_incidence_heterogeneity_summary.csv
- data/processed/growth_incidence_heterogeneity_variable_dictionary.csv
- charts/123_dynamic_transfer_present_value.png
- charts/124_dynamic_transfer_trajectory_capacity.png
- charts/125_growth_incidence_heterogeneity_coefficients.png
- charts/126_growth_incidence_heterogeneity_groups.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
PROC.mkdir(exist_ok=True)
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
LINE = 6.85  # 2017-PPP dollars/day, matching the cached PIP distribution basis
START_YEAR = 2025  # Scenario origin, not a common observation year or a nowcast.
END_YEAR = 2050
MODEL_YEARS = np.arange(START_YEAR, END_YEAR + 1)
DECILES = [f"decile{i}" for i in range(1, 11)]
BOTTOM60 = [f"decile{i}" for i in range(1, 7)]
BASELINE_BASIS = "mixed-vintage latest surveys; scenario 2025, not observed common-year baseline"
POVERTY_METHOD = "equal-population decile-mean approximation; not distribution-integrated PIP"
CAPACITY_BASIS = "mixed-vintage PIP GDP/population and prior WDI tax rate; scenario-scaled accounting capacity"
BENCHMARK_CACHE = "pip_country_6.85.csv"
STRATEGIES = [
    "permanent_transfer",
    "inclusive_growth_no_transfer",
    "mixed_growth_plus_transfer",
]

# These are scenarios, not estimates. The central capture value is rounded from
# analysis 28's observed income/consumption-spell results. Higher delivery and
# behavioral/local-price losses are explicitly adverse sensitivities.
SCENARIOS = {
    "central": {
        "growth": 0.025,
        "bottom60_capture": 0.35,
        "admin_delivery": 0.85,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.02,
        "discount_rate": 0.03,
    },
    "lower_growth_1.5pct": {
        "growth": 0.015,
        "bottom60_capture": 0.35,
        "admin_delivery": 0.85,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.02,
        "discount_rate": 0.03,
    },
    "higher_growth_4pct": {
        "growth": 0.040,
        "bottom60_capture": 0.35,
        "admin_delivery": 0.85,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.02,
        "discount_rate": 0.03,
    },
    "lower_bottom60_capture_25pct": {
        "growth": 0.025,
        "bottom60_capture": 0.25,
        "admin_delivery": 0.85,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.02,
        "discount_rate": 0.03,
    },
    "higher_bottom60_capture_45pct": {
        "growth": 0.025,
        "bottom60_capture": 0.45,
        "admin_delivery": 0.85,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.02,
        "discount_rate": 0.03,
    },
    "frictionless_delivery": {
        "growth": 0.025,
        "bottom60_capture": 0.35,
        "admin_delivery": 1.00,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.00,
        "discount_rate": 0.03,
    },
    "adverse_delivery_behavior_prices": {
        "growth": 0.025,
        "bottom60_capture": 0.35,
        "admin_delivery": 0.70,
        "behavioral_offset": 0.10,
        "local_price_leakage": 0.10,
        "discount_rate": 0.03,
    },
    "low_discount_2pct": {
        "growth": 0.025,
        "bottom60_capture": 0.35,
        "admin_delivery": 0.85,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.02,
        "discount_rate": 0.02,
    },
    "high_discount_5pct": {
        "growth": 0.025,
        "bottom60_capture": 0.35,
        "admin_delivery": 0.85,
        "behavioral_offset": 0.00,
        "local_price_leakage": 0.02,
        "discount_rate": 0.05,
    },
}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pip = pd.read_csv(RAW / "pip_country_deciles.csv")
    wdi = pd.read_csv(PROC / "wdi_combined.csv")
    regions = pd.read_csv(RAW / "wb_country_regions.csv")
    return pip, wdi, regions


def latest_pip_distributions(pip: pd.DataFrame) -> pd.DataFrame:
    """Latest observed national PIP decile distribution, restricted to 2010+."""
    d = pip[
        pip["reporting_level"].eq("national")
        & pip["distribution_type"].isin(["micro", "group"])
        & ~pip["is_interpolated"].fillna(False).astype(bool)
    ].dropna(
        subset=[
            "mean",
            "reporting_pop",
            "reporting_gdp",
            "welfare_type",
            "gini",
        ]
        + DECILES
    )
    d = d[
        np.isclose(d[DECILES].sum(axis=1), 1.0, atol=0.02)
        & d["reporting_year"].ge(2010)
        & d["reporting_pop"].gt(0)
        & d["reporting_gdp"].gt(0)
    ].copy()
    d = (
        d.sort_values(["country_code", "reporting_year"])
        .drop_duplicates("country_code", keep="last")
        .reset_index(drop=True)
    )
    return d


def match_prior_wdi_observation(
    wdi: pd.DataFrame,
    country_code: str,
    year: int,
    column: str,
    lookback: int = 10,
) -> tuple[float, float]:
    """Value and actual observation year in [year-lookback, year]."""
    d = wdi[
        wdi["country_code"].eq(country_code)
        & wdi["year"].between(year - lookback, year)
        & wdi[column].notna()
    ].sort_values("year")
    if not len(d):
        return np.nan, np.nan
    return float(d[column].iloc[-1]), float(d["year"].iloc[-1])


def match_prior_wdi(
    wdi: pd.DataFrame,
    country_code: str,
    year: int,
    column: str,
    lookback: int = 10,
) -> float:
    """Compatibility value-only accessor; the matching rule is unchanged."""
    return match_prior_wdi_observation(wdi, country_code, year, column, lookback)[0]


def prepare_dynamic_countries(pip: pd.DataFrame, wdi: pd.DataFrame) -> pd.DataFrame:
    d = latest_pip_distributions(pip)
    observations = [
        match_prior_wdi_observation(
            wdi, str(r.country_code), int(r.reporting_year), "tax_revenue_pct_gdp"
        )
        for r in d.itertuples()
    ]
    d["tax_revenue_pct_gdp"] = [value for value, _ in observations]
    d["tax_rate_observation_year"] = [year for _, year in observations]
    d["scenario_start_year"] = START_YEAR
    d["baseline_reporting_year"] = d["reporting_year"]
    # PIP survey_year may be fractional; preserve it rather than inventing a date.
    d["baseline_survey_year"] = d["survey_year"]
    d["baseline_age_years"] = START_YEAR - d["reporting_year"]
    d["tax_rate_age_years"] = START_YEAR - d["tax_rate_observation_year"]
    d["tax_rate_lag_from_reporting_year"] = (
        d["reporting_year"] - d["tax_rate_observation_year"]
    )
    d["baseline_basis"] = BASELINE_BASIS
    d["poverty_measure_method"] = POVERTY_METHOD
    d["tax_capacity_basis"] = CAPACITY_BASIS
    d["tax_revenue_ppp_year"] = (
        d["reporting_gdp"] * d["reporting_pop"] * d["tax_revenue_pct_gdp"] / 100
    )
    d["baseline_gdp_ppp_year"] = d["reporting_gdp"] * d["reporting_pop"]
    return d


def decile_poverty_metrics(incomes: np.ndarray, population: float) -> tuple[float, float]:
    """Annual gap and headcount from ten equal-population point masses.

    All people in a decile are assigned its mean. The convex shortfall function
    makes this a lower-bound gap for that underlying distribution (up to share
    rounding); headcount can err in either direction and moves in 10% steps per
    country. Neither measure integrates the within-decile distribution.
    """
    pop_decile = population / 10
    gap = float(np.maximum(LINE - incomes, 0).sum() * pop_decile * DAYS)
    headcount = float((incomes < LINE).sum() * pop_decile)
    return gap, headcount


def baseline_summary(countries: pd.DataFrame) -> dict[str, float | int | str]:
    """Describe the selected inputs, without aligning them to a common year."""
    pop = countries["reporting_pop"]
    return {
        "scenario_start_year": START_YEAR,
        "baseline_basis": BASELINE_BASIS,
        "poverty_measure_method": POVERTY_METHOD,
        "tax_capacity_basis": CAPACITY_BASIS,
        "n_countries": len(countries),
        "covered_population": float(pop.sum()),
        "baseline_reporting_year_min": countries["reporting_year"].min(),
        "baseline_reporting_year_max": countries["reporting_year"].max(),
        "population_weighted_baseline_age_years": float(
            (countries["baseline_age_years"] * pop).sum() / pop.sum()
        ),
        "survey_le_2019_countries": int(countries["reporting_year"].le(2019).sum()),
        "survey_le_2019_population_share": float(
            pop[countries["reporting_year"].le(2019)].sum() / pop.sum()
        ),
        "tax_rate_observation_year_min": countries["tax_rate_observation_year"].min(),
        "tax_rate_observation_year_max": countries["tax_rate_observation_year"].max(),
        "tax_data_countries": int(countries["tax_rate_observation_year"].notna().sum()),
    }


def reconcile_cached_pip(countries: pd.DataFrame, cache_path: Path) -> pd.DataFrame:
    """Optional, cache-only, same-country/year benchmark; never changes inputs.

    Require national survey rows at $6.85 with matching welfare/distribution type,
    mean, population and GDP. The gap-filled cache omits survey metadata and PPP
    conversion factors: matched line-invariant values verify consistency with the
    baseline cache, not independent certification of a PIP release or PPP vintage.
    Duplicate keys, interpolation, mismatches and absent data remain unavailable;
    never substitute a nearest year, a world aggregate, or a different PPP line.
    """
    keys = ["country_code", "reporting_year", "reporting_level", "welfare_type"]
    out = countries[keys].copy()
    metrics = [
        decile_poverty_metrics(
            np.array([getattr(r, c) for c in DECILES]) * float(r.mean) * 10,
            float(r.reporting_pop),
        )
        for r in countries.itertuples()
    ]
    out["decile_gap_annual_2017ppp"] = [gap for gap, _ in metrics]
    out["decile_headcount"] = [head for _, head in metrics]
    out["population"] = countries["reporting_pop"].to_numpy()
    out["benchmark_source"] = cache_path.name
    out["benchmark_status"] = "unavailable: cache absent"
    out["pip_gap_annual_2017ppp"] = np.nan
    out["pip_headcount"] = np.nan
    if not cache_path.is_file():
        return out
    try:
        cache = pd.read_csv(cache_path)
    except (OSError, ValueError, pd.errors.ParserError):
        out["benchmark_status"] = "unavailable: unreadable cache"
        return out
    invariants = ["mean", "reporting_pop", "reporting_gdp"]
    required = keys + invariants + [
        "poverty_line", "headcount", "poverty_gap", "distribution_type",
        "is_interpolated", "estimation_type",
    ]
    if not set(required).issubset(cache.columns):
        out["benchmark_status"] = "unavailable: missing verification columns"
        return out
    for column in invariants + ["poverty_line", "headcount", "poverty_gap"]:
        cache[column] = pd.to_numeric(cache[column], errors="coerce")
    # Reject ambiguous keys before filtering, rather than arbitrarily choosing a row.
    unique = cache.loc[~cache.duplicated(keys, keep=False), required]
    matched = countries.merge(
        unique, on=keys, how="left", suffixes=("", "_benchmark"), validate="one_to_one"
    )
    valid = (
        matched["poverty_line_benchmark"].eq(LINE)
        & matched["is_interpolated_benchmark"].eq(False)
        & matched["estimation_type_benchmark"].eq("survey")
        & matched["distribution_type"].eq(matched["distribution_type_benchmark"])
        & matched["headcount_benchmark"].between(0, 1)
        & matched["poverty_gap_benchmark"].between(0, 1)
    )
    for column in invariants:
        valid &= np.isclose(
            matched[column], matched[f"{column}_benchmark"], rtol=1e-10, atol=1e-10
        )
    valid = valid.to_numpy()
    out["benchmark_status"] = "unavailable: absent, ambiguous, or nonmatching survey row"
    out.loc[valid, "benchmark_status"] = "verified same-country/year cached survey"
    out.loc[valid, "pip_gap_annual_2017ppp"] = (
        matched.loc[valid, "poverty_gap_benchmark"]
        * matched.loc[valid, "reporting_pop"] * LINE * DAYS
    ).to_numpy()
    out.loc[valid, "pip_headcount"] = (
        matched.loc[valid, "headcount_benchmark"] * matched.loc[valid, "reporting_pop"]
    ).to_numpy()
    return out


def reconciliation_summary(reconciliation: pd.DataFrame) -> dict[str, float | int | str]:
    matched = reconciliation.dropna(subset=["pip_gap_annual_2017ppp", "pip_headcount"])
    result: dict[str, float | int | str] = {
        "baseline_decile_gap_annual_2017ppp": reconciliation["decile_gap_annual_2017ppp"].sum(),
        "baseline_decile_headcount": reconciliation["decile_headcount"].sum(),
        "benchmark_matched_countries": len(matched),
        "benchmark_matched_population_share": matched["population"].sum() / reconciliation["population"].sum(),
        "benchmark_scope": "verified matched subset only; diagnostic, not model calibration",
    }
    for metric in ["decile_gap_annual_2017ppp", "pip_gap_annual_2017ppp", "decile_headcount", "pip_headcount"]:
        result[f"matched_{metric}"] = matched[metric].sum(min_count=1)
    return result


def dynamic_method_limits() -> pd.DataFrame:
    return pd.DataFrame([
        ("baseline vintage", BASELINE_BASIS,
         "Latest eligible national distributions since 2010 are used unchanged at scenario year 2025. "
         "No common-year alignment, nowcast, or population projection; populations are fixed. "
         "Ages and the <=2019 share use PIP reporting_year; fractional source survey_year is preserved separately. "
         "Legacy country-year survey_year is an alias for reporting_year, not the fractional source date."),
        ("decile poverty and closure", POVERTY_METHOD,
         "Ten equal-population point masses; sum(max(line - decile mean, 0)) * population/10 * 365. "
         "Convexity understates the within-distribution gap (apart from rounding); headcount can err either way. "
         "An entire decile crosses at once. Zero post-transfer poverty is model closure, not demonstrated PIP closure. "
         "Existing decile shares are not renormalized; baseline rounding is retained."),
        ("GDP and tax capacity", CAPACITY_BASIS,
         "PIP reporting_gdp and reporting_pop come from each selected distribution, not observed common-year 2025 values. "
         "Their underlying source observation vintages are not separately supplied. WDI tax rates use the latest "
         "nonmissing observation in [reporting_year - 10, reporting_year], inclusive, with its year exported. "
         "Projected tax capacity is not observed 2050 revenue, fiscal feasibility, or collectible new tax. "
         "Legacy year2050_transfer_pct_observed_tax_revenue names scenario-scaled capacity."),
        ("PIP reconciliation", "optional local cache only",
         "Require unique country/reporting-year/coverage/welfare keys, survey (not interpolated) rows, $6.85, "
         "matching distribution type and mean/population/GDP. Cache omits survey metadata and PPP factors; "
         "invariant agreement verifies cache consistency, not independent PPP/release certification. "
         "Report benchmark and approximation on the same matched subset only; no calibration, downloads, "
         "nearest-year substitution, or invented full-baseline benchmark."),
        ("growth incidence and costs", "scenario, not causal estimate or forecast",
         "Equal absolute increments within bottom 60/top 40 implement capture of incremental mean welfare, "
         "not proportional distribution-neutral growth. Only targeted-transfer outlays are monetized; "
         "growth-enabling investment/resource costs remain unidentified."),
    ], columns=["element", "status", "interpretation_limit"])


def projected_decile_incomes(
    initial: np.ndarray,
    mean0: float,
    model_index: int,
    growth: float,
    bottom60_capture: float,
) -> np.ndarray:
    """Allocate cumulative national mean-welfare growth by two-group capture.

    Equal absolute increments are assigned within the bottom 60 and top 40;
    because deciles are equal-population groups, dividing each group's aggregate
    increment by 0.60 or 0.40 preserves the requested capture share. This does
    not assume pro-poor growth or identify incidence within either group.
    """
    cumulative_mean_increment = mean0 * ((1 + growth) ** model_index - 1)
    projected = initial.copy()
    projected[:6] += bottom60_capture * cumulative_mean_increment / 0.60
    projected[6:] += (1 - bottom60_capture) * cumulative_mean_increment / 0.40
    return projected


def run_dynamic_scenario(
    countries: pd.DataFrame, scenario_name: str, params: dict[str, float]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, float | int | str]] = []
    delivery = (
        params["admin_delivery"]
        * (1 - params["behavioral_offset"])
        * (1 - params["local_price_leakage"])
    )
    if delivery <= 0:
        raise ValueError(f"Non-positive net delivery in {scenario_name}")

    for r in countries.itertuples():
        initial = (
            np.array([getattr(r, c) for c in DECILES], dtype=float) * float(r.mean) * 10
        )
        for i, year in enumerate(MODEL_YEARS):
            grown = projected_decile_incomes(
                initial,
                float(r.mean),
                i,
                params["growth"],
                params["bottom60_capture"],
            )
            for strategy in STRATEGIES:
                market_income = initial if strategy == "permanent_transfer" else grown
                # Decile-mean approximation, not distribution-integrated PIP.
                net_gap, people_below = decile_poverty_metrics(
                    market_income, float(r.reporting_pop)
                )
                gross_outlay = (
                    0.0
                    if strategy == "inclusive_growth_no_transfer"
                    else net_gap / delivery
                )
                post_policy_income = (
                    market_income
                    if strategy == "inclusive_growth_no_transfer"
                    else np.maximum(market_income, LINE)
                )
                _, people_below_post = decile_poverty_metrics(
                    post_policy_income, float(r.reporting_pop)
                )
                gdp_growth = (
                    0.0 if strategy == "permanent_transfer" else params["growth"]
                )
                tax_capacity = float(r.tax_revenue_ppp_year) * (1 + gdp_growth) ** i
                rows.append(
                    {
                        "scenario": scenario_name,
                        "strategy": strategy,
                        "year": int(year),
                        "poverty_line_2017ppp_day": LINE,
                        "price_basis": "2017 PPP",
                        "country_code": r.country_code,
                        "country": r.country_name,
                        "survey_year": int(r.reporting_year),
                        "baseline_survey_year": r.baseline_survey_year,
                        "baseline_reporting_year": int(r.reporting_year),
                        "baseline_age_years": r.baseline_age_years,
                        "scenario_start_year": START_YEAR,
                        "tax_rate_observation_year": r.tax_rate_observation_year,
                        "baseline_basis": BASELINE_BASIS,
                        "poverty_measure_method": POVERTY_METHOD,
                        "tax_capacity_basis": CAPACITY_BASIS,
                        "welfare_type": r.welfare_type,
                        "population": float(r.reporting_pop),
                        "net_poverty_gap_annual_2017ppp": net_gap,
                        "gross_transfer_outlay_annual_2017ppp": gross_outlay,
                        "tax_revenue_annual_2017ppp": tax_capacity,
                        "transfer_pct_tax_revenue": (
                            100 * gross_outlay / tax_capacity
                            if tax_capacity > 0
                            else np.nan
                        ),
                        "people_below_before_transfer": people_below,
                        "people_below_after_policy": people_below_post,
                    }
                )

    detail = pd.DataFrame(rows)
    summaries: list[dict[str, float | int | str]] = []
    discount = params["discount_rate"]
    for strategy, d in detail.groupby("strategy"):
        annual = d.groupby("year", as_index=False).agg(
            gross_transfer_outlay_2017ppp=(
                "gross_transfer_outlay_annual_2017ppp",
                "sum",
            ),
            net_poverty_gap_2017ppp=("net_poverty_gap_annual_2017ppp", "sum"),
            people_below_before_transfer=("people_below_before_transfer", "sum"),
            people_below_after_policy=("people_below_after_policy", "sum"),
            covered_population=("population", "sum"),
        )
        pv = float(
            np.sum(
                annual["gross_transfer_outlay_2017ppp"].to_numpy()
                / (1 + discount) ** np.arange(len(annual))
            )
        )
        end = annual.iloc[-1]
        tax_end = d[d["year"].eq(END_YEAR)].dropna(
            subset=["tax_revenue_annual_2017ppp"]
        )
        tax_ratio = (
            100
            * tax_end["gross_transfer_outlay_annual_2017ppp"].sum()
            / tax_end["tax_revenue_annual_2017ppp"].sum()
            if len(tax_end) and tax_end["tax_revenue_annual_2017ppp"].sum() > 0
            else np.nan
        )
        eligible = tax_end[tax_end["people_below_before_transfer"].gt(0)]
        locally_manageable = eligible["transfer_pct_tax_revenue"].le(10)
        feasible_pop_share = (
            eligible.loc[locally_manageable, "people_below_before_transfer"].sum()
            / eligible["people_below_before_transfer"].sum()
            if eligible["people_below_before_transfer"].sum() > 0
            else np.nan
        )
        summaries.append(
            {
                "scenario": scenario_name,
                "strategy": strategy,
                "poverty_line_2017ppp_day": LINE,
                "price_basis": "2017 PPP",
                **baseline_summary(countries),
                **params,
                "net_delivery_fraction": delivery,
                "n_countries": countries["country_code"].nunique(),
                "covered_population": countries["reporting_pop"].sum(),
                "tax_data_countries": countries["tax_revenue_pct_gdp"].notna().sum(),
                "pv_targeted_transfer_trillion_2017ppp": pv / 1e12,
                "year0_transfer_billion_2017ppp": annual.iloc[0][
                    "gross_transfer_outlay_2017ppp"
                ]
                / 1e9,
                "year2050_transfer_billion_2017ppp": end[
                    "gross_transfer_outlay_2017ppp"
                ]
                / 1e9,
                "year2050_net_gap_billion_2017ppp": end["net_poverty_gap_2017ppp"]
                / 1e9,
                "year2050_population_below_before_transfer_share": end[
                    "people_below_before_transfer"
                ]
                / end["covered_population"],
                "year2050_population_below_after_policy_share": end[
                    "people_below_after_policy"
                ]
                / end["covered_population"],
                "year2050_transfer_pct_observed_tax_revenue": tax_ratio,
                "year2050_below_line_pop_share_in_countries_at_or_below_10pct_tax_revenue": feasible_pop_share,
                "monetized_cost_scope": "targeted transfer outlays only; growth-enabling investment cost not identified",
            }
        )
    return detail, pd.DataFrame(summaries)


def dynamic_analysis(
    pip: pd.DataFrame, wdi: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    countries = prepare_dynamic_countries(pip, wdi)
    reconciliation = reconcile_cached_pip(countries, RAW / BENCHMARK_CACHE)
    # Do not export the source cache's $2.15 headcount/gap as $6.85 diagnostics.
    baseline_columns = [
        "country_code", "country_name", "reporting_level", "welfare_type",
        "distribution_type", "mean", "reporting_pop", "reporting_gdp",
        "scenario_start_year", "baseline_reporting_year", "baseline_survey_year",
        "baseline_age_years", "tax_revenue_pct_gdp", "tax_rate_observation_year",
        "tax_rate_age_years", "tax_rate_lag_from_reporting_year",
        "baseline_gdp_ppp_year", "tax_revenue_ppp_year", "baseline_basis",
        "poverty_measure_method", "tax_capacity_basis", *DECILES,
    ]
    countries[baseline_columns].to_csv(PROC / "dynamic_transfer_baseline_countries.csv", index=False)
    pd.DataFrame([{
        **baseline_summary(countries), **reconciliation_summary(reconciliation),
    }]).to_csv(PROC / "dynamic_transfer_baseline_summary.csv", index=False)
    reconciliation.to_csv(PROC / "dynamic_transfer_pip_reconciliation.csv", index=False)
    dynamic_method_limits().to_csv(PROC / "dynamic_transfer_method_limits.csv", index=False)
    all_summaries: list[pd.DataFrame] = []
    central_detail: pd.DataFrame | None = None
    for name, params in SCENARIOS.items():
        detail, summary = run_dynamic_scenario(countries, name, params)
        all_summaries.append(summary)
        if name == "central":
            central_detail = detail
    assert central_detail is not None
    sensitivity = pd.concat(all_summaries, ignore_index=True)
    central_summary = sensitivity[sensitivity["scenario"].eq("central")].copy()
    central_detail.to_csv(PROC / "dynamic_transfer_country_year.csv", index=False)
    central_summary.to_csv(PROC / "dynamic_transfer_strategy_summary.csv", index=False)
    sensitivity.to_csv(PROC / "dynamic_transfer_sensitivity.csv", index=False)
    chart_dynamic_present_value(sensitivity)
    chart_dynamic_trajectory(central_detail)
    return central_summary, sensitivity


def chart_dynamic_present_value(sensitivity: pd.DataFrame) -> None:
    plot = sensitivity[
        sensitivity["strategy"].isin(
            ["permanent_transfer", "mixed_growth_plus_transfer"]
        )
    ].copy()
    central = plot[plot["scenario"].eq("central")].set_index("strategy")
    sensitivity_only = plot[~plot["scenario"].eq("central")]
    order = ["permanent_transfer", "mixed_growth_plus_transfer"]
    labels = [
        "Permanent transfer\n(no assumed growth)",
        "Mixed\n(inclusive growth + top-up)",
    ]
    x = np.arange(2)
    vals = central.loc[order, "pv_targeted_transfer_trillion_2017ppp"]
    low = (
        sensitivity_only.groupby("strategy")["pv_targeted_transfer_trillion_2017ppp"]
        .min()
        .reindex(order)
    )
    high = (
        sensitivity_only.groupby("strategy")["pv_targeted_transfer_trillion_2017ppp"]
        .max()
        .reindex(order)
    )
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.bar(x, vals, color=["#d1495b", "#3a7ca5"], width=0.62)
    ax.errorbar(
        x, vals, yerr=[vals - low, high - vals], fmt="none", color="black", capsize=7
    )
    for i, value in enumerate(vals):
        ax.text(i, value + 0.25, f"${value:.1f}T", ha="center", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Present value of targeted-transfer outlays (trillion 2017-PPP $)")
    ax.set_title(
        "Chart 123: Inclusive growth can phase down transfer outlays, but its own\n"
        "investment/resource cost is not identified (bars: central; whiskers: sensitivity range)",
        fontweight="bold",
    )
    ax.text(
        0.01,
        0.015,
        "$6.85/day; decile-mean gap approximation, not distribution-integrated PIP.\n"
        "2025–2050 scenario: mixed-vintage surveys/GDP/tax rates, not a common-year 2025 baseline.\n"
        "Whiskers vary growth, incidence, delivery, behavior, prices, and discounting.",
        transform=ax.transAxes,
        fontsize=9,
        color="dimgray",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 2},
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "123_dynamic_transfer_present_value.png")
    plt.close(fig)


def chart_dynamic_trajectory(detail: pd.DataFrame) -> None:
    annual = detail.groupby(["strategy", "year"], as_index=False).agg(
        transfer=("gross_transfer_outlay_annual_2017ppp", "sum"),
        below=("people_below_before_transfer", "sum"),
        pop=("population", "sum"),
    )
    labels = {
        "permanent_transfer": "Permanent transfer",
        "inclusive_growth_no_transfer": "Inclusive growth only",
        "mixed_growth_plus_transfer": "Mixed growth + transfer",
    }
    colors = {
        "permanent_transfer": "#d1495b",
        "inclusive_growth_no_transfer": "#f2b134",
        "mixed_growth_plus_transfer": "#3a7ca5",
    }
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    for strategy in STRATEGIES:
        d = annual[annual["strategy"].eq(strategy)]
        if strategy != "inclusive_growth_no_transfer":
            ax1.plot(
                d["year"],
                d["transfer"] / 1e12,
                lw=2.4,
                color=colors[strategy],
                label=labels[strategy],
            )
        if strategy == "permanent_transfer":
            ax2.plot(
                d["year"],
                100 * d["below"] / d["pop"],
                lw=2.4,
                color=colors[strategy],
                label=labels[strategy],
            )
        elif strategy == "inclusive_growth_no_transfer":
            # Growth-only and mixed have exactly the same market distribution
            # before the mixed strategy's top-up, so draw that path once rather
            # than hiding one identical line beneath the other.
            ax2.plot(
                d["year"],
                100 * d["below"] / d["pop"],
                lw=2.4,
                color=colors[strategy],
                label="Inclusive-growth market path\n(growth-only and mixed)",
            )
    ax1.set_title("Gross targeted-transfer outlay (decile approximation)")
    ax1.set_ylabel("Trillion 2017-PPP $ / year")
    ax1.set_xlabel("Model year")
    ax1.legend()
    ax2.set_title("Below line before top-up (decile approximation)")
    ax2.set_ylabel("Share of covered population (%)")
    ax2.set_xlabel("Model year")
    ax2.legend()
    fig.suptitle(
        "Chart 124: Top-ups close the decile-mean gap; inclusive growth changes the recurring burden\n"
        "(central assumptions: 2.5% survey-welfare growth, 35% bottom-60 capture, 85% delivery)",
        fontweight="bold",
    )
    fig.text(
        0.5, 0.01,
        "Scenario 2025 is not an observed common-year baseline: mixed-vintage surveys, GDP and tax rates.\n"
        "Headcounts and gaps approximate PIP; within-decile poverty is not resolved.",
        ha="center", fontsize=9, color="dimgray",
    )
    fig.tight_layout(rect=(0, 0.075, 1, 1))
    fig.savefig(CHARTS / "124_dynamic_transfer_trajectory_capacity.png")
    plt.close(fig)


def wdi_window_mean(
    wdi_country: pd.DataFrame, column: str, start: int, end: int
) -> float:
    values = wdi_country.loc[wdi_country["year"].between(start, end), column].dropna()
    return float(values.mean()) if len(values) else np.nan


def wdi_endpoint(
    wdi_country: pd.DataFrame, column: str, year: int, tolerance: int = 1
) -> float:
    d = wdi_country[
        wdi_country["year"].between(year - tolerance, year + tolerance)
        & wdi_country[column].notna()
    ].copy()
    if not len(d):
        return np.nan
    d["distance"] = (d["year"] - year).abs()
    return float(d.sort_values(["distance", "year"])[column].iloc[0])


def build_heterogeneity_spells(
    pip: pd.DataFrame, wdi: pd.DataFrame, regions: pd.DataFrame
) -> pd.DataFrame:
    d = pip[
        pip["reporting_level"].eq("national")
        & pip["distribution_type"].isin(["micro", "group"])
        & ~pip["is_interpolated"].fillna(False).astype(bool)
    ].dropna(
        subset=["mean", "reporting_pop", "comparable_spell", "welfare_type", "gini"]
        + DECILES
    )
    d = d[np.isclose(d[DECILES].sum(axis=1), 1.0, atol=0.02)].copy()
    keys = ["country_code", "welfare_type", "comparable_spell"]
    d = d.sort_values(keys + ["reporting_year"]).drop_duplicates(
        keys + ["reporting_year"], keep="last"
    )
    region_map = regions.set_index("country_code")["region"].to_dict()
    wdi_groups = {cc: g.sort_values("year") for cc, g in wdi.groupby("country_code")}
    rows: list[dict[str, float | int | str]] = []
    for (country_code, welfare_type, comparable_spell), g in d.groupby(keys):
        g = g.sort_values("reporting_year")
        wc = wdi_groups.get(country_code, pd.DataFrame(columns=wdi.columns))
        for i in range(1, len(g)):
            first, last = g.iloc[i - 1], g.iloc[i]
            start, end = int(first["reporting_year"]), int(last["reporting_year"])
            years = end - start
            if years < 2 or years > 15 or start < 1990:
                continue
            delta_mean = float(last["mean"] - first["mean"])
            if delta_mean <= 0 or first["mean"] <= 0:
                continue
            survey_growth = (
                float(last["mean"] / first["mean"]) ** (1 / years) - 1
            ) * 100
            first_bottom = float(first["mean"] * first[BOTTOM60].sum())
            last_bottom = float(last["mean"] * last[BOTTOM60].sum())
            capture = (last_bottom - first_bottom) / delta_mean
            gdppc_start = wdi_endpoint(wc, "gdppc_constant_2015usd", start)
            gdppc_end = wdi_endpoint(wc, "gdppc_constant_2015usd", end)
            gdppc_growth = (
                ((gdppc_end / gdppc_start) ** (1 / years) - 1) * 100
                if gdppc_start > 0 and gdppc_end > 0
                else np.nan
            )
            service_values = [
                wdi_window_mean(wc, c, start - 2, start)
                for c in [
                    "basic_water_access_pct",
                    "basic_sanitation_pct",
                    "electricity_access_pct",
                ]
            ]
            available_services = [v for v in service_values if pd.notna(v)]
            initial_services = (
                float(np.mean(available_services))
                if len(available_services) >= 2
                else np.nan
            )
            agri_start = wdi_window_mean(wc, "agriculture_va_pct", start - 2, start)
            agri_end = wdi_window_mean(wc, "agriculture_va_pct", end - 1, end + 1)
            rows.append(
                {
                    "country_code": country_code,
                    "country": first["country_name"],
                    "region": region_map.get(country_code, np.nan),
                    "welfare_type": welfare_type,
                    "comparable_spell": comparable_spell,
                    "start_year": start,
                    "end_year": end,
                    "years": years,
                    "bottom60_capture_share": capture,
                    "bottom60_capture_pct": 100 * capture,
                    "annual_survey_welfare_growth_pct": survey_growth,
                    "initial_pip_gini": float(first["gini"]),
                    "initial_gdppc_constant_2015usd": gdppc_start,
                    "annual_wdi_gdppc_growth_pct": gdppc_growth,
                    "initial_agriculture_va_pct": agri_start,
                    "agriculture_va_change_pct_points": (
                        agri_end - agri_start
                        if pd.notna(agri_start) and pd.notna(agri_end)
                        else np.nan
                    ),
                    "initial_manufacturing_va_pct": wdi_window_mean(
                        wc, "manufacturing_va_pct", start - 2, start
                    ),
                    "initial_tax_revenue_pct_gdp": wdi_window_mean(
                        wc, "tax_revenue_pct_gdp", start - 5, start
                    ),
                    "initial_basic_services_pct": initial_services,
                    "initial_trade_pct_gdp": wdi_window_mean(
                        wc, "trade_pct_gdp", start - 2, start
                    ),
                    "average_reporting_pop": float(
                        (first["reporting_pop"] + last["reporting_pop"]) / 2
                    ),
                }
            )
    out = pd.DataFrame(rows)
    out["main_sample"] = (
        out["annual_survey_welfare_growth_pct"].ge(1.0)
        & out["bottom60_capture_share"].between(0, 1)
        & out["region"].notna()
        & out["initial_gdppc_constant_2015usd"].gt(0)
    )
    out["initial_gini_10point"] = out["initial_pip_gini"] / 0.10
    out["log2_initial_gdppc"] = np.log2(out["initial_gdppc_constant_2015usd"])
    out["initial_agriculture_10point"] = out["initial_agriculture_va_pct"] / 10
    out["agriculture_change_10point"] = out["agriculture_va_change_pct_points"] / 10
    out["initial_manufacturing_10point"] = out["initial_manufacturing_va_pct"] / 10
    out["initial_tax_10point"] = out["initial_tax_revenue_pct_gdp"] / 10
    out["initial_services_10point"] = out["initial_basic_services_pct"] / 10
    out["initial_trade_10point"] = out["initial_trade_pct_gdp"] / 10
    return out


MODEL_SPECS = {
    "base": (
        "bottom60_capture_pct ~ initial_gini_10point + log2_initial_gdppc + "
        "annual_survey_welfare_growth_pct + annual_wdi_gdppc_growth_pct + "
        "C(welfare_type) + C(region) + C(start_decade)"
    ),
    "structural": (
        "bottom60_capture_pct ~ initial_gini_10point + log2_initial_gdppc + "
        "annual_survey_welfare_growth_pct + annual_wdi_gdppc_growth_pct + "
        "initial_agriculture_10point + agriculture_change_10point + "
        "initial_manufacturing_10point + initial_trade_10point + "
        "C(welfare_type) + C(region) + C(start_decade)"
    ),
    "fiscal_services": (
        "bottom60_capture_pct ~ initial_gini_10point + log2_initial_gdppc + "
        "annual_survey_welfare_growth_pct + annual_wdi_gdppc_growth_pct + "
        "initial_tax_10point + initial_services_10point + "
        "C(welfare_type) + C(region) + C(start_decade)"
    ),
}

MODEL_REQUIRED = {
    "base": [
        "bottom60_capture_pct",
        "initial_gini_10point",
        "log2_initial_gdppc",
        "annual_survey_welfare_growth_pct",
        "annual_wdi_gdppc_growth_pct",
        "welfare_type",
        "region",
        "start_decade",
        "country_code",
    ],
    "structural": [
        "bottom60_capture_pct",
        "initial_gini_10point",
        "log2_initial_gdppc",
        "annual_survey_welfare_growth_pct",
        "annual_wdi_gdppc_growth_pct",
        "initial_agriculture_10point",
        "agriculture_change_10point",
        "initial_manufacturing_10point",
        "initial_trade_10point",
        "welfare_type",
        "region",
        "start_decade",
        "country_code",
    ],
    "fiscal_services": [
        "bottom60_capture_pct",
        "initial_gini_10point",
        "log2_initial_gdppc",
        "annual_survey_welfare_growth_pct",
        "annual_wdi_gdppc_growth_pct",
        "initial_tax_10point",
        "initial_services_10point",
        "welfare_type",
        "region",
        "start_decade",
        "country_code",
    ],
}

TERM_LABELS = {
    "initial_gini_10point": "Initial PIP Gini (+10 points)",
    "log2_initial_gdppc": "Initial real GDP/cap (doubling)",
    "annual_survey_welfare_growth_pct": "Survey-welfare growth (+1 pp/yr)",
    "annual_wdi_gdppc_growth_pct": "WDI GDP/cap growth (+1 pp/yr)",
    "initial_agriculture_10point": "Initial agriculture VA (+10 pp)",
    "agriculture_change_10point": "Agriculture VA change (+10 pp)",
    "initial_manufacturing_10point": "Initial manufacturing VA (+10 pp)",
    "initial_trade_10point": "Initial trade/GDP (+10 pp)",
    "initial_tax_10point": "Initial tax revenue/GDP (+10 pp)",
    "initial_services_10point": "Initial basic services (+10 pp)",
}


def fit_clustered_models(spells: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    main = spells[spells["main_sample"]].copy()
    main["start_decade"] = (main["start_year"] // 10) * 10
    coefficient_rows: list[dict[str, float | int | str]] = []
    model_rows: list[dict[str, float | int | str]] = []

    for model_name, formula in MODEL_SPECS.items():
        model_data = main.dropna(subset=MODEL_REQUIRED[model_name]).copy()
        model = smf.ols(formula, data=model_data).fit(
            cov_type="cluster",
            cov_kwds={"groups": model_data["country_code"]},
        )
        ci = model.conf_int()
        for term in TERM_LABELS:
            if term in model.params.index:
                coefficient_rows.append(
                    {
                        "sample": "main_growth_ge_1pct_capture_0to100",
                        "model": model_name,
                        "term": term,
                        "term_label": TERM_LABELS[term],
                        "coefficient_capture_percentage_points": model.params[term],
                        "cluster_se": model.bse[term],
                        "ci_low": ci.loc[term, 0],
                        "ci_high": ci.loc[term, 1],
                        "p_value": model.pvalues[term],
                        "n_spells": int(model.nobs),
                        "n_countries": int(model_data["country_code"].nunique()),
                        "r_squared": model.rsquared,
                        "uncertainty": "country-clustered",
                        "interpretation": "observational association; not causal",
                    }
                )
        model_rows.append(
            {
                "sample": "main_growth_ge_1pct_capture_0to100",
                "model": model_name,
                "n_spells": int(model.nobs),
                "n_countries": int(model_data["country_code"].nunique()),
                "r_squared": model.rsquared,
            }
        )

    # Robustness uses the base covariates and keeps low-growth/outlying spells by
    # winsorizing the ratio rather than silently treating unstable denominators
    # as precise. Country-balanced WLS prevents frequent-survey countries from
    # dominating the check.
    robust = spells[
        spells["annual_survey_welfare_growth_pct"].ge(0.5)
        & spells["region"].notna()
        & spells["initial_gdppc_constant_2015usd"].gt(0)
    ].copy()
    robust["start_decade"] = (robust["start_year"] // 10) * 10
    lo, hi = robust["bottom60_capture_pct"].quantile([0.01, 0.99])
    robust["bottom60_capture_pct"] = robust["bottom60_capture_pct"].clip(lo, hi)
    robust["country_weight"] = 1 / robust.groupby("country_code")[
        "country_code"
    ].transform("size")
    formula = MODEL_SPECS["base"]
    robust_model_data = robust.dropna(subset=MODEL_REQUIRED["base"]).copy()
    robust_model = smf.wls(
        formula,
        data=robust_model_data,
        weights=robust_model_data["country_weight"],
    ).fit(
        cov_type="cluster",
        cov_kwds={"groups": robust_model_data["country_code"]},
    )
    ci = robust_model.conf_int()
    for term in TERM_LABELS:
        if term in robust_model.params.index:
            coefficient_rows.append(
                {
                    "sample": "robust_growth_ge_0.5pct_winsorized_country_balanced",
                    "model": "base_robustness",
                    "term": term,
                    "term_label": TERM_LABELS[term],
                    "coefficient_capture_percentage_points": robust_model.params[term],
                    "cluster_se": robust_model.bse[term],
                    "ci_low": ci.loc[term, 0],
                    "ci_high": ci.loc[term, 1],
                    "p_value": robust_model.pvalues[term],
                    "n_spells": int(robust_model.nobs),
                    "n_countries": int(robust_model_data["country_code"].nunique()),
                    "r_squared": robust_model.rsquared,
                    "uncertainty": "country-clustered",
                    "interpretation": "observational robustness association; not causal",
                }
            )
    model_rows.append(
        {
            "sample": "robust_growth_ge_0.5pct_winsorized_country_balanced",
            "model": "base_robustness",
            "n_spells": int(robust_model.nobs),
            "n_countries": int(robust_model_data["country_code"].nunique()),
            "r_squared": robust_model.rsquared,
        }
    )
    return pd.DataFrame(coefficient_rows), pd.DataFrame(model_rows)


def heterogeneity_dictionary() -> pd.DataFrame:
    rows = [
        (
            "bottom60_capture_share",
            "Change in bottom-60 aggregate PIP welfare divided by change in national mean welfare",
            "PIP deciles",
            "Outcome; unstable when total growth is near zero",
        ),
        (
            "initial_pip_gini",
            "Initial survey Gini, 0-1",
            "PIP gini",
            "Observed at spell start",
        ),
        (
            "initial_gdppc_constant_2015usd",
            "Real GDP per capita in constant 2015 US$",
            "WDI NY.GDP.PCAP.KD",
            "Nearest observation within one year",
        ),
        (
            "annual_wdi_gdppc_growth_pct",
            "Annualized real GDP-per-capita growth over survey spell",
            "WDI NY.GDP.PCAP.KD",
            "Descriptive national-accounts growth",
        ),
        (
            "annual_survey_welfare_growth_pct",
            "Annualized growth in PIP survey mean income/consumption",
            "PIP mean",
            "Not GDP growth",
        ),
        (
            "initial_agriculture_va_pct",
            "Agriculture, forestry and fishing value added (% GDP)",
            "WDI NV.AGR.TOTL.ZS",
            "Three-year initial mean",
        ),
        (
            "agriculture_va_change_pct_points",
            "End minus initial agriculture value-added share",
            "WDI NV.AGR.TOTL.ZS",
            "Structural-change proxy, not labor movement",
        ),
        (
            "initial_manufacturing_va_pct",
            "Manufacturing value added (% GDP)",
            "WDI NV.IND.MANF.ZS",
            "Three-year initial mean",
        ),
        (
            "initial_tax_revenue_pct_gdp",
            "Tax revenue excluding social contributions (% GDP)",
            "WDI GC.TAX.TOTL.GD.ZS",
            "Up-to-six-year initial mean; not total OECD tax",
        ),
        (
            "initial_basic_services_pct",
            "Mean of water, sanitation, electricity access when at least two are observed",
            "WDI SH.H2O.BASW.ZS; SH.STA.BASS.ZS; EG.ELC.ACCS.ZS",
            "Descriptive public/service coverage; delivery need not be public",
        ),
        (
            "initial_trade_pct_gdp",
            "Exports plus imports (% GDP)",
            "WDI NE.TRD.GNFS.ZS",
            "Openness, not commodity dependence",
        ),
        (
            "region",
            "World Bank country region",
            "data/raw/wb_country_regions.csv",
            "Region fixed effects",
        ),
        (
            "welfare_type",
            "PIP survey welfare concept: income or consumption",
            "PIP welfare_type",
            "Included as fixed effect",
        ),
        (
            "unavailable_requested_dimensions",
            "Commodity dependence; labor/sectoral employment; verified institutional-quality index",
            "Not present in pooled repository panel",
            "Not estimated and not replaced by an invented proxy",
        ),
    ]
    return pd.DataFrame(
        rows, columns=["variable", "definition", "source", "use_or_caveat"]
    )


def heterogeneity_analysis(
    pip: pd.DataFrame, wdi: pd.DataFrame, regions: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    spells = build_heterogeneity_spells(pip, wdi, regions)
    coefficients, model_summary = fit_clustered_models(spells)
    main = spells[spells["main_sample"]]
    descriptive = pd.DataFrame(
        [
            {
                "sample": "all_positive_growth_spells_starting_1990",
                "n_spells": len(spells),
                "n_countries": spells["country_code"].nunique(),
                "median_capture_share": spells["bottom60_capture_share"].median(),
                "main_sample_share": spells["main_sample"].mean(),
            },
            {
                "sample": "main_growth_ge_1pct_capture_0to100",
                "n_spells": len(main),
                "n_countries": main["country_code"].nunique(),
                "median_capture_share": main["bottom60_capture_share"].median(),
                "main_sample_share": 1.0,
            },
        ]
    )
    summary = pd.concat([descriptive, model_summary], ignore_index=True, sort=False)
    spells.to_csv(PROC / "growth_incidence_heterogeneity_data.csv", index=False)
    coefficients.to_csv(
        PROC / "growth_incidence_heterogeneity_coefficients.csv", index=False
    )
    summary.to_csv(PROC / "growth_incidence_heterogeneity_summary.csv", index=False)
    heterogeneity_dictionary().to_csv(
        PROC / "growth_incidence_heterogeneity_variable_dictionary.csv", index=False
    )
    chart_heterogeneity_coefficients(coefficients)
    chart_heterogeneity_groups(main)
    return spells, coefficients, summary


def chart_heterogeneity_coefficients(coefficients: pd.DataFrame) -> None:
    plot = coefficients[
        coefficients["model"].isin(["base", "structural", "fiscal_services"])
    ].copy()
    terms = list(dict.fromkeys(plot["term_label"]))
    y_map = {term: i for i, term in enumerate(reversed(terms))}
    offsets = {"base": -0.18, "structural": 0.0, "fiscal_services": 0.18}
    colors = {"base": "#3a7ca5", "structural": "#f2b134", "fiscal_services": "#59a14f"}
    fig, ax = plt.subplots(figsize=(12, 8))
    for model_name, d in plot.groupby("model"):
        y = np.array([y_map[t] + offsets[model_name] for t in d["term_label"]])
        ax.errorbar(
            d["coefficient_capture_percentage_points"],
            y,
            xerr=[
                d["coefficient_capture_percentage_points"] - d["ci_low"],
                d["ci_high"] - d["coefficient_capture_percentage_points"],
            ],
            fmt="o",
            capsize=3,
            color=colors[model_name],
            label=f"{model_name} (n={int(d['n_spells'].iloc[0])})",
        )
    ax.axvline(0, color="black", lw=1)
    ax.set_yticks(range(len(terms)))
    ax.set_yticklabels(list(reversed(terms)))
    ax.set_xlabel(
        "Associated change in bottom-60 capture (percentage points; 95% country-clustered CI)"
    )
    ax.set_title(
        "Chart 125: Growth-incidence correlates are imprecise and specification-sensitive\n"
        "(observational PIP spells; coefficients are associations, not causal effects)",
        fontweight="bold",
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS / "125_growth_incidence_heterogeneity_coefficients.png")
    plt.close(fig)


def chart_heterogeneity_groups(main: pd.DataFrame) -> None:
    d = main.copy()
    d["gini_quartile"] = pd.qcut(
        d["initial_pip_gini"],
        4,
        labels=["Lowest", "Lower-middle", "Upper-middle", "Highest"],
    )
    gini = (
        d.groupby("gini_quartile", observed=True)
        .agg(
            median=("bottom60_capture_pct", "median"),
            p25=("bottom60_capture_pct", lambda x: x.quantile(0.25)),
            p75=("bottom60_capture_pct", lambda x: x.quantile(0.75)),
            n=("bottom60_capture_pct", "size"),
        )
        .reset_index()
    )
    region = (
        d.groupby("region")
        .agg(
            median=("bottom60_capture_pct", "median"),
            n=("bottom60_capture_pct", "size"),
        )
        .query("n >= 8")
        .sort_values("median")
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    x = np.arange(len(gini))
    ax1.bar(x, gini["median"], color="#3a7ca5")
    ax1.errorbar(
        x,
        gini["median"],
        yerr=[gini["median"] - gini["p25"], gini["p75"] - gini["median"]],
        fmt="none",
        color="black",
        capsize=4,
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(
        [f"{q}\n(n={n})" for q, n in zip(gini["gini_quartile"], gini["n"])], rotation=12
    )
    ax1.set_ylabel("Median bottom-60 capture (%)")
    ax1.set_title("By initial PIP Gini quartile (bars; IQR whiskers)")
    ax2.barh(
        [f"{idx.strip()} (n={int(r.n)})" for idx, r in region.iterrows()],
        region["median"],
        color="#f2b134",
    )
    ax2.set_xlabel("Median bottom-60 capture (%)")
    ax2.set_title("By region (shown when n ≥ 8 spells)")
    fig.suptitle(
        "Chart 126: National growth incidence varies widely across observed contexts\n"
        "(descriptive groups; main sample requires ≥1% survey-welfare growth and capture between 0–100%)",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "126_growth_incidence_heterogeneity_groups.png")
    plt.close(fig)


def main() -> None:
    pip, wdi, regions = load_inputs()
    dynamic_summary, sensitivity = dynamic_analysis(pip, wdi)
    spells, coefficients, heterogeneity_summary = heterogeneity_analysis(
        pip, wdi, regions
    )

    print("\nDYNAMIC STRATEGY SUMMARY — CENTRAL SCENARIO")
    print(BASELINE_BASIS + "; " + POVERTY_METHOD)
    print("\nBASELINE VINTAGE AND CACHE-ONLY RECONCILIATION")
    print(pd.read_csv(PROC / "dynamic_transfer_baseline_summary.csv").to_string(index=False))
    cols = [
        "strategy",
        "pv_targeted_transfer_trillion_2017ppp",
        "year2050_transfer_billion_2017ppp",
        "year2050_population_below_before_transfer_share",
        "year2050_transfer_pct_observed_tax_revenue",
    ]
    print(
        dynamic_summary[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}")
    )
    print("\nSensitivity PV range by strategy (trillion 2017-PPP $):")
    print(
        sensitivity.groupby("strategy")["pv_targeted_transfer_trillion_2017ppp"]
        .agg(["min", "max"])
        .to_string(float_format=lambda x: f"{x:.3f}")
    )
    print("\nGROWTH-INCIDENCE HETEROGENEITY SAMPLE")
    print(
        heterogeneity_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}")
    )
    print("\nSelected country-clustered associations:")
    print(
        coefficients[
            coefficients["term"].isin(
                [
                    "initial_gini_10point",
                    "initial_tax_10point",
                    "initial_services_10point",
                ]
            )
        ][
            [
                "model",
                "term_label",
                "coefficient_capture_percentage_points",
                "ci_low",
                "ci_high",
                "p_value",
                "n_spells",
                "n_countries",
            ]
        ].to_string(
            index=False, float_format=lambda x: f"{x:.3f}"
        )
    )
    print(
        "\nCAVEATS: strategy paths are transparent scenarios, not forecasts or causal estimates. "
        "2025 is a scenario origin, not an observed common-year baseline. Surveys, GDP and tax rates "
        "are mixed-vintage; gaps/headcounts and post-transfer closure are decile-mean approximations. "
        "Growth-enabling investment costs are unobserved and not monetized. Domestic tax ratios "
        "measure accounting capacity only. Behavioral and local-price terms are sensitivities. "
        "Regressions are observational with country-clustered uncertainty; near-zero-growth ratio "
        "instability motivates the main-sample rule and robustness check. Commodity dependence, "
        "labor transformation, and institutional quality are not estimated because verified pooled "
        "variables are absent."
    )
    print("Refreshed eleven processed CSVs and Charts 123–126 from local caches only.")


if __name__ == "__main__":
    main()
