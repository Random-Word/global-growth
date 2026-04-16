#!/usr/bin/env python3
"""
Convert poverty gaps from 2017 PPP dollars to nominal USD.

The PIP poverty lines ($2.15, $3.65, $6.85/day) are in 2017 international dollars (PPP).
The poverty gap index × line × population × 365 gives us the gap in PPP dollars.
ODA is in current nominal USD (~$203B in 2023).

To compare apples-to-apples, we convert poverty gaps to nominal USD using
each country's implicit price level ratio: GDP_nominal / GDP_PPP.

This ratio captures the fact that goods are cheaper in poor countries:
$1 of nominal USD buys more than $1 PPP of consumption in-country.
"""
import pandas as pd
import numpy as np
import os

BASE = "/Users/rstory/Repositories/global-growth"
RAW = os.path.join(BASE, "data", "raw")
PROC = os.path.join(BASE, "data", "processed")

# Load WDI combined data
wdi = pd.read_csv(os.path.join(PROC, "wdi_combined.csv"))

# Load PIP country-level data for all thresholds
thresholds = {
    2.15: pd.read_csv(os.path.join(RAW, "pip_country_2.15.csv")),
    3.65: pd.read_csv(os.path.join(RAW, "pip_country_3.65.csv")),
    6.85: pd.read_csv(os.path.join(RAW, "pip_country_6.85.csv")),
}

# Get latest WDI data (GDP nominal + GDP PPP) for each country
wdi_latest = (
    wdi[wdi["year"] >= 2018]
    .sort_values("year")
    .drop_duplicates("country_code", keep="last")
)
# Compute implicit price level ratio: nominal USD per PPP dollar
wdi_latest = wdi_latest[
    ["country_code", "year", "gdp_current_usd", "gdp_ppp_current"]
].copy()
wdi_latest["price_level_ratio"] = (
    wdi_latest["gdp_current_usd"] / wdi_latest["gdp_ppp_current"]
)
wdi_latest = wdi_latest[wdi_latest["price_level_ratio"].notna()]

print("=" * 70)
print("PRICE LEVEL RATIOS (nominal USD per PPP dollar)")
print("=" * 70)
# Show for key countries
key = ["IND", "NGA", "ETH", "BGD", "COD", "TZA", "MDG", "MOZ", "CHN", "USA"]
for code in key:
    row = wdi_latest[wdi_latest["country_code"] == code]
    if len(row):
        r = row.iloc[0]
        print(
            f"  {code}: {r['price_level_ratio']:.3f} (${1:.2f} PPP = ${r['price_level_ratio']:.2f} nominal)"
        )

print(f"\n  Total countries with price level data: {len(wdi_latest)}")
print(f"  Median ratio (all): {wdi_latest['price_level_ratio'].median():.3f}")

# Also load PIP regional/world data for the global totals (for comparison)
for pl, pip_df in sorted(thresholds.items()):
    print(f"\n{'='*70}")
    print(f"POVERTY GAP CONVERSION: ${pl}/day line")
    print(f"{'='*70}")

    # Get latest observation per country
    latest = (
        pip_df[pip_df["reporting_year"] >= 2018]
        .sort_values("reporting_year")
        .drop_duplicates("country_code", keep="last")
    )

    # Compute country-level poverty gap in PPP dollars
    latest = latest[
        [
            "country_code",
            "country_name",
            "reporting_year",
            "poverty_gap",
            "reporting_pop",
            "headcount",
        ]
    ].copy()
    latest["gap_ppp"] = latest["poverty_gap"] * pl * latest["reporting_pop"] * 365

    # Merge with price level ratios
    merged = latest.merge(
        wdi_latest[["country_code", "price_level_ratio"]],
        on="country_code",
        how="inner",
    )

    # Convert to nominal USD
    merged["gap_nominal"] = merged["gap_ppp"] * merged["price_level_ratio"]

    # Filter to countries with non-zero gaps
    has_gap = merged[merged["gap_ppp"] > 0]

    total_ppp = has_gap["gap_ppp"].sum()
    total_nominal = has_gap["gap_nominal"].sum()
    weighted_avg_ratio = total_nominal / total_ppp if total_ppp > 0 else np.nan

    print(f"\n  Countries with non-zero gaps: {len(has_gap)}")
    print(f"  Total poverty gap (PPP):     ${total_ppp/1e9:.1f}B")
    print(f"  Total poverty gap (nominal): ${total_nominal/1e9:.1f}B")
    print(f"  Weighted avg price ratio:    {weighted_avg_ratio:.3f}")
    print(f"  → $1 PPP of poverty gap ≈ ${weighted_avg_ratio:.2f} nominal to deliver")

    # Show top 15 countries by PPP gap
    top = has_gap.nlargest(15, "gap_ppp")
    print(f"\n  Top 15 countries by poverty gap:")
    print(
        f"  {'Country':<25s} {'Gap PPP':>10s} {'Gap Nom':>10s} {'Ratio':>7s} {'People':>10s}"
    )
    for _, r in top.iterrows():
        print(
            f"  {r['country_name'][:25]:<25s} ${r['gap_ppp']/1e9:>8.1f}B ${r['gap_nominal']/1e9:>8.1f}B {r['price_level_ratio']:>6.3f} {r['reporting_pop']/1e6:>8.1f}M"
        )

    # Compare with ODA
    oda_2023 = 203  # billions nominal USD
    print(f"\n  ODA comparison (2023 ODA = ${oda_2023}B nominal):")
    print(
        f"    PPP gap:     ${total_ppp/1e9:.0f}B PPP → ODA/gap = {oda_2023/(total_ppp/1e9):.1f}×"
    )
    print(
        f"    Nominal gap: ${total_nominal/1e9:.0f}B nom → ODA/gap = {oda_2023/(total_nominal/1e9):.1f}×"
    )

# Also compute the "realistic cost" (3× overhead) in nominal terms
print(f"\n{'='*70}")
print("SUMMARY TABLE FOR README")
print(f"{'='*70}")
print(
    f"\n| Poverty Line | People Below | Gap (PPP) | Gap (Nominal) | Realistic Cost (3× nominal) | % of World GDP |"
)
print(f"|---|---|---|---|---|---|")

world_gdp_nominal = 105e12  # ~$105T in 2024

for pl, pip_df in sorted(thresholds.items()):
    latest = (
        pip_df[pip_df["reporting_year"] >= 2018]
        .sort_values("reporting_year")
        .drop_duplicates("country_code", keep="last")
    )
    latest["gap_ppp"] = latest["poverty_gap"] * pl * latest["reporting_pop"] * 365

    merged = latest.merge(
        wdi_latest[["country_code", "price_level_ratio"]],
        on="country_code",
        how="inner",
    )
    merged["gap_nominal"] = merged["gap_ppp"] * merged["price_level_ratio"]

    has_gap = merged[merged["gap_ppp"] > 0]

    total_ppp = has_gap["gap_ppp"].sum()
    total_nominal = has_gap["gap_nominal"].sum()
    total_people = has_gap["reporting_pop"].sum()
    realistic = total_nominal * 3
    pct_gdp = realistic / world_gdp_nominal * 100

    print(
        f"| ${pl}/day | {total_people/1e9:.2f}B | ${total_ppp/1e9:.0f}B | ${total_nominal/1e9:.0f}B | ${realistic/1e9:.0f}B | {pct_gdp:.2f}% |"
    )
