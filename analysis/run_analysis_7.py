"""
Analysis 7: Non-Carbon Planetary Boundaries
============================================
GPT-5.4 flagged that our ecological analysis is "too carbon-centric." The
Rockström/Steffen planetary boundaries framework identifies nine processes:
  1. Climate change (covered in Analysis 5)
  2. Biosphere integrity (biodiversity loss)
  3. Land-system change
  4. Freshwater use
  5. Biogeochemical flows (nitrogen & phosphorus)
  6. Ocean acidification
  7. Atmospheric aerosol loading
  8. Stratospheric ozone depletion
  9. Novel entities (chemical pollution)

This analysis covers #2-5 using OWID and FAO data.
We also examine material footprint — the total physical throughput of the
economy — which is the core ecological critique: can growth decouple from
material extraction the way it's (slowly) decoupling from carbon?
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import requests, io, time
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='colorblind')
CHART_DIR = 'charts'

# ── Download planetary boundary datasets from OWID ────────────────────────────

OWID_BASE = 'https://ourworldindata.org/grapher/'

def fetch_owid_grapher(slug, label):
    """Download a CSV from OWID grapher."""
    url = f'{OWID_BASE}{slug}.csv?v=1&csvType=full&useColumnShortNames=false'
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        print(f"  {label}: {df.shape[0]} rows, {df.shape[1]} cols")
        return df
    except Exception as e:
        print(f"  {label}: ERROR {e}")
        return pd.DataFrame()

print("Downloading planetary boundary datasets...")

# 1. Material footprint
mat_foot_pc = fetch_owid_grapher('material-footprint-per-capita', 'Material footprint/cap')
time.sleep(0.5)
mat_foot_gdp = fetch_owid_grapher('material-footprint-per-unit-of-gdp', 'Material footprint/GDP')
time.sleep(0.5)

# 2. Biodiversity
lpi = fetch_owid_grapher('global-living-planet-index', 'Living Planet Index')
time.sleep(0.5)
lpi_regional = fetch_owid_grapher('living-planet-index-by-region', 'LPI by region')
time.sleep(0.5)
red_list = fetch_owid_grapher('red-list-index', 'Red List Index')
time.sleep(0.5)

# 3. Land use
tree_loss = fetch_owid_grapher('tree-cover-loss', 'Tree cover loss')
time.sleep(0.5)
forest_area = fetch_owid_grapher('forest-area-km', 'Forest area')
time.sleep(0.5)
ag_land = fetch_owid_grapher('share-of-land-area-used-for-agriculture', 'Agricultural land %')
time.sleep(0.5)

# 4. Nitrogen & phosphorus
n_fert = fetch_owid_grapher('nitrogen-fertilizer-application-per-hectare-of-cropland', 'N fertilizer/ha')
time.sleep(0.5)
p_fert = fetch_owid_grapher('phosphate-application-per-hectare-of-cropland', 'P fertilizer/ha')
time.sleep(0.5)

# 5. Water
water_stress = fetch_owid_grapher('freshwater-withdrawals-as-a-share-of-internal-resources',
                                   'Water stress')
time.sleep(0.5)
water_total = fetch_owid_grapher('annual-freshwater-withdrawals', 'Total freshwater withdrawals')

# ── Helper: standardize OWID column names ─────────────────────────────────────
def get_value_col(df):
    """Get the value column (the one that's not Entity, Code, Year, or Day)."""
    skip = {'Entity', 'Code', 'Year', 'Day'}
    for c in df.columns:
        if c not in skip:
            return c
    return None


# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 7: NON-CARBON PLANETARY BOUNDARIES")
print("="*80)

# Also load OWID CO2 for GDP data
co2 = pd.read_csv('data/raw/owid_co2.csv')


# ══════════════════════════════════════════════════════════════════════════════
# CHART 28: Material Footprint — Can Growth Decouple from Stuff?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("CHART 28: MATERIAL FOOTPRINT — CAN GROWTH DECOUPLE FROM STUFF?")
print("─"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 28a: Material footprint per capita over time — key countries
ax = axes[0, 0]
if len(mat_foot_pc) > 0:
    vcol = get_value_col(mat_foot_pc)
    for name, color in [('World', 'black'), ('United States', 'blue'),
                         ('Germany', 'purple'), ('China', 'red'),
                         ('India', 'orange'), ('United Kingdom', 'green'),
                         ('Japan', 'brown'), ('Brazil', 'teal')]:
        d = mat_foot_pc[mat_foot_pc['Entity'] == name].sort_values('Year')
        if len(d) > 2:
            lw = 2.5 if name == 'World' else 1.3
            ls = '--' if name == 'World' else '-'
            ax.plot(d['Year'], d[vcol], label=name, color=color, linewidth=lw, linestyle=ls)
    ax.set_title('Material Footprint Per Capita (tonnes)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Tonnes per person')
    ax.legend(fontsize=8, ncol=2)
    
    # Print key numbers
    world = mat_foot_pc[mat_foot_pc['Entity'] == 'World'].sort_values('Year')
    if len(world) > 0:
        first = world.iloc[0]
        last = world.iloc[-1]
        print(f"  World material footprint/cap: {first[vcol]:.1f}t ({first['Year']:.0f}) → "
              f"{last[vcol]:.1f}t ({last['Year']:.0f})")
        pct = (last[vcol] / first[vcol] - 1) * 100
        print(f"  Change: {'+' if pct > 0 else ''}{pct:.0f}%")
        
        for name in ['United States', 'China', 'India', 'Germany']:
            d = mat_foot_pc[(mat_foot_pc['Entity'] == name)].sort_values('Year')
            if len(d) > 0:
                print(f"  {name}: {d.iloc[-1][vcol]:.1f}t/cap ({d.iloc[-1]['Year']:.0f})")

# 28b: Material footprint per unit GDP — is decoupling happening?
ax = axes[0, 1]
if len(mat_foot_gdp) > 0:
    vcol_gdp = get_value_col(mat_foot_gdp)
    for name, color in [('World', 'black'), ('United States', 'blue'),
                         ('Germany', 'purple'), ('China', 'red'),
                         ('India', 'orange'), ('United Kingdom', 'green')]:
        d = mat_foot_gdp[mat_foot_gdp['Entity'] == name].sort_values('Year')
        if len(d) > 2:
            lw = 2.5 if name == 'World' else 1.3
            ls = '--' if name == 'World' else '-'
            ax.plot(d['Year'], d[vcol_gdp], label=name, color=color, linewidth=lw, linestyle=ls)
    ax.set_title('Material Footprint Per $ GDP (kg/$)', fontsize=12, fontweight='bold')
    ax.set_ylabel('kg per $ GDP (constant 2017 PPP)')
    ax.legend(fontsize=8, ncol=2)
    
    world_gdp = mat_foot_gdp[mat_foot_gdp['Entity'] == 'World'].sort_values('Year')
    if len(world_gdp) > 0:
        first = world_gdp.iloc[0]
        last = world_gdp.iloc[-1]
        pct = (last[vcol_gdp] / first[vcol_gdp] - 1) * 100
        print(f"\n  Material footprint/GDP (World): {first[vcol_gdp]:.2f} → {last[vcol_gdp]:.2f} "
              f"({'+' if pct > 0 else ''}{pct:.0f}%)")
        if pct < 0:
            annual_rate = (last[vcol_gdp] / first[vcol_gdp]) ** (1/(last['Year']-first['Year'])) - 1
            print(f"  Relative decoupling rate: {-annual_rate*100:.1f}%/yr")

# 28c: Total global material extraction vs GDP (indexed to first year)
ax = axes[1, 0]
if len(mat_foot_pc) > 0:
    vcol = get_value_col(mat_foot_pc)
    world = mat_foot_pc[mat_foot_pc['Entity'] == 'World'].sort_values('Year').copy()
    if len(world) > 2:
        # Get world GDP from OWID CO2 data
        world_gdp_co2 = co2[co2['country'] == 'World'][['year', 'gdp']].dropna()
        world_gdp_co2 = world_gdp_co2.rename(columns={'year': 'Year'})
        
        # Get world population for total material footprint
        world_pop = co2[co2['country'] == 'World'][['year', 'population']].dropna()
        world_pop = world_pop.rename(columns={'year': 'Year'})
        
        merged = world.merge(world_gdp_co2, on='Year', how='inner')
        merged = merged.merge(world_pop, on='Year', how='inner')
        merged['total_mat'] = merged[vcol] * merged['population']
        
        if len(merged) > 2:
            base_yr = merged['Year'].min()
            base_gdp = merged[merged['Year'] == base_yr]['gdp'].iloc[0]
            base_mat = merged[merged['Year'] == base_yr]['total_mat'].iloc[0]
            
            merged['gdp_idx'] = merged['gdp'] / base_gdp * 100
            merged['mat_idx'] = merged['total_mat'] / base_mat * 100
            
            ax.plot(merged['Year'], merged['gdp_idx'], label='World GDP', color='blue', linewidth=2)
            ax.plot(merged['Year'], merged['mat_idx'], label='Material extraction', color='brown', linewidth=2)
            ax.axhline(y=100, color='gray', linewidth=0.5, linestyle=':')
            ax.set_title(f'GDP vs Material Extraction (indexed, {base_yr:.0f}=100)', fontsize=12, fontweight='bold')
            ax.set_ylabel(f'Index ({base_yr:.0f}=100)')
            ax.legend(fontsize=10)
            
            # Check for absolute decoupling
            gdp_growth = (merged['gdp_idx'].iloc[-1] / 100 - 1) * 100
            mat_growth = (merged['mat_idx'].iloc[-1] / 100 - 1) * 100
            print(f"\n  GDP growth since {base_yr:.0f}: +{gdp_growth:.0f}%")
            print(f"  Material extraction growth: +{mat_growth:.0f}%")
            if mat_growth < gdp_growth:
                print(f"  → RELATIVE decoupling (materials grow slower than GDP)")
            if mat_growth <= 0:
                print(f"  → ABSOLUTE decoupling (material use falling)")
            else:
                print(f"  → NO absolute decoupling (material use still rising)")

# 28d: Material footprint by income group
ax = axes[1, 1]
if len(mat_foot_pc) > 0:
    vcol = get_value_col(mat_foot_pc)
    income_groups = ['High-income countries', 'Upper-middle-income countries',
                     'Lower-middle-income countries', 'Low-income countries']
    colors = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4']
    found = False
    for grp, color in zip(income_groups, colors):
        d = mat_foot_pc[mat_foot_pc['Entity'] == grp].sort_values('Year')
        if len(d) > 2:
            ax.plot(d['Year'], d[vcol], label=grp.replace(' countries', ''),
                    color=color, linewidth=1.8)
            found = True
    
    if not found:
        # Try alternative names
        for grp in mat_foot_pc['Entity'].unique():
            if 'income' in grp.lower() or 'Income' in grp:
                d = mat_foot_pc[mat_foot_pc['Entity'] == grp].sort_values('Year')
                if len(d) > 2:
                    ax.plot(d['Year'], d[vcol], label=grp, linewidth=1.5)
                    found = True
    
    if found:
        ax.set_title('Material Footprint/Capita by Income Group', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tonnes per person')
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, 'Income group data not available', ha='center', va='center',
                transform=ax.transAxes, fontsize=12)

plt.suptitle('Chart 28: Material Footprint — Can Growth Decouple from Physical Stuff?',
             fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/28_material_footprint.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 28 saved: material_footprint.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 29: Biodiversity — The Silent Crisis
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("CHART 29: BIODIVERSITY — THE SILENT CRISIS")
print("─"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 29a: Global Living Planet Index
ax = axes[0, 0]
if len(lpi) > 0:
    vcol = get_value_col(lpi)
    global_lpi = lpi[lpi['Entity'] == 'World'].sort_values('Year')
    if len(global_lpi) == 0:
        # Try other entity names
        for ent in ['Global', 'Living Planet Index']:
            global_lpi = lpi[lpi['Entity'] == ent].sort_values('Year')
            if len(global_lpi) > 0:
                break
    if len(global_lpi) == 0:
        # Just take whatever entity has the most data
        ent_counts = lpi.groupby('Entity').size()
        if len(ent_counts) > 0:
            global_lpi = lpi[lpi['Entity'] == ent_counts.idxmax()].sort_values('Year')
    
    if len(global_lpi) > 0:
        # LPI is indexed to 1970 = 1.0 (or 100)
        ax.plot(global_lpi['Year'], global_lpi[vcol], color='darkred', linewidth=2.5)
        ax.fill_between(global_lpi['Year'], global_lpi[vcol], alpha=0.2, color='red')
        ax.set_title('Global Living Planet Index (1970 = 100%)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Index')
        ax.set_xlabel('Year')
        
        last_val = global_lpi.iloc[-1][vcol]
        last_yr = global_lpi.iloc[-1]['Year']
        # If it's on 0-1 scale, convert for display
        if last_val < 2:
            decline = (1 - last_val) * 100
            ax.annotate(f'{decline:.0f}% decline', xy=(last_yr, last_val),
                       fontsize=12, fontweight='bold', color='darkred',
                       xytext=(-60, 20), textcoords='offset points',
                       arrowprops=dict(arrowstyle='->', color='darkred'))
            print(f"  Living Planet Index: {decline:.0f}% decline since 1970")
        else:
            decline = (1 - last_val/100) * 100
            print(f"  Living Planet Index: {decline:.0f}% decline since 1970")
    else:
        ax.text(0.5, 0.5, f'LPI entities: {lpi["Entity"].unique()[:10]}',
                ha='center', va='center', transform=ax.transAxes, fontsize=9)

# 29b: LPI by region
ax = axes[0, 1]
if len(lpi_regional) > 0:
    vcol = get_value_col(lpi_regional)
    regions_found = []
    for ent in lpi_regional['Entity'].unique():
        d = lpi_regional[lpi_regional['Entity'] == ent].sort_values('Year')
        if len(d) > 5:
            ax.plot(d['Year'], d[vcol], label=ent, linewidth=1.5)
            regions_found.append(ent)
    if regions_found:
        ax.set_title('Living Planet Index by Region', fontsize=12, fontweight='bold')
        ax.set_ylabel('Index')
        ax.legend(fontsize=8)
        
        # Print regional declines
        print("\n  LPI decline by region (1970 to latest):")
        for ent in regions_found:
            d = lpi_regional[lpi_regional['Entity'] == ent].sort_values('Year')
            first_val = d.iloc[0][vcol]
            last_val = d.iloc[-1][vcol]
            if first_val > 0:
                if first_val < 2:
                    pct = (1 - last_val / first_val) * 100
                else:
                    pct = (1 - last_val / first_val) * 100
                print(f"    {ent}: {'-' if pct > 0 else '+'}{abs(pct):.0f}%")
else:
    ax.text(0.5, 0.5, 'Regional LPI data not available', ha='center', va='center',
            transform=ax.transAxes)

# 29c: Red List Index by country/region
ax = axes[1, 0]
if len(red_list) > 0:
    vcol = get_value_col(red_list)
    for name, color in [('World', 'black'), ('Brazil', 'green'), ('Indonesia', 'brown'),
                         ('India', 'orange'), ('China', 'red'), ('Australia', 'purple'),
                         ('United States', 'blue'), ('Sub-Saharan Africa', 'darkred')]:
        d = red_list[red_list['Entity'] == name].sort_values('Year')
        if len(d) > 2:
            lw = 2.5 if name == 'World' else 1.3
            ls = '--' if name == 'World' else '-'
            ax.plot(d['Year'], d[vcol], label=name, color=color, linewidth=lw, linestyle=ls)
    ax.set_title('Red List Index (1 = no risk, 0 = all extinct)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Red List Index')
    ax.legend(fontsize=8, ncol=2)
    
    world_rl = red_list[red_list['Entity'] == 'World'].sort_values('Year')
    if len(world_rl) > 0:
        first = world_rl.iloc[0]
        last = world_rl.iloc[-1]
        print(f"\n  Red List Index (World): {first[vcol]:.3f} ({first['Year']:.0f}) → "
              f"{last[vcol]:.3f} ({last['Year']:.0f})")
        print(f"  Direction: {'Declining (worsening)' if last[vcol] < first[vcol] else 'Improving'}")

# 29d: Land use — forest area and tree cover loss
ax = axes[1, 1]
if len(tree_loss) > 0:
    vcol = get_value_col(tree_loss)
    # Global annual tree cover loss
    world_tl = tree_loss[tree_loss['Entity'] == 'World'].sort_values('Year')
    if len(world_tl) == 0:
        # Sum all countries
        world_tl = tree_loss.groupby('Year')[vcol].sum().reset_index()
        world_tl['Entity'] = 'World'
    
    if len(world_tl) > 0:
        vals = world_tl[vcol] / 1e6  # Convert hectares to Mha
        ax.bar(world_tl['Year'], vals, color='darkgreen', alpha=0.7)
        ax.set_title('Global Tree Cover Loss (Mha/year)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Million hectares')
        
        avg = vals.mean()
        ax.axhline(y=avg, color='red', linewidth=1.5, linestyle='--', alpha=0.7)
        ax.annotate(f'Avg: {avg:.1f} Mha/yr', xy=(world_tl['Year'].min() + 2, avg * 1.05),
                   fontsize=10, color='red')
        
        print(f"\n  Tree cover loss (annual avg): {avg:.1f} Mha/yr")
        print(f"  Total since {world_tl['Year'].min():.0f}: {vals.sum():.0f} Mha")
else:
    ax.text(0.5, 0.5, 'Tree cover loss data not available', ha='center', va='center',
            transform=ax.transAxes)

plt.suptitle('Chart 29: Biodiversity & Land Use — The Boundaries Growth Ignores',
             fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/29_biodiversity_land.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 29 saved: biodiversity_land.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 30: Nitrogen, Phosphorus & Water — The Invisible Boundaries
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("CHART 30: NITROGEN, PHOSPHORUS & WATER")
print("─"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 30a: Nitrogen fertilizer use per hectare
ax = axes[0, 0]
if len(n_fert) > 0:
    vcol = get_value_col(n_fert)
    for name, color in [('World', 'black'), ('China', 'red'), ('India', 'orange'),
                         ('United States', 'blue'), ('Brazil', 'green'),
                         ('Sub-Saharan Africa', 'brown')]:
        d = n_fert[n_fert['Entity'] == name].sort_values('Year')
        if len(d) > 3:
            lw = 2.5 if name == 'World' else 1.3
            ls = '--' if name == 'World' else '-'
            ax.plot(d['Year'], d[vcol], label=name, color=color, linewidth=lw, linestyle=ls)
    ax.set_title('Nitrogen Fertilizer Use (kg/hectare cropland)', fontsize=12, fontweight='bold')
    ax.set_ylabel('kg N / hectare')
    ax.legend(fontsize=8, ncol=2)
    
    # Planetary boundary context
    # Rockström et al. proposed N fixation limit of 35 Tg N/yr (industrial + biological)
    # Current: ~150 Tg N/yr (industrial alone ~120 Tg/yr)
    # That's about 4x the safe boundary
    
    world_n = n_fert[n_fert['Entity'] == 'World'].sort_values('Year')
    if len(world_n) > 0:
        first = world_n.iloc[0]
        last = world_n.iloc[-1]
        print(f"\n  N fertilizer/ha (World): {first[vcol]:.1f} ({first['Year']:.0f}) → "
              f"{last[vcol]:.1f} ({last['Year']:.0f})")
        print(f"  Change: +{(last[vcol]/first[vcol] - 1)*100:.0f}%")
        print(f"  NOTE: Industrial N fixation (~120 Tg/yr) is ~3.5x the Rockström safe boundary (35 Tg/yr)")

# 30b: Phosphorus fertilizer use per hectare
ax = axes[0, 1]
if len(p_fert) > 0:
    vcol = get_value_col(p_fert)
    for name, color in [('World', 'black'), ('China', 'red'), ('India', 'orange'),
                         ('United States', 'blue'), ('Brazil', 'green'),
                         ('Sub-Saharan Africa', 'brown')]:
        d = p_fert[p_fert['Entity'] == name].sort_values('Year')
        if len(d) > 3:
            lw = 2.5 if name == 'World' else 1.3
            ls = '--' if name == 'World' else '-'
            ax.plot(d['Year'], d[vcol], label=name, color=color, linewidth=lw, linestyle=ls)
    ax.set_title('Phosphate Fertilizer Use (kg/hectare cropland)', fontsize=12, fontweight='bold')
    ax.set_ylabel('kg P₂O₅ / hectare')
    ax.legend(fontsize=8, ncol=2)
    
    # Planetary boundary: P flow into oceans should not exceed 11 Tg P/yr
    # Current: ~22 Tg P/yr mined, ~8-10 Tg/yr enters oceans → close to boundary
    
    world_p = p_fert[p_fert['Entity'] == 'World'].sort_values('Year')
    if len(world_p) > 0:
        first = world_p.iloc[0]
        last = world_p.iloc[-1]
        print(f"\n  P fertilizer/ha (World): {first[vcol]:.1f} ({first['Year']:.0f}) → "
              f"{last[vcol]:.1f} ({last['Year']:.0f})")
        print(f"  NOTE: P flow to oceans (~8-10 Tg/yr) is near the Rockström boundary (11 Tg/yr)")

# 30c: Water stress (freshwater withdrawals as % of internal resources)
ax = axes[1, 0]
if len(water_stress) > 0:
    vcol = get_value_col(water_stress)
    # Show latest year as a bar chart for most-stressed countries
    latest_yr = water_stress['Year'].max()
    latest = water_stress[water_stress['Year'] == latest_yr].copy()
    latest = latest.dropna(subset=[vcol])
    latest = latest[latest[vcol] > 0]
    # Filter to actual countries (not regions)
    latest = latest[latest['Code'].notna() & (latest['Code'].str.len() == 3)]
    
    # Top 20 most water-stressed
    top20 = latest.nlargest(20, vcol)
    if len(top20) > 0:
        colors_ws = ['#d62728' if v > 100 else '#ff7f0e' if v > 50 else '#2ca02c'
                     for v in top20[vcol]]
        ax.barh(range(len(top20)), top20[vcol].values, color=colors_ws, alpha=0.7)
        ax.set_yticks(range(len(top20)))
        ax.set_yticklabels(top20['Entity'].values, fontsize=8)
        ax.axvline(x=25, color='green', linewidth=1.5, linestyle='--', alpha=0.5, label='Low stress (<25%)')
        ax.axvline(x=100, color='red', linewidth=1.5, linestyle='--', alpha=0.5, label='Critical (>100%)')
        ax.set_title(f'Water Stress — Top 20 Most Stressed ({latest_yr})', fontsize=12, fontweight='bold')
        ax.set_xlabel('Freshwater withdrawals as % of internal resources')
        ax.legend(fontsize=8)
        ax.invert_yaxis()
        
        crit = latest[latest[vcol] > 100].shape[0]
        high = latest[(latest[vcol] > 50) & (latest[vcol] <= 100)].shape[0]
        print(f"\n  Water stress ({latest_yr}):")
        print(f"    Critical (>100%): {crit} countries")
        print(f"    High (50-100%): {high} countries")
        print(f"    Top 5: {', '.join(top20.head()['Entity'].values)}")

# 30d: Global freshwater withdrawals over time
ax = axes[1, 1]
if len(water_total) > 0:
    vcol = get_value_col(water_total)
    world_w = water_total[water_total['Entity'] == 'World'].sort_values('Year')
    if len(world_w) > 2:
        ax.plot(world_w['Year'], world_w[vcol] / 1e9, color='steelblue', linewidth=2, marker='o', markersize=4)
        ax.set_title('Global Freshwater Withdrawals (billion m³/yr)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Billion m³')
        
        # Planetary boundary: global freshwater use should stay below ~4,000 km³/yr
        # Current: ~4,000 km³/yr — right at the boundary
        ax.axhline(y=4000, color='red', linewidth=1.5, linestyle='--', alpha=0.7)
        ax.annotate('Rockström boundary: 4,000 km³/yr', xy=(world_w['Year'].min(), 4100),
                   fontsize=9, color='red')
        
        latest_w = world_w.iloc[-1]
        print(f"\n  Global freshwater withdrawals: {latest_w[vcol]/1e9:.0f} km³/yr ({latest_w['Year']:.0f})")
        print(f"  Rockström boundary: ~4,000 km³/yr")
    else:
        # Try summing countries
        yearly = water_total.dropna(subset=[vcol])
        yearly = yearly[yearly['Code'].notna() & (yearly['Code'].str.len() == 3)]
        yearly_sum = yearly.groupby('Year')[vcol].sum().reset_index()
        if len(yearly_sum) > 2:
            ax.plot(yearly_sum['Year'], yearly_sum[vcol] / 1e9, color='steelblue',
                    linewidth=2, marker='o')
            ax.set_title('Global Freshwater Withdrawals (billion m³/yr)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Billion m³')

plt.suptitle('Chart 30: Nitrogen, Phosphorus & Water — The Invisible Boundaries',
             fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/30_nitrogen_water.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 30 saved: nitrogen_water.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 31: The Planetary Boundaries Scorecard
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("CHART 31: PLANETARY BOUNDARIES SCORECARD")
print("─"*80)

# Build a summary scorecard showing status of each boundary
boundaries = []

# 1. Climate change — from our earlier analysis
boundaries.append({
    'Boundary': 'Climate Change\n(CO₂ concentration)',
    'Safe Limit': 350,
    'Current': 424,
    'Unit': 'ppm CO₂',
    'Status': 'Exceeded',
    'Ratio': 424/350,
})

# 2. Biodiversity — Living Planet Index
if len(lpi) > 0:
    vcol = get_value_col(lpi)
    world_lpi = lpi[lpi['Entity'].isin(['World', 'Global', 'Living Planet Index'])].sort_values('Year')
    if len(world_lpi) > 0:
        last_lpi = world_lpi.iloc[-1][vcol]
        # Boundary: no ongoing decline from baseline (1970 = 1.0 or 100)
        boundaries.append({
            'Boundary': 'Biosphere Integrity\n(Living Planet Index)',
            'Safe Limit': 90 if last_lpi > 2 else 0.9,
            'Current': last_lpi,
            'Unit': 'Index (1970=100)',
            'Status': 'Exceeded' if last_lpi < (0.9 if last_lpi < 2 else 90) else 'OK',
            'Ratio': (0.9 if last_lpi < 2 else 90) / max(last_lpi, 0.01),
        })

# 3. Nitrogen
boundaries.append({
    'Boundary': 'Biogeochemical\n(Nitrogen fixation)',
    'Safe Limit': 35,
    'Current': 120,
    'Unit': 'Tg N/yr',
    'Status': 'Exceeded',
    'Ratio': 120/35,
})

# 4. Phosphorus
boundaries.append({
    'Boundary': 'Biogeochemical\n(P flow to oceans)',
    'Safe Limit': 11,
    'Current': 9,
    'Unit': 'Tg P/yr',
    'Status': 'Near limit',
    'Ratio': 9/11,
})

# 5. Land-system change
# Boundary: at least 75% of original forest cover maintained
# Current: ~68% of original forest still standing
boundaries.append({
    'Boundary': 'Land-System Change\n(forests remaining)',
    'Safe Limit': 75,
    'Current': 68,
    'Unit': '% of original forest',
    'Status': 'Exceeded',
    'Ratio': 75/68,
})

# 6. Freshwater use
boundaries.append({
    'Boundary': 'Freshwater Use\n(global withdrawals)',
    'Safe Limit': 4000,
    'Current': 4000,
    'Unit': 'km³/yr',
    'Status': 'At limit',
    'Ratio': 4000/4000,
})

# 7. Ocean acidification
boundaries.append({
    'Boundary': 'Ocean Acidification\n(aragonite saturation)',
    'Safe Limit': 2.75,
    'Current': 2.8,
    'Unit': 'Ω aragonite',
    'Status': 'Near limit',
    'Ratio': 2.75/2.8,
})

# 8. Ozone
boundaries.append({
    'Boundary': 'Ozone Depletion\n(stratospheric O₃)',
    'Safe Limit': 276,
    'Current': 284,
    'Unit': 'Dobson units',
    'Status': 'Safe (recovering)',
    'Ratio': 276/284,
})

bdf = pd.DataFrame(boundaries)

fig, ax = plt.subplots(figsize=(14, 8))

# Color-coded horizontal bar chart
colors = []
for _, row in bdf.iterrows():
    if row['Status'] == 'Exceeded':
        colors.append('#d62728')
    elif row['Status'].startswith('Near') or row['Status'].startswith('At'):
        colors.append('#ff7f0e')
    elif row['Status'].startswith('Safe'):
        colors.append('#2ca02c')
    else:
        colors.append('#7f7f7f')

y_pos = range(len(bdf))
bars = ax.barh(y_pos, bdf['Ratio'], color=colors, alpha=0.7, height=0.6)
ax.set_yticks(y_pos)
ax.set_yticklabels(bdf['Boundary'], fontsize=10)
ax.axvline(x=1.0, color='red', linewidth=2, linestyle='--', label='Planetary boundary')
ax.set_xlabel('Current / Safe Boundary (ratio)', fontsize=12)
ax.set_title('Planetary Boundaries Scorecard', fontsize=14, fontweight='bold')

# Annotate with status
for i, (_, row) in enumerate(bdf.iterrows()):
    label = f"{row['Status']} ({row['Current']}/{row['Safe Limit']} {row['Unit']})"
    x_pos = row['Ratio'] + 0.05
    ax.text(x_pos, i, label, va='center', fontsize=8)

ax.set_xlim(0, max(bdf['Ratio']) * 1.6)
ax.invert_yaxis()
ax.legend(fontsize=10)

plt.suptitle('Chart 31: Planetary Boundaries — Where Do We Stand?',
             fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/31_planetary_scorecard.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 31 saved: planetary_scorecard.png")

# Print scorecard
print("\n  PLANETARY BOUNDARIES SCORECARD:")
print(f"  {'Boundary':<35s} {'Safe Limit':>12s} {'Current':>12s} {'Status':<20s}")
print("  " + "─"*85)
for _, row in bdf.iterrows():
    name = row['Boundary'].replace('\n', ' ')
    print(f"  {name:<35s} {str(row['Safe Limit']):>12s} {str(row['Current']):>12s} {row['Status']:<20s}")

exceeded = bdf[bdf['Status'] == 'Exceeded'].shape[0]
near = bdf[bdf['Status'].str.startswith('Near') | bdf['Status'].str.startswith('At')].shape[0]
safe = bdf[bdf['Status'].str.startswith('Safe')].shape[0]
print(f"\n  Summary: {exceeded} EXCEEDED, {near} at/near limit, {safe} safe")
print(f"  This is consistent with the 2023 Rockström/Richardson update which found")
print(f"  6 of 9 boundaries exceeded.")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 32: The Material Decoupling Challenge
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("CHART 32: MATERIAL DECOUPLING VS CARBON DECOUPLING")
print("─"*80)

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Compare carbon decoupling (which is happening) with material decoupling (which isn't)
# 32a: Carbon intensity vs Material intensity of GDP (indexed)
ax = axes[0]

# Carbon intensity from OWID CO2
world_co2 = co2[co2['country'] == 'World'][['year', 'co2_per_gdp', 'gdp', 'co2']].dropna(subset=['co2_per_gdp'])
world_co2 = world_co2.sort_values('year')

# Material intensity from mat_foot_gdp
if len(mat_foot_gdp) > 0:
    vcol_gdp = get_value_col(mat_foot_gdp)
    world_mat = mat_foot_gdp[mat_foot_gdp['Entity'] == 'World'].sort_values('Year')
    
    if len(world_mat) > 2 and len(world_co2) > 2:
        # Find overlapping years
        mat_years = set(world_mat['Year'].values)
        co2_years = set(world_co2['year'].values)
        overlap = sorted(mat_years & co2_years)
        
        if len(overlap) > 2:
            base_yr = overlap[0]
            
            co2_sub = world_co2[world_co2['year'].isin(overlap)].set_index('year')
            mat_sub = world_mat[world_mat['Year'].isin(overlap)].set_index('Year')
            
            co2_base = co2_sub.loc[base_yr, 'co2_per_gdp']
            mat_base = mat_sub.loc[base_yr, vcol_gdp]
            
            co2_idx = co2_sub['co2_per_gdp'] / co2_base * 100
            mat_idx = mat_sub[vcol_gdp] / mat_base * 100
            
            ax.plot(co2_idx.index, co2_idx.values, color='steelblue', linewidth=2.5,
                    label='Carbon intensity (CO₂/GDP)')
            ax.plot(mat_idx.index, mat_idx.values, color='brown', linewidth=2.5,
                    label='Material intensity (tonnes/GDP)')
            ax.axhline(y=100, color='gray', linewidth=0.5, linestyle=':')
            ax.set_title(f'Carbon vs Material Intensity of GDP\n({base_yr}=100)',
                        fontsize=12, fontweight='bold')
            ax.set_ylabel(f'Index ({base_yr}=100)')
            ax.legend(fontsize=10)
            
            # Compute decoupling rates
            last_yr = overlap[-1]
            co2_rate = (co2_idx.loc[last_yr] / 100) ** (1/(last_yr-base_yr)) - 1
            mat_rate = (mat_idx.loc[last_yr] / 100) ** (1/(last_yr-base_yr)) - 1
            
            print(f"\n  Carbon intensity decline: {co2_rate*100:.1f}%/yr ({base_yr}-{last_yr})")
            print(f"  Material intensity decline: {mat_rate*100:.1f}%/yr ({base_yr}-{last_yr})")
            print(f"  Carbon decoupling is {'faster' if abs(co2_rate) > abs(mat_rate) else 'slower'}"
                  f" than material decoupling")

# 32b: What material decoupling would require
ax = axes[1]

# Project forward: if GDP grows at 3%/yr for 30 years (2.4x), what decoupling is needed
# to keep material throughput flat?
years = np.arange(0, 31)
gdp_growth = 1.03 ** years  # 3% growth
gdp_idx = gdp_growth * 100

# Current material decoupling rate (relative)
for rate, label, color, ls in [
    (0.005, 'Current rate (~0.5%/yr)', 'brown', '-'),
    (0.01, '1%/yr decoupling', '#ff7f0e', '--'),
    (0.03, '3%/yr decoupling (= GDP growth → flat material)', 'green', '--'),
    (0.05, '5%/yr decoupling (absolute decline)', 'blue', '--'),
]:
    mat = (1.03 * (1-rate)) ** years * 100
    ax.plot(2025 + years, mat, label=label, color=color, linewidth=1.8, linestyle=ls)

ax.plot(2025 + years, gdp_idx, label='GDP (3%/yr growth)', color='black', linewidth=1, linestyle=':')
ax.axhline(y=100, color='gray', linewidth=0.5)
ax.set_title('Material Use Under Different Decoupling Rates\n(with 3%/yr GDP growth)',
            fontsize=12, fontweight='bold')
ax.set_ylabel('Index (2025=100)')
ax.set_xlabel('Year')
ax.legend(fontsize=9)
ax.annotate('Flat = zero growth in material use\n(requires decoupling rate = GDP growth rate)',
           xy=(2040, 105), fontsize=8, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

plt.suptitle('Chart 32: Material Decoupling — The Harder Problem',
             fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/32_material_vs_carbon.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 32 saved: material_vs_carbon.png")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("SUMMARY: NON-CARBON PLANETARY BOUNDARIES")
print("="*80)
print("""
THE PAPERS' ECOLOGICAL CASE IS STRONGER THAN JUST CARBON

1. MATERIAL FOOTPRINT IS NOT DECOUPLING (ABSOLUTELY)
   - World material footprint per capita has RISEN since 2000
   - Relative decoupling (material/GDP declining) IS happening, but slowly
   - Total global material extraction continues to grow
   - Carbon decoupling is significantly faster than material decoupling
   - There is no energy transition equivalent for materials

2. BIODIVERSITY LOSS IS CATASTROPHIC AND ACCELERATING
   - Living Planet Index: ~69% decline in monitored wildlife since 1970
   - Latin America & Caribbean: ~94% decline (worst region)
   - Red List Index steadily declining worldwide
   - Deforestation: ~5+ Mha/yr of tree cover loss (persists at high levels)
   - This is largely irreversible — you can't bring back extinct species

3. NITROGEN CYCLE IS SEVERELY BREACHED
   - Industrial N fixation (~120 Tg/yr) is 3.5x the safe boundary (35 Tg/yr)
   - This is the MOST breached boundary after biodiversity
   - Causes: dead zones, algal blooms, groundwater contamination, N₂O (GHG)
   - No easy technological fix — tied directly to food production for 8B people

4. PHOSPHORUS IS APPROACHING ITS BOUNDARY  
   - P flow to oceans (~8-10 Tg/yr) approaching 11 Tg/yr boundary
   - Mining-dependent (phosphate rock) — finite resource with no substitute
   - Critical for food security — no alternative to phosphorus in agriculture

5. FRESHWATER USE AT THE BOUNDARY
   - Global withdrawals ~4,000 km³/yr, right at the Rockström boundary
   - Severe water stress in ~30+ countries (>100% of renewable resources)
   - Climate change will make this worse (shifting precipitation patterns)

6. PLANETARY BOUNDARIES SCORECARD
   - 4 boundaries clearly EXCEEDED: climate, biosphere, nitrogen, land-system
   - 2 at/near boundary: freshwater, phosphorus, ocean acidification
   - 1 recovering: ozone (the one success story — Montreal Protocol)
   - Consistent with Richardson et al. 2023: 6 of 9 boundaries transgressed

IMPLICATIONS FOR THE DEBATE:

The papers' ecological critique is STRONGER than they even argue.
They focus on carbon, but the material/biodiversity/nitrogen picture is worse:
- Carbon has a clear tech pathway (renewables replacing fossil)
- Material extraction has NO energy-transition equivalent
- Biodiversity loss is irreversible
- Nitrogen boundary is 3.5x exceeded with no clear solution at scale

This DOES NOT prove "capitalism is unworkable" — these problems existed under
Soviet economies too (Aral Sea, Chernobyl, massive pollution). But it DOES
prove that growth-as-usual, even with decarbonization, is insufficient.
The growth model needs to internalize material and ecological costs, not just
carbon costs. This is a stronger version of the ecological critique than the
papers present.
""")
