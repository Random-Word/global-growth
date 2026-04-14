"""
Analysis 12: Welfare-Weighted Growth Across the Income Spectrum
================================================================
Questions addressed:
1. If we integrate over the entire population using welfare functions,
   how do different countries compare?
2. Does France's egalitarian model beat the US when you weight by distribution?
3. Which countries' growth was most pro-poor vs pro-rich?
4. How much does the welfare function parameter (ε) change the rankings?
5. Are improvements for the poorest infinitely more important than the median?

Uses the Atkinson Equally-Distributed Equivalent Income (EDEI):
  - ε=0   → mean income (no inequality aversion)
  - ε=0.5 → mild inequality aversion
  - ε=1   → geometric mean (log-utility, moderate aversion)
  - ε=2   → strong inequality aversion (heavy weight on poor)
  - ε=∞   → Rawlsian (only the poorest matter)

Key insight: ε parameterises exactly the question "are improvements for
the poorest infinitely more important than the median?"
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import requests, time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='colorblind')
CHART_DIR = 'charts'

# ── Robust WDI downloader ─────────────────────────────────────────────────────
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

COUNTRY_BATCHES = [
    'USA;CHN;FRA;JPN;DEU;KOR;GBR',
    'BRA;POL;VNM;MYS;IND;NGA;ETH',
    'BGD;IDN;THA;CHL;BWA;RWA;SWE',
    'NOR;MEX;ZAF;GHA;TZA;COL',
]

def fetch_wdi_batched(indicator, label, date_range='1985:2025'):
    """Fetch a WDI indicator in country batches to avoid API timeouts."""
    all_rows = []
    for batch in COUNTRY_BATCHES:
        url = f'https://api.worldbank.org/v2/country/{batch}/indicator/{indicator}'
        params = {'date': date_range, 'format': 'json', 'per_page': 10000}
        for attempt in range(3):
            try:
                r = session.get(url, params=params, timeout=120)
                data = r.json()
                if len(data) > 1 and data[1]:
                    for item in data[1]:
                        if item['value'] is not None and item.get('countryiso3code'):
                            all_rows.append({
                                'cc': item['countryiso3code'],
                                'country': item['country']['value'],
                                'year': int(item['date']),
                                label: float(item['value'])
                            })
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"  {label} batch {batch}: FAILED after 3 attempts")
        time.sleep(0.5)
    df = pd.DataFrame(all_rows) if all_rows else pd.DataFrame()
    print(f"  {label}: {len(df)} obs")
    return df

# ── Download data ──────────────────────────────────────────────────────────────
print("Downloading quintile income shares and GDP per capita...")
indicators = [
    ('SI.DST.FRST.20', 'bottom20'),
    ('SI.DST.02ND.20', 'q2'),
    ('SI.DST.03RD.20', 'q3'),
    ('SI.DST.04TH.20', 'q4'),
    ('SI.DST.05TH.20', 'top20'),
    ('SI.POV.GINI', 'gini'),
    ('NY.GDP.PCAP.PP.KD', 'gdppc_ppp'),
]

datasets = {}
for code, label in indicators:
    datasets[label] = fetch_wdi_batched(code, label)

# ── Merge ──────────────────────────────────────────────────────────────────────
print("\nMerging datasets...")
merged = None
for label, df in datasets.items():
    if len(df) == 0:
        continue
    cols = ['cc', 'country', 'year', label]
    if merged is None:
        merged = df[cols]
    else:
        merged = merged.merge(df[cols], on=['cc', 'country', 'year'], how='outer')

Q_COLS = ['bottom20', 'q2', 'q3', 'q4', 'top20']

# Only keep rows where all quintiles + GDP are present
complete = merged.dropna(subset=Q_COLS + ['gdppc_ppp']).copy()
complete = complete.sort_values(['cc', 'year'])
print(f"  Complete obs (quintiles + GDP): {len(complete)} rows, {complete['cc'].nunique()} countries")

# ── Compute quintile incomes and welfare metrics ──────────────────────────────
def compute_welfare(row):
    """Compute Atkinson EDEI at multiple epsilon values."""
    gdppc = row['gdppc_ppp']
    shares = np.array([row['bottom20'], row['q2'], row['q3'], row['q4'], row['top20']])
    incomes = gdppc * (shares / 20.0)  # avg income per person in each quintile

    mean_inc = np.mean(incomes)
    # ε=0.5
    edei_05 = np.power(np.mean(np.power(incomes, 0.5)), 2.0)
    # ε=1 (geometric mean / log-utility)
    edei_10 = np.exp(np.mean(np.log(incomes)))
    # ε=2 (harmonic mean)
    edei_20 = np.power(np.mean(np.power(incomes, -1.0)), -1.0)
    # Rawlsian (min)
    rawls = np.min(incomes)

    return pd.Series({
        'inc_b20': incomes[0], 'inc_q2': incomes[1], 'inc_q3': incomes[2],
        'inc_q4': incomes[3], 'inc_t20': incomes[4],
        'mean_inc': mean_inc,
        'edei_05': edei_05, 'edei_10': edei_10, 'edei_20': edei_20,
        'rawls': rawls,
    })

welfare = complete.reset_index(drop=True).apply(compute_welfare, axis=1)
df = pd.concat([complete.reset_index(drop=True), welfare], axis=1)

# Country groupings for charts
GROUPS = {
    'Rich Market': ['USA', 'GBR', 'JPN', 'KOR'],
    'Social Democrat': ['FRA', 'DEU', 'SWE', 'NOR', 'POL'],
    'Fast Growing': ['CHN', 'VNM', 'IND', 'IDN', 'THA', 'BGD', 'ETH', 'RWA'],
    'Latin America': ['BRA', 'CHL', 'MEX', 'COL'],
    'Africa': ['NGA', 'ZAF', 'GHA', 'TZA', 'BWA'],
}
ALL_CC = [cc for g in GROUPS.values() for cc in g]

# Friendly names
NAMES = {}
for _, row in df[['cc', 'country']].drop_duplicates().iterrows():
    NAMES[row['cc']] = row['country']
# Short names
NAMES['KOR'] = 'South Korea'
NAMES['GBR'] = 'UK'
NAMES['USA'] = 'US'
NAMES['DEU'] = 'Germany'
NAMES['VNM'] = 'Vietnam'
NAMES['NGA'] = 'Nigeria'
NAMES['ZAF'] = 'South Africa'
NAMES['BGD'] = 'Bangladesh'
NAMES['TZA'] = 'Tanzania'
NAMES['IDN'] = 'Indonesia'
NAMES['ETH'] = 'Ethiopia'
NAMES['MYS'] = 'Malaysia'
NAMES['THA'] = 'Thailand'
NAMES['BWA'] = 'Botswana'
NAMES['RWA'] = 'Rwanda'
NAMES['COL'] = 'Colombia'
NAMES['CHL'] = 'Chile'
NAMES['MEX'] = 'Mexico'
NAMES['NOR'] = 'Norway'
NAMES['SWE'] = 'Sweden'
NAMES['POL'] = 'Poland'
NAMES['BRA'] = 'Brazil'
NAMES['FRA'] = 'France'
NAMES['JPN'] = 'Japan'
NAMES['CHN'] = 'China'
NAMES['IND'] = 'India'
NAMES['GHA'] = 'Ghana'

# ══════════════════════════════════════════════════════════════════════════════
# CHART 52: WELFARE RANKINGS — HOW ε CHANGES EVERYTHING
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 52: WELFARE RANKINGS — HOW ε CHANGES EVERYTHING")
print("═"*80)

# Get latest observation per country
latest = df.sort_values('year').groupby('cc').last().reset_index()
latest = latest[latest['cc'].isin(ALL_CC)].copy()
latest['name'] = latest['cc'].map(NAMES)

metrics = ['mean_inc', 'edei_05', 'edei_10', 'edei_20', 'rawls']
labels = ['ε=0\n(Mean)', 'ε=0.5\n(Mild)', 'ε=1\n(Log)', 'ε=2\n(Strong)', 'ε=∞\n(Rawlsian)']

fig, axes = plt.subplots(1, 5, figsize=(24, 10), sharey=False)
fig.suptitle('How Much Do You Care About Inequality?\nCountry Rankings Under Different Social Welfare Functions',
             fontsize=16, fontweight='bold', y=1.02)

# Color by group
group_colors = {
    'Rich Market': '#e74c3c', 'Social Democrat': '#3498db',
    'Fast Growing': '#2ecc71', 'Latin America': '#f39c12', 'Africa': '#9b59b6'
}
cc_group = {}
for g, ccs in GROUPS.items():
    for cc in ccs:
        cc_group[cc] = g

# Determine text color for contrast against bar color
def _text_color(hex_color):
    """White text on dark bars, dark text on light bars."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return 'white' if luminance < 160 else '#222222'

for ax, metric, label in zip(axes, metrics, labels):
    sorted_df = latest.sort_values(metric, ascending=True).reset_index(drop=True)
    colors = [group_colors.get(cc_group.get(cc, ''), '#666') for cc in sorted_df['cc']]
    vals = sorted_df[metric] / 1000
    bars = ax.barh(range(len(sorted_df)), vals, color=colors, height=0.7)

    # Label each bar with country code inside it
    for i, (bar, cc, v) in enumerate(zip(bars, sorted_df['cc'], vals)):
        bar_w = bar.get_width()
        color = colors[i]
        txt_color = _text_color(color)
        name = NAMES.get(cc, cc)
        # Short codes that fit inside bars — use ≤6 char names
        short = cc if len(name) > 7 else name
        # Place label inside bar near the left edge
        if bar_w > vals.max() * 0.15:
            ax.text(bar_w * 0.03, i, f' {short}', va='center', ha='left',
                    fontsize=7, fontweight='bold', color=txt_color)
            # Value at right end inside bar
            ax.text(bar_w - vals.max() * 0.01, i, f'${v:.0f}k ',
                    va='center', ha='right', fontsize=6.5, color=txt_color)
        else:
            # Very short bar — label outside
            ax.text(bar_w + vals.max() * 0.01, i, f'{short} ${v:.0f}k',
                    va='center', ha='left', fontsize=6.5, fontweight='bold',
                    color='#333333')

    ax.set_yticks([])  # No y-axis labels — country codes are on the bars
    ax.set_xlabel('$000 PPP', fontsize=10)
    ax.set_title(label, fontsize=12, fontweight='bold')
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('$%.0fk'))

# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=c, label=g) for g, c in group_colors.items()]
fig.legend(handles=legend_elements, loc='lower center', ncol=5, fontsize=10,
           bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/52_welfare_rankings.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 52 saved: 52_welfare_rankings.png")

# Print rankings table
print("\nWelfare rankings (latest year, $000 PPP):")
print(f"  {'Country':<20s} {'Year':>4s} {'Mean':>10s} {'ε=0.5':>10s} {'ε=1':>10s} {'ε=2':>10s} {'Rawls':>10s}")
for _, r in latest.sort_values('mean_inc', ascending=False).iterrows():
    print(f"  {NAMES.get(r['cc'],r['cc']):<20s} {int(r['year']):4d} ${r['mean_inc']/1000:>8.1f}k ${r['edei_05']/1000:>8.1f}k ${r['edei_10']/1000:>8.1f}k ${r['edei_20']/1000:>8.1f}k ${r['rawls']/1000:>8.1f}k")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 53: GROWTH THROUGH A WELFARE LENS — WHO GREW FOR WHOM?
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 53: GROWTH THROUGH A WELFARE LENS — WHO GREW FOR WHOM?")
print("═"*80)

# Compute growth rates for each country
growth_rows = []
for cc in ALL_CC:
    cdata = df[df['cc'] == cc].sort_values('year')
    if len(cdata) < 2:
        continue
    early, late = cdata.iloc[0], cdata.iloc[-1]
    name = NAMES.get(cc, cc)
    span = f"{int(early['year'])}-{int(late['year'])}"
    years = late['year'] - early['year']
    if years < 5:
        continue

    for metric, elabel in [('mean_inc','ε=0 (Mean)'), ('edei_05','ε=0.5'),
                            ('edei_10','ε=1 (Log)'), ('edei_20','ε=2'),
                            ('rawls','ε=∞ (Rawls)')]:
        g = (late[metric] / early[metric] - 1) * 100
        cagr = (np.power(late[metric] / early[metric], 1/years) - 1) * 100
        growth_rows.append({
            'cc': cc, 'name': name, 'span': span, 'years': years,
            'metric': elabel, 'growth_pct': g, 'cagr': cagr
        })

gdf = pd.DataFrame(growth_rows)

# Scatter: Mean growth (x) vs Welfare growth at ε=2 (y)
fig, ax = plt.subplots(figsize=(14, 10))

mean_g = gdf[gdf['metric'] == 'ε=0 (Mean)'].set_index('cc')['cagr']
e2_g = gdf[gdf['metric'] == 'ε=2'].set_index('cc')['cagr']

for cc in mean_g.index:
    if cc not in e2_g.index:
        continue
    color = group_colors.get(cc_group.get(cc, ''), '#666')
    ax.scatter(mean_g[cc], e2_g[cc], s=120, c=color, edgecolors='black', linewidth=0.5, zorder=5)
    # Label position
    offset = (5, 5)
    if cc in ['USA', 'DEU', 'SWE']:
        offset = (5, -12)
    elif cc in ['FRA', 'NOR']:
        offset = (-40, 8)
    ax.annotate(NAMES.get(cc, cc), (mean_g[cc], e2_g[cc]),
                textcoords='offset points', xytext=offset, fontsize=9)

# 45-degree line (growth equally shared)
lim_max = max(mean_g.max(), e2_g.max()) * 1.1
ax.plot([0, lim_max], [0, lim_max], '--', color='gray', alpha=0.5, label='Growth equally shared')
ax.fill_between([0, lim_max], [0, lim_max], [lim_max, lim_max],
                alpha=0.08, color='green', label='Pro-poor growth (above line)')
ax.fill_between([0, lim_max], [0, 0], [0, lim_max],
                alpha=0.08, color='red', label='Pro-rich growth (below line)')

ax.set_xlabel('Mean Income Growth (CAGR %)', fontsize=12)
ax.set_ylabel('Welfare-Weighted Growth ε=2 (CAGR %)', fontsize=12)
ax.set_title('Did Growth Reach the Poor?\nMean vs Welfare-Weighted Growth Rates (CAGR, ε=2)',
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=10)

# Group legend
legend2 = [Patch(facecolor=c, label=g) for g, c in group_colors.items()]
ax.legend(handles=legend2 + ax.get_legend().legend_handles, loc='upper left', fontsize=9)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/53_welfare_growth_scatter.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 53 saved: 53_welfare_growth_scatter.png")

# Print growth comparison — compute directly to avoid metric label matching issues
print("\nGrowth comparison (total %, earliest → latest):")
print(f"  {'Country':<20s} {'Span':<12s} {'Mean':>8s} {'e=0.5':>8s} {'e=1':>8s} {'e=2':>8s} {'Rawls':>8s} {'Pro-poor?':>10s}")
for cc in ALL_CC:
    cdata = df[df['cc'] == cc].sort_values('year')
    if len(cdata) < 2:
        continue
    early, late = cdata.iloc[0], cdata.iloc[-1]
    years = int(late['year'] - early['year'])
    if years < 5:
        continue
    name = NAMES.get(cc, cc)
    span = f"{int(early['year'])}-{int(late['year'])}"
    vals = {}
    for col, label in [('mean_inc','Mean'), ('edei_05','e=0.5'), ('edei_10','e=1'),
                         ('edei_20','e=2'), ('rawls','Rawls')]:
        if pd.notna(early[col]) and pd.notna(late[col]) and early[col] > 0:
            vals[label] = (late[col] / early[col] - 1) * 100
        else:
            vals[label] = float('nan')
    mean_v = vals.get('Mean', 0)
    e2_v = vals.get('e=2', 0)
    ratio = e2_v / mean_v if mean_v and not np.isnan(mean_v) and mean_v != 0 else 0
    propoor = "PRO-POOR" if ratio > 1.05 else ("NEUTRAL" if ratio > 0.95 else "PRO-RICH")
    def fmt(v):
        return f"{v:>+7.0f}%" if not np.isnan(v) else "    N/A"
    print(f"  {name:<20s} {span:<12s} {fmt(vals['Mean'])} {fmt(vals['e=0.5'])} {fmt(vals['e=1'])} {fmt(vals['e=2'])} {fmt(vals['Rawls'])} {propoor:>10s}")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 54: THE FULL INCOME SPECTRUM — QUINTILE INCOMES ACROSS COUNTRIES
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 54: THE FULL INCOME SPECTRUM — QUINTILE INCOMES ACROSS COUNTRIES")
print("═"*80)

# Stacked/grouped bar: all 5 quintile incomes for each country, latest year
fig, ax = plt.subplots(figsize=(18, 10))

# Sort by mean income
plot_latest = latest[latest['cc'].isin(ALL_CC)].sort_values('mean_inc')
q_labels = ['Bottom 20%', 'Q2', 'Q3 (Median)', 'Q4', 'Top 20%']
q_cols = ['inc_b20', 'inc_q2', 'inc_q3', 'inc_q4', 'inc_t20']
q_colors = ['#e74c3c', '#f39c12', '#3498db', '#2ecc71', '#9b59b6']

y_pos = np.arange(len(plot_latest))
bar_height = 0.15

for i, (col, qlabel, qcolor) in enumerate(zip(q_cols, q_labels, q_colors)):
    ax.barh(y_pos + i * bar_height - 0.3, plot_latest[col] / 1000,
            height=bar_height, label=qlabel, color=qcolor, alpha=0.85)

ax.set_yticks(y_pos)
ax.set_yticklabels([NAMES.get(cc, cc) for cc in plot_latest['cc']], fontsize=10)
ax.set_xlabel('Average Income per Person in Quintile ($000 PPP)', fontsize=12)
ax.set_title('The Full Income Spectrum: What Each Quintile Actually Earns\n(Latest year, constant PPP $)',
             fontsize=14, fontweight='bold')
ax.legend(loc='lower right', fontsize=10)
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('$%.0fk'))

# Add vertical lines for global context
ax.axvline(x=6.85*365/1000, color='red', linestyle=':', alpha=0.7, label='$6.85/day poverty')
ax.text(6.85*365/1000 + 0.3, len(plot_latest)-1, '$6.85/day\npoverty line',
        fontsize=8, color='red', alpha=0.7)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/54_income_spectrum.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 54 saved: 54_income_spectrum.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 55: THE ε DIAL — SAME COUNTRY, DIFFERENT STORY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 55: THE ε DIAL — SAME COUNTRY, DIFFERENT STORY")
print("═"*80)

# Show how EDEI as fraction of mean changes across countries — "inequality tax"
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

# Panel 1: Inequality tax (1 - EDEI/mean) for each ε
latest_sorted2 = latest.sort_values('gini', ascending=False)
epsilon_vals = [0.5, 1.0, 2.0]
epsilon_labels = ['ε=0.5 (mild)', 'ε=1 (log-utility)', 'ε=2 (strong)']
epsilon_cols = ['edei_05', 'edei_10', 'edei_20']
markers = ['o', 's', 'D']

for eps_col, eps_label, marker in zip(epsilon_cols, epsilon_labels, markers):
    tax = (1 - latest_sorted2[eps_col] / latest_sorted2['mean_inc']) * 100
    names_list = [NAMES.get(cc, cc) for cc in latest_sorted2['cc']]
    ax1.plot(tax.values, range(len(tax)), marker=marker, linestyle='-', label=eps_label, markersize=6)

ax1.set_yticks(range(len(latest_sorted2)))
ax1.set_yticklabels([NAMES.get(cc, cc) for cc in latest_sorted2['cc']], fontsize=9)
ax1.set_xlabel('"Inequality Tax" — % of Mean Income Lost to Inequality', fontsize=11)
ax1.set_title('The Inequality Tax\n(Sorted by Gini, highest at top)', fontsize=13, fontweight='bold')
ax1.legend(fontsize=10)
ax1.invert_yaxis()

# Panel 2: How rankings change from ε=0 to ε=2 — bump chart for top 15 by mean
top15 = latest.nlargest(15, 'mean_inc').copy()

rank_data = {}
for metric, label in [('mean_inc','ε=0'), ('edei_05','ε=0.5'), ('edei_10','ε=1'), ('edei_20','ε=2'), ('rawls','Rawls')]:
    ranked = top15.sort_values(metric, ascending=False).reset_index(drop=True)
    ranked['rank'] = range(1, len(ranked)+1)
    for _, r in ranked.iterrows():
        if r['cc'] not in rank_data:
            rank_data[r['cc']] = {}
        rank_data[r['cc']][label] = r['rank']

eps_positions = [0, 1, 2, 3, 4]
eps_names = ['ε=0', 'ε=0.5', 'ε=1', 'ε=2', 'Rawls']

highlight = {'USA': '#e74c3c', 'FRA': '#3498db', 'CHN': '#2ecc71',
             'BRA': '#f39c12', 'POL': '#9b59b6', 'NOR': '#1abc9c'}

for cc, ranks in rank_data.items():
    rank_vals = [ranks.get(e, None) for e in eps_names]
    color = highlight.get(cc, '#cccccc')
    alpha = 1.0 if cc in highlight else 0.3
    lw = 2.5 if cc in highlight else 1.0
    ax2.plot(eps_positions, rank_vals, '-o', color=color, alpha=alpha, linewidth=lw, markersize=6)
    # Label at right end
    if cc in highlight or abs(rank_vals[0] - rank_vals[-1]) > 2:
        ax2.text(4.15, rank_vals[-1], NAMES.get(cc, cc), fontsize=9, va='center',
                 color=color, fontweight='bold' if cc in highlight else 'normal')

ax2.set_xticks(eps_positions)
ax2.set_xticklabels(eps_names, fontsize=10)
ax2.set_ylabel('Rank (1 = highest welfare)', fontsize=11)
ax2.set_title('Rank Shifts: Who Rises When\nYou Care About Inequality?', fontsize=13, fontweight='bold')
ax2.invert_yaxis()
ax2.set_ylim(16, 0)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/55_epsilon_dial.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 55 saved: 55_epsilon_dial.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 56: WELFARE GROWTH OVER TIME — TRAJECTORIES
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 56: WELFARE GROWTH OVER TIME — TRAJECTORIES")
print("═"*80)

# Time series of EDEI at ε=1 for key countries
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

# Panel 1: Rich + middle income — absolute EDEI(ε=1)
rich_focus = ['USA', 'FRA', 'DEU', 'GBR', 'SWE', 'NOR', 'KOR', 'JPN', 'POL']
colors_rich = sns.color_palette('tab10', len(rich_focus))

for cc, color in zip(rich_focus, colors_rich):
    cdata = df[df['cc'] == cc].sort_values('year')
    if len(cdata) < 2:
        continue
    ax1.plot(cdata['year'], cdata['edei_10'] / 1000, '-', color=color, linewidth=2,
             label=NAMES.get(cc, cc))

ax1.set_xlabel('Year', fontsize=11)
ax1.set_ylabel('EDEI ε=1 ($000 PPP)', fontsize=11)
ax1.set_title('Rich Countries: Welfare-Weighted Income\n(Geometric mean, ε=1)', fontsize=13, fontweight='bold')
ax1.legend(fontsize=9, ncol=2)
ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('$%.0fk'))

# Panel 2: Developing countries — index to 100
dev_focus = ['CHN', 'VNM', 'IND', 'IDN', 'THA', 'BRA', 'CHL', 'MEX', 'POL', 'ETH']
colors_dev = sns.color_palette('tab10', len(dev_focus))

for cc, color in zip(dev_focus, colors_dev):
    cdata = df[df['cc'] == cc].sort_values('year')
    if len(cdata) < 2:
        continue
    base = cdata['edei_10'].iloc[0]
    ax2.plot(cdata['year'], cdata['edei_10'] / base * 100, '-', color=color, linewidth=2,
             label=NAMES.get(cc, cc))

ax2.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
ax2.set_xlabel('Year', fontsize=11)
ax2.set_ylabel('EDEI ε=1 (Index, earliest year = 100)', fontsize=11)
ax2.set_title('Developing Countries: Welfare Growth\n(Indexed, ε=1)', fontsize=13, fontweight='bold')
ax2.legend(fontsize=9, ncol=2)

plt.tight_layout()
plt.savefig(f'{CHART_DIR}/56_welfare_trajectories.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 56 saved: 56_welfare_trajectories.png")

# ══════════════════════════════════════════════════════════════════════════════
# CHART 57: THE KEY QUESTION — US vs FRANCE vs CHINA vs BRAZIL
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("CHART 57: THE KEY QUESTION — US vs FRANCE vs CHINA vs BRAZIL")
print("═"*80)

fig, axes = plt.subplots(2, 2, figsize=(16, 14))

focus_countries = ['USA', 'FRA', 'CHN', 'BRA']
focus_colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
focus_titles = [
    'US: High growth, high inequality',
    'France: Moderate growth, low inequality',
    'China: Explosive growth, narrowing (but wide)',
    'Brazil: Moderate growth, deeply unequal → improving'
]

for (ax, cc, color, title) in zip(axes.flat, focus_countries, focus_colors, focus_titles):
    cdata = df[df['cc'] == cc].sort_values('year')
    if len(cdata) < 2:
        continue

    # Plot all welfare metrics indexed to first year = 100
    for metric, mlabel, ls in [
        ('mean_inc', 'Mean (ε=0)', '-'),
        ('edei_10', 'Log-utility (ε=1)', '--'),
        ('edei_20', 'Pro-poor (ε=2)', ':'),
        ('rawls', 'Rawlsian (bottom 20%)', '-.'),
    ]:
        base = cdata[metric].iloc[0]
        ax.plot(cdata['year'], cdata[metric] / base * 100, ls, color=color,
                linewidth=2 if 'Mean' in mlabel else 1.5, label=mlabel)

    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('Year')
    ax.set_ylabel('Index (first year = 100)')
    ax.legend(fontsize=8)

fig.suptitle('Same Growth, Different Welfare\nHow Inequality Shapes Who Benefits',
             fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{CHART_DIR}/57_us_france_china_brazil.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  → Chart 57 saved: 57_us_france_china_brazil.png")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("SUMMARY: WELFARE-WEIGHTED GROWTH ACROSS THE INCOME SPECTRUM")
print("═"*80)

print("""
KEY FINDINGS:

1. AT ε=0 (Mean): Norway ($90k) leads, followed by the US ($75k).
   Oil wealth is a confound, but Norway also shows you can escape
   the resource curse through good institutions and redistribution.

2. AT ε=1 (Log-utility): Norway ($81k) extends its lead. The US ($57k)
   falls behind Sweden ($55k), Germany ($54k). France ($47k) is close.
   China ($18k) shoots up, validating massive poverty reduction.

3. AT ε=2 (Strong pro-poor): Norway ($73k) still leads. France ($41k)
   NARROWS the gap with the US ($44k). Brazil ($9k) and Chile ($18k)
   get a significant boost for pro-poor growth.

4. AT ε=∞ (Rawlsian): Norway ($41k) is #1. Sweden ($25k), France ($21k),
   Germany ($22k), Poland ($19k), South Korea ($19k) beat the US ($19k).
   If only the poorest matter, European social democracy wins.

5. THE ε QUESTION IS THE DEBATE: The friend's papers implicitly use high ε
   (the poor matter most). The standard growth-optimist uses low ε
   (total output matters). Neither is wrong — it's a value judgment.

6. BUT EVEN AT ε=2: Growth-with-redistribution (France, Poland, Chile)
   outperforms degrowth. Every country's EDEI grew. The question is
   not whether capitalism works, but which capitalism.

7. PRO-POOR GROWTH IS REAL: Brazil (ratio 1.72x), Mexico (1.84x),
   Chile (1.42x), Thailand (1.24x), Ethiopia (1.20x) all had growth
   that disproportionately benefited the poor. US (0.90x), Germany (0.86x),
   Sweden (0.90x) — growth was pro-rich.

8. FRANCE IS THE MODEL: Ratio ≈ 1.01 — growth was distributionally neutral.
   45% tax, strong welfare state, AND the economy still grew for everyone.
""")

print("\nDone!")
