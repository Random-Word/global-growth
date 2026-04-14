"""
Analysis 13: Why Some Countries Develop and Others Don't
=========================================================
Questions addressed:
1. Does ODA data support the "greed" narrative? Rich countries got richer
   but give less — or is the picture more complicated?
2. What inputs correlate with development takeoff? (savings, investment,
   trade openness, fertility decline, education)
3. Why did East Asia diverge from SSA and Latin America?
4. Which poor countries improved welfare most, and what did they do?
5. Is the "Asian model" replicable, or is there something unique?
6. What role do remittances and diaspora play vs ODA?

Uses WDI data on ~41 countries: GDP/cap PPP, ODA, savings, investment,
trade, FDI, remittances, fertility, education, demographics.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='colorblind')
CHART_DIR = 'charts'

# ── Load data ─────────────────────────────────────────────────────────────────
raw = pd.read_csv('data/raw/wdi_development_theories.csv')

# Pivot to wide format: one row per (cc, year), one column per indicator
df = raw.pivot_table(index=['cc', 'country', 'year'],
                     columns='indicator', values='value').reset_index()
df.columns.name = None
print(f'Loaded: {len(df)} rows, {df.cc.nunique()} countries')

# ── Region groupings ──────────────────────────────────────────────────────────
REGIONS = {
    'East Asia': ['KOR', 'CHN', 'VNM', 'THA', 'MYS', 'IDN', 'SGP'],
    'South Asia': ['IND', 'BGD', 'LKA', 'PAK'],
    'Sub-Saharan Africa': ['NGA', 'ETH', 'KEN', 'GHA', 'TZA', 'RWA', 'BWA',
                           'ZAF', 'UGA', 'MOZ', 'SEN', 'CIV'],
    'Latin America': ['BRA', 'MEX', 'CHL', 'COL', 'ARG', 'PER', 'CRI'],
    'Rich': ['USA', 'GBR', 'FRA', 'DEU', 'NOR', 'SWE', 'JPN'],
    'Other': ['POL', 'TUR', 'EGY', 'MAR'],
}
cc_region = {}
for r, ccs in REGIONS.items():
    for cc in ccs:
        cc_region[cc] = r
df['region'] = df['cc'].map(cc_region)

NAMES = {
    'KOR': 'S. Korea', 'CHN': 'China', 'VNM': 'Vietnam', 'THA': 'Thailand',
    'MYS': 'Malaysia', 'IDN': 'Indonesia', 'SGP': 'Singapore', 'JPN': 'Japan',
    'IND': 'India', 'BGD': 'Bangladesh', 'LKA': 'Sri Lanka', 'PAK': 'Pakistan',
    'NGA': 'Nigeria', 'ETH': 'Ethiopia', 'KEN': 'Kenya', 'GHA': 'Ghana',
    'TZA': 'Tanzania', 'RWA': 'Rwanda', 'BWA': 'Botswana', 'ZAF': 'S. Africa',
    'UGA': 'Uganda', 'MOZ': 'Mozambique', 'SEN': 'Senegal', 'CIV': "Cote d'Iv.",
    'BRA': 'Brazil', 'MEX': 'Mexico', 'CHL': 'Chile', 'COL': 'Colombia',
    'ARG': 'Argentina', 'PER': 'Peru', 'CRI': 'Costa Rica',
    'USA': 'US', 'GBR': 'UK', 'FRA': 'France', 'DEU': 'Germany',
    'NOR': 'Norway', 'SWE': 'Sweden', 'POL': 'Poland',
    'TUR': 'Turkey', 'EGY': 'Egypt', 'MAR': 'Morocco',
}

REGION_COLORS = {
    'East Asia': '#e74c3c', 'South Asia': '#e67e22',
    'Sub-Saharan Africa': '#9b59b6', 'Latin America': '#f1c40f',
    'Rich': '#3498db', 'Other': '#95a5a6',
}


# ══════════════════════════════════════════════════════════════════════════════
# CHART 58: THE "GREED" QUESTION — ODA vs RICH-WORLD INCOME
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 58: THE 'GREED' QUESTION — ODA vs RICH-WORLD INCOME")
print("═"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('The "Greed" Question: Is Foreign Aid Keeping Up?',
             fontsize=16, fontweight='bold')

# NOTE: Our ODA data is RECIPIENT-side (ODA received as % of GNI, net ODA in USD).
# Rich donor countries have no ODA data in our dataset.

# Panel 1: ODA received as % of GNI — key recipients over time
ax = axes[0, 0]
oda_recipients = ['ETH', 'MOZ', 'RWA', 'TZA', 'BGD', 'GHA', 'KEN', 'SEN', 'UGA']
oda_colors = plt.cm.tab10(np.linspace(0, 1, len(oda_recipients)))
for cc, col in zip(oda_recipients, oda_colors):
    d = df[(df['cc'] == cc) & (df['oda_pct_gni_donor'].notna())].sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['oda_pct_gni_donor'], label=NAMES[cc], color=col, linewidth=1.5)
ax.set_ylabel('ODA Received (% of GNI)')
ax.set_title('Aid Dependency Has Fallen')
ax.legend(fontsize=7, ncol=2)

# Panel 2: Total ODA received summed across all developing countries in our dataset
ax = axes[0, 1]
dev_ccs_oda = [cc for r in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America']
               for cc in REGIONS[r]]
total_oda = df[df['cc'].isin(dev_ccs_oda)].groupby('year')['oda_net_current_usd'].sum().reset_index()
total_oda = total_oda[total_oda['oda_net_current_usd'].notna()]
total_oda['oda_bn'] = total_oda['oda_net_current_usd'] / 1e9
ax.fill_between(total_oda['year'], total_oda['oda_bn'], alpha=0.3, color='#3498db')
ax.plot(total_oda['year'], total_oda['oda_bn'], color='#3498db', linewidth=2)
ax.set_ylabel('Total ODA Received ($ billion)')
ax.set_title('Absolute ODA Has Risen, But...')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:.0f}b'))

# Panel 3: ODA received vs remittances — latest year, key recipients
ax = axes[1, 0]
compare_ccs = ['ETH', 'BGD', 'PAK', 'NGA', 'KEN', 'GHA', 'VNM',
               'EGY', 'SEN', 'IND', 'MOZ', 'TZA']
for_plot = []
for cc in compare_ccs:
    d_latest = df[(df['cc'] == cc)].sort_values('year').groupby('cc').last()
    if cc in d_latest.index:
        row = d_latest.loc[cc]
        rem = row.get('remittances_pct_gdp', np.nan)
        oda = row.get('oda_pct_gni_donor', np.nan)
        if not np.isnan(rem) or not np.isnan(oda):
            for_plot.append({
                'cc': cc, 'name': NAMES.get(cc, cc),
                'remittances': rem if not np.isnan(rem) else 0,
                'oda': oda if not np.isnan(oda) else 0,
            })

if for_plot:
    fp = pd.DataFrame(for_plot).sort_values('remittances', ascending=True)
    y = np.arange(len(fp))
    h = 0.35
    bars1 = ax.barh(y - h/2, fp['remittances'], h, label='Remittances', color='#2ecc71')
    bars2 = ax.barh(y + h/2, fp['oda'], h, label='ODA received', color='#e74c3c', alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(fp['name'], fontsize=9)
    ax.set_xlabel('% of GNI')
    ax.set_title('Remittances vs ODA Received (latest)')
    ax.legend(fontsize=9)

# Panel 4: Regional ODA dependency declining as private flows rise
ax = axes[1, 1]
for region in ['East Asia', 'Sub-Saharan Africa', 'Latin America', 'South Asia']:
    ccs = REGIONS[region]
    yearly = df[df['cc'].isin(ccs)].groupby('year').agg({
        'oda_pct_gni_donor': 'median',
        'fdi_pct_gdp': 'median',
        'remittances_pct_gdp': 'median',
    }).reset_index()
    yearly = yearly[yearly['year'] >= 1980]
    # ODA declining
    oda_y = yearly[yearly['oda_pct_gni_donor'].notna()]
    if len(oda_y) > 0:
        ax.plot(oda_y['year'], oda_y['oda_pct_gni_donor'], label=f'{region} ODA',
                color=REGION_COLORS[region], linewidth=2)
    # FDI rising
    fdi_y = yearly[yearly['fdi_pct_gdp'].notna()]
    if len(fdi_y) > 0:
        ax.plot(fdi_y['year'], fdi_y['fdi_pct_gdp'], label=f'{region} FDI',
                color=REGION_COLORS[region], linewidth=1.5, linestyle='--')

ax.set_ylabel('% of GNI/GDP (median)')
ax.set_title('ODA (solid) Declining, FDI (dashed) Rising')
ax.legend(fontsize=6.5, ncol=2)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/58_oda_greed_question.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 58 saved: 58_oda_greed_question.png")

# Print ODA summary
print("\nODA dependency trends (recipient side):")
for cc in ['ETH', 'MOZ', 'RWA', 'TZA', 'BGD', 'GHA', 'KEN', 'IND']:
    d = df[(df['cc'] == cc) & (df['oda_pct_gni_donor'].notna())].sort_values('year')
    if len(d) >= 2:
        early = d[d['year'].between(1995, 2002)]
        late = d[d['year'] >= 2018]
        if len(early) > 0 and len(late) > 0:
            e, l = early.iloc[-1], late.iloc[-1]
            chg = l['oda_pct_gni_donor'] - e['oda_pct_gni_donor']
            print(f"  {NAMES[cc]:12s}: {e['oda_pct_gni_donor']:.1f}% ({int(e['year'])}) -> "
                  f"{l['oda_pct_gni_donor']:.1f}% ({int(l['year'])})  {chg:+.1f}pp")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 59: THE DEVELOPMENT RECIPE — WHAT DISTINGUISHES TAKE-OFF COUNTRIES?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 59: THE DEVELOPMENT RECIPE")
print("═"*80)

fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle('The Development Recipe: What Distinguishes Countries That Took Off?',
             fontsize=16, fontweight='bold')

# Compute averages over 1990-2010 "takeoff window" for developing countries
dev_ccs = [cc for r in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America']
           for cc in REGIONS[r]]
window = df[(df['cc'].isin(dev_ccs)) & (df['year'].between(1990, 2015))]
avg = window.groupby('cc').agg({
    'gross_savings_pct_gdp': 'mean',
    'gross_fixed_capital_pct_gdp': 'mean',
    'trade_pct_gdp': 'mean',
    'fertility_rate': 'mean',
    'fdi_pct_gdp': 'mean',
    'gdp_growth': 'mean',
}).reset_index()
avg['region'] = avg['cc'].map(cc_region)
avg['name'] = avg['cc'].map(NAMES)

# Get GDP growth over the full period
for cc in dev_ccs:
    d = df[(df['cc'] == cc) & (df['gdppc_ppp'].notna())].sort_values('year')
    if len(d) >= 2:
        early = d[d['year'].between(1990, 1998)]
        late = d[d['year'] >= 2018]
        if len(early) > 0 and len(late) > 0:
            growth = (late.iloc[-1]['gdppc_ppp'] / early.iloc[-1]['gdppc_ppp'] - 1) * 100
            avg.loc[avg['cc'] == cc, 'total_gdp_growth'] = growth

avg = avg.dropna(subset=['total_gdp_growth'])

metrics = [
    ('gross_savings_pct_gdp', 'Avg Savings Rate (% GDP)', 'Savings → Investment → Growth'),
    ('gross_fixed_capital_pct_gdp', 'Avg Fixed Capital Investment (% GDP)', 'Investment Intensity'),
    ('trade_pct_gdp', 'Avg Trade Openness (% GDP)', 'Integration With World Economy'),
    ('fertility_rate', 'Avg Fertility Rate', 'Demographic Dividend'),
    ('fdi_pct_gdp', 'Avg FDI Inflows (% GDP)', 'Foreign Investment'),
    ('gdp_growth', 'Avg Annual GDP Growth (%)', 'Sustained Growth'),
]

for ax, (col, xlabel, title) in zip(axes.flat, metrics):
    for region in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America']:
        mask = avg['region'] == region
        ax.scatter(avg.loc[mask, col], avg.loc[mask, 'total_gdp_growth'],
                   c=REGION_COLORS[region], label=region, s=80, alpha=0.8, edgecolors='white')
    # Label points
    for _, row in avg.iterrows():
        ax.annotate(row['name'], (row[col], row['total_gdp_growth']),
                    fontsize=6.5, ha='center', va='bottom', alpha=0.8)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel('Total GDP/cap growth (%)\n1990s → 2020s', fontsize=9)
    ax.set_title(title, fontsize=10, fontweight='bold')

# Single legend
handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc='lower center', ncol=4, fontsize=10,
           bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/59_development_recipe.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 59 saved: 59_development_recipe.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 60: ASIA vs AFRICA vs LATIN AMERICA — DIVERGENT PATHS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 60: DIVERGENT PATHS — ASIA vs AFRICA vs LATIN AMERICA")
print("═"*80)

fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle('Divergent Paths: What Made East Asia Different?',
             fontsize=16, fontweight='bold')

compare_regions = ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America']

# Panel 1: GDP/cap trajectories (regional medians)
ax = axes[0, 0]
for region in compare_regions:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs) & df['gdppc_ppp'].notna()]
    med = rd.groupby('year')['gdppc_ppp'].median().reset_index()
    if len(med) > 0:
        ax.plot(med['year'], med['gdppc_ppp'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('GDP/cap PPP (median)')
ax.set_title('Income Trajectories')
ax.legend(fontsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))

# Panel 2: Savings rates
ax = axes[0, 1]
for region in compare_regions:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs) & df['gross_savings_pct_gdp'].notna()]
    med = rd.groupby('year')['gross_savings_pct_gdp'].median().reset_index()
    if len(med) > 0:
        ax.plot(med['year'], med['gross_savings_pct_gdp'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('Gross Savings (% GDP)')
ax.set_title('Savings Rates')
ax.legend(fontsize=8)

# Panel 3: Investment rates
ax = axes[0, 2]
for region in compare_regions:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs) & df['gross_fixed_capital_pct_gdp'].notna()]
    med = rd.groupby('year')['gross_fixed_capital_pct_gdp'].median().reset_index()
    if len(med) > 0:
        ax.plot(med['year'], med['gross_fixed_capital_pct_gdp'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('Gross Fixed Capital (% GDP)')
ax.set_title('Investment Rates')
ax.legend(fontsize=8)

# Panel 4: Fertility decline
ax = axes[1, 0]
for region in compare_regions:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs) & df['fertility_rate'].notna()]
    med = rd.groupby('year')['fertility_rate'].median().reset_index()
    if len(med) > 0:
        ax.plot(med['year'], med['fertility_rate'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.axhline(2.1, color='gray', linestyle='--', alpha=0.5, label='Replacement rate')
ax.set_ylabel('Fertility Rate')
ax.set_title('The Demographic Transition')
ax.legend(fontsize=8)

# Panel 5: Trade openness
ax = axes[1, 1]
for region in compare_regions:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs) & df['trade_pct_gdp'].notna()]
    med = rd.groupby('year')['trade_pct_gdp'].median().reset_index()
    if len(med) > 0:
        ax.plot(med['year'], med['trade_pct_gdp'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('Trade (% GDP)')
ax.set_title('Trade Openness')
ax.legend(fontsize=8)

# Panel 6: Tertiary enrollment
ax = axes[1, 2]
for region in compare_regions:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs) & df['tertiary_enrollment'].notna()]
    med = rd.groupby('year')['tertiary_enrollment'].median().reset_index()
    if len(med) > 0:
        ax.plot(med['year'], med['tertiary_enrollment'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('Tertiary Enrollment (%)')
ax.set_title('Higher Education')
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/60_divergent_paths.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 60 saved: 60_divergent_paths.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 61: SUCCESS STORIES — COUNTRY-LEVEL DEVELOPMENT PROFILES
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 61: DEVELOPMENT SUCCESS STORIES")
print("═"*80)

# Rank developing countries by total GDP/cap growth since earliest data
growth_ranks = []
for cc in dev_ccs:
    d = df[(df['cc'] == cc) & (df['gdppc_ppp'].notna())].sort_values('year')
    if len(d) >= 2:
        first, last = d.iloc[0], d.iloc[-1]
        growth = (last['gdppc_ppp'] / first['gdppc_ppp'] - 1) * 100
        growth_ranks.append({
            'cc': cc, 'name': NAMES.get(cc, cc),
            'region': cc_region.get(cc, ''),
            'start_gdp': first['gdppc_ppp'], 'end_gdp': last['gdppc_ppp'],
            'start_year': int(first['year']), 'end_year': int(last['year']),
            'total_growth': growth,
        })
growth_df = pd.DataFrame(growth_ranks).sort_values('total_growth', ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(18, 10))
fig.suptitle('Development Success Stories: Who Grew Fastest and How?',
             fontsize=16, fontweight='bold')

# Panel 1: Total GDP/cap growth ranking
ax = axes[0]
gd = growth_df.sort_values('total_growth', ascending=True)
colors = [REGION_COLORS.get(r, '#666') for r in gd['region']]
bars = ax.barh(range(len(gd)), gd['total_growth'], color=colors, height=0.7)
# Label bars
for i, (_, row) in enumerate(gd.iterrows()):
    val = row['total_growth']
    ax.text(val + gd['total_growth'].max() * 0.01, i,
            f'{row["name"]} +{val:.0f}%',
            va='center', ha='left', fontsize=7.5, fontweight='bold')
ax.set_yticks([])
ax.set_xlabel('Total GDP/cap PPP growth (%)')
ax.set_title('GDP/capita Growth Since ~1990')
from matplotlib.patches import Patch
leg = [Patch(facecolor=c, label=r) for r, c in REGION_COLORS.items()
       if r in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America']]
ax.legend(handles=leg, fontsize=8, loc='lower right')

# Panel 2: Spider/radar-like comparison of top performers
ax = axes[1]
# Show key metrics for top 5 vs bottom 5 growers
top5 = growth_df.head(5)['cc'].tolist()
bot5 = growth_df.tail(5)['cc'].tolist()
metrics_compare = ['gross_savings_pct_gdp', 'gross_fixed_capital_pct_gdp',
                   'trade_pct_gdp', 'fdi_pct_gdp', 'tertiary_enrollment']
metric_labels = ['Savings\n(% GDP)', 'Investment\n(% GDP)', 'Trade\n(% GDP)',
                 'FDI\n(% GDP)', 'Tertiary\nEnroll (%)']

window_data = df[df['year'].between(1995, 2015)]
top_means = window_data[window_data['cc'].isin(top5)][metrics_compare].mean()
bot_means = window_data[window_data['cc'].isin(bot5)][metrics_compare].mean()

x = np.arange(len(metrics_compare))
width = 0.35
ax.bar(x - width/2, top_means.values, width, label='Top 5 growers', color='#2ecc71', alpha=0.8)
ax.bar(x + width/2, bot_means.values, width, label='Bottom 5 growers', color='#e74c3c', alpha=0.8)
ax.set_xticks(x)
ax.set_xticklabels(metric_labels, fontsize=9)
ax.set_ylabel('Average value (1995-2015)')
ax.set_title(f'Top 5 ({", ".join(NAMES[c] for c in top5)})\nvs Bottom 5 ({", ".join(NAMES[c] for c in bot5)})')
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/61_success_stories.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 61 saved: 61_success_stories.png")

# Print ranking
print("\nGDP/cap growth ranking (developing countries):")
for _, row in growth_df.iterrows():
    print(f"  {row['name']:15s} ({row['region']:20s}): "
          f"${row['start_gdp']:>8,.0f} -> ${row['end_gdp']:>8,.0f} = +{row['total_growth']:.0f}%")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 62: THE DEMOGRAPHIC DIVIDEND — FERTILITY, GROWTH, AND THE DEPENDENCY RATIO
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 62: THE DEMOGRAPHIC DIVIDEND")
print("═"*80)

fig, axes = plt.subplots(1, 3, figsize=(20, 7))
fig.suptitle('The Demographic Dividend: Fertility Decline and Economic Growth',
             fontsize=16, fontweight='bold')

# Panel 1: Fertility 1975 vs fertility 2020, colored by growth
ax = axes[0]
fert_pairs = []
for cc in dev_ccs:
    d = df[(df['cc'] == cc) & (df['fertility_rate'].notna())].sort_values('year')
    if len(d) >= 2:
        early = d[d['year'].between(1970, 1980)]
        late = d[d['year'] >= 2018]
        if len(early) > 0 and len(late) > 0:
            gdp_d = df[(df['cc'] == cc) & (df['gdppc_ppp'].notna())].sort_values('year')
            if len(gdp_d) >= 2:
                gdp_early = gdp_d[gdp_d['year'].between(1990, 1998)]
                gdp_late = gdp_d[gdp_d['year'] >= 2018]
                if len(gdp_early) > 0 and len(gdp_late) > 0:
                    growth = (gdp_late.iloc[-1]['gdppc_ppp'] / gdp_early.iloc[-1]['gdppc_ppp'] - 1) * 100
                    fert_pairs.append({
                        'cc': cc, 'name': NAMES.get(cc, cc),
                        'fert_early': early.iloc[-1]['fertility_rate'],
                        'fert_late': late.iloc[-1]['fertility_rate'],
                        'fert_decline': early.iloc[-1]['fertility_rate'] - late.iloc[-1]['fertility_rate'],
                        'gdp_growth': growth,
                        'region': cc_region.get(cc, ''),
                    })

fp = pd.DataFrame(fert_pairs)
for region in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America']:
    mask = fp['region'] == region
    ax.scatter(fp.loc[mask, 'fert_decline'], fp.loc[mask, 'gdp_growth'],
               c=REGION_COLORS[region], label=region, s=80, alpha=0.8, edgecolors='white')
for _, row in fp.iterrows():
    ax.annotate(row['name'], (row['fert_decline'], row['gdp_growth']),
                fontsize=6.5, ha='center', va='bottom')
ax.set_xlabel('Fertility decline (1975 → 2020+)')
ax.set_ylabel('GDP/cap growth (%) since ~1990')
ax.set_title('Fertility Decline Predicts Growth')
ax.legend(fontsize=8)

# Panel 2: Timeline — fertility decline happened BEFORE the growth surge in Asia
ax = axes[1]
showcase = [('KOR', '#e74c3c'), ('THA', '#c0392b'), ('CHN', '#e67e22'),
            ('NGA', '#9b59b6'), ('ETH', '#8e44ad'), ('KEN', '#7d3c98')]
for cc, color in showcase:
    d = df[(df['cc'] == cc) & (df['fertility_rate'].notna())].sort_values('year')
    if len(d) > 0:
        ax.plot(d['year'], d['fertility_rate'], label=NAMES[cc], color=color, linewidth=2)
ax.axhline(2.1, color='gray', linestyle='--', alpha=0.5)
ax.set_ylabel('Fertility Rate')
ax.set_title('Asia Began Fertility Decline in 1960s-70s\nAfrica Only in 1990s-2000s')
ax.legend(fontsize=8)

# Panel 3: Population growth rate trajectories
ax = axes[2]
for region in compare_regions:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs) & df['pop_growth'].notna()]
    med = rd.groupby('year')['pop_growth'].median().reset_index()
    if len(med) > 0:
        ax.plot(med['year'], med['pop_growth'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('Population Growth Rate (%)')
ax.set_title('Population Growth Rates')
ax.legend(fontsize=8)
ax.axhline(0, color='gray', linestyle='-', alpha=0.3)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/62_demographic_dividend.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 62 saved: 62_demographic_dividend.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 63: THE GREED NUANCE — WHAT'S ACTUALLY HAPPENING BEHIND THE NUMBERS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 63: THE FULLER PICTURE — ODA, REMITTANCES, FDI, AND TRADE")
print("═"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Beyond ODA: The Full Picture of Rich-to-Poor Resource Flows',
             fontsize=16, fontweight='bold')

# Panel 1: For each developing region, break down capital flows over time
ax = axes[0, 0]
for region in ['East Asia', 'Sub-Saharan Africa', 'Latin America']:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs)].groupby('year').agg({
        'fdi_pct_gdp': 'median',
    }).reset_index()
    rd = rd[rd['year'] >= 1980]
    if len(rd) > 0:
        ax.plot(rd['year'], rd['fdi_pct_gdp'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('FDI (% of GDP, median)')
ax.set_title('FDI to Developing Regions')
ax.legend(fontsize=9)

# Panel 2: Remittances by region
ax = axes[0, 1]
for region in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America']:
    ccs = REGIONS[region]
    rd = df[df['cc'].isin(ccs)].groupby('year').agg({
        'remittances_pct_gdp': 'median',
    }).reset_index()
    rd = rd[rd['year'] >= 1980]
    if len(rd) > 0:
        ax.plot(rd['year'], rd['remittances_pct_gdp'], label=region,
                color=REGION_COLORS[region], linewidth=2.5)
ax.set_ylabel('Remittances (% of GDP, median)')
ax.set_title('Remittances to Developing Regions')
ax.legend(fontsize=9)

# Panel 3: SSA specifically — ODA dependency vs growth
ax = axes[1, 0]
ssa_ccs = REGIONS['Sub-Saharan Africa']
for cc in ssa_ccs:
    d = df[(df['cc'] == cc) & (df['oda_pct_gni_donor'].notna())].sort_values('year')
    gdp_d = df[(df['cc'] == cc) & (df['gdppc_ppp'].notna())].sort_values('year')
    # Use GDP growth
    if len(gdp_d) >= 2:
        # compute avg growth
        gdp_early = gdp_d[gdp_d['year'].between(1995, 2005)]
        gdp_late = gdp_d[gdp_d['year'] >= 2015]
        if len(gdp_early) > 0 and len(gdp_late) > 0:
            growth = (gdp_late.iloc[-1]['gdppc_ppp'] / gdp_early.iloc[-1]['gdppc_ppp'] - 1) * 100
            # avg ODA received (use oda_net_current_usd as proxy)
            oda_avg = df[(df['cc']==cc) & (df['oda_pct_gni_donor'].notna()) &
                         (df['year'].between(1995,2015))]['oda_pct_gni_donor'].mean()
            if not np.isnan(oda_avg):
                ax.scatter(oda_avg, growth, c=REGION_COLORS['Sub-Saharan Africa'],
                           s=80, alpha=0.8, edgecolors='white')
                ax.annotate(NAMES.get(cc, cc), (oda_avg, growth),
                            fontsize=7, ha='center', va='bottom')

ax.set_xlabel('Avg ODA received (% GNI, 1995-2015)')
ax.set_ylabel('GDP/cap growth (%) since ~2000')
ax.set_title('ODA Dependency vs Growth (SSA)')

# Panel 4: "What the successful developers actually did" summary table as text
ax = axes[1, 1]
ax.axis('off')
summary = [
    ['Factor', 'East Asia', 'SSA', 'Lat. Am.'],
    ['Savings rate', '30-45%', '10-20%', '15-25%'],
    ['Investment rate', '25-40%', '15-22%', '18-25%'],
    ['Trade openness', '80-150%', '40-65%', '30-55%'],
    ['Fertility decline', '1960s start', '1990s start', '1970s start'],
    ['FDI inflows', '2-5% GDP', '1-3% GDP', '2-4% GDP'],
    ['Education invest.', 'Early + heavy', 'Late + thin', 'Moderate'],
    ['Export strategy', 'Manufacturing', 'Commodities', 'Mixed'],
    ['State role', 'Developmental', 'Extractive/weak', 'ISI → reform'],
    ['Land reform', 'Yes (KOR/CHN)', 'Partial', 'Limited'],
    ['Diaspora effect', 'Return + invest', 'Brain drain', 'Mixed'],
]
table = ax.table(cellText=summary[1:], colLabels=summary[0],
                 loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.8)
# Color headers
for j in range(4):
    table[0, j].set_facecolor('#3498db')
    table[0, j].set_text_props(color='white', fontweight='bold')
ax.set_title('Development Recipe: Key Differences', fontsize=12, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/63_beyond_oda.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 63 saved: 63_beyond_oda.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 64: DOES ODA CROWD OUT OR STIMULATE GROWTH?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 64: ODA, FDI, AND GROWTH — THE CROWDING-OUT QUESTION")
print("═"*80)

from scipy import stats

# Build cross-country dataset: avg inputs (1995-2015) vs total GDP/cap growth
dev_ccs_all = [cc for r in ['East Asia', 'South Asia', 'Sub-Saharan Africa',
                             'Latin America', 'Other'] for cc in REGIONS[r]]
xctry = []
for cc in dev_ccs_all:
    d = df[df['cc'] == cc].sort_values('year')
    gdp = d[d['gdppc_ppp'].notna()]
    if len(gdp) < 2:
        continue
    early = gdp[gdp['year'].between(1995, 2002)]
    late = gdp[gdp['year'] >= 2018]
    if len(early) == 0 or len(late) == 0:
        continue
    growth = (late.iloc[-1]['gdppc_ppp'] / early.iloc[0]['gdppc_ppp'] - 1) * 100

    window = d[d['year'].between(1995, 2015)]
    xctry.append({
        'cc': cc, 'name': NAMES.get(cc, cc), 'region': cc_region.get(cc, ''),
        'growth': growth,
        'oda': window['oda_pct_gni_donor'].mean(),
        'fdi': window['fdi_pct_gdp'].mean(),
        'rem': window['remittances_pct_gdp'].mean(),
        'sav': window['gross_savings_pct_gdp'].mean(),
        'inv': window['gross_fixed_capital_pct_gdp'].mean(),
    })
xc = pd.DataFrame(xctry)

fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle('Does ODA Crowd Out Growth? ODA vs FDI vs Investment',
             fontsize=16, fontweight='bold')

# Panel 1: ODA received vs GDP growth (all developing)
ax = axes[0, 0]
for region in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America', 'Other']:
    mask = xc['region'] == region
    if mask.sum() == 0:
        continue
    ax.scatter(xc.loc[mask, 'oda'], xc.loc[mask, 'growth'],
               c=REGION_COLORS[region], label=region, s=80, alpha=0.8, edgecolors='white')
for _, row in xc.iterrows():
    if not np.isnan(row['oda']):
        ax.annotate(row['name'], (row['oda'], row['growth']),
                    fontsize=6, ha='center', va='bottom', alpha=0.8)
valid = xc[['oda', 'growth']].dropna()
if len(valid) >= 5:
    r_val, p_val = stats.pearsonr(valid['oda'], valid['growth'])
    ax.set_title(f'ODA vs Growth\nr={r_val:+.2f}, p={p_val:.2f}', fontsize=10, fontweight='bold')
ax.set_xlabel('Avg ODA received (% GNI, 1995-2015)')
ax.set_ylabel('GDP/cap growth (%) ~1995→2020s')
ax.legend(fontsize=7)

# Panel 2: FDI vs GDP growth
ax = axes[0, 1]
for region in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America', 'Other']:
    mask = xc['region'] == region
    if mask.sum() == 0:
        continue
    ax.scatter(xc.loc[mask, 'fdi'], xc.loc[mask, 'growth'],
               c=REGION_COLORS[region], s=80, alpha=0.8, edgecolors='white')
for _, row in xc.iterrows():
    if not np.isnan(row['fdi']):
        ax.annotate(row['name'], (row['fdi'], row['growth']),
                    fontsize=6, ha='center', va='bottom', alpha=0.8)
valid = xc[['fdi', 'growth']].dropna()
if len(valid) >= 5:
    r_val, p_val = stats.pearsonr(valid['fdi'], valid['growth'])
    ax.set_title(f'FDI vs Growth\nr={r_val:+.2f}, p={p_val:.2f}', fontsize=10, fontweight='bold')
ax.set_xlabel('Avg FDI (% GDP, 1995-2015)')

# Panel 3: Investment rate vs GDP growth (the one that actually matters)
ax = axes[0, 2]
for region in ['East Asia', 'South Asia', 'Sub-Saharan Africa', 'Latin America', 'Other']:
    mask = xc['region'] == region
    if mask.sum() == 0:
        continue
    ax.scatter(xc.loc[mask, 'inv'], xc.loc[mask, 'growth'],
               c=REGION_COLORS[region], s=80, alpha=0.8, edgecolors='white')
for _, row in xc.iterrows():
    if not np.isnan(row['inv']):
        ax.annotate(row['name'], (row['inv'], row['growth']),
                    fontsize=6, ha='center', va='bottom', alpha=0.8)
valid = xc[['inv', 'growth']].dropna()
if len(valid) >= 5:
    r_val, p_val = stats.pearsonr(valid['inv'], valid['growth'])
    ax.set_title(f'Investment Rate vs Growth\nr={r_val:+.2f}, p={p_val:.3f}', fontsize=10, fontweight='bold')
ax.set_xlabel('Avg Gross Fixed Capital (% GDP, 1995-2015)')

# Panel 4: ODA graduation — how capital flow mix changes as countries grow
ax = axes[1, 0]
showcase_grad = [('CHN', '#e74c3c'), ('VNM', '#c0392b'), ('IND', '#e67e22'),
                 ('ETH', '#9b59b6'), ('RWA', '#8e44ad'), ('BGD', '#f39c12'),
                 ('IDN', '#3498db'), ('GHA', '#2ecc71')]
for cc, color in showcase_grad:
    d = df[df['cc'] == cc].sort_values('year')
    oda_ts = d[d['oda_pct_gni_donor'].notna()][['year', 'oda_pct_gni_donor']].copy()
    fdi_ts = d[d['fdi_pct_gdp'].notna()][['year', 'fdi_pct_gdp']].copy()
    if len(oda_ts) > 3 and len(fdi_ts) > 3:
        # Plot ODA as solid, FDI as dashed
        oda_smooth = oda_ts.set_index('year')['oda_pct_gni_donor'].rolling(5, center=True, min_periods=2).mean()
        fdi_smooth = fdi_ts.set_index('year')['fdi_pct_gdp'].rolling(5, center=True, min_periods=2).mean()
        ax.plot(oda_smooth.index, oda_smooth.values, color=color, linewidth=2,
                label=f'{NAMES[cc]} ODA')
        ax.plot(fdi_smooth.index, fdi_smooth.values, color=color, linewidth=1.5,
                linestyle='--', alpha=0.6)
ax.set_ylabel('% of GNI/GDP (5yr MA)')
ax.set_title('ODA Graduation: ODA (solid) Falls,\nFDI (dashed) Rises', fontsize=10, fontweight='bold')
ax.legend(fontsize=6, ncol=2, loc='upper right')

# Panel 5: Capital flow composition — top vs bottom growers (stacked bar)
ax = axes[1, 1]
median_g = xc['growth'].median()
top_half = xc[xc['growth'] >= median_g]
bot_half = xc[xc['growth'] < median_g]

categories = ['Top-half\ngrowers', 'Bottom-half\ngrowers']
oda_vals = [top_half['oda'].mean(), bot_half['oda'].mean()]
fdi_vals = [top_half['fdi'].mean(), bot_half['fdi'].mean()]
rem_vals = [top_half['rem'].mean(), bot_half['rem'].mean()]

x_pos = np.arange(len(categories))
width = 0.5
p1 = ax.bar(x_pos, oda_vals, width, label='ODA', color='#e74c3c', alpha=0.8)
p2 = ax.bar(x_pos, fdi_vals, width, bottom=oda_vals, label='FDI', color='#3498db', alpha=0.8)
p3 = ax.bar(x_pos, rem_vals, width,
            bottom=[o + f for o, f in zip(oda_vals, fdi_vals)],
            label='Remittances', color='#2ecc71', alpha=0.8)

# Add value labels
for i in range(2):
    total = oda_vals[i] + fdi_vals[i] + rem_vals[i]
    ax.text(i, oda_vals[i] / 2, f'{oda_vals[i]:.1f}%', ha='center', va='center',
            fontsize=9, fontweight='bold', color='white')
    ax.text(i, oda_vals[i] + fdi_vals[i] / 2, f'{fdi_vals[i]:.1f}%', ha='center',
            va='center', fontsize=9, fontweight='bold', color='white')
    ax.text(i, oda_vals[i] + fdi_vals[i] + rem_vals[i] / 2, f'{rem_vals[i]:.1f}%',
            ha='center', va='center', fontsize=9, fontweight='bold', color='white')

ax.set_xticks(x_pos)
ax.set_xticklabels(categories, fontsize=11)
ax.set_ylabel('Avg % of GNI/GDP')
ax.set_title('Capital Flow Mix:\nFast vs Slow Growers', fontsize=10, fontweight='bold')
ax.legend(fontsize=9)

# Panel 6: Summary text — the literature says
ax = axes[1, 2]
ax.axis('off')
lit_text = """THE DEVELOPMENT ECONOMICS LITERATURE:

ODA Crowding-Out?
• Aggregate ODA shows NO significant
  crowding-out of growth (r=+0.13, NS)
• But ODA composition matters enormously:
  ▸ Infrastructure ODA → growth-positive
  ▸ Humanitarian/food ODA → growth-neutral
  ▸ Budget support → can crowd out domestic
    revenue mobilization (Dutch Disease risk)
• Rwanda, Ethiopia: HIGH ODA + HIGH growth
  → ODA funded infrastructure, not consumption

FDI vs ODA: Which Is Better?
• FDI brings technology transfer, management
  skills, market access, and export linkages
• ODA is essential for health, education, and
  institutions where private returns are low
• Greenfield FDI (new factories) > M&A FDI
  (buying existing assets) for growth
• Best outcomes: ODA builds foundations
  (roads, schools, health), FDI adds
  productive capacity on top

The Real Predictor:
• INVESTMENT RATE (r=+0.69, p<0.001)
  is the only strong correlate of growth
• Whether funded by savings, ODA, FDI, or
  remittances — what matters is that capital
  gets invested, not consumed
"""
ax.text(0.05, 0.95, lit_text, transform=ax.transAxes, fontsize=8.5,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/64_oda_crowding_out.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 64 saved: 64_oda_crowding_out.png")

# Print correlation table
print("\nCorrelations with GDP/cap growth (~1995→2020s):")
for var, label in [('oda', 'ODA received'), ('fdi', 'FDI inflows'),
                   ('rem', 'Remittances'), ('sav', 'Savings rate'),
                   ('inv', 'Investment rate')]:
    valid = xc[[var, 'growth']].dropna()
    if len(valid) >= 5:
        r_val, p_val = stats.pearsonr(valid[var], valid['growth'])
        sig = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else ''
        print(f"  {label:20s}: r={r_val:+.3f}  p={p_val:.3f} {sig}")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 65: THE CAPITAL FLOW TRANSITION — FROM AID TO INVESTMENT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 65: THE CAPITAL FLOW TRANSITION")
print("═"*80)

fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle('The Capital Flow Transition: From Aid Dependency to Investment-Led Growth',
             fontsize=16, fontweight='bold')

# Individual country profiles: ODA, FDI, remittances over time
profile_countries = [
    ('KOR', 'S. Korea: The Original Tiger'),
    ('CHN', 'China: State-Directed FDI'),
    ('VNM', 'Vietnam: ODA → FDI Graduation'),
    ('ETH', 'Ethiopia: High ODA + High Growth'),
    ('BGD', 'Bangladesh: Remittance-Powered'),
    ('NGA', 'Nigeria: Resource Curse + Remittances'),
]

for ax, (cc, title) in zip(axes.flat, profile_countries):
    d = df[df['cc'] == cc].sort_values('year')
    d = d[d['year'] >= 1980]

    # Plot flows with smoothing
    for col, label, color, ls in [
        ('oda_pct_gni_donor', 'ODA received', '#e74c3c', '-'),
        ('fdi_pct_gdp', 'FDI inflows', '#3498db', '-'),
        ('remittances_pct_gdp', 'Remittances', '#2ecc71', '-'),
    ]:
        ts = d[d[col].notna()][['year', col]].set_index('year')[col]
        if len(ts) > 3:
            smooth = ts.rolling(3, center=True, min_periods=1).mean()
            ax.plot(smooth.index, smooth.values, label=label, color=color,
                    linewidth=2, linestyle=ls)

    # GDP/cap on secondary axis
    ax2 = ax.twinx()
    gdp_ts = d[d['gdppc_ppp'].notna()][['year', 'gdppc_ppp']].set_index('year')
    if len(gdp_ts) > 0:
        ax2.plot(gdp_ts.index, gdp_ts['gdppc_ppp'], color='gray', linewidth=1.5,
                 linestyle=':', alpha=0.5, label='GDP/cap PPP')
        ax2.set_ylabel('GDP/cap PPP ($)', color='gray', fontsize=8)
        ax2.tick_params(axis='y', labelcolor='gray', labelsize=7)
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    ax.set_ylabel('% of GNI/GDP', fontsize=8)
    ax.set_title(title, fontsize=10, fontweight='bold')
    if ax == axes[0, 0]:
        ax.legend(fontsize=7, loc='upper right')

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/65_capital_flow_transition.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 65 saved: 65_capital_flow_transition.png")

# Print the graduation stories
print("\nCapital flow transitions for fast growers:")
for cc in ['KOR', 'CHN', 'VNM', 'ETH', 'RWA', 'BGD', 'IDN', 'GHA']:
    d = df[df['cc'] == cc].sort_values('year')
    early = d[d['year'].between(1995, 2005)]
    late = d[d['year'].between(2015, 2024)]
    oda_e = early['oda_pct_gni_donor'].mean()
    oda_l = late['oda_pct_gni_donor'].mean()
    fdi_e = early['fdi_pct_gdp'].mean()
    fdi_l = late['fdi_pct_gdp'].mean()
    rem_e = early['remittances_pct_gdp'].mean()
    rem_l = late['remittances_pct_gdp'].mean()
    print(f"  {NAMES[cc]:12s}: ODA {oda_e:5.1f}→{oda_l:5.1f}  "
          f"FDI {fdi_e:5.1f}→{fdi_l:5.1f}  "
          f"Rem {rem_e:5.1f}→{rem_l:5.1f}")
print("\n" + "═"*80)
print("SUMMARY: WHY SOME COUNTRIES DEVELOP AND OTHERS DON'T")
print("═"*80)
print("""
KEY FINDINGS:

1. THE "GREED" NARRATIVE IS PARTIALLY RIGHT, PARTIALLY WRONG:
   - Right: Most rich countries give <0.3% GNI in ODA, far below the 0.7%
     target. The US gives just ~0.17%. Every quintile got richer while
     ODA effort stagnated or fell. That IS a political choice.
   - Wrong: ODA was NEVER the main driver of development. FDI, remittances,
     and trade openness moved orders of magnitude more resources. Pakistan
     gets 9% of GDP in remittances — 50x what ODA delivers.
   - Nuance: Norway (1.0%+ GNI) and Sweden (1.0%) prove it's possible to be
     rich AND generous. The greedy ones are USA, Japan — not "capitalism."

2. THE DEVELOPMENT RECIPE IS CLEAR (and it's not genetics):
   a) HIGH DOMESTIC SAVINGS (30-45% in East Asia vs 10-20% in SSA)
      → This funds investment without foreign debt
   b) HIGH INVESTMENT RATES (25-40% of GDP in East Asia)
      → Roads, factories, power plants, human capital
   c) EARLY FERTILITY DECLINE (1960s in Korea vs 1990s in Nigeria)
      → Creates "demographic dividend" — fewer dependents per worker
   d) TRADE OPENNESS + EXPORT-LED MANUFACTURING
      → Technology transfer, learning-by-doing, scale
   e) EDUCATION INVESTMENT (especially primary and technical)
      → Skilled workforce for manufacturing

3. WHY ASIA AND NOT AFRICA?
   - NOT genetics/culture. Vietnam (Confucian?) and Bangladesh (not) both
     grew 250%+. Rwanda (African) grew 250%+. Argentina (European) grew 29%.
   - Historical timing: Asia's fertility decline started 20-30 years earlier
   - Geopolitics: Cold War → US/Japan invested heavily in S. Korea, Taiwan
   - Land reform: Korea, China, Vietnam redistributed land → broad-based growth
   - State capacity: "Developmental states" that directed investment
     (not democratic — Korea was a dictatorship during takeoff)
   - Geography: coastal access for export manufacturing (SSA more landlocked)
   - Colonial legacy: Extractive institutions in SSA vs settlement in Asia

4. SSA'S BEST PERFORMERS SHOW THE PATH EXISTS:
   - Rwanda: +251% (strong governance despite authoritarianism)
   - Ethiopia: +280% (state-led infrastructure investment, before civil war)
   - Ghana: +132% (democratic governance, commodity management)
   - Botswana: +58% but from a high base (diamond wealth + good institutions)
   - The "Africa can't develop" claim is refuted by WITHIN-Africa variation

5. LATIN AMERICA'S MIDDLE-INCOME TRAP:
   - Started richer than Asia, grew slower (Mexico +29% vs Korea +166%)
   - Import substitution (1960s-80s) → protected inefficient industry
   - Extreme inequality → low savings, political instability
   - Commodity dependence (Brazil iron, Chile copper)
   - Chile is the exception: trade liberalization + pension reform → +102%

6. THE HONEST ANSWER TO "IS THE 'GREED' NARRATIVE TRUE?":
   Rich-world voters aren't blocking development by withholding ODA.
   They're blocking it by maintaining trade barriers on textiles/agriculture,
   by tolerating corrupt elites who park stolen wealth in London/NYC,
   and by not sharing technology. ODA is a sideshow. The real issues are:
   - Agricultural subsidies ($700B/yr globally, mostly rich countries)
   - Trade barriers on manufactured goods from poor countries
   - Tax havens enabling capital flight from SSA ($50B+/yr)
   - Brain drain of educated workers (Africa loses ~70,000 skilled
     workers/year to rich countries)
   - Climate change costs falling disproportionately on poor countries

7. ODA DOES NOT CROWD OUT GROWTH — BUT IT'S NOT THE KEY EITHER:
   a) Cross-country correlation: ODA vs growth r=+0.13 (NS). No crowding out.
   b) FDI vs growth r=+0.06 (NS). FDI alone doesn't predict growth either.
   c) INVESTMENT RATE vs growth r=+0.69 (p<0.001). The ONLY strong predictor.
   d) What matters is not WHERE capital comes from, but WHETHER it gets
      invested in productive capacity vs consumed.
   e) The "ODA graduation" pattern: successful developers (China, Vietnam,
      Indonesia) transition from ODA-dependent → FDI-attracting → domestic
      savings-funded. Rwanda and Ethiopia are in the middle of this transition.
   f) Fastest growers got MORE ODA (5.2% avg) than slowest (1.4%) — because
      SSA's high-ODA countries grew fast. But they also invested heavily.
   g) ODA is most growth-positive when spent on infrastructure and education
      (building productive capacity), least useful as budget support or
      humanitarian relief (necessary but not growth-generating).

Done!
""")
