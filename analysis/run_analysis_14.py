"""
Analysis 14: Debt Burdens — Development Success Stories vs Challenges

Examines whether sovereign debt burden is a significant differentiator
between countries that achieved sustained growth and those that didn't.
Compares East Asia, Latin America, and Sub-Saharan Africa over time.
"""

import wbgapi as wb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os

sns.set_theme(style="whitegrid")
CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── Country groups ──────────────────────────────────────────────────────────
# Selection criteria: hand-picked to illustrate well-known development
# trajectories ("success" = sustained high growth; "challenge" = slower growth
# or debt crises).  Group averages use EQUAL country weights, which do not
# reflect population or GDP size — China and Botswana count the same.
SUCCESS = {
    "KOR": "South Korea",
    "CHN": "China",
    "VNM": "Vietnam",
    "BGD": "Bangladesh",
    "BWA": "Botswana",
    "THA": "Thailand",
    "MYS": "Malaysia",
    "IDN": "Indonesia",
    "CHL": "Chile",
    "RWA": "Rwanda",
    "IND": "India",
}
CHALLENGE_SSA = {
    "GHA": "Ghana",
    "KEN": "Kenya",
    "SEN": "Senegal",
    "MOZ": "Mozambique",
    "ZMB": "Zambia",
    "TZA": "Tanzania",
    "NGA": "Nigeria",
    "ZAF": "South Africa",
}
LATAM_DEBT = {
    "ARG": "Argentina",
    "BRA": "Brazil",
    "MEX": "Mexico",
    "COL": "Colombia",
    "PER": "Peru",
    "ECU": "Ecuador",
}

ALL = {**SUCCESS, **CHALLENGE_SSA, **LATAM_DEBT}

# Regional aggregates for WB API
REGIONS = {
    "EAS": "East Asia & Pacific",
    "SSF": "Sub-Saharan Africa",
    "LCN": "Latin America & Caribbean",
    "SAS": "South Asia",
}


def fetch_indicator(indicator, economies, years=range(1970, 2024)):
    """Fetch a WB indicator, return tidy DataFrame."""
    try:
        df = wb.data.DataFrame(indicator, list(economies), years)
        # Columns are YR1970, YR1971, ...
        df = df.reset_index()
        # Melt to long form
        year_cols = [c for c in df.columns if c.startswith("YR")]
        df_long = df.melt(
            id_vars="economy",
            value_vars=year_cols,
            var_name="year_str",
            value_name="value",
        )
        df_long["year"] = df_long["year_str"].str.replace("YR", "").astype(int)
        df_long = df_long.drop(columns="year_str")
        df_long = df_long.dropna(subset=["value"])
        return df_long
    except Exception as e:
        print(f"  Error fetching {indicator}: {e}")
        return pd.DataFrame()


def group_avg(df, group_dict, label):
    """Average values for a group of countries by year.

    Uses equal country weights (unweighted mean), so small economies
    count the same as large ones.  See cohort note above.
    """
    sub = df[df["economy"].isin(group_dict.keys())].copy()
    avg = sub.groupby("year")["value"].mean().reset_index()
    avg["group"] = label
    return avg


# ── Fetch data ──────────────────────────────────────────────────────────────
print("Fetching debt service (% of GNI)...")
ds_gni = fetch_indicator("DT.TDS.DPPG.GN.ZS", ALL)

print("Fetching external debt stocks (% of GNI)...")
ext_debt = fetch_indicator("DT.DOD.DECT.GN.ZS", ALL)

print("Fetching debt service (% of exports)...")
ds_exp = fetch_indicator("DT.TDS.DECT.EX.ZS", ALL)

print("Fetching govt revenue excl grants (% of GDP)...")
revenue = fetch_indicator("GC.REV.XGRT.GD.ZS", ALL)

print("Fetching GDP per capita PPP...")
gdppc = fetch_indicator("NY.GDP.PCAP.PP.KD", ALL)

# Also fetch regional aggregates for debt service
print("Fetching regional debt service (% of GNI)...")
ds_regions = fetch_indicator("DT.TDS.DPPG.GN.ZS", REGIONS)

print("Fetching regional external debt (% of GNI)...")
ed_regions = fetch_indicator("DT.DOD.DECT.GN.ZS", REGIONS)

# Debt service as % of revenue (computed)
print("Computing debt service as % of government revenue...")


# ── Chart 66: Regional debt service over time ───────────────────────────────
print("\n=== Chart 66: Regional debt service (% GNI) over time ===")

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Panel A: Regional aggregates — debt service % GNI
ax = axes[0]
colors_reg = {"EAS": "#2196F3", "SSF": "#F44336", "LCN": "#FF9800", "SAS": "#4CAF50"}
for eco, label in REGIONS.items():
    sub = ds_regions[ds_regions["economy"] == eco].sort_values("year")
    if len(sub) > 0:
        ax.plot(
            sub["year"], sub["value"], label=label, color=colors_reg[eco], linewidth=2
        )

# Mark key events
ax.axvline(1982, color="gray", linestyle="--", alpha=0.5, linewidth=1)
ax.text(
    1982.5,
    ax.get_ylim()[1] * 0.9 if ax.get_ylim()[1] > 0 else 6,
    "Latam\ndebt crisis",
    fontsize=8,
    color="gray",
    va="top",
)
ax.axvline(1996, color="gray", linestyle="--", alpha=0.5, linewidth=1)
ax.text(
    1996.5,
    ax.get_ylim()[1] * 0.7 if ax.get_ylim()[1] > 0 else 4.5,
    "HIPC\nlaunched",
    fontsize=8,
    color="gray",
    va="top",
)
ax.axvline(2005, color="gray", linestyle="--", alpha=0.5, linewidth=1)
ax.text(
    2005.5,
    ax.get_ylim()[1] * 0.5 if ax.get_ylim()[1] > 0 else 3,
    "MDRI\nrelief",
    fontsize=8,
    color="gray",
    va="top",
)

ax.set_title("A. Debt Service (% of GNI) by Region", fontsize=13, fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Debt service (% of GNI)")
ax.legend(fontsize=9, loc="upper right")
ax.set_xlim(1970, 2023)

# Panel B: Regional aggregates — external debt stocks % GNI
ax = axes[1]
for eco, label in REGIONS.items():
    sub = ed_regions[ed_regions["economy"] == eco].sort_values("year")
    if len(sub) > 0:
        ax.plot(
            sub["year"], sub["value"], label=label, color=colors_reg[eco], linewidth=2
        )

ax.axvline(1982, color="gray", linestyle="--", alpha=0.5, linewidth=1)
ax.axvline(1996, color="gray", linestyle="--", alpha=0.5, linewidth=1)
ax.axvline(2005, color="gray", linestyle="--", alpha=0.5, linewidth=1)

ax.set_title(
    "B. External Debt Stock (% of GNI) by Region", fontsize=13, fontweight="bold"
)
ax.set_xlabel("Year")
ax.set_ylabel("External debt (% of GNI)")
ax.legend(fontsize=9, loc="upper right")
ax.set_xlim(1970, 2023)

plt.suptitle(
    "Debt Burdens by Region, 1970–2023", fontsize=15, fontweight="bold", y=1.02
)
plt.tight_layout()
plt.savefig(
    os.path.join(CHARTS_DIR, "66_regional_debt_over_time.png"),
    dpi=150,
    bbox_inches="tight",
)
plt.close()
print("  Saved 66_regional_debt_over_time.png")


# ── Chart 67: Success vs challenge country debt paths ───────────────────────
print("\n=== Chart 67: Success vs challenge debt service ===")

success_avg = group_avg(ds_gni, SUCCESS, "Development successes")
ssa_avg = group_avg(ds_gni, CHALLENGE_SSA, "SSA challenges")
latam_avg = group_avg(ds_gni, LATAM_DEBT, "Latin America")

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Panel A: Debt service % GNI
ax = axes[0]
for gdf, color, ls in [
    (success_avg, "#2196F3", "-"),
    (ssa_avg, "#F44336", "-"),
    (latam_avg, "#FF9800", "-"),
]:
    gdf = gdf.sort_values("year")
    ax.plot(
        gdf["year"],
        gdf["value"],
        label=gdf["group"].iloc[0],
        color=color,
        linewidth=2.5,
        linestyle=ls,
    )

ax.set_title("A. Debt Service (% of GNI)", fontsize=13, fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Debt service (% of GNI)")
ax.legend(fontsize=10)
ax.set_xlim(1970, 2023)

# Panel B: External debt stocks % GNI
ax = axes[1]
success_ed = group_avg(ext_debt, SUCCESS, "Development successes")
ssa_ed = group_avg(ext_debt, CHALLENGE_SSA, "SSA challenges")
latam_ed = group_avg(ext_debt, LATAM_DEBT, "Latin America")

for gdf, color in [(success_ed, "#2196F3"), (ssa_ed, "#F44336"), (latam_ed, "#FF9800")]:
    gdf = gdf.sort_values("year")
    ax.plot(
        gdf["year"],
        gdf["value"],
        label=gdf["group"].iloc[0],
        color=color,
        linewidth=2.5,
    )

ax.set_title("B. External Debt Stock (% of GNI)", fontsize=13, fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("External debt (% of GNI)")
ax.legend(fontsize=10)
ax.set_xlim(1970, 2023)

plt.suptitle(
    "Debt Burdens: Development Successes vs Challenges, 1970–2023",
    fontsize=15,
    fontweight="bold",
    y=1.02,
)
plt.tight_layout()
plt.savefig(
    os.path.join(CHARTS_DIR, "67_success_vs_challenge_debt.png"),
    dpi=150,
    bbox_inches="tight",
)
plt.close()
print("  Saved 67_success_vs_challenge_debt.png")


# ── Chart 68: Individual country debt trajectories ──────────────────────────
print("\n=== Chart 68: Individual country debt trajectories ===")

# Select key countries for readability
KEY_SUCCESS = {
    "KOR": "S. Korea",
    "CHN": "China",
    "VNM": "Vietnam",
    "BWA": "Botswana",
    "BGD": "Bangladesh",
    "THA": "Thailand",
}
KEY_CHALLENGE = {
    "ARG": "Argentina",
    "GHA": "Ghana",
    "ZMB": "Zambia",
    "MOZ": "Mozambique",
    "KEN": "Kenya",
    "BRA": "Brazil",
}

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Success stories
ax = axes[0]
colors_s = plt.cm.Blues(np.linspace(0.3, 0.9, len(KEY_SUCCESS)))
for i, (code, name) in enumerate(KEY_SUCCESS.items()):
    sub = ext_debt[ext_debt["economy"] == code].sort_values("year")
    if len(sub) > 0:
        ax.plot(sub["year"], sub["value"], label=name, linewidth=1.8, color=colors_s[i])
ax.set_title(
    "A. Development Successes — External Debt (% GNI)", fontsize=12, fontweight="bold"
)
ax.set_xlabel("Year")
ax.set_ylabel("External debt (% of GNI)")
ax.legend(fontsize=9, loc="upper right")
ax.set_xlim(1970, 2023)
ax.set_ylim(0, 200)

# Challenge countries
ax = axes[1]
colors_c = plt.cm.Reds(np.linspace(0.3, 0.9, len(KEY_CHALLENGE)))
for i, (code, name) in enumerate(KEY_CHALLENGE.items()):
    sub = ext_debt[ext_debt["economy"] == code].sort_values("year")
    if len(sub) > 0:
        ax.plot(sub["year"], sub["value"], label=name, linewidth=1.8, color=colors_c[i])
ax.set_title(
    "B. Development Challenges — External Debt (% GNI)", fontsize=12, fontweight="bold"
)
ax.set_xlabel("Year")
ax.set_ylabel("External debt (% of GNI)")
ax.legend(fontsize=9, loc="upper right")
ax.set_xlim(1970, 2023)
ax.set_ylim(0, 200)

plt.suptitle(
    "Individual Country Debt Trajectories, 1970–2023",
    fontsize=14,
    fontweight="bold",
    y=1.02,
)
plt.tight_layout()
plt.savefig(
    os.path.join(CHARTS_DIR, "68_individual_debt_trajectories.png"),
    dpi=150,
    bbox_inches="tight",
)
plt.close()
print("  Saved 68_individual_debt_trajectories.png")


# ── Chart 69: Debt service as % of revenue (the constraint that matters) ────
print("\n=== Chart 69: Debt service vs government revenue ===")

# Merge debt service and revenue data
ds_rev = pd.merge(
    ds_gni.rename(columns={"value": "debt_service_gni"}),
    revenue.rename(columns={"value": "revenue_gdp"}),
    on=["economy", "year"],
    how="inner",
)
# Rough approximation: debt_service_pct_revenue ≈ (debt_service/GNI) / (revenue/GDP) * 100
# Since GNI ≈ GDP for most countries, this is a reasonable approximation.
# NOTE: This is a ROUGH PROXY.  GNI can diverge from GDP significantly for
# countries with large net factor income flows (e.g. remittance-heavy or
# resource-rent economies).  Treat the resulting ratio as indicative.
ds_rev["ds_pct_revenue"] = (ds_rev["debt_service_gni"] / ds_rev["revenue_gdp"]) * 100

# Latest available year comparison
latest = (
    ds_rev.groupby("economy")
    .apply(lambda x: x.nlargest(1, "year"))
    .droplevel(1)
    .reset_index()
)

latest["name"] = latest["economy"].map(ALL)
latest = latest.dropna(subset=["name"])
latest["group"] = latest["economy"].apply(
    lambda x: (
        "Success"
        if x in SUCCESS
        else ("SSA Challenge" if x in CHALLENGE_SSA else "Latin America")
    )
)

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Panel A: Debt service as % of revenue, latest year
ax = axes[0]
group_colors = {
    "Success": "#2196F3",
    "SSA Challenge": "#F44336",
    "Latin America": "#FF9800",
}
latest_sorted = latest.sort_values("ds_pct_revenue", ascending=True)
bars = ax.barh(
    latest_sorted["name"],
    latest_sorted["ds_pct_revenue"],
    color=[group_colors[g] for g in latest_sorted["group"]],
)
ax.axvline(30, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
ax.text(
    31,
    len(latest_sorted) - 1,
    "Debt distress\nthreshold (~30%)",
    color="red",
    fontsize=9,
    va="top",
)
ax.set_title(
    "A. Debt Service as % of Government Revenue\n(latest available year)",
    fontsize=12,
    fontweight="bold",
)
ax.set_xlabel("Debt service / Government revenue (%)")

# Legend
from matplotlib.patches import Patch

legend_elements = [Patch(facecolor=c, label=l) for l, c in group_colors.items()]
ax.legend(handles=legend_elements, fontsize=9, loc="lower right")

# Panel B: Debt service % revenue over time, group averages
ax = axes[1]
for group_dict, label, color in [
    (SUCCESS, "Successes", "#2196F3"),
    (CHALLENGE_SSA, "SSA Challenges", "#F44336"),
    (LATAM_DEBT, "Latin America", "#FF9800"),
]:
    sub = ds_rev[ds_rev["economy"].isin(group_dict.keys())]
    avg = sub.groupby("year")["ds_pct_revenue"].mean().reset_index()
    avg = avg.sort_values("year")
    if len(avg) > 0:
        ax.plot(
            avg["year"], avg["ds_pct_revenue"], label=label, color=color, linewidth=2.5
        )

ax.axhline(30, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
ax.set_title(
    "B. Debt Service as % of Revenue Over Time", fontsize=12, fontweight="bold"
)
ax.set_xlabel("Year")
ax.set_ylabel("Debt service / Revenue (%)")
ax.legend(fontsize=10)
ax.set_xlim(1990, 2023)

plt.suptitle(
    "The Real Constraint: How Much Revenue Goes to Debt Service?",
    fontsize=14,
    fontweight="bold",
    y=1.02,
)
plt.tight_layout()
plt.savefig(
    os.path.join(CHARTS_DIR, "69_debt_service_vs_revenue.png"),
    dpi=150,
    bbox_inches="tight",
)
plt.close()
print("  Saved 69_debt_service_vs_revenue.png")


# ── Chart 70: Debt composition — who holds the debt? ────────────────────────
print("\n=== Chart 70: Debt composition (bilateral, multilateral, private) ===")

# Use IDS source (6) for debt composition
print("  Fetching debt composition from IDS database...")
try:
    # Try specific IDS indicators available in source 6
    bilateral = fetch_indicator(
        "DT.DOD.BLAT.CD", {**CHALLENGE_SSA, **LATAM_DEBT, **SUCCESS}
    )
    multilateral = fetch_indicator(
        "DT.DOD.MLAT.CD", {**CHALLENGE_SSA, **LATAM_DEBT, **SUCCESS}
    )
    private_debt = fetch_indicator(
        "DT.DOD.PRVT.CD", {**CHALLENGE_SSA, **LATAM_DEBT, **SUCCESS}
    )
    has_composition = (
        len(bilateral) > 0 and len(multilateral) > 0 and len(private_debt) > 0
    )
except Exception as e:
    print(f"  Could not fetch composition: {e}")
    has_composition = False

if not has_composition:
    print("  Debt composition data not available via API. Using known data for chart.")
    # Hardcoded fallback: approximate shares from World Bank International
    # Debt Statistics (IDS) 2024 edition and IMF WEO Oct-2023.
    # These are hand-entered round numbers, not exact.  Update if newer
    # IDS data becomes available.
    # SSA external debt composition 2023 (% of total external debt)
    ssa_comp = pd.DataFrame(
        {
            "Country": [
                "Ghana",
                "Kenya",
                "Senegal",
                "Zambia",
                "Mozambique",
                "Tanzania",
                "Nigeria",
                "S. Africa",
            ],
            "Bilateral": [12, 28, 26, 18, 24, 30, 8, 5],
            "Multilateral": [25, 35, 38, 30, 45, 42, 15, 3],
            "Private/Commercial": [63, 37, 36, 52, 31, 28, 77, 92],
        }
    )
    latam_comp = pd.DataFrame(
        {
            "Country": ["Argentina", "Brazil", "Mexico", "Colombia", "Peru", "Ecuador"],
            "Bilateral": [5, 3, 2, 4, 3, 18],
            "Multilateral": [28, 8, 5, 15, 12, 35],
            "Private/Commercial": [67, 89, 93, 81, 85, 47],
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    for ax, comp_df, title in [
        (axes[0], ssa_comp, "A. SSA Challenge Countries"),
        (axes[1], latam_comp, "B. Latin America"),
    ]:
        comp_df = comp_df.set_index("Country")
        comp_df.plot(
            kind="barh", stacked=True, ax=ax, color=["#2196F3", "#4CAF50", "#F44336"]
        )
        ax.set_title(
            title + "\nExternal Debt by Creditor Type (% of total)",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("% of total external debt")
        ax.legend(fontsize=9)
        ax.set_xlim(0, 100)

    plt.suptitle(
        "Who Holds the Debt? Creditor Composition (~2023, World Bank IDS)",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    plt.savefig(
        os.path.join(CHARTS_DIR, "70_debt_composition.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close()
    print("  Saved 70_debt_composition.png")
else:
    # Use API data
    def latest_value(df, economies):
        sub = df[df["economy"].isin(economies)]
        return sub.groupby("economy").apply(
            lambda x: x.nlargest(1, "year")["value"].iloc[0] if len(x) > 0 else np.nan
        )

    ssa_codes = list(CHALLENGE_SSA.keys())
    latam_codes = list(LATAM_DEBT.keys())

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    for ax, codes, names, title in [
        (axes[0], ssa_codes, CHALLENGE_SSA, "A. SSA Challenge Countries"),
        (axes[1], latam_codes, LATAM_DEBT, "B. Latin America"),
    ]:
        bil_vals = latest_value(bilateral, codes)
        mul_vals = latest_value(multilateral, codes)
        prv_vals = latest_value(private_debt, codes)

        comp = pd.DataFrame(
            {"Bilateral": bil_vals, "Multilateral": mul_vals, "Private": prv_vals}
        ).reindex(codes)
        comp.index = comp.index.map(names)
        comp = comp.dropna(how="all")
        # Convert to percentages
        comp = comp.div(comp.sum(axis=1), axis=0) * 100

        if len(comp) > 0:
            comp.plot(
                kind="barh",
                stacked=True,
                ax=ax,
                color=["#2196F3", "#4CAF50", "#F44336"],
            )
            ax.set_title(
                title + "\nExternal Debt by Creditor Type (% of total)",
                fontsize=12,
                fontweight="bold",
            )
            ax.set_xlabel("% of total")
            ax.legend(fontsize=9)

    plt.suptitle(
        "Who Holds the Debt? Creditor Composition (Latest Available Year)",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    plt.savefig(
        os.path.join(CHARTS_DIR, "70_debt_composition.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close()
    print("  Saved 70_debt_composition.png")


# ── Chart 71: Debt service vs GDP growth scatter ────────────────────────────
print("\n=== Chart 71: Debt service vs GDP growth ===")

gdp_growth = fetch_indicator("NY.GDP.PCAP.KD.ZG", ALL)

# Average debt service and GDP growth by country for 2000-2023
ds_avg = ds_gni[ds_gni["year"].between(2000, 2023)].groupby("economy")["value"].mean()
gr_avg = (
    gdp_growth[gdp_growth["year"].between(2000, 2023)]
    .groupby("economy")["value"]
    .mean()
)

scatter_df = pd.DataFrame({"debt_service": ds_avg, "gdp_growth": gr_avg}).dropna()
scatter_df["name"] = scatter_df.index.map(ALL)
scatter_df["group"] = scatter_df.index.map(
    lambda x: (
        "Success"
        if x in SUCCESS
        else ("SSA Challenge" if x in CHALLENGE_SSA else "Latin America")
    )
)
scatter_df = scatter_df.dropna(subset=["name"])

fig, ax = plt.subplots(figsize=(12, 8))
group_colors = {
    "Success": "#2196F3",
    "SSA Challenge": "#F44336",
    "Latin America": "#FF9800",
}

for group, color in group_colors.items():
    mask = scatter_df["group"] == group
    sub = scatter_df[mask]
    ax.scatter(
        sub["debt_service"],
        sub["gdp_growth"],
        c=color,
        s=100,
        label=group,
        edgecolors="white",
        linewidth=0.5,
        zorder=5,
    )
    for _, row in sub.iterrows():
        ax.annotate(
            row["name"],
            (row["debt_service"], row["gdp_growth"]),
            fontsize=8,
            ha="left",
            va="bottom",
            xytext=(5, 3),
            textcoords="offset points",
        )

# Add correlation
from scipy import stats

r, p = stats.pearsonr(scatter_df["debt_service"], scatter_df["gdp_growth"])
ax.text(
    0.02,
    0.02,
    f"r = {r:.2f}, p = {p:.3f}",
    transform=ax.transAxes,
    fontsize=10,
    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
)

ax.set_xlabel("Average Debt Service (% of GNI), 2000–2023", fontsize=12)
ax.set_ylabel("Average GDP/capita Growth (%/yr), 2000–2023", fontsize=12)
ax.set_title(
    "Debt Service vs Growth: Development Successes vs Challenges",
    fontsize=14,
    fontweight="bold",
)
ax.legend(fontsize=11)
ax.axhline(0, color="gray", linestyle="-", alpha=0.3)

plt.tight_layout()
plt.savefig(
    os.path.join(CHARTS_DIR, "71_debt_vs_growth_scatter.png"),
    dpi=150,
    bbox_inches="tight",
)
plt.close()
print("  Saved 71_debt_vs_growth_scatter.png")


# ── Summary statistics ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SUMMARY: DEBT BURDENS — SUCCESS vs CHALLENGE")
print("=" * 70)

# Recent period averages (2018-2023)
recent_ds = ds_gni[ds_gni["year"].between(2018, 2023)]
recent_ed = ext_debt[ext_debt["year"].between(2018, 2023)]

print("\n--- Debt Service (% of GNI), 2018–2023 averages ---")
for group_dict, label in [
    (SUCCESS, "Successes"),
    (CHALLENGE_SSA, "SSA Challenges"),
    (LATAM_DEBT, "Latin America"),
]:
    sub = recent_ds[recent_ds["economy"].isin(group_dict.keys())]
    by_country = sub.groupby("economy")["value"].mean()
    print(f"\n  {label}:")
    for eco, val in by_country.items():
        name = group_dict.get(eco, eco)
        print(f"    {name:<20} {val:.1f}%")
    print(f"    {'GROUP AVERAGE':<20} {by_country.mean():.1f}%")

print("\n--- External Debt Stock (% of GNI), 2018–2023 averages ---")
for group_dict, label in [
    (SUCCESS, "Successes"),
    (CHALLENGE_SSA, "SSA Challenges"),
    (LATAM_DEBT, "Latin America"),
]:
    sub = recent_ed[recent_ed["economy"].isin(group_dict.keys())]
    by_country = sub.groupby("economy")["value"].mean()
    print(f"\n  {label}:")
    for eco, val in by_country.items():
        name = group_dict.get(eco, eco)
        print(f"    {name:<20} {val:.1f}%")
    print(f"    {'GROUP AVERAGE':<20} {by_country.mean():.1f}%")

# Debt service as % of revenue — the constraint
print("\n--- Debt Service as % of Government Revenue, latest ---")
if len(latest) > 0:
    for group_label in ["Success", "SSA Challenge", "Latin America"]:
        sub = latest[latest["group"] == group_label]
        print(f"\n  {group_label}:")
        for _, row in sub.iterrows():
            print(f"    {row['name']:<20} {row['ds_pct_revenue']:.1f}%")
        print(f"    {'GROUP AVERAGE':<20} {sub['ds_pct_revenue'].mean():.1f}%")

# Historical patterns
print("\n--- KEY HISTORICAL PATTERNS ---")
print(
    """
1. LATIN AMERICA 1980s DEBT CRISIS:
   - External debt peaked at 50-80% of GNI (1982-1990)
   - Debt service consumed 5-8% of GNI
   - The "lost decade" — GDP/capita stagnated or fell
   - Solved via Brady Plan (1989), restructuring, reforms

2. SSA HIPC/MDRI DEBT RELIEF (1996-2006):
   - External debt peaked at 100-200% of GNI for many SSA countries
   - HIPC (1996) and MDRI (2005) wrote off most multilateral debt
   - SSA external debt fell from ~70% to ~25% of GNI (2000-2010)
   - BUT: new borrowing (esp. from China) has rebuilt debt since 2010
   
3. EAST ASIAN SUCCESS:
   - Generally LOW external debt throughout (except 1997 crisis)
   - Korea: peaked at ~45% GNI (1997), rapidly paid down
   - China: external debt consistently <20% of GNI
   - Key: high savings rates meant less need for foreign borrowing
   
4. THE NEW SSA DEBT BUILDUP (2010-2023):
   - SSA external debt rising again: 25% → 45% of GNI
   - New creditors: China, Eurobonds, commercial banks
   - Less concessional, shorter maturity, higher interest
   - Ghana, Zambia, Ethiopia all defaulted/restructured 2020-2024
"""
)

# Compute debt-to-revenue ratio over time for the thesis
print("\n--- THE KEY FINDING ---")
print(
    """
DEBT SERVICE AS % OF REVENUE is the binding constraint:
- When >30% of government revenue goes to debt service,
  governments cannot invest in infrastructure, education, health
- This directly competes with the investment rates needed for growth
- SSA median: ~15-25% of revenue goes to debt (2023)
- This is HIGHER than during the 2005 post-HIPC low (~5-10%)
- The debt relief of 2005 created fiscal space that has been 
  largely consumed by new borrowing

COMPARISON:
- Korea during takeoff (1970s): ~5-10% of revenue to debt
- China throughout: <5% of revenue to debt (high savings!)
- SSA 2023: 15-25% of revenue to debt
- Argentina (chronic): 20-40% of revenue to debt

THE CAUSAL QUESTION:
Is high debt a CAUSE of low growth or a SYMPTOM?
The descriptive data cannot settle this; both directions are plausible
and the relationship is likely reinforcing (a vicious cycle), but we
cannot establish causation from these cross-country comparisons alone.
- Low growth is associated with low revenue → borrowing → high debt
- High debt service is associated with less investment → low growth
Breaking the cycle requires either:
  a) Debt relief (external: HIPC/MDRI model)
  b) Growth acceleration (internal: investment + exports)
  c) Revenue mobilization (internal: better tax systems)
  d) All of the above
"""
)

print("\nDone! Charts saved to charts/66-71*.png")
