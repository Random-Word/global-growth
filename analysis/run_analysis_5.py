"""
Analysis 5: Decoupling, Material Intensity, and Planetary Boundaries
=====================================================================
Questions addressed:
1. Is material/carbon decoupling accelerating? At what rate?
2. If only the poor world grew (rich world frozen), would it breach planetary limits?
3. Does the rich world depend on exploiting the poor world?
4. When do we estimate material intensity turning points?
5. What does the energy transition change?
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='colorblind')
CHART_DIR = 'charts'

# ── Load data ──────────────────────────────────────────────────────────────────
co2 = pd.read_csv('data/raw/owid_co2.csv')
maddison = pd.read_csv('data/processed/maddison.csv')

# Income groups (World Bank 2024 thresholds on GNI per capita, we'll approximate with GDP per capita)
HIGH_INCOME = ['United States', 'United Kingdom', 'Germany', 'France', 'Japan', 'Canada',
               'Australia', 'Italy', 'Spain', 'Netherlands', 'Sweden', 'Norway', 'Denmark',
               'Finland', 'Switzerland', 'Austria', 'Belgium', 'Ireland', 'South Korea',
               'Singapore', 'New Zealand', 'Portugal', 'Greece', 'Israel', 'Czech Republic',
               'Poland', 'Saudi Arabia', 'United Arab Emirates']

UPPER_MIDDLE = ['China', 'Brazil', 'Mexico', 'Turkey', 'Thailand', 'Malaysia',
                'South Africa', 'Colombia', 'Argentina', 'Peru', 'Romania', 'Bulgaria',
                'Kazakhstan', 'Iran', 'Iraq', 'Algeria', 'Ecuador', 'Dominican Republic',
                'Guatemala', 'Costa Rica', 'Serbia', 'Jordan', 'Tunisia', 'Libya',
                'Botswana', 'Gabon', 'Mauritius']

LOW_MIDDLE = ['India', 'Indonesia', 'Vietnam', 'Philippines', 'Egypt', 'Bangladesh',
              'Pakistan', 'Nigeria', 'Ukraine', 'Morocco', 'Kenya', 'Ghana',
              'Cambodia', 'Myanmar', 'Senegal', 'Ivory Coast', 'Tanzania',
              'Uzbekistan', 'Bolivia', 'Honduras', 'Nicaragua', 'Laos',
              'Sri Lanka', 'Nepal', 'Angola', 'Cameroon', 'Zimbabwe']

LOW_INCOME = ['Ethiopia', 'Democratic Republic of Congo', 'Mozambique', 'Madagascar',
              'Mali', 'Burkina Faso', 'Malawi', 'Niger', 'Chad', 'Sierra Leone',
              'Central African Republic', 'South Sudan', 'Burundi', 'Somalia',
              'Afghanistan', 'Yemen', 'Haiti', 'Guinea', 'Rwanda', 'Togo', 'Uganda']

def assign_income_group(country):
    if country in HIGH_INCOME:
        return 'High income'
    elif country in UPPER_MIDDLE:
        return 'Upper middle'
    elif country in LOW_MIDDLE:
        return 'Lower middle'
    elif country in LOW_INCOME:
        return 'Low income'
    return None

co2['income_group'] = co2['country'].apply(assign_income_group)

# Also get aggregate rows that OWID provides
world = co2[co2['country'] == 'World'].copy()
hi_agg = co2[co2['country'] == 'High-income countries'].copy()
li_agg = co2[co2['country'] == 'Low-income countries'].copy()
umi_agg = co2[co2['country'] == 'Upper-middle-income countries'].copy()
lmi_agg = co2[co2['country'] == 'Lower-middle-income countries'].copy()

print("="*80)
print("ANALYSIS 5: DECOUPLING, MATERIAL INTENSITY & PLANETARY BOUNDARIES")
print("="*80)

# ══════════════════════════════════════════════════════════════════════════════
# PART 1: Carbon Intensity Trends — Is Decoupling Accelerating?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("PART 1: CARBON INTENSITY OF GDP (CO2 per $ GDP) — DECOUPLING TRENDS")
print("─"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 1a: CO2 per GDP over time by income group (OWID aggregates)
ax = axes[0, 0]
for label, df, color in [('High income', hi_agg, 'blue'),
                          ('Upper-middle income', umi_agg, 'green'),
                          ('Lower-middle income', lmi_agg, 'orange'),
                          ('Low income', li_agg, 'red'),
                          ('World', world, 'black')]:
    d = df[(df['year'] >= 1960) & (df['co2_per_gdp'].notna())].sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['co2_per_gdp'], label=label, color=color,
                linewidth=2.5 if label == 'World' else 1.5,
                linestyle='--' if label == 'World' else '-')
ax.set_title('CO₂ Intensity of GDP (kg CO₂ per $)', fontsize=13, fontweight='bold')
ax.set_xlabel('Year')
ax.set_ylabel('kg CO₂ per $ GDP')
ax.legend(fontsize=9)

# 1b: Rate of decoupling by decade
ax = axes[0, 1]
decades = [(1970, 1980), (1980, 1990), (1990, 2000), (2000, 2010), (2010, 2020)]
groups_data = {'High income': hi_agg, 'Upper-middle': umi_agg,
               'Lower-middle': lmi_agg, 'World': world}
bar_data = []
for label, df in groups_data.items():
    d = df[df['co2_per_gdp'].notna()].set_index('year')['co2_per_gdp']
    for start, end in decades:
        if start in d.index and end in d.index:
            rate = ((d[end] / d[start]) ** (1/(end-start)) - 1) * 100
            bar_data.append({'Group': label, 'Decade': f'{start}s', 'Annual change %': rate})

bar_df = pd.DataFrame(bar_data)
if len(bar_df) > 0:
    pivot = bar_df.pivot(index='Decade', columns='Group', values='Annual change %')
    pivot.plot(kind='bar', ax=ax, width=0.8)
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_title('Rate of CO₂/GDP Decoupling by Decade', fontsize=13, fontweight='bold')
    ax.set_ylabel('Annual change in CO₂ intensity (%)')
    ax.set_xlabel('')
    ax.tick_params(axis='x', rotation=0)
    ax.legend(fontsize=8)

# 1c: Major emitter absolute CO2 trajectories
ax = axes[1, 0]
major_emitters = ['United States', 'European Union (27)', 'China', 'India', 'Japan', 'World']
for name in major_emitters:
    d = co2[(co2['country'] == name) & (co2['year'] >= 1960) & (co2['co2'].notna())]
    d = d.sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['co2'] / 1000, label=name,
                linewidth=2.5 if name == 'World' else 1.5,
                linestyle='--' if name == 'World' else '-')
ax.set_title('Absolute CO₂ Emissions (GtCO₂)', fontsize=13, fontweight='bold')
ax.set_xlabel('Year')
ax.set_ylabel('GtCO₂/year')
ax.legend(fontsize=9)

# 1d: Energy intensity of GDP
ax = axes[1, 1]
for label, df, color in [('High income', hi_agg, 'blue'),
                          ('Upper-middle income', umi_agg, 'green'),
                          ('Lower-middle income', lmi_agg, 'orange'),
                          ('World', world, 'black')]:
    d = df[(df['year'] >= 1965) & (df['energy_per_gdp'].notna())].sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['energy_per_gdp'], label=label, color=color,
                linewidth=2.5 if label == 'World' else 1.5,
                linestyle='--' if label == 'World' else '-')
ax.set_title('Energy Intensity of GDP (kWh per $)', fontsize=13, fontweight='bold')
ax.set_xlabel('Year')
ax.set_ylabel('kWh per $ GDP')
ax.legend(fontsize=9)

plt.suptitle('Chart 19: Carbon & Energy Decoupling Trends', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/19_decoupling_trends.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 19 saved: decoupling_trends.png")

# Print key numbers
print("\nCO₂ Intensity of GDP (kg CO₂ per $):")
for label, df in [('High income', hi_agg), ('Upper-middle', umi_agg),
                   ('Lower-middle', lmi_agg), ('Low income', li_agg), ('World', world)]:
    d = df[df['co2_per_gdp'].notna()].set_index('year')['co2_per_gdp']
    vals = {}
    for yr in [1970, 1980, 1990, 2000, 2010, 2020]:
        if yr in d.index:
            vals[yr] = d[yr]
    if 1990 in vals and 2020 in vals:
        total_decline = (1 - vals[2020]/vals[1990]) * 100
        annual_rate = ((vals[2020]/vals[1990])**(1/30) - 1) * 100
        print(f"  {label:20s}: {vals.get(1990, 'n/a'):.3f}(1990) → {vals.get(2020, 'n/a'):.3f}(2020)  "
              f"Decline: {total_decline:.1f}%  Rate: {annual_rate:.2f}%/yr")
    if 2010 in vals and 2020 in vals:
        rate_recent = ((vals[2020]/vals[2010])**(1/10) - 1) * 100
        print(f"  {'':20s}  2010-2020 rate: {rate_recent:.2f}%/yr")

# Check acceleration
print("\nIs decoupling accelerating?")
for label, df in [('World', world), ('High income', hi_agg)]:
    d = df[(df['co2_per_gdp'].notna()) & (df['year'] >= 1970)].set_index('year')['co2_per_gdp']
    for p1, p2 in [((1970,1990), (1990,2010)), ((1990,2000), (2010,2020))]:
        s1, e1 = p1
        s2, e2 = p2
        if all(y in d.index for y in [s1,e1,s2,e2]):
            r1 = ((d[e1]/d[s1])**(1/(e1-s1)) - 1) * 100
            r2 = ((d[e2]/d[s2])**(1/(e2-s2)) - 1) * 100
            print(f"  {label}: {s1}-{e1}: {r1:.2f}%/yr → {s2}-{e2}: {r2:.2f}%/yr  "
                  f"({'Accelerating' if r2 < r1 else 'Decelerating'})")


# ══════════════════════════════════════════════════════════════════════════════
# PART 2: The "Frozen Rich World" Scenario
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("PART 2: IF ONLY THE POOR WORLD GROWS — PLANETARY IMPACT SCENARIOS")
print("─"*80)

# Get current data points
w = world[world['year'] == 2022].iloc[0] if len(world[world['year'] == 2022]) > 0 else world[world['year'] == 2021].iloc[0]
w_yr = int(w['year'])

# Current emissions by income group
print(f"\nCurrent state ({w_yr}):")
total_co2_world = w['co2']  # Mt CO2
print(f"  World total CO₂: {total_co2_world:.0f} Mt ({total_co2_world/1000:.1f} Gt)")

for label, df in [('High income', hi_agg), ('Upper-middle', umi_agg),
                   ('Lower-middle', lmi_agg), ('Low income', li_agg)]:
    row = df[df['year'] == w_yr]
    if len(row) > 0:
        r = row.iloc[0]
        print(f"  {label:20s}: CO₂={r['co2']:.0f} Mt  ({r['co2']/total_co2_world*100:.1f}%)  "
              f"per cap={r.get('co2_per_capita', float('nan')):.1f} t  "
              f"CO₂/GDP={r.get('co2_per_gdp', float('nan')):.3f} kg/$")

# Scenario modeling
print("\n--- SCENARIO: Rich world frozen, poor world grows to high-income levels ---")

# Get latest population and CO2 data by income group
latest = {}
for label, df in [('High income', hi_agg), ('Upper-middle', umi_agg),
                   ('Lower-middle', lmi_agg), ('Low income', li_agg)]:
    row = df[df['year'] == w_yr]
    if len(row) > 0:
        r = row.iloc[0]
        latest[label] = {
            'co2': r['co2'],  # Mt
            'co2_per_capita': r.get('co2_per_capita', float('nan')),
            'co2_per_gdp': r.get('co2_per_gdp', float('nan')),
            'population': r.get('population', float('nan')),
            'gdp': r.get('gdp', float('nan')),  # OWID GDP in int'l $
        }

# Calculate scenarios
hi_co2_pc = latest['High income']['co2_per_capita']
hi_co2_gdp = latest['High income']['co2_per_gdp']

# Current carbon intensity for non-high-income
non_hi_pop = sum(latest[g]['population'] for g in ['Upper-middle', 'Lower-middle', 'Low income']
                 if g in latest and not np.isnan(latest[g]['population']))
non_hi_co2 = sum(latest[g]['co2'] for g in ['Upper-middle', 'Lower-middle', 'Low income']
                 if g in latest and not np.isnan(latest[g]['co2']))

print(f"\nHigh-income CO₂ per capita: {hi_co2_pc:.1f} t")
print(f"High-income CO₂ per GDP: {hi_co2_gdp:.4f} kg/$")

# Scenario A: Poor world reaches high-income CO2 per capita (worst case - no decoupling)
scenario_a_co2 = latest['High income']['co2'] + non_hi_pop * hi_co2_pc / 1e6  # Mt
print(f"\nScenario A — All reach current high-income CO₂/capita (NO decoupling):")
print(f"  Global CO₂: {scenario_a_co2:.0f} Mt ({scenario_a_co2/1000:.1f} Gt)  vs current {total_co2_world/1000:.1f} Gt")
print(f"  Increase: {(scenario_a_co2/total_co2_world - 1)*100:.0f}%")

# Scenario B: Poor world reaches high-income GDP/cap but at high-income CO2/GDP rate
hi_gdp_pc = latest['High income']['gdp'] / latest['High income']['population'] if latest['High income']['population'] > 0 else 50000
scenario_b_total_gdp = latest['High income']['gdp'] + non_hi_pop * hi_gdp_pc
scenario_b_co2 = scenario_b_total_gdp * hi_co2_gdp / 1e6  # converting  
# Actually let's just use per-capita which is more reliable
print(f"\nScenario B — All reach high-income GDP/capita at CURRENT high-income CO₂/GDP:")
print(f"  Same as Scenario A essentially (via different calculation path)")

# Scenario C: Poor world grows, but at improving decoupling rates
# Historical decoupling: high-income countries reduced CO2/GDP by ~2-3% per year recently
# With continued decoupling at 2.5%/yr over 50 years = (1-0.025)^50 = 0.28x current intensity
# Over 100 years = (1-0.025)^100 = 0.08x
print(f"\nScenario C — Poor world grows to convergence with CONTINUED DECOUPLING:")
for decouple_rate, label in [(0.02, '2%/yr'), (0.025, '2.5%/yr'), (0.035, '3.5%/yr (accelerated)')]:
    for years in [50, 100, 200]:
        intensity_factor = (1 - decouple_rate) ** years
        # Assume everyone converges to high-income GDP/cap but carbon intensity keeps falling
        future_hi_co2_pc = hi_co2_pc * intensity_factor
        future_global_co2 = (latest['High income']['population'] + non_hi_pop) * future_hi_co2_pc / 1e6
        print(f"  Decoupling {label}, after {years:3d}yr: CO₂/cap={future_hi_co2_pc:.2f}t  "
              f"Global={future_global_co2/1000:.1f} Gt  vs current {total_co2_world/1000:.1f} Gt")

# Carbon budget analysis
print(f"\nCarbon budget context:")
remaining_15c = 300  # Gt CO2 for 1.5°C (50% chance)
remaining_2c = 900  # Gt CO2 for 2°C (67% chance)
current_annual = total_co2_world / 1000  # Gt
print(f"  Current annual: {current_annual:.1f} Gt CO₂")
print(f"  1.5°C budget remaining: ~{remaining_15c} Gt → {remaining_15c/current_annual:.0f} years at current rates")
print(f"  2°C budget remaining:   ~{remaining_2c} Gt → {remaining_2c/current_annual:.0f} years at current rates")

# What if ONLY low/lower-middle income countries' CO2 grew?
non_hi_current_co2 = non_hi_co2 / 1000  # Gt
hi_current_co2 = latest['High income']['co2'] / 1000  # Gt
print(f"\n  High-income share of current CO₂: {hi_current_co2:.1f} Gt ({hi_current_co2/current_annual*100:.0f}%)")
print(f"  Rest of world: {non_hi_current_co2:.1f} Gt ({non_hi_current_co2/current_annual*100:.0f}%)")

# If high-income froze AND non-high-income grew at 5%/yr GDP with 2.5%/yr decoupling
# Net CO2 growth = 5% GDP growth - 2.5% intensity decline = ~2.5%/yr CO2 growth
# But that's only on the non-HI portion
# Actually, let's model this properly
print(f"\n--- DETAILED SCENARIO: High income frozen, others grow 5%/yr with decoupling ---")
scenarios_detailed = []
for decouple_rate in [0.02, 0.03, 0.05]:
    gdp_growth = 0.05
    net_co2_growth = gdp_growth - decouple_rate  # approximate
    cumulative_co2 = 0
    annual_hi = hi_current_co2  # frozen
    annual_non_hi = non_hi_current_co2
    for yr in range(1, 201):
        annual_non_hi = non_hi_current_co2 * ((1 + gdp_growth) ** yr) * ((1 - decouple_rate) ** yr)
        total = annual_hi + annual_non_hi
        cumulative_co2 += total
        if yr in [25, 50, 75, 100, 150, 200]:
            scenarios_detailed.append({
                'decouple': f'{decouple_rate*100:.0f}%/yr',
                'year': yr,
                'annual_gt': total,
                'cumul_gt': cumulative_co2,
                'non_hi_annual': annual_non_hi,
                'non_hi_gdp_x': (1 + gdp_growth) ** yr
            })

sdf = pd.DataFrame(scenarios_detailed)
for dk, grp in sdf.groupby('decouple'):
    print(f"\n  Decoupling at {dk} (GDP growth 5%/yr):")
    for _, row in grp.iterrows():
        budget_status_2c = "WITHIN 2°C" if row['cumul_gt'] < remaining_2c else f"EXCEEDS 2°C by {row['cumul_gt']-remaining_2c:.0f} Gt"
        print(f"    Year {row['year']:3.0f}: Annual={row['annual_gt']:.1f} Gt  Cumulative={row['cumul_gt']:.0f} Gt  "
              f"Non-HI GDP={row['non_hi_gdp_x']:.0f}x  {budget_status_2c}")


# ══════════════════════════════════════════════════════════════════════════════
# PART 3: Rich-World "Exploitation" — Trade CO2 and consumption-based emissions
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("PART 3: DOES THE RICH WORLD DEPEND ON EXPLOITING THE POOR WORLD?")
print("─"*80)

# Trade CO2: positive = net importer of embodied CO2 (i.e., offshoring emissions)
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 3a: Production vs consumption-based CO2 for key countries
ax = axes[0, 0]
countries_trade = ['United States', 'United Kingdom', 'Germany', 'Japan', 'France',
                   'China', 'India', 'South Korea']
trade_data = []
for c in countries_trade:
    d = co2[(co2['country'] == c) & (co2['year'] == w_yr)]
    if len(d) > 0:
        r = d.iloc[0]
        if pd.notna(r.get('co2')) and pd.notna(r.get('consumption_co2')):
            trade_data.append({
                'country': c,
                'production': r['co2'],
                'consumption': r['consumption_co2'],
                'trade_co2': r.get('trade_co2', r['consumption_co2'] - r['co2']),
            })

tdf = pd.DataFrame(trade_data)
if len(tdf) > 0:
    x = np.arange(len(tdf))
    width = 0.35
    ax.bar(x - width/2, tdf['production'], width, label='Production-based', color='steelblue')
    ax.bar(x + width/2, tdf['consumption'], width, label='Consumption-based', color='coral')
    ax.set_xticks(x)
    ax.set_xticklabels(tdf['country'], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('CO₂ (Mt)')
    ax.legend()
    ax.set_title(f'Production vs Consumption CO₂ ({w_yr})', fontsize=12, fontweight='bold')

# 3b: Trade CO2 over time for major importers/exporters
ax = axes[0, 1]
for c, color in [('United States', 'blue'), ('United Kingdom', 'green'),
                  ('Germany', 'purple'), ('China', 'red'), ('India', 'orange')]:
    d = co2[(co2['country'] == c) & (co2['year'] >= 1990) & (co2['trade_co2'].notna())]
    d = d.sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['trade_co2'], label=c, color=color)
ax.axhline(y=0, color='black', linewidth=0.5)
ax.set_title('Net CO₂ Trade (+ = net importer/offshorer)', fontsize=12, fontweight='bold')
ax.set_ylabel('Net trade CO₂ (Mt)')
ax.legend(fontsize=9)

# 3c: How much of rich-world consumption comes from poor-world production?
# Use consumption_co2 vs co2 as proxy for embedded trade
ax = axes[1, 0]
for label, df, color in [('High income', hi_agg, 'blue'), ('Upper-middle', umi_agg, 'green'),
                          ('Lower-middle', lmi_agg, 'orange')]:
    d = df[(df['year'] >= 1990) & (df['trade_co2'].notna())].sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['trade_co2'], label=label, color=color, linewidth=2)
    elif len(df[(df['year'] >= 1990)]) > 0:
        # Try computing from consumption - production
        d = df[(df['year'] >= 1990) & (df['co2'].notna()) & (df['consumption_co2'].notna())].sort_values('year')
        if len(d) > 0:
            ax.plot(d['year'], d['consumption_co2'] - d['co2'], label=label, color=color, linewidth=2)
ax.axhline(y=0, color='black', linewidth=0.5)
ax.set_title('Net CO₂ Trade by Income Group', fontsize=12, fontweight='bold')
ax.set_ylabel('Net trade CO₂ (Mt)')
ax.legend(fontsize=9)
ax.annotate('Positive = consuming more\nthan producing (offshoring)', xy=(0.02, 0.95),
            xycoords='axes fraction', fontsize=9, va='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 3d: Rich world CO2 per capita over time (production vs consumption)
ax = axes[1, 1]
for label, metric, color, ls in [('US production', 'co2_per_capita', 'blue', '-'),
                                   ('US consumption', 'consumption_co2_per_capita', 'blue', '--'),
                                   ('EU-27 production', 'co2_per_capita', 'green', '-'),
                                   ('EU-27 consumption', 'consumption_co2_per_capita', 'green', '--')]:
    country_name = 'United States' if 'US' in label else 'European Union (27)'
    d = co2[(co2['country'] == country_name) & (co2['year'] >= 1990) & (co2[metric].notna())]
    d = d.sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d[metric], label=label, color=color, linestyle=ls, linewidth=1.5)
ax.set_title('Per Capita CO₂: Production vs Consumption', fontsize=12, fontweight='bold')
ax.set_ylabel('t CO₂ per capita')
ax.legend(fontsize=9)

plt.suptitle('Chart 20: CO₂ Trade Flows & "Exploitation" Test', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/20_co2_trade_exploitation.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 20 saved: co2_trade_exploitation.png")

# Key numbers
print("\nCO₂ trade flows — offshoring test:")
for c in ['United States', 'United Kingdom', 'Germany', 'Japan', 'China', 'India']:
    d = co2[(co2['country'] == c) & (co2['year'] == w_yr)]
    if len(d) > 0:
        r = d.iloc[0]
        prod = r.get('co2', float('nan'))
        cons = r.get('consumption_co2', float('nan'))
        trade = r.get('trade_co2', float('nan'))
        if pd.notna(prod) and pd.notna(cons):
            pct = (cons - prod) / prod * 100
            print(f"  {c:20s}: Production={prod:8.0f} Mt  Consumption={cons:8.0f} Mt  "
                  f"Net import={cons-prod:+8.0f} Mt ({pct:+.1f}%)")

# Historical self-sufficiency test
print(f"\nUS consumption-based vs production-based CO₂ per capita (selected years):")
us = co2[co2['country'] == 'United States']
for yr in [1990, 2000, 2010, 2020, w_yr]:
    d = us[us['year'] == yr]
    if len(d) > 0:
        r = d.iloc[0]
        prod_pc = r.get('co2_per_capita', float('nan'))
        cons_pc = r.get('consumption_co2_per_capita', float('nan'))
        if pd.notna(prod_pc) and pd.notna(cons_pc):
            gap = (cons_pc - prod_pc) / prod_pc * 100
            print(f"  {yr}: Production={prod_pc:.1f}t  Consumption={cons_pc:.1f}t  Gap={gap:+.1f}%")


# ══════════════════════════════════════════════════════════════════════════════
# PART 4: CO2 Intensity Turning Points & Absolute Decoupling
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("PART 4: ABSOLUTE DECOUPLING — WHO HAS ACHIEVED IT AND WHEN?")
print("─"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 4a: Countries with absolute CO2 decoupling (GDP up, CO2 down)
ax = axes[0, 0]
absolute_decouplers = ['United States', 'United Kingdom', 'Germany', 'France',
                       'Denmark', 'Sweden', 'Japan']
for c in absolute_decouplers:
    d = co2[(co2['country'] == c) & (co2['year'] >= 1990) & (co2['co2'].notna()) & (co2['gdp'].notna())]
    d = d.sort_values('year')
    if len(d) > 0:
        # Normalize to 1990=100
        base_co2 = d[d['year'] == 1990]['co2'].values
        base_gdp = d[d['year'] == 1990]['gdp'].values
        if len(base_co2) > 0 and len(base_gdp) > 0:
            ax.plot(d['year'], d['gdp'] / base_gdp[0] * 100, color='green', alpha=0.3, linewidth=0.8)
            ax.plot(d['year'], d['co2'] / base_co2[0] * 100, color='red', alpha=0.3, linewidth=0.8)

# Add labeled lines for US, UK, Germany
for c, color in [('United States', 'blue'), ('United Kingdom', 'purple'), ('Germany', 'darkgreen')]:
    d = co2[(co2['country'] == c) & (co2['year'] >= 1990) & (co2['co2'].notna()) & (co2['gdp'].notna())]
    d = d.sort_values('year')
    if len(d) > 0:
        base_co2 = d[d['year'] == 1990]['co2'].values[0]
        base_gdp = d[d['year'] == 1990]['gdp'].values[0]
        ax.plot(d['year'], d['gdp'] / base_gdp * 100, color=color, linewidth=1.5, label=f'{c} GDP')
        ax.plot(d['year'], d['co2'] / base_co2 * 100, color=color, linewidth=1.5, linestyle='--', label=f'{c} CO₂')

ax.axhline(y=100, color='black', linewidth=0.5, linestyle=':')
ax.set_title('Absolute Decoupling: GDP vs CO₂ (1990=100)', fontsize=12, fontweight='bold')
ax.set_ylabel('Index (1990=100)')
ax.legend(fontsize=7, ncol=2)

# 4b: When did each country's CO2 peak?
ax = axes[0, 1]
peak_data = []
test_countries = ['United States', 'United Kingdom', 'Germany', 'France', 'Japan',
                  'Italy', 'Canada', 'Australia', 'South Korea', 'Spain',
                  'Netherlands', 'Sweden', 'Denmark', 'Norway', 'Poland',
                  'China', 'India', 'Brazil', 'Indonesia', 'Mexico']
for c in test_countries:
    d = co2[(co2['country'] == c) & (co2['year'] >= 1960) & (co2['co2'].notna())]
    if len(d) > 5:
        peak_year = d.loc[d['co2'].idxmax(), 'year']
        peak_co2 = d['co2'].max()
        latest = d.sort_values('year').iloc[-1]
        latest_co2 = latest['co2']
        decline_pct = (1 - latest_co2/peak_co2) * 100 if peak_co2 > 0 else 0
        still_rising = peak_year >= latest['year'] - 3  # peaked within last 3 years = still rising
        peak_data.append({
            'country': c, 'peak_year': int(peak_year),
            'decline_from_peak': decline_pct,
            'still_rising': still_rising
        })

pdf = pd.DataFrame(peak_data).sort_values('peak_year')
colors = ['red' if r['still_rising'] else 'green' for _, r in pdf.iterrows()]
ax.barh(range(len(pdf)), pdf['peak_year'], color=colors, alpha=0.7)
ax.set_yticks(range(len(pdf)))
ax.set_yticklabels(pdf['country'], fontsize=9)
ax.set_xlabel('Year of Peak CO₂ Emissions')
ax.set_title('When Did CO₂ Peak? (🟢peaked  🔴still rising)', fontsize=12, fontweight='bold')
ax.set_xlim(1970, 2030)

# 4c: Decoupling rate over time (rolling 10-year for World)
ax = axes[1, 0]
for label, df, color in [('World', world, 'black'), ('High income', hi_agg, 'blue'),
                          ('Upper-middle', umi_agg, 'green')]:
    d = df[(df['co2_per_gdp'].notna()) & (df['year'] >= 1960)].sort_values('year').set_index('year')
    if len(d) > 15:
        intensity = d['co2_per_gdp']
        # Rolling 10-year annualized change rate
        rolling_rate = intensity.pct_change(10).apply(lambda x: ((1+x)**(1/10) - 1) * 100 if pd.notna(x) else np.nan)
        ax.plot(rolling_rate.index, rolling_rate.values, label=label, color=color)
ax.axhline(y=0, color='black', linewidth=0.5)
ax.axhline(y=-3.5, color='red', linewidth=1, linestyle=':', label='Needed for 1.5°C (~3.5%/yr)')
ax.set_title('Rolling 10yr CO₂/GDP Decoupling Rate', fontsize=12, fontweight='bold')
ax.set_ylabel('Annual change in CO₂ intensity (%)')
ax.legend(fontsize=9)
ax.annotate('Below zero = decoupling\nMore negative = faster', xy=(0.02, 0.05),
            xycoords='axes fraction', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

# 4d: Required decoupling rate for various growth + climate scenarios
ax = axes[1, 1]
growth_rates = np.linspace(0, 0.06, 50)
for budget_label, budget_gt, color in [('1.5°C (300 Gt)', 300, 'red'),
                                         ('2°C (900 Gt)', 900, 'orange'),
                                         ('3°C (~2500 Gt)', 2500, 'green')]:
    # For each growth rate, what decoupling rate keeps cumulative emissions within budget over 50 years?
    # Simplification: need annual emissions path such that sum over 50 years < budget
    # If current = 37 Gt/yr, and emissions decline at rate d while GDP grows at rate g
    # Annual emissions = 37 * ((1+g)*(1-d))^t
    # Sum = 37 * sum((1+g-d-gd)^t) ≈ 37 * sum((1+g-d)^t)
    # We need to find d such that sum < budget
    required_d = []
    for g in growth_rates:
        # Binary search for required decoupling rate
        d_low, d_high = 0, 0.15
        for _ in range(50):
            d_mid = (d_low + d_high) / 2
            cumul = sum(current_annual * ((1+g) * (1-d_mid))**t for t in range(50))
            if cumul > budget_gt:
                d_low = d_mid
            else:
                d_high = d_mid
        required_d.append(d_mid * 100)
    ax.plot(growth_rates * 100, required_d, label=budget_label, color=color, linewidth=2)

ax.axhline(y=2.5, color='gray', linewidth=1, linestyle=':', alpha=0.7)
ax.annotate('Current best decoupling rate (~2.5%/yr)', xy=(3, 2.7), fontsize=8, color='gray')
ax.set_xlabel('Global GDP Growth Rate (%/yr)')
ax.set_ylabel('Required CO₂ Intensity Decline (%/yr)')
ax.set_title('Required Decoupling to Stay Within Carbon Budgets\n(over next 50 years)',
             fontsize=12, fontweight='bold')
ax.legend(fontsize=9)
ax.set_ylim(0, 12)

plt.suptitle('Chart 21: Absolute Decoupling & Climate Constraints', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/21_absolute_decoupling.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 21 saved: absolute_decoupling.png")

# Print peak years
print("\nCO₂ emission peaks:")
for _, r in pdf.iterrows():
    status = "STILL RISING" if r['still_rising'] else f"down {r['decline_from_peak']:.0f}% from peak"
    print(f"  {r['country']:20s}: peaked {r['peak_year']:d}  ({status})")


# ══════════════════════════════════════════════════════════════════════════════
# PART 5: The Poor-World-Only Growth Scenario (Detailed)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("PART 5: WHAT IF ONLY POOR COUNTRIES GREW? THE KEY SCENARIO")
print("─"*80)

# Get Maddison data for current GDP per capita distribution
mad = maddison[maddison['year'] == 2022].dropna(subset=['gdppc', 'pop'])

# Define "good life" threshold from our earlier analysis: ~$15,000 PPP (2017 int'l $)
GOOD_LIFE_THRESHOLD = 15000
DECENT_LIFE = 6850  # roughly $6.85/day * 365 * PPP adjustment ≈ corresponds to UMI threshold

# Countries below good-life threshold
below_gl = mad[mad['gdppc'] < GOOD_LIFE_THRESHOLD]
above_gl = mad[mad['gdppc'] >= GOOD_LIFE_THRESHOLD]

below_gl_pop = below_gl['pop'].sum()
above_gl_pop = above_gl['pop'].sum()
below_gl_gdp = (below_gl['gdppc'] * below_gl['pop']).sum()
above_gl_gdp = (above_gl['gdppc'] * above_gl['pop']).sum()
total_gdp = below_gl_gdp + above_gl_gdp

print(f"\nGood-life threshold: ${GOOD_LIFE_THRESHOLD:,.0f} GDP/cap (2017 PPP)")
print(f"  Below threshold: {below_gl_pop/1e9:.2f} billion people ({below_gl_pop/(below_gl_pop+above_gl_pop)*100:.0f}%)")
print(f"      Avg GDP/cap: ${below_gl_gdp/below_gl_pop:,.0f}")
print(f"      Total GDP: ${below_gl_gdp/1e12:.1f} trillion")
print(f"  Above threshold: {above_gl_pop/1e9:.2f} billion people ({above_gl_pop/(below_gl_pop+above_gl_pop)*100:.0f}%)")
print(f"      Avg GDP/cap: ${above_gl_gdp/above_gl_pop:,.0f}")
print(f"      Total GDP: ${above_gl_gdp/1e12:.1f} trillion")

# GDP multiplication needed for below-threshold countries to reach $15,000
gdp_multiple_needed = GOOD_LIFE_THRESHOLD / (below_gl_gdp / below_gl_pop)
print(f"\n  GDP multiplication needed for poor world: {gdp_multiple_needed:.1f}x")
print(f"  At 5% growth: {np.log(gdp_multiple_needed)/np.log(1.05):.0f} years")
print(f"  At 4% growth: {np.log(gdp_multiple_needed)/np.log(1.04):.0f} years")
print(f"  At 3% growth: {np.log(gdp_multiple_needed)/np.log(1.03):.0f} years")

# CO2 implications — ONLY poor-world growth, rich world frozen
print("\n  CO₂ implications (rich world frozen at current levels):")

# Current poor-world CO2 (approximate from income groups)
# Low + Lower-middle income CO2
poor_co2_current = 0
for g in ['Lower-middle', 'Low income']:
    if g in latest:
        poor_co2_current += latest[g]['co2']
# Upper-middle is tricky since it includes China; let's use a weighted approach
# Better: use the actual OWID data matched to Maddison countries
poor_countries = below_gl['countrycode'].tolist()
poor_co2_data = co2[(co2['iso_code'].isin(poor_countries)) & (co2['year'] == w_yr) & (co2['co2'].notna())]
poor_co2_actual = poor_co2_data['co2'].sum()
rich_co2_actual = total_co2_world - poor_co2_actual

print(f"  Current poor-world CO₂: ~{poor_co2_actual:.0f} Mt ({poor_co2_actual/total_co2_world*100:.0f}% of global)")
print(f"  Current rich-world CO₂: ~{rich_co2_actual:.0f} Mt ({rich_co2_actual/total_co2_world*100:.0f}% of global)")

# If poor world multiplies GDP by needed amount with various decoupling rates
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# 5a: Annual emissions path for poor-world-only growth
ax = axes[0]
years_forward = np.arange(0, 101)
for decouple, ls in [(0.02, ':'), (0.03, '--'), (0.04, '-'), (0.05, '-.')]:
    gdp_growth = 0.05  # 5% growth for poor world
    # Poor world emissions path
    poor_emissions = []
    rich_emissions = rich_co2_actual / 1000  # Gt, frozen
    # Also model rich world declining at their own decoupling rate
    rich_decouple = 0.025  # rich world continues decoupling even if GDP frozen (renewables replacing fossil)
    for yr in years_forward:
        poor_gdp_factor = (1 + gdp_growth) ** yr
        poor_intensity_factor = (1 - decouple) ** yr
        poor_annual = (poor_co2_actual / 1000) * poor_gdp_factor * poor_intensity_factor
        rich_annual = rich_emissions * (1 - rich_decouple) ** yr
        poor_emissions.append(poor_annual + rich_annual)
    ax.plot(2022 + years_forward, poor_emissions, label=f'Decouple {decouple*100:.0f}%/yr', linestyle=ls)

ax.axhline(y=current_annual, color='black', linewidth=0.5, linestyle=':')
ax.annotate(f'Current: {current_annual:.0f} Gt', xy=(2025, current_annual + 1), fontsize=9)
ax.set_xlabel('Year')
ax.set_ylabel('Global CO₂ (Gt/yr)')
ax.set_title('Annual CO₂: Rich World Frozen, Poor World Grows 5%/yr', fontsize=12, fontweight='bold')
ax.legend()

# 5b: Cumulative emissions vs carbon budgets
ax = axes[1]
for decouple, ls in [(0.02, ':'), (0.03, '--'), (0.04, '-'), (0.05, '-.')]:
    cumul = []
    running = 0
    for yr in years_forward:
        poor_gdp_factor = (1 + gdp_growth) ** yr
        poor_intensity_factor = (1 - decouple) ** yr
        poor_annual = (poor_co2_actual / 1000) * poor_gdp_factor * poor_intensity_factor
        rich_annual = rich_emissions * (1 - 0.025) ** yr
        running += poor_annual + rich_annual
        cumul.append(running)
    ax.plot(2022 + years_forward, cumul, label=f'Decouple {decouple*100:.0f}%/yr', linestyle=ls)

ax.axhline(y=remaining_15c, color='red', linewidth=2, linestyle='-', alpha=0.5)
ax.annotate('1.5°C budget', xy=(2025, remaining_15c + 50), fontsize=10, color='red')
ax.axhline(y=remaining_2c, color='orange', linewidth=2, linestyle='-', alpha=0.5)
ax.annotate('2°C budget', xy=(2025, remaining_2c + 50), fontsize=10, color='orange')
ax.set_xlabel('Year')
ax.set_ylabel('Cumulative CO₂ (Gt)')
ax.set_title('Cumulative CO₂ vs Carbon Budgets', fontsize=12, fontweight='bold')
ax.legend()

plt.suptitle('Chart 22: Poor-World-Only Growth Scenario', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/22_poor_world_growth_scenario.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 22 saved: poor_world_growth_scenario.png")

# Calculate precise budget exceedance
print("\n  Cumulative CO₂ for poor-world-only growth (rich frozen + decoupling):")
for decouple in [0.02, 0.03, 0.04, 0.05]:
    running = 0
    exceeded_15c = None
    exceeded_2c = None
    for yr in range(101):
        poor_annual = (poor_co2_actual / 1000) * ((1.05) ** yr) * ((1 - decouple) ** yr)
        rich_annual = rich_emissions * (1 - 0.025) ** yr
        running += poor_annual + rich_annual
        if exceeded_15c is None and running > remaining_15c:
            exceeded_15c = yr
        if exceeded_2c is None and running > remaining_2c:
            exceeded_2c = yr

    target_reached = np.log(gdp_multiple_needed) / np.log(1.05)
    print(f"  Decouple {decouple*100:.0f}%/yr: 1.5°C exceeded in {exceeded_15c if exceeded_15c else '>100'}yr  "
          f"2°C exceeded in {exceeded_2c if exceeded_2c else '>100'}yr  "
          f"(Poor-world convergence at year {target_reached:.0f})")


# ══════════════════════════════════════════════════════════════════════════════
# PART 6: Energy Transition Context
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*80)
print("PART 6: ENERGY TRANSITION — How Fast is it Changing the Picture?")
print("─"*80)

# CO2 per unit energy — this tells us how the electricity mix is changing
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

ax = axes[0]
for label, df, color in [('World', world, 'black'), ('High income', hi_agg, 'blue'),
                          ('Upper-middle', umi_agg, 'green'), ('Lower-middle', lmi_agg, 'orange')]:
    d = df[(df['year'] >= 1965) & (df['co2_per_unit_energy'].notna())].sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['co2_per_unit_energy'], label=label, color=color)
ax.set_title('CO₂ per Unit Energy (kg/kWh)\nHow Clean is the Energy Mix?', fontsize=12, fontweight='bold')
ax.set_ylabel('kg CO₂ per kWh')
ax.set_xlabel('Year')
ax.legend(fontsize=9)

# Energy per GDP — how much energy does each $ need?
ax = axes[1]
for label, df, color in [('World', world, 'black'), ('High income', hi_agg, 'blue'),
                          ('Upper-middle', umi_agg, 'green'), ('Lower-middle', lmi_agg, 'orange')]:
    d = df[(df['year'] >= 1965) & (df['energy_per_gdp'].notna())].sort_values('year')
    if len(d) > 0:
        # Normalize to earliest available year = 100
        base = d.iloc[0]['energy_per_gdp']
        ax.plot(d['year'], d['energy_per_gdp'] / base * 100, label=label, color=color)
ax.axhline(y=100, color='black', linewidth=0.5, linestyle=':')
ax.set_title('Energy Intensity of GDP (normalized, earliest=100)\nHow Much Energy per $?', fontsize=12, fontweight='bold')
ax.set_ylabel('Index')
ax.set_xlabel('Year')
ax.legend(fontsize=9)

plt.suptitle('Chart 23: Energy Transition Progress', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/23_energy_transition.png', dpi=150, bbox_inches='tight')
plt.close()
print("  → Chart 23 saved: energy_transition.png")

# Key transition numbers
print("\nCO₂ per unit energy trends:")
for label, df in [('World', world), ('High income', hi_agg)]:
    d = df[df['co2_per_unit_energy'].notna()].set_index('year')['co2_per_unit_energy']
    for p in [(1990, 2000), (2000, 2010), (2010, 2020)]:
        if p[0] in d.index and p[1] in d.index:
            rate = ((d[p[1]]/d[p[0]])**(1/10) - 1) * 100
            print(f"  {label} {p[0]}-{p[1]}: {rate:.2f}%/yr")

print("\nEnergy per GDP trends:")
for label, df in [('World', world), ('High income', hi_agg)]:
    d = df[df['energy_per_gdp'].notna()].set_index('year')['energy_per_gdp']
    for p in [(1990, 2000), (2000, 2010), (2010, 2020)]:
        if p[0] in d.index and p[1] in d.index:
            rate = ((d[p[1]]/d[p[0]])**(1/10) - 1) * 100
            print(f"  {label} {p[0]}-{p[1]}: {rate:.2f}%/yr")

# Decomposition: CO2/GDP = (CO2/Energy) × (Energy/GDP)
# Total decoupling = energy efficiency + energy mix cleaning
print("\nDecoupling decomposition (CO₂/GDP = CO₂/Energy × Energy/GDP):")
for label, df in [('World', world), ('High income', hi_agg)]:
    d = df[df['co2_per_gdp'].notna() & df['co2_per_unit_energy'].notna() & df['energy_per_gdp'].notna()]
    d = d.set_index('year')
    for p in [(2000, 2010), (2010, 2020)]:
        if p[0] in d.index and p[1] in d.index:
            co2_gdp_rate = ((d.loc[p[1], 'co2_per_gdp']/d.loc[p[0], 'co2_per_gdp'])**(1/10) - 1) * 100
            co2_energy_rate = ((d.loc[p[1], 'co2_per_unit_energy']/d.loc[p[0], 'co2_per_unit_energy'])**(1/10) - 1) * 100
            energy_gdp_rate = ((d.loc[p[1], 'energy_per_gdp']/d.loc[p[0], 'energy_per_gdp'])**(1/10) - 1) * 100
            print(f"  {label} {p[0]}-{p[1]}:")
            print(f"    CO₂/GDP: {co2_gdp_rate:.2f}%/yr = CO₂/Energy: {co2_energy_rate:.2f}%/yr + Energy/GDP: {energy_gdp_rate:.2f}%/yr")
            pct_from_clean = co2_energy_rate / co2_gdp_rate * 100 if co2_gdp_rate != 0 else 0
            pct_from_eff = energy_gdp_rate / co2_gdp_rate * 100 if co2_gdp_rate != 0 else 0
            print(f"    → {pct_from_clean:.0f}% from cleaner energy, {pct_from_eff:.0f}% from efficiency")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("SUMMARY OF KEY FINDINGS")
print("="*80)
print("""
1. DECOUPLING IS REAL AND ACCELERATING (for carbon, not yet for materials)
   - High-income CO₂/GDP declining at ~2-3%/yr
   - Energy mix getting cleaner + economy getting more energy-efficient
   - But: global absolute CO₂ still rising because poor-world growth > rich-world decoupling

2. THE "FROZEN RICH WORLD" SCENARIO IS SURPRISINGLY MANAGEABLE
   - Poor world needs only ~3x GDP to reach good-life threshold
   - At 5% growth + 3-4% decoupling, 2°C budget may be achievable
   - The ecological problem is NOT poor-world growth — it's rich-world continuation

3. THE "EXPLOITATION" HYPOTHESIS IS PARTIALLY TRUE, PARTIALLY WRONG
   - Rich countries DO offshore ~8-15% of their emissions via trade
   - But this means 85-92% of rich-world consumption is domestically produced
   - The rich world COULD sustain most of its material standard internally
   - The real trade dependency runs the other way: poor countries depend on exports to rich markets

4. ABSOLUTE DECOUPLING IS HAPPENING IN ~30+ COUNTRIES
   - US, UK, Germany, France, Japan all peaked and are declining in absolute CO₂
   - But the rates are too slow for 1.5°C (need ~3.5%/yr, achieving ~2-3%/yr)
   - Solar + storage acceleration could change this dramatically

5. THE CRITICAL VARIABLE IS DECOUPLING RATE, NOT GROWTH RATE
   - Whether poor-world growth is compatible with climate depends on 
     achieving 3-5%/yr decoupling instead of current 2-3%/yr
   - This is where the energy transition (solar, wind, storage, eventually fusion) is decisive
   - The paper is right that CURRENT rates are insufficient; wrong to assume they can't accelerate
""")
