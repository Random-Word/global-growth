#!/usr/bin/env python3
"""Analysis 22: Poverty-gap affordability under the World Bank's 2021-PPP lines.

In June 2025 the World Bank re-based its global poverty lines on 2021 PPPs:
    extreme            $3.00/day  (was $2.15 at 2017 PPP)
    lower-middle (LMIC) $4.20/day  (was $3.65)
    upper-middle (UMIC) $8.30/day  (was $6.85)
    "Prosperity Gap" benchmark $25/day
This script re-runs the report's poverty-gap / affordability arithmetic at the
new 2021-PPP lines so the README headline numbers can be refreshed, and puts the
old 2017-PPP lines next to the new ones using one consistent method.

PIP convention (confirmed against the live API, see probe notes below):
- `https://api.worldbank.org/pip/v1/pip-grp?group=wb` returns regional rows plus
  a `WLD` world row. Regional rows CANNOT be summed for a world total (they
  overlap); use the WLD row directly (repo memory).
- `poverty_gap` is the FGT(1) index: the mean over the WHOLE population of
  max(1 - y/z, 0), expressed as a fraction of the line z. So the aggregate annual
  shortfall in PPP$ = poverty_gap * line * TOTAL_population * 365.
- The current PIP release (20260324) DEFAULTS to 2021 PPP. We still pass
  `ppp_version` explicitly for reproducibility and to fetch the 2017-PPP
  comparison series.

PRICE-BASIS NOTE (the methodological fix in this revision):
- The poverty gap is denominated in PPP (international) dollars; world GDP can be
  measured in either nominal (current US$, NY.GDP.MKTP.CD) or PPP (current int$,
  NY.GDP.MKTP.PP.CD) dollars. Dividing a PPP-dollar gap by NOMINAL world GDP is a
  price-basis mismatch that OVERSTATES the burden by ~1/price-level-ratio (~2-3x),
  because goods are cheaper in poor countries where the gap is concentrated.
- The report's correct method (see analysis/ppp_nominal_conversion.py) converts
  each country's PPP gap to nominal US$ BEFORE aggregating, using that country's
  implicit price level ratio r_i = GDP_nominal_i / GDP_PPP_i (nominal US$ per PPP$).
- We therefore report THREE internally-consistent measures per line:
    (a) PPP gap / PPP world GDP        (both in international $)
    (b) nominal-converted gap / nominal world GDP   <-- HEADLINE (matches report)
    (c) raw PPP gap, absolute int$.
  Delivery/overhead multipliers (1x/2x/3x) are applied to the NOMINAL measure (b).
- The $25/day "prosperity gap" is reported SEPARATELY as a distance-to-prosperity
  diagnostic, NOT as a closeable transfer cost with delivery multipliers.

Outputs:
- charts/106_affordability_2021ppp.png   (headline = nominal/nominal measure b)
- charts/107_ppp_line_comparison.png     (2017-PPP vs 2021-PPP, nominal/nominal)
- data/processed/affordability_2021ppp.csv (ppp/ppp, nominal/nominal, absolute cols)
"""

from __future__ import annotations

import io
import time
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
for d in (RAW, PROC, CHARTS):
    d.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="colorblind")
plt.rcParams.update(
    {
        "figure.figsize": (12, 7),
        "font.size": 11,
        "axes.titlesize": 13,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)

PIP_BASE = "https://api.worldbank.org/pip/v1"
PIP_RELEASE = "20260324"  # current PIP release (defaults to 2021 PPP)
# 2021-PPP poverty lines (June 2025 revision) used in the affordability bars.
LINES_2021 = [3.00, 4.20, 8.30]
# The $25/day "prosperity gap" benchmark is handled as a SEPARATE diagnostic, not
# as a closeable transfer cost (no delivery multipliers applied to it).
PROSPERITY_LINE = 25.0
# 2017-PPP comparison pairs for the side-by-side chart.
LINE_PAIRS = [(2.15, 3.00), (3.65, 4.20), (6.85, 8.30)]
LINES_2017 = [p[0] for p in LINE_PAIRS]
# Reference year: latest year with a genuine world GDP figure that PIP also
# carries. 2023+ PIP rows are lineup/nowcast extrapolations (data caveat).
REF_YEAR = 2023
# 2021-PPP country file naming uses the float repr of the line ("3.0", "4.2"...).
COUNTRY_FILE_2021 = {
    l: f"pip_2021ppp_{l}_country.csv" for l in LINES_2021 + [PROSPERITY_LINE]
}
# 2017-PPP country files were downloaded earlier under a different naming scheme.
COUNTRY_FILE_2017 = {l: f"pip_country_{l}.csv" for l in LINES_2017}
DELIVERY_MULTIPLIERS = (1, 2, 3)  # report uses up to 3x delivery/overhead cost
# Cached WDI panel with per-country nominal (NY.GDP.MKTP.CD -> gdp_current_usd)
# and PPP (NY.GDP.MKTP.PP.CD -> gdp_ppp_current) GDP, used for price-level ratios.
WDI_PANEL = PROC / "wdi_combined.csv"
GDP_RATIO_MIN_YEAR = 2015  # accept latest GDP ratio in [2015, REF_YEAR] per country


def fetch_csv(url: str, cache_name: str, timeout: int = 180) -> pd.DataFrame:
    """Fetch a CSV from PIP/WDI with a local cache under data/raw."""
    path = RAW / cache_name
    if path.exists() and path.stat().st_size > 200:
        return pd.read_csv(path)
    print(f"  fetching {cache_name} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8")
    df = pd.read_csv(io.StringIO(text))
    df.to_csv(path, index=False)
    time.sleep(1.0)
    return df


def fetch_world(line: float, ppp: int) -> pd.Series | None:
    """Return the PIP WLD row at REF_YEAR for a given line and PPP vintage."""
    url = (
        f"{PIP_BASE}/pip-grp?group=wb&year=all&povline={line}"
        f"&ppp_version={ppp}&format=csv"
    )
    df = fetch_csv(url, f"pip_{ppp}ppp_{line}_world.csv")
    wld = df[df["region_code"] == "WLD"].copy()
    if wld.empty:
        return None
    yr = (
        REF_YEAR
        if REF_YEAR in set(wld["reporting_year"])
        else wld["reporting_year"].max()
    )
    return wld[wld["reporting_year"] == yr].iloc[0]


def world_gdp_nominal(year: int) -> float:
    """World nominal GDP (current US$) from WDI JSON, $106.7T (2023) fallback."""
    import json

    jurl = (
        "https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.CD"
        "?format=json&per_page=200&date=2010:2024"
    )
    try:
        req = urllib.request.Request(jurl, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        vals = {int(r["date"]): r["value"] for r in data[1] if r["value"]}
        return float(vals.get(year, vals[max(vals)]))
    except Exception as exc:
        print(f"  WDI GDP fetch failed ({exc}); using $106.7T fallback (2023).")
        return 106.7e12


def world_gdp_ppp(year: int) -> float:
    """World PPP GDP (current int$, NY.GDP.MKTP.PP.CD), $188.5T (2023) fallback."""
    import json

    jurl = (
        "https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.PP.CD"
        "?format=json&per_page=200&date=2010:2024"
    )
    try:
        req = urllib.request.Request(jurl, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        vals = {int(r["date"]): r["value"] for r in data[1] if r["value"]}
        return float(vals.get(year, vals[max(vals)]))
    except Exception as exc:
        print(f"  WDI PPP-GDP fetch failed ({exc}); using $188.5T fallback (2023).")
        # Fall back to the cached WDI panel WLD row if available.
        try:
            wdi = pd.read_csv(WDI_PANEL)
            wld = wdi[(wdi["country_code"] == "WLD") & wdi["gdp_ppp_current"].notna()]
            sub = wld[wld["year"] <= year]
            if not sub.empty:
                return float(sub.sort_values("year")["gdp_ppp_current"].iloc[-1])
        except Exception:
            pass
        return 188.5e12


def country_price_ratios() -> tuple[dict[str, float], float]:
    """Per-country price-level ratio r_i = GDP_nominal_i / GDP_PPP_i (nominal US$
    per PPP$), plus the world fallback ratio (world nominal GDP / world PPP GDP).

    Implements the same conversion as analysis/ppp_nominal_conversion.py, reading
    the cached WDI panel (NY.GDP.MKTP.CD and NY.GDP.MKTP.PP.CD). For each country
    we take the latest non-missing ratio in [GDP_RATIO_MIN_YEAR, REF_YEAR].
    """
    wdi = pd.read_csv(WDI_PANEL)
    cty = wdi[
        (wdi["year"] >= GDP_RATIO_MIN_YEAR)
        & (wdi["year"] <= REF_YEAR)
        & (wdi["country_code"].str.len() == 3)  # ISO3 countries only, drop aggregates
        & wdi["gdp_current_usd"].notna()
        & wdi["gdp_ppp_current"].notna()
        & (wdi["gdp_ppp_current"] > 0)
    ].copy()
    cty = cty.sort_values("year").drop_duplicates("country_code", keep="last")
    cty["ratio"] = cty["gdp_current_usd"] / cty["gdp_ppp_current"]
    ratio_map = dict(zip(cty["country_code"], cty["ratio"]))
    ratio_map.pop("WLD", None)
    # World fallback ratio from the WLD row at REF_YEAR (nominal / PPP).
    wld = wdi[(wdi["country_code"] == "WLD") & (wdi["year"] <= REF_YEAR)]
    wld = wld.dropna(subset=["gdp_current_usd", "gdp_ppp_current"]).sort_values("year")
    world_ratio = (
        float(wld["gdp_current_usd"].iloc[-1] / wld["gdp_ppp_current"].iloc[-1])
        if not wld.empty
        else 0.566
    )
    return ratio_map, world_ratio


def nominal_conversion(
    country_csv: str, line: float, ratio_map: dict[str, float], world_ratio: float
) -> dict | None:
    """Convert a line's country-level PPP poverty gaps to nominal US$ and return
    the gap-weighted effective price-level ratio r_eff = sum(nominal)/sum(PPP).

    Each country's PPP gap = poverty_gap_i * line * reporting_pop_i * 365. Countries
    without a GDP ratio fall back to the world-average ratio (flagged via n_fallback).
    """
    path = RAW / country_csv
    if not path.exists():
        print(f"  WARN: country file {country_csv} missing; cannot nominal-convert.")
        return None
    df = pd.read_csv(path)
    d = df[
        (df["reporting_year"] <= REF_YEAR)
        & (df["reporting_year"] >= GDP_RATIO_MIN_YEAR)
    ].copy()
    if d.empty:
        return None
    used_year = (
        REF_YEAR
        if (d["reporting_year"] == REF_YEAR).any()
        else int(d["reporting_year"].max())
    )
    d = d.sort_values("reporting_year").drop_duplicates("country_code", keep="last")
    d["gap_ppp"] = d["poverty_gap"] * line * d["reporting_pop"] * 365.0
    d = d[d["gap_ppp"] > 0].copy()
    d["ratio"] = d["country_code"].map(ratio_map)
    d["is_fallback"] = d["ratio"].isna()
    d["ratio"] = d["ratio"].fillna(world_ratio)
    d["gap_nominal"] = d["gap_ppp"] * d["ratio"]
    sum_ppp = float(d["gap_ppp"].sum())
    sum_nom = float(d["gap_nominal"].sum())
    return {
        "country_ppp_gap": sum_ppp,
        "country_nominal_gap": sum_nom,
        "r_eff": sum_nom / sum_ppp if sum_ppp > 0 else float("nan"),
        "n_countries": int(len(d)),
        "n_fallback": int(d["is_fallback"].sum()),
        "ratio_used_year": used_year,
    }


def affordability_row(
    line: float,
    ppp: int,
    world_gdp_nom: float,
    world_gdp_ppp_val: float,
    country_csv: str,
    ratio_map: dict[str, float],
    world_ratio: float,
) -> dict | None:
    """Compute the THREE internally-consistent affordability measures for one
    (line, PPP) world aggregate:
        (a) PPP gap / PPP world GDP
        (b) nominal-converted gap / nominal world GDP   <-- headline
        (c) raw PPP gap, absolute int$.
    The PPP gap base is the WLD aggregate (FGT1 arithmetic); the nominal gap is
    that base scaled by the gap-weighted price-level ratio r_eff derived from the
    country-level files (so all three measures share one consistent gap base).
    """
    r = fetch_world(line, ppp)
    if r is None:
        return None
    year = int(r["reporting_year"])
    pop = float(r["reporting_pop"])
    hc = float(r["headcount"])  # fraction below the line
    pg = float(r["poverty_gap"])  # FGT(1): fraction of line, averaged over all pop
    # (c) Aggregate annual shortfall in PPP int$: gap-fraction * line * total-pop * 365.
    gap_ppp_yr = pg * line * pop * 365.0

    # Country-level nominal conversion -> gap-weighted effective price-level ratio.
    conv = nominal_conversion(country_csv, line, ratio_map, world_ratio)
    if conv is None:
        # No country file: fall back to the world ratio so the row is still usable.
        r_eff = world_ratio
        n_countries = n_fallback = 0
        ratio_used_year = REF_YEAR
    else:
        r_eff = conv["r_eff"]
        n_countries = conv["n_countries"]
        n_fallback = conv["n_fallback"]
        ratio_used_year = conv["ratio_used_year"]

    # (b) Nominal-converted gap = PPP gap base * gap-weighted price-level ratio.
    gap_nominal_yr = gap_ppp_yr * r_eff

    caveat = "lineup/nowcast (2023+ extrapolation)" if year >= 2023 else "survey-based"
    row = {
        "pip_release": PIP_RELEASE,
        "ppp_version": ppp,
        "line": line,
        "year": year,
        "ref_year": REF_YEAR,
        "data_caveat": caveat,
        "headcount_millions": hc * pop / 1e6,
        "poverty_gap_fgt1": pg,
        # (c) absolute PPP gap
        "gap_ppp_yr": gap_ppp_yr,
        # (a) PPP / PPP measure
        "gap_pct_world_gdp_ppp": gap_ppp_yr / world_gdp_ppp_val * 100.0,
        # price-level conversion
        "price_level_ratio_eff": r_eff,
        "n_countries": n_countries,
        "n_fallback_ratio": n_fallback,
        "ratio_used_year": ratio_used_year,
        # (b) nominal / nominal measure (headline) at 1x
        "gap_nominal_yr": gap_nominal_yr,
        "gap_pct_world_gdp_nominal": gap_nominal_yr / world_gdp_nom * 100.0,
    }
    # Delivery/overhead multipliers applied to the NOMINAL measure (b).
    for m in DELIVERY_MULTIPLIERS:
        row[f"gap_nominal_{m}x"] = gap_nominal_yr * m
        row[f"gap_nominal_{m}x_pct_gdp"] = gap_nominal_yr * m / world_gdp_nom * 100.0
    return row


def prosperity_diagnostic(
    world_gdp_nom: float,
    world_gdp_ppp_val: float,
    ratio_map: dict[str, float],
    world_ratio: float,
) -> dict | None:
    """Distance-to-prosperity diagnostic for the $25/day benchmark.

    Reported as a structural distance metric (absolute $ and % of world GDP), NOT
    as a closeable transfer cost — so NO delivery multipliers are applied. The $25
    "prosperity gap" reflects the income distance to a developed-economy standard;
    most of it cannot be closed by transfers and would require broad-based growth.
    """
    r = fetch_world(PROSPERITY_LINE, 2021)
    if r is None:
        return None
    year = int(r["reporting_year"])
    pop = float(r["reporting_pop"])
    pg = float(r["poverty_gap"])
    hc = float(r["headcount"])
    gap_ppp_yr = pg * PROSPERITY_LINE * pop * 365.0
    conv = nominal_conversion(
        COUNTRY_FILE_2021[PROSPERITY_LINE], PROSPERITY_LINE, ratio_map, world_ratio
    )
    r_eff = conv["r_eff"] if conv else world_ratio
    gap_nominal_yr = gap_ppp_yr * r_eff
    return {
        "line": PROSPERITY_LINE,
        "year": year,
        "headcount_millions": hc * pop / 1e6,
        "gap_ppp_yr": gap_ppp_yr,
        "gap_pct_world_gdp_ppp": gap_ppp_yr / world_gdp_ppp_val * 100.0,
        "price_level_ratio_eff": r_eff,
        "gap_nominal_yr": gap_nominal_yr,
        "gap_pct_world_gdp_nominal": gap_nominal_yr / world_gdp_nom * 100.0,
        "n_countries": conv["n_countries"] if conv else 0,
        "n_fallback_ratio": conv["n_fallback"] if conv else 0,
    }


def main() -> None:
    print(
        f"Probe: PIP release {PIP_RELEASE} defaults to 2021 PPP; ref year {REF_YEAR}."
    )
    world_gdp_nom = world_gdp_nominal(REF_YEAR)
    world_gdp_ppp_val = world_gdp_ppp(REF_YEAR)
    print(f"World nominal GDP {REF_YEAR}: ${world_gdp_nom/1e12:.1f}T (NY.GDP.MKTP.CD)")
    print(
        f"World PPP GDP     {REF_YEAR}: ${world_gdp_ppp_val/1e12:.1f}T (NY.GDP.MKTP.PP.CD)"
    )
    print(
        f"World price-level ratio (nominal/PPP): {world_gdp_nom/world_gdp_ppp_val:.3f}\n"
    )

    # Per-country price-level ratios for the nominal conversion (report's method).
    ratio_map, world_ratio = country_price_ratios()
    print(
        f"Loaded price-level ratios for {len(ratio_map)} countries "
        f"(world fallback ratio = {world_ratio:.3f}).\n"
    )

    # Cache country-level files (drive the nominal conversion). The WLD aggregate
    # still drives the PPP gap base since regional rows cannot be summed (repo memory).
    for line in LINES_2021 + [PROSPERITY_LINE]:
        try:
            fetch_csv(
                f"{PIP_BASE}/pip?country=all&year=all&povline={line}"
                f"&ppp_version=2021&fill_gaps=true&format=csv",
                COUNTRY_FILE_2021[line],
            )
        except Exception as exc:
            print(f"  country fetch failed for ${line}: {exc}")

    rows_2021 = [
        r
        for line in LINES_2021
        if (
            r := affordability_row(
                line,
                2021,
                world_gdp_nom,
                world_gdp_ppp_val,
                COUNTRY_FILE_2021[line],
                ratio_map,
                world_ratio,
            )
        )
    ]
    rows_2017 = [
        r
        for line in LINES_2017
        if (
            r := affordability_row(
                line,
                2017,
                world_gdp_nom,
                world_gdp_ppp_val,
                COUNTRY_FILE_2017[line],
                ratio_map,
                world_ratio,
            )
        )
    ]
    df21 = pd.DataFrame(rows_2021)
    df17 = pd.DataFrame(rows_2017)

    prosperity = prosperity_diagnostic(
        world_gdp_nom, world_gdp_ppp_val, ratio_map, world_ratio
    )

    out = pd.concat([df21, df17], ignore_index=True)
    out.to_csv(PROC / "affordability_2021ppp.csv", index=False)
    print("Saved data/processed/affordability_2021ppp.csv\n")

    # ---- Three-measure side-by-side table (the corrected headline) ----
    print(
        "THREE INTERNALLY-CONSISTENT MEASURES (2021-PPP lines, "
        f"{int(df21['year'].iloc[0])}, {df21['data_caveat'].iloc[0]}):"
    )
    hdr = (
        f"  {'line':>7s} {'(a) PPP/PPP':>12s} {'(b) NOM/NOM':>12s} "
        f"{'(b) 3x':>9s} {'r_eff':>6s} {'(c) PPP $B':>11s} {'fallbk':>7s}"
    )
    print(hdr)
    for _, r in df21.iterrows():
        print(
            f"  ${r['line']:>5.2f} {r['gap_pct_world_gdp_ppp']:>11.3f}% "
            f"{r['gap_pct_world_gdp_nominal']:>11.3f}% "
            f"{r['gap_nominal_3x_pct_gdp']:>8.3f}% "
            f"{r['price_level_ratio_eff']:>6.3f} "
            f"{r['gap_ppp_yr']/1e9:>10.1f} "
            f"{int(r['n_fallback_ratio']):>7d}"
        )
    print(
        "  (a) = PPP gap / PPP world GDP; (b) = nominal-converted gap / nominal "
        "world GDP [HEADLINE]; (c) = raw PPP gap absolute.\n"
    )

    if prosperity is not None:
        print(
            "DISTANCE-TO-PROSPERITY DIAGNOSTIC ($25/day, separate from affordability):"
        )
        print(
            f"  $25.00/day: {prosperity['headcount_millions']:.0f}M below; "
            f"PPP/PPP {prosperity['gap_pct_world_gdp_ppp']:.2f}% GDP, "
            f"nominal/nominal {prosperity['gap_pct_world_gdp_nominal']:.2f}% GDP "
            f"(structural income distance, NOT a transfer cost; no delivery multiplier).\n"
        )

    # ---- Chart 106: headline = nominal/nominal gap as % of nominal world GDP ----
    fig = plt.figure(figsize=(13, 7))
    gs = fig.add_gridspec(1, 3, width_ratios=[2.4, 0.05, 1.0], wspace=0.25)
    ax = fig.add_subplot(gs[0, 0])
    ax_div = fig.add_subplot(gs[0, 2])

    x = np.arange(len(df21))
    width = 0.26
    for i, m in enumerate(DELIVERY_MULTIPLIERS):
        vals = df21[f"gap_nominal_{m}x_pct_gdp"].values
        bars = ax.bar(x + (i - 1) * width, vals, width, label=f"{m}x delivery/overhead")
        for b, v in zip(bars, vals):
            ax.annotate(
                f"{v:.2f}%",
                (b.get_x() + b.get_width() / 2, v),
                ha="center",
                va="bottom",
                fontsize=8,
            )
    # Annotate the PPP/PPP measure (a) for reference under each group.
    for xi, (_, r) in zip(x, df21.iterrows()):
        ax.annotate(
            f"PPP/PPP: {r['gap_pct_world_gdp_ppp']:.2f}%",
            (xi, 0),
            xytext=(0, -22),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=7.5,
            color="dimgray",
        )
    ax.set_xticks(x)
    ax.set_xticklabels([f"${l:.2f}/day" for l in df21["line"]])
    ax.set_ylabel("Nominal-converted gap as % of NOMINAL world GDP")
    ax.set_title(
        f"Affordability of closing the poverty gap, 2021-PPP lines (headline = "
        f"nominal/nominal)\nWLD {int(df21['year'].iloc[0])} "
        f"({df21['data_caveat'].iloc[0]}), PIP rel. {PIP_RELEASE}, "
        f"nominal world GDP ${world_gdp_nom/1e12:.0f}T",
        fontsize=11,
    )
    ax.legend(title="applied to nominal measure (b)")
    ax.margins(y=0.18)

    # Separate distance-to-prosperity diagnostic panel ($25, no multipliers).
    if prosperity is not None:
        pv_nom = prosperity["gap_pct_world_gdp_nominal"]
        pv_ppp = prosperity["gap_pct_world_gdp_ppp"]
        pb = ax_div.bar(
            [0, 1], [pv_ppp, pv_nom], color=["#9ecae1", "#3182bd"], width=0.6
        )
        for b, v in zip(pb, [pv_ppp, pv_nom]):
            ax_div.annotate(
                f"{v:.1f}%",
                (b.get_x() + b.get_width() / 2, v),
                ha="center",
                va="bottom",
                fontsize=8,
            )
        ax_div.set_xticks([0, 1])
        ax_div.set_xticklabels(["PPP/PPP", "nom/nom"], fontsize=9)
        ax_div.set_ylabel("Gap as % of world GDP", fontsize=9)
        ax_div.set_title(
            "Distance to prosperity\n$25/day diagnostic\n(NOT a transfer cost)",
            fontsize=9.5,
        )
        ax_div.margins(y=0.2)
    fig.savefig(CHARTS / "106_affordability_2021ppp.png")
    plt.close(fig)

    # ---- Chart 107: 2017-PPP vs 2021-PPP nominal/nominal gap-%-GDP ----
    fig, ax = plt.subplots()
    labels, old_vals, new_vals = [], [], []
    for old_line, new_line in LINE_PAIRS:
        o = df17[df17["line"] == old_line]
        n = df21[df21["line"] == new_line]
        if o.empty or n.empty:
            continue
        labels.append(f"${old_line:.2f}\u2192${new_line:.2f}")
        old_vals.append(o["gap_pct_world_gdp_nominal"].iloc[0])
        new_vals.append(n["gap_pct_world_gdp_nominal"].iloc[0])
    xp = np.arange(len(labels))
    w = 0.38
    b1 = ax.bar(xp - w / 2, old_vals, w, label="2017 PPP (old line)")
    b2 = ax.bar(xp + w / 2, new_vals, w, label="2021 PPP (new line)")
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(
                f"{b.get_height():.2f}%",
                (b.get_x() + b.get_width() / 2, b.get_height()),
                ha="center",
                va="bottom",
                fontsize=8,
            )
    ax.set_xticks(xp)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Nominal-converted gap as % of NOMINAL world GDP (1x)")
    ax.set_title(
        "2017-PPP vs 2021-PPP poverty-gap affordability\n"
        "(consistent method: nominal-converted gap / nominal world GDP)"
    )
    ax.legend()
    fig.savefig(CHARTS / "107_ppp_line_comparison.png")
    plt.close(fig)

    # ---- Headcount comparison to the report's statement ----
    print("Headcounts (latest available year):")
    for _, r in df21.iterrows():
        print(
            f"  ${r['line']:.2f}/day: {r['headcount_millions']:.0f}M below "
            f"(nominal/nominal gap {r['gap_pct_world_gdp_nominal']:.2f}% GDP at 1x, "
            f"{r['gap_nominal_3x_pct_gdp']:.2f}% at 3x; "
            f"PPP/PPP {r['gap_pct_world_gdp_ppp']:.2f}%)"
        )
    print(
        "\nSaved charts/106_affordability_2021ppp.png and "
        "charts/107_ppp_line_comparison.png"
    )


if __name__ == "__main__":
    main()
