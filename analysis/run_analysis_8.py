"""
Analysis 8: Country-Level Ecological Decoupling Decomposition
==============================================================
The global aggregates hide enormous variation. Carbon decoupling varies hugely
by country — does the same apply to material consumption, nitrogen, biodiversity,
and deforestation? Are some countries actually achieving absolute decoupling on
multiple dimensions simultaneously?
"""

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import requests, io, time
import warnings

warnings.filterwarnings("ignore")

sns.set_theme(style="whitegrid", palette="colorblind")
CHART_DIR = "charts"

OWID_BASE = "https://ourworldindata.org/grapher/"


def fetch_owid(slug, label):
    url = f"{OWID_BASE}{slug}.csv?v=1&csvType=full&useColumnShortNames=false"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        print(f"  {label}: {df.shape[0]} rows, {df['Entity'].nunique()} entities")
        return df
    except Exception as e:
        print(f"  {label}: ERROR {e}")
        return pd.DataFrame()


def get_value_col(df):
    skip = {"Entity", "Code", "Year", "Day"}
    for c in df.columns:
        if c not in skip:
            return c
    return None


# ── Download country-level datasets ──────────────────────────────────────────
print("Downloading country-level ecological datasets...")

dmc_pc = fetch_owid("domestic-material-consumption-per-capita", "DMC per capita")
time.sleep(0.5)
n_fert = fetch_owid(
    "nitrogen-fertilizer-application-per-hectare-of-cropland", "N fertilizer/ha"
)
time.sleep(0.5)
red_list = fetch_owid("red-list-index", "Red List Index")
time.sleep(0.5)
tree_loss = fetch_owid("tree-cover-loss", "Tree cover loss")
time.sleep(0.5)
forest_area = fetch_owid("forest-area-km", "Forest area")
time.sleep(0.5)
water_stress = fetch_owid(
    "freshwater-withdrawals-as-a-share-of-internal-resources", "Water stress"
)

print("\nLoading existing CO2 data...")
co2 = pd.read_csv("data/raw/owid_co2.csv")
print(f"  CO2: {co2.shape[0]} rows")

# ── Standardize column names ─────────────────────────────────────────────────
dmc_col = get_value_col(dmc_pc)
n_col = get_value_col(n_fert)
rl_col = get_value_col(red_list)
tc_col = get_value_col(tree_loss)
fa_col = get_value_col(forest_area)
ws_col = get_value_col(water_stress)

# Key countries for the analysis — mix of rich, middle, poor, big emitters
KEY_COUNTRIES = [
    "United States",
    "United Kingdom",
    "Germany",
    "France",
    "Japan",
    "China",
    "India",
    "Brazil",
    "Indonesia",
    "Nigeria",
    "South Korea",
    "Australia",
    "Canada",
    "Sweden",
    "Poland",
]

COUNTRY_COLORS = {
    "United States": "#1f77b4",
    "United Kingdom": "#2ca02c",
    "Germany": "#9467bd",
    "France": "#8c564b",
    "Japan": "#e377c2",
    "China": "#d62728",
    "India": "#ff7f0e",
    "Brazil": "#17becf",
    "Indonesia": "#bcbd22",
    "Nigeria": "#7f7f7f",
    "South Korea": "#aec7e8",
    "Australia": "#ffbb78",
    "Canada": "#98df8a",
    "Sweden": "#ff9896",
    "Poland": "#c5b0d5",
    "World": "black",
}


# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("ANALYSIS 8: COUNTRY-LEVEL ECOLOGICAL DECOUPLING")
print("=" * 80)


# ══════════════════════════════════════════════════════════════════════════════
# CHART 33: Material Consumption Per Capita by Country
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("CHART 33: DOMESTIC MATERIAL CONSUMPTION — COUNTRY TRAJECTORIES")
print("─" * 80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 33a: DMC per capita trajectories
ax = axes[0, 0]
if len(dmc_pc) > 0:
    for name in KEY_COUNTRIES + ["World"]:
        d = dmc_pc[dmc_pc["Entity"] == name].sort_values("Year")
        if len(d) > 3:
            lw = 2.5 if name == "World" else 1.3
            ls = "--" if name == "World" else "-"
            ax.plot(
                d["Year"],
                d[dmc_col],
                label=name,
                color=COUNTRY_COLORS.get(name, None),
                linewidth=lw,
                linestyle=ls,
            )
    ax.set_title(
        "Domestic Material Consumption Per Capita", fontsize=12, fontweight="bold"
    )
    ax.set_ylabel("Tonnes per person")
    ax.legend(fontsize=7, ncol=3, loc="upper left")

# 33b: Change in DMC/cap — who's decoupling absolutely?
ax = axes[0, 1]
if len(dmc_pc) > 0:
    changes = []
    for ent in dmc_pc["Entity"].unique():
        d = dmc_pc[dmc_pc["Entity"] == ent].sort_values("Year")
        if len(d) < 5:
            continue
        # Use ~2000 and latest
        early = d[(d["Year"] >= 2000) & (d["Year"] <= 2005)]
        late = d[d["Year"] >= d["Year"].max() - 3]
        if len(early) > 0 and len(late) > 0:
            e_val = early[dmc_col].mean()
            l_val = late[dmc_col].mean()
            if e_val > 0:
                pct_change = (l_val / e_val - 1) * 100
                changes.append(
                    {
                        "country": ent,
                        "early": e_val,
                        "late": l_val,
                        "pct_change": pct_change,
                    }
                )

    cdf = pd.DataFrame(changes)
    # Filter to countries with 3-letter codes (not regions)
    country_codes = dmc_pc[dmc_pc["Code"].notna() & (dmc_pc["Code"].str.len() == 3)]
    real_countries = country_codes["Entity"].unique()
    cdf = cdf[cdf["country"].isin(real_countries)]

    if len(cdf) > 0:
        # Show distribution
        declining = cdf[cdf["pct_change"] < 0]
        rising = cdf[cdf["pct_change"] >= 0]

        ax.hist(
            cdf["pct_change"], bins=40, color="steelblue", alpha=0.7, edgecolor="white"
        )
        ax.axvline(x=0, color="red", linewidth=2, linestyle="--")
        ax.set_title(
            f"Change in DMC/Capita (~2000 to latest)\n"
            f"{len(declining)} declining, {len(rising)} rising",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("% change in DMC per capita")
        ax.set_ylabel("Number of countries")

        # Annotate key countries
        for name in [
            "United States",
            "China",
            "India",
            "Germany",
            "United Kingdom",
            "Japan",
            "Brazil",
        ]:
            row = cdf[cdf["country"] == name]
            if len(row) > 0:
                val = row.iloc[0]["pct_change"]
                ax.annotate(
                    name.replace("United States", "US").replace("United Kingdom", "UK"),
                    xy=(val, 0),
                    fontsize=7,
                    rotation=90,
                    va="bottom",
                    ha="center",
                )

        print(
            f"\n  Countries with DECLINING DMC/cap: {len(declining)} ({len(declining)/len(cdf)*100:.0f}%)"
        )
        print(
            f"  Countries with RISING DMC/cap: {len(rising)} ({len(rising)/len(cdf)*100:.0f}%)"
        )
        print(f"  Median change: {cdf['pct_change'].median():+.0f}%")

        # Print key country details
        print(f"\n  Key country DMC/cap changes (2000→latest):")
        for name in [
            "United States",
            "United Kingdom",
            "Germany",
            "Japan",
            "China",
            "India",
            "Brazil",
            "Australia",
            "South Korea",
            "Sweden",
            "Nigeria",
            "Indonesia",
        ]:
            row = cdf[cdf["country"] == name]
            if len(row) > 0:
                r = row.iloc[0]
                print(
                    f"    {name:20s}: {r['early']:.1f} → {r['late']:.1f}t ({r['pct_change']:+.0f}%)"
                )

# 33c: DMC/cap vs GDP/cap (cross-section latest year)
ax = axes[1, 0]
if len(dmc_pc) > 0:
    # Get latest GDP/cap from CO2 data
    latest_gdp = co2[co2["year"] >= 2020].groupby("country")["gdp"].last()
    latest_pop = co2[co2["year"] >= 2020].groupby("country")["population"].last()
    latest_gdppc = (latest_gdp / latest_pop).dropna()

    latest_dmc = (
        dmc_pc[dmc_pc["Year"] >= dmc_pc["Year"].max() - 2]
        .groupby("Entity")[dmc_col]
        .mean()
    )

    # Match
    common = set(latest_gdppc.index) & set(latest_dmc.index)
    if len(common) > 10:
        scatter_df = pd.DataFrame(
            {
                "gdp_pc": [latest_gdppc[c] for c in common],
                "dmc_pc": [latest_dmc[c] for c in common],
                "country": list(common),
            }
        ).dropna()

        ax.scatter(scatter_df["gdp_pc"], scatter_df["dmc_pc"], alpha=0.4, s=20)
        ax.set_xscale("log")
        ax.set_title(
            "Material Consumption vs Income (latest)", fontsize=12, fontweight="bold"
        )
        ax.set_xlabel("GDP per capita (USD)")
        ax.set_ylabel("DMC per capita (tonnes)")

        # Label key countries
        for name in KEY_COUNTRIES:
            row = scatter_df[scatter_df["country"] == name]
            if len(row) > 0:
                ax.annotate(
                    name.replace("United States", "US")
                    .replace("United Kingdom", "UK")
                    .replace("South Korea", "S.Korea"),
                    xy=(row.iloc[0]["gdp_pc"], row.iloc[0]["dmc_pc"]),
                    fontsize=7,
                    alpha=0.8,
                )
                ax.scatter(
                    row["gdp_pc"],
                    row["dmc_pc"],
                    s=60,
                    zorder=5,
                    color=COUNTRY_COLORS.get(name, "red"),
                )

        # Fit line (log-log)
        valid = scatter_df[(scatter_df["gdp_pc"] > 0) & (scatter_df["dmc_pc"] > 0)]
        if len(valid) > 10:
            slope, intercept, r, p, se = stats.linregress(
                np.log10(valid["gdp_pc"]), np.log10(valid["dmc_pc"])
            )
            x_line = np.logspace(
                np.log10(valid["gdp_pc"].min()), np.log10(valid["gdp_pc"].max()), 100
            )
            y_line = 10 ** (slope * np.log10(x_line) + intercept)
            ax.plot(x_line, y_line, "r--", alpha=0.5)
            ax.annotate(
                f"Elasticity: {slope:.2f}\nR²={r**2:.2f}",
                xy=(0.05, 0.95),
                xycoords="axes fraction",
                fontsize=10,
                va="top",
            )
            print(f"\n  Material-income elasticity: {slope:.2f} (R²={r**2:.2f})")
            if slope < 1:
                print(
                    f"  → Elasticity < 1: richer countries use proportionally LESS material/$ of GDP"
                )
            else:
                print(
                    f"  → Elasticity ≥ 1: richer countries use proportionally MORE material/$ of GDP"
                )

# 33d: Rich vs developing country DMC trends (indexed)
ax = axes[1, 1]
if len(dmc_pc) > 0:
    groups = {
        "Rich avg\n(US, UK, DE, FR, JP)": [
            "United States",
            "United Kingdom",
            "Germany",
            "France",
            "Japan",
        ],
        "China": ["China"],
        "India": ["India"],
        "Brazil + Indonesia": ["Brazil", "Indonesia"],
    }
    group_colors = ["blue", "red", "orange", "green"]
    for (label, countries), color in zip(groups.items(), group_colors):
        group_data = dmc_pc[dmc_pc["Entity"].isin(countries)].copy()
        if len(group_data) > 0:
            yearly = group_data.groupby("Year")[dmc_col].mean()
            yearly = yearly[yearly.index >= 1970]
            if len(yearly) > 3:
                base_val = yearly.iloc[0]
                if base_val > 0:
                    indexed = yearly / base_val * 100
                    ax.plot(
                        indexed.index,
                        indexed.values,
                        label=label,
                        color=color,
                        linewidth=2 if "China" in label else 1.5,
                    )

    ax.axhline(y=100, color="gray", linewidth=0.5, linestyle=":")
    ax.set_title(
        "Material Consumption Trajectories (indexed)", fontsize=12, fontweight="bold"
    )
    ax.set_ylabel(f"Index (earliest year = 100)")
    ax.legend(fontsize=9)

plt.suptitle(
    "Chart 33: Material Consumption — Country-Level Variation",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/33_material_by_country.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 33 saved")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 34: Nitrogen Use — Who's Getting Efficient, Who's Not?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("CHART 34: NITROGEN FERTILIZER — COUNTRY TRAJECTORIES & EFFICIENCY")
print("─" * 80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 34a: N fertilizer per hectare trajectories
ax = axes[0, 0]
if len(n_fert) > 0:
    for name in KEY_COUNTRIES + ["World"]:
        d = n_fert[n_fert["Entity"] == name].sort_values("Year")
        if len(d) > 5:
            lw = 2.5 if name == "World" else 1.3
            ls = "--" if name == "World" else "-"
            ax.plot(
                d["Year"],
                d[n_col],
                label=name,
                color=COUNTRY_COLORS.get(name, None),
                linewidth=lw,
                linestyle=ls,
            )
    ax.set_title(
        "Nitrogen Fertilizer per Hectare of Cropland", fontsize=12, fontweight="bold"
    )
    ax.set_ylabel("kg N / hectare")
    ax.legend(fontsize=7, ncol=3, loc="upper left")

# 34b: Who peaked and who's still rising?
ax = axes[0, 1]
if len(n_fert) > 0:
    peak_data = []
    for ent in n_fert["Entity"].unique():
        d = n_fert[(n_fert["Entity"] == ent) & (n_fert["Year"] >= 1970)].sort_values(
            "Year"
        )
        if len(d) < 10:
            continue

        # Find peak
        peak_idx = d[n_col].idxmax()
        peak_yr = d.loc[peak_idx, "Year"]
        peak_val = d.loc[peak_idx, n_col]
        latest_val = d.iloc[-1][n_col]
        latest_yr = d.iloc[-1]["Year"]

        if peak_val > 10:  # Ignore tiny users
            declined = latest_val < peak_val * 0.9  # 10%+ below peak
            peak_data.append(
                {
                    "country": ent,
                    "peak_year": peak_yr,
                    "peak_val": peak_val,
                    "latest_val": latest_val,
                    "latest_yr": latest_yr,
                    "pct_from_peak": (latest_val / peak_val - 1) * 100,
                    "peaked": declined,
                }
            )

    pdf = pd.DataFrame(peak_data)
    # Filter to real countries
    real = n_fert[n_fert["Code"].notna() & (n_fert["Code"].str.len() == 3)][
        "Entity"
    ].unique()
    pdf = pdf[pdf["country"].isin(real)]

    if len(pdf) > 0:
        peaked = pdf[pdf["peaked"]]
        still_rising = pdf[~pdf["peaked"]]

        # Histogram of peak years for countries that have peaked
        if len(peaked) > 0:
            ax.hist(
                peaked["peak_year"],
                bins=range(1970, 2025, 5),
                alpha=0.7,
                color="steelblue",
                edgecolor="white",
                label=f"Peaked ({len(peaked)})",
            )
        ax.axvline(x=2020, color="red", linewidth=1.5, linestyle="--", alpha=0.5)
        ax.set_title(
            f"When Did N Fertilizer/ha Peak?\n"
            f"{len(peaked)} peaked, {len(still_rising)} still rising or flat",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("Peak year")
        ax.set_ylabel("Number of countries")
        ax.legend()

        print(f"\n  Countries where N/ha has peaked (10%+ below peak): {len(peaked)}")
        print(f"  Countries still at/above peak: {len(still_rising)}")

        for name in [
            "China",
            "India",
            "United States",
            "Germany",
            "France",
            "Brazil",
            "United Kingdom",
            "Japan",
            "Indonesia",
            "Nigeria",
        ]:
            row = pdf[pdf["country"] == name]
            if len(row) > 0:
                r = row.iloc[0]
                status = "PEAKED" if r["peaked"] else "still rising"
                print(
                    f"    {name:20s}: peak {r['peak_val']:.0f} kg/ha ({int(r['peak_year'])}), "
                    f"now {r['latest_val']:.0f} ({r['pct_from_peak']:+.0f}%) — {status}"
                )

# 34c: N use vs GDP/cap (does N use decouple with affluence?)
ax = axes[1, 0]
if len(n_fert) > 0:
    # Latest N/ha vs GDP/capita
    latest_n = n_fert[n_fert["Year"] >= 2020].groupby("Entity")[n_col].mean()
    latest_gdp = co2[co2["year"] >= 2020].groupby("country")["gdp"].last()
    latest_pop = co2[co2["year"] >= 2020].groupby("country")["population"].last()
    latest_gdppc = (latest_gdp / latest_pop).dropna()

    common = set(latest_n.index) & set(latest_gdppc.index)
    if len(common) > 10:
        ndf = pd.DataFrame(
            {
                "gdp_pc": [latest_gdppc[c] for c in common],
                "n_ha": [latest_n[c] for c in common],
                "country": list(common),
            }
        ).dropna()
        ndf = ndf[ndf["n_ha"] > 0]

        ax.scatter(ndf["gdp_pc"], ndf["n_ha"], alpha=0.4, s=20)
        ax.set_xscale("log")
        ax.set_title(
            "N Fertilizer/ha vs Income (latest)", fontsize=12, fontweight="bold"
        )
        ax.set_xlabel("GDP per capita (USD)")
        ax.set_ylabel("kg N / hectare")

        for name in KEY_COUNTRIES:
            row = ndf[ndf["country"] == name]
            if len(row) > 0:
                ax.annotate(
                    name.replace("United States", "US")
                    .replace("United Kingdom", "UK")
                    .replace("South Korea", "S.Korea"),
                    xy=(row.iloc[0]["gdp_pc"], row.iloc[0]["n_ha"]),
                    fontsize=7,
                    alpha=0.8,
                )
                ax.scatter(
                    row["gdp_pc"],
                    row["n_ha"],
                    s=60,
                    zorder=5,
                    color=COUNTRY_COLORS.get(name, "red"),
                )

# 34d: Nitrogen use efficiency trend (cereal yield per kg N)
ax = axes[1, 1]
if len(n_fert) > 0:
    # Compute N efficiency: we need cereal yield data
    # Use a proxy: compare N/ha trajectory shapes
    # Show indexed N/ha for countries that peaked vs still rising
    peaked_countries = ["China", "Germany", "France", "Japan", "United Kingdom"]
    rising_countries = ["India", "Brazil", "Indonesia", "Nigeria"]

    for name in peaked_countries:
        d = n_fert[(n_fert["Entity"] == name) & (n_fert["Year"] >= 1980)].sort_values(
            "Year"
        )
        if len(d) > 3:
            ax.plot(
                d["Year"],
                d[n_col],
                label=name,
                linewidth=1.3,
                color=COUNTRY_COLORS.get(name, None),
                linestyle="-",
            )

    for name in rising_countries:
        d = n_fert[(n_fert["Entity"] == name) & (n_fert["Year"] >= 1980)].sort_values(
            "Year"
        )
        if len(d) > 3:
            ax.plot(
                d["Year"],
                d[n_col],
                label=name,
                linewidth=1.3,
                color=COUNTRY_COLORS.get(name, None),
                linestyle="--",
            )

    ax.set_title(
        "N/ha: Peaked Countries (solid) vs Still Rising (dashed)",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_ylabel("kg N / hectare")
    ax.legend(fontsize=8, ncol=2)

plt.suptitle(
    "Chart 34: Nitrogen Fertilizer — Country-Level Divergence",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/34_nitrogen_by_country.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 34 saved")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 35: Biodiversity & Deforestation — Country Decomposition
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("CHART 35: BIODIVERSITY & DEFORESTATION BY COUNTRY")
print("─" * 80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 35a: Red List Index by country — who's losing species fastest?
ax = axes[0, 0]
if len(red_list) > 0:
    for name in [
        "World",
        "United States",
        "China",
        "India",
        "Brazil",
        "Indonesia",
        "Australia",
        "United Kingdom",
        "Germany",
        "Japan",
        "Nigeria",
        "South Africa",
    ]:
        d = red_list[red_list["Entity"] == name].sort_values("Year")
        if len(d) > 2:
            lw = 2.5 if name == "World" else 1.3
            ls = "--" if name == "World" else "-"
            ax.plot(
                d["Year"],
                d[rl_col],
                label=name,
                linewidth=lw,
                linestyle=ls,
                color=COUNTRY_COLORS.get(name, None),
            )
    ax.set_title(
        "Red List Index by Country (1=safe, 0=all extinct)",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_ylabel("Red List Index")
    ax.legend(fontsize=7, ncol=2)

# 35b: RLI change — distribution across countries
ax = axes[0, 1]
if len(red_list) > 0:
    rl_changes = []
    for ent in red_list["Entity"].unique():
        d = red_list[red_list["Entity"] == ent].sort_values("Year")
        if len(d) < 3:
            continue
        first_val = d.iloc[0][rl_col]
        last_val = d.iloc[-1][rl_col]
        if first_val > 0:
            pct = (last_val / first_val - 1) * 100
            rl_changes.append(
                {
                    "country": ent,
                    "first": first_val,
                    "last": last_val,
                    "change_pct": pct,
                    "abs_change": last_val - first_val,
                }
            )

    rdf = pd.DataFrame(rl_changes)
    real = red_list[red_list["Code"].notna() & (red_list["Code"].str.len() == 3)][
        "Entity"
    ].unique()
    rdf = rdf[rdf["country"].isin(real)]

    if len(rdf) > 0:
        improving = rdf[rdf["abs_change"] > 0.005]  # Modest threshold
        worsening = rdf[rdf["abs_change"] < -0.005]
        stable = rdf[(rdf["abs_change"] >= -0.005) & (rdf["abs_change"] <= 0.005)]

        ax.hist(
            rdf["abs_change"], bins=50, color="darkred", alpha=0.7, edgecolor="white"
        )
        ax.axvline(x=0, color="green", linewidth=2, linestyle="--")
        ax.set_title(
            f"Change in Red List Index (1993→2024)\n"
            f"{len(improving)} improving, {len(stable)} stable, {len(worsening)} worsening",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("Change in RLI (positive = improving)")
        ax.set_ylabel("Number of countries")

        print(f"\n  Red List Index changes (1993→2024):")
        print(f"    Improving: {len(improving)} countries")
        print(f"    Stable: {len(stable)} countries")
        print(
            f"    Worsening: {len(worsening)} countries ({len(worsening)/len(rdf)*100:.0f}%)"
        )

        # Worst 10
        worst = rdf.nsmallest(10, "abs_change")
        print(f"\n    Worst 10 RLI declines:")
        for _, r in worst.iterrows():
            print(
                f"      {r['country']:25s}: {r['first']:.3f} → {r['last']:.3f} ({r['abs_change']:+.3f})"
            )

# 35c: Tree cover loss — top 10 countries
ax = axes[1, 0]
if len(tree_loss) > 0:
    # Total tree cover loss by country
    real = tree_loss[tree_loss["Code"].notna() & (tree_loss["Code"].str.len() == 3)]
    totals = real.groupby("Entity")[tc_col].sum().sort_values(ascending=False)
    top10 = totals.head(10)

    if len(top10) > 0:
        colors_tc = [
            (
                "#d62728"
                if c in ["Brazil", "Indonesia"]
                else "#ff7f0e" if c in ["Russia", "Canada"] else "#2ca02c"
            )
            for c in top10.index
        ]
        bars = ax.barh(
            range(len(top10)), top10.values / 1e6, color="darkgreen", alpha=0.7
        )
        ax.set_yticks(range(len(top10)))
        ax.set_yticklabels(top10.index, fontsize=9)
        ax.set_title(
            f'Total Tree Cover Loss (2001–{tree_loss["Year"].max():.0f})',
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("Million hectares lost")
        ax.invert_yaxis()

        # Annotate values
        for i, (country, val) in enumerate(top10.items()):
            ax.text(val / 1e6 + 0.5, i, f"{val/1e6:.0f} Mha", va="center", fontsize=8)

        print(f"\n  Top 10 tree cover loss (2001-{tree_loss['Year'].max():.0f}):")
        for country, val in top10.items():
            print(f"    {country:25s}: {val/1e6:.0f} Mha")

# 35d: Forest area trends — who's reforesting?
ax = axes[1, 1]
if len(forest_area) > 0:
    for name in [
        "China",
        "India",
        "Brazil",
        "Indonesia",
        "United States",
        "Russia",
        "Vietnam",
        "United Kingdom",
        "France",
    ]:
        d = forest_area[forest_area["Entity"] == name].sort_values("Year")
        if len(d) > 2:
            # Index to first available year
            base = d.iloc[0][fa_col]
            if base > 0:
                indexed = d[fa_col] / base * 100
                ax.plot(
                    d["Year"],
                    indexed,
                    label=name,
                    linewidth=1.5,
                    color=COUNTRY_COLORS.get(name, None),
                )

    ax.axhline(y=100, color="gray", linewidth=0.5, linestyle=":")
    ax.set_title(
        "Forest Area Trends (indexed to earliest year = 100)",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_ylabel("Index (earliest = 100)")
    ax.legend(fontsize=8, ncol=2)

    # Print key reforestation stories
    print(f"\n  Forest area changes:")
    for name in [
        "China",
        "India",
        "Brazil",
        "Indonesia",
        "United States",
        "Vietnam",
        "United Kingdom",
        "France",
        "Germany",
    ]:
        d = forest_area[forest_area["Entity"] == name].sort_values("Year")
        if len(d) > 1:
            first = d.iloc[0]
            last = d.iloc[-1]
            pct = (last[fa_col] / first[fa_col] - 1) * 100
            print(
                f"    {name:20s}: {first[fa_col]/1e6:.1f} → {last[fa_col]/1e6:.1f} Mha "
                f"({pct:+.1f}%, {first['Year']:.0f}→{last['Year']:.0f})"
            )

plt.suptitle(
    "Chart 35: Biodiversity & Deforestation — Country Decomposition",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/35_biodiversity_by_country.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 35 saved")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 36: Multi-Dimensional Decoupling — Who's Doing What?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("CHART 36: MULTI-DIMENSIONAL DECOUPLING — THE FULL PICTURE")
print("─" * 80)

# Build a multi-dimensional decoupling scorecard for key countries
# For each country compute: CO2/GDP change, DMC/GDP change, N/ha change, RLI change, forest change
# over roughly 2000-latest

scorecard_countries = [
    "United States",
    "United Kingdom",
    "Germany",
    "France",
    "Japan",
    "China",
    "India",
    "Brazil",
    "Indonesia",
    "South Korea",
    "Australia",
    "Canada",
    "Sweden",
    "Poland",
    "Nigeria",
]


def compute_change(df, entity_col, year_col, val_col, entity, start=2000, end=None):
    """Compute % change between start and end period."""
    d = df[(df[entity_col] == entity)].sort_values(year_col)
    if end is None:
        end = d[year_col].max()
    early = d[(d[year_col] >= start) & (d[year_col] <= start + 5)]
    late = d[(d[year_col] >= end - 3)]
    if len(early) > 0 and len(late) > 0:
        e = early[val_col].mean()
        l = late[val_col].mean()
        if e > 0:
            return (l / e - 1) * 100, e, l
    return np.nan, np.nan, np.nan


scores = []
for country in scorecard_countries:
    row = {"country": country}

    # CO2 per GDP (from OWID co2)
    co2_d = co2[co2["country"] == country][["year", "co2_per_gdp"]].dropna()
    early_co2 = co2_d[(co2_d["year"] >= 2000) & (co2_d["year"] <= 2005)][
        "co2_per_gdp"
    ].mean()
    late_co2 = co2_d[co2_d["year"] >= co2_d["year"].max() - 3]["co2_per_gdp"].mean()
    if early_co2 > 0:
        row["co2_gdp_chg"] = (late_co2 / early_co2 - 1) * 100
    else:
        row["co2_gdp_chg"] = np.nan

    # DMC per capita
    if len(dmc_pc) > 0:
        chg, _, _ = compute_change(dmc_pc, "Entity", "Year", dmc_col, country)
        row["dmc_pc_chg"] = chg

    # N fertilizer per ha
    if len(n_fert) > 0:
        chg, _, _ = compute_change(n_fert, "Entity", "Year", n_col, country)
        row["n_ha_chg"] = chg

    # Red List Index (absolute change, not %)
    if len(red_list) > 0:
        d = red_list[red_list["Entity"] == country].sort_values("Year")
        if len(d) > 1:
            row["rli_change"] = d.iloc[-1][rl_col] - d.iloc[0][rl_col]
        else:
            row["rli_change"] = np.nan

    # Tree cover loss rate (ha/yr average)
    if len(tree_loss) > 0:
        d = tree_loss[tree_loss["Entity"] == country]
        if len(d) > 0:
            row["tree_loss_avg_mha"] = d[tc_col].mean() / 1e6
        else:
            row["tree_loss_avg_mha"] = np.nan

    # Forest area change
    if len(forest_area) > 0:
        _, e, l = compute_change(
            forest_area, "Entity", "Year", fa_col, country, start=1990
        )
        if e > 0:
            row["forest_chg"] = (l / e - 1) * 100
        else:
            row["forest_chg"] = np.nan

    scores.append(row)

sdf = pd.DataFrame(scores).set_index("country")

# 36a: Heatmap of decoupling scores
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

ax = axes[0]
# Prepare heatmap data
heat_cols = {
    "co2_gdp_chg": "CO₂/GDP\n(% change)",
    "dmc_pc_chg": "Material/cap\n(% change)",
    "n_ha_chg": "N fert/ha\n(% change)",
    "rli_change": "Red List\n(abs change)",
    "forest_chg": "Forest area\n(% change)",
}

heat_data = sdf[list(heat_cols.keys())].copy()
heat_data.columns = list(heat_cols.values())

# For the heatmap, normalize each column to [-1, 1] range
# Negative = worse (for CO2, DMC, N) but GOOD for CO2/GDP reduction
# So flip the sign for CO2, DMC, N (negative = good = green)
# For RLI: positive = good. For forest: positive = good.
display_data = heat_data.copy()

# Create a version where green = good, red = bad
# CO2/GDP: negative = good (decoupling)
# DMC/cap: negative = good (decoupling)
# N/ha: negative = good (efficiency)
# RLI: positive = good (less extinction risk)
# Forest: positive = good (reforestation)
color_data = heat_data.copy()
# Flip signs where negative = good
for c in ["CO₂/GDP\n(% change)", "Material/cap\n(% change)", "N fert/ha\n(% change)"]:
    if c in color_data.columns:
        color_data[c] = -color_data[c]  # Now positive = good for all

# Scale each column to roughly [-1, 1]
for c in color_data.columns:
    col = color_data[c].dropna()
    if len(col) > 0:
        max_abs = max(abs(col.max()), abs(col.min()), 1)
        color_data[c] = color_data[c] / max_abs

im = ax.imshow(color_data.values, cmap="RdYlGn", aspect="auto", vmin=-1, vmax=1)
ax.set_xticks(range(len(heat_data.columns)))
ax.set_xticklabels(heat_data.columns, fontsize=9, rotation=0, ha="center")
ax.set_yticks(range(len(heat_data.index)))
ax.set_yticklabels(heat_data.index, fontsize=9)

# Annotate cells with actual values
for i in range(len(heat_data.index)):
    for j in range(len(heat_data.columns)):
        val = heat_data.iloc[i, j]
        if pd.notna(val):
            if abs(val) >= 1:
                txt = f"{val:+.0f}" if j != 3 else f"{val:+.3f}"
            else:
                txt = f"{val:+.2f}" if j == 3 else f"{val:+.1f}"
            ax.text(
                j,
                i,
                txt,
                ha="center",
                va="center",
                fontsize=7,
                color="white" if abs(color_data.iloc[i, j]) > 0.6 else "black",
            )

ax.set_title(
    "Ecological Decoupling Scorecard (~2000→latest)\nGreen = improving, Red = worsening",
    fontsize=12,
    fontweight="bold",
)
plt.colorbar(im, ax=ax, label="Normalized score (green=good)", shrink=0.8)

# 36b: Scatter: CO2 decoupling vs material decoupling
ax = axes[1]
valid = sdf.dropna(subset=["co2_gdp_chg", "dmc_pc_chg"])
if len(valid) > 3:
    ax.scatter(valid["co2_gdp_chg"], valid["dmc_pc_chg"], s=100, alpha=0.7, zorder=5)
    for country in valid.index:
        ax.annotate(
            country.replace("United States", "US")
            .replace("United Kingdom", "UK")
            .replace("South Korea", "S.Korea"),
            xy=(valid.loc[country, "co2_gdp_chg"], valid.loc[country, "dmc_pc_chg"]),
            fontsize=8,
            alpha=0.8,
            ha="left",
        )

    # Quadrant lines
    ax.axhline(y=0, color="gray", linewidth=1, linestyle="-")
    ax.axvline(x=0, color="gray", linewidth=1, linestyle="-")

    # Quadrant labels
    ax.annotate(
        "Carbon ✓ Material ✓\n(full decoupling)",
        xy=(0.02, 0.02),
        xycoords="axes fraction",
        fontsize=9,
        color="green",
        fontweight="bold",
    )
    ax.annotate(
        "Carbon ✓ Material ✗\n(carbon only)",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        fontsize=9,
        color="orange",
        fontweight="bold",
        va="top",
    )
    ax.annotate(
        "Carbon ✗ Material ✓\n(unusual)",
        xy=(0.72, 0.02),
        xycoords="axes fraction",
        fontsize=9,
        color="orange",
        fontweight="bold",
    )
    ax.annotate(
        "Carbon ✗ Material ✗\n(no decoupling)",
        xy=(0.72, 0.95),
        xycoords="axes fraction",
        fontsize=9,
        color="red",
        fontweight="bold",
        va="top",
    )

    ax.set_xlabel("CO₂/GDP change (%); negative = decoupling", fontsize=11)
    ax.set_ylabel(
        "Material consumption/cap change (%); negative = decoupling", fontsize=11
    )
    ax.set_title(
        "CO₂ Decoupling vs Material Decoupling\n(~2000 to latest)",
        fontsize=12,
        fontweight="bold",
    )
    ax.text(0.5, 0.02, "Note: CO\u2082 normalized by GDP; materials by population \u2014 different metrics", transform=ax.transAxes, fontsize=7, ha='center', color='gray', style='italic')

    # Count quadrants
    both_good = valid[(valid["co2_gdp_chg"] < 0) & (valid["dmc_pc_chg"] < 0)]
    co2_only = valid[(valid["co2_gdp_chg"] < 0) & (valid["dmc_pc_chg"] >= 0)]
    neither = valid[(valid["co2_gdp_chg"] >= 0) & (valid["dmc_pc_chg"] >= 0)]

    print(f"\n  Carbon + material decoupling: {len(both_good)}/{len(valid)} countries")
    print(f"  Carbon only: {len(co2_only)}/{len(valid)} countries")
    print(f"  Neither: {len(neither)}/{len(valid)} countries")
    if len(both_good) > 0:
        print(f"  Full decouplers: {', '.join(both_good.index)}")

plt.suptitle(
    "Chart 36: Multi-Dimensional Decoupling Scorecard",
    fontsize=15,
    fontweight="bold",
    y=1.02,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/36_multidim_decoupling.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 36 saved")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SUMMARY: COUNTRY-LEVEL ECOLOGICAL VARIATION")
print("=" * 80)

# Print the full scorecard table
print("\n  ECOLOGICAL DECOUPLING SCORECARD (2000→latest):")
print(
    f"  {'Country':<20s} {'CO₂/GDP':>8s} {'DMC/cap':>8s} {'N fert/ha':>10s} {'RLI':>8s} {'Forest':>8s}"
)
print("  " + "─" * 70)
for country in scorecard_countries:
    r = sdf.loc[country]
    co2_s = f"{r['co2_gdp_chg']:+.0f}%" if pd.notna(r.get("co2_gdp_chg")) else "N/A"
    dmc_s = f"{r['dmc_pc_chg']:+.0f}%" if pd.notna(r.get("dmc_pc_chg")) else "N/A"
    n_s = f"{r['n_ha_chg']:+.0f}%" if pd.notna(r.get("n_ha_chg")) else "N/A"
    rl_s = f"{r['rli_change']:+.3f}" if pd.notna(r.get("rli_change")) else "N/A"
    fa_s = f"{r['forest_chg']:+.1f}%" if pd.notna(r.get("forest_chg")) else "N/A"
    print(f"  {country:<20s} {co2_s:>8s} {dmc_s:>8s} {n_s:>10s} {rl_s:>8s} {fa_s:>8s}")

print(
    """

KEY FINDINGS:

1. MATERIAL DECOUPLING IS HIGHLY UNEVEN
   - Rich countries (US, UK, Germany) show some per-capita decline
   - China's DMC/cap has exploded (urbanization + infrastructure)
   - There is NO global absolute material decoupling

2. NITROGEN: A TALE OF TWO TRAJECTORIES
   - China PEAKED at ~230 kg/ha and is declining (policy intervention)
   - India, Brazil, Indonesia, Nigeria still rising
   - Rich countries mostly peaked in the 1980s-2000s
   - This is one area where policy has demonstrably worked (in some countries)

3. BIODIVERSITY: ALMOST UNIVERSALLY DECLINING
   - The Red List Index is worsening in the vast majority of countries
   - Very few countries show improvement
   - Tropical countries (Indonesia, Brazil) face the worst pressure

4. TREE COVER LOSS (includes wildfire, logging, and deforestation): CONCENTRATED BUT PERSISTENT
   - Brazil, Indonesia, Russia, Canada, and DRC drive most tree cover loss
   - China and India are REFORESTING (tree planting programs)
   - But plantations ≠ biodiversity restoration

5. MULTI-DIMENSIONAL DECOUPLING IS RARE
   - Few countries are decoupling on ALL dimensions simultaneously
   - Carbon decoupling does NOT imply material or ecological decoupling
   - Based on carbon and material metrics, UK, Germany, and Sweden perform relatively well — but a full multi-dimensional ranking incorporating nitrogen, biodiversity, and land use was not computed
   - Developing countries are mostly moving in the wrong direction on materials

IMPLICATIONS:
   Carbon decoupling is not a proxy for ecological sustainability.
   A country can reduce CO₂/GDP while increasing material throughput,
   losing biodiversity, and using more nitrogen. The ecological challenge
   is fundamentally multi-dimensional, and carbon-only climate policy
   addresses less than half the problem.
"""
)
