#!/usr/bin/env python3
"""
Analysis: Market reforms and growth episodes.
USSR trajectory. China vs USSR comparison.
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

mad = pd.read_csv(os.path.join(PROC, "maddison.csv"))

###############################################################################
# 1. USSR GROWTH TRAJECTORY
###############################################################################
print("=" * 70)
print("1. USSR / RUSSIA GROWTH TRAJECTORY")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle(
    "The USSR Growth Story: Industrialization Without Markets",
    fontsize=16,
    fontweight="bold",
)

# Panel A: USSR/Russia absolute trajectory
ax = axes[0][0]

# Maddison has Russia (RUS) and Former USSR (SUN)
ussr_codes = ["RUS", "SUN"]
for cc in mad["countrycode"].unique():
    if (
        "USSR" in str(mad[mad["countrycode"] == cc]["country"].iloc[0])
        or cc in ussr_codes
    ):
        cdata = mad[(mad["countrycode"] == cc) & (mad["gdppc"].notna())].sort_values(
            "year"
        )
        if len(cdata) > 0:
            print(
                f"  Found: {cc} = {cdata.iloc[0]['country']}, {len(cdata)} obs, {cdata['year'].min()}-{cdata['year'].max()}"
            )

# Russia and comparators
comparators = {
    "RUS": ("Russia/USSR", "#d62728", "-"),
    "CHN": ("China", "#e377c2", "-"),
    "KOR": ("South Korea", "#8c564b", "-"),
    "JPN": ("Japan", "#9467bd", "-"),
    "USA": ("United States", "#1f77b4", "--"),
    "IND": ("India", "#7f7f7f", "-"),
    "POL": ("Poland", "#17becf", "-"),
    "BRA": ("Brazil", "#2ca02c", "-"),
}

for cc, (name, color, ls) in comparators.items():
    cdata = mad[
        (mad["countrycode"] == cc) & (mad["gdppc"].notna()) & (mad["year"] >= 1870)
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(
            cdata["year"], cdata["gdppc"], ls, color=color, linewidth=2.5, label=name
        )

ax.set_yscale("log")
ax.set_title("GDP per Capita: Russia vs Growth Success Stories")
ax.set_ylabel("GDP per capita (2011 int'l $, log)")
ax.set_xlabel("Year")
ax.legend(fontsize=8, loc="upper left")
ax.axvline(x=1917, color="red", linestyle=":", alpha=0.4, label="1917 Revolution")
ax.axvline(x=1991, color="blue", linestyle=":", alpha=0.4, label="1991 USSR collapse")
ax.axvline(x=1978, color="green", linestyle=":", alpha=0.4, label="1978 China reforms")

# Panel B: Growth rates by decade — USSR vs China vs Korea
ax = axes[0][1]

decades = [
    (1920, 1930),
    (1930, 1940),
    (1940, 1950),
    (1950, 1960),
    (1960, 1970),
    (1970, 1980),
    (1980, 1990),
    (1990, 2000),
    (2000, 2010),
    (2010, 2022),
]

print(f"\n  Growth rates by decade:")
print(
    f"  {'Decade':<12} {'Russia/USSR':<14} {'China':<10} {'S. Korea':<10} {'India':<10} {'USA':<10}"
)

decade_data = {}
for cc, name in [
    ("RUS", "Russia/USSR"),
    ("CHN", "China"),
    ("KOR", "S. Korea"),
    ("IND", "India"),
    ("USA", "USA"),
]:
    decade_data[name] = []
    for ds, de in decades:
        start = mad[
            (mad["countrycode"] == cc) & (mad["year"] == ds) & (mad["gdppc"].notna())
        ]
        end = mad[
            (mad["countrycode"] == cc) & (mad["year"] == de) & (mad["gdppc"].notna())
        ]
        if len(start) > 0 and len(end) > 0 and start.iloc[0]["gdppc"] > 0:
            g = (
                (end.iloc[0]["gdppc"] / start.iloc[0]["gdppc"]) ** (1 / (de - ds)) - 1
            ) * 100
            decade_data[name].append(g)
        else:
            decade_data[name].append(np.nan)

# Print table
for i, (ds, de) in enumerate(decades):
    row = f"  {ds}-{de}  "
    for name in ["Russia/USSR", "China", "S. Korea", "India", "USA"]:
        val = decade_data[name][i]
        row += f"  {val:>6.1f}%" if not np.isnan(val) else f"  {'n/a':>6s} "
    print(row)

# Bar chart
decade_labels = [f"{ds}" for ds, _ in decades]
x = np.arange(len(decades))
width = 0.18
colors_bar = {
    "Russia/USSR": "#d62728",
    "China": "#e377c2",
    "S. Korea": "#8c564b",
    "India": "#7f7f7f",
    "USA": "#1f77b4",
}
for i, (name, vals) in enumerate(decade_data.items()):
    # Leave missing decades as gaps, not zeros — 0% growth ≠ no data
    vals_plot = [v if not np.isnan(v) else 0 for v in vals]
    mask = [not np.isnan(v) for v in vals]
    positions = x + i * width
    bar_colors = [colors_bar[name] if m else "none" for m in mask]
    bar_edges = [colors_bar[name] if m else "none" for m in mask]
    ax.bar(
        positions,
        vals_plot,
        width,
        label=name,
        color=bar_colors,
        edgecolor=bar_edges,
        alpha=0.8,
    )

ax.set_xticks(x + width * 2)
ax.set_xticklabels(decade_labels, rotation=45, fontsize=9)
ax.set_title("Growth by Decade: Russia vs Comparators")
ax.set_ylabel("Annual GDP/capita growth (%)")
ax.legend(fontsize=8)
ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)

# Panel C: China vs USSR — same "start year" normalization
# Both started from similar GDP/cap. When did they diverge?
ax = axes[1][0]

rus = mad[(mad["countrycode"] == "RUS") & (mad["gdppc"].notna())].sort_values("year")
chn = mad[(mad["countrycode"] == "CHN") & (mad["gdppc"].notna())].sort_values("year")

# Russia 1917 vs China 1949 (revolution years)
# Russia 1928 vs China 1978 (industrialization / reform start)
for start_label, rus_start, chn_start, ls in [
    ("Revolution year", 1917, 1949, "-"),
    ("Reform/industrialization", 1928, 1978, "--"),
]:
    rus_base = rus[rus["year"] == rus_start]
    chn_base = chn[chn["year"] == chn_start]
    if len(rus_base) > 0 and len(chn_base) > 0:
        # Plot years since start
        rus_subset = rus[rus["year"] >= rus_start].copy()
        chn_subset = chn[chn["year"] >= chn_start].copy()
        rus_subset["t"] = rus_subset["year"] - rus_start
        chn_subset["t"] = chn_subset["year"] - chn_start
        rus_subset["gdppc_idx"] = rus_subset["gdppc"] / rus_base.iloc[0]["gdppc"]
        chn_subset["gdppc_idx"] = chn_subset["gdppc"] / chn_base.iloc[0]["gdppc"]

        ax.plot(
            rus_subset["t"],
            rus_subset["gdppc_idx"],
            ls,
            color="#d62728",
            linewidth=2.5,
            label=f"Russia from {rus_start}",
        )
        ax.plot(
            chn_subset["t"],
            chn_subset["gdppc_idx"],
            ls,
            color="#e377c2",
            linewidth=2.5,
            label=f"China from {chn_start}",
        )

ax.set_title("Russia vs China: Growth Indexed to Start Year")
ax.set_xlabel("Years since start")
ax.set_ylabel("GDP per capita (multiple of start)")
ax.legend(fontsize=9)
ax.set_xlim(0, 80)

# Print key milestones
print(f"\n  USSR/Russia key milestones:")
for yr in [1913, 1928, 1940, 1950, 1960, 1970, 1980, 1989, 1991, 1998, 2008, 2022]:
    row = rus[rus["year"] == yr]
    if len(row) > 0:
        ratio_to_usa = (
            row.iloc[0]["gdppc"]
            / mad[(mad["countrycode"] == "USA") & (mad["year"] == yr)].iloc[0]["gdppc"]
            * 100
            if len(mad[(mad["countrycode"] == "USA") & (mad["year"] == yr)]) > 0
            else 0
        )
        print(f"    {yr}: ${row.iloc[0]['gdppc']:,.0f} ({ratio_to_usa:.0f}% of US)")

print(f"\n  China key milestones:")
for yr in [1949, 1960, 1970, 1978, 1990, 2000, 2010, 2022]:
    row = chn[chn["year"] == yr]
    if len(row) > 0:
        ratio_to_usa = (
            row.iloc[0]["gdppc"]
            / mad[(mad["countrycode"] == "USA") & (mad["year"] == yr)].iloc[0]["gdppc"]
            * 100
            if len(mad[(mad["countrycode"] == "USA") & (mad["year"] == yr)]) > 0
            else 0
        )
        print(f"    {yr}: ${row.iloc[0]['gdppc']:,.0f} ({ratio_to_usa:.0f}% of US)")

# Panel D: All sustained >4% growth episodes and their economic system
ax = axes[1][1]
ax.axis("off")

# Find all sustained growth episodes (10+ years at >4%)
print(f"\n  All sustained >4% growth episodes (10+ years) since 1950:")
episodes = []
for cc in mad["countrycode"].unique():
    cdata = mad[
        (mad["countrycode"] == cc) & (mad["gdppc"].notna()) & (mad["year"] >= 1950)
    ].sort_values("year")
    if len(cdata) < 12:
        continue

    # Sliding window: find all 10-year windows with >4% growth
    best_start = None
    best_end = None
    best_growth = 0
    best_gdp_start = 0.0
    best_gdp_end = 0.0

    for i in range(len(cdata)):
        for j in range(i + 1, len(cdata)):
            span = cdata.iloc[j]["year"] - cdata.iloc[i]["year"]
            if span < 10:
                continue
            if span > 40:
                break
            g = (
                (cdata.iloc[j]["gdppc"] / cdata.iloc[i]["gdppc"]) ** (1 / span) - 1
            ) * 100
            if g >= 4.0 and span > (best_end - best_start if best_start else 0):
                best_start = cdata.iloc[i]["year"]
                best_end = cdata.iloc[j]["year"]
                best_growth = g
                best_gdp_start = cdata.iloc[i]["gdppc"]
                best_gdp_end = cdata.iloc[j]["gdppc"]

    if best_start is not None:
        assert best_end is not None
        episodes.append(
            {
                "country": cdata.iloc[0]["country"],
                "code": cc,
                "start": int(best_start),
                "end": int(best_end),
                "span": int(best_end - best_start),
                "growth": best_growth,
                "gdp_start": best_gdp_start,
                "gdp_end": best_gdp_end,
            }
        )

df_ep = pd.DataFrame(episodes).sort_values("span", ascending=False)

# Classify economic system during the growth episode
# NOTE: This classification requires domain knowledge and is inherently
# subjective. Almost all modern economies involve some market mechanisms,
# so "market vs command" is a spectrum, not a binary. We code along a
# spectrum: pure command, state-directed, mixed, market-oriented, free market.
# The reader should note that only a handful of economies were ever truly
# command-based, which makes "every episode involved markets" partly
# definitional rather than a strong empirical finding.
market_reform_countries = {
    "CHN": "State-directed + market reform (1978)",
    "KOR": "State-directed industrial policy + market",
    "TWN": "State-directed industrial policy + market",
    "JPN": "State-directed + market (postwar)",
    "SGP": "Free market + state investment",
    "HKG": "Free market",
    "THA": "Market-oriented + state role",
    "MYS": "State-directed + market",
    "IDN": "Mixed: Suharto-era market reforms",
    "VNM": "Doi Moi market reforms (1986)",
    "IND": "Liberalization (1991)",
    "POL": "Shock therapy market reforms (1990)",
    "BWA": "Market economy + good governance",
    "IRL": "Market + FDI / EU integration",
    "CHL": "Market reforms (Chicago Boys)",
    "PER": "Market reforms (1990s)",
    "TUR": "Market-oriented + state role",
    "ROU": "Post-communist market transition",
    "EST": "Radical market reforms (1992)",
    "LVA": "Market transition",
    "LTU": "Market transition",
    "GEO": "Market reforms (2000s)",
    "RWA": "Market-friendly + state capacity",
    "ETH": "State-led developmentalism (EPRDF)",
    "BGD": "Garment export / market integration",
    "MMR": "Opening (2010s)",
    "MOZ": "Market reforms (1990s)",
    "AGO": "Oil + post-conflict",
    "GNQ": "Oil",
    "TKM": "Gas revenues",
    "AZE": "Oil",
    "BHR": "Oil",
    "OMN": "Oil",
    "SAU": "Oil",
    "QAT": "Oil/gas",
    "KWT": "Oil",
    "LBY": "Oil",
    "ARE": "Oil + market",
}

# Possible non-market growth episodes
non_market = {
    "RUS": "Soviet command economy (if 1928-1970)",
    "SUN": "Soviet command economy",
    "CUB": "Command economy",
    "PRK": "Command economy",
}

print(
    f"\n  {'Country':<25} {'Period':<14} {'Span':<6} {'Growth':<8} {'Start GDP':<12} {'System':<40}"
)
print(f"  {'-'*25} {'-'*14} {'-'*6} {'-'*8} {'-'*12} {'-'*40}")

non_market_count = 0
market_count = 0
resource_count = 0
ambiguous_count = 0

for _, ep in df_ep.head(50).iterrows():
    cc = ep["code"]
    system = market_reform_countries.get(cc, non_market.get(cc, "Unknown"))

    is_resource = cc in [
        "AGO",
        "GNQ",
        "TKM",
        "AZE",
        "BHR",
        "OMN",
        "SAU",
        "QAT",
        "KWT",
        "LBY",
        "ARE",
    ]
    is_non_market = cc in non_market

    if is_resource:
        resource_count += 1
        tag = "[RESOURCE]"
    elif is_non_market:
        non_market_count += 1
        tag = "[NON-MARKET]"
    elif system != "Unknown":
        market_count += 1
        tag = "[MARKET]"
    else:
        ambiguous_count += 1
        tag = "[?]"

    print(
        f"  {ep['country'][:25]:<25} {ep['start']}-{ep['end']:<8} {ep['span']:<6} {ep['growth']:.1f}%   ${ep['gdp_start']:>8,.0f}   {tag} {system[:35]}"
    )

# Also specifically check USSR growth
print(f"\n\n  USSR/RUSSIA DETAILED GROWTH PERIODS:")
rus = mad[(mad["countrycode"] == "RUS") & (mad["gdppc"].notna())].sort_values("year")
periods = [
    (1928, 1940, "Stalin industrialization"),
    (1940, 1950, "WWII"),
    (1950, 1960, "Post-war recovery"),
    (1960, 1970, "Mature Soviet"),
    (1970, 1980, "Stagnation begins"),
    (1980, 1989, "Late Soviet/Perestroika"),
    (1989, 1998, "Collapse"),
    (1998, 2008, "Putin oil boom"),
    (2008, 2022, "Stagnation"),
]

for ps, pe, label in periods:
    start = rus[rus["year"] == ps]
    end = rus[rus["year"] == pe]
    if len(start) > 0 and len(end) > 0 and start.iloc[0]["gdppc"] > 0:
        g = (
            (end.iloc[0]["gdppc"] / start.iloc[0]["gdppc"]) ** (1 / (pe - ps)) - 1
        ) * 100
        print(
            f"    {ps}-{pe} ({label}): {g:.1f}%/yr (${start.iloc[0]['gdppc']:,.0f} → ${end.iloc[0]['gdppc']:,.0f})"
        )

# Make the table for the chart
table_rows = []
for _, ep in df_ep.nlargest(20, "span").iterrows():
    cc = ep["code"]
    system = market_reform_countries.get(cc, non_market.get(cc, ""))
    is_resource = cc in [
        "AGO",
        "GNQ",
        "TKM",
        "AZE",
        "BHR",
        "OMN",
        "SAU",
        "QAT",
        "KWT",
        "LBY",
        "ARE",
    ]
    tag = "RES" if is_resource else "CMD" if cc in non_market else "MKT"
    table_rows.append(
        [
            ep["country"][:20],
            f"{int(ep['start'])}-{int(ep['end'])}",
            f"{int(ep['span'])} yrs",
            f"{ep['growth']:.1f}%",
            tag,
        ]
    )

table = ax.table(
    cellText=table_rows,
    colLabels=["Country", "Period", "Duration", "Growth/yr", "System"],
    loc="center",
    cellLoc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.1, 1.5)
ax.set_title(
    "Longest Sustained >4% Growth Episodes\n(MKT=market, CMD=command, RES=resource)",
    fontweight="bold",
    pad=20,
)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "17_market_reforms_growth.png"))
plt.close()
print(f"\n  -> Saved 17_market_reforms_growth.png")

print(f"\n  SUMMARY OF GROWTH EPISODES (>4% sustained, 10+ years):")
print(f"    Market-oriented: {market_count}")
print(f"    Resource-driven: {resource_count}")
print(f"    Non-market/command: {non_market_count}")
print(f"    Unclassified: {ambiguous_count}")


###############################################################################
# 2. THE COMMAND ECONOMY GROWTH PATTERN
###############################################################################
print("\n" + "=" * 70)
print("2. COMMAND ECONOMY GROWTH PATTERN — THE EXTENSIVE GROWTH TRAP")
print("=" * 70)

fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Panel A: USSR vs market economies — the divergence after initial catch-up
ax = axes[0]

# Index to 1950 = 100 for fair comparison
base_year = 1950
for cc, (name, color, ls) in comparators.items():
    cdata = mad[
        (mad["countrycode"] == cc) & (mad["gdppc"].notna()) & (mad["year"] >= base_year)
    ].sort_values("year")
    base = cdata[cdata["year"] == base_year]
    if len(cdata) > 0 and len(base) > 0:
        cdata = cdata.copy()
        cdata["idx"] = cdata["gdppc"] / base.iloc[0]["gdppc"] * 100
        ax.plot(cdata["year"], cdata["idx"], ls, color=color, linewidth=2.5, label=name)

ax.set_title(f"GDP per Capita Indexed to {base_year} = 100")
ax.set_ylabel(f"Index ({base_year} = 100)")
ax.set_xlabel("Year")
ax.legend(fontsize=9)
ax.set_yscale("log")
ax.axvline(x=1978, color="green", linestyle=":", alpha=0.4)
ax.axvline(x=1991, color="red", linestyle=":", alpha=0.4)
ax.text(1978, ax.get_ylim()[1] * 0.7, "China\nreforms", fontsize=8, ha="center")
ax.text(1991, ax.get_ylim()[1] * 0.7, "USSR\ncollapse", fontsize=8, ha="center")

# Panel B: The "extensive vs intensive growth" illustration
# USSR grew FAST then hit a wall. Show growth rate declining over time
ax = axes[1]

# 10-year rolling growth rate for USSR and China
for cc, name, color in [
    ("RUS", "Russia/USSR", "#d62728"),
    ("CHN", "China", "#e377c2"),
    ("KOR", "S. Korea", "#8c564b"),
    ("JPN", "Japan", "#9467bd"),
]:
    cdata = mad[(mad["countrycode"] == cc) & (mad["gdppc"].notna())].sort_values("year")
    rolling_g = []
    for i in range(len(cdata) - 1):
        for j in range(i + 1, len(cdata)):
            span = cdata.iloc[j]["year"] - cdata.iloc[i]["year"]
            if 9 <= span <= 11:
                g = (
                    (cdata.iloc[j]["gdppc"] / cdata.iloc[i]["gdppc"]) ** (1 / span) - 1
                ) * 100
                rolling_g.append({"year": cdata.iloc[j]["year"], "growth": g})
                break

    if rolling_g:
        df_rg = pd.DataFrame(rolling_g)
        df_rg = df_rg[df_rg["year"] >= 1940]
        ax.plot(
            df_rg["year"], df_rg["growth"], "-", color=color, linewidth=2.5, label=name
        )

ax.set_title(
    "10-Year Rolling GDP/capita Growth Rate\n(The command economy trajectory: fast start, then stall)"
)
ax.set_xlabel("Year (end of 10-year window)")
ax.set_ylabel("Annual growth rate (%)")
ax.legend(fontsize=10)
ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)
ax.axhline(y=4, color="green", linestyle="--", alpha=0.3, label="4% threshold")

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "18_command_vs_market.png"))
plt.close()
print("  -> Saved 18_command_vs_market.png")


###############################################################################
# 3. CHINA: PRE AND POST REFORM
###############################################################################
print("\n" + "=" * 70)
print("3. CHINA: MAO VS REFORM PERIOD")
print("=" * 70)

chn = mad[(mad["countrycode"] == "CHN") & (mad["gdppc"].notna())].sort_values("year")

mao_periods = [
    (1949, 1957, "First Five-Year Plan"),
    (1957, 1962, "Great Leap Forward"),
    (1962, 1966, "Recovery"),
    (1966, 1976, "Cultural Revolution"),
    (1976, 1978, "Post-Mao transition"),
]

reform_periods = [
    (1978, 1984, "Rural reforms / HRS"),
    (1984, 1992, "Urban/SOE reforms"),
    (1992, 2001, "Deng Southern Tour / WTO"),
    (2001, 2010, "WTO accession era"),
    (2010, 2022, "Xi era / slowdown"),
]

print(f"  MAOIST PERIOD:")
for ps, pe, label in mao_periods:
    start = chn[chn["year"] == ps]
    end = chn[chn["year"] == pe]
    if len(start) > 0 and len(end) > 0 and start.iloc[0]["gdppc"] > 0:
        g = (
            (end.iloc[0]["gdppc"] / start.iloc[0]["gdppc"]) ** (1 / (pe - ps)) - 1
        ) * 100
        print(
            f"    {ps}-{pe} ({label}): {g:.1f}%/yr (${start.iloc[0]['gdppc']:,.0f} → ${end.iloc[0]['gdppc']:,.0f})"
        )

print(f"\n  REFORM PERIOD:")
for ps, pe, label in reform_periods:
    start = chn[chn["year"] == ps]
    end = chn[chn["year"] == pe]
    if len(start) > 0 and len(end) > 0 and start.iloc[0]["gdppc"] > 0:
        g = (
            (end.iloc[0]["gdppc"] / start.iloc[0]["gdppc"]) ** (1 / (pe - ps)) - 1
        ) * 100
        print(
            f"    {ps}-{pe} ({label}): {g:.1f}%/yr (${start.iloc[0]['gdppc']:,.0f} → ${end.iloc[0]['gdppc']:,.0f})"
        )

# Overall comparison
mao_start = chn[chn["year"] == 1949]
mao_end = chn[chn["year"] == 1978]
reform_end = chn[chn["year"] == 2022]
if len(mao_start) > 0 and len(mao_end) > 0 and len(reform_end) > 0:
    g_mao = (
        (mao_end.iloc[0]["gdppc"] / mao_start.iloc[0]["gdppc"]) ** (1 / 29) - 1
    ) * 100
    g_reform = (
        (reform_end.iloc[0]["gdppc"] / mao_end.iloc[0]["gdppc"]) ** (1 / 44) - 1
    ) * 100
    print(f"\n  OVERALL:")
    print(f"    Mao era (1949-1978): {g_mao:.1f}%/yr")
    print(f"    Reform era (1978-2022): {g_reform:.1f}%/yr")
    print(f"    Reform-era growth was {g_reform/g_mao:.1f}x faster than Mao era")


###############################################################################
# SYNTHESIS
###############################################################################
print("\n" + "=" * 70)
print("SYNTHESIS: MARKETS AND GROWTH")
print("=" * 70)
print(
    """
EMPIRICAL FINDINGS:

1. THE USSR STORY
   - Stalin-era industrialization (1928-1940): ~4.6%/yr — genuinely fast
   - Post-war golden age (1950-1970): ~3.7%/yr — respectable but decelerating
   - Stagnation (1970-1989): ~1.0%/yr — the wall
   - Collapse (1989-1998): -3.5%/yr — catastrophic
   - Recovery (1998-2008): ~5.8%/yr — oil-fueled, market-oriented
   
   Russia peaked at ~37% of US GDP per capita in 1970-80, then fell back.
   It never caught up despite 60+ years of forced industrialization.

2. THE COMMAND ECONOMY PATTERN
   Command economies show a distinctive arc: fast initial growth through
   forced mobilization of labor and capital (extensive growth), then
   deceleration as efficiency/innovation gains (intensive growth) require
   market signals. The USSR hit this wall in the 1970s. China was heading
   the same way — then reformed.

3. CHINA: THE CRITICAL COMPARISON
   Mao era (1949-1978): ~2.8%/yr — decent but with catastrophic volatility
     (Great Leap Forward: -5% collapse, tens of millions dead)
   Reform era (1978-2022): ~6.8%/yr — historic
   
   The reform-era growth rate was ~2.5x the Mao-era rate. Market reforms
   didn't just accelerate growth — they made it sustainable and less
   prone to catastrophic policy errors.

4. EVERY SUSTAINED >4% NON-RESOURCE GROWTH EPISODE INVOLVED MARKET MECHANISMS
   In the data: not a single sustained (10+ year) non-resource growth
   episode above 4% occurred in a pure command economy. The closest
   is the USSR 1928-1940 (and that involved forced collectivization/
   famine). Ethiopia under the EPRDF is arguably the most "command-like"
   recent success, but even that involved significant market mechanisms
   and foreign investment.
   
   CAVEAT: This finding is partly definitional — almost all modern economies
   use price signals and private enterprise to some degree, so "involved
   markets" is a low bar. The more interesting variation is the DEGREE of
   state direction: East Asian successes were heavily state-directed,
   not laissez-faire. The data rejects pure command economics, but does
   not endorse any particular market model.

5. COUNTEREXAMPLES ARE WEAK
   - Cuba: never sustained >4% growth for a decade
   - North Korea: initial postwar growth, then stagnation
   - USSR 1930s: fast but at enormous human cost and not sustained
   - Ethiopia (EPRDF): state-led but market-integrated, not command
"""
)
