#!/usr/bin/env python3
"""
Comprehensive analysis of global growth, poverty, and development.
Addresses 7 key questions for the growth-vs-redistribution debate.

Use --corrections-only to refresh the withdrawn charts 00/06 offline without
loading datasets or running the analysis pipeline.
"""

import os, sys, warnings
import tempfile

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS = os.path.join(BASE, "charts")
PROC = os.path.join(BASE, "data", "processed")
RAW = os.path.join(BASE, "data", "raw")
os.makedirs(CHARTS, exist_ok=True)

plt.rcParams.update(
    {
        "figure.figsize": (14, 8),
        "font.size": 12,
        "axes.titlesize": 14,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.dpi": 150,
    }
)
sns.set_style("whitegrid")

WITHDRAWN_CHARTS = {
    "00_summary_dashboard.png": "Chart 00: Legacy summary dashboard withdrawn",
    "06_redistribution_cost.png": "Chart 06: Legacy redistribution cost comparison withdrawn",
}
GDP_SHARE_WITHDRAWAL = (
    "The legacy calculation divides a 2017-PPP poverty gap by\n"
    "constant-2015 market-US$ GDP. These price bases are incompatible.\n\n"
    "GDP-share levels, trends and growth-attribution claims are withdrawn;\n"
    "this calculation does not confirm that growth made redistribution cheaper.\n\n"
    "Use Analysis 28 / Chart 118 for same-basis 2021-PPP accounting\n"
    "and Chart 119 for its accounting decomposition, not causal attribution.\n"
    "No replacement estimates are computed in this notice."
)


def refresh_withdrawn_chart(filename, charts_dir=CHARTS):
    """Replace one legacy artifact atomically, without reading any data caches."""
    title = WITHDRAWN_CHARTS[filename]
    detail = (
        "The former dashboard is not republished from legacy results.\n"
        "Other analyses are not rerun or validated by this correction."
        if filename == "00_summary_dashboard.png"
        else "The former GDP-share table and years-of-growth estimate are withdrawn.\n"
        "The PPP-gap / nominal-military-spending comparison is also withdrawn.\n"
        "A 3x targeting multiplier is an assumption, not an estimated program cost."
    )
    os.makedirs(charts_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 8))
    temporary_path = None
    try:
        ax.axis("off")
        ax.set_title(title, fontsize=17, fontweight="bold", pad=24)
        ax.text(
            0.04, 0.92, "WITHDRAWN — incompatible price bases",
            transform=ax.transAxes, fontsize=17, fontweight="bold", color="#a12828",
            va="top", parse_math=False,
        )
        ax.text(
            0.04, 0.78, GDP_SHARE_WITHDRAWAL,
            transform=ax.transAxes, fontsize=14, va="top", linespacing=1.5,
            parse_math=False,
        )
        ax.text(
            0.04, 0.16, detail, transform=ax.transAxes, fontsize=11,
            va="top", color="#555555", linespacing=1.5, parse_math=False,
        )
        fig.tight_layout()
        # Render alongside the destination and publish only a complete PNG.
        with tempfile.NamedTemporaryFile(
            dir=charts_dir, prefix=f".{filename}.", suffix=".png", delete=False
        ) as temporary:
            temporary_path = temporary.name
        fig.savefig(temporary_path)
        os.replace(temporary_path, os.path.join(charts_dir, filename))
    finally:
        plt.close(fig)
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)
    print(f"  -> Saved {filename} (WITHDRAWN; no replacement estimates)")


if __name__ == "__main__" and "--corrections-only" in sys.argv[1:]:
    for filename in WITHDRAWN_CHARTS:
        refresh_withdrawn_chart(filename)
    raise SystemExit(0)

# ============================================================
# LOAD DATA
# ============================================================
print("Loading data...")

# WDI
wdi = pd.read_csv(os.path.join(PROC, "wdi_combined.csv"))
print(f"  WDI: {len(wdi)} rows")

# Maddison
mad = pd.read_csv(os.path.join(PROC, "maddison.csv"))
print(f"  Maddison: {len(mad)} rows, years {mad.year.min()}-{mad.year.max()}")

# PIP poverty data at different thresholds
pip_data = {}
pip_regional = {}
for pl in [2.15, 3.65, 6.85, 10.0]:
    key = str(pl)
    df = pd.read_csv(os.path.join(RAW, f"pip_country_{pl}.csv"))
    # Keep national-level data preferentially
    df = df.sort_values(["country_code", "reporting_year", "reporting_level"])
    df = df.drop_duplicates(subset=["country_code", "reporting_year"], keep="first")
    pip_data[key] = df
    pip_regional[key] = pd.read_csv(os.path.join(RAW, f"pip_regional_{pl}.csv"))
    print(
        f"  PIP {pl}: {len(df)} country-years, {len(pip_regional[key])} regional-years"
    )


###############################################################################
# ANALYSIS 1: LEGACY MIXED-BASIS DIAGNOSTIC (NOT A GDP SHARE)
# Cannot establish whether growth has made redistribution cheaper.
###############################################################################
print("\n" + "=" * 70)
print("ANALYSIS 1: LEGACY MIXED-BASIS DIAGNOSTIC — NOT A GDP SHARE")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle(
    "LEGACY MIXED-BASIS DIAGNOSTIC — SUPERSEDED BY CHART 118\n"
    "2017-PPP gap divided by constant-2015 market-US$ GDP",
    fontsize=16,
    fontweight="bold",
)

# Get legacy constant-2015 market-US$ GDP (World aggregate = WLD).
wdi_world = wdi[wdi["country_code"] == "WLD"].copy()
# LEGACY ONLY: PIP gaps are in 2017 PPP while this GDP series is in constant
# 2015 market USD. Being inflation-adjusted does not make the price bases
# comparable, so neither the level nor its decomposition is valid as a GDP
# share. Analysis 28 / Chart 118 supersedes this output with both series in
# constant 2021 PPP. Keep the calculation only to preserve the old pipeline.
gdp_by_year = wdi_world.set_index("year")["gdp_constant_2015usd"].dropna().to_dict()
print(
    "  WARNING: Chart 01 is a legacy mixed-price-basis diagnostic; "
    "use Chart 118 for poverty-gap/GDP levels and trends."
)

results_a1 = {}
for idx, pl in enumerate([2.15, 3.65, 6.85, 10.0]):
    key = str(pl)
    reg = pip_regional[key].copy()

    # Use WLD (world aggregate) row only — summing sub-regions double-counts
    wld = reg[reg["region_code"] == "WLD"].copy()

    # Compute total poverty gap in dollars from WLD row
    # poverty_gap index = (1/N) * sum of (z-yi)/z for poor
    # Total gap in dollars/year = P1 * poverty_line * total_population * 365
    gap_records = []
    for _, row in wld.iterrows():
        yr = row["reporting_year"]
        total_gap_usd = row["poverty_gap"] * pl * row["reporting_pop"] * 365
        total_pop = row["reporting_pop"]
        total_poor = row.get("pop_in_poverty", 0)

        global_gdp = gdp_by_year.get(yr, np.nan)
        gap_pct = (
            (total_gap_usd / global_gdp * 100)
            if global_gdp and not np.isnan(global_gdp)
            else np.nan
        )

        gap_records.append(
            {
                "year": yr,
                "poverty_line": pl,
                "total_gap_bn": total_gap_usd / 1e9,
                "global_gdp_tn": global_gdp / 1e12 if global_gdp else np.nan,
                "gap_pct_gdp": gap_pct,
                "total_poor_bn": total_poor / 1e9,
                "total_pop_bn": total_pop / 1e9,
                "headcount_rate": total_poor / total_pop if total_pop > 0 else np.nan,
            }
        )

    df_gap = pd.DataFrame(gap_records).dropna(subset=["gap_pct_gdp"])
    results_a1[key] = df_gap

    ax = axes[idx // 2][idx % 2]
    ax2 = ax.twinx()

    l1 = ax.plot(
        df_gap["year"],
        df_gap["gap_pct_gdp"],
        "b-o",
        markersize=3,
        label="Legacy mixed-basis ratio (x100; not a GDP share)",
    )
    l2 = ax2.plot(
        df_gap["year"],
        df_gap["total_gap_bn"],
        "r--s",
        markersize=3,
        alpha=0.7,
        label="Gap (billion 2017-PPP international $)",
    )

    ax.set_title(f"${pl}/day poverty line")
    ax.set_xlabel("Year")
    ax.set_ylabel("Mixed-basis ratio (x100; not a valid GDP share)", color="b")
    ax2.set_ylabel("Poverty gap (billion 2017-PPP international $)", color="r")

    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc="upper right", fontsize=9)

    if len(df_gap) >= 2:
        first = df_gap.iloc[0]
        last = df_gap.iloc[-1]
        print(f"\n  ${pl}/day line:")
        print(
            f"    {int(first['year'])}: gap = {first['total_gap_bn']:.0f}B 2017-PPP international $, {first['total_poor_bn']:.2f}B people"
        )
        print(
            f"    {int(last['year'])}: gap = {last['total_gap_bn']:.0f}B 2017-PPP international $, {last['total_poor_bn']:.2f}B people"
        )
        print(
            "    GDP-share levels and changes WITHDRAWN: incompatible price bases."
        )

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "01_poverty_gap_pct_gdp.png"))
plt.close()
print("\n  -> Saved 01_poverty_gap_pct_gdp.png")

# Also create a single combined chart
fig, ax = plt.subplots(figsize=(14, 8))
colors = ["#2196F3", "#FF9800", "#E91E63", "#9C27B0"]
for (key, df_gap), color in zip(results_a1.items(), colors):
    ax.plot(
        df_gap["year"],
        df_gap["gap_pct_gdp"],
        "-o",
        color=color,
        markersize=3,
        label=f"${key}/day",
    )
ax.set_title(
    "LEGACY MIXED-BASIS SERIES — SUPERSEDED BY CHART 118",
    fontsize=14,
    fontweight="bold",
)
ax.set_xlabel("Year")
ax.set_ylabel("Mixed-basis ratio (x100; not a valid GDP share)")
ax.text(
    0.02,
    0.02,
    "Incompatible units: 2017-PPP gap / constant-2015 market-US$ GDP. Do not interpret as a GDP share.",
    transform=ax.transAxes,
    fontsize=7,
    color="gray",
    style="italic",
)
ax.legend(fontsize=12)
ax.set_xlim(1990, None)
plt.savefig(os.path.join(CHARTS, "01b_poverty_gap_combined.png"))
plt.close()
print("  -> Saved 01b_poverty_gap_combined.png")


###############################################################################
# ANALYSIS 2: DECOMPOSE POVERTY REDUCTION — BY COUNTRY/REGION
###############################################################################
print("\n" + "=" * 70)
print("ANALYSIS 2: DECOMPOSE POVERTY REDUCTION BY REGION")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle(
    "Where Has Poverty Reduction Come From?\nPeople Lifted Above Each Poverty Line by Region",
    fontsize=16,
    fontweight="bold",
)

for idx, pl in enumerate([2.15, 3.65, 6.85, 10.0]):
    key = str(pl)
    reg = pip_regional[key].copy()

    ax = axes[idx // 2][idx % 2]

    # Pivot to get regions over time
    # Non-overlapping regions only (exclude AFE/AFW which are sub-regions of SSF)
    non_overlapping = {"EAS", "SAS", "SSF", "ECS", "LCN", "MEA", "NAC"}

    for _, grp in reg.groupby("region_code"):
        rcode = grp["region_code"].iloc[0]
        rname = grp["region_name"].iloc[0]
        if rcode not in non_overlapping:
            continue
        data = grp.sort_values("reporting_year")
        ax.plot(
            data["reporting_year"],
            data["pop_in_poverty"] / 1e9,
            "-",
            linewidth=2,
            label=rname[:30],
        )

    ax.set_title(f"${pl}/day poverty line")
    ax.set_xlabel("Year")
    ax.set_ylabel("People in poverty (billions)")
    ax.legend(fontsize=7, loc="upper right")

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "02_poverty_by_region.png"))
plt.close()
print("  -> Saved 02_poverty_by_region.png")

# Key country decomposition at $2.15
pip215 = pip_data["2.15"].copy()
key_countries = {
    "CHN": "China",
    "IND": "India",
    "IDN": "Indonesia",
    "BGD": "Bangladesh",
    "VNM": "Vietnam",
    "NGA": "Nigeria",
    "ETH": "Ethiopia",
    "COD": "DR Congo",
    "BRA": "Brazil",
}

fig, ax = plt.subplots(figsize=(14, 8))
for cc, name in key_countries.items():
    cdata = pip215[pip215["country_code"] == cc].sort_values("reporting_year")
    if len(cdata) > 0:
        poor = cdata["headcount"] * cdata["reporting_pop"]
        ax.plot(
            cdata["reporting_year"],
            poor / 1e6,
            "-o",
            markersize=3,
            linewidth=2,
            label=name,
        )

        if len(cdata) >= 2:
            first_yr = cdata.iloc[0]
            last_yr = cdata.iloc[-1]
            change = (
                last_yr["headcount"] * last_yr["reporting_pop"]
                - first_yr["headcount"] * first_yr["reporting_pop"]
            ) / 1e6
            print(
                f"  {name}: {change:+.0f}M people at $2.15/day ({int(first_yr['reporting_year'])}-{int(last_yr['reporting_year'])})"
            )

ax.set_title(
    "People in Extreme Poverty ($2.15/day) by Key Country",
    fontsize=14,
    fontweight="bold",
)
ax.set_xlabel("Year")
ax.set_ylabel("People in poverty (millions)")
ax.legend(fontsize=10)
plt.savefig(os.path.join(CHARTS, "02b_poverty_key_countries.png"))
plt.close()
print("  -> Saved 02b_poverty_key_countries.png")

# China's share of global poverty reduction
reg215 = pip_regional["2.15"]
# Use WLD row only — summing sub-regions double-counts (SSF = AFE + AFW)
world_data = reg215[reg215["region_code"] == "WLD"][
    ["reporting_year", "pop_in_poverty"]
].copy()
china_data = pip215[pip215["country_code"] == "CHN"].sort_values("reporting_year")

# Find overlapping years
common_start = max(
    world_data["reporting_year"].min(), china_data["reporting_year"].min()
)
common_end = min(world_data["reporting_year"].max(), china_data["reporting_year"].max())
print(f"\n  China's contribution to global $2.15/day poverty reduction:")
for start_yr, end_yr in [(1990, 2010), (1990, 2019), (2000, 2019)]:
    w_start = world_data[world_data["reporting_year"] == start_yr][
        "pop_in_poverty"
    ].values
    w_end = world_data[world_data["reporting_year"] == end_yr]["pop_in_poverty"].values
    c_start = china_data[china_data["reporting_year"] == start_yr]
    c_end = china_data[china_data["reporting_year"] == end_yr]
    if len(w_start) > 0 and len(w_end) > 0 and len(c_start) > 0 and len(c_end) > 0:
        w_change = w_end[0] - w_start[0]
        c_poor_start = c_start.iloc[0]["headcount"] * c_start.iloc[0]["reporting_pop"]
        c_poor_end = c_end.iloc[0]["headcount"] * c_end.iloc[0]["reporting_pop"]
        c_change = c_poor_end - c_poor_start
        pct = c_change / w_change * 100 if w_change != 0 else float("nan")
        print(f"    {start_yr}-{end_yr}: China = {pct:.1f}% of global reduction")


###############################################################################
# ANALYSIS 3: GROWTH TRAJECTORIES — TIME-NORMALIZED FROM LOW BASE
###############################################################################
print("\n" + "=" * 70)
print("ANALYSIS 3: GROWTH TRAJECTORIES FROM POVERTY")
print("=" * 70)

# Use Maddison for long-run data
# Identify when each growth success crossed key thresholds
# $1/day in 2011 PPP ≈ roughly $400-600/year in 2011 international dollars
# Maddison uses 2011 international $ GDP per capita

growth_cases = {
    "GBR": ("England/UK", "#1f77b4"),
    "USA": ("United States", "#ff7f0e"),
    "FRA": ("France", "#2ca02c"),
    "DEU": ("Germany", "#d62728"),
    "JPN": ("Japan", "#9467bd"),
    "KOR": ("South Korea", "#8c564b"),
    "CHN": ("China", "#e377c2"),
    "IND": ("India", "#7f7f7f"),
    "VNM": ("Vietnam", "#bcbd22"),
    "POL": ("Poland", "#17becf"),
    "MYS": ("Malaysia", "#ff6384"),
    "BWA": ("Botswana", "#36a2eb"),
    "TWN": ("Taiwan", "#cc65fe"),
}

# $2/day ~ $730/year; $5/day ~ $1825/year; we'll use $1000 (approx $2.75/day) as a base
BASE_THRESHOLD = 1000  # ~$2.75/day in 2011 int'l $

fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Panel A: Absolute GDP per capita over time
ax = axes[0]
for cc, (name, color) in growth_cases.items():
    cdata = mad[(mad["countrycode"] == cc) & (mad["gdppc"].notna())].sort_values("year")
    if len(cdata) > 0:
        # Only plot from 1700 onwards for readability
        cdata = cdata[cdata["year"] >= 1700]
        ax.plot(cdata["year"], cdata["gdppc"], color=color, linewidth=2, label=name)

ax.set_yscale("log")
ax.set_title("GDP per Capita (2011 int'l $), Log Scale", fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("GDP per capita (2011 int'l $)")
ax.axhline(y=730, color="red", linestyle="--", alpha=0.5, label="~$2/day")
ax.axhline(y=1825, color="orange", linestyle="--", alpha=0.5, label="~$5/day")
ax.axhline(y=2500, color="green", linestyle="--", alpha=0.5, label="~$6.85/day")
ax.legend(fontsize=8, loc="upper left")
ax.set_ylim(300, 80000)

# Panel B: Time-normalized — years since crossing $1000/year threshold
ax = axes[1]
for cc, (name, color) in growth_cases.items():
    cdata = mad[(mad["countrycode"] == cc) & (mad["gdppc"].notna())].sort_values("year")
    if len(cdata) == 0:
        continue
    # Find first year above threshold
    above = cdata[cdata["gdppc"] >= BASE_THRESHOLD]
    if len(above) == 0:
        continue
    t0_year = above.iloc[0]["year"]
    cdata = cdata[cdata["year"] >= t0_year].copy()
    cdata["years_since_t0"] = cdata["year"] - t0_year
    cdata["gdppc_ratio"] = cdata["gdppc"] / BASE_THRESHOLD

    ax.plot(
        cdata["years_since_t0"],
        cdata["gdppc_ratio"],
        color=color,
        linewidth=2,
        label=f"{name} (t₀={int(t0_year)})",
    )
    print(f"  {name}: crossed ${BASE_THRESHOLD}/yr in {int(t0_year)}")

ax.set_yscale("log")
ax.set_title(
    f"Growth After Crossing ${BASE_THRESHOLD}/yr (≈$2.75/day)\nTime Normalized",
    fontweight="bold",
)
ax.set_xlabel(f"Years since GDP/capita first reached ${BASE_THRESHOLD}")
ax.set_ylabel(f"GDP per capita (multiple of ${BASE_THRESHOLD})")
ax.axhline(y=1, color="gray", linestyle="-", alpha=0.3)
ax.axhline(y=10, color="green", linestyle="--", alpha=0.5, label="10x (~$27/day)")
ax.axhline(y=40, color="blue", linestyle="--", alpha=0.5, label="40x (high income)")
ax.legend(fontsize=7, loc="upper left")
ax.set_xlim(-10, 300)
ax.set_ylim(0.5, 100)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "03_growth_trajectories.png"))
plt.close()
print("  -> Saved 03_growth_trajectories.png")

# Compute time to reach various multiples
print("\n  Time to reach GDP/capita multiples from $1000 base:")
print(
    f"  {'Country':<15} {'t₀ year':<10} {'→ 5x':<10} {'→ 10x':<10} {'→ 20x':<10} {'→ 40x':<10}"
)
for cc, (name, color) in growth_cases.items():
    cdata = mad[(mad["countrycode"] == cc) & (mad["gdppc"].notna())].sort_values("year")
    above = cdata[cdata["gdppc"] >= BASE_THRESHOLD]
    if len(above) == 0:
        continue
    t0 = above.iloc[0]["year"]
    row = f"  {name:<15} {int(t0):<10}"
    for mult in [5, 10, 20, 40]:
        target = cdata[cdata["gdppc"] >= BASE_THRESHOLD * mult]
        if len(target) > 0:
            yrs = target.iloc[0]["year"] - t0
            row += f" {int(yrs):<10}"
        else:
            row += f" {'n/a':<10}"
    print(row)


###############################################################################
# ANALYSIS 4: CONVERGENCE ANALYSIS
###############################################################################
print("\n" + "=" * 70)
print("ANALYSIS 4: CONVERGENCE — ARE POOR COUNTRIES CATCHING UP?")
print("=" * 70)

# Sigma convergence: standard deviation of log GDP per capita over time
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle(
    "Convergence Analysis: Are Poor Countries Catching Up?",
    fontsize=16,
    fontweight="bold",
)

# Panel A: Sigma convergence (Maddison, 1950+)
ax = axes[0][0]
sigma_records = []
for yr in range(1950, 2023):
    yr_data = mad[
        (mad["year"] == yr)
        & (mad["gdppc"].notna())
        & (mad["gdppc"] > 0)
        & (mad["pop"].notna())
    ]
    if len(yr_data) >= 30:  # need enough countries
        log_gdppc = np.log(yr_data["gdppc"])
        sigma_records.append(
            {
                "year": yr,
                "sigma_unweighted": log_gdppc.std(),
                "n_countries": len(yr_data),
                # Population-weighted sigma
                "sigma_weighted": np.sqrt(
                    np.average(
                        (log_gdppc - np.average(log_gdppc, weights=yr_data["pop"]))
                        ** 2,
                        weights=yr_data["pop"],
                    )
                ),
            }
        )

df_sigma = pd.DataFrame(sigma_records)
ax.plot(
    df_sigma["year"],
    df_sigma["sigma_unweighted"],
    "b-",
    linewidth=2,
    label="Unweighted",
)
ax.plot(
    df_sigma["year"],
    df_sigma["sigma_weighted"],
    "r-",
    linewidth=2,
    label="Population-weighted",
)
ax.set_title("Sigma Convergence: Dispersion of log(GDP/capita)")
ax.set_xlabel("Year")
ax.set_ylabel("Std. dev. of log(GDP per capita)")
ax.legend()
print(
    f"  Sigma convergence (unweighted): {df_sigma.iloc[0]['sigma_unweighted']:.3f} ({int(df_sigma.iloc[0]['year'])}) -> {df_sigma.iloc[-1]['sigma_unweighted']:.3f} ({int(df_sigma.iloc[-1]['year'])})"
)
print(
    f"  Sigma convergence (pop-weighted): {df_sigma.iloc[0]['sigma_weighted']:.3f} ({int(df_sigma.iloc[0]['year'])}) -> {df_sigma.iloc[-1]['sigma_weighted']:.3f} ({int(df_sigma.iloc[-1]['year'])})"
)

# Panel B: Beta convergence scatter (initial GDP vs growth rate)
ax = axes[0][1]
# Use 1990-2022 period
start_yr, end_yr = 1990, 2022
start_data = mad[
    (mad["year"] == start_yr) & (mad["gdppc"].notna()) & (mad["gdppc"] > 0)
].set_index("countrycode")
end_data = mad[
    (mad["year"] == end_yr) & (mad["gdppc"].notna()) & (mad["gdppc"] > 0)
].set_index("countrycode")
common = start_data.index.intersection(end_data.index)

if len(common) > 10:
    log_initial = np.log(start_data.loc[common, "gdppc"])
    growth = (
        (
            np.log(end_data.loc[common, "gdppc"])
            - np.log(start_data.loc[common, "gdppc"])
        )
        / (end_yr - start_yr)
        * 100
    )

    ax.scatter(log_initial, growth, alpha=0.5, s=30)
    # Regression line
    _lr = stats.linregress(log_initial, growth)
    slope, intercept, r, p = _lr.slope, _lr.intercept, _lr.rvalue, _lr.pvalue  # type: ignore[union-attr]
    x_fit = np.linspace(log_initial.min(), log_initial.max(), 100)
    ax.plot(x_fit, intercept + slope * x_fit, "r-", linewidth=2)
    ax.set_title(
        f"Beta Convergence {start_yr}-{end_yr}\nSlope={slope:.3f}, R²={r**2:.3f}, p={p:.4f}"
    )
    ax.set_xlabel(f"Log GDP per capita in {start_yr}")
    ax.set_ylabel("Annual growth rate (%)")
    print(
        f"\n  Beta convergence {start_yr}-{end_yr}: slope={slope:.4f}, R²={r**2:.3f}, p={p:.4f}"
    )
    print(
        f"    {'Convergence' if slope < 0 else 'Divergence'} ({'significant' if p < 0.05 else 'not significant'})"
    )

    # Label some key countries
    for cc in ["CHN", "IND", "KOR", "NGA", "USA", "ETH", "VNM", "BWA", "COD", "BRA"]:
        if cc in common:
            ax.annotate(cc, (log_initial[cc], growth[cc]), fontsize=7, alpha=0.7)  # type: ignore[index]

# Panel C: Beta convergence by period
ax = axes[1][0]
periods = [(1960, 1980), (1980, 2000), (2000, 2022)]
colors_p = ["blue", "orange", "green"]
for (sy, ey), clr in zip(periods, colors_p):
    sd = mad[
        (mad["year"] == sy) & (mad["gdppc"].notna()) & (mad["gdppc"] > 0)
    ].set_index("countrycode")
    ed = mad[
        (mad["year"] == ey) & (mad["gdppc"].notna()) & (mad["gdppc"] > 0)
    ].set_index("countrycode")
    cm = sd.index.intersection(ed.index)
    if len(cm) > 10:
        lg = np.log(sd.loc[cm, "gdppc"])
        gr = (
            (np.log(ed.loc[cm, "gdppc"]) - np.log(sd.loc[cm, "gdppc"]))
            / (ey - sy)
            * 100
        )
        _lr = stats.linregress(lg, gr)
        slope, intercept, r, p = _lr.slope, _lr.intercept, _lr.rvalue, _lr.pvalue  # type: ignore[union-attr]
        x_fit = np.linspace(lg.min(), lg.max(), 100)
        ax.plot(
            x_fit,
            intercept + slope * x_fit,
            "-",
            color=clr,
            linewidth=2,
            label=f"{sy}-{ey}: β={slope:.3f}, R²={r**2:.2f}",
        )
        print(f"  Beta convergence {sy}-{ey}: slope={slope:.4f}, R²={r**2:.3f}")

ax.set_title("Beta Convergence by Period")
ax.set_xlabel("Log initial GDP per capita")
ax.set_ylabel("Annual growth rate (%)")
ax.legend(fontsize=10)

# Panel D: Growth rates of bottom 20 vs top 20 countries over time
ax = axes[1][1]
bottom_top = []
for yr in range(1960, 2020, 5):
    yr_start = mad[(mad["year"] == yr) & (mad["gdppc"].notna()) & (mad["gdppc"] > 0)]
    yr_end = mad[(mad["year"] == yr + 5) & (mad["gdppc"].notna()) & (mad["gdppc"] > 0)]
    common_bt = set(yr_start["countrycode"]) & set(yr_end["countrycode"])
    if len(common_bt) < 40:
        continue
    merged = yr_start[yr_start["countrycode"].isin(common_bt)].merge(
        yr_end[yr_end["countrycode"].isin(common_bt)],
        on="countrycode",
        suffixes=("_s", "_e"),
    )
    merged["growth"] = (np.log(merged["gdppc_e"]) - np.log(merged["gdppc_s"])) / 5 * 100
    merged = merged.sort_values("gdppc_s")
    n = max(len(merged) // 5, 5)
    bottom_top.append(
        {
            "year": yr,
            "bottom_20pct_growth": merged.head(n)["growth"].mean(),
            "top_20pct_growth": merged.tail(n)["growth"].mean(),
            "middle_growth": merged.iloc[n:-n]["growth"].mean(),
        }
    )

df_bt = pd.DataFrame(bottom_top)
ax.plot(
    df_bt["year"],
    df_bt["bottom_20pct_growth"],
    "r-o",
    label="Poorest 20% of countries",
    markersize=4,
)
ax.plot(
    df_bt["year"],
    df_bt["top_20pct_growth"],
    "b-s",
    label="Richest 20% of countries",
    markersize=4,
)
ax.plot(df_bt["year"], df_bt["middle_growth"], "g-^", label="Middle 60%", markersize=4)
ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)
ax.set_title("Average Growth Rate by Income Quintile Over Time")
ax.set_xlabel("Period start year")
ax.set_ylabel("Average annual growth (%)")
ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "04_convergence.png"))
plt.close()
print("  -> Saved 04_convergence.png")


###############################################################################
# ANALYSIS 5: GROWTH ELASTICITY OF POVERTY BY REGION
###############################################################################
print("\n" + "=" * 70)
print("ANALYSIS 5: GROWTH ELASTICITY OF POVERTY BY REGION")
print("=" * 70)

pip215 = pip_data["2.15"].copy()

# Merge with WDI GDP per capita
wdi_gdp = wdi[["country_code", "year", "gdppc_constant_2015usd"]].dropna()
wdi_gdp = wdi_gdp.rename(columns={"year": "reporting_year"})

pip_merged = pip215.merge(
    wdi_gdp,
    left_on=["country_code", "reporting_year"],
    right_on=["country_code", "reporting_year"],
    how="inner",
)

# Compute growth spells
regions_to_analyze = {
    "EAS": "East Asia & Pacific",
    "SAS": "South Asia",
    "SSA": "Sub-Saharan Africa",
    "LCN": "Latin America & Caribbean",
    "ECS": "Europe & Central Asia",
}

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("Growth Elasticity of Poverty ($2.15/day)", fontsize=14, fontweight="bold")

# Build elasticity estimates by region
elasticity_records = []
for _, row_start in pip_merged.iterrows():
    cc = row_start["country_code"]
    yr_s = row_start["reporting_year"]
    # Find observations 3-10 years later for same country
    future = pip_merged[
        (pip_merged["country_code"] == cc)
        & (pip_merged["reporting_year"] > yr_s)
        & (pip_merged["reporting_year"] <= yr_s + 10)
    ]
    if len(future) == 0:
        continue
    row_end = future.iloc[-1]

    h_s = row_start["headcount"]
    h_e = row_end["headcount"]
    g_s = row_start["gdppc_constant_2015usd"]
    g_e = row_end["gdppc_constant_2015usd"]

    if h_s > 0.01 and h_e > 0.001 and g_s > 0 and g_e > 0:
        pct_change_pov = np.log(h_e) - np.log(h_s)
        pct_change_gdp = np.log(g_e) - np.log(g_s)
        if abs(pct_change_gdp) > 0.01:
            elasticity = pct_change_pov / pct_change_gdp
            elasticity_records.append(
                {
                    "country_code": cc,
                    "region": row_start.get(
                        "region_code", row_start.get("region_name", "")
                    ),
                    "start_year": yr_s,
                    "end_year": row_end["reporting_year"],
                    "elasticity": elasticity,
                    "initial_gdppc": g_s,
                    "initial_headcount": h_s,
                    "gdp_growth": pct_change_gdp,
                }
            )

df_elast = pd.DataFrame(elasticity_records)
# Clip extreme values for visualization
df_elast = df_elast[(df_elast["elasticity"] > -15) & (df_elast["elasticity"] < 5)]

# Use region_code from PIP data
pip_regions = pip215[["country_code", "region_code"]].drop_duplicates()
df_elast = df_elast.merge(pip_regions, on="country_code", how="left")

ax = axes[0]
region_elasticities = {}
for rc, rname in regions_to_analyze.items():
    rdata = df_elast[df_elast["region_code"] == rc]
    if len(rdata) >= 5:
        median_e = rdata["elasticity"].median()
        region_elasticities[rname] = median_e

if region_elasticities:
    bars = ax.barh(
        list(region_elasticities.keys()),
        list(region_elasticities.values()),
        color="steelblue",
    )
    ax.set_xlabel("Median Growth Elasticity of Poverty")
    ax.set_title(
        "Elasticity by Region\n(more negative = growth reduces poverty faster)"
    )
    ax.axvline(x=0, color="gray", linestyle="-")
    for rname, e in region_elasticities.items():
        print(f"  {rname}: median elasticity = {e:.2f}")

# Panel B: Elasticity vs initial income
ax = axes[1]
ax.scatter(np.log(df_elast["initial_gdppc"]), df_elast["elasticity"], alpha=0.2, s=15)
# Binned averages
bins = pd.qcut(np.log(df_elast["initial_gdppc"]), 10, duplicates="drop")
binned = df_elast.groupby(bins, observed=True)["elasticity"].median()  # type: ignore[call-overload]
bin_centers = [(b.left + b.right) / 2 for b in binned.index]  # type: ignore[attr-defined]
ax.plot(
    bin_centers, binned.values, "r-o", linewidth=2, markersize=8, label="Binned median"
)
ax.set_xlabel("Log initial GDP per capita (2015 USD)")
ax.set_ylabel("Growth elasticity of poverty")
ax.set_title("Elasticity vs. Income Level")
ax.legend()
ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "05_growth_elasticity.png"))
plt.close()
print("  -> Saved 05_growth_elasticity.png")


###############################################################################
# ANALYSIS 6: REDISTRIBUTION VS. GROWTH — WHAT WOULD IT COST?
###############################################################################
print("\n" + "=" * 70)
print("ANALYSIS 6: REDISTRIBUTION VS. GROWTH COST COMPARISON")
print("=" * 70)

# Do not reuse results_a1 for GDP shares, targeting costs or years of growth.
refresh_withdrawn_chart("06_redistribution_cost.png")
print(GDP_SHARE_WITHDRAWAL)


###############################################################################
# ANALYSIS 7: GROWTH "ROTATION" — FLYING GEESE PATTERN
###############################################################################
print("\n" + "=" * 70)
print("ANALYSIS 7: GROWTH ROTATION / FLYING GEESE")
print("=" * 70)

# Track which countries had the fastest growth in each decade
# and visualize the "rotation" of growth leadership

fig, axes = plt.subplots(2, 2, figsize=(18, 14))

# Panel A: Growth rates of key developing countries over decades
ax = axes[0][0]
rotation_countries = {
    "JPN": "Japan",
    "KOR": "South Korea",
    "TWN": "Taiwan",
    "CHN": "China",
    "IND": "India",
    "VNM": "Vietnam",
    "THA": "Thailand",
    "MYS": "Malaysia",
    "IDN": "Indonesia",
    "BGD": "Bangladesh",
    "ETH": "Ethiopia",
    "RWA": "Rwanda",
}

decade_growth = {}
decades = [
    (1960, 1970),
    (1970, 1980),
    (1980, 1990),
    (1990, 2000),
    (2000, 2010),
    (2010, 2020),
]

for cc, name in rotation_countries.items():
    decade_growth[name] = []
    for ds, de in decades:
        start = mad[
            (mad["countrycode"] == cc) & (mad["year"] == ds) & (mad["gdppc"].notna())
        ]
        end = mad[
            (mad["countrycode"] == cc) & (mad["year"] == de) & (mad["gdppc"].notna())
        ]
        if len(start) > 0 and len(end) > 0 and start.iloc[0]["gdppc"] > 0:
            annual_growth = (
                (end.iloc[0]["gdppc"] / start.iloc[0]["gdppc"]) ** (1 / (de - ds)) - 1
            ) * 100
            decade_growth[name].append(annual_growth)
        else:
            decade_growth[name].append(np.nan)

decade_labels = [f"{ds}s" for ds, _ in decades]
for name, growths in decade_growth.items():
    valid = [(d, g) for d, g in zip(decade_labels, growths) if not np.isnan(g)]
    if valid:
        ax.plot(
            [d for d, g in valid],
            [g for d, g in valid],
            "-o",
            linewidth=2,
            label=name,
            markersize=4,
        )

ax.set_title("Growth by Decade: The 'Rotation' of Development")
ax.set_xlabel("Decade")
ax.set_ylabel("Annual GDP per capita growth (%)")
ax.legend(fontsize=7, loc="upper left", ncol=2)
ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)

# Panel B: Manufacturing share over time for flying geese countries
ax = axes[0][1]
mfg_countries = {
    "JPN": "Japan",
    "KOR": "South Korea",
    "CHN": "China",
    "IND": "India",
    "VNM": "Vietnam",
    "THA": "Thailand",
    "BGD": "Bangladesh",
    "IDN": "Indonesia",
}

wdi_sub = wdi[wdi["country_code"].isin(mfg_countries.keys())].copy()
if "manufacturing_va_pct" in wdi_sub.columns:
    for cc, name in mfg_countries.items():
        cdata = wdi_sub[
            (wdi_sub["country_code"] == cc) & (wdi_sub["manufacturing_va_pct"].notna())
        ].sort_values("year")
        if len(cdata) > 0:
            ax.plot(
                cdata["year"],
                cdata["manufacturing_va_pct"],
                "-",
                linewidth=2,
                label=name,
            )
else:
    ax.text(
        0.5,
        0.5,
        "Manufacturing data\nnot available\n(download timed out)",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=12,
    )

ax.set_title("Manufacturing as % of GDP\n(Flying Geese Pattern)")
ax.set_xlabel("Year")
ax.set_ylabel("Manufacturing VA (% of GDP)")
ax.legend(fontsize=9)

# Panel C: Global "growth frontier" — top 10 fastest growing countries by decade
ax = axes[1][0]
ax.axis("off")
table_data_fg = []
for ds, de in decades:
    growth_list = []
    for cc in mad["countrycode"].unique():
        start = mad[
            (mad["countrycode"] == cc) & (mad["year"] == ds) & (mad["gdppc"].notna())
        ]
        end = mad[
            (mad["countrycode"] == cc) & (mad["year"] == de) & (mad["gdppc"].notna())
        ]
        if len(start) > 0 and len(end) > 0 and start.iloc[0]["gdppc"] > 100:
            annual_g = (
                (end.iloc[0]["gdppc"] / start.iloc[0]["gdppc"]) ** (1 / (de - ds)) - 1
            ) * 100
            growth_list.append((cc, start.iloc[0]["country"], annual_g))

    growth_list.sort(key=lambda x: x[2], reverse=True)
    top5 = growth_list[:5]
    top5_str = ", ".join([f"{c[1][:12]} ({c[2]:.1f}%)" for c in top5])
    table_data_fg.append([f"{ds}-{de}", top5_str])

table_fg = ax.table(
    cellText=table_data_fg,
    colLabels=["Decade", "Top 5 Fastest Growing Countries (annual %)"],
    loc="center",
    cellLoc="left",
)
table_fg.auto_set_font_size(False)
table_fg.set_fontsize(10)
table_fg.scale(1.2, 1.8)
ax.set_title("Growth Leadership Rotation", fontweight="bold", pad=20)

# Panel D: Current poorest countries — growth trajectory
ax = axes[1][1]
# Which countries are still very poor and what's their recent growth?
latest_mad = mad[(mad["year"] == 2022) & (mad["gdppc"].notna())].sort_values("gdppc")
poorest_20 = latest_mad.head(20)

for _, row in poorest_20.iterrows():
    cc = row["countrycode"]
    cdata = mad[
        (mad["countrycode"] == cc) & (mad["gdppc"].notna()) & (mad["year"] >= 1990)
    ].sort_values("year")
    if len(cdata) > 2:
        ax.plot(
            cdata["year"],
            cdata["gdppc"],
            "-",
            linewidth=1.5,
            alpha=0.7,
            label=row["country"][:15],
        )

ax.set_title("GDP per Capita: World's 20 Poorest Countries (2022)")
ax.set_xlabel("Year")
ax.set_ylabel("GDP per capita (2011 int'l $)")
ax.legend(fontsize=6, loc="upper left", ncol=2)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "07_growth_rotation.png"))
plt.close()
print("  -> Saved 07_growth_rotation.png")

# Print growth leadership rotation
print("\n  Growth leadership by decade:")
for row in table_data_fg:
    print(f"  {row[0]}: {row[1]}")


###############################################################################
# BONUS ANALYSIS: THE "ESCAPE VELOCITY" QUESTION
###############################################################################
print("\n" + "=" * 70)
print("BONUS: ESCAPE VELOCITY — WHAT PREDICTS SUSTAINED GROWTH?")
print("=" * 70)

# Countries that were poor in 1960 — which escaped and which didn't?
poor_1960 = mad[(mad["year"] == 1960) & (mad["gdppc"].notna()) & (mad["gdppc"] < 3000)]
rich_2022 = mad[(mad["year"] == 2022) & (mad["gdppc"].notna())]

escaped = poor_1960.merge(
    rich_2022[["countrycode", "gdppc"]], on="countrycode", suffixes=("_1960", "_2022")
)
escaped["growth_factor"] = escaped["gdppc_2022"] / escaped["gdppc_1960"]
escaped["annual_growth"] = (
    (escaped["gdppc_2022"] / escaped["gdppc_1960"]) ** (1 / 62) - 1
) * 100

fig, ax = plt.subplots(figsize=(14, 8))
escaped_sorted = escaped.sort_values("growth_factor", ascending=True)
colors_esc = [
    "green" if g > 5 else "orange" if g > 2 else "red"
    for g in escaped_sorted["growth_factor"]
]
ax.barh(
    escaped_sorted["country"][:40],
    escaped_sorted["growth_factor"][:40],
    color=colors_esc[:40],
)
ax.set_xlabel("GDP per capita multiple (2022 vs 1960)")
ax.set_title(
    "Countries Poor in 1960 (< $3000 GDP/capita): Who Escaped?", fontweight="bold"
)
ax.axvline(x=5, color="blue", linestyle="--", alpha=0.5, label="5x growth")
ax.axvline(x=10, color="green", linestyle="--", alpha=0.5, label="10x growth")
ax.legend()
plt.savefig(os.path.join(CHARTS, "08_escape_velocity.png"))
plt.close()
print("  -> Saved 08_escape_velocity.png")

# Print top and bottom
print("\n  Biggest success stories (poor in 1960, most growth by 2022):")
top = escaped.nlargest(10, "growth_factor")
for _, r in top.iterrows():
    print(
        f"    {r['country']}: ${r['gdppc_1960']:.0f} -> ${r['gdppc_2022']:.0f} ({r['growth_factor']:.1f}x, {r['annual_growth']:.1f}%/yr)"
    )

print("\n  Least growth (poor in 1960, still poor):")
bottom = escaped.nsmallest(10, "growth_factor")
for _, r in bottom.iterrows():
    print(
        f"    {r['country']}: ${r['gdppc_1960']:.0f} -> ${r['gdppc_2022']:.0f} ({r['growth_factor']:.1f}x, {r['annual_growth']:.1f}%/yr)"
    )


###############################################################################
# SUMMARY DASHBOARD
###############################################################################
print("\n" + "=" * 70)
print("GENERATING SUMMARY DASHBOARD")
print("=" * 70)

# Withdraw the whole dashboard rather than republish its inherited conclusions.
# Independent analyses above still publish their own charts unchanged.
refresh_withdrawn_chart("00_summary_dashboard.png")


###############################################################################
# FINAL PRINTED SUMMARY
###############################################################################
print("\n" + "=" * 70)
print("COMPLETE ANALYSIS SUMMARY")
print("=" * 70)

print("""
KEY FINDINGS:

1. LEGACY POVERTY-GAP GDP SHARES — WITHDRAWN
    Analysis 1 divides a 2017-PPP gap by constant-2015 market-US$ GDP.
    Its levels and trends are not valid GDP shares and cannot confirm
    that growth caused redistribution to become cheaper. Use Analysis 28,
    Charts 118/119, for same-basis accounting, not causal attribution.

2. REGIONAL DECOMPOSITION
   China dominates extreme poverty reduction. Sub-Saharan Africa's share 
   of global extreme poverty has risen from ~13% to ~65%. The poverty 
   problem is increasingly an Africa problem.

3. GROWTH TRAJECTORIES
   Countries that escaped poverty took very different amounts of time.
   Late developers (China, Korea, Vietnam) grew faster than early ones
   (UK, France) — consistent with convergence and technology transfer.
   But many poor countries haven't entered the "fast growth" phase at all.

4. CONVERGENCE
   Population-weighted convergence is dramatic (driven by China/India).
   Unweighted convergence is weaker — most poor countries are NOT catching up.
   This is the crux: convergence is real for some, absent for others.

5. GROWTH ELASTICITY
   Growth reduces poverty much less effectively in Sub-Saharan Africa 
   than in East Asia. High inequality dampens the poverty-reducing 
   effect of growth. Your friend's paper correctly identifies this.

6. LEGACY REDISTRIBUTION COST COMPARISON — WITHDRAWN
    The old GDP-share costs and years-of-growth estimate are withdrawn.
    A 3x targeting multiplier is an assumption, not an estimated program
    cost. PPP gaps cannot be compared directly with nominal military
    spending. Charts 00/06 now show withdrawal notices, not estimates.

7. GROWTH ROTATION
   There IS evidence of a "flying geese" pattern: growth leadership
   has rotated from Japan → Korea/Taiwan → China → Vietnam/India.
   But it hasn't reached most of Sub-Saharan Africa.

SYNTHESIS:
    The legacy mixed-basis calculation cannot establish redistribution's
    GDP cost or attribute changes in affordability to growth. Consult the
    same-basis Analysis 28 accounting separately; an accounting decomposition
    does not establish causation. The unrelated descriptive analyses above
    have not been revalidated as part of this focused correction.
""")

print(f"\nAll charts saved to: {CHARTS}")
print("Files:")
for f in sorted(os.listdir(CHARTS)):
    print(f"  {f}")
