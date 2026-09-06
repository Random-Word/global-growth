#!/usr/bin/env python3
"""Analysis 30: fragile-state regimes and supportable causal-development designs.

This script pools two questions that use the same development panel and face the
same identification problem: adverse state conditions and development policies
are selected, not randomly assigned.

PART A — FRAGILE-STATE REGIMES
--------------------------------
Country-years below 50% of US GDP/capita are assigned to mutually exclusive,
time-varying regimes:

1. conflict affected: the UCDP leg of the World Bank FY20–FY26 medium-conflict
   rule (at least 150 battle deaths and at least 1 per 100,000 in a year);
2. low capacity, non-conflict: World Bank WGI government-effectiveness absolute
   score below 25, after removing conflict years;
3. stable developing: neither condition.

The rule is a reproducible proxy, NOT the official historical FCS list. The
official rule also required ACLED, had additional fragility criteria, and
changed over time. The official FY26 conflict and institutional-fragility lists
are exported only as a current crosswalk and are never backcast. Fixed,
non-overlapping five-year exposure/four-year outcome windows prevent a country
with persistent fragility from contributing many overlapping observations.
Country-cluster bootstraps and regressions respect repeated country spells.

PART B — CAUSAL-DEVELOPMENT EVIDENCE
------------------------------------
The only policy-like discontinuity directly supportable by the pooled annual
panel is onset of a sustained high-investment regime: two consecutive years
above 25% of GDP after two years at or below 20%. It is studied with:

* exact-year nearest-neighbour matching on pre-exposure outcomes and
    covariates (not region), an event study, a joint pre-period balance diagnostic, and a
  country-cluster bootstrap;
* same-region synthetic-control-like donor weighting with complete, clean
    investment windows and explicit pre-fit RMSPE. Case exports are diagnostic-only;
    aggregates (including fit-quality subsets) below the reporting minimum are
    withheld, and Chart 130 becomes an insufficient-support notice.

Neither design is called causal. Investment onset is endogenous, there is no
external assignment variable, and matching cannot remove unobserved reforms or
shocks. The joint Wald test tests zero mean growth gaps at each pre-period,
not parallel trends; neither rejection nor non-rejection identifies causality.
Pre-period imbalance or poor synthetic fit is a substantive finding.
No IV, regression discontinuity, or policy natural experiment is manufactured.

Authoritative inputs downloaded at run time:
* World Bank WGI 2025 revision, government effectiveness and political
  stability, 1996–2024;
* World Bank WDI ``VC.BTL.DETH`` (source: UCDP, CC BY 4.0);
* repository WDI panel and World Bank country/region lookup.

Outputs:
* data/processed/fragile_state_country_year_panel.csv
* data/processed/fragile_state_fixed_window_spells.csv
* data/processed/fragile_state_sample_attrition.csv
* data/processed/fragile_state_group_summary.csv
* data/processed/fragile_state_definition_sensitivity.csv
* data/processed/fragile_state_fy26_crosswalk.csv
* data/processed/causal_development_matched_events.csv
* data/processed/causal_development_event_study.csv
* data/processed/causal_development_synthetic_controls.csv
* data/processed/causal_development_synthetic_fit.csv
* data/processed/causal_development_estimates.csv
* data/processed/causal_development_method_limits.csv
* charts/127_fragile_state_regime_outcomes.png
* charts/128_fragile_state_definition_sensitivity.png
* charts/129_causal_development_matched_event_study.png
* charts/130_causal_development_synthetic_control.png
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
import statsmodels.formula.api as smf
from scipy.optimize import minimize

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

WGI_URL = (
    "https://www.worldbank.org/content/dam/sites/govindicators/doc/"
    "wgidataset_with_sourcedata-2025.xlsx"
)
BATTLE_URL = "https://api.worldbank.org/v2/en/indicator/VC.BTL.DETH?downloadformat=csv"
WGI_CACHE = RAW / "fragile_state_wgi_2025_revision.xlsx"
BATTLE_CACHE = RAW / "fragile_state_wdi_ucdp_battle_deaths.zip"
FCS_FY26_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "aa5bc1b55f2c7d72c157de331ab71f30-0090082026/original/"
    "C2-FCSList-FY06toFY26.pdf"
)

PRIMARY_CAPACITY_CUTOFF = 25.0
PRIMARY_CONFLICT_DEATHS = 150.0
PRIMARY_CONFLICT_RATE = 1.0
SPELL_STARTS = [1996, 2006, 2016]
EXPOSURE_YEARS = 5
OUTCOME_YEARS = 4
BOOTSTRAPS = 1_000
RNG_SEED = 30
MIN_MATCHED_EVENTS = 5
MIN_SYNTHETIC_CASES = 5
MIN_SYNTHETIC_DONORS = 5
MAX_SYNTHETIC_DONORS = 30

# Keep header-only exports readable when no cases survive the clean-window rule.
SYNTHETIC_TRAJECTORY_COLUMNS = [
    "treated_country_code", "onset_year", "event_time", "actual_gdppc_index",
    "synthetic_gdppc_index", "actual_minus_synthetic_pct", "pre_rmspe_pct",
    "effective_donors",
]
SYNTHETIC_FIT_COLUMNS = [
    "treated_country_code", "treated_country", "onset_year", "region",
    "treated_region", "donor_country_codes", "donor_regions", "donor_weights",
    "n_donors", "effective_donors", "pre_rmspe_pct", "post_rmspe_pct",
    "post_pre_rmspe_ratio", "mean_post_gap_pct", "largest_weight",
    "largest_weight_country", "largest_weight_region", "method_note",
]

REGIME_ORDER = [
    "conflict_affected",
    "low_capacity_nonconflict",
    "stable_developing",
]
REGIME_LABELS = {
    "conflict_affected": "Conflict-affected",
    "low_capacity_nonconflict": "Low capacity\n(no conflict)",
    "stable_developing": "Stable developing",
}
REGIME_COLORS = {
    "conflict_affected": "#d1495b",
    "low_capacity_nonconflict": "#f2b134",
    "stable_developing": "#3a7ca5",
}

# Official FY26 lists transcribed from the World Bank archive linked above.
# They are a current crosswalk only; they are not imposed on earlier years.
FY26_CONFLICT = {
    "AFG",
    "BFA",
    "CMR",
    "CAF",
    "COD",
    "ETH",
    "HTI",
    "IRQ",
    "LBN",
    "MLI",
    "MOZ",
    "MMR",
    "NER",
    "NGA",
    "SOM",
    "SSD",
    "SDN",
    "SYR",
    "UKR",
    "PSE",
    "YEM",
}
FY26_INSTITUTIONAL = {
    "BDI",
    "TCD",
    "COM",
    "COG",
    "ERI",
    "GNB",
    "KIR",
    "LBY",
    "MHL",
    "FSM",
    "PNG",
    "STP",
    "SLB",
    "TLS",
    "TUV",
    "VEN",
    "ZWE",
}


def download(url: str, cache_path: Path) -> bytes:
    """Download an authoritative input with retries and a clear failure."""
    if cache_path.exists() and cache_path.stat().st_size > 0:
        print(f"Loading cached authoritative input: {cache_path.relative_to(BASE)}")
        return cache_path.read_bytes()
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            cache_path.write_bytes(response.content)
            return response.content
        except requests.RequestException as exc:
            last_error = exc
            print(f"  download attempt {attempt + 1}/4 failed: {url}")
    raise RuntimeError(f"Could not download {url}: {last_error}")


def load_wgi() -> pd.DataFrame:
    """Load revised WGI absolute scores and estimates for GE and PV."""
    print("Downloading World Bank WGI 2025 revision ...")
    content = BytesIO(download(WGI_URL, WGI_CACHE))
    columns = [
        "Economy (code)",
        "Economy (name)",
        "Year",
        "Governance estimate (approx. -2.5 to +2.5)",
        "Governance score (0-100)",
        "Standard error (gov. score)",
    ]
    frames = []
    for sheet, prefix in [
        ("ge", "government_effectiveness"),
        ("pv", "political_stability"),
    ]:
        content.seek(0)
        d = pd.read_excel(content, sheet_name=sheet, usecols=columns)
        d = d.rename(
            columns={
                "Economy (code)": "country_code",
                "Economy (name)": "wgi_country",
                "Year": "year",
                "Governance estimate (approx. -2.5 to +2.5)": f"{prefix}_estimate",
                "Governance score (0-100)": f"{prefix}_score",
                "Standard error (gov. score)": f"{prefix}_score_se",
            }
        )
        frames.append(d.drop(columns="wgi_country" if sheet == "pv" else []))
    return frames[0].merge(frames[1], on=["country_code", "year"], how="outer")


def load_battle_deaths() -> pd.DataFrame:
    """Load WDI battle deaths (UCDP source) and reshape to country-year."""
    print("Downloading World Bank WDI/UCDP battle-death series ...")
    with ZipFile(BytesIO(download(BATTLE_URL, BATTLE_CACHE))) as archive:
        member = next(
            name
            for name in archive.namelist()
            if name.endswith(".csv") and name.startswith("API_VC.BTL.DETH")
        )
        wide = pd.read_csv(archive.open(member), skiprows=4)
    year_columns = [c for c in wide.columns if str(c).isdigit()]
    long = wide.melt(
        id_vars=["Country Code", "Country Name"],
        value_vars=year_columns,
        var_name="year",
        value_name="battle_deaths",
    ).rename(columns={"Country Code": "country_code", "Country Name": "battle_country"})
    long["year"] = pd.to_numeric(long["year"], errors="coerce").astype("Int64")
    long["battle_deaths"] = pd.to_numeric(long["battle_deaths"], errors="coerce")
    return long.dropna(subset=["year"])


def build_fy26_crosswalk(regions: pd.DataFrame) -> pd.DataFrame:
    """Export the official FY26 categories without using them retrospectively."""
    codes = sorted(FY26_CONFLICT | FY26_INSTITUTIONAL)
    names = (
        pd.read_csv(PROC / "wdi_combined.csv")
        .drop_duplicates("country_code")
        .set_index("country_code")["country"]
        .to_dict()
    )
    region_map = regions.set_index("country_code")["region"].str.strip().to_dict()
    rows = []
    for code in codes:
        rows.append(
            {
                "country_code": code,
                "country": names.get(code, code),
                "region": region_map.get(code, np.nan),
                "official_fy26_category": (
                    "conflict"
                    if code in FY26_CONFLICT
                    else "institutional_and_social_fragility"
                ),
                "effective_fiscal_year": 2026,
                "source_url": FCS_FY26_URL,
                "use_in_analysis": "current crosswalk only; not backcast",
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(PROC / "fragile_state_fy26_crosswalk.csv", index=False)
    return out


def build_country_year_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge WDI, WGI and UCDP using the WB country lookup as the universe."""
    wdi = pd.read_csv(PROC / "wdi_combined.csv")
    regions = pd.read_csv(RAW / "wb_country_regions.csv")
    regions["region"] = regions["region"].str.strip()
    actual_codes = set(regions["country_code"].dropna())
    wdi = wdi[wdi["country_code"].isin(actual_codes)].merge(
        regions[["country_code", "region", "income"]], on="country_code", how="inner"
    )
    wgi = load_wgi()
    battle = load_battle_deaths()
    panel = wdi.merge(wgi, on=["country_code", "year"], how="left").merge(
        battle[["country_code", "year", "battle_deaths"]],
        on=["country_code", "year"],
        how="left",
    )
    panel = panel[panel["year"].between(1996, 2024)].copy()

    # In the WDI/UCDP country series, absent records mean no recorded battle
    # deaths, not a measured positive count. Preserve a flag before replacing.
    panel["battle_deaths_reported"] = panel["battle_deaths"].notna()
    panel["battle_deaths"] = panel["battle_deaths"].fillna(0.0)
    panel["battle_deaths_per_100k"] = np.where(
        panel["population"] > 0,
        100_000 * panel["battle_deaths"] / panel["population"],
        np.nan,
    )
    panel["conflict_primary"] = panel["battle_deaths"].ge(
        PRIMARY_CONFLICT_DEATHS
    ) & panel["battle_deaths_per_100k"].ge(PRIMARY_CONFLICT_RATE)
    panel["conflict_broad"] = panel["battle_deaths"].ge(25)
    panel["conflict_high"] = panel["battle_deaths"].ge(PRIMARY_CONFLICT_DEATHS) & panel[
        "battle_deaths_per_100k"
    ].ge(10)

    us = panel[panel["country_code"].eq("USA")].set_index("year")["gdppc_ppp_current"]
    panel["us_gdppc_ppp_current"] = panel["year"].map(us)
    panel["gdppc_relative_to_us"] = (
        panel["gdppc_ppp_current"] / panel["us_gdppc_ppp_current"]
    )
    panel["developing_below_50pct_us"] = panel["gdppc_relative_to_us"].lt(0.50)
    panel = panel.sort_values(["country_code", "year"])
    lag_gdppc = panel.groupby("country_code")["gdppc_constant_2015usd"].shift(1)
    panel["gdppc_growth_pct"] = 100 * (
        panel["gdppc_constant_2015usd"] / lag_gdppc - 1
    )
    panel["log_gdppc"] = np.log(panel["gdppc_constant_2015usd"].where(lambda x: x > 0))
    panel["primary_regime"] = np.select(
        [
            panel["developing_below_50pct_us"] & panel["conflict_primary"],
            panel["developing_below_50pct_us"]
            & ~panel["conflict_primary"]
            & panel["government_effectiveness_score"].lt(PRIMARY_CAPACITY_CUTOFF),
            panel["developing_below_50pct_us"]
            & ~panel["conflict_primary"]
            & panel["government_effectiveness_score"].ge(PRIMARY_CAPACITY_CUTOFF),
        ],
        REGIME_ORDER,
        default="outside_or_unclassified",
    )
    panel["classification_note"] = (
        "time-varying analytical proxy; not official historical World Bank FCS status"
    )
    panel.to_csv(PROC / "fragile_state_country_year_panel.csv", index=False)
    crosswalk = build_fy26_crosswalk(regions)
    return panel, crosswalk


def value_at(group: pd.DataFrame, year: int, column: str) -> float:
    rows = group.loc[group["year"].eq(year), column].dropna()
    return float(rows.iloc[0]) if len(rows) else np.nan


def classify_window(
    exposure: pd.DataFrame,
    capacity_cutoff: float,
    conflict_column: str,
) -> str | None:
    if exposure[conflict_column].any():
        return "conflict_affected"
    capacity = exposure["government_effectiveness_score"].dropna()
    if len(capacity) < 3:
        return None
    if capacity.mean() < capacity_cutoff:
        return "low_capacity_nonconflict"
    return "stable_developing"


def build_fixed_window_spells(panel: pd.DataFrame) -> pd.DataFrame:
    """Build non-overlapping exposure/outcome windows for developing economies."""
    rows: list[dict] = []
    attrition_rows: list[dict] = []
    for country_code, group in panel.groupby("country_code"):
        group = group.sort_values("year")
        for start in SPELL_STARTS:
            exposure_end = start + EXPOSURE_YEARS - 1
            outcome_end = exposure_end + OUTCOME_YEARS
            exposure = group[group["year"].between(start, exposure_end)]
            if len(exposure) != EXPOSURE_YEARS:
                attrition_rows.append(
                    {
                        "country_code": country_code,
                        "cohort_start": start,
                        "reason": "incomplete_exposure_window",
                    }
                )
                continue
            start_rel = value_at(group, start, "gdppc_relative_to_us")
            if pd.isna(start_rel) or start_rel >= 0.50:
                attrition_rows.append(
                    {
                        "country_code": country_code,
                        "cohort_start": start,
                        "reason": "missing_or_not_developing_at_start",
                    }
                )
                continue
            regime = classify_window(
                exposure, PRIMARY_CAPACITY_CUTOFF, "conflict_primary"
            )
            if regime is None:
                attrition_rows.append(
                    {
                        "country_code": country_code,
                        "cohort_start": start,
                        "reason": "fewer_than_3_wgi_capacity_observations",
                    }
                )
                continue
            gdp0 = value_at(group, exposure_end, "gdppc_constant_2015usd")
            gdp1 = value_at(group, outcome_end, "gdppc_constant_2015usd")
            if pd.isna(gdp0) or pd.isna(gdp1) or gdp0 <= 0 or gdp1 <= 0:
                attrition_rows.append(
                    {
                        "country_code": country_code,
                        "cohort_start": start,
                        "reason": "missing_outcome_gdp",
                    }
                )
                continue
            outcome_growth = 100 * ((gdp1 / gdp0) ** (1 / OUTCOME_YEARS) - 1)
            rows.append(
                {
                    "country_code": country_code,
                    "country": group["country"].iloc[0],
                    "region": group["region"].iloc[0],
                    "cohort_start": start,
                    "exposure_end": exposure_end,
                    "outcome_end": outcome_end,
                    "regime": regime,
                    "start_rel_us": start_rel,
                    "start_gdppc_constant_2015usd": value_at(
                        group, start, "gdppc_constant_2015usd"
                    ),
                    "mean_battle_deaths": exposure["battle_deaths"].mean(),
                    "max_battle_deaths_per_100k": exposure[
                        "battle_deaths_per_100k"
                    ].max(),
                    "conflict_years": int(exposure["conflict_primary"].sum()),
                    "mean_government_effectiveness_score": exposure[
                        "government_effectiveness_score"
                    ].mean(),
                    "mean_political_stability_score": exposure[
                        "political_stability_score"
                    ].mean(),
                    "mean_investment_pct_gdp": exposure[
                        "gross_capital_formation_pct"
                    ].mean(),
                    "mean_trade_pct_gdp": exposure["trade_pct_gdp"].mean(),
                    "mean_fertility_rate": exposure["fertility_rate"].mean(),
                    "outcome_gdppc_growth_pct": outcome_growth,
                    "development_success_ge_3pct": float(outcome_growth >= 3),
                    "window_note": "5y exposure followed by distinct 4y outcome; country windows do not overlap",
                }
            )
    spells = pd.DataFrame(rows)
    attrition = pd.DataFrame(attrition_rows)
    attrition.to_csv(PROC / "fragile_state_sample_attrition.csv", index=False)
    spells.to_csv(PROC / "fragile_state_fixed_window_spells.csv", index=False)
    return spells


def cluster_bootstrap_mean(
    data: pd.DataFrame, value: str, seed: int, draws: int = BOOTSTRAPS
) -> tuple[float, float]:
    """Country-cluster bootstrap interval for a mean."""
    countries = data["country_code"].unique()
    if len(countries) < 2:
        return np.nan, np.nan
    clusters = [
        data.loc[data["country_code"].eq(code), value].dropna().to_numpy()
        for code in countries
    ]
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        selected = rng.integers(0, len(clusters), size=len(clusters))
        sample = np.concatenate([clusters[index] for index in selected])
        values.append(np.mean(sample))
    return tuple(np.quantile(values, [0.025, 0.975]))


def summarize_regimes(spells: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, regime in enumerate(REGIME_ORDER):
        d = spells[spells["regime"].eq(regime)]
        growth_lo, growth_hi = cluster_bootstrap_mean(
            d, "outcome_gdppc_growth_pct", RNG_SEED + i
        )
        success_lo, success_hi = cluster_bootstrap_mean(
            d, "development_success_ge_3pct", RNG_SEED + 10 + i
        )
        rows.append(
            {
                "regime": regime,
                "n_spells": len(d),
                "n_countries": d["country_code"].nunique(),
                "mean_outcome_growth_pct": d["outcome_gdppc_growth_pct"].mean(),
                "median_outcome_growth_pct": d["outcome_gdppc_growth_pct"].median(),
                "growth_cluster_ci_low": growth_lo,
                "growth_cluster_ci_high": growth_hi,
                "success_rate_ge_3pct": d["development_success_ge_3pct"].mean(),
                "success_cluster_ci_low": success_lo,
                "success_cluster_ci_high": success_hi,
                "uncertainty": "country-cluster bootstrap",
                "interpretation": "descriptive regime comparison; not causal",
            }
        )
    summary = pd.DataFrame(rows)

    model_data = spells.dropna(
        subset=[
            "start_gdppc_constant_2015usd",
            "mean_investment_pct_gdp",
            "mean_trade_pct_gdp",
        ]
    ).copy()
    model_data["log_start_gdppc"] = np.log(model_data["start_gdppc_constant_2015usd"])
    model = smf.ols(
        "outcome_gdppc_growth_pct ~ C(regime, Treatment(reference='stable_developing')) + "
        "log_start_gdppc + mean_investment_pct_gdp + mean_trade_pct_gdp + C(cohort_start)",
        data=model_data,
    ).fit(cov_type="cluster", cov_kwds={"groups": model_data["country_code"]})
    for regime in ["conflict_affected", "low_capacity_nonconflict"]:
        term = "C(regime, Treatment(reference='stable_developing'))" f"[T.{regime}]"
        summary.loc[
            summary["regime"].eq(regime), "adjusted_difference_vs_stable_pp"
        ] = model.params.get(term)
        summary.loc[summary["regime"].eq(regime), "adjusted_ci_low"] = (
            model.conf_int().loc[term, 0]
        )
        summary.loc[summary["regime"].eq(regime), "adjusted_ci_high"] = (
            model.conf_int().loc[term, 1]
        )
        summary.loc[summary["regime"].eq(regime), "adjusted_p_value"] = (
            model.pvalues.get(term)
        )
    summary["adjusted_model_n"] = int(model.nobs)
    summary["adjusted_model_note"] = (
        "OLS association with cohort FE and observed initial income/investment/trade; country-clustered SE"
    )
    summary.to_csv(PROC / "fragile_state_group_summary.csv", index=False)
    return summary


def definition_sensitivity(panel: pd.DataFrame) -> pd.DataFrame:
    """Rebuild regime summaries over conflict and capacity definitions."""
    conflict_definitions = {
        "broad_any_25_deaths": "conflict_broad",
        "primary_wb_ucdp_medium_leg": "conflict_primary",
        "high_150_deaths_and_10_per_100k": "conflict_high",
    }
    candidate_windows = []
    for country_code, group in panel.groupby("country_code"):
        by_year = group.set_index("year")
        for start in SPELL_STARTS:
            exposure_end = start + EXPOSURE_YEARS - 1
            outcome_end = exposure_end + OUTCOME_YEARS
            if not all(
                year in by_year.index for year in range(start, exposure_end + 1)
            ):
                continue
            start_rel = float(
                pd.to_numeric(
                    pd.Series([by_year.at[start, "gdppc_relative_to_us"]]),
                    errors="coerce",
                ).iloc[0]
            )
            gdp0 = float(
                pd.to_numeric(
                    pd.Series([by_year.at[exposure_end, "gdppc_constant_2015usd"]]),
                    errors="coerce",
                ).iloc[0]
            )
            gdp1 = float(
                pd.to_numeric(
                    pd.Series(
                        [
                            (
                                by_year.at[outcome_end, "gdppc_constant_2015usd"]
                                if outcome_end in by_year.index
                                else np.nan
                            )
                        ]
                    ),
                    errors="coerce",
                ).iloc[0]
            )
            if (
                pd.isna(start_rel)
                or start_rel >= 0.50
                or pd.isna(gdp0)
                or pd.isna(gdp1)
                or gdp0 <= 0
                or gdp1 <= 0
            ):
                continue
            exposure = by_year.loc[start:exposure_end]
            capacity = exposure["government_effectiveness_score"].dropna()
            if len(capacity) < 3:
                continue
            candidate_windows.append(
                {
                    "country_code": country_code,
                    "cohort_start": start,
                    "mean_capacity": capacity.mean(),
                    "conflict_broad": bool(exposure["conflict_broad"].any()),
                    "conflict_primary": bool(exposure["conflict_primary"].any()),
                    "conflict_high": bool(exposure["conflict_high"].any()),
                    "outcome_gdppc_growth_pct": 100
                    * ((gdp1 / gdp0) ** (1 / OUTCOME_YEARS) - 1),
                }
            )
    candidates = pd.DataFrame(candidate_windows)
    rows = []
    for capacity_cutoff in [20.0, 25.0, 30.0]:
        for conflict_name, conflict_column in conflict_definitions.items():
            classified = candidates.copy()
            classified["capacity_cutoff"] = capacity_cutoff
            classified["conflict_definition"] = conflict_name
            classified["regime"] = np.select(
                [
                    classified[conflict_column],
                    classified["mean_capacity"].lt(capacity_cutoff),
                ],
                ["conflict_affected", "low_capacity_nonconflict"],
                default="stable_developing",
            )
            rows.append(
                classified[
                    [
                        "capacity_cutoff",
                        "conflict_definition",
                        "country_code",
                        "cohort_start",
                        "regime",
                        "outcome_gdppc_growth_pct",
                    ]
                ]
            )
    detail = pd.concat(rows, ignore_index=True)
    out = (
        detail.groupby(["capacity_cutoff", "conflict_definition", "regime"])
        .agg(
            n_spells=("outcome_gdppc_growth_pct", "size"),
            n_countries=("country_code", "nunique"),
            mean_outcome_growth_pct=("outcome_gdppc_growth_pct", "mean"),
            median_outcome_growth_pct=("outcome_gdppc_growth_pct", "median"),
        )
        .reset_index()
    )
    stable = out[out["regime"].eq("stable_developing")][
        ["capacity_cutoff", "conflict_definition", "mean_outcome_growth_pct"]
    ].rename(columns={"mean_outcome_growth_pct": "stable_mean_growth_pct"})
    out = out.merge(stable, on=["capacity_cutoff", "conflict_definition"], how="left")
    out["unadjusted_difference_vs_stable_pp"] = (
        out["mean_outcome_growth_pct"] - out["stable_mean_growth_pct"]
    )
    out.to_csv(PROC / "fragile_state_definition_sensitivity.csv", index=False)
    return out


def chart_fragile_regimes(summary: pd.DataFrame) -> None:
    plot = summary.set_index("regime").loc[REGIME_ORDER].reset_index()
    x = np.arange(len(plot))
    means = plot["mean_outcome_growth_pct"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    ax1.bar(x, means, color=[REGIME_COLORS[r] for r in plot["regime"]])
    ax1.errorbar(
        x,
        means,
        yerr=[
            means - plot["growth_cluster_ci_low"],
            plot["growth_cluster_ci_high"] - means,
        ],
        fmt="none",
        color="black",
        capsize=5,
    )
    ax1.axhline(0, color="black", lw=1)
    ax1.set_xticks(x)
    ax1.set_xticklabels([REGIME_LABELS[r] for r in plot["regime"]])
    ax1.set_ylabel("Subsequent real GDP/cap growth (%/yr)")
    ax1.set_title("Four-year outcome growth after fixed exposure windows")
    for i, (mean, n_spells) in enumerate(
        zip(means.to_numpy(), plot["n_spells"].to_numpy())
    ):
        ax1.text(i, mean + 0.15, f"n={int(n_spells)}", ha="center", fontsize=9)

    rates = 100 * plot["success_rate_ge_3pct"]
    ax2.bar(x, rates, color=[REGIME_COLORS[r] for r in plot["regime"]])
    ax2.errorbar(
        x,
        rates,
        yerr=[
            rates - 100 * plot["success_cluster_ci_low"],
            100 * plot["success_cluster_ci_high"] - rates,
        ],
        fmt="none",
        color="black",
        capsize=5,
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels([REGIME_LABELS[r] for r in plot["regime"]])
    ax2.set_ylabel("Share with subsequent growth ≥3%/yr (%)")
    ax2.set_title("Development-success base rate")
    fig.suptitle(
        "Chart 127: Conflict and low state capacity are separate development regimes\n"
        "(developing <50% of US; non-overlapping windows; 95% country-cluster bootstrap intervals)",
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.01,
        "UCDP/WDI conflict proxy and revised WGI absolute government-effectiveness score; descriptive, not causal.",
        ha="center",
        fontsize=9,
        color="dimgray",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(CHARTS / "127_fragile_state_regime_outcomes.png")
    plt.close(fig)


def chart_fragile_sensitivity(sensitivity: pd.DataFrame) -> None:
    plot = sensitivity[~sensitivity["regime"].eq("stable_developing")].copy()
    conflict_order = [
        "broad_any_25_deaths",
        "primary_wb_ucdp_medium_leg",
        "high_150_deaths_and_10_per_100k",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    for ax, regime in zip(axes, ["conflict_affected", "low_capacity_nonconflict"]):
        d = plot[plot["regime"].eq(regime)]
        for cutoff, marker in zip([20.0, 25.0, 30.0], ["o", "s", "^"]):
            q = (
                d[d["capacity_cutoff"].eq(cutoff)]
                .set_index("conflict_definition")
                .reindex(conflict_order)
            )
            ax.plot(
                range(len(q)),
                q["unadjusted_difference_vs_stable_pp"],
                marker=marker,
                lw=2,
                label=f"capacity cutoff {cutoff:g}",
            )
        ax.axhline(0, color="black", lw=1)
        ax.set_xticks(range(3))
        ax.set_xticklabels(
            ["Broad\n≥25 deaths", "Primary\nWB-UCDP leg", "High\n≥10/100k"]
        )
        ax.set_title(REGIME_LABELS[regime].replace("\n", " "))
        ax.set_xlabel("Conflict definition")
    axes[0].set_ylabel("Mean growth difference vs stable developing (pp/yr)")
    axes[1].legend(fontsize=9)
    fig.suptitle(
        "Chart 128: Regime gaps are sensitive to conflict and capacity definitions\n"
        "(unadjusted fixed-window comparisons; sensitivity is evidence against a single precise effect)",
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(CHARTS / "128_fragile_state_definition_sensitivity.png")
    plt.close(fig)


def clean_investment_onsets(panel: pd.DataFrame) -> pd.DataFrame:
    """Identify sustained high-investment onsets after a clear low regime."""
    p = panel.sort_values(["country_code", "year"]).copy()
    investment_map = p.set_index(["country_code", "year"])[
        "gross_capital_formation_pct"
    ].to_dict()
    onset_rows = []
    for row in p.itertuples():
        c, year = str(row.country_code), int(str(row.year))
        if year < 1999 or year > 2019 or not row.developing_below_50pct_us:
            continue
        pre = [investment_map.get((c, year + k), np.nan) for k in [-2, -1]]
        treated = [investment_map.get((c, year + k), np.nan) for k in [0, 1]]
        if all(pd.notna(v) and v <= 20 for v in pre) and all(
            pd.notna(v) and v > 25 for v in treated
        ):
            onset_rows.append({"country_code": c, "onset_year": year})
    onsets = pd.DataFrame(onset_rows)
    if len(onsets):
        onsets = onsets.sort_values(["country_code", "onset_year"]).drop_duplicates(
            "country_code", keep="first"
        )
    return onsets


def pre_features(group: pd.DataFrame, year: int) -> dict[str, float]:
    """Features known before investment onset."""
    pre = group[group["year"].between(year - 3, year - 1)]
    return {
        "pre_log_gdppc": value_at(group, year - 1, "log_gdppc"),
        "pre_growth": pre["gdppc_growth_pct"].mean(),
        "pre_investment": pre["gross_capital_formation_pct"].mean(),
        "pre_trade": pre["trade_pct_gdp"].mean(),
        "pre_fertility": pre["fertility_rate"].mean(),
        "pre_government_effectiveness": value_at(
            group, year - 1, "government_effectiveness_score"
        ),
    }


MATCH_FEATURES = [
    "pre_log_gdppc",
    "pre_growth",
    "pre_investment",
    "pre_trade",
    "pre_fertility",
    "pre_government_effectiveness",
]


def has_clean_investment_window(
    group: pd.DataFrame, onset_year: int, pre_years: int, post_years: int = 5
) -> bool:
    """Require one finite investment observation <=25% in EVERY window year.

    Both endpoints are inclusive. Matched controls use -3..+5; synthetic
    donors use -5..+5, including their longer pre-fit period. Missing years,
    duplicate years, and missing/non-finite investment cannot establish a
    clean window, even if no sustained onset was recorded.
    """
    years = range(onset_year - pre_years, onset_year + post_years + 1)
    window = group[group["year"].between(years.start, years.stop - 1)]
    investment = window["gross_capital_formation_pct"]
    return bool(
        len(window) == len(years)
        and set(window["year"]) == set(years)
        and investment.notna().all()
        and np.isfinite(investment).all()
        and investment.le(25).all()
    )


def match_investment_events(
    panel: pd.DataFrame, onsets: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exact-year nearest-neighbour matching with clean control windows."""
    groups = {code: g.sort_values("year") for code, g in panel.groupby("country_code")}
    onset_keys = set(map(tuple, onsets[["country_code", "onset_year"]].to_numpy()))
    rows = []
    event_rows = []
    for treated_code, onset_year in onsets[["country_code", "onset_year"]].itertuples(
        index=False
    ):
        onset_year = int(onset_year)
        treated_group = groups[treated_code]
        region = treated_group["region"].iloc[0]
        treated_features = pre_features(treated_group, onset_year)
        if any(pd.isna(v) for v in treated_features.values()):
            continue
        candidates = []
        for control_code, control_group in groups.items():
            if control_code == treated_code:
                continue
            year_row = control_group[control_group["year"].eq(onset_year)]
            if not len(year_row) or not bool(
                year_row["developing_below_50pct_us"].iloc[0]
            ):
                continue
            # No sustained-onset event or >25% investment anywhere in the full
            # event window: controls are not-yet/window-clean.
            if any((control_code, onset_year + k) in onset_keys for k in range(-3, 6)):
                continue
            if not has_clean_investment_window(control_group, onset_year, pre_years=3):
                continue
            features = pre_features(control_group, onset_year)
            if any(pd.isna(v) for v in features.values()):
                continue
            candidates.append({"country_code": control_code, **features})
        if len(candidates) < 3:
            continue
        pool = pd.DataFrame(candidates)
        combined = pd.concat(
            [pool[MATCH_FEATURES], pd.DataFrame([treated_features])], ignore_index=True
        )
        scale = combined.std().replace(0, 1)
        distance = pd.Series(
            np.sqrt(
                (((pool[MATCH_FEATURES] - pd.Series(treated_features)) / scale) ** 2)
                .sum(axis=1)
                .to_numpy(dtype=float)
            ),
            index=pool.index,
        )
        nearest_pos = int(distance.argmin())
        nearest = pool.iloc[nearest_pos]
        control_code = str(nearest["country_code"])
        match_distance = float(distance.iloc[nearest_pos])
        pair_id = f"{treated_code}_{onset_year}"
        rows.append(
            {
                "pair_id": pair_id,
                "treated_country_code": treated_code,
                "treated_country": treated_group["country"].iloc[0],
                "control_country_code": control_code,
                "control_country": groups[control_code]["country"].iloc[0],
                # Retain region as a compatibility alias for treated_region.
                "region": region,
                "treated_region": region,
                "control_region": groups[control_code]["region"].iloc[0],
                "same_region": region == groups[control_code]["region"].iloc[0],
                "onset_year": onset_year,
                "match_distance": match_distance,
                **treated_features,
                **{f"control_{k}": nearest[k] for k in MATCH_FEATURES},
                "treatment_definition": "investment >25% GDP for t..t+1 after <=20% for t-2..t-1",
            }
        )
        for event_time in range(-3, 6):
            year = onset_year + event_time
            treated_growth = value_at(treated_group, year, "gdppc_growth_pct")
            control_growth = value_at(groups[control_code], year, "gdppc_growth_pct")
            event_rows.append(
                {
                    "pair_id": pair_id,
                    "treated_country_code": treated_code,
                    "control_country_code": control_code,
                    "onset_year": onset_year,
                    "event_time": event_time,
                    "treated_growth_pct": treated_growth,
                    "control_growth_pct": control_growth,
                    "difference_pp": treated_growth - control_growth,
                }
            )
    matches = pd.DataFrame(rows)
    events = pd.DataFrame(event_rows).dropna(subset=["difference_pp"])
    matches.to_csv(PROC / "causal_development_matched_events.csv", index=False)
    return matches, events


def bootstrap_event_series(events: pd.DataFrame) -> pd.DataFrame:
    countries = events["treated_country_code"].unique()
    clusters = [
        events[events["treated_country_code"].eq(code)][
            ["event_time", "difference_pp"]
        ].to_numpy()
        for code in countries
    ]
    rng = np.random.default_rng(RNG_SEED)
    draw_rows = []
    for draw in range(BOOTSTRAPS):
        selected = rng.integers(0, len(clusters), size=len(clusters))
        sample = np.vstack([clusters[index] for index in selected])
        for event_time in np.unique(sample[:, 0]):
            value = sample[sample[:, 0] == event_time, 1].mean()
            draw_rows.append({"draw": draw, "event_time": event_time, "value": value})
    draws = pd.DataFrame(draw_rows)
    summary = (
        events.groupby("event_time")
        .agg(
            treated_growth_pct=("treated_growth_pct", "mean"),
            control_growth_pct=("control_growth_pct", "mean"),
            difference_pp=("difference_pp", "mean"),
            n_pairs=("pair_id", "nunique"),
        )
        .reset_index()
    )
    intervals = (
        draws.groupby("event_time")["value"]
        .quantile(np.array([0.025, 0.975]))
        .unstack()
    )
    intervals.columns = ["cluster_ci_low", "cluster_ci_high"]
    return summary.merge(intervals, left_on="event_time", right_index=True, how="left")


def pre_period_balance_diagnostic(p_value: float) -> dict:
    """Label the zero-pre-gap Wald test without calling it a trends test."""
    available = bool(np.isfinite(p_value))
    not_rejected = bool(p_value >= 0.10) if available else None
    if not available:
        status = "unavailable (non-finite p-value)"
    elif not_rejected:
        status = "not rejected at 10%"
    else:
        status = "rejected at 10%"
    note = (
        "joint country-clustered Wald test that the mean treated-minus-control "
        "growth gap is zero at each event time -3,-2,-1; pre-period balance "
        "diagnostic, not a test of parallel trends; non-rejection is not proof "
        "of parallel trends or causal identification"
    )
    return {
        "pre_period_balance_joint_p_value": p_value,
        "pre_period_balance_not_rejected_10pct": not_rejected,
        "pre_period_balance_status": status,
        "pre_period_balance_note": note,
        # Retain old CSV/dict keys for consumers, explicitly marked as aliases.
        "pretrend_joint_p_value": p_value,
        "pretrend_passes_10pct": not_rejected,
        "pretrend_note": (
            "Deprecated pretrend_* compatibility aliases refer to pre-period "
            "balance, not parallel trends. " + note
        ),
    }


def matched_estimates(
    events: pd.DataFrame, event_summary: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Estimate post contrast, DiD, and a joint pre-period balance diagnostic."""
    by_pair = events.pivot(
        index="pair_id", columns="event_time", values="difference_pp"
    )
    pre_cols = [c for c in [-3, -2, -1] if c in by_pair.columns]
    post_cols = [c for c in [1, 2, 3, 4, 5] if c in by_pair.columns]
    pair_stats = pd.DataFrame(
        {
            "treated_country_code": by_pair.index.str.split("_").str[0],
            "pre_mean": by_pair[pre_cols].mean(axis=1),
            "post_mean": by_pair[post_cols].mean(axis=1),
        },
        index=by_pair.index,
    ).dropna()
    pair_stats["did"] = pair_stats["post_mean"] - pair_stats["pre_mean"]
    rng = np.random.default_rng(RNG_SEED + 1)
    countries = pair_stats["treated_country_code"].unique()
    clusters = [
        pair_stats.loc[
            pair_stats["treated_country_code"].eq(code), ["post_mean", "did"]
        ].to_numpy()
        for code in countries
    ]
    boot_post, boot_did = [], []
    for _ in range(BOOTSTRAPS):
        selected = rng.integers(0, len(clusters), size=len(clusters))
        sample = np.vstack([clusters[index] for index in selected])
        boot_post.append(sample[:, 0].mean())
        boot_did.append(sample[:, 1].mean())

    pre = events[events["event_time"].lt(0)].copy()
    pre_model = smf.ols("difference_pp ~ event_time", data=pre).fit(
        cov_type="cluster", cov_kwds={"groups": pre["treated_country_code"]}
    )
    pre_means_model = smf.ols("difference_pp ~ 0 + C(event_time)", data=pre).fit(
        cov_type="cluster", cov_kwds={"groups": pre["treated_country_code"]}
    )
    joint = pre_means_model.wald_test(np.eye(len(pre_means_model.params)), scalar=True)
    diagnostics = {
        "pre_level_pp": float(pre["difference_pp"].mean()),
        "pre_slope_pp_per_year": float(pre_model.params["event_time"]),
        **pre_period_balance_diagnostic(float(joint.pvalue)),
    }
    causal_status = (
        "not identified; pre-period balance "
        f"{diagnostics['pre_period_balance_status']}; "
        "parallel trends not established; endogenous onset and unobserved shocks remain"
    )
    rows = [
        {
            "method": "matched_event_study_post_level",
            "estimand": "mean treated-minus-control GDP/cap growth, event years +1..+5",
            "point_estimate": pair_stats["post_mean"].mean(),
            "ci_low": np.quantile(boot_post, 0.025),
            "ci_high": np.quantile(boot_post, 0.975),
            "n_events": len(pair_stats),
            **diagnostics,
            "causal_status": causal_status,
        },
        {
            "method": "matched_event_study_did",
            "estimand": "post (+1..+5) minus pre (-3..-1) matched growth difference",
            "point_estimate": pair_stats["did"].mean(),
            "ci_low": np.quantile(boot_did, 0.025),
            "ci_high": np.quantile(boot_did, 0.975),
            "n_events": len(pair_stats),
            **diagnostics,
            "causal_status": causal_status,
        },
    ]
    for key, value in diagnostics.items():
        event_summary[key] = value
    event_summary.to_csv(PROC / "causal_development_event_study.csv", index=False)
    return pd.DataFrame(rows), diagnostics


def synthetic_weights(target: np.ndarray, donors: np.ndarray) -> np.ndarray | None:
    """Nonnegative simplex weights with light ridge regularization."""
    n_donors = donors.shape[0]
    if n_donors < 3:
        return None
    scale = np.nanstd(np.vstack([target, donors]), axis=0)
    scale[~np.isfinite(scale) | (scale == 0)] = 1.0
    center = np.nanmean(np.vstack([target, donors]), axis=0)
    target_z = (target - center) / scale
    donors_z = (donors - center) / scale

    def objective(weights: np.ndarray) -> float:
        residual = target_z - weights @ donors_z
        return float(residual @ residual + 1e-4 * (weights @ weights))

    result = minimize(
        objective,
        np.repeat(1 / n_donors, n_donors),
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n_donors,
        constraints={"type": "eq", "fun": lambda weights: weights.sum() - 1.0},
        options={"maxiter": 1_000, "ftol": 1e-10},
    )
    return result.x if result.success else None


def synthetic_control_like(
    panel: pd.DataFrame, onsets: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit synthetic-control-like trajectories for clean investment onsets."""
    groups = {code: g.sort_values("year") for code, g in panel.groupby("country_code")}
    onset_by_country = onsets.set_index("country_code")["onset_year"].to_dict()
    trajectory_rows = []
    fit_rows = []
    for treated_code, onset_year in onsets[["country_code", "onset_year"]].itertuples(
        index=False
    ):
        onset_year = int(onset_year)
        treated = groups[treated_code]
        region = treated["region"].iloc[0]
        event_times = list(range(-5, 6))
        treated_log = np.array(
            [value_at(treated, onset_year + k, "log_gdppc") for k in event_times]
        )
        treated_inv = np.array(
            [
                value_at(treated, onset_year + k, "gross_capital_formation_pct")
                for k in range(-5, 0)
            ]
        )
        if np.isnan(treated_log).any() or np.isnan(treated_inv).any():
            continue
        donors = []
        for code, group in groups.items():
            if code == treated_code or group["region"].iloc[0] != region:
                continue
            year_row = group[group["year"].eq(onset_year)]
            if not len(year_row) or not bool(
                year_row["developing_below_50pct_us"].iloc[0]
            ):
                continue
            other_onset = onset_by_country.get(code)
            if other_onset is not None and abs(int(other_onset) - onset_year) <= 5:
                continue
            if not has_clean_investment_window(group, onset_year, pre_years=5):
                continue
            logs = np.array(
                [value_at(group, onset_year + k, "log_gdppc") for k in event_times]
            )
            inv = np.array(
                [
                    value_at(group, onset_year + k, "gross_capital_formation_pct")
                    for k in range(-5, 0)
                ]
            )
            if np.isnan(logs).any() or np.isnan(inv).any():
                continue
            donors.append(
                {
                    "country_code": code,
                    "region": group["region"].iloc[0],
                    "logs": logs,
                    "investment": inv,
                }
            )
        if len(donors) < MIN_SYNTHETIC_DONORS:
            continue
        # Limit the donor pool by pre-treatment level proximity before the
        # constrained fit; this avoids unstable high-dimensional simplex fits.
        donors.sort(key=lambda d: abs(d["logs"][4] - treated_log[4]))
        donors = donors[:MAX_SYNTHETIC_DONORS]
        # Fit pre-treatment trajectories relative to t=-1. Absolute levels are
        # addressed first by the level-proximity donor restriction; relative
        # paths avoid reporting a large level gap as an onset effect.
        target_predictors = np.concatenate(
            [treated_log[:5] - treated_log[4], treated_inv / 25]
        )
        donor_predictors = np.vstack(
            [
                np.concatenate([d["logs"][:5] - d["logs"][4], d["investment"] / 25])
                for d in donors
            ]
        )
        weights = synthetic_weights(target_predictors, donor_predictors)
        if weights is None:
            continue
        donor_logs = np.vstack([d["logs"] for d in donors])
        synthetic_log = weights @ donor_logs
        treated_relative = treated_log - treated_log[4]
        synthetic_relative = synthetic_log - synthetic_log[4]
        gaps = 100 * (np.exp(treated_relative - synthetic_relative) - 1)
        pre_rmspe = float(np.sqrt(np.mean(np.square(gaps[:5]))))
        post_rmspe = float(np.sqrt(np.mean(np.square(gaps[5:]))))
        effective_donors = float(1 / np.square(weights).sum())
        fit_rows.append(
            {
                "treated_country_code": treated_code,
                "treated_country": treated["country"].iloc[0],
                "onset_year": onset_year,
                # Retain region as a compatibility alias for treated_region.
                "region": region,
                "treated_region": region,
                # Lists are aligned in optimizer order (including zero weights).
                "donor_country_codes": ";".join(str(d["country_code"]) for d in donors),
                "donor_regions": ";".join(str(d["region"]) for d in donors),
                "donor_weights": ";".join(format(float(w), ".17g") for w in weights),
                "n_donors": len(donors),
                "effective_donors": effective_donors,
                "pre_rmspe_pct": pre_rmspe,
                "post_rmspe_pct": post_rmspe,
                "post_pre_rmspe_ratio": (
                    post_rmspe / pre_rmspe if pre_rmspe > 0 else np.nan
                ),
                "mean_post_gap_pct": gaps[6:].mean(),
                "largest_weight": weights.max(),
                "largest_weight_country": donors[int(weights.argmax())]["country_code"],
                "largest_weight_region": donors[int(weights.argmax())]["region"],
                "method_note": (
                    "synthetic-control-like; same-region donors with observed investment "
                    "<=25% GDP in every year -5..+5 inclusive; endogenous treatment "
                    "and no randomization inference"
                ),
            }
        )
        for event_time, actual, synthetic, gap in zip(
            event_times, treated_log, synthetic_log, gaps
        ):
            trajectory_rows.append(
                {
                    "treated_country_code": treated_code,
                    "onset_year": onset_year,
                    "event_time": event_time,
                    "actual_gdppc_index": 100 * np.exp(actual - treated_log[0]),
                    "synthetic_gdppc_index": 100 * np.exp(synthetic - synthetic_log[0]),
                    "actual_minus_synthetic_pct": gap,
                    "pre_rmspe_pct": pre_rmspe,
                    "effective_donors": effective_donors,
                }
            )
    trajectories = pd.DataFrame(trajectory_rows, columns=SYNTHETIC_TRAJECTORY_COLUMNS)
    fits = pd.DataFrame(fit_rows, columns=SYNTHETIC_FIT_COLUMNS)
    support = synthetic_support(len(fits))
    for frame in (trajectories, fits):
        frame["reporting_scope"] = "diagnostic_only"
        frame["aggregate_status"] = support["status"]
        frame["retained_cases"] = len(fits)
        frame["required_cases"] = MIN_SYNTHETIC_CASES
        frame["interpretation_limit"] = (
            "Case trajectories, gaps, fit diagnostics and donor weights are diagnostic-only; "
            "not causal effects or aggregate inference. " + support["reporting_note"]
        )
    trajectories.to_csv(PROC / "causal_development_synthetic_controls.csv", index=False)
    fits.to_csv(PROC / "causal_development_synthetic_fit.csv", index=False)
    return trajectories, fits


def synthetic_support(n_cases: int) -> dict:
    """One reporting gate for estimates, method limits, and Chart 130."""
    supported = n_cases >= MIN_SYNTHETIC_CASES
    return {
        "status": "estimated_with_diagnostic" if supported else "insufficient_support",
        "n_events": n_cases,
        "required_events": MIN_SYNTHETIC_CASES,
        "reporting_note": (
            f"Retained cases: {n_cases}; required cases: {MIN_SYNTHETIC_CASES}. "
            + (
                "Descriptive aggregate only; not causal identification."
                if supported else
                "Aggregate estimate and confidence intervals withheld; "
                "retained cases are diagnostic-only."
            )
        ),
    }


def synthetic_estimate(trajectories: pd.DataFrame, fits: pd.DataFrame) -> pd.DataFrame:
    """Gate each aggregate independently, including the fit-quality subset.

    Sparse cases retain diagnostics but never enter an aggregate bootstrap.
    Status rows replace previous numerical releases, including for zero cases.
    """
    by_case = (
        trajectories[trajectories["event_time"].between(1, 5)]
        .groupby("treated_country_code")["actual_minus_synthetic_pct"]
        .mean()
    )
    rng = np.random.default_rng(RNG_SEED + 2)
    rows = []
    for method, subset, suffix in (
        ("synthetic_control_like", fits, ""),
        ("synthetic_control_like_pre_rmspe_le_5pct",
         fits[fits["pre_rmspe_pct"].le(5)], ", pre-RMSPE <=5%"),
    ):
        values = by_case[by_case.index.isin(subset["treated_country_code"])].to_numpy()
        support = synthetic_support(len(values))
        point, low, high = np.nan, np.nan, np.nan
        if support["status"] == "estimated_with_diagnostic":
            boots = [
                rng.choice(values, size=len(values), replace=True).mean()
                for _ in range(BOOTSTRAPS)
            ]
            point = values.mean()
            low, high = np.quantile(boots, [0.025, 0.975])
        rows.append({
            "method": method,
            "estimand": "mean actual-minus-synthetic GDP/cap level gap, event years +1..+5 (%)" + suffix,
            "point_estimate": point,
            "ci_low": low,
            "ci_high": high,
            **support,
            "median_pre_rmspe_pct": subset["pre_rmspe_pct"].median() if len(subset) else np.nan,
            "median_effective_donors": subset["effective_donors"].median() if len(subset) else np.nan,
            "causal_status": "not identified; " + support["reporting_note"],
        })
    return pd.DataFrame(rows)


def method_limits(synthetic_rows: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = [
        (
            "official historical FCS treatment panel",
            "unsupported",
            "World Bank classifications change methodology; FY26 status cannot be backcast. The script exports an official FY26 crosswalk and uses transparent annual UCDP/WGI proxies for history.",
        ),
        (
            "exact replication of World Bank FY20-FY26 conflict tier",
            "unsupported",
            "The official rule combines ACLED and UCDP plus qualitative review. Only the authoritative WDI/UCDP series is pooled here, so the primary rule is explicitly the UCDP leg.",
        ),
        (
            "political regime type",
            "unsupported",
            "No verified democracy/autocracy panel is present in the repository; WGI political stability is not relabeled as regime type.",
        ),
        (
            "regression discontinuity",
            "unsupported",
            "The 20/25% investment cutoffs define exposure; no externally assigned running variable or policy eligibility threshold exists.",
        ),
        (
            "instrumental variables",
            "unsupported",
            "No defensible external instrument is available in the pooled files.",
        ),
        (
            "causal effect of high investment",
            "not identified",
            "Investment onset is endogenous to reforms, commodity cycles, reconstruction, and expected growth. Matching and synthetic weighting address observables/pre-fit only.",
        ),
        (
            "matched event study",
            "estimated with diagnostic",
            "Conditional comparison using exact onset year and standardized Euclidean distance on "
            + ", ".join(MATCH_FEATURES)
            + ". Region is neither a distance feature nor an exact restriction; "
            "treated_region and control_region are exported (legacy region means treated_region). "
            "Controls require observed investment <=25% GDP in every year -3..+5 inclusive. "
            "Country-cluster bootstrap and a joint pre-period balance diagnostic are reported: "
            "zero mean growth gaps at -3,-2,-1, not parallel trends. Deprecated pretrend_* "
            "fields are compatibility aliases for balance; non-rejection does not establish causality.",
        ),
        (
            "synthetic-control-like comparison",
            "not_evaluated" if synthetic_rows is None else synthetic_rows.iloc[0]["status"],
            "Same-region developing donors require observed investment <=25% GDP in every "
            f"year -5..+5 inclusive and complete log-GDP trajectories; at least {MIN_SYNTHETIC_DONORS} eligible "
            f"donors per case, capped at {MAX_SYNTHETIC_DONORS} by pre-onset level proximity. Donor country codes, "
            "regions and full nonnegative donor weights are exported in aligned optimizer order "
            "(semicolon-separated, including zero weights), as diagnostic-only data. Weights and "
            "pre-fit RMSPE reported; no randomization inference or claim that donor weights "
            "remove unobserved shocks. Clean-window selection uses post-onset investment "
            "and is descriptive, not an ex ante assignment rule. "
            f"Each aggregate, including the fit-quality subset, requires {MIN_SYNTHETIC_CASES} cases. "
            + (
                "Support not evaluated; no aggregate reporting status asserted."
                if synthetic_rows is None else
                " ".join(
                    f"{row.method}: {row.status}. {row.reporting_note}"
                    for row in synthetic_rows.itertuples(index=False)
                )
            ),
        ),
        (
            "WGI government effectiveness",
            "measurement caveat",
            "Perception-based composite with uncertainty; 2025 revision recalculates history to 1996. Cutoffs 20/25/30 are sensitivity definitions, not natural thresholds.",
        ),
        (
            "battle deaths",
            "measurement caveat",
            "UCDP/WDI records battle-related deaths, not all organized violence or civilian harm; absent country-years are treated as no recorded deaths.",
        ),
    ]
    out = pd.DataFrame(rows, columns=["requested_element", "status", "reason_or_limit"])
    out.to_csv(PROC / "causal_development_method_limits.csv", index=False)
    return out


def chart_matched_event(event_summary: pd.DataFrame, diagnostics: dict) -> None:
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11, 9), sharex=True, gridspec_kw={"height_ratios": [3, 2]}
    )
    for ax in (ax1, ax2):
        ax.axvspan(-3.4, -0.5, color="#fff3e0", alpha=0.8)
        ax.axvline(0, color="black", ls=":", lw=1)
    ax1.plot(
        event_summary["event_time"],
        event_summary["treated_growth_pct"],
        "o-",
        lw=2,
        color="#d1495b",
        label="High-investment onset",
    )
    ax1.plot(
        event_summary["event_time"],
        event_summary["control_growth_pct"],
        "s--",
        lw=2,
        color="#3a7ca5",
        label="Matched window-clean control",
    )
    ax1.axhline(0, color="gray", lw=1)
    ax1.set_ylabel("Real GDP/cap growth (%/yr)")
    ax1.legend()
    ax1.set_title("Growth paths around sustained high-investment onset")
    ax2.plot(
        event_summary["event_time"],
        event_summary["difference_pp"],
        "o-",
        color="#2e7d32",
        lw=2,
    )
    ax2.fill_between(
        event_summary["event_time"],
        event_summary["cluster_ci_low"],
        event_summary["cluster_ci_high"],
        color="#2e7d32",
        alpha=0.2,
        label="95% country-cluster bootstrap interval",
    )
    ax2.axhline(0, color="gray", lw=1)
    ax2.set_xlabel("Years relative to investment onset (t=0)")
    ax2.set_ylabel("Treated − control (pp/yr)")
    ax2.legend(fontsize=9)
    fig.suptitle(
        "Chart 129: Matched investment event study — pre-period balance, not parallel trends\n"
        f"joint zero-pre-gap p={diagnostics['pre_period_balance_joint_p_value']:.3f}; "
        f"pre slope={diagnostics['pre_slope_pp_per_year']:+.2f} pp/year",
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.01,
        "Exact year, nearest observed pre-state. Investment onset remains endogenous; estimates are not causal.",
        ha="center",
        fontsize=9,
        color="dimgray",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(CHARTS / "129_causal_development_matched_event_study.png")
    plt.close(fig)


def chart_synthetic(trajectories: pd.DataFrame, fits: pd.DataFrame) -> None:
    support = synthetic_support(len(fits))
    if support["status"] == "insufficient_support":
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_axis_off()
        ax.text(
            0.5, 0.82, "Chart 130: Synthetic aggregate withdrawn", ha="center",
            fontsize=20, fontweight="bold", transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.64, "Insufficient support", ha="center", fontsize=18,
            color="#b23a48", transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.47,
            f"Retained cases: {len(fits)} | Required cases: {MIN_SYNTHETIC_CASES}",
            ha="center", fontsize=16, transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.25,
            "Clean same-region donors leave too few cases for aggregate reporting.\n"
            "No aggregate effect, trajectory, or confidence interval is published.\n"
            "Case diagnostics and donor weights remain diagnostic-only, not causal evidence.",
            ha="center", fontsize=11, linespacing=1.8, transform=ax.transAxes,
        )
        fig.tight_layout()
        fig.savefig(CHARTS / "130_causal_development_synthetic_control.png")
        plt.close(fig)
        return
    means = (
        trajectories.groupby("event_time")
        .agg(
            actual=("actual_gdppc_index", "mean"),
            synthetic=("synthetic_gdppc_index", "mean"),
            gap=("actual_minus_synthetic_pct", "mean"),
        )
        .reset_index()
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    ax1.axvspan(-5.4, -0.5, color="#fff3e0", alpha=0.8)
    ax1.axvline(0, color="black", ls=":", lw=1)
    ax1.plot(means["event_time"], means["actual"], "o-", lw=2.2, label="Actual")
    ax1.plot(
        means["event_time"], means["synthetic"], "s--", lw=2.2, label="Synthetic-like"
    )
    ax1.set_xlabel("Event time")
    ax1.set_ylabel("GDP/cap index (t=-5 = 100 within case)")
    ax1.set_title("Average actual and weighted-donor trajectories")
    ax1.legend()

    ordered = fits.sort_values("pre_rmspe_pct", ascending=True).reset_index(drop=True)
    ax2.scatter(
        ordered["pre_rmspe_pct"],
        ordered["mean_post_gap_pct"],
        c=ordered["post_pre_rmspe_ratio"],
        cmap="viridis",
        s=70,
        edgecolor="white",
    )
    ax2.axhline(0, color="black", lw=1)
    ax2.set_xlabel("Pre-treatment RMSPE (%) — lower is better fit")
    ax2.set_ylabel("Mean actual − synthetic GDP/cap gap, t=+1..+5 (%)")
    ax2.set_title("Case estimates depend on pre-treatment fit")
    fig.suptitle(
        "Chart 130: Synthetic-control-like evidence is a robustness check, not an experiment\n"
        f"Retained cases: {len(fits)}; required cases: {MIN_SYNTHETIC_CASES}; "
        f"median pre-RMSPE={fits['pre_rmspe_pct'].median():.1f}%",
        fontweight="bold",
    )
    fig.text(0.5, 0.01, "Descriptive aggregate; case diagnostics are diagnostic-only. Not causal evidence.",
             ha="center", fontsize=9, color="dimgray")
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.savefig(CHARTS / "130_causal_development_synthetic_control.png")
    plt.close(fig)


def main() -> None:
    print("=" * 82)
    print("ANALYSIS 30 — FRAGILE-STATE REGIMES + CAUSAL-DEVELOPMENT DIAGNOSTICS")
    print("=" * 82)
    panel, crosswalk = build_country_year_panel()
    spells = build_fixed_window_spells(panel)
    regime_summary = summarize_regimes(spells)
    sensitivity = definition_sensitivity(panel)
    chart_fragile_regimes(regime_summary)
    chart_fragile_sensitivity(sensitivity)

    onsets = clean_investment_onsets(panel)
    matches, event_detail = match_investment_events(panel, onsets)
    if len(matches) < MIN_MATCHED_EVENTS:
        raise RuntimeError(
            f"Only {len(matches)} matched investment events; required {MIN_MATCHED_EVENTS}; design is too sparse"
        )
    event_summary = bootstrap_event_series(event_detail)
    matched_rows, diagnostics = matched_estimates(event_detail, event_summary)
    trajectories, fits = synthetic_control_like(panel, onsets)
    synthetic_row = synthetic_estimate(trajectories, fits)
    estimates = pd.concat([matched_rows, synthetic_row], ignore_index=True, sort=False)
    estimates.to_csv(PROC / "causal_development_estimates.csv", index=False)
    limits = method_limits(synthetic_row)
    chart_matched_event(event_summary, diagnostics)
    chart_synthetic(trajectories, fits)

    print("\nFRAGILE-STATE FIXED-WINDOW RESULTS")
    print(
        regime_summary[
            [
                "regime",
                "n_spells",
                "n_countries",
                "mean_outcome_growth_pct",
                "growth_cluster_ci_low",
                "growth_cluster_ci_high",
                "success_rate_ge_3pct",
                "adjusted_difference_vs_stable_pp",
                "adjusted_ci_low",
                "adjusted_ci_high",
            ]
        ].to_string(index=False, float_format=lambda x: f"{x:.3f}")
    )
    primary = sensitivity[
        sensitivity["capacity_cutoff"].eq(PRIMARY_CAPACITY_CUTOFF)
        & sensitivity["conflict_definition"].eq("primary_wb_ucdp_medium_leg")
    ]
    print("\nPrimary definition check:")
    print(primary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(
        f"\nOfficial FY26 crosswalk: {len(crosswalk)} economies; current status only."
    )

    print("\nCAUSAL-DEVELOPMENT DIAGNOSTICS")
    print(f"Candidate clean investment onsets: {len(onsets)}")
    print(f"Matched events: {len(matches)}; synthetic-control-like cases: {len(fits)}")
    print(estimates.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nUnsupported/limited requested elements:")
    print(limits[["requested_element", "status"]].to_string(index=False))
    print(
        "\nBOTTOM LINE: regime gaps and investment-onset contrasts are conditional "
        "associations. Causal identification requires an external assignment rule, "
        "instrument, or credible policy discontinuity that these data do not contain."
    )
    print(
        "\nSaved all Analysis 30 processed CSVs and Charts 127–130. README.md was not edited."
    )


if __name__ == "__main__":
    main()
