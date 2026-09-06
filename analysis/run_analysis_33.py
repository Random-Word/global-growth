#!/usr/bin/env python3
# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false
"""Analysis 33: externally driven commodity windfalls and development outcomes.

This analysis combines official World Bank Pink Sheet price indices with lagged
WDI export composition. A country-year windfall is the sum, across fuel, metals,
food, and agricultural raw materials, of the global log price change times the
country's average category export share of GDP in years t-5 through t-3.
Contemporaneous export shares are never used.

Identification comes from differential predetermined exposure to common global
price movements, conditional on country and year fixed effects. The main sample
removes countries supplying more than 3% of observed world exports in any one
category on average, reducing (not eliminating) price-setting concerns. Results
remain vulnerable to exposure-specific global shocks, endogenous historical
specialization, anticipation, and multiple direct channels. The shock is a
commodity windfall, not an instrument for investment and not a randomized
policy.

Offline prerequisites (run upstream analyses separately):
- analysis/download_data.py: data/processed/wdi_combined.csv and
    data/raw/wb_country_regions.csv, including the commodity-export indicators.
- analysis/run_analysis_29.py: growth_incidence_heterogeneity_data.csv.
- analysis/run_analysis_30.py: fragile_state_country_year_panel.csv (WGI).
- Manually cache the official World Bank annual Pink Sheet workbook at
    data/raw/causal_extensions/CMO-Historical-Data-Annual.xlsx from
    https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Annual.xlsx
    (landing page: https://www.worldbank.org/en/research/commodity-markets).
    This script never downloads inputs. SHA-256 identifies the cached bytes,
    not a verified release or an authenticated download date.

Central results retain country-clustered covariance and normal-reference 95%
intervals. A separate headline sensitivity uses country + year - country/year
intersection cluster covariance, with componentwise finite-sample corrections
and t(min(country clusters, year clusters)-1) reference intervals. It exports
the shock/lag coefficient covariance submatrix and shock variance components.
Neither method guarantees precision with few effective common price shocks;
year counts are not counts of independent price innovations. Negative shock
variance is flagged, never clipped into a spurious standard error.

Outputs:
- data/processed/commodity_price_indices.csv
- data/processed/commodity_windfall_country_year.csv
- data/processed/commodity_windfall_local_projections.csv
- data/processed/commodity_windfall_two_way_sensitivity.csv
- data/processed/commodity_windfall_robustness.csv
- data/processed/commodity_windfall_governance.csv
- data/processed/commodity_windfall_growth_incidence.csv
- data/processed/commodity_windfall_category_estimates.csv
- data/processed/commodity_windfall_year_influence.csv
- data/processed/commodity_windfall_diagnostics.csv
- data/processed/commodity_windfall_method_limits.csv
- charts/139_commodity_windfall_local_projections.png
- charts/140_commodity_windfall_governance.png
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy.stats import t as student_t
from statsmodels.regression.linear_model import RegressionResultsWrapper
from statsmodels.stats.sandwich_covariance import cov_cluster_2groups

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
OUTPUT_DIR = PROC
CHARTS = BASE / "charts"
CAUSAL_RAW = RAW / "causal_extensions"
for directory in (PROC, CHARTS, CAUSAL_RAW):
    directory.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="colorblind")
plt.rcParams.update(
    {
        "figure.figsize": (12, 7),
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)

PRICE_FILE = CAUSAL_RAW / "CMO-Historical-Data-Annual.xlsx"
PRICE_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "5d903e848db1d1b83e0ec8f744e55570-0350012021/related/"
    "CMO-Historical-Data-Annual.xlsx"
)
INFERENCE_LIMIT = (
    "Few effective common price innovations; year clusters are not independent "
    "shock counts. Neither clustering scheme establishes precise causal effects."
)
CATEGORIES = {
    "fuel": ("fuel_exports_pct_merchandise", "energy_price_index"),
    "metals": ("ores_metals_exports_pct_merchandise", "metals_price_index"),
    "food": ("food_exports_pct_merchandise", "food_price_index"),
    "ag_raw": ("ag_raw_exports_pct_merchandise", "ag_raw_price_index"),
}
OUTCOMES = {
    "gdppc": "Real GDP per capita",
    "investment": "Investment share of GDP",
    "government_revenue": "Government revenue share of GDP",
    "government_expense": "Government expense share of GDP",
    "inflation": "Consumer-price inflation",
}
DOMINANT_EXPORT_SHARE = 0.03
MIN_COUNTRIES = 30


def validate_annual_keys(frame: pd.DataFrame) -> None:
    if frame[["country_code", "year"]].isna().any().any():
        raise ValueError("Annual panel requires nonmissing country_code/year keys")
    if frame.duplicated(["country_code", "year"]).any():
        raise ValueError("Annual panel requires unique country_code/year keys")
    years = pd.to_numeric(frame["year"], errors="coerce")
    if not np.isfinite(years).all() or not years.eq(np.floor(years)).all():
        raise ValueError("Annual panel requires integer calendar years")


def calendar_shift(frame: pd.DataFrame, column: str, offset: int) -> pd.Series:
    """Value at calendar t+offset; never substitute an adjacent observed row."""
    validate_annual_keys(frame)
    values = frame.set_index(["country_code", "year"])[column]
    keys = pd.MultiIndex.from_arrays(
        [frame["country_code"], frame["year"] + offset],
        names=["country_code", "year"],
    )
    return pd.Series(values.reindex(keys).to_numpy(), index=frame.index)


def check_prerequisites() -> None:
    """Fail on absent/invalid upstream caches before publishing any outputs."""
    required = {
        PROC / "wdi_combined.csv": (
            "Run analysis/download_data.py with the commodity-export indicators",
            {"country_code", "country", "year", "population", "merchandise_exports_current_usd",
             "gdp_current_usd", "gdppc_constant_2015usd", "gross_capital_formation_pct",
             "government_revenue_ex_grants_pct_gdp", "government_expense_pct_gdp",
             "inflation_cpi_pct", *[c[0] for c in CATEGORIES.values()]},
        ),
        RAW / "wb_country_regions.csv": (
            "Run analysis/download_data.py", {"country_code", "region", "income"},
        ),
        PROC / "fragile_state_country_year_panel.csv": (
            "Run analysis/run_analysis_30.py first (WGI governance prerequisite)",
            {"country_code", "year", "government_effectiveness_estimate"},
        ),
        PROC / "growth_incidence_heterogeneity_data.csv": (
            "Run analysis/run_analysis_29.py first (survey-spell prerequisite)",
            {"country_code", "country", "region", "start_year", "end_year",
             "bottom60_capture_pct", "annual_survey_welfare_growth_pct"},
        ),
    }
    problems = []
    if not PRICE_FILE.is_file():
        problems.append(f"Missing {PRICE_FILE}. Cache {PRICE_URL} at that path manually.")
    for path, (instruction, columns) in required.items():
        try:
            frame = pd.read_csv(path)
            missing = columns - set(frame.columns)
            if missing:
                raise ValueError(f"missing columns: {sorted(missing)}")
            if frame.empty:
                raise ValueError("empty input")
            if "year" in columns:
                validate_annual_keys(frame)
            if "government_effectiveness_estimate" in columns:
                gov = pd.to_numeric(frame["government_effectiveness_estimate"], errors="coerce")
                if not np.isfinite(gov).any():
                    raise ValueError("no finite WGI government-effectiveness observations")
        except (OSError, ValueError) as exc:
            problems.append(f"{path}: {exc}. {instruction}.")
    if problems:
        raise RuntimeError("Analysis 33 prerequisites failed; no outputs written:\n" + "\n".join(problems))


def inference_metadata(used: pd.DataFrame) -> dict:
    return {
        "covariance_type": "country_clustered",
        "inference": "country-clustered; country and year fixed effects",
        "reference_distribution": "normal",
        "confidence_level": 0.95,
        "finite_sample_correction": "G/(G-1) * (N-1)/(N-K)",
        "n_year_clusters": used["year"].nunique(),
        "inference_limit": INFERENCE_LIMIT,
    }


def save(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    frame.to_csv(OUTPUT_DIR / name, index=False)
    print(f"  saved {name}: {len(frame):,} rows")
    return frame


def load_prices() -> pd.DataFrame:
    """Parse stable aggregate columns from the official annual Pink Sheet."""
    raw = pd.read_excel(PRICE_FILE, sheet_name="Annual Indices (Nominal)", header=None)
    prices = (
        pd.DataFrame(
            {
                "year": pd.to_numeric(raw.iloc[9:, 0], errors="coerce"),
                "energy_price_index": pd.to_numeric(raw.iloc[9:, 2], errors="coerce"),
                "food_price_index": pd.to_numeric(raw.iloc[9:, 6], errors="coerce"),
                "ag_raw_price_index": pd.to_numeric(raw.iloc[9:, 10], errors="coerce"),
                "metals_price_index": pd.to_numeric(raw.iloc[9:, 14], errors="coerce"),
            }
        )
        .dropna(subset=["year"])
        .copy()
    )
    prices["year"] = prices["year"].astype(int)
    prices = prices.sort_values("year").reset_index(drop=True)
    if prices["year"].duplicated().any():
        raise ValueError("Pink Sheet contains duplicate calendar years")
    for column in [c for c in prices if c.endswith("_index")]:
        if (prices[column].dropna() <= 0).any():
            raise ValueError(f"Pink Sheet {column} must be positive")
        prices[column.replace("_index", "_log_change")] = np.log(prices[column]).diff().where(
            prices["year"].diff().eq(1)
        )
    prices["source"] = (
        "World Bank Commodity Price Data (Pink Sheet), annual nominal indices"
    )
    prices["source_url"] = PRICE_URL
    prices["cache_path"] = str(PRICE_FILE)
    prices["source_sha256"] = hashlib.sha256(PRICE_FILE.read_bytes()).hexdigest()
    prices["source_bytes"] = PRICE_FILE.stat().st_size
    prices["acquisition_status"] = "user-supplied offline cache; acquisition date unverified"
    return save(prices, "commodity_price_indices.csv")


def build_panel(prices: pd.DataFrame) -> pd.DataFrame:
    wdi = pd.read_csv(PROC / "wdi_combined.csv")
    countries = pd.read_csv(RAW / "wb_country_regions.csv")
    countries["region"] = countries["region"].str.strip()
    countries["income"] = countries["income"].str.strip()
    d = wdi.merge(countries, on="country_code", how="inner").merge(
        prices, on="year", how="left"
    )
    d = d.sort_values(["country_code", "year"]).copy()
    validate_annual_keys(d)
    d["merchandise_exports_pct_gdp"] = (
        100 * d["merchandise_exports_current_usd"] / d["gdp_current_usd"]
    )

    category_value_columns = []
    for category, (composition, price) in CATEGORIES.items():
        exposure = f"{category}_export_exposure_gdp"
        d[exposure] = d[composition] / 100 * d["merchandise_exports_pct_gdp"] / 100
        # Predetermined rolling mean t-5:t-3; at least two observations.
        lagged = pd.concat([calendar_shift(d, exposure, -lag) for lag in (3, 4, 5)], axis=1)
        d[f"{exposure}_predetermined"] = lagged.mean(axis=1).where(lagged.count(axis=1).ge(2))
        d[f"{category}_windfall_pct_gdp"] = (
            100
            * d[f"{exposure}_predetermined"]
            * d[price.replace("_index", "_log_change")]
        )
        value_col = f"{category}_exports_usd"
        d[value_col] = d[composition] / 100 * d["merchandise_exports_current_usd"]
        category_value_columns.append(value_col)

    d["commodity_windfall_pct_gdp"] = d[
        [f"{c}_windfall_pct_gdp" for c in CATEGORIES]
    ].sum(axis=1, min_count=len(CATEGORIES))
    d["commodity_export_exposure_gdp"] = d[
        [f"{c}_export_exposure_gdp_predetermined" for c in CATEGORIES]
    ].sum(axis=1, min_count=len(CATEGORIES))

    # Price-taking restriction based on average observed share of world exports.
    annual_totals = d.groupby("year")[category_value_columns].transform("sum")
    supplier_flags = []
    for category in CATEGORIES:
        share = d[f"{category}_exports_usd"] / annual_totals[f"{category}_exports_usd"]
        mean_share = (
            share.where(d["year"].between(1995, 2019))
            .groupby(d["country_code"])
            .transform("mean")
        )
        d[f"{category}_mean_world_export_share"] = mean_share
        supplier_flags.append(mean_share.gt(DOMINANT_EXPORT_SHARE))
    d["dominant_global_supplier"] = pd.concat(supplier_flags, axis=1).any(axis=1)
    d["price_taker_sample"] = ~d["dominant_global_supplier"]

    d["log_gdppc"] = np.log(
        d["gdppc_constant_2015usd"].where(d["gdppc_constant_2015usd"] > 0)
    )
    d["gdppc_growth_pct"] = 100 * (d["log_gdppc"] - calendar_shift(d, "log_gdppc", -1))
    d["investment"] = d["gross_capital_formation_pct"]
    d["government_revenue"] = d["government_revenue_ex_grants_pct_gdp"]
    d["government_expense"] = d["government_expense_pct_gdp"]
    d["inflation"] = d["inflation_cpi_pct"]
    d["shock_lead1"] = calendar_shift(d, "commodity_windfall_pct_gdp", 1)
    d["shock_lag1"] = calendar_shift(d, "commodity_windfall_pct_gdp", -1)

    # Pre-shock governance is a moderator, not an assigned treatment.
    fragile_path = PROC / "fragile_state_country_year_panel.csv"
    gov = pd.read_csv(
        fragile_path,
        usecols=["country_code", "year", "government_effectiveness_estimate"],
    )
    # Shift lookup keys, not observations: WGI historically has biennial gaps.
    validate_annual_keys(gov)
    gov["year"] = gov["year"] + 3
    gov = gov.rename(columns={"government_effectiveness_estimate": "governance_predetermined"})
    d = d.merge(
        gov, on=["country_code", "year"], how="left", validate="one_to_one",
    )

    keep = [
        "country_code",
        "country",
        "region",
        "income",
        "year",
        "population",
        "commodity_windfall_pct_gdp",
        "commodity_export_exposure_gdp",
        "price_taker_sample",
        "dominant_global_supplier",
        "governance_predetermined",
        "log_gdppc",
        "gdppc_growth_pct",
        "investment",
        "government_revenue",
        "government_expense",
        "inflation",
        "shock_lead1",
        "shock_lag1",
    ]
    keep += [f"{c}_windfall_pct_gdp" for c in CATEGORIES]
    keep += [f"{c}_export_exposure_gdp_predetermined" for c in CATEGORIES]
    return save(d[keep], "commodity_windfall_country_year.csv")


def fit_fe(
    data: pd.DataFrame,
    outcome: str,
    shock: str = "commodity_windfall_pct_gdp",
    interaction: str | None = None,
) -> tuple[RegressionResultsWrapper, pd.DataFrame]:
    columns = ["country_code", "year", outcome, shock, "shock_lag1"]
    rhs = f"{shock} + shock_lag1"
    if interaction:
        columns.append(interaction)
        rhs = f"{shock} * {interaction} + shock_lag1"
    model_data = data[columns].dropna().copy()
    formula = f"{outcome} ~ {rhs} + C(country_code) + C(year)"
    model = smf.ols(formula, data=model_data).fit(
        cov_type="cluster", cov_kwds={"groups": model_data["country_code"], "use_correction": True},
        use_t=False,
    )
    return model, model_data


def two_way_sensitivity(model: RegressionResultsWrapper, used: pd.DataFrame) -> dict:
    """Same OLS/sample; actual two-way sandwich, not merely year fixed effects."""
    countries = pd.factorize(used["country_code"])[0]
    years = pd.factorize(used["year"])[0]
    df = min(used["country_code"].nunique(), used["year"].nunique()) - 1
    if df < 1:
        raise ValueError("Two-way covariance requires at least two countries and years")
    covariance, country_cov, year_cov = cov_cluster_2groups(
        model, countries, years, use_correction=True,
    )
    shock = model.model.exog_names.index("commodity_windfall_pct_gdp")
    lag = model.model.exog_names.index("shock_lag1")
    variance = covariance[shock, shock]
    estimate = float(model.params.iloc[shock])
    valid = np.isfinite(variance) and variance > 0
    se = np.sqrt(variance) if valid else np.nan
    critical = student_t.ppf(0.975, df)
    return {
        "estimate": estimate,
        "std_error": se,
        "ci_low": estimate - critical * se,
        "ci_high": estimate + critical * se,
        "p_value": 2 * student_t.sf(abs(estimate / se), df) if valid else np.nan,
        "covariance_type": "country_year_two_way_clustered",
        "inference": "sensitivity only; country and year fixed effects; country/year two-way clustering",
        "reference_distribution": "Student t",
        "reference_df": df,
        "confidence_level": 0.95,
        "finite_sample_correction": "componentwise G/(G-1) * (N-1)/(N-K), including intersection",
        "covariance_shock_shock": variance,
        "covariance_shock_lag1": covariance[shock, lag],
        "covariance_lag1_lag1": covariance[lag, lag],
        "country_component_shock_variance": country_cov[shock, shock],
        "year_component_shock_variance": year_cov[shock, shock],
        "intersection_component_shock_variance": country_cov[shock, shock] + year_cov[shock, shock] - variance,
        "n_country_years": int(model.nobs),
        "n_countries": used["country_code"].nunique(),
        "n_year_clusters": used["year"].nunique(),
        "n_intersection_clusters": used[["country_code", "year"]].drop_duplicates().shape[0],
        "inference_status": "ok_sensitivity_only" if valid else "nonpositive_or_nonfinite_variance_no_interval",
        "inference_limit": INFERENCE_LIMIT,
    }


def add_horizon_outcomes(panel: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Construct impact-year/cumulative outcomes on the unfiltered annual panel.

    Horizon zero is the impact year: GDP is log(y_t)-log(y_{t-1}) and level
    outcomes are x_t-x_{t-1}. Horizon h uses y_{t+h}-y_{t-1}. Exact calendar
    lookups require both endpoints, not intervening GDP/level observations.
    Inflation requires every annual observation from t-1 through t+h.
    """
    if not isinstance(horizon, (int, np.integer)) or horizon < 0:
        raise ValueError("horizon must be a nonnegative integer")
    d = panel.copy()
    before_log = calendar_shift(d, "log_gdppc", -1)
    future_log = calendar_shift(d, "log_gdppc", horizon)
    d["lp_gdppc"] = 100 * (future_log - before_log)
    for source, target in [
        ("investment", "lp_investment"),
        ("government_revenue", "lp_government_revenue"),
        ("government_expense", "lp_government_expense"),
    ]:
        d[target] = calendar_shift(d, source, horizon) - calendar_shift(d, source, -1)
    # Mean inflation over t..t+h, minus inflation at t-1.
    forward = pd.concat(
        [calendar_shift(d, "inflation", j) for j in range(horizon + 1)], axis=1,
    ).mean(axis=1, skipna=False)
    d["lp_inflation"] = forward - calendar_shift(d, "inflation", -1)
    return d


def local_projections(panel: pd.DataFrame) -> pd.DataFrame:
    sample = (
        panel["year"].between(1990, 2023)
        & panel["price_taker_sample"]
        & panel["commodity_export_exposure_gdp"].gt(0.005)
    )
    base = panel[sample].copy()
    lower, upper = base["commodity_windfall_pct_gdp"].quantile([0.01, 0.99])
    trim = panel["commodity_windfall_pct_gdp"].between(lower, upper)
    rows = []
    sensitivity_rows = []
    for horizon in range(0, 6):
        # Outcomes must be shifted before sample filtering; otherwise a year
        # with missing exposure can be mistaken for the adjacent year.
        d = add_horizon_outcomes(panel, horizon)[sample & trim].copy()
        for outcome_key in OUTCOMES:
            target = f"lp_{outcome_key}"
            try:
                model, used = fit_fe(d, target)
                term = "commodity_windfall_pct_gdp"
                rows.append(
                    {
                        "outcome": outcome_key,
                        "outcome_label": OUTCOMES[outcome_key],
                        "horizon": horizon,
                        "estimate": model.params[term],
                        "std_error": model.bse[term],
                        "ci_low": model.conf_int().loc[term, 0],
                        "ci_high": model.conf_int().loc[term, 1],
                        "p_value": model.pvalues[term],
                        "n_country_years": int(model.nobs),
                        "n_countries": used["country_code"].nunique(),
                        "shock_unit": "one-percentage-point-of-GDP commodity windfall",
                        **inference_metadata(used),
                        "outcome_window": (
                            "mean inflation t..t+h minus t-1; complete annual window required"
                            if outcome_key == "inflation" else
                            "h=0 is impact year t versus t-1; h uses exact t+h versus t-1 endpoints"
                        ),
                    }
                )
                if outcome_key in {"gdppc", "government_revenue", "investment"}:
                    sensitivity_rows.append({**rows[-1], **two_way_sensitivity(model, used)})
            except (ValueError, np.linalg.LinAlgError) as exc:
                raise RuntimeError(f"Local projection failed: {outcome_key} h={horizon}") from exc
    save(pd.DataFrame(sensitivity_rows), "commodity_windfall_two_way_sensitivity.csv")
    return save(pd.DataFrame(rows), "commodity_windfall_local_projections.csv")


def category_estimates(panel: pd.DataFrame) -> pd.DataFrame:
    """Report impact-year estimates separately by commodity category."""
    d = add_horizon_outcomes(panel, 0)
    for category in CATEGORIES:
        shock = f"{category}_windfall_pct_gdp"
        d[f"{shock}_lag1"] = calendar_shift(d, shock, -1)
    d = d[
        d["price_taker_sample"]
        & d["year"].between(1990, 2023)
        & d["commodity_export_exposure_gdp"].gt(0.005)
    ].copy()
    rows = []
    for category in CATEGORIES:
        shock = f"{category}_windfall_pct_gdp"
        model_data = d[
            [
                "country_code",
                "year",
                "lp_gdppc",
                "lp_government_revenue",
                shock,
                f"{shock}_lag1",
            ]
        ].copy()
        for outcome in ["lp_gdppc", "lp_government_revenue"]:
            used = model_data.dropna(subset=[outcome, shock, f"{shock}_lag1"])
            model = smf.ols(
                f"{outcome} ~ {shock} + {shock}_lag1 + C(country_code) + C(year)",
                data=used,
            ).fit(cov_type="cluster", cov_kwds={"groups": used["country_code"], "use_correction": True}, use_t=False)
            rows.append(
                {
                    "category": category,
                    "outcome": outcome,
                    "estimate": model.params[shock],
                    "std_error": model.bse[shock],
                    "ci_low": model.conf_int().loc[shock, 0],
                    "ci_high": model.conf_int().loc[shock, 1],
                    "p_value": model.pvalues[shock],
                    "n_country_years": int(model.nobs),
                    "n_countries": used.country_code.nunique(),
                    **inference_metadata(used),
                    "multiple_testing_note": "exploratory category decomposition; no multiplicity adjustment",
                }
            )
    return save(pd.DataFrame(rows), "commodity_windfall_category_estimates.csv")


def year_influence(panel: pd.DataFrame) -> pd.DataFrame:
    """Leave out each global price year to expose dependence on a few shocks."""
    d = add_horizon_outcomes(panel, 0)
    d = d[
        d["price_taker_sample"]
        & d["year"].between(1990, 2023)
        & d["commodity_export_exposure_gdp"].gt(0.005)
    ].copy()
    q = d["commodity_windfall_pct_gdp"].quantile([0.01, 0.99])
    d = d[d["commodity_windfall_pct_gdp"].between(q.iloc[0], q.iloc[1])]
    rows = []
    for omitted_year in sorted(d.year.unique()):
        subset = d[d.year.ne(omitted_year)]
        for outcome in ["lp_gdppc", "lp_government_revenue"]:
            model, used = fit_fe(subset, outcome)
            term = "commodity_windfall_pct_gdp"
            rows.append(
                {
                    "omitted_price_year": int(omitted_year),
                    "outcome": outcome,
                    "estimate": model.params[term],
                    "std_error": model.bse[term],
                    "ci_low": model.conf_int().loc[term, 0],
                    "ci_high": model.conf_int().loc[term, 1],
                    "p_value": model.pvalues[term],
                    "n_country_years": int(model.nobs),
                    "n_countries": used.country_code.nunique(),
                    **inference_metadata(used),
                }
            )
    return save(pd.DataFrame(rows), "commodity_windfall_year_influence.csv")


def diagnostics(panel: pd.DataFrame) -> pd.DataFrame:
    eligible = panel[panel.year.between(1990, 2023)].copy()
    main = eligible[
        eligible.price_taker_sample & eligible.commodity_export_exposure_gdp.gt(0.005)
    ]
    q = main.commodity_windfall_pct_gdp.quantile([0.01, 0.99])
    rows = [
        ("country_years_1990_2023", len(eligible), "all real countries in WDI lookup"),
        (
            "nonmissing_composite_shock",
            eligible.commodity_windfall_pct_gdp.notna().sum(),
            "requires all four category exposures; missing is not treated as zero",
        ),
        (
            "price_taker_exposed_country_years",
            len(main),
            "supplier <=3% and exposure >0.5% GDP",
        ),
        ("trimmed_low_cutoff_pct_gdp", q.iloc[0], "1st percentile"),
        ("trimmed_high_cutoff_pct_gdp", q.iloc[1], "99th percentile"),
        (
            "trimmed_country_years",
            main.commodity_windfall_pct_gdp.between(q.iloc[0], q.iloc[1]).sum(),
            "main local-projection shock sample before outcome missingness",
        ),
    ]
    return save(
        pd.DataFrame(rows, columns=["diagnostic", "value", "definition"]),
        "commodity_windfall_diagnostics.csv",
    )


def robustness(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    samples = {
        "main_price_takers_trimmed": panel[panel["price_taker_sample"]].copy(),
        "all_exporters": panel.copy(),
        "price_takers_2000_2019": panel[
            panel["price_taker_sample"] & panel["year"].between(2000, 2019)
        ].copy(),
        "price_takers_exposure_ge_2pct": panel[
            panel["price_taker_sample"]
            & panel["commodity_export_exposure_gdp"].ge(0.02)
        ].copy(),
    }
    for sample, d in samples.items():
        d = d[
            d["year"].between(1990, 2023) & d["commodity_export_exposure_gdp"].gt(0.005)
        ].copy()
        if "trimmed" in sample:
            q = d["commodity_windfall_pct_gdp"].quantile([0.01, 0.99])
            d = d[d["commodity_windfall_pct_gdp"].between(q.iloc[0], q.iloc[1])]
        for outcome in [
            "gdppc_growth_pct",
            "investment",
            "government_revenue",
            "inflation",
        ]:
            model, used = fit_fe(d, outcome)
            term = "commodity_windfall_pct_gdp"
            rows.append(
                {
                    "sample": sample,
                    "outcome": outcome,
                    "estimate": model.params[term],
                    "std_error": model.bse[term],
                    "ci_low": model.conf_int().loc[term, 0],
                    "ci_high": model.conf_int().loc[term, 1],
                    "p_value": model.pvalues[term],
                    "n_country_years": int(model.nobs),
                    "n_countries": used.country_code.nunique(),
                    **inference_metadata(used),
                }
            )
        # Lead-placebo: next year's shock should not predict current growth.
        model, used = fit_fe(
            d.rename(columns={"commodity_windfall_pct_gdp": "actual_shock"}),
            "gdppc_growth_pct",
            shock="shock_lead1",
        )
        term = "shock_lead1"
        rows.append(
            {
                "sample": sample,
                "outcome": "gdppc_growth_lead_placebo",
                "estimate": model.params[term],
                "std_error": model.bse[term],
                "ci_low": model.conf_int().loc[term, 0],
                "ci_high": model.conf_int().loc[term, 1],
                "p_value": model.pvalues[term],
                "n_country_years": int(model.nobs),
                "n_countries": used.country_code.nunique(),
                **inference_metadata(used),
            }
        )
    return save(pd.DataFrame(rows), "commodity_windfall_robustness.csv")


def governance_heterogeneity(panel: pd.DataFrame) -> pd.DataFrame:
    d = panel[
        panel["price_taker_sample"]
        & panel["year"].between(1996, 2023)
        & panel["commodity_export_exposure_gdp"].gt(0.005)
    ].copy()
    d["governance_z"] = (
        d["governance_predetermined"] - d["governance_predetermined"].mean()
    ) / d["governance_predetermined"].std()
    rows = []
    for outcome in [
        "gdppc_growth_pct",
        "investment",
        "government_revenue",
        "government_expense",
    ]:
        model, used = fit_fe(d, outcome, interaction="governance_z")
        for term in [
            "commodity_windfall_pct_gdp",
            "commodity_windfall_pct_gdp:governance_z",
        ]:
            rows.append(
                {
                    "outcome": outcome,
                    "term": term,
                    "estimate": model.params[term],
                    "std_error": model.bse[term],
                    "ci_low": model.conf_int().loc[term, 0],
                    "ci_high": model.conf_int().loc[term, 1],
                    "p_value": model.pvalues[term],
                    "n_country_years": int(model.nobs),
                    "n_countries": used.country_code.nunique(),
                    **inference_metadata(used),
                    "interpretation_limit": "WGI governance is a predetermined moderator, not randomized",
                }
            )
    return save(pd.DataFrame(rows), "commodity_windfall_governance.csv")


def growth_incidence(panel: pd.DataFrame) -> pd.DataFrame:
    path = PROC / "growth_incidence_heterogeneity_data.csv"
    if not path.exists():
        raise RuntimeError(f"Missing {path}; run analysis/run_analysis_29.py first")
    spells = pd.read_csv(path)
    shocks = panel[["country_code", "year", "commodity_windfall_pct_gdp"]].dropna()
    rows = []
    for row in spells.itertuples(index=False):
        window = shocks[
            (shocks.country_code == row.country_code)
            & shocks.year.between(row.start_year, row.end_year)
        ]
        rows.append(
            {
                "country_code": row.country_code,
                "country": row.country,
                "region": row.region,
                "start_year": row.start_year,
                "end_year": row.end_year,
                "bottom60_capture_pct": row.bottom60_capture_pct,
                "annual_survey_welfare_growth_pct": row.annual_survey_welfare_growth_pct,
                "average_windfall_pct_gdp": window.commodity_windfall_pct_gdp.mean(),
                "shock_years_observed": len(window),
            }
        )
    result = pd.DataFrame(rows)
    usable = result.dropna().query("shock_years_observed >= 2")
    if len(usable) >= 30:
        model = smf.ols(
            "bottom60_capture_pct ~ average_windfall_pct_gdp + "
            "annual_survey_welfare_growth_pct + C(region) + C(start_year)",
            data=usable,
        ).fit(cov_type="cluster", cov_kwds={"groups": usable["country_code"], "use_correction": True}, use_t=False)
        result["pooled_capture_association"] = model.params.get(
            "average_windfall_pct_gdp"
        )
        result["pooled_capture_p_value"] = model.pvalues.get("average_windfall_pct_gdp")
        result["model_n"] = int(model.nobs)
        result["model_n_countries"] = usable["country_code"].nunique()
        result["inference_status"] = "estimated_exploratory_association"
    else:
        result["inference_status"] = "skipped_fewer_than_30_complete_spells"
    result["covariance_type"] = "country_clustered"
    result["inference"] = "country-clustered; region and spell-start-year fixed effects, not country fixed effects"
    result["reference_distribution"] = "normal"
    result["finite_sample_correction"] = "G/(G-1) * (N-1)/(N-K)"
    result["interpretation_limit"] = (
        "sparse survey-spell association; not a causal incidence estimate"
    )
    return save(result, "commodity_windfall_growth_incidence.csv")


def method_limits(panel: pd.DataFrame) -> pd.DataFrame:
    dominant = sorted(
        panel.loc[panel.dominant_global_supplier, "country"].dropna().unique()
    )
    rows = [
        (
            "assignment",
            "Global price changes interacted with export composition measured t-5 to t-3.",
            "Supports differential-exposure interpretation conditional on fixed effects; specialization itself is not random.",
        ),
        (
            "price_setting",
            f"Main sample excludes average suppliers above {100*DOMINANT_EXPORT_SHARE:.0f}% of observed world exports in any category: "
            + ", ".join(dominant),
            "Reduces but cannot prove absence of influence on prices.",
        ),
        (
            "exclusion_restriction",
            "Commodity prices affect exporters through income, fiscal, exchange-rate, investment, inflation, and political channels.",
            "The shock is not a valid investment instrument without further restrictions.",
        ),
        (
            "common_shocks",
            "Central regressions: country/year fixed effects, country-clustered covariance, normal-reference 95% CIs. "
            "Separate GDP/revenue/investment h=0..5 sensitivity: country + year - intersection covariance, "
            "componentwise finite-sample correction, t(min(country,year clusters)-1) 95% CIs. "
            "Survey-spell incidence instead uses region/start-year fixed effects and country clustering.",
            INFERENCE_LIMIT,
        ),
        (
            "offline_prerequisites",
            "Run analysis29 for survey spells and analysis30 for WGI governance; WDI export indicators "
            "and country lookup must also be cached. Preflight rejects missing inputs before any output writes.",
            "No network acquisition is performed by analysis33.",
        ),
        (
            "pink_sheet_provenance",
            f"Source URL: {PRICE_URL}; cache: {PRICE_FILE}; "
            f"SHA-256: {hashlib.sha256(PRICE_FILE.read_bytes()).hexdigest()}",
            "Hash identifies local workbook bytes only; original acquisition date and release are unverified. "
            "Price-index output records source URL, SHA-256 and byte count.",
        ),
        (
            "calendar_alignment",
            "All lags/leads use calendar-year keys: exposure t-5..t-3 requires >=2 observations; "
            "governance is exactly t-3. LP endpoints are t-1 and t+h, before sample filtering; "
            "inflation requires all years t-1..t+h.",
            "Missing rows never stand in for adjacent calendar years; duplicate country/year keys are rejected.",
        ),
        (
            "anticipation",
            "Predetermined shares avoid contemporaneous quantity response; a one-year lead placebo is reported.",
            "Futures markets and investment before annual price changes can still create anticipation.",
        ),
        (
            "governance",
            "Government effectiveness is lagged three years and used only as a moderator.",
            "Its interaction is descriptive heterogeneity, not the causal effect of institutions.",
        ),
        (
            "poverty_incidence",
            "PIP survey spells are sparse and asynchronous with annual shocks.",
            "Any bottom-60 association is exploratory and cannot identify distributional causality.",
        ),
    ]
    return save(
        pd.DataFrame(
            rows, columns=["issue", "implementation", "identification_conclusion"]
        ),
        "commodity_windfall_method_limits.csv",
    )


def make_charts(lp: pd.DataFrame, governance: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True)
    for ax, outcome in zip(axes, ["gdppc", "investment", "government_revenue"]):
        d = lp[lp.outcome == outcome]
        ax.axhline(0, color="black", lw=0.8)
        ax.fill_between(d.horizon, d.ci_low, d.ci_high, alpha=0.2)
        ax.plot(d.horizon, d.estimate, marker="o")
        ax.set_title(OUTCOMES[outcome])
        ax.set_xlabel("Years after price shock")
        ax.set_ylabel("Response to 1 pp-of-GDP windfall")
    fig.suptitle(
        "Commodity windfall local projections\n"
        "Country/year FE; central country-clustered normal 95% CIs\n"
        "Few common shocks limit inference; see separate two-way sensitivity",
        y=1.04,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(CHARTS / "139_commodity_windfall_local_projections.png")
    plt.close(fig)

    interactions = governance[governance.term.str.contains(":")].copy()
    governance_labels = {
        "gdppc_growth_pct": "Real GDP per-capita growth",
        "investment": "Investment share of GDP",
        "government_revenue": "Government revenue share of GDP",
        "government_expense": "Government expense share of GDP",
    }
    interactions["label"] = interactions.outcome.map(governance_labels)
    fig, ax = plt.subplots(figsize=(10, 5))
    y = np.arange(len(interactions))
    ax.axvline(0, color="black", lw=0.8)
    ax.errorbar(
        interactions.estimate,
        y,
        xerr=[
            interactions.estimate - interactions.ci_low,
            interactions.ci_high - interactions.estimate,
        ],
        fmt="o",
        capsize=3,
    )
    ax.set_yticks(y, interactions.label)
    ax.set_xlabel(
        "Change in windfall coefficient per 1 SD higher lagged government effectiveness"
    )
    ax.set_title(
        "Institutional heterogeneity is imprecisely identified\nPredetermined WGI moderator; country-clustered normal 95% CIs"
    )
    fig.savefig(CHARTS / "140_commodity_windfall_governance.png")
    plt.close(fig)


def main() -> None:
    print("Analysis 33: commodity windfalls")
    check_prerequisites()
    prices = load_prices()
    panel = build_panel(prices)
    lp = local_projections(panel)
    robust = robustness(panel)
    governance = governance_heterogeneity(panel)
    incidence = growth_incidence(panel)
    category_estimates(panel)
    influence = year_influence(panel)
    diagnostics(panel)
    method_limits(panel)
    make_charts(lp, governance)
    print("\nCentral estimates (horizon 0; country-clustered, normal 95% CIs):")
    print(
        lp[lp.horizon.eq(0)][
            [
                "outcome",
                "estimate",
                "ci_low",
                "ci_high",
                "p_value",
                "n_country_years",
                "n_countries",
            ]
        ].to_string(index=False)
    )
    print("\nLead placebo:")
    print(robust[robust.outcome.eq("gdppc_growth_lead_placebo")].to_string(index=False))
    if not incidence.empty and "pooled_capture_association" in incidence:
        print(
            "\nExploratory bottom-60 capture association:",
            incidence.pooled_capture_association.dropna().head(1).tolist(),
        )
    print("\nLeave-one-price-year estimate ranges:")
    print(influence.groupby("outcome").estimate.agg(["min", "max"]).to_string())
    print("\nCountry/year two-way sensitivity (same headline OLS coefficients):")
    sensitivity = pd.read_csv(OUTPUT_DIR / "commodity_windfall_two_way_sensitivity.csv")
    print(sensitivity[["outcome", "horizon", "estimate", "std_error", "ci_low", "ci_high",
                       "p_value", "n_countries", "n_year_clusters", "reference_df"]].to_string(index=False))
    print(INFERENCE_LIMIT)


if __name__ == "__main__":
    main()
