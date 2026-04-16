"""
Analysis 17: Is the Energy Transition Actually on Track?
========================================================

The "Can everyone live well?" section leans heavily on the solar/storage
S-curve and an implicit claim that the rest of the decarbonization stack
follows. This analysis subjects that optimism to the same empirical
discipline the rest of the README applies, with deployment-reality data:

1. Global solar+wind generation vs. IEA NZE-2050 2030 waypoint
2. Global primary-energy fossil share, 1990–2024 (has the S-curve *displaced*
   fossils, or only supplemented them?)
3. US grid interconnection queue (LBNL "Queued Up" 2014–2024)
4. Levelized cost of storage (LCOS) by duration and chemistry
5. Critical mineral supply gap: copper demand (IEA NZE) vs announced supply
6. Global fossil-fuel subsidies, explicit + implicit (IMF Parry et al.)
7. China vs. US vs. EU leading-edge electrification: EV share of new car
   sales and electricity share of industrial final energy
8. Global final-energy consumption by sector with tractability tier overlay

Data sources:
- OWID energy dataset (charts 83, 84) — Ember + BP + EIA aggregated
- LBNL "Queued Up 2024" (chart 85) — published GW figures
- NREL ATB 2023 + BNEF 2023 LCOS summaries (chart 86)
- IEA Critical Minerals Outlook 2024 + S&P Global 2022 (chart 87)
- IMF Parry, Black & Vernon 2023 WP/23/169 (chart 88)
- IEA Global EV Outlook 2024 + IEA World Energy Balances (chart 89)
- IEA World Energy Balances 2023 + IEA NZE final-energy share (chart 90)

Figures 6–8 rely on hardcoded values extracted from published reports,
with sources cited in the captions, because the underlying datasets are
either proprietary (BNEF), in PDF tables (IEA Critical Minerals, IMF WP),
or reported in narrative form (LBNL Queued Up). OWID data is fetched live.

Charts: 83–90.
"""

from __future__ import annotations

import io
import subprocess
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", palette="colorblind")

CHART_DIR = Path("charts")
CHART_DIR.mkdir(exist_ok=True)
CACHE_DIR = Path("data/raw/energy_transition")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch(url: str, cache_name: str) -> str:
    cache = CACHE_DIR / cache_name
    if cache.exists() and cache.stat().st_size > 0:
        return cache.read_text()
    for _ in range(3):
        try:
            r = subprocess.run(
                [
                    "curl",
                    "-sSL",
                    "--http1.1",
                    "--max-time",
                    "120",
                    "--retry",
                    "3",
                    "--retry-all-errors",
                    "-o",
                    str(cache),
                    "-w",
                    "%{http_code}",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if (
                r.returncode == 0
                and cache.exists()
                and cache.stat().st_size > 0
                and r.stdout.strip().startswith("2")
            ):
                return cache.read_text()
            if cache.exists():
                cache.unlink()
        except Exception as e:
            print(f"  ! fetch attempt failed: {e}")
    print(f"  ! fetch failed for {cache_name}")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Load OWID energy dataset (used by charts 83, 84, 90)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[0] Downloading OWID energy dataset…")
OWID_URL = (
    "https://nyc3.digitaloceanspaces.com/owid-public/data/energy/owid-energy-data.csv"
)
owid_text = fetch(OWID_URL, "owid-energy-data.csv")
owid = pd.read_csv(io.StringIO(owid_text)) if owid_text else pd.DataFrame()
print(f"  rows={len(owid):,} cols={len(owid.columns)}")

world = owid[owid["country"] == "World"].copy() if not owid.empty else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Chart 83: Solar+wind vs IEA NZE 2030 waypoint
# ─────────────────────────────────────────────────────────────────────────────
print("\n[83] Solar+wind deployment vs IEA NZE trajectory…")
# IEA Net Zero by 2050 (2023 update) calls for roughly 8,300 TWh solar and
# 8,100 TWh wind by 2030 — combined ~16,400 TWh, up from ~4,400 TWh in 2024.
# Source: IEA, Net Zero Roadmap: A Global Pathway to Keep the 1.5 °C Goal in
# Reach (2023 update), Table A.3 ("Total electricity generation by source").

if not world.empty and "solar_electricity" in world.columns:
    sw = world[world["year"] >= 1990][
        ["year", "solar_electricity", "wind_electricity"]
    ].dropna(how="all")
    sw = sw.fillna(0)
    sw["combined"] = sw["solar_electricity"] + sw["wind_electricity"]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(
        sw["year"],
        sw["solar_electricity"],
        lw=2.5,
        label="Solar (actual)",
        color="#e69f00",
    )
    ax.plot(
        sw["year"],
        sw["wind_electricity"],
        lw=2.5,
        label="Wind (actual)",
        color="#0072b2",
    )
    ax.plot(
        sw["year"],
        sw["combined"],
        lw=2.8,
        label="Solar + wind (actual)",
        color="#009e73",
    )

    # NZE waypoints: 2024 actual ≈ 4,400 TWh (combined), 2030 target ≈ 16,400 TWh
    nze_years = [2024, 2030]
    nze_values = [sw["combined"].iloc[-1] if len(sw) else 4400, 16400]
    ax.plot(nze_years, nze_values, "r--", lw=2, label="IEA NZE 2030 target (combined)")
    ax.scatter([2030], [16400], color="red", s=80, zorder=5)
    ax.annotate(
        "NZE 2030\n~16,400 TWh",
        xy=(2030, 16400),
        xytext=(2027, 13500),
        fontsize=10,
        color="red",
        ha="center",
    )

    # Stated-policies / current-trend projection: extend combined curve with recent
    # CAGR (~20%/yr combined over last 5 years) for comparison
    last5 = sw.tail(6)
    if len(last5) >= 2:
        cagr = (last5["combined"].iloc[-1] / last5["combined"].iloc[0]) ** (1 / 5) - 1
        proj_years = np.arange(sw["year"].iloc[-1], 2031)
        proj = sw["combined"].iloc[-1] * (1 + cagr) ** (
            proj_years - sw["year"].iloc[-1]
        )
        ax.plot(
            proj_years,
            proj,
            ":",
            lw=2,
            color="gray",
            label=f"Current CAGR ({cagr*100:.0f}%/yr) extrapolation",
        )

    ax.set_xlabel("Year")
    ax.set_ylabel("Electricity generation (TWh)")
    ax.set_title(
        "Solar + wind deployment vs IEA Net Zero 2030 waypoint\n"
        "The S-curve is real — but still 3–4× below the 1.5 °C trajectory",
        fontsize=12,
    )
    ax.legend(loc="upper left", fontsize=10)
    ax.set_xlim(1990, 2031)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(CHART_DIR / "83_solar_wind_vs_nze.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(
        f"  last year {sw['year'].iloc[-1]}: solar {sw['solar_electricity'].iloc[-1]:,.0f} TWh, "
        f"wind {sw['wind_electricity'].iloc[-1]:,.0f} TWh, combined {sw['combined'].iloc[-1]:,.0f} TWh"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chart 84: Global primary energy fossil share (has the S-curve displaced fossils?)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[84] Global primary energy fossil share 1965–2024…")
if not world.empty:
    cols = [
        "year",
        "fossil_fuel_consumption",
        "primary_energy_consumption",
        "solar_consumption",
        "wind_consumption",
        "hydro_consumption",
        "nuclear_consumption",
        "biofuel_consumption",
        "other_renewable_consumption",
    ]
    have = [c for c in cols if c in world.columns]
    e = world[have].copy()
    e = e[e["year"] >= 1965].dropna(
        subset=["primary_energy_consumption", "fossil_fuel_consumption"]
    )
    e["fossil_share"] = (
        e["fossil_fuel_consumption"] / e["primary_energy_consumption"] * 100
    )
    e["solar_share"] = (
        e.get("solar_consumption", 0) / e["primary_energy_consumption"] * 100
    )
    e["wind_share"] = (
        e.get("wind_consumption", 0) / e["primary_energy_consumption"] * 100
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    ax1.fill_between(
        e["year"],
        0,
        e["fossil_share"],
        color="#d55e00",
        alpha=0.7,
        label="Fossil fuels",
    )
    ax1.plot(e["year"], e["fossil_share"], color="#662c00", lw=2)
    ax1.set_ylim(0, 100)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("% of global primary energy")
    ax1.set_title(
        "Fossil share of global primary energy\n"
        "1965: 94%  →  2024: ~82%. The S-curve is adding supply,\n"
        "not yet displacing fossils at aggregate scale.",
        fontsize=11,
    )
    ax1.grid(True, alpha=0.3)

    # Right panel: zoom on solar + wind share of primary energy (not electricity)
    ax2.plot(e["year"], e["solar_share"], color="#e69f00", lw=2.5, label="Solar")
    ax2.plot(e["year"], e["wind_share"], color="#0072b2", lw=2.5, label="Wind")
    ax2.plot(
        e["year"],
        e["solar_share"] + e["wind_share"],
        color="#009e73",
        lw=2.5,
        ls="--",
        label="Solar + wind",
    )
    ax2.set_xlabel("Year")
    ax2.set_ylabel("% of global primary energy")
    ax2.set_title(
        "Solar + wind as a share of primary energy\n"
        "Impressive growth — but starting from a very low base;\n"
        "~6–7% of primary energy in 2024 vs ~82% fossil",
        fontsize=11,
    )
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(1965, e["year"].max())

    plt.tight_layout()
    plt.savefig(CHART_DIR / "84_fossil_share_primary.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(
        f"  2024 fossil share: {e['fossil_share'].iloc[-1]:.1f}%, "
        f"solar+wind share: {(e['solar_share']+e['wind_share']).iloc[-1]:.1f}%"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chart 85: US grid interconnection queue (LBNL "Queued Up" 2024)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[85] US interconnection queue growth…")
# Source: LBNL, "Queued Up: Characteristics of Power Plants Seeking Transmission
# Interconnection" (annual, Rand Berkeley Lab). Numbers approximate from the
# 2024 edition (Rand, Seel, Bolinger, Wiser 2024). GW active in queues end-of-year.
queue_data = pd.DataFrame(
    {
        "year": [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "solar_gw": [240, 280, 340, 380, 430, 540, 680, 900, 1200, 1450, 1600],
        "wind_gw": [200, 210, 240, 260, 280, 340, 420, 520, 570, 600, 620],
        "storage_gw": [10, 20, 40, 60, 80, 120, 200, 400, 680, 1000, 1100],
        "gas_gw": [110, 120, 130, 150, 150, 140, 130, 120, 100, 95, 90],
        "total_gw": [600, 680, 800, 900, 1010, 1200, 1550, 2020, 2640, 3200, 3450],
    }
)

fig, ax = plt.subplots(figsize=(11, 6))
ax.stackplot(
    queue_data["year"],
    queue_data["solar_gw"],
    queue_data["wind_gw"],
    queue_data["storage_gw"],
    queue_data["gas_gw"],
    labels=["Solar", "Wind", "Storage", "Gas"],
    colors=["#e69f00", "#0072b2", "#cc79a7", "#999999"],
    alpha=0.85,
)
ax.plot(
    queue_data["year"], queue_data["total_gw"], "k-", lw=2.5, label="Total in queue"
)
ax.axhline(1300, color="red", ls="--", lw=1.5, alpha=0.6)
ax.text(
    2014.5, 1350, "US peak demand ≈ 1,300 GW (for reference)", color="red", fontsize=9
)

ax.set_xlabel("Year")
ax.set_ylabel("GW in interconnection queue (end of year)")
ax.set_title(
    "US transmission interconnection queue: 600 GW → ~3,450 GW in a decade\n"
    "Clean generation & storage waiting in line exceed total US grid capacity.\n"
    "Median wait time: ~5 years. The LCOE chart doesn't price this friction.",
    fontsize=11,
)
ax.legend(loc="upper left", fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xlim(2014, 2024)
plt.figtext(
    0.5,
    -0.02,
    'Source: Lawrence Berkeley National Laboratory, "Queued Up" (annual series, 2024 ed.)',
    ha="center",
    fontsize=9,
    style="italic",
)
plt.tight_layout()
plt.savefig(CHART_DIR / "85_interconnection_queue.png", dpi=150, bbox_inches="tight")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chart 86: LCOS by duration and chemistry
# ─────────────────────────────────────────────────────────────────────────────
print("\n[86] Levelized cost of storage by duration…")
# Sources: NREL ATB 2023 (Li-ion 4h: $190/MWh), BNEF LCOS 2H 2023 (Li-ion 2h,
# flow batteries, pumped hydro), Form Energy public targets (iron-air 100h).
# Numbers are approximate central estimates for US, 2024$.
lcos = pd.DataFrame(
    {
        "tech": [
            "Li-ion\n(2h)",
            "Li-ion\n(4h)",
            "Li-ion\n(8h)",
            "Flow\n(10h)",
            "Pumped hydro\n(12h)",
            "Iron-air\n(100h target)",
            "Iron-air\n(100h pilot est.)",
        ],
        "lcos": [180, 210, 320, 180, 150, 25, 80],  # $/MWh discharged
        "proven_at_gw": [True, True, False, False, True, False, False],
        "tier": [1, 1, 2, 2, 1, 3, 3],
    }
)

fig, ax = plt.subplots(figsize=(12, 6))
colors = {1: "#009e73", 2: "#e69f00", 3: "#d55e00"}
bar_colors = [colors[t] for t in lcos["tier"]]
bars = ax.bar(
    range(len(lcos)), lcos["lcos"], color=bar_colors, edgecolor="black", linewidth=1
)

# Annotate bars
for i, (bar, proven) in enumerate(zip(bars, lcos["proven_at_gw"])):
    h = bar.get_height()
    marker = "✓ at GW scale" if proven else "pre-commercial"
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        h + 8,
        f"${h:.0f}/MWh\n{marker}",
        ha="center",
        va="bottom",
        fontsize=9,
    )

ax.set_xticks(range(len(lcos)))
ax.set_xticklabels(lcos["tech"], fontsize=10)
ax.set_ylabel("Levelized Cost of Storage ($/MWh discharged, 2024$)")
ax.set_title(
    "Storage cost vs duration: Tier 1 proven, Tier 3 aspirational\n"
    "Short-duration Li-ion is cheap and deployed; 100h iron-air cost claim\n"
    "is a target, not a demonstrated figure.",
    fontsize=11,
)
ax.set_ylim(0, max(lcos["lcos"]) + 80)

# Legend for tiers
from matplotlib.patches import Patch

tier_legend = [
    Patch(facecolor=colors[1], label="Tier 1: Deployed at GW scale"),
    Patch(facecolor=colors[2], label="Tier 2: Commercial, scaling"),
    Patch(facecolor=colors[3], label="Tier 3: Target / pilot only"),
]
ax.legend(handles=tier_legend, loc="upper left")
ax.grid(True, alpha=0.3, axis="y")
plt.figtext(
    0.5,
    -0.02,
    "Sources: NREL ATB 2023; BloombergNEF LCOS 2H 2023; Form Energy published targets (2023). "
    "Iron-air LCOS is manufacturer target (~$20–30/MWh); pilot cost estimates are higher.",
    ha="center",
    fontsize=8,
    style="italic",
    wrap=True,
)
plt.tight_layout()
plt.savefig(CHART_DIR / "86_lcos_by_duration.png", dpi=150, bbox_inches="tight")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chart 87: Critical mineral supply gap (copper, lithium)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[87] Copper & lithium demand-supply gap…")
# Copper: S&P Global "The Future of Copper" (2022) — projects demand to double
# by 2035, from ~25 Mt to ~50 Mt/yr; announced supply (incl. recycling) reaches
# ~40 Mt, leaving ~10 Mt/yr gap.
# Lithium: IEA Critical Minerals Outlook 2024 — STEPS scenario demand quadruples
# by 2040; announced projects (including current production) cover ~65–70%.

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

# Copper panel
years = np.arange(2023, 2036)
baseline = np.linspace(25, 27, len(years))  # flat demand w/o transition
nze_demand = np.linspace(25, 50, len(years))  # NZE demand path
announced = np.linspace(25, 40, len(years))  # announced mining + recycling

ax = axes[0]
ax.plot(years, baseline, "--", color="gray", lw=2, label="Baseline (no transition)")
ax.plot(years, nze_demand, "-", color="#d55e00", lw=2.5, label="NZE/transition demand")
ax.plot(
    years, announced, "-", color="#009e73", lw=2.5, label="Announced + recycling supply"
)
ax.fill_between(
    years, announced, nze_demand, color="red", alpha=0.2, label="Supply gap"
)
ax.set_xlabel("Year")
ax.set_ylabel("Mt copper / yr")
ax.set_title(
    "Copper: the likeliest near-term bottleneck\n"
    "~10 Mt/yr gap by 2035 under NZE demand",
    fontsize=11,
)
ax.legend(loc="upper left", fontsize=9)
ax.grid(True, alpha=0.3)

# Lithium panel (IEA CM Outlook 2024, STEPS vs NZE; figures in kt LCE)
ax = axes[1]
years_li = [2023, 2030, 2040]
steps = [170, 520, 900]  # kt LCE/yr
nze = [170, 820, 1700]
announced_li = [170, 480, 650]
ax.plot(years_li, steps, "-o", color="#0072b2", lw=2.5, label="IEA STEPS demand")
ax.plot(years_li, nze, "-o", color="#d55e00", lw=2.5, label="IEA NZE demand")
ax.plot(
    years_li,
    announced_li,
    "-s",
    color="#009e73",
    lw=2.5,
    label="Announced project capacity",
)
ax.set_xlabel("Year")
ax.set_ylabel("kt lithium (LCE) / yr")
ax.set_title(
    "Lithium: announced projects cover ~65% of STEPS\n" "~40% of NZE demand by 2040",
    fontsize=11,
)
ax.legend(loc="upper left", fontsize=9)
ax.grid(True, alpha=0.3)

plt.suptitle(
    "Critical mineral demand vs supply: copper & lithium",
    fontsize=13,
    fontweight="bold",
    y=1.02,
)
plt.figtext(
    0.5,
    -0.02,
    'Sources: S&P Global, "The Future of Copper" (2022); IEA, Global Critical '
    "Minerals Outlook 2024. Numbers rounded; ranges wide.",
    ha="center",
    fontsize=9,
    style="italic",
)
plt.tight_layout()
plt.savefig(CHART_DIR / "87_critical_minerals_gap.png", dpi=150, bbox_inches="tight")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chart 88: Global fossil-fuel subsidies, explicit + implicit
# ─────────────────────────────────────────────────────────────────────────────
print("\n[88] Global fossil-fuel subsidies…")
# Source: Parry, Black & Vernon (2023), "Fossil Fuel Subsidies Surged to Record
# $7 Trillion in 2022", IMF Working Paper WP/23/169, Table 1.
# Explicit = undercharging for supply costs. Implicit = undercharging for
# environmental costs (air pollution, climate damages, forgone VAT).
subs = pd.DataFrame(
    {
        "year": [2015, 2017, 2020, 2022],
        "explicit": [0.54, 0.50, 0.45, 1.30],  # $T
        "implicit": [4.24, 4.30, 5.35, 5.70],  # $T
    }
)
subs["total"] = subs["explicit"] + subs["implicit"]

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(subs))
w = 0.4
ax.bar(
    x,
    subs["explicit"],
    w,
    label="Explicit (undercharging supply costs)",
    color="#d55e00",
    edgecolor="black",
)
ax.bar(
    x,
    subs["implicit"],
    w,
    bottom=subs["explicit"],
    label="Implicit (uncharged environmental + health costs)",
    color="#999999",
    edgecolor="black",
)
for i, row in subs.iterrows():
    ax.text(
        i,
        row["total"] + 0.1,
        f"${row['total']:.1f}T",
        ha="center",
        fontsize=11,
        fontweight="bold",
    )

ax.set_xticks(x)
ax.set_xticklabels(subs["year"])
ax.set_ylabel("Global fossil-fuel subsidies ($ trillion)")
ax.set_title(
    "Global fossil-fuel subsidies: $7T in 2022 — 7% of world GDP\n"
    "This is the size of the incumbent-resistance margin.\n"
    "For reference: total clean-energy investment was ~$1.8T (2023).",
    fontsize=11,
)
ax.legend(loc="upper left")
ax.grid(True, alpha=0.3, axis="y")
ax.set_ylim(0, 8.5)
plt.figtext(
    0.5,
    -0.02,
    "Source: Parry, Black & Vernon (2023), IMF Working Paper WP/23/169. "
    "Explicit jumped in 2022 due to Russia-Ukraine energy-price surge.",
    ha="center",
    fontsize=9,
    style="italic",
)
plt.tight_layout()
plt.savefig(CHART_DIR / "88_fossil_subsidies.png", dpi=150, bbox_inches="tight")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chart 89: China vs US vs EU — leading-edge electrification
# ─────────────────────────────────────────────────────────────────────────────
print("\n[89] China vs US vs EU electrification indicators…")
# Two panels:
#  (a) EV share of new car sales (IEA Global EV Outlook 2024, incl. PHEV+BEV)
#  (b) Electricity share of industrial final energy consumption (IEA World
#      Energy Balances 2023, approximate central values)

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# EV share of new sales
ev_years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
ev_data = {
    "China": [4.5, 4.9, 5.7, 15.5, 29.0, 38.0, 47.0],
    "European Union": [2.0, 3.5, 11.0, 18.0, 22.0, 22.0, 21.0],
    "United States": [2.0, 2.0, 2.2, 4.8, 8.0, 9.5, 10.5],
    "World": [2.1, 2.5, 4.2, 8.8, 14.0, 18.0, 22.0],
}
colors_c = {
    "China": "#d55e00",
    "European Union": "#0072b2",
    "United States": "#009e73",
    "World": "gray",
}

ax = axes[0]
for country, vals in ev_data.items():
    ax.plot(ev_years, vals, "-o", lw=2.5, label=country, color=colors_c[country])
ax.set_xlabel("Year")
ax.set_ylabel("EV share of new car sales (%)")
ax.set_title(
    "Electric vehicle share of new car sales\n"
    "China is 4–5× ahead of the US on the leading-edge\n"
    "consumer electrification indicator",
    fontsize=11,
)
ax.legend(loc="upper left")
ax.grid(True, alpha=0.3)

# Electricity share of industrial final energy
# Approximate central estimates from IEA World Energy Balances 2023
# ("electricity" as % of industrial final consumption, 2022 baseline).
ind_countries = ["United States", "European Union", "Japan", "China", "Korea"]
ind_shares = [21, 32, 29, 27, 42]

ax = axes[1]
bar_colors = ["#009e73", "#0072b2", "#cc79a7", "#d55e00", "#f0e442"]
bars = ax.barh(ind_countries, ind_shares, color=bar_colors, edgecolor="black")
for bar, v in zip(bars, ind_shares):
    ax.text(
        v + 0.5,
        bar.get_y() + bar.get_height() / 2,
        f"{v}%",
        va="center",
        fontsize=11,
        fontweight="bold",
    )
ax.set_xlabel("Electricity share of industrial final energy consumption (%)")
ax.set_title(
    "Industrial electrification rate (2022)\n"
    "China leads the US, though Korea and EU lead both.\n"
    "The remaining ~70–80% is industrial heat — the hard 80%.",
    fontsize=11,
)
ax.set_xlim(0, 55)
ax.grid(True, alpha=0.3, axis="x")

plt.figtext(
    0.5,
    -0.02,
    "Sources: IEA Global EV Outlook 2024 (left); IEA World Energy Balances 2023 (right). "
    "Industrial electrification share: electricity / total industrial final energy consumption.",
    ha="center",
    fontsize=9,
    style="italic",
)
plt.tight_layout()
plt.savefig(CHART_DIR / "89_electrification_leaders.png", dpi=150, bbox_inches="tight")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chart 90: Final-energy sector with tractability tier
# ─────────────────────────────────────────────────────────────────────────────
print("\n[90] Final-energy by sector with tractability scorecard…")
# Source: IEA World Energy Balances 2023 (global 2022 final consumption, ~440 EJ).
# Shares are approximate; "electricity" share of each sector from IEA sectoral breakdown.
# Tier scoring reflects maturity of a deployed, commercially-competitive
# low-carbon pathway:
#   Tier 1 = proven at scale, cost-competitive today
#   Tier 2 = demonstrated, scaling, partial cost parity
#   Tier 3 = requires breakthrough, pilot-only
sector = pd.DataFrame(
    {
        "sector": [
            "Buildings\n(heat + elec)",
            "Road transport",
            "Industry: low-temp\nheat (<200°C)",
            "Industry: high-temp\nheat (>400°C)",
            "Industry: feedstock\n(petchem, steel, cement)",
            "Aviation",
            "Shipping",
            "Agriculture",
        ],
        "share_final": [29, 19, 8, 15, 13, 3, 3, 2],  # % of global final energy
        "tier": [1, 1, 2, 2, 3, 3, 3, 2],
        "pathway": [
            "Heat pumps + elec + insulation",
            "EVs (cars), e-trucks emerging",
            "Industrial heat pumps, electric boilers",
            "Green H2, electric arc, CCS — scaling",
            "H2-DRI steel, new cement chem, biogenic petchem — pre-commercial at scale",
            "SAF (bio/synthetic) — 0.2% share, expensive",
            "Ammonia/methanol, battery-electric short-haul — early pilots",
            "Electric tractors, low-C fertilizers, precision ag",
        ],
    }
)

fig, ax = plt.subplots(figsize=(13, 7))
colors = {1: "#009e73", 2: "#e69f00", 3: "#d55e00"}
bar_colors = [colors[t] for t in sector["tier"]]
bars = ax.barh(
    range(len(sector)), sector["share_final"], color=bar_colors, edgecolor="black"
)

for i, (bar, row) in enumerate(zip(bars, sector.iterrows())):
    _, r = row
    ax.text(
        r["share_final"] + 0.3,
        i,
        f"{r['share_final']}%  —  {r['pathway']}",
        va="center",
        fontsize=9,
    )

ax.set_yticks(range(len(sector)))
ax.set_yticklabels(sector["sector"], fontsize=10)
ax.set_xlabel("Share of global final energy consumption (%)")
ax.set_title(
    "Global final energy by sector: the hard 80%\n"
    "Electricity is ~20% of final energy. The other 80% — industrial heat,\n"
    "aviation, shipping, feedstocks — is where decarbonization is hardest.",
    fontsize=12,
)
ax.set_xlim(0, 48)

from matplotlib.patches import Patch

tier_legend = [
    Patch(facecolor=colors[1], label="Tier 1: Proven, cost-competitive"),
    Patch(facecolor=colors[2], label="Tier 2: Demonstrated, scaling"),
    Patch(facecolor=colors[3], label="Tier 3: Requires breakthrough"),
]
ax.legend(handles=tier_legend, loc="lower right")
ax.grid(True, alpha=0.3, axis="x")
ax.invert_yaxis()
plt.figtext(
    0.5,
    -0.02,
    "Source: IEA World Energy Balances 2023 (global final consumption, ~440 EJ, 2022). "
    "Tier assignment reflects technical maturity and cost-parity status as of 2024.",
    ha="center",
    fontsize=9,
    style="italic",
)
plt.tight_layout()
plt.savefig(
    CHART_DIR / "90_final_energy_tractability.png", dpi=150, bbox_inches="tight"
)
plt.close()

print("\n✓ Analysis 17 complete. Charts 83–90 written to charts/.")
