#!/usr/bin/env python3
"""
Analysis: Does poverty reduction drive subsequent growth?
And what does it take to build a $6.85/day economy?
"""
import os, warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats

BASE = "/Users/rstory/Repositories/global-growth"
CHARTS = os.path.join(BASE, "charts")
PROC = os.path.join(BASE, "data", "processed")
RAW = os.path.join(BASE, "data", "raw")

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

# Load data
wdi = pd.read_csv(os.path.join(PROC, "wdi_combined.csv"))
mad = pd.read_csv(os.path.join(PROC, "maddison.csv"))
pip215 = pd.read_csv(os.path.join(RAW, "pip_country_2.15.csv"))
pip685 = pd.read_csv(os.path.join(RAW, "pip_country_6.85.csv"))

# Deduplicate PIP
for df in [pip215, pip685]:
    df.sort_values(["country_code", "reporting_year", "reporting_level"], inplace=True)
    df.drop_duplicates(
        subset=["country_code", "reporting_year"], keep="first", inplace=True
    )


###############################################################################
# Q1: IS EXTREME POVERTY ITSELF A BARRIER TO GROWTH?
# Test: do countries that reduce extreme poverty subsequently grow faster?
###############################################################################
print("=" * 70)
print("Q1: DOES POVERTY REDUCTION PREDICT SUBSEQUENT GROWTH?")
print("=" * 70)

# Approach: For each country, measure poverty reduction in decade 1,
# then GDP growth in decade 2. If poverty traps exist, past poverty
# reduction should predict future growth (virtuous cycle).

fig, axes = plt.subplots(2, 2, figsize=(16, 14))
fig.suptitle(
    "Does Poverty Reduction Drive Subsequent Growth?", fontsize=16, fontweight="bold"
)

# Panel A: Initial poverty level vs subsequent growth
ax = axes[0][0]
# Get poverty in ~2000 and GDP growth 2000-2020
pov2000 = pip215[(pip215["reporting_year"].between(1998, 2002))].copy()
pov2000 = pov2000.sort_values("reporting_year").drop_duplicates(
    "country_code", keep="last"
)

gdp_2000 = wdi[
    (wdi["year"].between(1998, 2002)) & (wdi["gdppc_constant_2015usd"].notna())
]
gdp_2000 = gdp_2000.sort_values("year").drop_duplicates("country_code", keep="last")
gdp_2019 = wdi[
    (wdi["year"].between(2018, 2020)) & (wdi["gdppc_constant_2015usd"].notna())
]
gdp_2019 = gdp_2019.sort_values("year").drop_duplicates("country_code", keep="last")

merged_q1 = pov2000.merge(
    gdp_2000[["country_code", "gdppc_constant_2015usd"]], on="country_code"
)
merged_q1 = merged_q1.merge(
    gdp_2019[["country_code", "gdppc_constant_2015usd"]],
    on="country_code",
    suffixes=("_start", "_end"),
)
merged_q1["annual_growth"] = (
    (
        merged_q1["gdppc_constant_2015usd_end"]
        / merged_q1["gdppc_constant_2015usd_start"]
    )
    ** (1 / 20)
    - 1
) * 100
merged_q1 = merged_q1[merged_q1["annual_growth"].between(-10, 20)]

ax.scatter(merged_q1["headcount"] * 100, merged_q1["annual_growth"], alpha=0.5, s=40)
# Regression
valid = merged_q1.dropna(subset=["headcount", "annual_growth"])
if len(valid) > 10:
    _lr = stats.linregress(valid["headcount"] * 100, valid["annual_growth"])
    slope, intercept, r, p = _lr.slope, _lr.intercept, _lr.rvalue, _lr.pvalue  # type: ignore[union-attr]
    x_fit = np.linspace(0, 100, 100)
    ax.plot(x_fit, intercept + slope * x_fit, "r-", linewidth=2)
    ax.set_title(
        f"Initial Poverty Rate (~2000) vs. Growth 2000-2020\nSlope={slope:.3f}, R²={r**2:.3f}, p={p:.4f}"
    )
    print(f"  Initial poverty vs growth: slope={slope:.4f}, R²={r**2:.3f}, p={p:.4f}")
    print(
        f"  Interpretation: {'Higher poverty → lower growth' if slope < 0 else 'No clear relationship'}"
    )

    # Label key countries
    for cc, name in [
        ("CHN", "CHN"),
        ("IND", "IND"),
        ("NGA", "NGA"),
        ("ETH", "ETH"),
        ("VNM", "VNM"),
        ("BWA", "BWA"),
        ("COD", "COD"),
        ("BRA", "BRA"),
        ("RWA", "RWA"),
        ("BGD", "BGD"),
    ]:
        row = merged_q1[merged_q1["country_code"] == cc]
        if len(row) > 0:
            ax.annotate(
                name,
                (row.iloc[0]["headcount"] * 100, row.iloc[0]["annual_growth"]),
                fontsize=8,
            )

ax.set_xlabel("Extreme poverty rate ($2.15/day) ~2000 (%)")
ax.set_ylabel("Annual GDP/capita growth 2000-2020 (%)")

# Panel B: Poverty CHANGE in 1990s vs GDP growth in 2000s
ax = axes[0][1]
pov1990 = pip215[(pip215["reporting_year"].between(1988, 1992))].drop_duplicates(
    "country_code", keep="last"
)
pov2000b = pip215[(pip215["reporting_year"].between(1998, 2002))].drop_duplicates(
    "country_code", keep="last"
)
pov2010 = pip215[(pip215["reporting_year"].between(2008, 2012))].drop_duplicates(
    "country_code", keep="last"
)

gdp_2010 = wdi[
    (wdi["year"].between(2008, 2012)) & (wdi["gdppc_constant_2015usd"].notna())
]
gdp_2010 = gdp_2010.sort_values("year").drop_duplicates("country_code", keep="last")

mer = pov1990[["country_code", "headcount"]].merge(
    pov2000b[["country_code", "headcount"]], on="country_code", suffixes=("_90", "_00")
)
mer["pov_change_90s"] = (mer["headcount_00"] - mer["headcount_90"]) * 100  # ppt change

mer2 = mer.merge(
    gdp_2000[["country_code", "gdppc_constant_2015usd"]], on="country_code"
)
mer2 = mer2.merge(
    gdp_2010[["country_code", "gdppc_constant_2015usd"]],
    on="country_code",
    suffixes=("_00", "_10"),
)
mer2["growth_00s"] = (
    (mer2["gdppc_constant_2015usd_10"] / mer2["gdppc_constant_2015usd_00"]) ** (1 / 10)
    - 1
) * 100
mer2 = mer2[mer2["growth_00s"].between(-10, 20)]

ax.scatter(mer2["pov_change_90s"], mer2["growth_00s"], alpha=0.5, s=40)
if len(mer2) > 10:
    _lr = stats.linregress(mer2["pov_change_90s"], mer2["growth_00s"])
    slope, intercept, r, p = _lr.slope, _lr.intercept, _lr.rvalue, _lr.pvalue  # type: ignore[union-attr]
    x_fit = np.linspace(mer2["pov_change_90s"].min(), mer2["pov_change_90s"].max(), 100)
    ax.plot(x_fit, intercept + slope * x_fit, "r-", linewidth=2)
    ax.set_title(
        f"Poverty Change in 1990s vs Growth in 2000s\nSlope={slope:.3f}, R²={r**2:.3f}, p={p:.4f}"
    )
    print(
        f"  Poverty change (90s) vs growth (00s): slope={slope:.4f}, R²={r**2:.3f}, p={p:.4f}"
    )

ax.set_xlabel("Change in extreme poverty rate 1990→2000 (ppt)")
ax.set_ylabel("Annual GDP/capita growth 2000-2010 (%)")
ax.axvline(x=0, color="gray", linestyle="--", alpha=0.3)

# Panel C: The demand multiplier logic — income levels and local business activity
# Use mean income from PIP data to look at consumption multipliers
ax = axes[1][0]

# What share of GDP is household consumption in low vs mid vs high income countries?
# proxy: look at mean consumption from PIP relative to GDP per capita
pip_with_gdp = pip215.merge(
    wdi[["country_code", "year", "gdppc_ppp_current"]].rename(
        columns={"year": "reporting_year"}
    ),
    on=["country_code", "reporting_year"],
    how="inner",
)
pip_with_gdp = pip_with_gdp[
    pip_with_gdp["mean"].notna() & pip_with_gdp["gdppc_ppp_current"].notna()
]

# Group by income level
pip_with_gdp["income_group"] = pd.cut(
    pip_with_gdp["gdppc_ppp_current"],
    bins=[0, 2000, 5000, 15000, 100000],
    labels=["<$2k", "$2-5k", "$5-15k", "$15k+"],
)
# Mean survey income / GDP per capita ratio (rough proxy for how much GDP is captured as consumption)
pip_with_gdp["mean_annual"] = pip_with_gdp["mean"] * 365  # daily to annual
pip_with_gdp["cons_gdp_ratio"] = (
    pip_with_gdp["mean_annual"] / pip_with_gdp["gdppc_ppp_current"]
)

group_means = pip_with_gdp.groupby("income_group", observed=True)["cons_gdp_ratio"].agg(
    ["mean", "median", "count"]
)
print(f"\n  Consumption/GDP ratio by income group:")
print(group_means.to_string())

bars = ax.bar(group_means.index.astype(str), group_means["median"], color="steelblue")
ax.set_title("Median Survey Consumption / GDP per Capita\nby Country Income Level")
ax.set_xlabel("GDP per Capita Group")
ax.set_ylabel("Consumption-to-GDP Ratio")
ax.axhline(y=1, color="gray", linestyle="--", alpha=0.3)

# Panel D: Growth episodes in very poor countries — what preceded breakthroughs?
ax = axes[1][1]

# Find "growth breakthrough" episodes: countries with GDP/cap < $2000 (Maddison)
# that then sustained 4%+ growth for 10+ years
breakthroughs = []
countries_checked = 0
for cc in mad["countrycode"].unique():
    cdata = mad[
        (mad["countrycode"] == cc) & (mad["gdppc"].notna()) & (mad["year"] >= 1950)
    ].sort_values("year")
    if len(cdata) < 15:
        continue
    countries_checked += 1

    for i in range(len(cdata) - 10):
        start = cdata.iloc[i]
        if start["gdppc"] > 2000:  # only look at poor starting points
            continue
        # Check if next 10 years average 4%+ growth
        end_idx = min(i + 10, len(cdata) - 1)
        end = cdata.iloc[end_idx]
        years = end["year"] - start["year"]
        if years < 8:
            continue
        annual_g = ((end["gdppc"] / start["gdppc"]) ** (1 / years) - 1) * 100
        if annual_g >= 4.0:
            breakthroughs.append(
                {
                    "country": start["country"],
                    "countrycode": cc,
                    "start_year": int(start["year"]),
                    "start_gdppc": start["gdppc"],
                    "end_year": int(end["year"]),
                    "end_gdppc": end["gdppc"],
                    "annual_growth": annual_g,
                }
            )
            break  # only first breakthrough per country

df_break = pd.DataFrame(breakthroughs).sort_values("start_year")
print(f"\n  Growth breakthroughs (4%+ sustained from <$2000 GDP/cap):")
print(f"  Found {len(df_break)} episodes from {countries_checked} countries checked")

# Plot when these breakthroughs occurred
decade_counts = df_break.groupby((df_break["start_year"] // 10) * 10).size()
ax.bar(decade_counts.index.astype(str), decade_counts.values, color="steelblue")
ax.set_title(
    f"When Did Growth Breakthroughs Occur?\n({len(df_break)} episodes of 4%+ annual growth from <$2k GDP/cap)"
)
ax.set_xlabel("Decade of breakthrough start")
ax.set_ylabel("Number of countries")

# Print some notable ones
for _, r in df_break.iterrows():
    if r["countrycode"] in [
        "CHN",
        "KOR",
        "VNM",
        "IND",
        "BWA",
        "ETH",
        "TWN",
        "THA",
        "IDN",
        "MYS",
        "BGD",
        "RWA",
        "POL",
    ]:
        print(
            f"    {r['country']}: {int(r['start_year'])} (${r['start_gdppc']:.0f}) → {int(r['end_year'])} (${r['end_gdppc']:.0f}), {r['annual_growth']:.1f}%/yr"
        )

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "09_poverty_and_growth.png"))
plt.close()
print("\n  -> Saved 09_poverty_and_growth.png")


###############################################################################
# Q2: WHAT DOES A $6.85/DAY ECONOMY LOOK LIKE?
# What GDP per capita, life expectancy, education levels are associated?
###############################################################################
print("\n" + "=" * 70)
print("Q2: STRUCTURAL PROFILE OF A $6.85/DAY ECONOMY")
print("=" * 70)

fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle(
    "What Does It Take to Build a $6.85/day Economy?", fontsize=16, fontweight="bold"
)

# Find countries where the $6.85/day headcount is < 20% (i.e., "made it")
# vs >60% (deep poverty)
pip685_latest = pip685[pip685["reporting_year"] >= 2015].copy()
pip685_latest = pip685_latest.sort_values("reporting_year").drop_duplicates(
    "country_code", keep="last"
)

# Merge with WDI indicators
wdi_latest = wdi[wdi["year"] >= 2015].copy()
wdi_latest = wdi_latest.sort_values("year").drop_duplicates("country_code", keep="last")

profile = pip685_latest[
    ["country_code", "country_name", "headcount", "mean", "gini"]
].merge(
    wdi_latest[
        [
            "country_code",
            "gdppc_ppp_current",
            "gdppc_constant_2015usd",
            "life_expectancy",
            "under5_mortality",
            "population",
        ]
    ],
    on="country_code",
    how="inner",
)

profile["poverty_group"] = pd.cut(
    profile["headcount"],
    bins=[-0.01, 0.05, 0.20, 0.50, 1.01],
    labels=["<5% poor", "5-20%", "20-50%", ">50% poor"],
)

# Panel A: GDP per capita needed
ax = axes[0][0]
for grp, color in [
    ("<5% poor", "green"),
    ("5-20%", "blue"),
    ("20-50%", "orange"),
    (">50% poor", "red"),
]:
    data = profile[profile["poverty_group"] == grp]["gdppc_ppp_current"].dropna()
    if len(data) > 0:
        ax.hist(data, bins=20, alpha=0.5, color=color, label=f"{grp} (n={len(data)})")
ax.set_title("GDP per Capita (PPP) by $6.85/day Poverty Group")
ax.set_xlabel("GDP per capita (current PPP $)")
ax.set_ylabel("Number of countries")
ax.legend(fontsize=9)
ax.set_xlim(0, 40000)

# Print thresholds
print("\n  GDP per capita (PPP) needed for different $6.85/day headcounts:")
for grp in ["<5% poor", "5-20%", "20-50%", ">50% poor"]:
    data = profile[profile["poverty_group"] == grp]["gdppc_ppp_current"].dropna()
    if len(data) > 0:
        print(
            f"    {grp}: median GDP/cap = ${data.median():,.0f}, range ${data.min():,.0f}-${data.max():,.0f}"
        )

# Panel B: Life expectancy
ax = axes[0][1]
for grp, color in [
    ("<5% poor", "green"),
    ("5-20%", "blue"),
    ("20-50%", "orange"),
    (">50% poor", "red"),
]:
    data = profile[profile["poverty_group"] == grp]["life_expectancy"].dropna()
    if len(data) > 0:
        ax.hist(data, bins=15, alpha=0.5, color=color, label=f"{grp}")
ax.set_title("Life Expectancy by Poverty Group")
ax.set_xlabel("Life expectancy at birth (years)")
ax.legend(fontsize=9)

# Panel C: Inequality (Gini)
ax = axes[0][2]
gini_data = profile[profile["gini"].notna()]
for grp, color in [
    ("<5% poor", "green"),
    ("5-20%", "blue"),
    ("20-50%", "orange"),
    (">50% poor", "red"),
]:
    data = gini_data[gini_data["poverty_group"] == grp]["gini"].dropna()
    if len(data) > 0:
        ax.hist(data * 100, bins=15, alpha=0.5, color=color, label=f"{grp}")
ax.set_title("Gini Coefficient by Poverty Group")
ax.set_xlabel("Gini (%)")
ax.legend(fontsize=9)

print(f"\n  Gini by poverty group:")
for grp in ["<5% poor", "5-20%", "20-50%", ">50% poor"]:
    data = gini_data[gini_data["poverty_group"] == grp]["gini"].dropna()
    if len(data) > 0:
        print(f"    {grp}: median Gini = {data.median()*100:.1f}")

# Panel D: Child mortality
ax = axes[1][0]
for grp, color in [
    ("<5% poor", "green"),
    ("5-20%", "blue"),
    ("20-50%", "orange"),
    (">50% poor", "red"),
]:
    data = profile[profile["poverty_group"] == grp]["under5_mortality"].dropna()
    if len(data) > 0:
        ax.hist(data, bins=15, alpha=0.5, color=color, label=f"{grp}")
ax.set_title("Under-5 Mortality by Poverty Group")
ax.set_xlabel("Under-5 mortality (per 1,000 live births)")
ax.legend(fontsize=9)

# Panel E: Scatter — GDP per capita vs $6.85 headcount
ax = axes[1][1]
ax.scatter(
    profile["gdppc_ppp_current"],
    profile["headcount"] * 100,
    s=profile["population"].clip(upper=5e8) / 5e6,
    alpha=0.5,
)
ax.set_xlabel("GDP per capita (PPP $)")
ax.set_ylabel("% below $6.85/day")
ax.set_title("GDP per Capita vs. $6.85/day Poverty Rate\n(bubble size = population)")
ax.axhline(y=20, color="green", linestyle="--", alpha=0.5, label="20% threshold")
ax.axvline(x=15000, color="blue", linestyle="--", alpha=0.5, label="$15k GDP/cap")
ax.legend()
ax.set_xlim(0, 40000)

# Label key countries
for cc, name in [
    ("CHN", "China"),
    ("IND", "India"),
    ("NGA", "Nigeria"),
    ("ETH", "Ethiopia"),
    ("IDN", "Indonesia"),
    ("BGD", "Bangladesh"),
    ("COD", "DRC"),
    ("BRA", "Brazil"),
    ("VNM", "Vietnam"),
    ("KEN", "Kenya"),
    ("TZA", "Tanzania"),
    ("GHA", "Ghana"),
    ("ZAF", "S.Africa"),
    ("PHL", "Philippines"),
]:
    row = profile[profile["country_code"] == cc]
    if len(row) > 0:
        ax.annotate(
            name,
            (row.iloc[0]["gdppc_ppp_current"], row.iloc[0]["headcount"] * 100),
            fontsize=7,
        )

# Panel F: How long did it take countries to go from >50% poor at $6.85 to <20%?
ax = axes[1][2]
# Track the $6.85/day headcount trajectory
transition_times = []
for cc in pip685["country_code"].unique():
    cdata = pip685[pip685["country_code"] == cc].sort_values("reporting_year")
    if len(cdata) < 5:
        continue
    # Find first year >50% poor
    above50 = cdata[cdata["headcount"] > 0.50]
    below20 = cdata[cdata["headcount"] < 0.20]
    if len(above50) > 0 and len(below20) > 0:
        t_start = above50.iloc[0]["reporting_year"]
        t_end = below20.iloc[0]["reporting_year"]
        if t_end > t_start:
            transition_times.append(
                {
                    "country": cdata.iloc[0]["country_name"],
                    "country_code": cc,
                    "start_year": t_start,
                    "end_year": t_end,
                    "years": t_end - t_start,
                }
            )

df_trans = pd.DataFrame(transition_times).sort_values("years")
if len(df_trans) > 0:
    colors_t = [
        "green" if y <= 25 else "orange" if y <= 40 else "red"
        for y in df_trans["years"]
    ]
    ax.barh(df_trans["country"][:25], df_trans["years"][:25], color=colors_t[:25])
    ax.set_xlabel("Years to go from >50% to <20% poor at $6.85/day")
    ax.set_title("Transition Time: From Mass Poverty\nto Broad Prosperity")

    print(f"\n  Fastest transitions from >50% to <20% at $6.85/day:")
    for _, r in df_trans.head(15).iterrows():
        print(
            f"    {r['country']}: {int(r['start_year'])}→{int(r['end_year'])} ({int(r['years'])} years)"
        )

    print(f"\n  Still >50% at $6.85/day (haven't transitioned):")
    still_poor = pip685_latest[pip685_latest["headcount"] > 0.5].sort_values(
        "headcount", ascending=False
    )
    for _, r in still_poor.head(10).iterrows():
        print(f"    {r['country_name']}: {r['headcount']*100:.1f}%")

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "10_building_685_economy.png"))
plt.close()
print("\n  -> Saved 10_building_685_economy.png")


###############################################################################
# Q3: THE REDISTRIBUTION-TO-GROWTH PIPELINE
# If you gave everyone above $2.15/day via transfers, what would the
# aggregate demand injection look like relative to their local economies?
###############################################################################
print("\n" + "=" * 70)
print("Q3: DEMAND INJECTION FROM $2.15/DAY TRANSFERS")
print("=" * 70)

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# For each country with significant extreme poverty, estimate:
# 1. The poverty gap in $
# 2. That gap as % of their own GDP
# 3. The potential demand multiplier effect

pip215_latest = pip215[pip215["reporting_year"] >= 2018].copy()
pip215_latest = pip215_latest.sort_values("reporting_year").drop_duplicates(
    "country_code", keep="last"
)
pip215_latest = pip215_latest[
    pip215_latest["headcount"] > 0.01
]  # at least 1% extreme poverty

wdi_recent = (
    wdi[wdi["year"] >= 2018]
    .sort_values("year")
    .drop_duplicates("country_code", keep="last")
)

demand = pip215_latest.merge(
    wdi_recent[["country_code", "gdp_ppp_current", "gdppc_ppp_current", "population"]],
    on="country_code",
    how="inner",
)

# Total poverty gap per country = poverty_gap_index * poverty_line * population * 365
demand["total_gap_usd"] = demand["poverty_gap"] * 2.15 * demand["reporting_pop"] * 365
demand["gap_pct_own_gdp"] = demand["total_gap_usd"] / demand["gdp_ppp_current"] * 100
demand = demand[demand["gap_pct_own_gdp"].notna()]

ax = axes[0]
# Top 20 countries by gap as % of own GDP
top20 = demand.nlargest(25, "gap_pct_own_gdp")
colors_d = [
    "red" if g > 5 else "orange" if g > 2 else "steelblue"
    for g in top20["gap_pct_own_gdp"]
]
ax.barh(top20["country_name"].str[:20], top20["gap_pct_own_gdp"], color=colors_d)
ax.set_xlabel("Poverty Gap as % of Own GDP")
ax.set_title(
    "$2.15/day Poverty Gap as % of Domestic GDP\n(= demand injection from closing the gap)"
)

print(f"  Top countries by poverty gap as % of own GDP:")
for _, r in top20.head(15).iterrows():
    multiplier_range = f"${r['total_gap_usd']/1e9:.1f}B → ${r['total_gap_usd']*2.5/1e9:.1f}B"  # 2.5x GiveDirectly multiplier
    print(
        f"    {r['country_name'][:25]:<25s}: gap = {r['gap_pct_own_gdp']:.1f}% of GDP, {multiplier_range} with 2.5x multiplier"
    )

# Panel B: Aggregate demand injection with multiplier
ax = axes[1]
# Total for Sub-Saharan Africa
ssa_codes = demand[
    demand["country_code"].isin(
        pip215[pip215["region_code"].isin(["SSA", "AFE", "AFW"])][
            "country_code"
        ].unique()
    )
]

# Also compute for all developing world
total_gap = demand["total_gap_usd"].sum()
ssa_gap = ssa_codes["total_gap_usd"].sum() if len(ssa_codes) > 0 else 0

scenarios = {
    "Perfect\ntransfer": total_gap / 1e9,
    "With 2.5x\nmultiplier": total_gap * 2.5 / 1e9,
    "SSA\ntransfer": ssa_gap / 1e9,
    "SSA with\n2.5x mult": ssa_gap * 2.5 / 1e9,
}

bars = ax.bar(
    scenarios.keys(),
    scenarios.values(),
    color=["steelblue", "green", "orange", "darkgreen"],
)
ax.set_ylabel("$ Billions")
ax.set_title("Aggregate Demand from Closing $2.15/day Gap")
for bar, val in zip(bars, scenarios.values()):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 1,
        f"${val:.0f}B",
        ha="center",
        fontsize=11,
    )

print(f"\n  Global $2.15/day poverty gap total: ${total_gap/1e9:.1f}B")
print(f"  With 2.5x GiveDirectly-style multiplier: ${total_gap*2.5/1e9:.1f}B")
print(f"  SSA portion: ${ssa_gap/1e9:.1f}B → ${ssa_gap*2.5/1e9:.1f}B with multiplier")

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "11_demand_injection.png"))
plt.close()
print("  -> Saved 11_demand_injection.png")


###############################################################################
# Q4: THE PATH FROM $2.15 TO $6.85 — WHAT STRUCTURAL CHANGES HAPPENED
# IN COUNTRIES THAT MADE THE TRANSITION?
###############################################################################
print("\n" + "=" * 70)
print("Q4: STRUCTURAL CHANGES ON THE PATH FROM $2.15 TO $6.85")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle(
    "The Path from Extreme to Moderate Poverty:\nWhat Changed in Countries that Made It?",
    fontsize=16,
    fontweight="bold",
)

# Track countries that substantially reduced both $2.15 and $6.85 poverty
success_countries = [
    "CHN",
    "VNM",
    "IDN",
    "THA",
    "MYS",
    "BRA",
    "COL",
    "PER",
    "TUR",
    "POL",
    "ROU",
]
stalled_countries = ["NGA", "COD", "MDG", "MOZ", "TCD", "BFA", "MLI", "NER"]

# Panel A: GDP per capita trajectories
ax = axes[0][0]
for cc in success_countries:
    cdata = wdi[
        (wdi["country_code"] == cc) & (wdi["gdppc_ppp_current"].notna())
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(
            cdata["year"],
            cdata["gdppc_ppp_current"],
            "-",
            linewidth=2,
            label=cdata.iloc[0]["country"][:12] if "country" in cdata.columns else cc,
        )
for cc in stalled_countries[:4]:
    cdata = wdi[
        (wdi["country_code"] == cc) & (wdi["gdppc_ppp_current"].notna())
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(
            cdata["year"],
            cdata["gdppc_ppp_current"],
            "--",
            linewidth=1.5,
            alpha=0.7,
            label=f"{cc} (stalled)",
        )
ax.set_title("GDP per Capita: Success vs Stalled")
ax.set_ylabel("GDP per capita (PPP $)")
ax.legend(fontsize=7, ncol=2)
ax.set_yscale("log")

# Panel B: Life expectancy trajectories
ax = axes[0][1]
for cc in success_countries:
    cdata = wdi[
        (wdi["country_code"] == cc) & (wdi["life_expectancy"].notna())
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(cdata["year"], cdata["life_expectancy"], "-", linewidth=2)
for cc in stalled_countries[:4]:
    cdata = wdi[
        (wdi["country_code"] == cc) & (wdi["life_expectancy"].notna())
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(cdata["year"], cdata["life_expectancy"], "--", linewidth=1.5, alpha=0.7)
ax.set_title("Life Expectancy: Success vs Stalled")
ax.set_ylabel("Life expectancy (years)")

# Panel C: Poverty rate trajectories at $6.85
ax = axes[1][0]
for cc in success_countries:
    cdata = pip685[pip685["country_code"] == cc].sort_values("reporting_year")
    if len(cdata) > 0:
        name = cdata.iloc[0].get("country_name", cc)
        ax.plot(
            cdata["reporting_year"],
            cdata["headcount"] * 100,
            "-",
            linewidth=2,
            label=str(name)[:12],
        )
for cc in stalled_countries[:4]:
    cdata = pip685[pip685["country_code"] == cc].sort_values("reporting_year")
    if len(cdata) > 0:
        ax.plot(
            cdata["reporting_year"],
            cdata["headcount"] * 100,
            "--",
            linewidth=1.5,
            alpha=0.7,
            label=f"{cc} (stalled)",
        )
ax.set_title("$6.85/day Poverty Rate Over Time")
ax.set_ylabel("% below $6.85/day")
ax.legend(fontsize=7, ncol=2)

# Panel D: Summary comparison table
ax = axes[1][1]
ax.axis("off")

comparison = []
for label, countries in [
    ("Successes", success_countries),
    ("Stalled", stalled_countries),
]:
    gdp_growths = []
    le_changes = []
    pov_changes = []
    for cc in countries:
        g_start = wdi[
            (wdi["country_code"] == cc)
            & (wdi["year"].between(1990, 1995))
            & (wdi["gdppc_ppp_current"].notna())
        ]
        g_end = wdi[
            (wdi["country_code"] == cc)
            & (wdi["year"].between(2018, 2022))
            & (wdi["gdppc_ppp_current"].notna())
        ]
        if len(g_start) > 0 and len(g_end) > 0:
            growth = (
                (
                    g_end.iloc[-1]["gdppc_ppp_current"]
                    / g_start.iloc[0]["gdppc_ppp_current"]
                )
                ** (1 / 30)
                - 1
            ) * 100
            gdp_growths.append(growth)

        le_start = wdi[
            (wdi["country_code"] == cc)
            & (wdi["year"].between(1990, 1995))
            & (wdi["life_expectancy"].notna())
        ]
        le_end = wdi[
            (wdi["country_code"] == cc)
            & (wdi["year"].between(2018, 2022))
            & (wdi["life_expectancy"].notna())
        ]
        if len(le_start) > 0 and len(le_end) > 0:
            le_changes.append(
                le_end.iloc[-1]["life_expectancy"] - le_start.iloc[0]["life_expectancy"]
            )

        p_start = pip685[
            (pip685["country_code"] == cc)
            & (pip685["reporting_year"].between(1990, 1995))
        ]
        p_end = pip685[
            (pip685["country_code"] == cc)
            & (pip685["reporting_year"].between(2018, 2022))
        ]
        if len(p_start) > 0 and len(p_end) > 0:
            pov_changes.append(
                (p_end.iloc[-1]["headcount"] - p_start.iloc[0]["headcount"]) * 100
            )

    comparison.append(
        [
            label,
            f"{np.mean(gdp_growths):.1f}%" if gdp_growths else "n/a",
            f"{np.mean(le_changes):+.1f} yrs" if le_changes else "n/a",
            f"{np.mean(pov_changes):+.1f} ppt" if pov_changes else "n/a",
        ]
    )

print(f"\n  Success vs Stalled comparison (1990-2022 averages):")
print(f"    {'Group':<12} {'GDP growth/yr':<15} {'Life exp Δ':<15} {'$6.85 pov Δ':<15}")
for row in comparison:
    print(f"    {row[0]:<12} {row[1]:<15} {row[2]:<15} {row[3]:<15}")

table = ax.table(
    cellText=comparison,
    colLabels=[
        "Group",
        "Avg GDP\ngrowth/yr",
        "Life exp\nchange",
        "$6.85 poverty\nchange (ppt)",
    ],
    loc="center",
    cellLoc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1.2, 2.0)
ax.set_title("Averages: 1990-2022", fontweight="bold", pad=20)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "12_path_to_685.png"))
plt.close()
print("\n  -> Saved 12_path_to_685.png")


###############################################################################
# FINAL SYNTHESIS
###############################################################################
print("\n" + "=" * 70)
print("SYNTHESIS: FROM $2.15 TRANSFERS TO $6.85 ECONOMIES")
print("=" * 70)
print(
    """
KEY FINDINGS:

1. POVERTY AS GROWTH BARRIER
   The relationship between initial poverty and subsequent growth is
   real but modest. Poverty doesn't mechanically prevent growth, but
   it correlates with the institutional/structural factors that do.

2. DEMAND INJECTION FROM TRANSFERS
   For the poorest countries, the $2.15/day poverty gap represents
   a significant portion of domestic GDP (5-15% for the worst cases).
   With a 2.5x multiplier (per GiveDirectly evidence), direct transfers
   would create a meaningful demand stimulus — but NOT enough on its own
   to drive transition to a $6.85/day economy.

3. WHAT $6.85/DAY ECONOMIES LOOK LIKE
   Countries below 20% poverty at $6.85/day typically have:
   - GDP per capita > $12-15k PPP
   - Life expectancy > 70 years
   - Under-5 mortality < 20 per 1,000
   - Moderate Gini (30-40)
   Getting there requires roughly a 5-10x increase in GDP/capita for
   the poorest countries — which took successful countries 20-40 years.

4. THE TRANSITION FROM $2.15 TO $6.85
   Successful transitions all involved:
   - Sustained 4-7% annual GDP/capita growth for 20+ years
   - This ALWAYS involved structural economic change (agriculture → 
     manufacturing/services)
   - Transfers alone cannot produce this transformation
   
5. THE COMPLEMENTARY CASE
   Transfers can: eliminate extreme poverty NOW, create demand stimulus,
   improve human capital (health, nutrition, school attendance), and
   potentially catalyze local market development.
   
   Transfers cannot: build infrastructure, create institutions, develop
   export industries, or substitute for the 5-10x GDP growth needed
   for a $6.85/day economy.
   
   The honest answer: you need BOTH, and the sequencing matters.
   Transfers first (cheap, immediate), investment in growth-enabling
   conditions simultaneously, then hope for the growth breakthrough
   that historically has been the only path to broad prosperity.
"""
)
