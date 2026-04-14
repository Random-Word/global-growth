"""
Analysis 10: From Transfers to Self-Sufficiency
================================================
Can cash transfers drive durable productivity growth, or do countries
need something fundamentally different to reach the $15k "good life" threshold?

Charts 41-46:
  41 - Development anatomy: what does $15k look like?
  42 - Efficient outliers: who achieves good welfare cheaply?
  43 - Historical transition paths: what successful countries did
  44 - Investment and structural transformation
  45 - The SSA gap: how far, on how many dimensions?
  46 - Transfer evidence and graduation models
"""

import os
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

PROC = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
CHARTS = os.path.join(os.path.dirname(__file__), "..", "charts")
os.makedirs(CHARTS, exist_ok=True)

# Load data
wdi = pd.read_csv(os.path.join(PROC, "wdi_combined.csv"))
maddison = pd.read_csv(os.path.join(PROC, "maddison.csv"))

# Filter to countries only (exclude aggregates)
AGGREGATES = {
    "WLD",
    "HIC",
    "LIC",
    "LMC",
    "UMC",
    "MIC",
    "LMY",
    "INB",
    "EAS",
    "ECS",
    "LCN",
    "MEA",
    "NAC",
    "SAS",
    "SSF",
    "AFE",
    "AFW",
    "ARB",
    "CEB",
    "CSS",
    "EAP",
    "EAR",
    "EMU",
    "FCS",
    "HPC",
    "IBD",
    "IBT",
    "IDA",
    "IDB",
    "IDX",
    "LAC",
    "LDC",
    "LTE",
    "MNA",
    "OED",
    "OSS",
    "PRE",
    "PSS",
    "PST",
    "SAS",
    "SSA",
    "SST",
    "TEA",
    "TEC",
    "TLA",
    "TMN",
    "TSA",
    "TSS",
    "UMC",
    "EUU",
    "EUR",
}
wdi = wdi[~wdi["country_code"].isin(AGGREGATES)].copy()

print("=" * 70)
print("ANALYSIS 10: FROM TRANSFERS TO SELF-SUFFICIENCY")
print("=" * 70)

###############################################################################
# CHART 41: DEVELOPMENT ANATOMY — WHAT DOES $15K LOOK LIKE?
###############################################################################
print("\n  Chart 41: Development anatomy at $15k")

# Use latest available data for each country
latest = (
    wdi.sort_values("year", ascending=False)
    .groupby("country_code")
    .first()
    .reset_index()
)
latest = latest[latest["gdppc_ppp_current"].notna()].copy()

# Define GDP bins
bins = [0, 2000, 5000, 10000, 15000, 25000, 50000, 200000]
labels = ["<$2k", "$2-5k", "$5-10k", "$10-15k", "$15-25k", "$25-50k", ">$50k"]
latest["gdp_bin"] = pd.cut(latest["gdppc_ppp_current"], bins=bins, labels=labels)

fig, axes = plt.subplots(2, 3, figsize=(20, 14))
fig.suptitle(
    "What Does the $15k 'Good Life' Threshold Actually Look Like?",
    fontsize=16,
    fontweight="bold",
)

# Panel A: Electricity access by GDP bin
ax = axes[0][0]
for gdp_bin in labels:
    data = latest[latest["gdp_bin"] == gdp_bin]["electricity_access_pct"].dropna()
    if len(data) > 0:
        ax.bar(
            labels.index(gdp_bin),
            data.median(),
            color=plt.cm.viridis(labels.index(gdp_bin) / len(labels)),
            alpha=0.8,
        )
        ax.errorbar(
            labels.index(gdp_bin),
            data.median(),
            yerr=[
                [data.median() - data.quantile(0.25)],
                [data.quantile(0.75) - data.median()],
            ],
            color="black",
            capsize=5,
        )
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, fontsize=9)
ax.set_ylabel("% of population")
ax.set_title("Electricity Access")
ax.axhline(y=99, color="green", linestyle="--", alpha=0.5, label="~Universal (99%)")
ax.axvline(x=3, color="red", linestyle="--", alpha=0.5)
ax.annotate("$15k", (3, 50), fontsize=10, color="red", fontweight="bold")
ax.legend(fontsize=8)

# Panel B: Basic water + sanitation
ax = axes[0][1]
width = 0.35
for i, gdp_bin in enumerate(labels):
    water = latest[latest["gdp_bin"] == gdp_bin]["basic_water_access_pct"].dropna()
    sanit = latest[latest["gdp_bin"] == gdp_bin]["basic_sanitation_pct"].dropna()
    if len(water) > 0:
        ax.bar(
            i - width / 2,
            water.median(),
            width,
            color="steelblue",
            alpha=0.8,
            label="Water" if i == 0 else "",
        )
    if len(sanit) > 0:
        ax.bar(
            i + width / 2,
            sanit.median(),
            width,
            color="darkorange",
            alpha=0.8,
            label="Sanitation" if i == 0 else "",
        )
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, fontsize=9)
ax.set_ylabel("% of population")
ax.set_title("Basic Water & Sanitation Access")
ax.axvline(x=3, color="red", linestyle="--", alpha=0.5)
ax.legend(fontsize=9)

# Panel C: Secondary school enrollment
ax = axes[0][2]
for i, gdp_bin in enumerate(labels):
    data = latest[latest["gdp_bin"] == gdp_bin]["secondary_enrollment_pct"].dropna()
    if len(data) > 0:
        ax.bar(i, data.median(), color=plt.cm.viridis(i / len(labels)), alpha=0.8)
        ax.errorbar(
            i,
            data.median(),
            yerr=[
                [data.median() - data.quantile(0.25)],
                [data.quantile(0.75) - data.median()],
            ],
            color="black",
            capsize=5,
        )
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, fontsize=9)
ax.set_ylabel("Gross enrollment ratio (%)")
ax.set_title("Secondary School Enrollment")
ax.axvline(x=3, color="red", linestyle="--", alpha=0.5)

# Panel D: Health expenditure per capita
ax = axes[1][0]
for i, gdp_bin in enumerate(labels):
    data = latest[latest["gdp_bin"] == gdp_bin]["health_expenditure_pc"].dropna()
    if len(data) > 0:
        ax.bar(i, data.median(), color=plt.cm.viridis(i / len(labels)), alpha=0.8)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, fontsize=9)
ax.set_ylabel("$/person/year")
ax.set_title("Health Expenditure per Capita")
ax.axvline(x=3, color="red", linestyle="--", alpha=0.5)
ax.set_yscale("log")

# Panel E: Under-5 mortality
ax = axes[1][1]
for i, gdp_bin in enumerate(labels):
    data = latest[latest["gdp_bin"] == gdp_bin]["under5_mortality"].dropna()
    if len(data) > 0:
        ax.bar(i, data.median(), color=plt.cm.RdYlGn_r(i / len(labels)), alpha=0.8)
        ax.errorbar(
            i,
            data.median(),
            yerr=[
                [data.median() - data.quantile(0.25)],
                [data.quantile(0.75) - data.median()],
            ],
            color="black",
            capsize=5,
        )
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, fontsize=9)
ax.set_ylabel("Deaths per 1,000 live births")
ax.set_title("Under-5 Mortality")
ax.axvline(x=3, color="red", linestyle="--", alpha=0.5)

# Panel F: Summary table
ax = axes[1][2]
ax.axis("off")
summary_data = []
indicators = [
    ("electricity_access_pct", "Electricity (% pop)", "{:.0f}%"),
    ("basic_water_access_pct", "Clean water (% pop)", "{:.0f}%"),
    ("basic_sanitation_pct", "Sanitation (% pop)", "{:.0f}%"),
    ("secondary_enrollment_pct", "Secondary school (%)", "{:.0f}%"),
    ("health_expenditure_pc", "Health $/person", "${:.0f}"),
    ("under5_mortality", "Under-5 mortality", "{:.0f}‰"),
    ("life_expectancy", "Life expectancy", "{:.1f}yr"),
    ("fertility_rate", "Fertility rate", "{:.1f}"),
]
for col, label, fmt in indicators:
    row = [label]
    for gdp_bin in ["<$2k", "$5-10k", "$10-15k", "$15-25k"]:
        data = latest[latest["gdp_bin"] == gdp_bin][col].dropna()
        if len(data) > 0:
            row.append(fmt.format(data.median()))
        else:
            row.append("—")
    summary_data.append(row)

table = ax.table(
    cellText=summary_data,
    colLabels=["Indicator", "<$2k", "$5-10k", "$10-15k", "$15-25k"],
    loc="center",
    cellLoc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.2, 1.6)
ax.set_title("Median Development Profile by GDP/cap", fontweight="bold", pad=20)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "41_development_anatomy.png"), dpi=150)
plt.close()
print("  -> Saved 41_development_anatomy.png")

# Print the key table
print("\n  Development anatomy at key thresholds:")
print(
    f"  {'Indicator':<25} {'<$2k':<12} {'$5-10k':<12} {'$10-15k':<12} {'$15-25k':<12}"
)
print("  " + "-" * 70)
for row in summary_data:
    print(f"  {row[0]:<25} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<12}")

###############################################################################
# CHART 42: EFFICIENT OUTLIERS — WHO ACHIEVES GOOD WELFARE CHEAPLY?
###############################################################################
print("\n  Chart 42: Efficient outliers")

fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle(
    "Efficient Outliers: Countries That Punch Above Their Income Weight",
    fontsize=16,
    fontweight="bold",
)

# Use latest data with GDP
latest_with_gdp = latest[latest["gdppc_ppp_current"].notna()].copy()

# Panel A: Life expectancy vs GDP — highlight efficient outliers
ax = axes[0][0]
mask = latest_with_gdp["life_expectancy"].notna()
data = latest_with_gdp[mask]
ax.scatter(
    data["gdppc_ppp_current"],
    data["life_expectancy"],
    s=data["population"].clip(upper=1.5e9) / 1e7,
    alpha=0.4,
    color="steelblue",
)

# Label outliers: high life expectancy at low GDP
efficient = data[(data["gdppc_ppp_current"] < 15000) & (data["life_expectancy"] > 72)]
for _, r in efficient.iterrows():
    if r["country_code"] in ["CRI", "LKA", "VNM", "CUB", "ALB", "BGD", "TUN", "GEO"]:
        ax.annotate(
            r["country_code"],
            (r["gdppc_ppp_current"], r["life_expectancy"]),
            fontsize=8,
            fontweight="bold",
            color="darkred",
        )

# Label inefficient: low life expectancy at moderate GDP
inefficient = data[(data["gdppc_ppp_current"] > 15000) & (data["life_expectancy"] < 70)]
for _, r in inefficient.iterrows():
    if r["country_code"] in ["GNQ", "TKM", "BRN", "TTO", "BHS", "USA"]:
        ax.annotate(
            r["country_code"],
            (r["gdppc_ppp_current"], r["life_expectancy"]),
            fontsize=8,
            fontweight="bold",
            color="gray",
        )

ax.axvline(x=15000, color="red", linestyle="--", alpha=0.5, label="$15k threshold")
ax.axhline(y=70, color="green", linestyle="--", alpha=0.5, label="70yr life expectancy")
ax.set_xscale("log")
ax.set_xlabel("GDP per capita (PPP, current $)")
ax.set_ylabel("Life expectancy (years)")
ax.set_title("Life Expectancy vs Income\n(labeled: efficient outliers in red)")
ax.legend(fontsize=9)

# Panel B: Under-5 mortality vs GDP
ax = axes[0][1]
mask = latest_with_gdp["under5_mortality"].notna()
data = latest_with_gdp[mask]
ax.scatter(
    data["gdppc_ppp_current"],
    data["under5_mortality"],
    s=data["population"].clip(upper=1.5e9) / 1e7,
    alpha=0.4,
    color="coral",
)

# Label outliers
efficient_mort = data[
    (data["gdppc_ppp_current"] < 10000) & (data["under5_mortality"] < 15)
]
for _, r in efficient_mort.iterrows():
    if r["country_code"] in ["CRI", "LKA", "VNM", "CUB", "GEO", "TUN", "UKR"]:
        ax.annotate(
            r["country_code"],
            (r["gdppc_ppp_current"], r["under5_mortality"]),
            fontsize=8,
            fontweight="bold",
            color="darkgreen",
        )

ax.axvline(x=15000, color="red", linestyle="--", alpha=0.5)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("GDP per capita (PPP, current $)")
ax.set_ylabel("Under-5 mortality (per 1,000)")
ax.set_title("Child Mortality vs Income\n(green: efficient outliers)")

# Panel C: Welfare Efficiency Index — composite welfare per $ of GDP
ax = axes[1][0]
# Build a simple composite: normalize life_expectancy and inverse under5_mortality
data = latest_with_gdp[
    latest_with_gdp["life_expectancy"].notna()
    & latest_with_gdp["under5_mortality"].notna()
    & (latest_with_gdp["gdppc_ppp_current"] > 500)
].copy()

if len(data) > 0:
    # Normalize: life expectancy 40-85 → 0-1, under5 mortality 2-200 → 1-0
    data["le_norm"] = (data["life_expectancy"].clip(40, 85) - 40) / 45
    data["mort_norm"] = 1 - (
        data["under5_mortality"].clip(2, 200).apply(np.log) - np.log(2)
    ) / (np.log(200) - np.log(2))

    # Add education if available
    data["sec_norm"] = 0.5  # default
    mask_sec = data["secondary_enrollment_pct"].notna()
    data.loc[mask_sec, "sec_norm"] = (
        data.loc[mask_sec, "secondary_enrollment_pct"].clip(0, 120) / 120
    )

    data["welfare_index"] = (data["le_norm"] + data["mort_norm"] + data["sec_norm"]) / 3
    data["efficiency"] = data["welfare_index"] / np.log10(data["gdppc_ppp_current"])

    # Sort and show top/bottom
    data_sorted = data.sort_values("efficiency", ascending=False)
    top_eff = data_sorted.head(15)
    bottom_eff = data_sorted[data_sorted["gdppc_ppp_current"] > 10000].tail(10)

    ax.barh(
        range(len(top_eff)),
        top_eff["efficiency"],
        color="seagreen",
        alpha=0.8,
    )
    ax.set_yticks(range(len(top_eff)))
    ax.set_yticklabels(
        [
            f"{r['country_code']} (${r['gdppc_ppp_current']/1000:.0f}k)"
            for _, r in top_eff.iterrows()
        ],
        fontsize=9,
    )
    ax.set_xlabel("Welfare per log(GDP/cap)")
    ax.set_title("Most Efficient: Best Welfare per $ of Income")
    ax.invert_yaxis()

# Panel D: Table of efficient outliers vs their income peers
ax = axes[1][1]
ax.axis("off")
outlier_codes = ["CRI", "LKA", "VNM", "CUB", "GEO", "TUN", "ALB"]
peer_codes = ["GNQ", "TTO", "BRN", "TKM", "OMN"]

table_data = []
for code in outlier_codes + ["---"] + peer_codes:
    if code == "---":
        table_data.append(["—" * 3, "—", "—", "—", "—", "—"])
        continue
    r = latest_with_gdp[latest_with_gdp["country_code"] == code]
    if len(r) == 0:
        continue
    r = r.iloc[0]
    table_data.append(
        [
            f"{r.get('country', code)}",
            (
                f"${r['gdppc_ppp_current']/1000:.1f}k"
                if pd.notna(r.get("gdppc_ppp_current"))
                else "—"
            ),
            (
                f"{r['life_expectancy']:.1f}"
                if pd.notna(r.get("life_expectancy"))
                else "—"
            ),
            (
                f"{r['under5_mortality']:.0f}"
                if pd.notna(r.get("under5_mortality"))
                else "—"
            ),
            (
                f"{r['electricity_access_pct']:.0f}%"
                if pd.notna(r.get("electricity_access_pct"))
                else "—"
            ),
            (
                f"{r['secondary_enrollment_pct']:.0f}%"
                if pd.notna(r.get("secondary_enrollment_pct"))
                else "—"
            ),
        ]
    )

if table_data:
    tbl = ax.table(
        cellText=table_data,
        colLabels=[
            "Country",
            "GDP/cap",
            "Life Exp",
            "U5 Mort",
            "Electric",
            "Sec School",
        ],
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.1, 1.5)
ax.set_title("Efficient Outliers vs Rich Underperformers", fontweight="bold", pad=20)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "42_efficient_outliers.png"), dpi=150)
plt.close()
print("  -> Saved 42_efficient_outliers.png")

###############################################################################
# CHART 43: HISTORICAL TRANSITION PATHS — WHAT SUCCESSFUL COUNTRIES DID
###############################################################################
print("\n  Chart 43: Successful transition paths")

# Track countries that went from <$3k to >$10k GDP/cap (PPP)
transition_countries = {
    "KOR": "South Korea",
    "CHN": "China",
    "VNM": "Vietnam",
    "THA": "Thailand",
    "MYS": "Malaysia",
    "BWA": "Botswana",
    "CHL": "Chile",
    "POL": "Poland",
    "IDN": "Indonesia",
    "IND": "India",
}

# Stalled countries for comparison
stalled_countries = {
    "NGA": "Nigeria",
    "COD": "DR Congo",
    "KEN": "Kenya",
    "GHA": "Ghana",
    "ZAF": "S. Africa",
    "MEX": "Mexico",
}

fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle(
    "Paths to $15k: What Successful Transitions Look Like",
    fontsize=16,
    fontweight="bold",
)

# Panel A: GDP trajectories of successful transitions
ax = axes[0][0]
colors_trans = plt.cm.tab10(np.linspace(0, 1, len(transition_countries)))
for i, (code, name) in enumerate(transition_countries.items()):
    cdata = wdi[
        (wdi["country_code"] == code) & wdi["gdppc_ppp_current"].notna()
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(
            cdata["year"],
            cdata["gdppc_ppp_current"],
            label=name,
            color=colors_trans[i],
            linewidth=2,
        )

ax.axhline(y=15000, color="red", linestyle="--", alpha=0.7, label="$15k threshold")
ax.set_xlabel("Year")
ax.set_ylabel("GDP per capita (PPP, current $)")
ax.set_title("GDP/capita Trajectories: Successful Transitions")
ax.legend(fontsize=8, ncol=2)
ax.set_yscale("log")
ax.set_ylim(500, 80000)

# Panel B: Stalled countries
ax = axes[0][1]
colors_stalled = plt.cm.Set2(np.linspace(0, 1, len(stalled_countries)))
for i, (code, name) in enumerate(stalled_countries.items()):
    cdata = wdi[
        (wdi["country_code"] == code) & wdi["gdppc_ppp_current"].notna()
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(
            cdata["year"],
            cdata["gdppc_ppp_current"],
            label=name,
            color=colors_stalled[i],
            linewidth=2,
        )

ax.axhline(y=15000, color="red", linestyle="--", alpha=0.7, label="$15k threshold")
ax.set_xlabel("Year")
ax.set_ylabel("GDP per capita (PPP, current $)")
ax.set_title("Stalled: Countries Stuck Below $15k")
ax.legend(fontsize=9)
ax.set_yscale("log")
ax.set_ylim(500, 80000)

# Panel C: Structural transformation — agriculture share declining
ax = axes[1][0]
for i, (code, name) in enumerate(list(transition_countries.items())[:6]):
    cdata = wdi[
        (wdi["country_code"] == code) & wdi["agriculture_va_pct"].notna()
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(cdata["year"], cdata["agriculture_va_pct"], label=name, linewidth=2)

ax.set_xlabel("Year")
ax.set_ylabel("Agriculture value added (% GDP)")
ax.set_title("Structural Transformation:\nAgriculture Shrinks as Countries Develop")
ax.legend(fontsize=9)

# Panel D: Investment rates (gross capital formation)
ax = axes[1][1]
# Compare investment rates of successful vs stalled
for i, (code, name) in enumerate(list(transition_countries.items())[:5]):
    cdata = wdi[
        (wdi["country_code"] == code) & wdi["gross_capital_formation_pct"].notna()
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(
            cdata["year"],
            cdata["gross_capital_formation_pct"],
            label=name,
            color=colors_trans[i],
            linewidth=2,
        )

for i, (code, name) in enumerate(list(stalled_countries.items())[:3]):
    cdata = wdi[
        (wdi["country_code"] == code) & wdi["gross_capital_formation_pct"].notna()
    ].sort_values("year")
    if len(cdata) > 0:
        ax.plot(
            cdata["year"],
            cdata["gross_capital_formation_pct"],
            label=name,
            color=colors_stalled[i],
            linewidth=2,
            linestyle="--",
        )

ax.axhline(y=25, color="green", linestyle=":", alpha=0.5, label="25% threshold")
ax.set_xlabel("Year")
ax.set_ylabel("Gross capital formation (% GDP)")
ax.set_title("Investment Rates:\nSuccessful (solid) vs Stalled (dashed)")
ax.legend(fontsize=8, ncol=2)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "43_transition_paths.png"), dpi=150)
plt.close()
print("  -> Saved 43_transition_paths.png")

# Compute transition statistics
print("\n  Transition statistics:")
print(
    f"  {'Country':<15} {'Start GDP':<12} {'Current GDP':<12} {'Years <$3k→>$10k':<18} {'Peak Invest%':<12}"
)
print("  " + "-" * 70)
for code, name in transition_countries.items():
    cdata = wdi[
        (wdi["country_code"] == code) & wdi["gdppc_ppp_current"].notna()
    ].sort_values("year")
    if len(cdata) == 0:
        continue
    first = cdata.iloc[0]
    last = cdata.iloc[-1]
    # Find year crossed $3k and $10k
    crossed_3k = cdata[cdata["gdppc_ppp_current"] >= 3000]
    crossed_10k = cdata[cdata["gdppc_ppp_current"] >= 10000]
    yr_3k = int(crossed_3k.iloc[0]["year"]) if len(crossed_3k) > 0 else None
    yr_10k = int(crossed_10k.iloc[0]["year"]) if len(crossed_10k) > 0 else None
    transition_yrs = (
        f"{yr_10k - yr_3k}yr ({yr_3k}→{yr_10k})" if yr_3k and yr_10k else "—"
    )

    inv = wdi[
        (wdi["country_code"] == code) & wdi["gross_capital_formation_pct"].notna()
    ]
    peak_inv = (
        f"{inv['gross_capital_formation_pct'].max():.0f}%" if len(inv) > 0 else "—"
    )

    print(
        f"  {name:<15} ${first['gdppc_ppp_current']/1000:.1f}k      ${last['gdppc_ppp_current']/1000:.1f}k      {transition_yrs:<18} {peak_inv}"
    )


###############################################################################
# CHART 44: INVESTMENT & STRUCTURAL TRANSFORMATION
###############################################################################
print("\n  Chart 44: Investment and structural transformation")

fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle(
    "What Self-Sustaining Development Requires:\nInvestment, Structure, and Trade",
    fontsize=16,
    fontweight="bold",
)

# Panel A: Savings rate vs GDP/cap
ax = axes[0][0]
data = latest_with_gdp[latest_with_gdp["gross_savings_pct_gdp"].notna()].copy()
ax.scatter(
    data["gdppc_ppp_current"],
    data["gross_savings_pct_gdp"],
    s=data["population"].clip(upper=1.5e9) / 1e7,
    alpha=0.4,
    color="steelblue",
)

# Label key countries
for code in ["CHN", "KOR", "IND", "VNM", "NGA", "USA", "ETH", "BWA"]:
    r = data[data["country_code"] == code]
    if len(r) > 0:
        r = r.iloc[0]
        ax.annotate(
            code,
            (r["gdppc_ppp_current"], r["gross_savings_pct_gdp"]),
            fontsize=8,
            fontweight="bold",
        )

ax.set_xscale("log")
ax.set_xlabel("GDP per capita (PPP)")
ax.set_ylabel("Gross savings (% GDP)")
ax.set_title("Domestic Savings Rate\n(fuel for investment)")
ax.axhline(
    y=25, color="green", linestyle="--", alpha=0.5, label="25% (high-growth threshold)"
)
ax.axvline(x=15000, color="red", linestyle="--", alpha=0.5)
ax.legend(fontsize=9)

# Panel B: Trade openness vs GDP/cap
ax = axes[0][1]
data = latest_with_gdp[latest_with_gdp["trade_pct_gdp"].notna()].copy()
ax.scatter(
    data["gdppc_ppp_current"],
    data["trade_pct_gdp"],
    s=data["population"].clip(upper=1.5e9) / 1e7,
    alpha=0.4,
    color="coral",
)
for code in ["CHN", "KOR", "VNM", "IND", "NGA", "DEU", "ETH"]:
    r = data[data["country_code"] == code]
    if len(r) > 0:
        r = r.iloc[0]
        ax.annotate(
            code,
            (r["gdppc_ppp_current"], r["trade_pct_gdp"]),
            fontsize=8,
            fontweight="bold",
        )

ax.set_xscale("log")
ax.set_xlabel("GDP per capita (PPP)")
ax.set_ylabel("Trade (% GDP)")
ax.set_title("Trade Openness")
ax.axvline(x=15000, color="red", linestyle="--", alpha=0.5)

# Panel C: Structural transformation — scatter of agriculture% vs GDP
ax = axes[1][0]
data = latest_with_gdp[
    latest_with_gdp["agriculture_va_pct"].notna()
    & latest_with_gdp["services_va_pct"].notna()
].copy()
ax.scatter(
    data["gdppc_ppp_current"],
    data["agriculture_va_pct"],
    s=data["population"].clip(upper=1.5e9) / 1e7,
    alpha=0.4,
    color="forestgreen",
    label="Agriculture",
)
ax.scatter(
    data["gdppc_ppp_current"],
    data["services_va_pct"],
    s=data["population"].clip(upper=1.5e9) / 1e7,
    alpha=0.3,
    color="purple",
    label="Services",
)
ax.set_xscale("log")
ax.set_xlabel("GDP per capita (PPP)")
ax.set_ylabel("% of GDP")
ax.set_title("Structural Transformation:\nAgriculture → Services")
ax.axvline(x=15000, color="red", linestyle="--", alpha=0.5)
ax.legend(fontsize=9)

# Panel D: Fertility rate vs GDP — the demographic transition
ax = axes[1][1]
data = latest_with_gdp[latest_with_gdp["fertility_rate"].notna()].copy()
ax.scatter(
    data["gdppc_ppp_current"],
    data["fertility_rate"],
    s=data["population"].clip(upper=1.5e9) / 1e7,
    alpha=0.4,
    color="darkred",
)
for code in ["NGA", "NER", "TCD", "MLI", "CHN", "KOR", "IND", "VNM", "USA", "ETH"]:
    r = data[data["country_code"] == code]
    if len(r) > 0:
        r = r.iloc[0]
        ax.annotate(
            code,
            (r["gdppc_ppp_current"], r["fertility_rate"]),
            fontsize=8,
            fontweight="bold",
        )

ax.set_xscale("log")
ax.set_xlabel("GDP per capita (PPP)")
ax.set_ylabel("Births per woman")
ax.set_title("Demographic Transition:\nFertility Falls with Development")
ax.axhline(
    y=2.1, color="green", linestyle="--", alpha=0.5, label="Replacement rate (2.1)"
)
ax.axvline(x=15000, color="red", linestyle="--", alpha=0.5)
ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "44_investment_structure.png"), dpi=150)
plt.close()
print("  -> Saved 44_investment_structure.png")


###############################################################################
# CHART 45: THE SSA GAP — HOW FAR ON HOW MANY DIMENSIONS
###############################################################################
print("\n  Chart 45: Sub-Saharan Africa development gap")

fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle(
    "Sub-Saharan Africa: The Multi-Dimensional Development Gap",
    fontsize=16,
    fontweight="bold",
)

# Define SSA countries (approximate — WB income classification)
# Use region from WDI if available, otherwise use list
ssa_codes = set()
for code in wdi["country_code"].unique():
    cdata = wdi[wdi["country_code"] == code]
    if len(cdata) == 0:
        continue
    gdp_latest = cdata.sort_values("year", ascending=False)[
        "gdppc_ppp_current"
    ].dropna()
    if len(gdp_latest) == 0:
        continue
    country = cdata.iloc[0]["country"]
    # Rough SSA identification by well-known SSA countries
    ssa_names = [
        "Nigeria",
        "Ethiopia",
        "Congo, Dem. Rep.",
        "Tanzania",
        "South Africa",
        "Kenya",
        "Uganda",
        "Ghana",
        "Mozambique",
        "Madagascar",
        "Cameroon",
        "Angola",
        "Niger",
        "Mali",
        "Burkina Faso",
        "Malawi",
        "Zambia",
        "Senegal",
        "Chad",
        "Somalia",
        "Zimbabwe",
        "Rwanda",
        "Benin",
        "Burundi",
        "South Sudan",
        "Togo",
        "Sierra Leone",
        "Congo, Rep.",
        "Liberia",
        "Central African Republic",
        "Mauritania",
        "Eritrea",
        "Gambia, The",
        "Botswana",
        "Namibia",
        "Gabon",
        "Lesotho",
        "Guinea-Bissau",
        "Equatorial Guinea",
        "Mauritius",
        "Eswatini",
        "Djibouti",
        "Comoros",
        "Cabo Verde",
        "Guinea",
        "Cote d'Ivoire",
    ]
    if country in ssa_names:
        ssa_codes.add(code)

# Also add well-known SSA codes
for c in [
    "NGA",
    "ETH",
    "COD",
    "TZA",
    "ZAF",
    "KEN",
    "UGA",
    "GHA",
    "MOZ",
    "MDG",
    "CMR",
    "AGO",
    "NER",
    "MLI",
    "BFA",
    "MWI",
    "ZMB",
    "SEN",
    "TCD",
    "ZWE",
    "RWA",
    "BEN",
    "BDI",
    "SSD",
    "TGO",
    "SLE",
    "COG",
    "LBR",
    "CAF",
    "MRT",
    "ERI",
    "GMB",
    "BWA",
    "NAM",
    "GAB",
    "LSO",
    "GNB",
    "GNQ",
    "MUS",
    "SWZ",
    "DJI",
    "COM",
    "CPV",
    "GIN",
    "CIV",
]:
    ssa_codes.add(c)

latest_ssa = latest[latest["country_code"].isin(ssa_codes)].copy()
latest_nonssa_dev = latest[
    (~latest["country_code"].isin(ssa_codes))
    & (latest["gdppc_ppp_current"].notna())
    & (latest["gdppc_ppp_current"] >= 15000)
    & (latest["gdppc_ppp_current"] <= 50000)
].copy()

# East Asian comparators (at similar GDP/cap as SSA was 20-30 years ago)
ea_codes = {"CHN", "VNM", "IDN", "THA", "MYS", "KOR", "IND", "BGD"}

# Panel A: Radar-style bar comparison — SSA vs $15k+ countries
ax = axes[0][0]
compare_indicators = [
    ("electricity_access_pct", "Electricity"),
    ("basic_water_access_pct", "Clean Water"),
    ("basic_sanitation_pct", "Sanitation"),
    ("secondary_enrollment_pct", "Secondary Ed"),
    ("life_expectancy", "Life Expect."),
]

ssa_vals = []
dev_vals = []
for col, label in compare_indicators:
    ssa_med = latest_ssa[col].dropna().median()
    dev_med = latest_nonssa_dev[col].dropna().median()
    ssa_vals.append(ssa_med)
    dev_vals.append(dev_med)

x = np.arange(len(compare_indicators))
width = 0.35
ax.bar(x - width / 2, ssa_vals, width, label="SSA median", color="coral", alpha=0.8)
ax.bar(
    x + width / 2, dev_vals, width, label="$15-50k median", color="seagreen", alpha=0.8
)
ax.set_xticks(x)
ax.set_xticklabels([label for _, label in compare_indicators], rotation=45, fontsize=9)
ax.set_title("SSA vs Developed Countries:\nKey Development Indicators")
ax.legend(fontsize=9)

# Panel B: GDP/cap distribution — SSA vs world
ax = axes[0][1]
ssa_gdps = latest_ssa["gdppc_ppp_current"].dropna()
all_gdps = latest[latest["gdppc_ppp_current"].notna()]["gdppc_ppp_current"]

ax.hist(
    all_gdps.apply(np.log10),
    bins=30,
    alpha=0.4,
    color="steelblue",
    label="World",
    density=True,
)
ax.hist(
    ssa_gdps.apply(np.log10),
    bins=20,
    alpha=0.6,
    color="coral",
    label="SSA",
    density=True,
)
ax.axvline(x=np.log10(15000), color="red", linestyle="--", label="$15k")
ax.set_xlabel("log₁₀(GDP per capita PPP)")
ax.set_ylabel("Density")
ax.set_title("GDP/capita Distribution:\nSSA vs World")
ax.legend(fontsize=9)

# Custom tick labels
tick_vals = [3, 3.5, 4, 4.5, 5]
ax.set_xticks(tick_vals)
ax.set_xticklabels(
    [f"${10**v/1000:.0f}k" if 10**v >= 1000 else f"${10**v:.0f}" for v in tick_vals]
)

# Panel C: Investment gap
ax = axes[1][0]
ssa_invest = latest_ssa["gross_capital_formation_pct"].dropna()
ea_latest = latest[latest["country_code"].isin(ea_codes)]
ea_invest = ea_latest["gross_capital_formation_pct"].dropna()

groups = ["SSA median", "East Asia median", "25% threshold"]
values = [
    ssa_invest.median() if len(ssa_invest) > 0 else 0,
    ea_invest.median() if len(ea_invest) > 0 else 0,
    25,
]
colors_bar = ["coral", "steelblue", "green"]
bars = ax.bar(groups, values, color=colors_bar, alpha=0.8)
for bar, val in zip(bars, values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        f"{val:.1f}%",
        ha="center",
        fontsize=11,
        fontweight="bold",
    )
ax.set_ylabel("Gross capital formation (% GDP)")
ax.set_title("The Investment Gap")

# Panel D: What SSA needs — multiplier table
ax = axes[1][1]
ax.axis("off")

# Calculate: for each SSA country, how many multiples of current GDP to reach $15k
ssa_multipliers = []
for _, r in latest_ssa.iterrows():
    if pd.notna(r.get("gdppc_ppp_current")) and r["gdppc_ppp_current"] > 0:
        mult = 15000 / r["gdppc_ppp_current"]
        years_3pct = np.log(mult) / np.log(1.03) if mult > 1 else 0
        years_5pct = np.log(mult) / np.log(1.05) if mult > 1 else 0
        ssa_multipliers.append(
            {
                "country": r["country"],
                "gdp": r["gdppc_ppp_current"],
                "mult": mult,
                "yrs_3": years_3pct,
                "yrs_5": years_5pct,
            }
        )

if ssa_multipliers:
    mult_df = pd.DataFrame(ssa_multipliers).sort_values("gdp")
    # Show bottom 10, median, top 5
    table_rows = []
    bottom5 = mult_df.head(5)
    for _, r in bottom5.iterrows():
        table_rows.append(
            [
                r["country"][:20],
                f"${r['gdp']/1000:.1f}k",
                f"{r['mult']:.1f}x",
                f"{r['yrs_3']:.0f}yr" if r["mult"] > 1 else "—",
                f"{r['yrs_5']:.0f}yr" if r["mult"] > 1 else "—",
            ]
        )
    table_rows.append(
        [
            "—— Median ——",
            f"${mult_df['gdp'].median()/1000:.1f}k",
            f"{mult_df['mult'].median():.1f}x",
            f"{mult_df['yrs_3'].median():.0f}yr",
            f"{mult_df['yrs_5'].median():.0f}yr",
        ]
    )
    top5 = mult_df.tail(5)
    for _, r in top5.iterrows():
        table_rows.append(
            [
                r["country"][:20],
                f"${r['gdp']/1000:.1f}k",
                f"{r['mult']:.1f}x" if r["mult"] > 1 else "At threshold",
                f"{r['yrs_3']:.0f}yr" if r["mult"] > 1 else "—",
                f"{r['yrs_5']:.0f}yr" if r["mult"] > 1 else "—",
            ]
        )

    tbl = ax.table(
        cellText=table_rows,
        colLabels=[
            "Country",
            "Current GDP/cap",
            "Multiplier",
            "Years @3%",
            "Years @5%",
        ],
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.1, 1.4)
    ax.set_title("SSA Distance to $15k Threshold", fontweight="bold", pad=20)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "45_ssa_gap.png"), dpi=150)
plt.close()
print("  -> Saved 45_ssa_gap.png")

# Print SSA summary stats
if ssa_multipliers:
    mult_df = pd.DataFrame(ssa_multipliers)
    print(f"\n  SSA distance to $15k:")
    print(f"    Median GDP/cap: ${mult_df['gdp'].median():,.0f}")
    print(f"    Median multiplier needed: {mult_df['mult'].median():.1f}x")
    print(f"    Median years at 3% growth: {mult_df['yrs_3'].median():.0f}")
    print(f"    Median years at 5% growth: {mult_df['yrs_5'].median():.0f}")
    print(f"    Countries already above $15k: {(mult_df['mult'] <= 1).sum()}")
    print(f"    Countries needing >10x: {(mult_df['mult'] > 10).sum()}")


###############################################################################
# CHART 46: CASH TRANSFERS VS GRADUATION MODELS
###############################################################################
print("\n  Chart 46: Transfer evidence and development models")

fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle(
    "From Transfers to Self-Sufficiency:\nWhat the Evidence Says",
    fontsize=16,
    fontweight="bold",
)

# Panel A: Cash transfer evidence timeline / effectiveness
ax = axes[0][0]
ax.axis("off")

# Summarize the key evidence on cash transfers and productivity
evidence = [
    [
        "GiveDirectly (Kenya)\n3yr RCT",
        "~$1,000\none-time",
        "+$270/yr income\n(+38%)",
        "Assets: +$0.85/dollar\nConsumption: sustained\nEnterprise: modest",
    ],
    [
        "GiveDirectly (Kenya)\nGeneral Equilibrium",
        "$1,871\naverage",
        "$2.60 local\nmultiplier",
        "Wages +5.5%, prices\nflat — demand creates\njobs, not inflation",
    ],
    [
        "Graduation (6-country)\nBanerjee et al. 2015",
        "~$1,500\n(asset+cash+coaching)",
        "+$344/yr income\n(+38%) at year 7",
        "SUSTAINED 7yr+ later\nSavings up, health up\nMicro-enterprise growth",
    ],
    [
        "Ethiopia PSNP\n(public works + cash)",
        "$68/yr/person",
        "+$94/yr income\n(+21%)",
        "Productive assets up\nBUT needs continuation\nfor fragile households",
    ],
    [
        "Mexico Progresa/\nOportunidades (CCT)",
        "$55/month\nconditional",
        "Children: +0.7yr\nschooling",
        "HUMAN CAPITAL path\nNext-gen earnings +8%\nNutrition → cognition",
    ],
]

tbl = ax.table(
    cellText=evidence,
    colLabels=["Program", "Transfer Size", "Income Effect", "Long-run / Productivity"],
    loc="center",
    cellLoc="left",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(8)
tbl.scale(1.1, 2.2)
ax.set_title(
    "Cash Transfer Evidence: Income Effects and Durability", fontweight="bold", pad=20
)

# Panel B: The development ladder — what transfers can and cannot do
ax = axes[0][1]
ax.axis("off")

# Draw a conceptual ladder
ladder_items = [
    (
        0.9,
        "Self-sustaining $15k+ economy",
        "green",
        "Markets, industry, services, trade, innovation",
    ),
    (
        0.75,
        "Middle-income $5-15k",
        "yellowgreen",
        "Manufacturing, urbanization, secondary education",
    ),
    (
        0.6,
        "Lower-middle $2-5k",
        "gold",
        "Agricultural surplus, basic infrastructure, primary education",
    ),
    (
        0.45,
        "Low-income <$2k",
        "orange",
        "Subsistence, minimal infrastructure, high mortality",
    ),
    (
        0.3,
        "Extreme poverty <$2.15/day",
        "red",
        "Survival mode, stunting, no savings capacity",
    ),
]

for y, label, color, desc in ladder_items:
    ax.barh(y, 0.7, height=0.12, left=0.15, color=color, alpha=0.7)
    ax.text(0.5, y, label, ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(0.88, y, desc, ha="left", va="center", fontsize=7, style="italic")

# Add arrows showing what different interventions can do
ax.annotate(
    "Cash transfers\ncan lift people\nfrom here...",
    xy=(0.15, 0.3),
    xytext=(0.02, 0.15),
    fontsize=8,
    color="blue",
    fontweight="bold",
    arrowprops=dict(arrowstyle="->", color="blue"),
)
ax.annotate(
    "...to here\n(maybe)",
    xy=(0.15, 0.45),
    xytext=(0.02, 0.52),
    fontsize=8,
    color="blue",
    arrowprops=dict(arrowstyle="->", color="blue"),
)
ax.annotate(
    "Graduation programs\ncan push to here",
    xy=(0.15, 0.6),
    xytext=(0.02, 0.68),
    fontsize=8,
    color="darkgreen",
    fontweight="bold",
    arrowprops=dict(arrowstyle="->", color="darkgreen"),
)
ax.annotate(
    "Development\n(infrastructure,\ninstitutions,\nindustrial policy)\nrequired",
    xy=(0.85, 0.75),
    xytext=(0.88, 0.9),
    fontsize=8,
    color="purple",
    fontweight="bold",
    arrowprops=dict(arrowstyle="->", color="purple"),
)

ax.set_xlim(0, 1.5)
ax.set_ylim(0.1, 1.0)
ax.set_title(
    "The Development Ladder:\nWhat Each Intervention Can Reach", fontweight="bold"
)

# Panel C: Historical investment rates during transition periods
ax = axes[1][0]
# For successful countries, track investment rate during their high-growth period
transition_invest = {}
for code, name in [
    ("KOR", "Korea"),
    ("CHN", "China"),
    ("VNM", "Vietnam"),
    ("BWA", "Botswana"),
    ("THA", "Thailand"),
    ("IDN", "Indonesia"),
]:
    cdata = wdi[
        (wdi["country_code"] == code)
        & wdi["gross_capital_formation_pct"].notna()
        & wdi["gdppc_ppp_current"].notna()
    ].sort_values("year")
    if len(cdata) > 0:
        # During transition period (GDP < $15k)
        transition = cdata[cdata["gdppc_ppp_current"] < 15000]
        if len(transition) > 0:
            transition_invest[name] = transition["gross_capital_formation_pct"].median()

# Add SSA average
ssa_med = latest_ssa["gross_capital_formation_pct"].dropna().median()
transition_invest["SSA (current)"] = ssa_med

names = list(transition_invest.keys())
vals = list(transition_invest.values())
colors_inv = ["steelblue"] * (len(names) - 1) + ["coral"]
bars = ax.barh(range(len(names)), vals, color=colors_inv, alpha=0.8)
for bar, val in zip(bars, vals):
    ax.text(
        bar.get_width() + 0.3,
        bar.get_y() + bar.get_height() / 2,
        f"{val:.1f}%",
        va="center",
        fontsize=10,
    )
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names)
ax.set_xlabel("Median investment rate during transition (% GDP)")
ax.set_title("Investment During High-Growth Transition\nvs SSA Today")
ax.axvline(x=25, color="green", linestyle="--", alpha=0.5, label="25% threshold")
ax.legend(fontsize=9)
ax.invert_yaxis()

# Panel D: What $15k requires — decomposing the path
ax = axes[1][1]
ax.axis("off")

requirements = [
    ["Component", "What It Means", "Can Transfers Help?"],
    [
        "Agricultural\nproductivity",
        "Green Revolution:\nhigher yields, freed labor",
        "No — needs seeds,\nirrigation, extension",
    ],
    [
        "Basic\ninfrastructure",
        "Roads, electricity,\nwater, sanitation",
        "No — public investment\nand planning required",
    ],
    [
        "Human capital",
        "Primary → secondary\neducation, health",
        "YES — conditional transfers\nimprove school attendance\nand nutrition",
    ],
    [
        "Institutional\ncapacity",
        "Tax collection, rule of law,\nproperty rights",
        "No — governance reform\nneeded",
    ],
    [
        "Structural\ntransformation",
        "Agriculture → industry\n→ services",
        "No — industrial policy,\ntrade, FDI needed",
    ],
    [
        "Demographic\ntransition",
        "Fertility decline,\nworking-age bulge",
        "Partially — health +\neducation → lower fertility",
    ],
    [
        "Domestic\nsavings",
        "25-35% of GDP invested\ndomestically",
        "No — need income growth\nfirst",
    ],
]

tbl = ax.table(
    cellText=requirements[1:],
    colLabels=requirements[0],
    loc="center",
    cellLoc="left",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(8)
tbl.scale(1.1, 2.0)

# Color the "Can Transfers Help?" column
for i in range(len(requirements) - 1):
    cell = tbl[i + 1, 2]
    text = requirements[i + 1][2]
    if text.startswith("No"):
        cell.set_facecolor("#ffcccc")
    elif text.startswith("YES"):
        cell.set_facecolor("#ccffcc")
    elif text.startswith("Partial"):
        cell.set_facecolor("#ffffcc")

ax.set_title(
    "The 7 Components of Reaching $15k:\nWhat Transfers Can and Cannot Do",
    fontweight="bold",
    pad=20,
)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "46_transfers_vs_development.png"), dpi=150)
plt.close()
print("  -> Saved 46_transfers_vs_development.png")


###############################################################################
# SYNTHESIS
###############################################################################
print("\n" + "=" * 70)
print("SYNTHESIS: TRANSFERS TO SELF-SUFFICIENCY")
print("=" * 70)

print(
    """
  THE EVIDENCE ON CASH TRANSFERS AND PRODUCTIVITY:

  1. UNCONDITIONAL CASH TRANSFERS (GiveDirectly-style):
     - Excellent at alleviating immediate poverty
     - Recipients invest 30-40% in productive assets (livestock, housing, tools)
     - Local economic multiplier of $2.60 per dollar (Egger et al. 2022)
     - BUT: gains primarily from asset accumulation, not enterprise innovation
     - Long-run productivity effects: modest. Income gains of ~$270/yr on $1,000
     - Does NOT build infrastructure, institutions, or industrial base

  2. GRADUATION PROGRAMS (BRAC/Banerjee et al.):
     - Asset transfer + skills training + savings + coaching + health
     - 6-country RCT: 38% income gains SUSTAINED 7+ years post-program
     - Cost: ~$1,500 per household (more than cash, but more durable)
     - Creates micro-enterprise capacity that persists
     - STILL doesn't address systemic barriers (infrastructure, macro policy)

  3. CONDITIONAL CASH TRANSFERS (Mexico Progresa, Brazil Bolsa Familia):
     - Conditions: school attendance, health visits
     - +0.7 years schooling, +8% next-generation earnings
     - THE HUMAN CAPITAL PATHWAY: nutrition → cognition → education → productivity
     - This IS a long-run productivity mechanism, via children
     - Takes a generation (20-30 years) to pay off

  KEY INSIGHT:
  Cash transfers can move people from extreme poverty ($2.15) to low-income ($5-6/day).
  They CANNOT build the institutional and physical infrastructure needed to reach $15k.
  
  No country has ever transferred its way to $15k GDP/capita. Every success required:
  1. Agricultural productivity revolution (freeing labor)
  2. Infrastructure investment (roads, electricity, ports)
  3. Human capital investment (education, health)
  4. Structural transformation (agriculture → manufacturing → services)
  5. Trade integration and industrial policy
  6. Demographic transition (falling fertility → working-age bulge)
  7. Domestic savings rate >25% of GDP
  
  Transfers help with #3 (via conditional transfers) and partially with #6.
  They don't address #1, #2, #4, #5, or #7.
  
  THE REAL ANSWER: Transfers and development are sequential, not alternatives.
  - Phase 1: Cash/graduation transfers → escape extreme poverty trap
  - Phase 2: Public investment → infrastructure, institutions, human capital
  - Phase 3: Market-driven structural transformation → self-sustaining growth
  
  The danger of permanent transfer dependency is REAL:
  - The entire global ODA system delivers ~$203B/yr
  - One US election cycle can cut this dramatically
  - Countries dependent on external transfers have no sovereign path to prosperity
  - Self-sufficiency at $15k is the only durable outcome
"""
)
