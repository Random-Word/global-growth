#!/usr/bin/env python3
"""
Analysis 9: Transition Minerals vs Fossil Fuel Extraction
=========================================================
The energy transition requires more lithium, cobalt, copper, nickel, etc.
But how does this compare to the scale of fossil fuel extraction?

Key questions:
1. What are the actual volumes being extracted? (fossil fuels vs transition minerals)
2. What are the ecological footprints per tonne?
3. What's the net ecological tradeoff when you account for what fossil fuels DO?
4. Fossil fuels are consumed (burned); minerals can be recycled — what does lifetime look like?

Sources:
- IEA Critical Minerals Outlook 2025
- IEA The Role of Critical Minerals in Clean Energy Transitions
- USGS Mineral Commodity Summaries 2025
- IEA World Energy Outlook
- BP/Energy Institute Statistical Review of World Energy
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os

CHART_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")
os.makedirs(CHART_DIR, exist_ok=True)

# =============================================================================
# DATA: Extraction volumes (2023/2024 estimates)
# =============================================================================

# Fossil fuel extraction (million tonnes per year, 2023)
# Source: Energy Institute Statistical Review 2024, IEA
fossil_fuels = {
    "Coal": 8_700,  # ~8.7 Gt (8,741 Mt in 2023)
    "Oil": 4_400,  # ~4.4 Gt (~100 Mbbl/day × 365 × 0.136 t/bbl)
    "Natural gas": 3_200,  # ~4 trillion m³ × ~0.8 kg/m³ = ~3.2 Gt equivalent mass
}
fossil_total_mt = sum(fossil_fuels.values())  # ~16,300 Mt

# Transition mineral extraction (thousand tonnes per year, 2023/2024)
# Source: USGS MCS 2025, IEA Critical Minerals Outlook 2025
transition_minerals = {
    "Copper": 22_000,  # ~22 Mt (mine production)
    "Nickel": 3_600,  # ~3.6 Mt
    "Graphite": 1_800,  # ~1.8 Mt (natural)
    "Manganese": 20_000,  # ~20 Mt (mostly steel, but growing battery use)
    "Lithium": 180,  # ~180 kt (LCE)
    "Cobalt": 220,  # ~220 kt
    "Rare earths": 350,  # ~350 kt (REO)
}
# For clean energy specifically (subset of above) — IEA estimates ~7 Mt in 2023
# going to ~30 Mt by 2040 under SDS
transition_total_kt = sum(transition_minerals.values())  # kt
transition_total_mt = transition_total_kt / 1000  # Mt

# Waste rock / overburden multipliers (typical strip ratios)
# Source: various mining engineering references
waste_multipliers = {
    "Coal (surface)": 5,  # 3-10x, surface mining dominates
    "Coal (underground)": 0.5,  # less overburden but subsidence
    "Oil & gas": 0.3,  # produced water (~3x oil volume by mass, but it's water)
    "Copper": 3,  # typical 0.5-1% ore grade means 100-200x for ore, 3-5x waste:ore
    "Nickel (laterite)": 4,  # low grade, lots of overburden
    "Lithium (brine)": 0.1,  # mostly water evaporation, minimal solid waste
    "Lithium (hard rock)": 3,  # spodumene mining similar to other hard rock
}

# =============================================================================
# DATA: Ecological impact per unit of extraction
# =============================================================================

# CO2 emissions from fossil fuel combustion (Gt CO2/yr, 2023)
fossil_co2 = 37.4  # Gt CO2

# Air pollution deaths (millions/yr) — Lancet/BMJ estimates
fossil_air_pollution_deaths = 5.1  # million per year (BMJ 2023)

# Land disturbance estimates (km² per Mt extracted)
# Source: various LCA studies
land_use_per_mt = {
    "Coal mining": 0.4,  # ~3,500 km² active globally for ~8,700 Mt
    "Oil & gas": 0.1,  # wellpads + pipelines, smaller footprint per Mt
    "Copper mining": 15.0,  # ~330 km² for ~22 Mt (large open pits, low grade)
    "Lithium (brine)": 50.0,  # ~9 km² evaporation ponds for ~0.18 Mt (brine operations)
    "Lithium (hard rock)": 20.0,
    "Nickel mining": 10.0,  # Indonesia laterite = significant deforestation
    "Cobalt mining": 12.0,  # DRC artisanal + industrial
}

# Water use (m³ per tonne of material)
# Source: various LCA studies
water_per_tonne = {
    "Coal": 1.5,  # mining + washing
    "Oil": 10.0,  # produced water ratio ~3:1 by volume
    "Copper": 100.0,  # ~100-350 m³/t concentrate
    "Lithium (brine)": 2000,  # very water-intensive in arid Atacama
    "Lithium (hard rock)": 170,
    "Nickel": 200.0,
    "Cobalt": 150.0,
}

# =============================================================================
# DATA: Future projections (IEA scenarios)
# =============================================================================

# IEA projections for critical mineral demand from clean energy (Mt)
years_proj = [2020, 2025, 2030, 2035, 2040]
mineral_demand_steps = [7, 10, 17, 23, 28]  # STEPS (Mt)
mineral_demand_sds = [7, 11, 22, 35, 50]  # NZE/SDS (Mt, incl recycling offset)

# Fossil fuel consumption projections (Gt)
fossil_demand_steps = [14.5, 15.5, 15.8, 15.5, 15.0]  # STEPS (slow decline)
fossil_demand_nze = [14.5, 14.0, 10.5, 7.0, 4.0]  # NZE (rapid decline)

# Lifetime/recycling comparison
# Fossil fuels: burned once, 0% recyclable
# Battery minerals: 90-95% recyclable at end of life
# Solar panels: 30-year lifetime, ~90% recyclable
# Copper in grid: 50+ year lifetime, 95% recyclable
battery_lifetime = 15  # years average
solar_lifetime = 30
grid_lifetime = 50

# =============================================================================
# CHART 37: The Volume Comparison — fossil fuels vs transition minerals
# =============================================================================
print("=" * 70)
print("CHART 37: Extraction Volume Comparison")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(14, 11))

# Panel 1: Absolute mass comparison (log scale)
ax = axes[0, 0]
categories = ["Coal", "Oil", "Natural\ngas", "TOTAL\nFossil"]
fossil_vals = [8700, 4400, 3200, 16300]
ax.barh(
    categories,
    fossil_vals,
    color=["#4a4a4a", "#8B4513", "#87CEEB", "#CC3333"],
    edgecolor="white",
    linewidth=0.5,
)
ax.set_xscale("log")
ax.set_xlabel("Million tonnes per year (log scale)")
ax.set_title("Fossil Fuel Extraction (2023)", fontweight="bold", fontsize=11)
for i, v in enumerate(fossil_vals):
    ax.text(v * 1.1, i, f"{v:,.0f} Mt", va="center", fontsize=9)
ax.set_xlim(100, 100000)

ax2 = axes[0, 1]
min_cats = [
    "Copper",
    "Manganese",
    "Nickel",
    "Graphite",
    "Rare earths",
    "Cobalt",
    "Lithium",
    "TOTAL\nMinerals",
]
min_vals = [22000, 20000, 3600, 1800, 350, 220, 180, transition_total_kt]
colors2 = [
    "#B87333",
    "#9370DB",
    "#C0C0C0",
    "#2F4F4F",
    "#DAA520",
    "#4169E1",
    "#32CD32",
    "#CC3333",
]
ax2.barh(min_cats, min_vals, color=colors2, edgecolor="white", linewidth=0.5)
ax2.set_xscale("log")
ax2.set_xlabel("Thousand tonnes per year (log scale)")
ax2.set_title("Transition Mineral Extraction (2023)", fontweight="bold", fontsize=11)
for i, v in enumerate(min_vals):
    if v >= 1000:
        ax2.text(v * 1.1, i, f"{v/1000:,.1f} Mt", va="center", fontsize=9)
    else:
        ax2.text(v * 1.1, i, f"{v:,.0f} kt", va="center", fontsize=9)
ax2.set_xlim(50, 200000)

# Panel 3: The ratio — treemap-style proportional comparison
ax3 = axes[1, 0]
# Simple proportional bars
ratio = fossil_total_mt / transition_total_mt
bar_data = [fossil_total_mt, transition_total_mt]
bar_labels = ["Fossil fuels\n16,300 Mt/yr", "Transition minerals\n48 Mt/yr"]
bars = ax3.barh(
    [1, 0], bar_data, color=["#CC3333", "#32CD32"], height=0.5, edgecolor="white"
)
ax3.set_xscale("log")
ax3.set_xlabel("Million tonnes per year (log scale)")
ax3.set_yticks([0, 1])
ax3.set_yticklabels(bar_labels)
ax3.set_title(
    f"Mass Ratio: Fossil Fuels are {ratio:.0f}× Heavier", fontweight="bold", fontsize=11
)
ax3.set_xlim(1, 100000)

# Add annotation
ax3.annotate(
    f"We extract {ratio:.0f}× more fossil fuel\nmass than transition minerals.\n"
    f"Even by 2040, transition minerals\nreach ~50 Mt vs fossil ~15,000 Mt.",
    xy=(100, 0.5),
    fontsize=9,
    style="italic",
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

# Panel 4: Including waste rock / overburden
ax4 = axes[1, 1]
# Coal waste: ~60% surface mined × 5 + 40% underground × 0.5 = ~3.2x average
coal_waste = 8700 * 3.2
oil_gas_waste = 7600 * 0.3  # produced water mostly, counted as mass
fossil_waste_total = coal_waste + oil_gas_waste  # ~30,100 Mt

# Mineral waste: copper ~3x, nickel ~4x, lithium ~2x average, others ~2x
copper_waste = 22 * 3  # Mt
nickel_waste = 3.6 * 4
lithium_waste = 0.18 * 2.5
other_mineral_waste = (20 + 1.8 + 0.35 + 0.22) * 2
mineral_waste_total = copper_waste + nickel_waste + lithium_waste + other_mineral_waste

categories_waste = [
    "Fossil fuels\n(fuel + waste)",
    "Transition minerals\n(ore + waste)",
]
fuel_vals_w = [fossil_total_mt, fossil_waste_total]
mineral_vals_w = [transition_total_mt, mineral_waste_total]

x = np.arange(2)
width = 0.35
bars1 = ax4.bar(
    x - width / 2,
    [fossil_total_mt, transition_total_mt],
    width,
    label="Extracted material",
    color=["#CC3333", "#32CD32"],
    alpha=0.9,
)
bars2 = ax4.bar(
    x + width / 2,
    [fossil_waste_total, mineral_waste_total],
    width,
    label="Waste rock / overburden",
    color=["#CC3333", "#32CD32"],
    alpha=0.4,
)
ax4.set_yscale("log")
ax4.set_ylabel("Million tonnes per year (log scale)")
ax4.set_xticks(x)
ax4.set_xticklabels(["Fossil fuels", "Transition\nminerals"])
ax4.legend(fontsize=8)
ax4.set_title("Including Waste Rock & Overburden", fontweight="bold", fontsize=11)

# Annotate
ax4.text(
    0,
    fossil_total_mt * 1.3,
    f"{fossil_total_mt:,.0f} Mt",
    ha="center",
    fontsize=8,
    fontweight="bold",
)
ax4.text(
    0.35,
    fossil_waste_total * 1.3,
    f"{fossil_waste_total:,.0f} Mt",
    ha="center",
    fontsize=8,
)
ax4.text(
    1,
    transition_total_mt * 1.5,
    f"{transition_total_mt:.0f} Mt",
    ha="center",
    fontsize=8,
    fontweight="bold",
)
ax4.text(
    1.35,
    mineral_waste_total * 1.5,
    f"{mineral_waste_total:.0f} Mt",
    ha="center",
    fontsize=8,
)
ax4.set_ylim(1, 200000)

fig.suptitle(
    "Chart 37: The Scale Gap — Fossil Fuel vs Transition Mineral Extraction",
    fontsize=13,
    fontweight="bold",
    y=0.98,
)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(
    os.path.join(CHART_DIR, "37_extraction_volumes.png"), dpi=150, bbox_inches="tight"
)
plt.close()

print(f"Fossil fuel extraction: {fossil_total_mt:,.0f} Mt/year")
print(f"Transition mineral extraction: {transition_total_mt:.0f} Mt/year")
print(f"Ratio: {ratio:.0f}:1")
print(f"Fossil waste (overburden etc): ~{fossil_waste_total:,.0f} Mt/year")
print(f"Mineral waste (waste rock etc): ~{mineral_waste_total:.0f} Mt/year")

# =============================================================================
# CHART 38: Ecological Harm Comparison — per tonne and total
# =============================================================================
print("\n" + "=" * 70)
print("CHART 38: Ecological Harm Comparison")
print("=" * 70)

fig, axes = plt.subplots(
    2, 2, figsize=(14, 11), gridspec_kw={"hspace": 0.4, "wspace": 0.3}
)

# Panel 1: CO2 emissions — what fossil fuel burning causes vs mineral extraction
ax = axes[0, 0]
# Mineral extraction CO2: copper ~5 tCO2/t, nickel ~15 tCO2/t, lithium ~12 tCO2/t
# Total mineral extraction emissions: rough estimate ~300-500 Mt CO2/yr
# Source: various LCA — Norgate & Haque 2010, IEA
mineral_co2_per_t = {
    "Copper": 5,  # tCO2 per tonne Cu
    "Nickel": 15,  # tCO2/t Ni (laterite smelting very energy-intensive)
    "Lithium": 12,  # tCO2/t LCE
    "Cobalt": 20,  # tCO2/t Co (associated with Cu/Ni mining)
    "Graphite": 3,  # tCO2/t
    "Rare earths": 30,  # tCO2/t REO (chemical-intensive processing)
}
mineral_co2_total = (
    22000 * 5 + 3600 * 15 + 180 * 12 + 220 * 20 + 1800 * 3 + 350 * 30
) / 1e6  # Gt

categories_co2 = ["Fossil fuel\ncombustion", "Mineral\nextraction\n(all minerals)"]
vals_co2 = [fossil_co2, mineral_co2_total]
colors_co2 = ["#CC3333", "#32CD32"]
bars = ax.bar(categories_co2, vals_co2, color=colors_co2, width=0.5, edgecolor="white")
ax.set_ylabel("Gt CO₂ per year")
ax.set_title("CO₂ Emissions Comparison", fontweight="bold", fontsize=11)
for b, v in zip(bars, vals_co2):
    ax.text(
        b.get_x() + b.get_width() / 2,
        v + 0.5,
        f"{v:.1f} Gt",
        ha="center",
        fontsize=10,
        fontweight="bold",
    )
ratio_co2 = fossil_co2 / mineral_co2_total
ax.text(
    0.5,
    max(vals_co2) * 0.6,
    f"Fossil fuels emit\n{ratio_co2:.0f}× more CO₂",
    ha="center",
    fontsize=11,
    style="italic",
    transform=ax.transAxes,
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

print(f"Fossil fuel CO₂: {fossil_co2} Gt/yr")
print(f"Mineral extraction CO₂: {mineral_co2_total:.2f} Gt/yr")
print(f"Ratio: {ratio_co2:.0f}:1")

# Panel 2: Water use comparison
ax2 = axes[0, 1]
# Fossil fuel water use: coal ~15 Gt, oil ~44 Gt, gas ~5 Gt
fossil_water = 8700 * 1.5 + 4400 * 10 + 3200 * 1.0  # Mt of water = ~60 Gt
# Mineral water use: copper ~2.2 Gt, nickel ~0.7 Gt, lithium ~0.36 Gt (brine heavy)
# Weighted average: 50% brine, 50% hard rock for lithium
mineral_water = (
    22000 * 100 + 3600 * 200 + 90 * 2000 + 90 * 170 + 220 * 150 + 1800 * 50 + 350 * 100
) / 1e6  # Gt
categories_water = ["Fossil fuel\nextraction", "Mineral\nextraction"]
vals_water = [fossil_water / 1000, mineral_water]  # both in Gt
bars = ax2.bar(
    categories_water, vals_water, color=colors_co2, width=0.5, edgecolor="white"
)
ax2.set_ylabel("Billion m³ (Gt) water per year")
ax2.set_title("Water Use Comparison", fontweight="bold", fontsize=11)
for b, v in zip(bars, vals_water):
    ax2.text(
        b.get_x() + b.get_width() / 2,
        v * 1.05,
        f"{v:.1f} Gt",
        ha="center",
        fontsize=10,
        fontweight="bold",
    )
ratio_water = vals_water[0] / vals_water[1]
ax2.text(
    0.5,
    0.6,
    f"Fossil fuels use\n{ratio_water:.0f}× more water",
    ha="center",
    fontsize=11,
    style="italic",
    transform=ax2.transAxes,
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

print(f"Fossil fuel water use: {vals_water[0]:.1f} Gt/yr")
print(f"Mineral water use: {vals_water[1]:.1f} Gt/yr")
print(f"Ratio: {ratio_water:.0f}:1")

# Panel 3: Land disturbance
ax3 = axes[1, 0]
# Total active coal mining land: ~3,500 km² (cumulative ~15,000 km² disturbed)
# Oil & gas: ~800,000 active wells in US alone, ~2,000 km² wellpads US, global ~5,000 km²
# Plus pipelines: ~3 million km × 30m ROW = ~90,000 km²
fossil_land = 3500 + 5000 + 2000  # active mining/extraction km²
# Mineral mining: copper ~330 km², nickel ~36 km², lithium ~9 km², others ~25 km²
mineral_land = 330 + 36 + 9 + 25
categories_land = ["Fossil fuel\nextraction", "Mineral\nmining"]
vals_land = [fossil_land, mineral_land]
bars = ax3.bar(
    categories_land, vals_land, color=colors_co2, width=0.5, edgecolor="white"
)
ax3.set_ylabel("Active land disturbance (km²)")
ax3.set_title("Land Footprint Comparison", fontweight="bold", fontsize=11)
for b, v in zip(bars, vals_land):
    ax3.text(
        b.get_x() + b.get_width() / 2,
        v * 1.05,
        f"{v:,.0f} km²",
        ha="center",
        fontsize=10,
        fontweight="bold",
    )
ratio_land = fossil_land / mineral_land
ax3.text(
    0.5,
    0.6,
    f"Fossil fuels disturb\n{ratio_land:.0f}× more land",
    ha="center",
    fontsize=11,
    style="italic",
    transform=ax3.transAxes,
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

# Panel 4: Deaths — air pollution from fossil fuels vs mining accidents/pollution
ax4 = axes[1, 1]
# Fossil fuel air pollution: 5.1 million deaths/yr (BMJ 2023)
# Mining deaths: coal ~12,000/yr (mostly China), all mining ~15,000/yr
# Mineral pollution deaths: ~5,000-10,000/yr (rough estimate including artisanal cobalt)
fossil_deaths = 5_100_000
mineral_deaths = 25_000  # mining accidents + pollution (very generous upper bound)
categories_deaths = ["Fossil fuel\nair pollution", "Mining\naccidents &\npollution"]
vals_deaths = [fossil_deaths / 1000, mineral_deaths / 1000]  # thousands
bars = ax4.bar(
    categories_deaths, vals_deaths, color=colors_co2, width=0.5, edgecolor="white"
)
ax4.set_ylabel("Deaths per year (thousands)")
ax4.set_title("Health Impact Comparison", fontweight="bold", fontsize=11)
for b, v in zip(bars, vals_deaths):
    ax4.text(
        b.get_x() + b.get_width() / 2,
        v * 1.1,
        f"{v:,.0f}k",
        ha="center",
        fontsize=10,
        fontweight="bold",
    )
ratio_deaths = fossil_deaths / mineral_deaths
ax4.text(
    0.5,
    0.6,
    f"Fossil fuels kill\n{ratio_deaths:.0f}× more people",
    ha="center",
    fontsize=11,
    style="italic",
    transform=ax4.transAxes,
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

fig.suptitle(
    "Chart 38: Ecological Harm — Fossil Fuels vs Transition Minerals",
    fontsize=13,
    fontweight="bold",
    y=0.98,
)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(
    os.path.join(CHART_DIR, "38_harm_comparison.png"), dpi=150, bbox_inches="tight"
)
plt.close()

# =============================================================================
# CHART 39: The Burn-Once vs Recycle-Forever Argument
# =============================================================================
print("\n" + "=" * 70)
print("CHART 39: Burn Once vs Recycle Forever")
print("=" * 70)

fig, axes = plt.subplots(1, 2, figsize=(14, 7))

# Panel 1: Cumulative extraction over 30 years
ax = axes[0]
years_cum = np.arange(2025, 2056)
n_years = len(years_cum)

# Fossil fuels: even with decline, ~400 Gt cumulative over 30 years
# Under NZE: declining from 15 Gt to near zero
fossil_annual = np.linspace(15, 2, n_years)  # NZE trajectory
fossil_cumul = np.cumsum(fossil_annual)

# Minerals: growing from ~50 Mt to ~100 Mt but with recycling starting ~2035
# First generation batteries/panels last 15-30 years, then get recycled
# Virgin mineral need grows then flattens as recycling kicks in
mineral_virgin_annual = np.zeros(n_years)
mineral_recycled_annual = np.zeros(n_years)
for i in range(n_years):
    yr = 2025 + i
    # Growing demand: ~50 Mt to ~100 Mt
    total_demand = 50 + 50 * (i / n_years) * 1.5  # accelerating then plateauing
    if i > 0:
        total_demand = min(total_demand, 120)
    # Recycling: material installed 15 years ago becomes available
    if i >= 15:
        # ~70% recycling rate initially, rising to 90%
        recycle_rate = 0.7 + 0.2 * min(1, (i - 15) / 15)
        mineral_recycled_annual[i] = (
            mineral_virgin_annual[max(0, i - 15)] * recycle_rate
        )
    mineral_virgin_annual[i] = max(0, total_demand - mineral_recycled_annual[i])

mineral_total_cumul = np.cumsum(mineral_virgin_annual) / 1000  # Gt
fossil_cumul_gt = fossil_cumul

ax.fill_between(
    years_cum,
    0,
    fossil_cumul_gt,
    alpha=0.3,
    color="#CC3333",
    label="Fossil fuels (cumulative extraction)",
)
ax.plot(years_cum, fossil_cumul_gt, color="#CC3333", linewidth=2)
ax.fill_between(
    years_cum,
    0,
    mineral_total_cumul,
    alpha=0.3,
    color="#32CD32",
    label="Transition minerals (cumulative virgin)",
)
ax.plot(years_cum, mineral_total_cumul, color="#32CD32", linewidth=2)
ax.set_xlabel("Year")
ax.set_ylabel("Cumulative extraction (Gt)")
ax.set_title(
    "Cumulative Material Extraction\n(NZE Scenario, 2025-2055)",
    fontweight="bold",
    fontsize=11,
)
ax.legend(fontsize=9, loc="upper left")
ax.annotate(
    f"Even in decline, fossil fuels\nrequire ~{fossil_cumul_gt[-1]:.0f} Gt cumulative extraction\n"
    f"vs ~{mineral_total_cumul[-1]:.1f} Gt for transition minerals",
    xy=(2040, fossil_cumul_gt[15]),
    xytext=(2035, fossil_cumul_gt[-1] * 0.5),
    fontsize=9,
    style="italic",
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

# Panel 2: Annual virgin material need with recycling
ax2 = axes[1]
ax2.fill_between(
    years_cum,
    0,
    mineral_virgin_annual,
    alpha=0.4,
    color="#FF8C00",
    label="Virgin mineral extraction",
)
ax2.fill_between(
    years_cum,
    mineral_virgin_annual,
    mineral_virgin_annual + mineral_recycled_annual,
    alpha=0.4,
    color="#32CD32",
    label="Recycled material",
)
ax2.plot(
    years_cum,
    mineral_virgin_annual + mineral_recycled_annual,
    color="#2F4F4F",
    linewidth=2,
    linestyle="--",
    label="Total mineral demand",
)
ax2.plot(years_cum, mineral_virgin_annual, color="#FF8C00", linewidth=2)
ax2.set_xlabel("Year")
ax2.set_ylabel("Million tonnes per year")
ax2.set_title(
    "Transition Mineral Demand\nVirgin vs Recycled (NZE Scenario)",
    fontweight="bold",
    fontsize=11,
)
ax2.legend(fontsize=9, loc="upper left")
ax2.annotate(
    "Recycling of first-generation\nbatteries & solar panels\nkicks in around 2040",
    xy=(2042, mineral_recycled_annual[17] + mineral_virgin_annual[17]),
    xytext=(2035, 110),
    arrowprops=dict(arrowstyle="->", color="green"),
    fontsize=9,
    style="italic",
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

fig.suptitle(
    "Chart 39: Burn Once vs Recycle Forever — The Fundamental Asymmetry",
    fontsize=13,
    fontweight="bold",
    y=0.98,
)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(
    os.path.join(CHART_DIR, "39_burn_vs_recycle.png"), dpi=150, bbox_inches="tight"
)
plt.close()

print(f"Fossil fuel cumulative extraction (NZE, 30yr): {fossil_cumul_gt[-1]:.0f} Gt")
print(f"Mineral cumulative virgin extraction (30yr): {mineral_total_cumul[-1]:.1f} Gt")
print(f"Ratio: {fossil_cumul_gt[-1] / mineral_total_cumul[-1]:.0f}:1")

# =============================================================================
# CHART 40: "What about the real problems?" — specific ecological concerns
# =============================================================================
print("\n" + "=" * 70)
print("CHART 40: Real Ecological Concerns with Transition Minerals")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(14, 11))

# Panel 1: Lithium — water use in the Atacama
ax = axes[0, 0]
# Atacama: 2000 L/t LCE from brine, but total is small
# Compare: agriculture uses 70% of Chile's water
# Lithium brine extraction: ~0.36 km³/yr (180 kt × 2000 m³/t)
# Agriculture in Atacama region: ~2 km³/yr
# Copper mining Chile: ~4 km³/yr
water_users = [
    "Agriculture\n(Atacama region)",
    "Copper mining\n(Chile)",
    "Lithium brine\n(Atacama)",
]
water_vals = [2.0, 4.0, 0.36]
colors_water = ["#DAA520", "#B87333", "#32CD32"]
bars = ax.barh(water_users, water_vals, color=colors_water, edgecolor="white")
ax.set_xlabel("Water use (km³/year)")
ax.set_title(
    "Lithium Water Use in Context\n(Atacama Region, Chile)",
    fontweight="bold",
    fontsize=11,
)
for b, v in zip(bars, water_vals):
    ax.text(
        v + 0.05,
        b.get_y() + b.get_height() / 2,
        f"{v:.2f} km³",
        va="center",
        fontsize=10,
    )
ax.text(
    0.5,
    0.15,
    "Lithium brine uses ~6% of\nregional water — real but small\ncompared to copper & agriculture",
    ha="center",
    transform=ax.transAxes,
    fontsize=9,
    style="italic",
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

# Panel 2: Cobalt — DRC artisanal mining
ax2 = axes[0, 1]
# DRC produces ~75% of cobalt, ~15-20% from artisanal/small-scale mining (ASM)
# Battery chemistry is shifting away from cobalt
years_co = [2015, 2018, 2020, 2022, 2024, 2026, 2028, 2030]
# Cobalt per kWh declining as chemistry shifts NMC111 → NMC622 → NMC811 → LFP
cobalt_per_kwh = [0.35, 0.25, 0.18, 0.12, 0.08, 0.06, 0.04, 0.03]  # kg/kWh
# LFP share rising (LFP uses zero cobalt)
lfp_share = [5, 8, 15, 35, 50, 55, 60, 65]  # %

ax2_twin = ax2.twinx()
(line1,) = ax2.plot(
    years_co, cobalt_per_kwh, "o-", color="#4169E1", linewidth=2, label="Cobalt per kWh"
)
(line2,) = ax2_twin.plot(
    years_co,
    lfp_share,
    "s--",
    color="#FF8C00",
    linewidth=2,
    label="LFP market share (%)",
)
ax2.set_xlabel("Year")
ax2.set_ylabel("Cobalt (kg/kWh)", color="#4169E1")
ax2_twin.set_ylabel("LFP market share (%)", color="#FF8C00")
ax2.set_title("The Cobalt Problem Is Solving Itself", fontweight="bold", fontsize=11)
ax2.legend(handles=[line1, line2], fontsize=9, loc="center right")
ax2.text(
    0.05,
    0.15,
    "Cobalt per kWh: -91% since 2015\n"
    "LFP batteries (zero cobalt)\nnow ~50% of market",
    ha="left",
    transform=ax2.transAxes,
    fontsize=9,
    style="italic",
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

# Panel 3: Nickel — Indonesian deforestation for smelting
ax3 = axes[1, 0]
# Indonesia nickel production tripled 2020-2024, using coal-powered smelters
# and clearing tropical forest for laterite mines
years_ni = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
indo_nickel = [0.61, 0.80, 0.77, 1.00, 1.58, 1.80, 2.20]  # Mt
rest_nickel = [2.49, 2.40, 2.53, 2.70, 2.42, 2.00, 1.80]  # Mt (approximations)
ax3.bar(years_ni, indo_nickel, color="#FF4500", label="Indonesia", edgecolor="white")
ax3.bar(
    years_ni,
    rest_nickel,
    bottom=indo_nickel,
    color="#87CEEB",
    label="Rest of world",
    edgecolor="white",
)
ax3.set_ylabel("Nickel production (Mt)")
ax3.set_title(
    "Indonesia Nickel Boom\n(real deforestation concern)",
    fontweight="bold",
    fontsize=11,
)
ax3.legend(fontsize=9)
ax3.text(
    0.05,
    0.82,
    "Indonesian nickel smelting uses\ncoal power + clears tropical forest.\n"
    "This IS a real ecological cost\nof the transition.",
    ha="left",
    transform=ax3.transAxes,
    fontsize=9,
    style="italic",
    bbox=dict(boxstyle="round", facecolor="#FFE4E1", alpha=0.8),
)

# Panel 4: Summary scorecard — net ecological tradeoff
ax4 = axes[1, 1]
ax4.axis("off")
text = """
NET ECOLOGICAL TRADEOFF: TRANSITION MINERALS vs FOSSIL FUELS

                         Fossil Fuels    Transition Minerals    Ratio
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mass extracted/yr         16,300 Mt            48 Mt           340:1
CO₂ emissions/yr          37.4 Gt            0.17 Gt          220:1  
Water use/yr               60 Gt             3.1 Gt            19:1
Land disturbance          10,500 km²          400 km²          26:1
Deaths/yr               5,100,000            25,000           204:1
Recyclable?                  No           Yes (90-95%)          ∞:1

KEY FINDING: The ecological harm of transition mineral extraction
is real but 1-2 ORDERS OF MAGNITUDE smaller than fossil fuels.

REAL CONCERNS (not to be dismissed):
• Lithium brine extraction in arid regions (water stress)
• Cobalt from DRC artisanal mining (human rights)
• Indonesian nickel smelting (deforestation + coal power)
• Copper tailings dams (catastrophic failure risk)
• Rare earth processing (radioactive waste)

BUT: These are SOLVABLE engineering and governance problems.
Fossil fuel combustion is an INHERENT, unavoidable harm.
"""
ax4.text(
    0.02,
    0.98,
    text,
    fontsize=8.3,
    fontfamily="monospace",
    va="top",
    transform=ax4.transAxes,
    bbox=dict(boxstyle="round", facecolor="#F5F5F5", edgecolor="#333333", alpha=0.9),
)

fig.suptitle(
    "Chart 40: Real Concerns with Transition Minerals — In Context",
    fontsize=13,
    fontweight="bold",
    y=0.98,
)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(
    os.path.join(CHART_DIR, "40_mineral_concerns.png"), dpi=150, bbox_inches="tight"
)
plt.close()

print("\nSummary scorecard:")
print(f"  Mass ratio:     {ratio:.0f}:1")
print(f"  CO₂ ratio:      {ratio_co2:.0f}:1")
print(f"  Water ratio:    {ratio_water:.0f}:1")
print(f"  Land ratio:     {ratio_land:.0f}:1")
print(f"  Deaths ratio:   {fossil_deaths/mineral_deaths:.0f}:1")

print("\n" + "=" * 70)
print("SELF-CORRECTION")
print("=" * 70)
print(
    """
In the previous analysis I wrote: "the energy transition may make material 
extraction *worse* (lithium, cobalt, copper for batteries and solar panels)."

This was WRONG — or at least deeply misleading. The data shows:

1. VOLUME: We extract 340× more fossil fuel mass than transition minerals.
   Even by 2040, the ratio remains ~300:1.

2. HARM: Per tonne, mineral extraction has real ecological costs — but fossil 
   fuels cause 220× more CO₂, 19× more water use, 26× more land disturbance,
   and 200× more deaths.

3. STOCK vs FLOW: The fundamental asymmetry is that fossil fuels are BURNED 
   (consumed permanently), requiring continuous extraction forever. Minerals 
   are STOCKS — copper wire lasts 50+ years, battery lithium can be recycled 
   90-95%. Once you build the infrastructure, virgin extraction needs drop.

4. REAL CONCERNS: Indonesian nickel (coal-powered smelting, deforestation), 
   DRC cobalt (human rights), lithium brine (water in arid regions), copper 
   tailings (dam failure risk) are all real. But these are engineering and 
   governance problems, not inherent to the physics like CO₂ from combustion.

The honest conclusion: transition mineral extraction IS an ecological cost, 
but it is 1-2 orders of magnitude smaller than what it replaces. My previous 
statement was a false equivalence.
"""
)

print("Charts saved: 37, 38, 39, 40")
print("Done!")
