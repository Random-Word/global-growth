#!/usr/bin/env python3
"""Analysis 21: "Weightless growth" falsification test.

The report argues a good life is achievable within planetary boundaries. An open
question (flagged in critique) is whether the good-life OUTCOME bundle saturates
with respect to MATERIAL FOOTPRINT per capita the way it does with respect to GDP
per capita.

Logic:
- If outcomes saturate (reliably cross good_life_score >= 0.80) at a material
  footprint at or below the per-capita sustainable boundary (~6-8 t/cap/yr), the
  "good life within boundaries" claim is empirically supported.
- If good outcomes only appear far above that boundary, the claim depends on
  either (a) future dematerialization or (b) rich countries offshoring their
  material footprint (consumption-based accounting).

Sustainable boundary: the ecological / decoupling literature puts a per-capita
"safe operating space" material footprint at roughly 6-8 t/cap/yr (approximate;
e.g. Bringezu's safe operating space ~6-8 t/cap). We do not overstate precision
and mark 8 t/cap as the (generous) reference line.

Offshoring / accounting caveat (verified from OWID metadata, printed below):
- MATERIAL FOOTPRINT (MF / RMC, SDG 12.2.1) = raw-material-equivalents of final
  demand = CONSUMPTION-BASED: imported materials are attributed to the consuming
  country, so offshoring is netted IN. BUT OWID's `material-footprint-per-capita`
  grapher now only exposes the WORLD aggregate (no per-country rows), so a
  per-country consumption-based comparison is not possible from this source.
- The country-level series we can use is DOMESTIC MATERIAL CONSUMPTION per capita
  (DMC, SDG 12.2.2) = domestic extraction + physical imports - physical exports,
  counted at DIRECT physical weight => PRODUCTION / TERRITORIAL-based apparent
  consumption. DMC does NOT net offshoring out (upstream extraction embedded in
  imported manufactured goods is excluded).

BASIS MISMATCH (critical): the ~8 t/cap boundary comes from MF-basis literature,
but the per-country predictor here is DMC. These are DIFFERENT accounting bases, so
every DMC-vs-8 t/cap comparison below is a "DMC vs MF-origin boundary (basis
mismatch)" comparison, not a like-for-like test.

BIAS DIRECTION IS NOT UNIVERSAL:
- DMC UNDERSTATES rich, import-dependent economies' true consumption footprint
  (upstream extraction embedded in imported manufactured goods is missing).
- DMC can OVERSTATE resource/manufacturing EXPORTERS relative to consumption-based
  MF (extraction/processing for exports is counted territorially but consumed
  abroad). So the sign of (DMC - MF) is country-specific, not one-directional.
- NET EFFECT: the NEGATIVE finding ("good outcomes are not TYPICAL at <=8 t/cap")
  is CONSERVATIVE, because rich high-outcome economies' true MF is generally higher
  than their DMC. The POSITIVE existence-proof cases (high outcome at <=8 t/cap DMC)
  are NOT proven on a true MF basis: some may be exporters whose MF is lower, but
  others could have higher MF once imports' upstream extraction is counted.

Outputs:
- charts/104_weightless_growth_saturation.png
- charts/105_good_life_vs_material_boundary.png
- data/processed/weightless_growth_saturation.csv
- data/processed/weightless_growth_existence_proofs.csv
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
from scipy.optimize import curve_fit

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

OWID_BASE = "https://ourworldindata.org/grapher/"
MATERIAL_BOUNDARY_TPC = 8.0  # generous upper end of ~6-8 t/cap sustainable range
SCORE_TARGETS = (0.80, 0.85)


def fetch_owid_grapher(slug: str, label: str) -> pd.DataFrame:
    """Download a CSV from OWID grapher (same pattern as run_analysis_7)."""
    url = f"{OWID_BASE}{slug}.csv?v=1&csvType=full&useColumnShortNames=false"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    print(f"  {label}: {df.shape[0]} rows, {df.shape[1]} cols")
    return df


def load_cached_grapher(slug: str, cache_name: str, label: str) -> pd.DataFrame:
    """Fetch an OWID grapher CSV, caching to data/raw for offline reruns."""
    cache = RAW / cache_name
    if cache.exists():
        print(f"  Using cached {cache.name}")
        return pd.read_csv(cache)
    print(f"Downloading {slug} from OWID...")
    df = fetch_owid_grapher(slug, label)
    df.to_csv(cache, index=False)
    print(f"  Cached -> {cache.name}")
    return df


def get_value_col(df: pd.DataFrame) -> str:
    skip = {"Entity", "Code", "Year", "Day"}
    return next(c for c in df.columns if c not in skip)


# ── Saturating fit: score ~ a*log(x)+b, clipped to [0,1] for display ──────────
def log_fit(x: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * np.log(x) + b


def fit_log_curve(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    popt, _ = curve_fit(log_fit, x, y, p0=[0.1, 0.0], maxfev=10000)
    return float(popt[0]), float(popt[1])


def crossing_x(a: float, b: float, target: float) -> float:
    if a <= 0:
        return np.nan
    return float(np.exp((target - b) / a))


# ── Robustness fit: logistic on log(x) (saturating, bounded in [0, L]) ────────
def logistic_logx(x: np.ndarray, k: float, x0: float, L: float = 1.0) -> np.ndarray:
    return L / (1.0 + np.exp(-k * (np.log(x) - x0)))


def fit_logistic_logx(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    popt, _ = curve_fit(
        lambda xx, k, x0: logistic_logx(xx, k, x0),
        x,
        y,
        p0=[1.0, float(np.log(np.median(x)))],
        maxfev=20000,
    )
    return float(popt[0]), float(popt[1])


def logistic_crossing(k: float, x0: float, target: float, L: float = 1.0) -> float:
    if target <= 0 or target >= L or k == 0:
        return np.nan
    val = L / target - 1.0
    if val <= 0:
        return np.nan
    return float(np.exp(x0 - np.log(val) / k))


# ── Binned reliability cross-check (mirrors run_analysis_19 logic) ────────────
def bin_reliability(
    data: pd.DataFrame,
    value_col: str,
    bins: list[float],
    labels: list[str],
    estimand: str,
    pop_col: str = "population",
) -> pd.DataFrame:
    """Per-bin reliability. Reports BOTH the unweighted share of country-years
    scoring >= target and the POPULATION-WEIGHTED share (people, not units).
    `estimand` labels what the rows describe, e.g. 'all_country_years' vs
    'latest_year_per_country'."""
    d = data.dropna(subset=[value_col, "good_life_score"]).copy()
    if pop_col not in d.columns:
        pop_col = "analysis_population"
    d["bin"] = pd.cut(d[value_col], bins=bins, labels=labels, right=False)
    rows: list[dict[str, object]] = []
    for label in labels:
        sub = d[d["bin"] == label]
        if len(sub) == 0:
            continue
        w = sub[pop_col].fillna(0.0)
        w_sum = float(w.sum())
        if w_sum > 0:
            pw80 = float((w * (sub["good_life_score"] >= 0.80)).sum() / w_sum)
            pw85 = float((w * (sub["good_life_score"] >= 0.85)).sum() / w_sum)
        else:
            pw80 = pw85 = np.nan
        rows.append(
            {
                "predictor": value_col,
                "estimand": estimand,
                "bin": label,
                "n_countries": int(sub["country_code"].nunique()),
                "n_country_years": int(len(sub)),
                "median_score": float(sub["good_life_score"].median()),
                "share_score_80": float((sub["good_life_score"] >= 0.80).mean()),
                "share_score_85": float((sub["good_life_score"] >= 0.85).mean()),
                "pop_weighted_share_score_80": pw80,
                "pop_weighted_share_score_85": pw85,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    # ── Load good-life panel ──────────────────────────────────────────────────
    panel = pd.read_csv(PROC / "good_life_v2_country_year_panel.csv")
    panel = panel[
        panel["good_life_score"].notna()
        & (panel["good_life_indicators_available"] >= 8)
    ].copy()
    print(f"Good-life panel: {len(panel)} country-years")

    # ── Material footprint (MF, consumption-based) is World-only in OWID now ───
    mf_world = load_cached_grapher(
        "material-footprint-per-capita",
        "owid_material_footprint_per_capita.csv",
        "Material footprint/cap (World)",
    )
    n_codes = mf_world["Code"].dropna().nunique()
    if n_codes <= 1:
        print(
            f"  NOTE: material-footprint-per-capita has {n_codes} ISO code(s) "
            "(World aggregate only) -> no per-country consumption-based series."
        )
        mf_latest = mf_world.sort_values("Year").iloc[-1]
        print(
            f"  World MF/cap (consumption-based) {int(mf_latest['Year'])}: "
            f"{mf_latest[get_value_col(mf_world)]:.1f} t/cap"
        )

    # ── Country-level predictor: domestic material consumption per capita ─────
    mat = load_cached_grapher(
        "domestic-material-consumption-per-capita",
        "owid_dmc_per_capita.csv",
        "DMC/cap (by country)",
    )
    mat_val = get_value_col(mat)
    print(f"  DMC value column: '{mat_val}'")
    print(
        "  Series accounting basis: DOMESTIC MATERIAL CONSUMPTION (SDG 12.2.2) =\n"
        "  PRODUCTION / TERRITORIAL-based apparent consumption (direct trade weight).\n"
        "  Offshoring is NOT netted out; DMC understates import-heavy economies' true\n"
        "  consumption-based material footprint."
    )
    mat = mat.rename(
        columns={"Code": "country_code", "Year": "year", mat_val: "mat_fp_pc"}
    )
    mat = mat[["country_code", "year", "mat_fp_pc"]].dropna(subset=["country_code"])
    # Drop non-positive DMC (reporting gaps, e.g. 0.0 t/cap) -- not real low footprints
    nonpos = mat[mat["mat_fp_pc"] <= 0]
    if len(nonpos):
        excl_codes = sorted(nonpos["country_code"].unique())
        print(
            f"  Excluding {len(nonpos)} country-year(s) with non-positive DMC "
            f"(reporting gaps, treated as missing): "
            f"{len(excl_codes)} ISO code(s) -> {', '.join(excl_codes)}"
        )
    else:
        print("  No non-positive DMC country-years to exclude.")
    mat = mat[mat["mat_fp_pc"] > 0]

    panel = panel.merge(mat, on=["country_code", "year"], how="left")

    # Trend-context panel: both predictors + score present
    both = panel[
        panel["gdppc_ppp_current"].notna()
        & panel["mat_fp_pc"].notna()
        & panel["good_life_score"].notna()
    ].copy()
    if both.empty:
        raise RuntimeError(
            "No country-years with score + GDP/cap + DMC; check merge keys."
        )
    print(
        f"  Country-years with score + GDP/cap + DMC/cap: {len(both)} "
        f"({both['country_code'].nunique()} countries, "
        f"{int(both['year'].min())}-{int(both['year'].max())})"
    )

    # Latest year per country where both predictors available
    latest = both.sort_values("year").drop_duplicates("country_code", keep="last")
    print(f"  Latest-year cross-section: {len(latest)} countries")

    # ── B. Saturation fits + crossing thresholds ─────────────────────────────
    predictors = {
        "gdppc_ppp_current": ("GDP per capita (PPP, current intl $)", latest),
        "mat_fp_pc": (
            "Domestic material consumption per capita (DMC, territorial, t/cap)",
            latest,
        ),
    }
    fit_results: dict[str, tuple[float, float]] = {}
    logistic_results: dict[str, tuple[float, float]] = {}
    crossing_rows: list[dict[str, object]] = []
    for col, (label, df) in predictors.items():
        sub = df.dropna(subset=[col, "good_life_score"])
        sub = sub[sub[col] > 0]
        a, b = fit_log_curve(sub[col].to_numpy(), sub["good_life_score"].to_numpy())
        fit_results[col] = (a, b)
        for target in SCORE_TARGETS:
            x_cross = crossing_x(a, b, target)
            crossing_rows.append(
                {
                    "predictor": col,
                    "predictor_label": label,
                    "fit_form": "log",
                    "fit_a": a,
                    "fit_b": b,
                    "score_target": target,
                    "x_crossing": x_cross,
                    "n_countries": int(sub["country_code"].nunique()),
                }
            )
            print(f"  [{col}] log fit: score={target:.2f} crossing at x={x_cross:,.1f}")

    # Robustness: logistic-on-log(x) fit for the DMC predictor (is the ~18 t/cap
    # crossing form-dependent?). A second functional form bounded in [0, 1].
    dmc = latest.dropna(subset=["mat_fp_pc", "good_life_score"])
    dmc = dmc[dmc["mat_fp_pc"] > 0]
    k, x0 = fit_logistic_logx(
        dmc["mat_fp_pc"].to_numpy(), dmc["good_life_score"].to_numpy()
    )
    logistic_results["mat_fp_pc"] = (k, x0)
    for target in SCORE_TARGETS:
        x_cross = logistic_crossing(k, x0, target)
        crossing_rows.append(
            {
                "predictor": "mat_fp_pc",
                "predictor_label": predictors["mat_fp_pc"][0],
                "fit_form": "logistic_logx",
                "fit_a": k,
                "fit_b": x0,
                "score_target": target,
                "x_crossing": x_cross,
                "n_countries": int(dmc["country_code"].nunique()),
            }
        )
        print(
            f"  [mat_fp_pc] logistic(ln x) fit: score={target:.2f} "
            f"crossing at x={x_cross:,.1f}"
        )
    crossings = pd.DataFrame(crossing_rows)

    # ── Binned reliability cross-check ───────────────────────────────────────
    # Two estimands are reported side by side:
    #   - 'all_country_years': every country-year (the original; over-weights
    #     countries with long time series).
    #   - 'latest_year_per_country': one row per country (cross-section).
    # Each also carries a POPULATION-WEIGHTED share (people, not units) alongside
    # the unweighted (country-year) share.
    gdp_bins = [0, 5000, 10000, 15000, 20000, 30000, 50000, np.inf]
    gdp_labels = ["<5k", "5-10k", "10-15k", "15-20k", "20-30k", "30-50k", "50k+"]
    mat_bins = [0, 4, 6, 8, 10, 15, 20, 30, np.inf]
    mat_labels = ["<4", "4-6", "6-8", "8-10", "10-15", "15-20", "20-30", "30+"]
    rel_gdp = bin_reliability(
        both, "gdppc_ppp_current", gdp_bins, gdp_labels, "all_country_years"
    )
    rel_mat = bin_reliability(
        both, "mat_fp_pc", mat_bins, mat_labels, "all_country_years"
    )
    rel_gdp_latest = bin_reliability(
        latest, "gdppc_ppp_current", gdp_bins, gdp_labels, "latest_year_per_country"
    )
    rel_mat_latest = bin_reliability(
        latest, "mat_fp_pc", mat_bins, mat_labels, "latest_year_per_country"
    )
    reliability = pd.concat(
        [rel_gdp, rel_mat, rel_gdp_latest, rel_mat_latest], ignore_index=True
    )
    print(
        "\nDMC bin reliability (all country-years) -- unweighted vs pop-weighted share >=0.80:"
    )
    print(
        rel_mat[
            [
                "bin",
                "n_countries",
                "median_score",
                "share_score_80",
                "pop_weighted_share_score_80",
            ]
        ].to_string(index=False)
    )
    print(
        "\nDMC bin reliability (latest year per country) -- unweighted vs pop-weighted share >=0.80:"
    )
    print(
        rel_mat_latest[
            [
                "bin",
                "n_countries",
                "median_score",
                "share_score_80",
                "pop_weighted_share_score_80",
            ]
        ].to_string(index=False)
    )

    # ── C. Sustainable-boundary comparison (DMC vs MF-origin boundary) ───────
    # NB: basis mismatch -- the <=8 t/cap boundary is from MF literature, but the
    # per-country predictor is DMC. Existence proofs are NOT proven on a true MF
    # basis (see module docstring). Flag small/stale cases for sensitivity.
    high = latest[latest["good_life_score"] >= 0.80].copy()
    within = high[high["mat_fp_pc"] <= MATERIAL_BOUNDARY_TPC].copy()
    pop_col = "population" if "population" in latest.columns else "analysis_population"
    total_pop = latest[pop_col].sum()
    high_pop = high[pop_col].sum()
    within_pop = within[pop_col].sum()

    # Build + save existence-proof CSV with robustness flags
    SMALL_STATE_POP = 1_000_000
    ep = within.copy()
    ind_col = (
        "good_life_indicators_available"
        if "good_life_indicators_available" in ep.columns
        else None
    )
    ep_out = pd.DataFrame(
        {
            "country_code": ep["country_code"],
            "country": ep["country"],
            "year": ep["year"].astype(int),
            "dmc_per_cap": ep["mat_fp_pc"],
            "good_life_score": ep["good_life_score"],
            "population": ep[pop_col],
            "n_good_life_indicators_available": (ep[ind_col] if ind_col else np.nan),
            "small_state_flag": ep[pop_col] < SMALL_STATE_POP,
            "stale_year_flag": ep["year"] < 2015,
        }
    ).sort_values("dmc_per_cap")
    ep_path = PROC / "weightless_growth_existence_proofs.csv"
    ep_out.to_csv(ep_path, index=False)

    # Population-weighted shares including vs excluding small states (<1M)
    ep_big = ep[ep[pop_col] >= SMALL_STATE_POP]
    within_pop_big = ep_big[pop_col].sum()
    high_big_pop = high[high[pop_col] >= SMALL_STATE_POP][pop_col].sum()
    total_pop_big = latest[latest[pop_col] >= SMALL_STATE_POP][pop_col].sum()

    print("\n" + "=" * 78)
    print(f"High-outcome (score>=0.80) countries (latest): {len(high)}")
    print(
        f"  ... with DMC <= {MATERIAL_BOUNDARY_TPC:.0f} t/cap "
        f"(DMC vs MF-origin boundary, basis mismatch): {len(within)}"
    )
    print(
        f"  Existence-proof countries: {len(ep_out)} "
        f"({int(ep_out['small_state_flag'].sum())} small states <1M; "
        f"{int(ep_out['stale_year_flag'].sum())} with stale year <2015)"
    )
    if total_pop and not np.isnan(total_pop):
        print("  Population-weighted share (INCLUDING small states):")
        print(
            f"    {within_pop / total_pop:.1%} of cross-section pop; "
            f"{within_pop / high_pop:.1%} of high-outcome pop"
            if high_pop
            else ""
        )
        if total_pop_big:
            print("  Population-weighted share (EXCLUDING small states <1M):")
            print(
                f"    {within_pop_big / total_pop_big:.1%} of cross-section pop; "
                f"{within_pop_big / high_big_pop:.1%} of high-outcome pop"
                if high_big_pop
                else ""
            )
    if len(within):
        print("  EXISTENCE-PROOF countries (high outcome, low DMC):")
        for _, r in within.sort_values("mat_fp_pc").iterrows():
            small = " [small <1M]" if r[pop_col] < SMALL_STATE_POP else ""
            stale = " [stale <2015]" if r["year"] < 2015 else ""
            print(
                f"    {r['country']:<24} score={r['good_life_score']:.3f} "
                f"DMC={r['mat_fp_pc']:.1f} t/cap  GDP/cap={r['gdppc_ppp_current']:,.0f}"
                f"{small}{stale}"
            )
    else:
        print("  No high-outcome country is at/below the 8 t/cap boundary.")
    print(f"  Saved {ep_path.relative_to(BASE)} ({len(ep_out)} rows)")

    # ── Save crossing + reliability table ────────────────────────────────────
    boundary_row = pd.DataFrame(
        [
            {
                "predictor": "summary",
                "predictor_label": "boundary_comparison",
                "score_target": 0.80,
                "x_crossing": np.nan,
                "material_boundary_tpc": MATERIAL_BOUNDARY_TPC,
                "n_high_outcome_countries": len(high),
                "n_high_outcome_within_boundary": len(within),
                "pop_share_high_within_boundary": (
                    within_pop / total_pop if total_pop else np.nan
                ),
            }
        ]
    )
    out = pd.concat([crossings, reliability, boundary_row], ignore_index=True)
    out_path = PROC / "weightless_growth_saturation.csv"
    out.to_csv(out_path, index=False)
    print(f"\nSaved {out_path.relative_to(BASE)}")

    # ── Chart 104: two-panel saturation comparison ───────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    panel_specs = [
        ("gdppc_ppp_current", "GDP per capita (PPP, current intl $)", axes[0], None),
        (
            "mat_fp_pc",
            "Domestic material consumption per capita (DMC, territorial, t/cap)",
            axes[1],
            MATERIAL_BOUNDARY_TPC,
        ),
    ]
    for col, label, ax, boundary in panel_specs:
        sub = latest.dropna(subset=[col, "good_life_score"])
        sub = sub[sub[col] > 0]
        ax.scatter(sub[col], sub["good_life_score"], s=28, alpha=0.6, color="#4C72B0")
        a, b = fit_results[col]
        xs = np.linspace(sub[col].min(), sub[col].max(), 200)
        ax.plot(
            xs,
            np.clip(log_fit(xs, a, b), 0, 1),
            color="#C44E52",
            lw=2,
            label="log fit: a·ln(x)+b",
        )
        if col in logistic_results:
            k, x0 = logistic_results[col]
            ax.plot(
                xs,
                np.clip(logistic_logx(xs, k, x0), 0, 1),
                color="#8172B3",
                lw=2,
                ls="--",
                label="logistic(ln x) fit (robustness)",
            )
            xc_log = logistic_crossing(k, x0, 0.80)
            if (
                not np.isnan(xc_log)
                and sub[col].min() <= xc_log <= sub[col].max() * 1.05
            ):
                ax.axvline(
                    xc_log,
                    color="#8172B3",
                    ls=":",
                    lw=1.2,
                    label=f"logistic score=0.80 at x={xc_log:,.0f}",
                )
        for target, style in zip(SCORE_TARGETS, ["--", ":"]):
            xc = crossing_x(a, b, target)
            if not np.isnan(xc) and sub[col].min() <= xc <= sub[col].max() * 1.05:
                ax.axvline(
                    xc,
                    color="#55A868",
                    ls=style,
                    lw=1.5,
                    label=f"log score={target:.2f} at x={xc:,.0f}",
                )
        ax.axhline(0.80, color="grey", ls="-", lw=0.6, alpha=0.5)
        if boundary is not None:
            ax.axvline(
                boundary,
                color="black",
                ls="-",
                lw=1.8,
                label=f"MF-origin boundary ~{boundary:.0f} t/cap",
            )
            ax.text(
                0.99,
                0.02,
                "Basis mismatch: predictor is DMC (territorial); ~8 t/cap boundary\n"
                "is from consumption-based MF literature — not like-for-like.",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=7,
                color="#555555",
                style="italic",
            )
        ax.set_xlabel(label)
        ax.set_ylabel("Good-life outcome score (0-1)")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=8, loc="lower right")
    axes[0].set_title("Outcomes vs GDP/cap")
    axes[1].set_title(
        "Outcomes vs domestic material consumption/cap (DMC, territorial)"
    )
    fig.suptitle(
        "Weightless growth test: does the good life saturate below the material boundary?",
        fontsize=13,
    )
    fig.savefig(CHARTS / "104_weightless_growth_saturation.png")
    plt.close(fig)

    # ── Chart 105: scatter vs material boundary, highlight existence-proof ────
    fig, ax = plt.subplots(figsize=(12, 7))
    sub = latest.dropna(subset=["mat_fp_pc", "good_life_score"])
    low_fp_high = (sub["mat_fp_pc"] <= MATERIAL_BOUNDARY_TPC) & (
        sub["good_life_score"] >= 0.80
    )
    ax.scatter(
        sub.loc[~low_fp_high, "mat_fp_pc"],
        sub.loc[~low_fp_high, "good_life_score"],
        s=32,
        alpha=0.55,
        color="#8C8C8C",
        label="other countries",
    )
    ax.scatter(
        sub.loc[low_fp_high, "mat_fp_pc"],
        sub.loc[low_fp_high, "good_life_score"],
        s=80,
        color="#55A868",
        edgecolor="black",
        zorder=5,
        label="high outcome & ≤8 t/cap (existence proof)",
    )
    for _, r in sub[low_fp_high].iterrows():
        ax.annotate(
            r["country"],
            (r["mat_fp_pc"], r["good_life_score"]),
            fontsize=8,
            xytext=(4, 4),
            textcoords="offset points",
        )
    ax.axvline(
        MATERIAL_BOUNDARY_TPC,
        color="black",
        ls="--",
        lw=1.8,
        label=f"MF-origin boundary ~{MATERIAL_BOUNDARY_TPC:.0f} t/cap",
    )
    ax.axhline(0.80, color="#C44E52", ls=":", lw=1.2, label="good_life_score = 0.80")
    ax.set_xlabel("Domestic material consumption per capita (DMC, territorial, t/cap)")
    ax.set_ylabel("Good-life outcome score (0-1)")
    ax.set_ylim(0, 1)
    ax.set_title(
        "Good life vs material boundary: DMC predictor vs MF-origin ~8 t/cap line\n"
        "(latest year per country; basis mismatch — not a like-for-like test)"
    )
    ax.text(
        0.99,
        0.02,
        "Predictor = DOMESTIC MATERIAL CONSUMPTION (territorial). The ~8 t/cap boundary\n"
        "is from consumption-based MATERIAL FOOTPRINT literature. DMC understates rich\n"
        "import-dependent economies but can overstate exporters — sign is not universal.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
        color="#555555",
        style="italic",
    )
    ax.legend(fontsize=9, loc="lower right")
    fig.savefig(CHARTS / "105_good_life_vs_material_boundary.png")
    plt.close(fig)

    print(f"Saved charts/104_weightless_growth_saturation.png")
    print(f"Saved charts/105_good_life_vs_material_boundary.png")


if __name__ == "__main__":
    main()
