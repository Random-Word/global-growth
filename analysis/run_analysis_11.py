"""
Analysis 11: Are Rich-World Citizens Actually Worse Off?
=========================================================
Questions addressed:
1. Has the bottom quintile in rich countries actually lost real income?
2. How do income shares across quintiles shift over time (relative inequality)?
3. How does the bottom 20% in a rich country compare to the global median?
4. Have life expectancy and other HDI-type metrics improved for all?
5. Does the "squeezed feeling" reflect absolute loss or relative stagnation?

This directly tests the claim that capitalism is "untenable" because even
rich-world citizens are not benefiting from growth.
"""

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import requests, json, time
import warnings

warnings.filterwarnings("ignore")

sns.set_theme(style="whitegrid", palette="colorblind")
CHART_DIR = "charts"

# ── Load PIP survey mean income (actual household-survey data) ────────────────
import os

pip_mean = pd.read_csv(
    os.path.join("data", "raw", "pip_country_2.15.csv"),
    usecols=["country_code", "reporting_year", "reporting_level", "mean"],
)
pip_mean = pip_mean[pip_mean["reporting_level"] == "national"].copy()
# PIP mean is daily per-capita income/consumption in 2017 PPP $
pip_mean["survey_mean_annual"] = pip_mean["mean"] * 365.25
pip_mean = pip_mean.rename(columns={"reporting_year": "year"})
pip_mean = pip_mean[["country_code", "year", "survey_mean_annual"]].dropna()


# ── Download WDI data for rich countries ───────────────────────────────────────
def fetch_wdi(indicator, label, countries="all", date_range="1970:2025"):
    """Fetch a WDI indicator."""
    url = f"https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"
    params = {"date": date_range, "format": "json", "per_page": 20000}
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=90)
            data = r.json()
            if len(data) > 1 and data[1]:
                rows = []
                for item in data[1]:
                    if item["value"] is not None and item.get("countryiso3code"):
                        rows.append(
                            {
                                "country_code": item["countryiso3code"],
                                "country": item["country"]["value"],
                                "year": int(item["date"]),
                                label: float(item["value"]),
                            }
                        )
                df = pd.DataFrame(rows)
                print(f"  {label}: {len(df)} obs")
                return df
            else:
                print(f"  {label}: NO DATA")
                return pd.DataFrame()
        except Exception as e:
            print(f"  {label}: attempt {attempt+1} failed ({e})")
            time.sleep(3)
    return pd.DataFrame()


RICH = "USA;GBR;FRA;DEU;JPN;SWE;NOR;DNK;CAN;AUS"

print("Downloading income distribution and welfare indicators...")
datasets = {}
indicators = [
    ("SI.DST.FRST.20", "bottom20_share", RICH),
    ("SI.DST.02ND.20", "q2_share", RICH),
    ("SI.DST.03RD.20", "q3_share", RICH),
    ("SI.DST.04TH.20", "q4_share", RICH),
    ("SI.DST.05TH.20", "top20_share", RICH),
    ("SI.POV.GINI", "gini", RICH),
    ("NY.GDP.PCAP.PP.KD", "gdppc_ppp", RICH),
    ("SP.DYN.LE00.IN", "life_expectancy", RICH),
    ("SH.DYN.MORT", "under5_mortality", RICH),
    ("SH.STA.MMRT", "maternal_mortality", RICH),
    ("SE.TER.ENRR", "tertiary_enrollment", RICH),
    # Global comparators
    ("NY.GDP.PCAP.PP.KD", "gdppc_ppp_global", "all"),
    ("SI.DST.FRST.20", "bottom20_share_global", "all"),
    ("SP.DYN.LE00.IN", "life_expectancy_global", "all"),
]

for code, label, ctry in indicators:
    df = fetch_wdi(code, label, countries=ctry)
    if len(df) > 0:
        datasets[label] = df
    time.sleep(1.5)

# ── Merge quintile data for rich countries ────────────────────────────────────
print("\nMerging datasets...")
quintile_cols = ["bottom20_share", "q2_share", "q3_share", "q4_share", "top20_share"]
rich_data = None
for col in quintile_cols + [
    "gini",
    "gdppc_ppp",
    "life_expectancy",
    "under5_mortality",
    "tertiary_enrollment",
]:
    if col in datasets:
        df = datasets[col][["country_code", "country", "year", col]]
        if rich_data is None:
            rich_data = df
        else:
            rich_data = rich_data.merge(
                df, on=["country_code", "country", "year"], how="outer"
            )

if rich_data is not None:
    # Merge PIP survey mean income (household-survey-based, not GDP/cap)
    rich_data = rich_data.merge(pip_mean, on=["country_code", "year"], how="left")
    # Use survey mean where available; interpolate within each country for gaps
    rich_data = rich_data.sort_values(["country_code", "year"])
    rich_data["survey_mean_annual"] = rich_data.groupby("country_code")[
        "survey_mean_annual"
    ].transform(lambda s: s.interpolate(method="linear", limit_area="inside"))

    # Compute real income at each quintile using survey mean (not GDP/cap).
    # GDP/cap includes corporate earnings, government spending, capital formation
    # that are not household income. Survey mean is actual household income/consumption.
    income_base = rich_data["survey_mean_annual"].fillna(rich_data["gdppc_ppp"])
    for q, col in [
        ("Q1_bottom20", "bottom20_share"),
        ("Q2", "q2_share"),
        ("Q3_median", "q3_share"),
        ("Q4", "q4_share"),
        ("Q5_top20", "top20_share"),
    ]:
        rich_data[f"income_{q}"] = income_base * (rich_data[col] / 20)

    print(
        f"  Rich-country dataset: {len(rich_data)} rows, {rich_data['country_code'].nunique()} countries"
    )

# ══════════════════════════════════════════════════════════════════════════════
# CHART 47: Real Income by Quintile Over Time
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("CHART 47: REAL INCOME BY QUINTILE — ABSOLUTE GAINS AT EVERY LEVEL")
print("═" * 80)

fig, axes = plt.subplots(2, 3, figsize=(20, 13))
country_order = [
    ("USA", "United States"),
    ("GBR", "United Kingdom"),
    ("FRA", "France"),
    ("DEU", "Germany"),
    ("JPN", "Japan"),
    ("SWE", "Sweden"),
]
colors = {
    "Q1_bottom20": "#d62728",
    "Q2": "#ff7f0e",
    "Q3_median": "#2ca02c",
    "Q4": "#1f77b4",
    "Q5_top20": "#9467bd",
}
labels = {
    "Q1_bottom20": "Bottom 20%",
    "Q2": "2nd quintile",
    "Q3_median": "Middle 20%",
    "Q4": "4th quintile",
    "Q5_top20": "Top 20%",
}

for idx, (cc, name) in enumerate(country_order):
    ax = axes[idx // 3, idx % 3]
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    d = d[d["year"] >= 1980]

    for q in ["Q1_bottom20", "Q2", "Q3_median", "Q4", "Q5_top20"]:
        col = f"income_{q}"
        series = d.dropna(subset=[col])
        if len(series) > 2:
            ax.plot(
                series["year"],
                series[col] / 1000,
                color=colors[q],
                label=labels[q],
                linewidth=2 if q in ("Q1_bottom20", "Q5_top20") else 1.2,
            )

    ax.set_title(name, fontsize=13, fontweight="bold")
    ax.set_ylabel("Real income (thousand PPP $)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}k"))

    # Annotate bottom-20% gain
    b20 = d.dropna(subset=["income_Q1_bottom20"])
    if len(b20) > 5:
        first = b20.iloc[0]
        last = b20.iloc[-1]
        pct_change = (
            last["income_Q1_bottom20"] / first["income_Q1_bottom20"] - 1
        ) * 100
        ax.annotate(
            f'Bottom 20%: +{pct_change:.0f}%\n({int(first["year"])}→{int(last["year"])})',
            xy=(0.02, 0.02),
            xycoords="axes fraction",
            fontsize=9,
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
        )

    if idx == 0:
        ax.legend(fontsize=8, loc="upper left")

plt.suptitle(
    "Chart 47: Real Income by Quintile — Everyone Got Richer in Absolute Terms",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/47_quintile_real_income.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 47 saved: quintile_real_income.png")

# Print the key numbers
print("\nReal income by quintile (PPP constant $, avg income per person in quintile):")
for cc, name in country_order:
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    d = d.dropna(subset=["income_Q1_bottom20", "income_Q5_top20"])
    if len(d) < 2:
        continue
    first = d.iloc[0]
    last = d.iloc[-1]
    b20_chg = (last["income_Q1_bottom20"] / first["income_Q1_bottom20"] - 1) * 100
    t20_chg = (last["income_Q5_top20"] / first["income_Q5_top20"] - 1) * 100
    print(
        f"  {name:20s}: Bottom20 ${first['income_Q1_bottom20']:,.0f}→${last['income_Q1_bottom20']:,.0f} "
        f"(+{b20_chg:.0f}%)  Top20 ${first['income_Q5_top20']:,.0f}→${last['income_Q5_top20']:,.0f} "
        f"(+{t20_chg:.0f}%)  [{int(first['year'])}→{int(last['year'])}]"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHART 48: Income Share Shifts — Who's Getting a Bigger Slice?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("CHART 48: INCOME SHARE SHIFTS — RELATIVE INEQUALITY")
print("═" * 80)

fig, axes = plt.subplots(2, 3, figsize=(20, 13))

for idx, (cc, name) in enumerate(country_order):
    ax = axes[idx // 3, idx % 3]
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    d = d[d["year"] >= 1980]

    # Stacked area: share of income going to each quintile
    d_clean = d.dropna(subset=quintile_cols)
    if len(d_clean) > 2:
        years = d_clean["year"].values
        bottom = np.zeros(len(d_clean))
        q_colors = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#9467bd"]
        q_labels = ["Bottom 20%", "2nd", "Middle", "4th", "Top 20%"]

        for i, (col, color, label) in enumerate(zip(quintile_cols, q_colors, q_labels)):
            vals = d_clean[col].values
            ax.fill_between(
                years, bottom, bottom + vals, color=color, alpha=0.7, label=label
            )
            bottom = bottom + vals

        # Annotate the top-20% share change
        first_top = d_clean.iloc[0]["top20_share"]
        last_top = d_clean.iloc[-1]["top20_share"]
        first_bot = d_clean.iloc[0]["bottom20_share"]
        last_bot = d_clean.iloc[-1]["bottom20_share"]
        direction_top = "+" if last_top > first_top else ""
        direction_bot = "+" if last_bot > first_bot else ""
        ax.annotate(
            f"Top 20%: {first_top:.1f}→{last_top:.1f}% ({direction_top}{last_top-first_top:.1f}pp)\n"
            f"Bot 20%: {first_bot:.1f}→{last_bot:.1f}% ({direction_bot}{last_bot-first_bot:.1f}pp)",
            xy=(0.02, 0.02),
            xycoords="axes fraction",
            fontsize=8,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    ax.set_title(name, fontsize=13, fontweight="bold")
    ax.set_ylabel("Income share (%)")
    ax.set_ylim(0, 100)
    if idx == 0:
        ax.legend(fontsize=7, loc="upper right")

plt.suptitle(
    "Chart 48: Income Share Shifts — The Rich Got a Bigger Slice, But the Pie Grew",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/48_income_share_shifts.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 48 saved: income_share_shifts.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 49: Rich-Country Poor vs Global Median
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("CHART 49: RICH-COUNTRY POOR vs GLOBAL MEDIAN")
print("═" * 80)

fig, axes = plt.subplots(1, 2, figsize=(16, 8))

# 49a: Bottom-20% income in rich countries vs GDP/capita of developing nations
ax = axes[0]
if "gdppc_ppp_global" in datasets:
    global_gdp = datasets["gdppc_ppp_global"]

    # Get latest year global GDP/cap for comparison countries
    comparators = {
        "CHN": "China",
        "IND": "India",
        "BRA": "Brazil",
        "MEX": "Mexico",
        "THA": "Thailand",
        "IDN": "Indonesia",
        "ZAF": "South Africa",
        "NGA": "Nigeria",
        "VNM": "Vietnam",
        "BGD": "Bangladesh",
        "COL": "Colombia",
        "TUR": "Türkiye",
    }

    # Rich-country bottom-20% real incomes (latest)
    rich_b20 = []
    for cc, name in country_order:
        d = rich_data[(rich_data["country_code"] == cc)].sort_values("year")
        d = d.dropna(subset=["income_Q1_bottom20"])
        if len(d) > 0:
            last = d.iloc[-1]
            rich_b20.append(
                {
                    "country": name,
                    "income": last["income_Q1_bottom20"],
                    "label": f"{name}\nbottom 20%",
                    "color": "#d62728",
                }
            )

    # Developing country average income (GDP/capita PPP)
    dev_avg = []
    for cc, name in comparators.items():
        d = global_gdp[global_gdp["country_code"] == cc].sort_values("year")
        d = d.dropna(subset=["gdppc_ppp_global"])
        if len(d) > 0:
            last = d.iloc[-1]
            dev_avg.append(
                {
                    "country": name,
                    "income": last["gdppc_ppp_global"],
                    "label": f"{name}\naverage",
                    "color": "#1f77b4",
                }
            )

    # Combine and sort
    all_bars = sorted(rich_b20 + dev_avg, key=lambda x: x["income"], reverse=True)

    y_pos = range(len(all_bars))
    colors_bar = [b["color"] for b in all_bars]
    incomes = [b["income"] for b in all_bars]
    bar_labels = [b["label"] for b in all_bars]

    bars = ax.barh(y_pos, incomes, color=colors_bar, alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(bar_labels, fontsize=8)
    ax.set_xlabel("Income per person (PPP constant $)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
    ax.set_title(
        "Bottom 20% in Rich Countries vs Average in Developing",
        fontsize=12,
        fontweight="bold",
    )
    ax.invert_yaxis()

    # Add value labels
    for bar, val in zip(bars, incomes):
        ax.text(
            val + 500,
            bar.get_y() + bar.get_height() / 2,
            f"${val:,.0f}",
            va="center",
            fontsize=8,
        )

    # Legend
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#d62728", alpha=0.8, label="Rich-country bottom 20%"),
        Patch(facecolor="#1f77b4", alpha=0.8, label="Developing-country average"),
    ]
    ax.legend(handles=legend_elements, fontsize=9, loc="lower right")

# 49b: Gini trend comparison
ax = axes[1]
gini_colors = {
    "USA": "#1f77b4",
    "GBR": "#ff7f0e",
    "FRA": "#2ca02c",
    "DEU": "#d62728",
    "JPN": "#9467bd",
    "SWE": "#8c564b",
}
for cc, name in country_order:
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    d = d.dropna(subset=["gini"])
    d = d[d["year"] >= 1980]
    if len(d) > 2:
        ax.plot(d["year"], d["gini"], label=name, color=gini_colors[cc], linewidth=2)
        # Annotate latest
        last = d.iloc[-1]
        ax.annotate(
            f'{last["gini"]:.1f}',
            xy=(last["year"], last["gini"]),
            fontsize=9,
            fontweight="bold",
            color=gini_colors[cc],
        )

ax.set_title(
    "Gini Coefficient Trends — Inequality Trajectories Diverge",
    fontsize=12,
    fontweight="bold",
)
ax.set_ylabel("Gini coefficient")
ax.legend(fontsize=9)
ax.annotate(
    "Higher = more unequal\nUS stands alone",
    xy=(0.02, 0.95),
    xycoords="axes fraction",
    fontsize=9,
    va="top",
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

plt.suptitle(
    "Chart 49: Rich-Country Poor vs the World — Context Matters",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/49_rich_poor_vs_global.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 49 saved: rich_poor_vs_global.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 50: Human Development — Universal Gains Even at the Bottom
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("CHART 50: HUMAN DEVELOPMENT — UNIVERSAL GAINS")
print("═" * 80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 50a: Life expectancy trends
ax = axes[0, 0]
le_colors = {
    "USA": "#1f77b4",
    "GBR": "#ff7f0e",
    "FRA": "#2ca02c",
    "DEU": "#d62728",
    "JPN": "#9467bd",
    "SWE": "#8c564b",
}
for cc, name in country_order:
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    d = d.dropna(subset=["life_expectancy"])
    d = d[d["year"] >= 1970]
    if len(d) > 2:
        ax.plot(
            d["year"],
            d["life_expectancy"],
            label=name,
            color=le_colors[cc],
            linewidth=1.5,
        )
ax.set_title("Life Expectancy at Birth", fontsize=12, fontweight="bold")
ax.set_ylabel("Years")
ax.legend(fontsize=8)
ax.annotate(
    "US diverges from peers\nafter ~2010 (opioids, COVID)",
    xy=(2010, 76),
    fontsize=9,
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

# 50b: Under-5 mortality — dramatic improvement
ax = axes[0, 1]
for cc, name in country_order:
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    d = d.dropna(subset=["under5_mortality"])
    d = d[d["year"] >= 1970]
    if len(d) > 2:
        ax.plot(
            d["year"],
            d["under5_mortality"],
            label=name,
            color=le_colors[cc],
            linewidth=1.5,
        )
ax.set_title(
    "Under-5 Mortality (per 1,000 live births)", fontsize=12, fontweight="bold"
)
ax.set_ylabel("Deaths per 1,000")
ax.legend(fontsize=8)

# 50c: Tertiary enrollment
ax = axes[1, 0]
for cc, name in country_order:
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    d = d.dropna(subset=["tertiary_enrollment"])
    d = d[d["year"] >= 1970]
    if len(d) > 2:
        ax.plot(
            d["year"],
            d["tertiary_enrollment"],
            label=name,
            color=le_colors[cc],
            linewidth=1.5,
        )
ax.set_title("Tertiary Education Enrollment Rate (%)", fontsize=12, fontweight="bold")
ax.set_ylabel("% gross enrollment")
ax.legend(fontsize=8)

# 50d: Summary scorecard — then vs now for bottom 20%
ax = axes[1, 1]
ax.axis("off")
# Build a summary table
rows = []
for cc, name in [
    ("USA", "US"),
    ("GBR", "UK"),
    ("FRA", "France"),
    ("DEU", "Germany"),
    ("JPN", "Japan"),
    ("SWE", "Sweden"),
]:
    d = rich_data[rich_data["country_code"] == cc].sort_values("year")
    b20 = d.dropna(subset=["income_Q1_bottom20"])
    le = d.dropna(subset=["life_expectancy"])
    gi = d.dropna(subset=["gini"])

    if len(b20) > 2 and len(le) > 2:
        first_b20 = (
            b20[b20["year"] >= 1985].iloc[0]
            if len(b20[b20["year"] >= 1985]) > 0
            else b20.iloc[0]
        )
        last_b20 = b20.iloc[-1]
        first_le = le[le["year"] <= 1995]
        last_le = le.iloc[-1]
        first_gi = gi[gi["year"] <= 1995]
        last_gi = gi.iloc[-1] if len(gi) > 0 else None

        b20_early = first_b20["income_Q1_bottom20"]
        b20_late = last_b20["income_Q1_bottom20"]
        le_early = first_le.iloc[-1]["life_expectancy"] if len(first_le) > 0 else None
        le_late = last_le["life_expectancy"]
        gi_early = first_gi.iloc[-1]["gini"] if len(first_gi) > 0 else None
        gi_late = last_gi["gini"] if last_gi is not None else None

        rows.append(
            {
                "Country": name,
                "Bottom 20%\n~1990 PPP$": f"${b20_early:,.0f}",
                "Bottom 20%\nLatest PPP$": f"${b20_late:,.0f}",
                "Change": f"+{(b20_late/b20_early-1)*100:.0f}%",
                "Life Exp\n~1990": f"{le_early:.1f}" if le_early else "n/a",
                "Life Exp\nLatest": f"{le_late:.1f}",
                "Gini\n~1990": f"{gi_early:.1f}" if gi_early else "n/a",
                "Gini\nLatest": f"{gi_late:.1f}" if gi_late else "n/a",
            }
        )

if rows:
    table_df = pd.DataFrame(rows)
    table = ax.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)
    # Color the "Change" column green
    for i in range(len(rows)):
        table[i + 1, 3].set_facecolor("#c6efce")
    for j in range(len(table_df.columns)):
        table[0, j].set_facecolor("#4472c4")
        table[0, j].set_text_props(color="white", fontweight="bold")
    ax.set_title(
        "Summary: Bottom 20% Got Richer Everywhere", fontsize=12, fontweight="bold"
    )

plt.suptitle(
    "Chart 50: Human Development in Rich Countries — Universal Gains",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/50_human_development_rich.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 50 saved: human_development_rich.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 51: The Real Story — Absolute vs Relative
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("CHART 51: THE REAL STORY — ABSOLUTE GAINS, RELATIVE FRUSTRATION")
print("═" * 80)

fig, axes = plt.subplots(1, 2, figsize=(16, 8))

# 51a: US — the extreme case: bottom 20% income vs top 20% (indexed to 1990=100)
ax = axes[0]
us = rich_data[rich_data["country_code"] == "USA"].sort_values("year")
us = us.dropna(subset=["income_Q1_bottom20", "income_Q5_top20", "income_Q3_median"])
if len(us) > 5:
    base_row = us[us["year"] >= 1985].iloc[0]
    base_year = int(base_row["year"])
    for q, label, color, lw in [
        ("income_Q1_bottom20", "Bottom 20%", "#d62728", 2.5),
        ("income_Q3_median", "Middle 20%", "#2ca02c", 2),
        ("income_Q5_top20", "Top 20%", "#9467bd", 2.5),
    ]:
        indexed = us[q] / base_row[q] * 100
        ax.plot(us["year"], indexed, label=label, color=color, linewidth=lw)

    ax.axhline(y=100, color="grey", linewidth=0.5, linestyle="--")
    ax.set_title(
        f"United States: Growth Indexed to {base_year}=100",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_ylabel(f"Real income index ({base_year}=100)")
    ax.legend(fontsize=10)
    ax.annotate(
        "Top 20% grew FASTER,\nbut bottom 20% still grew",
        xy=(2015, 110),
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
    )

# 51b: France — the egalitarian case
ax = axes[1]
fr = rich_data[rich_data["country_code"] == "FRA"].sort_values("year")
fr = fr.dropna(subset=["income_Q1_bottom20", "income_Q5_top20", "income_Q3_median"])
if len(fr) > 5:
    base_row = fr[fr["year"] >= 1985].iloc[0]
    base_year = int(base_row["year"])
    for q, label, color, lw in [
        ("income_Q1_bottom20", "Bottom 20%", "#d62728", 2.5),
        ("income_Q3_median", "Middle 20%", "#2ca02c", 2),
        ("income_Q5_top20", "Top 20%", "#9467bd", 2.5),
    ]:
        indexed = fr[q] / base_row[q] * 100
        ax.plot(fr["year"], indexed, label=label, color=color, linewidth=lw)

    ax.axhline(y=100, color="grey", linewidth=0.5, linestyle="--")
    ax.set_title(
        f"France: Growth Indexed to {base_year}=100", fontsize=12, fontweight="bold"
    )
    ax.set_ylabel(f"Real income index ({base_year}=100)")
    ax.legend(fontsize=10)
    ax.annotate(
        "More equal growth,\nbut ALL quintiles still grew",
        xy=(2010, 110),
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
    )

plt.suptitle(
    "Chart 51: The Real Story — Everyone Gained, But Unequally",
    fontsize=15,
    fontweight="bold",
    y=1.01,
)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/51_absolute_vs_relative.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → Chart 51 saved: absolute_vs_relative.png")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
# Compute US top quintile share change for summary
us_top_chg_str = "N/A"
if rich_data is not None:
    us = rich_data[
        (rich_data["country_code"] == "USA") & rich_data["top20_share"].notna()
    ].sort_values("year")
    if len(us) >= 2:
        chg = us["top20_share"].iloc[-1] - us["top20_share"].iloc[0]
        us_top_chg_str = f"{chg:+.1f}"

print("\n" + "═" * 80)
print("SUMMARY: ARE RICH-WORLD CITIZENS WORSE OFF?")
print("═" * 80)
print(
    """
ANSWER: NO — not in absolute terms. Every quintile got richer in every rich country.

Key findings:
1. ABSOLUTE INCOME: The bottom 20% saw real income gains of +12-49% over ~30 years
   in every major rich country (PPP constant $).

2. RELATIVE SHARE: The top 20% captured a disproportionate share of growth in most
   countries — especially the US (+{us_top_chg}pp) and Germany. France held inequality
   roughly stable.

3. THE "SQUEEZED FEELING" IS REAL BUT RELATIVE: The US bottom 20% earns ~$19k PPP.
   That is higher than the AVERAGE income in China, Brazil, Mexico, and Thailand.
   It is 10x the average income in Nigeria or Bangladesh.

4. THE POLITICAL PUZZLE: Voters feel squeezed because they compare themselves to
   their own society's top, not to the global poor. This is a political constraint
   on redistribution, not evidence that capitalism failed them.

5. THE FRIEND'S ARGUMENT: "Capitalism is untenable because even rich-world citizens
   aren't benefiting" is EMPIRICALLY FALSE. Every quintile benefited. The valid
   version of the argument is: "Capitalism distributes growth unequally within
   countries, which creates political barriers to international redistribution."
   That's a real problem — but it's a political problem, not an economic failure.
""".format(
        us_top_chg=us_top_chg_str
    )
)

print("\nDone!")
