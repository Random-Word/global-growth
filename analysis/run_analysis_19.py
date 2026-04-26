#!/usr/bin/env python3
"""Analysis 19: Good-Life Threshold v2.

The threshold is estimated as an outcome-reliability band across health,
nutrition, basic services, education, safety, and environmental indicators.
Resource variables are treated as predictors or correlates, not definitions of
the good life itself.

Outputs:
- charts/97_good_life_v2_reliability_curves.png
- charts/98_good_life_v2_outcome_ladder.png
- charts/99_good_life_v2_world_status_over_time.png
- charts/100_good_life_v2_pip_headcount_ladder.png
- charts/101_good_life_v2_median_vs_gdp.png
- data/processed/good_life_v2_*.csv
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class Criterion:
    name: str
    label: str
    column: str
    threshold: float
    direction: str
    domain: str


@dataclass(frozen=True)
class ResourceMeasure:
    column: str
    label: str
    thresholds: tuple[float, ...]
    display_divisor: float
    axis_label: str


CRITERIA = [
    Criterion("life70", "Life expectancy >=70", "life_expectancy", 70, ">=", "Health"),
    Criterion(
        "under5_25", "Under-5 mortality <=25", "under5_mortality", 25, "<=", "Health"
    ),
    Criterion(
        "neonatal_12",
        "Neonatal mortality <=12",
        "neonatal_mortality_per_1000",
        12,
        "<=",
        "Health",
    ),
    Criterion(
        "maternal_70",
        "Maternal mortality <=70",
        "maternal_mortality_per_100k",
        70,
        "<=",
        "Health",
    ),
    Criterion(
        "skilled_birth_90",
        "Skilled birth attendance >=90%",
        "skilled_birth_attendance_pct",
        90,
        ">=",
        "Health",
    ),
    Criterion(
        "dpt_90", "DPT immunization >=90%", "dpt_immunization_pct", 90, ">=", "Health"
    ),
    Criterion(
        "measles_90",
        "Measles immunization >=90%",
        "measles_immunization_pct",
        90,
        ">=",
        "Health",
    ),
    Criterion(
        "water_90",
        "Basic water >=90%",
        "basic_water_access_pct",
        90,
        ">=",
        "Basic services",
    ),
    Criterion(
        "sanitation_90",
        "Basic sanitation >=90%",
        "basic_sanitation_pct",
        90,
        ">=",
        "Basic services",
    ),
    Criterion(
        "electricity_90",
        "Electricity >=90%",
        "electricity_access_pct",
        90,
        ">=",
        "Basic services",
    ),
    Criterion(
        "clean_cooking_80",
        "Clean cooking >=80%",
        "clean_cooking_access_pct",
        80,
        ">=",
        "Basic services",
    ),
    Criterion(
        "primary_90",
        "Primary completion >=90%",
        "primary_completion_pct",
        90,
        ">=",
        "Education",
    ),
    Criterion(
        "secondary_75",
        "Secondary enrollment >=75%",
        "secondary_enrollment_pct",
        75,
        ">=",
        "Education",
    ),
    Criterion(
        "literacy_90",
        "Adult literacy >=90%",
        "adult_literacy_pct",
        90,
        ">=",
        "Education",
    ),
    Criterion(
        "undernourishment_5",
        "Undernourishment <=5%",
        "undernourishment_pct",
        5,
        "<=",
        "Nutrition",
    ),
    Criterion(
        "stunting_15",
        "Child stunting <=15%",
        "child_stunting_pct",
        15,
        "<=",
        "Nutrition",
    ),
    Criterion(
        "wasting_5", "Child wasting <=5%", "child_wasting_pct", 5, "<=", "Nutrition"
    ),
    Criterion(
        "pm25_15",
        "PM2.5 <=15 ug/m3",
        "pm25_exposure_ugm3",
        15,
        "<=",
        "Safety/environment",
    ),
    Criterion(
        "homicide_10",
        "Homicide <=10/100k",
        "homicide_per_100k",
        10,
        "<=",
        "Safety/environment",
    ),
]

RESOURCE_MEASURES = [
    ResourceMeasure(
        "gdppc_ppp_current",
        "GDP/capita, current PPP",
        (3000, 5000, 7500, 10000, 12500, 15000, 17500, 20000, 25000, 30000, 40000),
        1000,
        "GDP/capita threshold (current PPP, $k)",
    ),
    ResourceMeasure(
        "household_consumption_ppp_pc_current",
        "Household consumption/capita, PPP",
        (2500, 5000, 7500, 10000, 12500, 15000, 17500, 20000, 25000, 30000),
        1000,
        "Household consumption/cap threshold (PPP, $k)",
    ),
    ResourceMeasure(
        "pip_median_daily",
        "PIP median welfare/day",
        (3.65, 5, 6.85, 10, 12.5, 15, 17.5, 20, 25, 30),
        1,
        "PIP median welfare threshold ($/day, 2017 PPP)",
    ),
]


def save_table(dataframe: pd.DataFrame, filename: str) -> Path:
    path = PROC / filename
    dataframe.to_csv(path, index=False)
    print(f"  saved {path.relative_to(BASE)} ({len(dataframe):,} rows)")
    return path


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return np.nan
    return float(np.average(values[valid], weights=weights[valid]))


def weighted_share(mask: pd.Series, weights: pd.Series) -> float:
    valid = mask.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return np.nan
    return float(np.average(mask[valid].astype(float), weights=weights[valid]))


def latest_per_country(dataframe: pd.DataFrame, min_year: int = 2018) -> pd.DataFrame:
    return (
        dataframe[dataframe["year"] >= min_year]
        .sort_values("year")
        .drop_duplicates("country_code", keep="last")
    )


def latest_covered_per_country(
    dataframe: pd.DataFrame, min_year: int = 2018, min_indicators: int = 8
) -> pd.DataFrame:
    covered = dataframe[
        (dataframe["year"] >= min_year)
        & (dataframe["good_life_indicators_available"] >= min_indicators)
        & dataframe["good_life_score"].notna()
    ].copy()
    return covered.sort_values("year").drop_duplicates("country_code", keep="last")


def read_pip_country(poverty_line: float) -> pd.DataFrame | None:
    path = RAW / f"pip_country_{poverty_line}.csv"
    if not path.exists():
        return None
    pip = pd.read_csv(path)
    pip = pip[pip["country_code"].notna()].copy()
    pip = pip[pip["reporting_level"].eq("national") | pip["reporting_level"].isna()]
    pip = pip.sort_values(["country_code", "reporting_year"])
    pip = pip.drop_duplicates(["country_code", "reporting_year"], keep="last")
    return pip


def load_panel() -> tuple[pd.DataFrame, list[float]]:
    wdi = pd.read_csv(PROC / "wdi_combined.csv")
    extended_path = PROC / "good_life_wdi_extended.csv"
    if extended_path.exists():
        extended = pd.read_csv(extended_path)
        wdi = wdi.merge(
            extended.drop(columns=["country"], errors="ignore"),
            on=["country_code", "year"],
            how="left",
        )
    else:
        print(
            "  WARNING: good_life_wdi_extended.csv not found; run download_good_life_data.py first"
        )

    pip10 = read_pip_country(10.0)
    if pip10 is None:
        raise FileNotFoundError("data/raw/pip_country_10.0.csv is required")

    country_codes = set(pip10["country_code"].dropna().unique())
    wdi = wdi[wdi["country_code"].isin(country_codes)].copy()

    pip_base = pip10[
        [
            "country_code",
            "reporting_year",
            "mean",
            "median",
            "gini",
            "decile1",
            "decile2",
            "decile3",
            "decile4",
            "reporting_pop",
            "welfare_type",
        ]
    ].copy()
    pip_base = pip_base.rename(
        columns={
            "reporting_year": "year",
            "mean": "pip_mean_daily",
            "median": "pip_median_daily",
            "gini": "pip_gini",
            "reporting_pop": "pip_reporting_pop",
        }
    )
    pip_base["pip_mean_annual"] = pip_base["pip_mean_daily"] * 365
    pip_base["pip_median_annual"] = pip_base["pip_median_daily"] * 365

    panel = wdi.merge(pip_base, on=["country_code", "year"], how="left")
    available_lines: list[float] = []
    for poverty_line in [2.15, 3.65, 6.85, 10.0, 15.0, 20.0, 25.0]:
        pip_line = read_pip_country(poverty_line)
        if pip_line is None:
            continue
        available_lines.append(poverty_line)
        keep = pip_line[
            ["country_code", "reporting_year", "headcount", "poverty_gap"]
        ].copy()
        keep = keep.rename(
            columns={
                "reporting_year": "year",
                "headcount": f"pip_headcount_{poverty_line:g}",
                "poverty_gap": f"pip_gap_{poverty_line:g}",
            }
        )
        panel = panel.merge(keep, on=["country_code", "year"], how="left")

    if "household_consumption_ppp_current" in panel.columns:
        panel["household_consumption_ppp_pc_current"] = (
            panel["household_consumption_ppp_current"] / panel["population"]
        )
    else:
        panel["household_consumption_ppp_pc_current"] = np.nan

    if "population" in panel.columns:
        panel["analysis_population"] = panel["population"]
    else:
        panel["analysis_population"] = panel["pip_reporting_pop"]
    panel["analysis_population"] = panel["analysis_population"].fillna(
        panel.get("pip_reporting_pop")
    )
    return panel, available_lines


def add_outcome_scores(panel: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    score_columns: list[str] = []
    for criterion in CRITERIA:
        if criterion.column not in panel.columns:
            continue
        values = panel[criterion.column]
        if criterion.direction == ">=":
            met = values >= criterion.threshold
        else:
            met = values <= criterion.threshold
        column = f"met_{criterion.name}"
        panel[column] = np.where(values.notna(), met.astype(float), np.nan)
        score_columns.append(column)

    panel["good_life_indicators_available"] = panel[score_columns].notna().sum(axis=1)
    panel["good_life_indicators_met"] = panel[score_columns].sum(axis=1, skipna=True)
    panel["good_life_score"] = panel[score_columns].mean(axis=1, skipna=True)

    for domain in sorted({criterion.domain for criterion in CRITERIA}):
        domain_columns = [
            f"met_{criterion.name}"
            for criterion in CRITERIA
            if criterion.domain == domain and f"met_{criterion.name}" in panel.columns
        ]
        if domain_columns:
            safe_name = domain.lower().replace("/", "_").replace(" ", "_")
            panel[f"domain_{safe_name}_score"] = panel[domain_columns].mean(
                axis=1, skipna=True
            )
    return panel, score_columns


def build_reliability_tables(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    recent = panel[
        (panel["year"] >= 2010) & (panel["good_life_indicators_available"] >= 8)
    ].copy()
    for measure in RESOURCE_MEASURES:
        if measure.column not in recent.columns:
            continue
        usable = recent[
            recent[measure.column].notna() & recent["good_life_score"].notna()
        ].copy()
        for threshold in measure.thresholds:
            above = usable[usable[measure.column] >= threshold]
            row: dict[str, object] = {
                "resource_measure": measure.column,
                "resource_label": measure.label,
                "threshold": threshold,
                "threshold_display": threshold / measure.display_divisor,
                "axis_label": measure.axis_label,
                "country_years": int(len(above)),
                "countries": int(above["country_code"].nunique()),
                "median_outcome_score": (
                    float(above["good_life_score"].median()) if len(above) else np.nan
                ),
                "mean_indicators_available": (
                    float(above["good_life_indicators_available"].mean())
                    if len(above)
                    else np.nan
                ),
            }
            for target_score in [0.80, 0.85, 0.90]:
                meets = above["good_life_score"] >= target_score
                row[f"share_score_{int(target_score * 100)}"] = (
                    float(meets.mean()) if len(above) else np.nan
                )
                row[f"pop_share_score_{int(target_score * 100)}"] = weighted_share(
                    meets, above["analysis_population"]
                )
            rows.append(row)

    reliability = pd.DataFrame(rows)
    summary_rows: list[dict[str, object]] = []
    for measure in RESOURCE_MEASURES:
        measure_rows = reliability[
            (reliability["resource_measure"] == measure.column)
            & (reliability["country_years"] >= 30)
        ].sort_values("threshold")
        for target_score in [80, 85, 90]:
            for target_reliability in [80, 90, 95]:
                column = f"share_score_{target_score}"
                pop_column = f"pop_share_score_{target_score}"
                match = measure_rows[measure_rows[column] >= target_reliability / 100]
                pop_match = measure_rows[
                    measure_rows[pop_column] >= target_reliability / 100
                ]
                summary_rows.append(
                    {
                        "resource_measure": measure.column,
                        "resource_label": measure.label,
                        "target_outcome_score_pct": target_score,
                        "target_reliability_pct": target_reliability,
                        "threshold_unweighted": (
                            float(match.iloc[0]["threshold"]) if len(match) else np.nan
                        ),
                        "threshold_unweighted_display": (
                            float(match.iloc[0]["threshold_display"])
                            if len(match)
                            else np.nan
                        ),
                        "threshold_population_weighted": (
                            float(pop_match.iloc[0]["threshold"])
                            if len(pop_match)
                            else np.nan
                        ),
                        "threshold_population_weighted_display": (
                            float(pop_match.iloc[0]["threshold_display"])
                            if len(pop_match)
                            else np.nan
                        ),
                        "axis_label": measure.axis_label,
                    }
                )
    summary = pd.DataFrame(summary_rows)
    save_table(reliability, "good_life_v2_threshold_reliability.csv")
    save_table(summary, "good_life_v2_threshold_summary.csv")
    return reliability, summary


def build_outcome_ladder(panel: pd.DataFrame) -> pd.DataFrame:
    latest = latest_covered_per_country(panel, min_year=2018, min_indicators=8)
    latest = latest[
        latest["gdppc_ppp_current"].notna() & latest["analysis_population"].notna()
    ].copy()
    bins = [0, 5000, 10000, 15000, 20000, 30000, np.inf]
    labels = ["<$5k", "$5-10k", "$10-15k", "$15-20k", "$20-30k", "$30k+"]
    latest["income_bin"] = pd.cut(
        latest["gdppc_ppp_current"], bins=bins, labels=labels, right=False
    )

    rows: list[dict[str, object]] = []
    domain_columns = [
        column for column in latest.columns if column.startswith("domain_")
    ]
    for income_bin in labels:
        group = latest[latest["income_bin"].astype(str).eq(income_bin)]
        if group.empty:
            continue
        rows.append(
            {
                "income_bin": income_bin,
                "countries": int(group["country_code"].nunique()),
                "population": float(group["analysis_population"].sum()),
                "good_life_score": weighted_mean(
                    group["good_life_score"], group["analysis_population"]
                ),
                **{
                    column: weighted_mean(group[column], group["analysis_population"])
                    for column in domain_columns
                },
            }
        )
    ladder = pd.DataFrame(rows)
    save_table(ladder, "good_life_v2_outcome_ladder.csv")
    return ladder


def build_historical_status(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    annual = panel[
        (panel["year"] >= 1981)
        & (panel["analysis_population"].notna())
        & (panel["analysis_population"] > 0)
    ].copy()
    annual["year"] = annual["year"].astype(int)
    for year, group in annual.groupby("year"):
        reporting_year = int(np.asarray(year).item())
        covered = group[group["good_life_indicators_available"] >= 6].copy()
        row: dict[str, object] = {
            "year": reporting_year,
            "countries": int(group["country_code"].nunique()),
            "population": float(group["analysis_population"].sum()),
            "covered_population": float(covered["analysis_population"].sum()),
            "covered_population_share": (
                float(
                    covered["analysis_population"].sum()
                    / group["analysis_population"].sum()
                )
                if group["analysis_population"].sum()
                else np.nan
            ),
            "population_weighted_score": weighted_mean(
                covered["good_life_score"], covered["analysis_population"]
            ),
        }
        for target_score in [0.80, 0.85, 0.90]:
            row[f"pop_share_score_{int(target_score * 100)}"] = weighted_share(
                covered["good_life_score"] >= target_score,
                covered["analysis_population"],
            )
        rows.append(row)
    historical = pd.DataFrame(rows).sort_values("year")
    save_table(historical, "good_life_v2_world_status_over_time.csv")
    return historical


def build_current_status(
    panel: pd.DataFrame, available_lines: list[float]
) -> pd.DataFrame:
    covered = latest_covered_per_country(panel, min_year=2018, min_indicators=8)
    latest = latest_per_country(panel, min_year=2018)
    rows: list[dict[str, object]] = [
        {
            "metric": "population_weighted_good_life_score",
            "value": weighted_mean(
                covered["good_life_score"], covered["analysis_population"]
            ),
            "unit": "0-1 score",
        },
        {
            "metric": "population_share_score_80",
            "value": weighted_share(
                covered["good_life_score"] >= 0.80, covered["analysis_population"]
            ),
            "unit": "share of covered population",
        },
        {
            "metric": "population_share_score_85",
            "value": weighted_share(
                covered["good_life_score"] >= 0.85, covered["analysis_population"]
            ),
            "unit": "share of covered population",
        },
        {
            "metric": "population_share_score_90",
            "value": weighted_share(
                covered["good_life_score"] >= 0.90, covered["analysis_population"]
            ),
            "unit": "share of covered population",
        },
        {
            "metric": "covered_population",
            "value": float(covered["analysis_population"].sum()),
            "unit": "people",
        },
    ]
    for poverty_line in available_lines:
        column = f"pip_headcount_{poverty_line:g}"
        if column not in latest.columns:
            continue
        pip_latest = latest[
            latest[column].notna() & latest["pip_reporting_pop"].notna()
        ].copy()
        rows.append(
            {
                "metric": f"people_below_pip_{poverty_line:g}_per_day",
                "value": float(
                    (pip_latest[column] * pip_latest["pip_reporting_pop"]).sum()
                ),
                "unit": "people, country PIP sum",
            }
        )
    status = pd.DataFrame(rows)
    save_table(status, "good_life_v2_current_status.csv")
    return status


def build_pip_world_ladder(available_lines: list[float]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for poverty_line in available_lines:
        path = RAW / f"pip_regional_{poverty_line}.csv"
        if not path.exists():
            continue
        regional = pd.read_csv(path)
        world = regional[regional["region_code"].eq("WLD")].copy()
        if world.empty:
            continue
        world["poverty_line"] = poverty_line
        rows.append(
            world[
                [
                    "reporting_year",
                    "poverty_line",
                    "headcount",
                    "poverty_gap",
                    "reporting_pop",
                ]
            ]
        )
    if not rows:
        return pd.DataFrame()
    ladder = pd.concat(rows, ignore_index=True).rename(
        columns={"reporting_year": "year"}
    )
    ladder["people_below_line"] = ladder["headcount"] * ladder["reporting_pop"]
    save_table(ladder, "good_life_v2_pip_world_ladder.csv")
    return ladder


def plot_reliability_curves(reliability: pd.DataFrame) -> None:
    plot_measures = [
        "gdppc_ppp_current",
        "household_consumption_ppp_pc_current",
        "pip_median_daily",
    ]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), sharey=True)
    for axis, measure_name in zip(axes, plot_measures):
        measure_data = reliability[
            reliability["resource_measure"].eq(measure_name)
        ].copy()
        if measure_data.empty:
            axis.set_visible(False)
            continue
        for target, label in [
            (80, "Score >=80%"),
            (85, "Score >=85%"),
            (90, "Score >=90%"),
        ]:
            axis.plot(
                measure_data["threshold_display"],
                measure_data[f"share_score_{target}"] * 100,
                marker="o",
                linewidth=2,
                label=label,
            )
        axis.axhline(90, color="gray", linestyle="--", linewidth=1)
        axis.set_title(str(measure_data["resource_label"].iloc[0]))
        axis.set_xlabel(str(measure_data["axis_label"].iloc[0]))
        axis.set_ylim(0, 105)
        axis.grid(True, alpha=0.3)
    axes[0].set_ylabel("Share of country-years above resource threshold (%)")
    axes[0].legend(loc="lower right", fontsize=9)
    plt.suptitle(
        "Chart 97: Good-life reliability rises as resources increase, but not identically across measures",
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(CHARTS / "97_good_life_v2_reliability_curves.png")
    plt.close()


def plot_outcome_ladder(ladder: pd.DataFrame) -> None:
    domain_columns = [
        column for column in ladder.columns if column.startswith("domain_")
    ]
    display_names = {
        "domain_basic_services_score": "Basic services",
        "domain_education_score": "Education",
        "domain_health_score": "Health",
        "domain_nutrition_score": "Nutrition",
        "domain_safety_environment_score": "Safety/environment",
    }
    plot_data = ladder.melt(
        id_vars="income_bin",
        value_vars=domain_columns,
        var_name="domain",
        value_name="score",
    )
    plot_data["domain"] = (
        plot_data["domain"].map(display_names).fillna(plot_data["domain"])
    )
    plt.figure(figsize=(12, 7))
    sns.lineplot(
        data=plot_data,
        x="income_bin",
        y="score",
        hue="domain",
        marker="o",
        linewidth=2.5,
    )
    plt.ylim(0, 1.02)
    plt.ylabel("Population-weighted domain score")
    plt.xlabel("Latest GDP/capita bin (current PPP)")
    plt.title(
        "Chart 98: A good life is a bundle; domains saturate at different income levels",
        fontweight="bold",
    )
    plt.legend(title="")
    plt.tight_layout()
    plt.savefig(CHARTS / "98_good_life_v2_outcome_ladder.png")
    plt.close()


def plot_historical_status(historical: pd.DataFrame) -> None:
    fig, axis = plt.subplots(figsize=(12, 7))
    historical = historical[historical["covered_population_share"] >= 0.5].copy()
    axis.plot(
        historical["year"],
        historical["population_weighted_score"],
        linewidth=3,
        label="Average outcome score",
    )
    axis.plot(
        historical["year"],
        historical["pop_share_score_80"],
        linewidth=2,
        label="Population with score >=80%",
    )
    axis.plot(
        historical["year"],
        historical["pop_share_score_85"],
        linewidth=2,
        label="Population with score >=85%",
    )
    axis.plot(
        historical["year"],
        historical["covered_population_share"],
        color="gray",
        linestyle="--",
        linewidth=1.5,
        label="Population with enough indicators",
    )
    axis.set_ylim(0, 1.02)
    axis.set_ylabel("Share / score")
    axis.set_xlabel("Year")
    axis.set_title(
        "Chart 99: The world has moved toward the good-life bundle, but coverage and ambition matter",
        fontweight="bold",
    )
    axis.legend(loc="lower right")
    axis.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(CHARTS / "99_good_life_v2_world_status_over_time.png")
    plt.close()


def plot_pip_ladder(pip_world: pd.DataFrame) -> None:
    if pip_world.empty:
        return
    selected = pip_world[
        pip_world["poverty_line"].isin([2.15, 6.85, 10.0, 15.0, 20.0, 25.0])
    ].copy()
    selected = selected[selected["year"] >= 1981]
    plt.figure(figsize=(12, 7))
    for poverty_line, group in selected.groupby("poverty_line"):
        plt.plot(
            group["year"],
            group["headcount"] * 100,
            linewidth=2,
            label=f"${poverty_line:g}/day",
        )
    plt.ylabel("World population below line (%)")
    plt.xlabel("Year")
    plt.title(
        "Chart 100: Higher welfare lines make clear how far the world remains from a good-life floor",
        fontweight="bold",
    )
    plt.legend(title="PIP line")
    plt.ylim(0, 100)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(CHARTS / "100_good_life_v2_pip_headcount_ladder.png")
    plt.close()


def plot_median_vs_gdp(panel: pd.DataFrame) -> None:
    latest = latest_covered_per_country(panel, min_year=2018, min_indicators=8)
    plot_data = latest[
        latest["gdppc_ppp_current"].notna()
        & latest["pip_median_daily"].notna()
        & latest["good_life_score"].notna()
        & (latest["good_life_indicators_available"] >= 8)
    ].copy()
    if plot_data.empty:
        return
    plot_data["population_millions"] = plot_data["analysis_population"] / 1e6
    plt.figure(figsize=(12, 7))
    scatter = plt.scatter(
        plot_data["gdppc_ppp_current"],
        plot_data["pip_median_daily"],
        s=np.clip(plot_data["population_millions"], 5, 300),
        c=plot_data["good_life_score"],
        cmap="viridis",
        alpha=0.75,
        edgecolors="white",
        linewidth=0.4,
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.axvline(15000, color="red", linestyle=":", linewidth=1, label="$15k GDP/cap")
    plt.axhline(
        15, color="purple", linestyle=":", linewidth=1, label="$15/day median welfare"
    )
    plt.xlabel("GDP/capita (current PPP, log scale)")
    plt.ylabel("PIP median welfare ($/day, 2017 PPP, log scale)")
    plt.title(
        "Chart 101: GDP and median welfare diverge enough to measure both",
        fontweight="bold",
    )
    plt.colorbar(scatter, label="Good-life outcome score")
    plt.legend(loc="lower right")
    plt.grid(True, which="both", alpha=0.25)
    plt.tight_layout()
    plt.savefig(CHARTS / "101_good_life_v2_median_vs_gdp.png")
    plt.close()


def main() -> None:
    print("=" * 80)
    print("ANALYSIS 19: GOOD-LIFE THRESHOLD V2")
    print("=" * 80)

    panel, available_lines = load_panel()
    panel, score_columns = add_outcome_scores(panel)
    print(f"  outcome criteria available in panel: {len(score_columns)}")
    save_table(panel, "good_life_v2_country_year_panel.csv")

    reliability, summary = build_reliability_tables(panel)
    ladder = build_outcome_ladder(panel)
    historical = build_historical_status(panel)
    build_current_status(panel, available_lines)
    pip_world = build_pip_world_ladder(available_lines)

    plot_reliability_curves(reliability)
    plot_outcome_ladder(ladder)
    plot_historical_status(historical)
    plot_pip_ladder(pip_world)
    plot_median_vs_gdp(panel)

    key = summary[
        (summary["target_outcome_score_pct"].eq(85))
        & (summary["target_reliability_pct"].eq(90))
    ][
        [
            "resource_label",
            "threshold_unweighted_display",
            "threshold_population_weighted_display",
            "axis_label",
        ]
    ]
    print("\n90% reliability threshold for outcome score >=85%:")
    print(key.to_string(index=False))
    print("\nDone.")


if __name__ == "__main__":
    main()
