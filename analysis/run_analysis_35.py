#!/usr/bin/env python3
"""External welfare validation with cached three-year Cantril averages.

Offline, descriptive analysis. No annual happiness observations are inferred.
Run after analysis19; outputs include a generated report and three figures.
"""

from pathlib import Path
import hashlib
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data/processed"
RAW = BASE / "data/raw"
CHARTS = BASE / "charts"
# Fixed nine-indicator core: a coverage sensitivity, NOT the full welfare bundle.
# Thresholds are inherited unchanged from Analysis 19. All nine are required.
DOMAINS = {
    "health": ["met_life70", "met_under5_25"],
    "services": [
        "met_water_90",
        "met_sanitation_90",
        "met_electricity_90",
        "met_clean_cooking_80",
    ],
    "education": ["met_secondary_75"],
    "nutrition": ["met_undernourishment_5"],
    "environment": ["met_pm25_15"],
}
CORE = [item for items in DOMAINS.values() for item in items]
RESOURCES = [
    "gdppc_ppp_current",
    "household_consumption_ppp_pc_current",
    "pip_median_daily",
]
LABELS = [
    "GDP/capita (current PPP)",
    "Household consumption/capita (current PPP)",
    "PIP median/day (2017 PPP)",
]


def fixed_core(frame: pd.DataFrame) -> pd.Series:
    """Equal domain weights; missing any core item makes the score unavailable."""
    domains = pd.DataFrame(
        {key: frame[items].mean(axis=1) for key, items in DOMAINS.items()}
    )
    return domains.mean(axis=1).where(frame[CORE].notna().all(axis=1))


def window_means(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Exact t-2:t means only, with three nonmissing annual values per variable."""
    if frame.duplicated(["country_code", "year"]).any():
        raise ValueError("Duplicate country-years")
    outputs = []
    for code, group in frame.groupby("country_code"):
        annual = group.set_index("year")[columns].sort_index()
        annual = annual.reindex(
            range(int(annual.index.min()), int(annual.index.max()) + 1)
        )
        rolled = annual.rolling(3, min_periods=3).mean().reset_index()
        rolled["country_code"] = code
        outputs.append(rolled)
    return pd.concat(outputs, ignore_index=True)


def leave_one_out_rmse(x: np.ndarray, y: np.ndarray, quadratic: bool = False) -> float:
    """Each snapshot row is a country; no other row from that country is trained on."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    design = np.column_stack(
        [np.ones(len(x)), x, x * x] if quadratic else [np.ones(len(x)), x]
    )
    errors = []
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        coef = np.linalg.lstsq(design[keep], y[keep], rcond=None)[0]
        errors.append(float(y[i] - design[i] @ coef))
    return float(np.sqrt(np.mean(np.square(errors))))


def pareto_mask(frame: pd.DataFrame) -> np.ndarray:
    """Maximize life evaluation and core score, minimize consumption CO2."""
    values = (
        frame[["life_satisfaction", "fixed_core_score", "consumption_co2_per_capita"]]
        .to_numpy()
        .copy()
    )
    if not np.isfinite(values).all():
        raise ValueError("Frontier requires complete finite observations")
    values[:, 2] *= -1
    return np.array(
        [
            not np.any(np.all(values >= row, axis=1) & np.any(values > row, axis=1))
            for row in values
        ]
    )


def build_panel() -> pd.DataFrame:
    countries = pd.read_csv(RAW / "wb_country_regions.csv")
    valid = set(
        countries.loc[
            countries.region.notna() & countries.region.ne("Aggregates"), "country_code"
        ]
    )
    welfare = pd.read_csv(PROC / "good_life_v2_country_year_panel.csv")
    welfare = welfare[welfare.country_code.isin(valid)].copy()
    # Older Analysis19 outputs had duplicate country-name alias rows. Require
    # the corrected producer rather than selecting a favorable score here.
    duplicate_rows = welfare[welfare.duplicated(["country_code", "year"], keep=False)]
    duplicate_rows.to_csv(
        PROC / "wellbeing_validation_duplicate_audit.csv", index=False
    )
    if not duplicate_rows.empty:
        raise ValueError(
            "Duplicate welfare keys: rerun corrected Analysis19 before wellbeing validation"
        )
    welfare["fixed_core_score"] = fixed_core(welfare)
    welfare["available_score"] = welfare.good_life_score.where(
        welfare.good_life_indicators_available >= 8
    )
    domain_cols = [
        column
        for column in welfare
        if isinstance(column, str)
        and column.startswith("domain_")
        and column.endswith("_score")
    ]
    welfare["available_domain_score"] = (
        welfare[domain_cols]
        .mean(axis=1)
        .where(welfare[domain_cols].notna().all(axis=1))
    )
    cols = RESOURCES + [
        "gdppc_constant_2015usd",
        "population",
        "fixed_core_score",
        "available_score",
        "available_domain_score",
    ]
    means = window_means(welfare, cols)
    # Do not average income and consumption concepts across a PIP window.
    types = welfare[["country_code", "year", "welfare_type"]]
    for index, row in means[means.pip_median_daily.notna()].iterrows():
        observed = types[
            (types.country_code == row.country_code)
            & types.year.between(row.year - 2, row.year)
        ].welfare_type
        if len(observed) != 3 or observed.isna().any() or observed.nunique() != 1:
            means.loc[index, "pip_median_daily"] = np.nan
    co2 = pd.read_csv(RAW / "owid_co2.csv").rename(columns={"iso_code": "country_code"})
    co2 = co2[co2.country_code.isin(valid)]
    means = means.merge(
        window_means(co2, ["consumption_co2_per_capita"]),
        on=["country_code", "year"],
        how="left",
        validate="one_to_one",
    )
    happiness = pd.read_csv(RAW / "good_life_owid_cantril_ladder.csv").rename(
        columns={
            "Entity": "country",
            "Code": "country_code",
            "Year": "year",
            "Self-reported life satisfaction": "life_satisfaction",
        }
    )
    happiness = happiness[happiness.country_code.isin(valid)]
    assert happiness.life_satisfaction.between(0, 10).all()
    panel = happiness.merge(
        means, on=["country_code", "year"], how="left", validate="one_to_one"
    )
    panel["window_start"] = panel.year - 2
    panel["nonoverlapping_panel"] = panel.year.isin([2013, 2016, 2019, 2022, 2025])
    return panel


def main() -> None:
    panel = build_panel()
    panel.to_csv(PROC / "wellbeing_validation_panel.csv", index=False)
    coverage = panel.groupby("year").agg(
        happiness_countries=("country_code", "size"),
        fixed_core_countries=("fixed_core_score", "count"),
        consumption_co2_countries=("consumption_co2_per_capita", "count"),
    )
    coverage.to_csv(PROC / "wellbeing_validation_coverage.csv")
    # Prespecified recency rule: latest window with >=60 complete core countries.
    eligible = coverage[coverage.fixed_core_countries >= 60]
    if eligible.empty:
        raise ValueError(
            "No common window has 60 fixed-core countries; do not relax coverage silently"
        )
    year = int(eligible.index.max())
    snapshot = panel[panel.year.eq(year)].copy()
    core = snapshot.dropna(
        subset=[
            "fixed_core_score",
            "available_score",
            "available_domain_score",
            "population",
        ]
    )
    results = []
    for sample, data in [
        ("all", core),
        ("exclude_CHN_IND", core[~core.country_code.isin(["CHN", "IND"])]),
    ]:
        for score in ["available_score", "available_domain_score", "fixed_core_score"]:
            x, y = data[score].to_numpy(), data.life_satisfaction.to_numpy()
            results.append(
                {
                    "sample": sample,
                    "predictor": score,
                    "countries": len(data),
                    "pearson_r": np.corrcoef(x, y)[0, 1],
                    "loco_rmse": leave_one_out_rmse(x, y),
                }
            )
    associations = pd.DataFrame(results)
    associations.to_csv(
        PROC / "wellbeing_validation_score_sensitivity.csv", index=False
    )
    # Compare resources only on identical countries and one matched time window.
    resources = snapshot.dropna(subset=RESOURCES).copy()
    resources = resources[(resources[RESOURCES] > 0).all(axis=1)]
    models = []
    for predictor in RESOURCES:
        x, y = (
            np.log(resources[predictor].to_numpy()),
            resources.life_satisfaction.to_numpy(),
        )
        for quadratic in [False, True]:
            models.append(
                {
                    "predictor": predictor,
                    "form": "quadratic_log" if quadratic else "log_linear",
                    "countries": len(resources),
                    "pearson_log_r": np.corrcoef(x, y)[0, 1],
                    "loco_rmse": leave_one_out_rmse(x, y, quadratic),
                }
            )
    pd.DataFrame(models).to_csv(
        PROC / "wellbeing_validation_resource_models.csv", index=False
    )
    # Real domestic GDP measure avoids treating current PPP time changes as growth.
    longitudinal = panel[
        panel.nonoverlapping_panel & panel.gdppc_constant_2015usd.gt(0)
    ].copy()
    longitudinal = longitudinal.groupby("country_code").filter(
        lambda group: len(group) >= 3
    )
    longitudinal["log_real_gdp"] = np.log(longitudinal.gdppc_constant_2015usd)
    fit = smf.ols(
        "life_satisfaction ~ log_real_gdp + C(country_code) + C(year)",
        data=longitudinal,
    ).fit(cov_type="cluster", cov_kwds={"groups": longitudinal.country_code})
    interval = fit.conf_int().loc["log_real_gdp"] * np.log(1.1)
    effect = float(fit.params["log_real_gdp"] * np.log(1.1))
    pd.DataFrame(
        [
            {
                "countries": longitudinal.country_code.nunique(),
                "windows": len(longitudinal),
                "association_per_10pct_real_gdp": effect,
                "ci_low": interval.iloc[0],
                "ci_high": interval.iloc[1],
                "causal": False,
            }
        ]
    ).to_csv(PROC / "wellbeing_validation_within_country.csv", index=False)
    frontier = snapshot.dropna(
        subset=["life_satisfaction", "fixed_core_score", "consumption_co2_per_capita"]
    ).copy()
    frontier["sample_pareto_frontier"] = pareto_mask(frontier)
    frontier.to_csv(PROC / "wellbeing_validation_frontier.csv", index=False)

    plt.rcParams.update(
        {"figure.dpi": 140, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(
        core.fixed_core_score, core.life_satisfaction, c="#197b89", alpha=0.7
    )
    axes[0].set(
        xlabel="Fixed nine-indicator, five-domain score",
        ylabel="Cantril life evaluation (0–10)",
        title=f"Matched {year-2}–{year} window; n={len(core)}",
    )
    for code in ["CHN", "IND", "USA", "CRI", "FIN"]:
        for row in core[core.country_code.eq(code)].itertuples():
            axes[0].annotate(
                code,
                (row.fixed_core_score, row.life_satisfaction),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=8,
            )
    coverage[["happiness_countries", "fixed_core_countries"]].plot(
        ax=axes[1], color=["#197b89", "#c46e27"]
    )
    axes[1].set(
        xlabel="Window end year",
        ylabel="Countries",
        title="Coverage loss is reported, not imputed",
    )
    fig.suptitle(
        "Objective outcomes and self-reported lives: descriptive external validation"
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "143_wellbeing_objective_validation.png")
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, column, label in zip(axes, RESOURCES, LABELS):
        ax.scatter(
            resources[column], resources.life_satisfaction, alpha=0.6, color="#197b89"
        )
        ax.set(
            xscale="log",
            xlabel=label,
            ylabel="Cantril life evaluation",
            title=f"Identical sample: n={len(resources)}",
        )
    fig.suptitle(
        f"Resource associations, {year-2}–{year}: no causal threshold inferred"
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "144_wellbeing_resources.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 6))
    points = ax.scatter(
        frontier.consumption_co2_per_capita,
        frontier.life_satisfaction,
        c=frontier.fixed_core_score,
        cmap="viridis",
        vmin=0,
        vmax=1,
        s=45,
    )
    frontier_points = frontier[frontier.sample_pareto_frontier]
    for code, (carbon, satisfaction) in zip(
        frontier_points.country_code,
        frontier_points[["consumption_co2_per_capita", "life_satisfaction"]].to_numpy(
            dtype=float
        ),
    ):
        ax.annotate(
            str(code),
            (carbon, satisfaction),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
        )
    fig.colorbar(points, ax=ax, label="Fixed-core objective score")
    ax.set(
        xlabel="Consumption-based fossil/industrial CO₂ (tonnes/person/year)",
        ylabel="Cantril life evaluation (0–10)",
        title=f"Sample frontier, {year-2}–{year}: carbon only, not ecological sufficiency",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "145_wellbeing_carbon_frontier.png")
    plt.close(fig)
    r = associations.iloc[2].pearson_r
    r_without = associations.iloc[5].pearson_r
    excluded_codes = (
        ", ".join(
            core.loc[
                core.country_code.isin(["CHN", "IND"]), "country_code"
            ].sort_values()
        )
        or "none"
    )
    inputs = [
        RAW / "good_life_owid_cantril_ladder.csv",
        RAW / "owid_co2.csv",
        RAW / "wb_country_regions.csv",
        PROC / "good_life_v2_country_year_panel.csv",
    ]
    manifest = {
        "inputs_sha256": {
            str(path.relative_to(BASE)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
        },
        "happiness_source": "https://ourworldindata.org/grapher/happiness-cantril-ladder",
        "window_definition": "End year t denotes t-2:t survey average; every covariate needs all three annual values",
        "core_domains": DOMAINS,
        "snapshot_rule": "Latest endpoint with at least 60 fixed-core countries",
        "snapshot_end": year,
        "limitations": [
            "No survey microdata or survey SEs in cached CSV",
            "No subgroup wellbeing or causal estimates",
            "Current PPP resource levels only used in a common cross section",
            "No country-level material footprint cache; DMC not substituted",
            "Consumption CO2 excludes land-use change and other greenhouse gases",
            "Core omits several full-bundle indicators and uses normative equal domain weights",
        ],
    }
    (PROC / "wellbeing_validation_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    report = f"""# Wellbeing validation: generated results

Generated by [analysis/run_analysis_35.py](analysis/run_analysis_35.py) from cached inputs; see the [input hashes and method registry](data/processed/wellbeing_validation_manifest.json).

- Selected common window: **{year-2}–{year}** (latest with at least 60 fixed-core countries).
- Paired objective-score sample: **{len(core)} countries**. Fixed-core Pearson correlation with life evaluation: **{r:.2f}**; excluding China and India where present: **{r_without:.2f}** (actually removed: **{excluded_codes}**). These are unweighted country-level associations, not individual effects or population-weighted summaries.
- Resource comparison: **{len(resources)} identical countries**, log-linear and quadratic-log leave-one-country-out prediction errors reported in the [model table](data/processed/wellbeing_validation_resource_models.csv). Lower errors are descriptive predictive performance, not causal superiority.
- Non-overlapping-window country/year fixed-effects model: **{longitudinal.country_code.nunique()} countries**, **{len(longitudinal)} observations**. A 10% increase in three-year-average real GDP/capita is associated with **{effect:.3f}** Cantril points (country-clustered 95% interval **{interval.iloc[0]:.3f} to {interval.iloc[1]:.3f}**). Time-varying confounding, reverse causality, measurement error and selection remain; this is not a policy effect or a resolution of the Easterlin debate.
- Carbon/frontier sample: **{len(frontier)} countries**. Labels mark nondominance in this sample across life evaluation, objective score and consumption CO₂—not sustainability, efficient policies or a ranking robust to measurement uncertainty.

## Interpretation and limits

The fixed core requires all nine indicators in every year of each three-year window, then weights five domains equally. It preserves Analysis 19 thresholds but omits maternal/neonatal outcomes, vaccination, literacy, child nutrition and homicide; it is a coverage/weighting sensitivity, not a replacement full bundle. Score comparisons use identical countries. No missing outcome is filled with success or failure. Duplicate country-years trigger an audit and an error requiring the corrected Analysis 19 producer; conflicting scores are never selected or averaged. PIP windows mixing income and consumption concepts are excluded from resource comparisons.

The Cantril measure evaluates life as a whole; it is not daily positive affect or a clinical mental-health measure. Cultural response styles and adaptation matter. Neither high reported satisfaction nor a high national mean excuses deprivation or rights violations. Population-weighted summaries of national means cannot recover individual wellbeing inequality.

OWID end-year labels represent three-year survey averages. Covariates are matched to exactly those years. The within-country model uses endpoints 2013, 2016, 2019, 2022 and 2025, requiring at least three available windows per country. Survey sampling uncertainty is unavailable in the cached data; the regression intervals do not incorporate it. Richer annual and subgroup Gallup data may need institutional access: [WHR data-sharing terms](https://worldhappiness.report/data-sharing/).

The carbon comparison uses consumption-based fossil/industrial CO₂, not territorial emissions, material footprint, all greenhouse gases or all planetary boundaries. The cached material-footprint file is world-only and cannot support country merges. A complete ecological frontier needs compatible country footprints, land, water and nutrients. No happiness-per-tonne ratio is calculated.

## Figures

![Objective welfare validation](charts/143_wellbeing_objective_validation.png)

![Resource comparison](charts/144_wellbeing_resources.png)

![Carbon frontier](charts/145_wellbeing_carbon_frontier.png)
"""
    (BASE / "WELLBEING_VALIDATION.md").write_text(report)
    print(report.split("## Interpretation")[0])


if __name__ == "__main__":
    main()
