"""
Analysis 15: IMF & World Bank — Help or Harm?

Key questions:
1. Do countries that relied heavily on IMF programs grow faster or slower?
2. The 1997 Asian crisis natural experiment: Korea/Thailand/Indonesia (IMF) vs Malaysia (rejected IMF)
3. Did structural adjustment (1980s-90s) improve or damage African growth?
4. Social spending before/during/after IMF program eras
5. The "repeat customer" puzzle: do frequent IMF users grow more?

Uses World Bank / WDI data via wbgapi.
"""

import wbgapi as wb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import os

sns.set_theme(style="whitegrid")
CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── Country groups ──────────────────────────────────────────────────────────
# IMF-heavy: countries that had many/frequent IMF programs since 1980
IMF_HEAVY = {
    "ARG": "Argentina",
    "GHA": "Ghana",
    "JAM": "Jamaica",
    "PAK": "Pakistan",
    "KEN": "Kenya",
    "ZMB": "Zambia",
    "SEN": "Senegal",
    "ECU": "Ecuador",
    "JOR": "Jordan",
    "PHL": "Philippines",
}

# IMF-light/none: successful developers that avoided or minimally used IMF
IMF_LIGHT = {
    "CHN": "China",
    "VNM": "Vietnam",
    "IND": "India",
    "BWA": "Botswana",
    "MYS": "Malaysia",
    "THA": "Thailand",  # Used IMF in 1997 but rarely otherwise
    "CHL": "Chile",     # Used IMF in 1980s but reformed independently
    "BGD": "Bangladesh",
    "RWA": "Rwanda",
    "IDN": "Indonesia",
}

# 1997 Asian crisis: IMF program vs no program
ASIAN_IMF = {
    "KOR": "S. Korea (IMF)",
    "THA": "Thailand (IMF)",
    "IDN": "Indonesia (IMF)",
}
ASIAN_NO_IMF = {
    "MYS": "Malaysia (no IMF)",
    "CHN": "China (no crisis)",
    "VNM": "Vietnam (no crisis)",
}

# Sub-Saharan Africa: for structural adjustment era comparison
SSA_COUNTRIES = {
    "GHA": "Ghana", "KEN": "Kenya", "SEN": "Senegal", "TZA": "Tanzania",
    "ZMB": "Zambia", "MOZ": "Mozambique", "NGA": "Nigeria", "UGA": "Uganda",
    "ETH": "Ethiopia", "MLI": "Mali", "BFA": "Burkina Faso", "MWI": "Malawi",
    "CMR": "Cameroon", "CIV": "Côte d'Ivoire", "MDG": "Madagascar",
}

# ── Data fetching ───────────────────────────────────────────────────────────
ALL_COUNTRIES = list(set(
    list(IMF_HEAVY.keys()) + list(IMF_LIGHT.keys()) +
    list(ASIAN_IMF.keys()) + list(ASIAN_NO_IMF.keys()) +
    list(SSA_COUNTRIES.keys())
))

INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "GDP per capita (PPP, constant 2021$)",
    "NY.GDP.PCAP.KD.ZG": "GDP per capita growth (%)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (%)",
    "SH.XPD.CHEX.GD.ZS": "Health expenditure (% GDP)",
    "SE.XPD.TOTL.GD.ZS": "Education expenditure (% GDP)",
    "GC.XPN.TOTL.GD.ZS": "Government expenditure (% GDP)",
    "NE.GDI.TOTL.ZS": "Gross capital formation (% GDP)",
    "BN.CAB.XOKA.GD.ZS": "Current account (% GDP)",
}

print("Fetching data from World Bank...")
data = {}
for code, label in INDICATORS.items():
    try:
        df = wb.data.DataFrame(code, ALL_COUNTRIES, range(1970, 2024), labels=True)
        if not df.empty:
            # Reshape: rows are country, columns are years
            df = df.drop(columns=["Country"], errors="ignore")
            # Columns are like 'YR1970', 'YR1971', etc
            df.columns = [int(c.replace("YR", "")) if "YR" in str(c) else c for c in df.columns]
            data[code] = df
            print(f"  ✓ {label}: {df.shape}")
    except Exception as e:
        print(f"  ✗ {label}: {e}")


def get_country_series(indicator, country_code, years=None):
    """Get a time series for one country from fetched data."""
    if indicator not in data:
        return pd.Series(dtype=float)
    df = data[indicator]
    if country_code not in df.index:
        return pd.Series(dtype=float)
    s = df.loc[country_code].dropna()
    s.index = s.index.astype(int)
    if years:
        s = s.reindex(years)
    return s


def get_group_avg(indicator, country_dict, year_start, year_end):
    """Get group average for an indicator over a year range."""
    years = list(range(year_start, year_end + 1))
    vals = []
    for cc in country_dict:
        s = get_country_series(indicator, cc, years)
        avg = s.mean()
        if not np.isnan(avg):
            vals.append(avg)
    return np.mean(vals) if vals else np.nan


def get_group_timeseries(indicator, country_dict, year_start, year_end):
    """Get group average time series."""
    years = list(range(year_start, year_end + 1))
    all_series = []
    for cc in country_dict:
        s = get_country_series(indicator, cc, years)
        if not s.empty:
            all_series.append(s)
    if not all_series:
        return pd.Series(dtype=float)
    df = pd.DataFrame(all_series)
    return df.mean(axis=0)


# ═══════════════════════════════════════════════════════════════════════════
# CHART 72: IMF-Heavy vs IMF-Light GDP per capita trajectories
# ═══════════════════════════════════════════════════════════════════════════
print("\n── Chart 72: IMF-Heavy vs IMF-Light growth trajectories ──")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Panel A: Group average GDP per capita (indexed to 1990 = 100)
ax = axes[0]
for group_name, group_dict, color in [
    ("IMF-heavy (10 countries)", IMF_HEAVY, "#d32f2f"),
    ("IMF-light/none (10 countries)", IMF_LIGHT, "#1976d2"),
]:
    ts = get_group_timeseries("NY.GDP.PCAP.PP.KD", group_dict, 1990, 2023)
    if not ts.empty and 1990 in ts.index:
        indexed = (ts / ts[1990]) * 100
        ax.plot(indexed.index, indexed.values, lw=2.5, label=group_name, color=color)

ax.set_xlabel("Year")
ax.set_ylabel("GDP per capita (indexed, 1990 = 100)")
ax.set_title("A. GDP per capita since 1990 (indexed)")
ax.legend(fontsize=9)
ax.axhline(100, color="gray", ls="--", alpha=0.3)

# Panel B: Average GDP per capita growth by decade
ax = axes[1]
decades = [("1980s", 1980, 1989), ("1990s", 1990, 1999), ("2000s", 2000, 2009), ("2010s", 2010, 2019)]
width = 0.35
x = np.arange(len(decades))
heavy_vals = []
light_vals = []
for label, ys, ye in decades:
    heavy_vals.append(get_group_avg("NY.GDP.PCAP.KD.ZG", IMF_HEAVY, ys, ye))
    light_vals.append(get_group_avg("NY.GDP.PCAP.KD.ZG", IMF_LIGHT, ys, ye))

bars1 = ax.bar(x - width/2, heavy_vals, width, label="IMF-heavy", color="#d32f2f", alpha=0.8)
bars2 = ax.bar(x + width/2, light_vals, width, label="IMF-light", color="#1976d2", alpha=0.8)
ax.set_xticks(x)
ax.set_xticklabels([d[0] for d in decades])
ax.set_ylabel("Avg GDP/capita growth (%/yr)")
ax.set_title("B. Average growth by decade")
ax.legend(fontsize=9)
ax.axhline(0, color="black", lw=0.5)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        if not np.isnan(h):
            ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width()/2, h),
                       xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)

fig.suptitle("IMF-Heavy vs IMF-Light Countries: Growth Trajectories",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "72_imf_heavy_vs_light_growth.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("  Saved chart 72")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 73: 1997 Asian Crisis — IMF vs No-IMF recovery
# ═══════════════════════════════════════════════════════════════════════════
print("\n── Chart 73: 1997 Asian Crisis natural experiment ──")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Panel A: GDP per capita indexed to 1996 = 100
ax = axes[0]
crisis_countries = {**ASIAN_IMF, **ASIAN_NO_IMF}
colors_crisis = {
    "KOR": ("#d32f2f", "-"), "THA": ("#e57373", "-"), "IDN": ("#ff8a80", "-"),
    "MYS": ("#1976d2", "--"), "CHN": ("#64b5f6", "--"), "VNM": ("#90caf9", "--"),
}
for cc, name in crisis_countries.items():
    ts = get_country_series("NY.GDP.PCAP.PP.KD", cc, list(range(1994, 2010)))
    if not ts.empty and 1996 in ts.index:
        indexed = (ts / ts[1996]) * 100
        color, ls = colors_crisis[cc]
        ax.plot(indexed.index, indexed.values, lw=2, label=name, color=color, ls=ls)

ax.axvline(1997, color="gray", ls=":", lw=1, alpha=0.7)
ax.axvline(1998, color="gray", ls=":", lw=1, alpha=0.7)
ax.annotate("Crisis", xy=(1997.5, ax.get_ylim()[1] * 0.95 if ax.get_ylim()[1] > 100 else 95),
           ha="center", fontsize=9, color="gray")
ax.set_xlabel("Year")
ax.set_ylabel("GDP per capita (indexed, 1996 = 100)")
ax.set_title("A. GDP per capita recovery paths")
ax.legend(fontsize=8, loc="upper left")
ax.axhline(100, color="gray", ls="--", alpha=0.3)

# Panel B: GDP growth rates 1997-2003
ax = axes[1]
for cc, name in crisis_countries.items():
    ts = get_country_series("NY.GDP.PCAP.KD.ZG", cc, list(range(1995, 2005)))
    if not ts.empty:
        color, ls = colors_crisis[cc]
        ax.plot(ts.index, ts.values, lw=2, label=name, color=color, ls=ls, marker="o", ms=4)

ax.axvline(1997, color="gray", ls=":", lw=1, alpha=0.7)
ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Year")
ax.set_ylabel("GDP per capita growth (%)")
ax.set_title("B. Annual growth rates around the crisis")
ax.legend(fontsize=8, loc="lower right")

fig.suptitle("1997 Asian Financial Crisis: IMF Program vs No IMF Program",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "73_asian_crisis_imf_vs_no_imf.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("  Saved chart 73")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 74: SSA structural adjustment era — growth before/during/after
# ═══════════════════════════════════════════════════════════════════════════
print("\n── Chart 74: SSA growth across structural adjustment eras ──")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Panel A: SSA average GDP per capita growth by era
eras = [
    ("Pre-SAP\n1970–1979", 1970, 1979),
    ("SAP era\n1980–1999", 1980, 1999),
    ("Post-SAP\n2000–2014", 2000, 2014),
    ("Recent\n2015–2023", 2015, 2023),
]
ax = axes[0]
vals = []
stds = []
for label, ys, ye in eras:
    country_avgs = []
    for cc in SSA_COUNTRIES:
        s = get_country_series("NY.GDP.PCAP.KD.ZG", cc, list(range(ys, ye + 1)))
        if not s.empty:
            country_avgs.append(s.mean())
    vals.append(np.mean(country_avgs) if country_avgs else np.nan)
    stds.append(np.std(country_avgs) if country_avgs else np.nan)

colors_era = ["#4caf50", "#d32f2f", "#1976d2", "#ff9800"]
bars = ax.bar(range(len(eras)), vals, color=colors_era, alpha=0.8,
              yerr=stds, capsize=5, edgecolor="gray", linewidth=0.5)
ax.set_xticks(range(len(eras)))
ax.set_xticklabels([e[0] for e in eras])
ax.set_ylabel("Avg GDP/capita growth (%/yr)")
ax.set_title("A. SSA growth by era (15 countries)")
ax.axhline(0, color="black", lw=0.5)
for i, v in enumerate(vals):
    if not np.isnan(v):
        ax.annotate(f"{v:.1f}%", xy=(i, v), xytext=(0, 5 if v >= 0 else -15),
                   textcoords="offset points", ha="center", fontsize=10, fontweight="bold")

# Panel B: SSA investment rates by era
ax = axes[1]
inv_vals = []
for label, ys, ye in eras:
    inv_vals.append(get_group_avg("NE.GDI.TOTL.ZS", SSA_COUNTRIES, ys, ye))

bars2 = ax.bar(range(len(eras)), inv_vals, color=colors_era, alpha=0.8,
               edgecolor="gray", linewidth=0.5)
ax.set_xticks(range(len(eras)))
ax.set_xticklabels([e[0] for e in eras])
ax.set_ylabel("Gross capital formation (% GDP)")
ax.set_title("B. SSA investment rates by era")
for i, v in enumerate(inv_vals):
    if not np.isnan(v):
        ax.annotate(f"{v:.0f}%", xy=(i, v), xytext=(0, 5),
                   textcoords="offset points", ha="center", fontsize=10, fontweight="bold")

fig.suptitle("Sub-Saharan Africa: Growth Before, During, and After Structural Adjustment",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "74_ssa_structural_adjustment_eras.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("  Saved chart 74")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 75: Social spending — health & education during IMF program eras
# ═══════════════════════════════════════════════════════════════════════════
print("\n── Chart 75: Social spending patterns ──")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Panel A: Health expenditure trends
ax = axes[0]
for group_name, group_dict, color, ls in [
    ("IMF-heavy", IMF_HEAVY, "#d32f2f", "-"),
    ("IMF-light", IMF_LIGHT, "#1976d2", "--"),
]:
    ts = get_group_timeseries("SH.XPD.CHEX.GD.ZS", group_dict, 2000, 2021)
    if not ts.empty:
        ax.plot(ts.index, ts.values, lw=2.5, label=group_name, color=color, ls=ls)

ax.set_xlabel("Year")
ax.set_ylabel("Health expenditure (% GDP)")
ax.set_title("A. Health spending")
ax.legend(fontsize=9)

# Panel B: Education expenditure trends
ax = axes[1]
for group_name, group_dict, color, ls in [
    ("IMF-heavy", IMF_HEAVY, "#d32f2f", "-"),
    ("IMF-light", IMF_LIGHT, "#1976d2", "--"),
]:
    ts = get_group_timeseries("SE.XPD.TOTL.GD.ZS", group_dict, 2000, 2021)
    if not ts.empty:
        ax.plot(ts.index, ts.values, lw=2.5, label=group_name, color=color, ls=ls)

ax.set_xlabel("Year")
ax.set_ylabel("Education expenditure (% GDP)")
ax.set_title("B. Education spending")
ax.legend(fontsize=9)

fig.suptitle("Social Spending: IMF-Heavy vs IMF-Light Countries",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "75_social_spending_imf_groups.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("  Saved chart 75")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 76: The selection problem — scatter of initial GDP vs IMF reliance
# ═══════════════════════════════════════════════════════════════════════════
print("\n── Chart 76: The selection problem ──")

# For a broader sample, use all countries from both groups
all_study = {**IMF_HEAVY, **IMF_LIGHT}

fig, ax = plt.subplots(figsize=(10, 7))

# Get 1990 GDP/capita and 1990-2023 average growth
scatter_data = []
for cc, name in all_study.items():
    gdp_1990 = get_country_series("NY.GDP.PCAP.PP.KD", cc, [1990])
    growth_avg = get_country_series("NY.GDP.PCAP.KD.ZG", cc, list(range(1990, 2024)))
    if not gdp_1990.empty and not growth_avg.empty and 1990 in gdp_1990.index:
        group = "IMF-heavy" if cc in IMF_HEAVY else "IMF-light"
        scatter_data.append({
            "code": cc, "name": name,
            "gdp_1990": gdp_1990[1990],
            "avg_growth": growth_avg.mean(),
            "group": group,
        })

sdf = pd.DataFrame(scatter_data)
if not sdf.empty:
    for group, color, marker in [("IMF-heavy", "#d32f2f", "o"), ("IMF-light", "#1976d2", "^")]:
        gdf = sdf[sdf["group"] == group]
        ax.scatter(gdf["gdp_1990"], gdf["avg_growth"], c=color, marker=marker,
                  s=80, label=group, alpha=0.85, edgecolors="white", linewidth=0.5)
        for _, row in gdf.iterrows():
            ax.annotate(row["code"], (row["gdp_1990"], row["avg_growth"]),
                       xytext=(5, 3), textcoords="offset points", fontsize=7)

    ax.set_xlabel("GDP per capita in 1990 (PPP, constant 2021$)")
    ax.set_ylabel("Average GDP/capita growth 1990–2023 (%/yr)")
    ax.set_title("The Selection Problem: Countries Seek IMF Help Because They're In Crisis",
                fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)
    ax.axhline(0, color="black", lw=0.5)

    # Add note
    ax.text(0.02, 0.02,
            "Countries that relied heavily on IMF programs were generally poorer\n"
            "and more crisis-prone to begin with — making causal inference difficult.",
            transform=ax.transAxes, fontsize=8, va="bottom", style="italic",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3))

fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "76_imf_selection_problem.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("  Saved chart 76")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 77: IMF's own evolution — before and after "Neoliberalism: Oversold?"
# This compares investment rates and current account balances
# ═══════════════════════════════════════════════════════════════════════════
print("\n── Chart 77: Investment rates — IMF-heavy vs IMF-light ──")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Panel A: Investment rates over time
ax = axes[0]
for group_name, group_dict, color, ls in [
    ("IMF-heavy", IMF_HEAVY, "#d32f2f", "-"),
    ("IMF-light", IMF_LIGHT, "#1976d2", "--"),
]:
    ts = get_group_timeseries("NE.GDI.TOTL.ZS", group_dict, 1980, 2023)
    if not ts.empty:
        ax.plot(ts.index, ts.values, lw=2.5, label=group_name, color=color, ls=ls)

ax.set_xlabel("Year")
ax.set_ylabel("Gross capital formation (% GDP)")
ax.set_title("A. Investment rates")
ax.legend(fontsize=9)
ax.axhline(25, color="green", ls=":", alpha=0.4)
ax.annotate("25% threshold\n(development minimum)", xy=(1982, 25.5),
           fontsize=7, color="green", alpha=0.7)

# Panel B: Current account balance
ax = axes[1]
for group_name, group_dict, color, ls in [
    ("IMF-heavy", IMF_HEAVY, "#d32f2f", "-"),
    ("IMF-light", IMF_LIGHT, "#1976d2", "--"),
]:
    ts = get_group_timeseries("BN.CAB.XOKA.GD.ZS", group_dict, 1980, 2023)
    if not ts.empty:
        ax.plot(ts.index, ts.values, lw=2.5, label=group_name, color=color, ls=ls)

ax.set_xlabel("Year")
ax.set_ylabel("Current account balance (% GDP)")
ax.set_title("B. External balance")
ax.legend(fontsize=9)
ax.axhline(0, color="black", lw=0.5)

fig.suptitle("Investment & External Balance: IMF-Heavy vs IMF-Light Countries",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "77_investment_imf_groups.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("  Saved chart 77")


# ═══════════════════════════════════════════════════════════════════════════
# Summary statistics table
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY: IMF-Heavy vs IMF-Light Countries")
print("=" * 70)

for period_name, ys, ye in [("1980–1999", 1980, 1999), ("2000–2023", 2000, 2023), ("1990–2023", 1990, 2023)]:
    print(f"\n  {period_name}:")
    for group_name, group_dict in [("IMF-heavy", IMF_HEAVY), ("IMF-light", IMF_LIGHT)]:
        g = get_group_avg("NY.GDP.PCAP.KD.ZG", group_dict, ys, ye)
        inv = get_group_avg("NE.GDI.TOTL.ZS", group_dict, ys, ye)
        print(f"    {group_name:15s}: growth={g:+.1f}%/yr  investment={inv:.0f}% GDP")

# Asian crisis comparison
print("\n" + "=" * 70)
print("1997 ASIAN CRISIS: Recovery comparison")
print("=" * 70)
for cc, name in {**ASIAN_IMF, **ASIAN_NO_IMF}.items():
    # GDP per capita growth, 1998
    g98 = get_country_series("NY.GDP.PCAP.KD.ZG", cc, [1998])
    # Average growth 1999-2005 (recovery)
    recovery = get_country_series("NY.GDP.PCAP.KD.ZG", cc, list(range(1999, 2006)))
    trough = g98.iloc[0] if not g98.empty else np.nan
    rec_avg = recovery.mean() if not recovery.empty else np.nan
    print(f"  {name:25s}: 1998 trough={trough:+.1f}%  recovery 1999-2005={rec_avg:+.1f}%/yr")

# SSA era comparison
print("\n" + "=" * 70)
print("SSA GROWTH BY ERA")
print("=" * 70)
for label, ys, ye in eras:
    avg = get_group_avg("NY.GDP.PCAP.KD.ZG", SSA_COUNTRIES, ys, ye)
    inv = get_group_avg("NE.GDI.TOTL.ZS", SSA_COUNTRIES, ys, ye)
    label_clean = label.replace("\n", " ")
    print(f"  {label_clean:20s}: growth={avg:+.1f}%/yr  investment={inv:.0f}% GDP")

print("\nDone! Charts 72-77 saved.")
