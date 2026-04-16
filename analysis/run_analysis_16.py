"""
Analysis 16: Rich-World Working-Class Welfare — Who Actually Stagnated?
=======================================================================

The popular "working-class stagnation" narrative is usually illustrated with
a single number: real median wages for US men without a bachelor's degree.
That framing privileges one demographic slice and treats it as representative
of a broader "rich-world working class" story. This analysis tests that
framing against the actual multi-group, multi-country data:

1. US real earnings by education level  (1979–present)
2. US real earnings by gender × education  (who stagnated?)
3. US real median household income by race/ethnicity  (1970–present)
4. Cross-country real average wages  (OECD, 1990–2023)  — is US-type
   stagnation universal across rich countries, or US-specific?
5. Bottom-50% share of pre-tax national income  (WID, major economies)

Data sources:
- FRED (St. Louis Fed) for US real earnings series (CPS quarterly)
- US Census historical income tables (H-05: race-level household income)
- OECD "Average annual wages" dataset (real, constant prices, 2022 PPPs)
- World Inequality Database (WID.world) for income-share decomposition

All downloads are cached under data/raw/wages/ for reproducibility.
Charts: 78–82.
"""

from __future__ import annotations

import io
import os
import json
import subprocess
import warnings
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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
CACHE_DIR = Path("data/raw/wages")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch(url: str, cache_name: str, binary: bool = False) -> bytes | str:
    """Fetch URL with on-disk caching via curl (Python urllib hangs on some hosts)."""
    cache = CACHE_DIR / cache_name
    if cache.exists() and cache.stat().st_size > 0:
        return cache.read_bytes() if binary else cache.read_text()
    # Use curl: reliably fast on this environment, unlike Python urllib.
    last_err = None
    for attempt in range(3):
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-sSL",
                    "--http1.1",
                    "--max-time",
                    "90",
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
                timeout=120,
            )
            http_code = result.stdout.strip()
            if (
                result.returncode == 0
                and cache.exists()
                and cache.stat().st_size > 0
                and http_code.startswith("2")
            ):
                return cache.read_bytes() if binary else cache.read_text()
            last_err = f"curl rc={result.returncode} http={http_code} stderr={result.stderr.strip()[:200]}"
            if cache.exists():
                cache.unlink()
        except Exception as e:
            last_err = str(e)
    print(f"  ! fetch failed for {cache_name}: {last_err}")
    return b"" if binary else ""


def fred_csv(series_id: str) -> pd.DataFrame:
    """Download a single FRED series as CSV and return a date-indexed DataFrame."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    text = fetch(url, f"fred_{series_id}.csv")
    if not text:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(text))
    # FRED uses "DATE" (older) or "observation_date" (newer)
    date_col = "observation_date" if "observation_date" in df.columns else "DATE"
    df = df.rename(columns={date_col: "date", series_id: "value"})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["date", "value"]].dropna()


# ─────────────────────────────────────────────────────────────────────────────
# 1. US median weekly earnings by education  (FRED, quarterly)
#    FRED only publishes NOMINAL series by education; we deflate with CPI-U
#    (CPIAUCSL) to constant 2024 dollars.
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] Downloading FRED nominal earnings by education + CPI-U for deflation…")

EDUCATION_SERIES = {
    # Employed full time, wage/salary workers, 25 years+, median usual weekly
    # NOMINAL earnings, quarterly, not seasonally adjusted (Q suffix required).
    "Less than HS": "LEU0252916700Q",
    "HS graduate": "LEU0252917300Q",
    "Some college": "LEU0254929400Q",
    "Bachelor's+": "LEU0252918500Q",
}

# CPI-U, all items, seasonally adjusted, monthly.
cpi = fred_csv("CPIAUCSL")
if not cpi.empty:
    cpi = cpi.rename(columns={"value": "cpi"}).copy()
    cpi["year"] = cpi["date"].dt.year
    cpi["quarter"] = cpi["date"].dt.quarter
    cpi_q = cpi.groupby(["year", "quarter"], as_index=False).cpi.mean()
    # Deflate to 2024 annual average
    cpi_2024 = cpi_q[cpi_q.year == 2024].cpi.mean()
    cpi_q["deflator"] = cpi_2024 / cpi_q["cpi"]
else:
    cpi_q = pd.DataFrame()
    print("  ! CPIAUCSL download failed — education series will be in nominal $.")

edu_frames = {}
for label, sid in EDUCATION_SERIES.items():
    df = fred_csv(sid)
    if df.empty:
        print(f"  {label:<16s} {sid}  FAILED")
        continue
    df["group"] = label
    if not cpi_q.empty:
        df["year"] = df["date"].dt.year
        df["quarter"] = df["date"].dt.quarter
        df = df.merge(
            cpi_q[["year", "quarter", "deflator"]], on=["year", "quarter"], how="left"
        )
        df["value"] = df["value"] * df["deflator"]
        df = df.drop(columns=["year", "quarter", "deflator"])
    edu_frames[label] = df
    print(
        f"  {label:<16s} {sid}  n={len(df)}  range={df.date.min().year}–{df.date.max().year}"
    )

edu = (
    pd.concat(edu_frames.values(), ignore_index=True) if edu_frames else pd.DataFrame()
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. US real median weekly earnings by gender  (FRED)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Downloading FRED real earnings by gender…")

GENDER_SERIES = {
    # Real median weekly earnings, 1982-84 CPI-adjusted $, quarterly, SA (Q suffix)
    "Men (16+)": "LES1252881900Q",
    "Women (16+)": "LES1252882800Q",
}

gen_frames = {}
for label, sid in GENDER_SERIES.items():
    df = fred_csv(sid)
    if not df.empty:
        df["group"] = label
        gen_frames[label] = df
        print(
            f"  {label:<16s} {sid}  n={len(df)}  range={df.date.min().year}–{df.date.max().year}"
        )
    else:
        print(f"  {label:<16s} {sid}  FAILED")

gen = (
    pd.concat(gen_frames.values(), ignore_index=True) if gen_frames else pd.DataFrame()
)


# ─────────────────────────────────────────────────────────────────────────────
# 3. US real median weekly earnings by race/ethnicity  (FRED)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] Downloading FRED real earnings by race/ethnicity…")

RACE_SERIES = {
    # Real median weekly earnings, 16 years and over, 1982-84 CPI-adjusted $,
    # quarterly, NSA (Q suffix).
    "White": "LEU0252883700Q",
    "Black": "LEU0252884600Q",
    "Hispanic": "LEU0252885500Q",
    "Asian": "LEU0254871100Q",
}

race_frames = {}
for label, sid in RACE_SERIES.items():
    df = fred_csv(sid)
    if not df.empty:
        df["group"] = label
        race_frames[label] = df
        print(
            f"  {label:<10s} {sid}  n={len(df)}  range={df.date.min().year}–{df.date.max().year}"
        )
    else:
        print(f"  {label:<10s} {sid}  FAILED")

race = (
    pd.concat(race_frames.values(), ignore_index=True)
    if race_frames
    else pd.DataFrame()
)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Cross-country real average wages  (OECD, 2022 constant PPP USD)
#    Source: OECD DSD_EARNINGS@DF_EARNINGS (Average annual wages).
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Downloading OECD real average wages…")

# OECD SDMX JSON endpoint — all countries, annual, full series.
# The "Average annual wages" indicator in 2022 constant prices, 2022 USD PPPs.
# Bare flow query: OECD returns all 7 key dimensions when no dot pattern is given.
OECD_URL = (
    "https://sdmx.oecd.org/public/rest/data/OECD.ELS.SAE,DSD_EARNINGS@AV_AN_WAGE,1.0/"
    "?format=csvfile"
)
oecd_text = fetch(OECD_URL, "oecd_avg_wages.csv")

oecd = pd.DataFrame()
if oecd_text:
    oecd = pd.read_csv(io.StringIO(oecd_text))
    # Filter: USD_PPP unit (already expressed in constant 2022 USD PPP), both
    # sexes (_Z), MEAN aggregation. USD_PPP only appears with PRICE_BASE=Q in
    # this dataset but represents the constant-price PPP series.
    if "UNIT_MEASURE" in oecd.columns:
        oecd = oecd[oecd["UNIT_MEASURE"] == "USD_PPP"]
    if "SEX" in oecd.columns:
        oecd = oecd[oecd["SEX"] == "_Z"]
    if "AGGREGATION_OPERATION" in oecd.columns:
        oecd = oecd[oecd["AGGREGATION_OPERATION"] == "MEAN"]
    cols = {c.lower(): c for c in oecd.columns}
    country_col = cols.get("ref_area") or cols.get("country") or "REF_AREA"
    year_col = cols.get("time_period") or cols.get("time") or "TIME_PERIOD"
    value_col = cols.get("obs_value") or cols.get("value") or "OBS_VALUE"
    oecd = oecd.rename(
        columns={country_col: "cc", year_col: "year", value_col: "value"}
    )
    oecd = oecd[["cc", "year", "value"]].dropna()
    oecd["year"] = pd.to_numeric(oecd["year"], errors="coerce").astype("Int64")
    oecd["value"] = pd.to_numeric(oecd["value"], errors="coerce")
    oecd = oecd.dropna()
    print(
        f"  OECD rows: {len(oecd)}, countries: {oecd.cc.nunique()}, "
        f"years: {oecd.year.min()}–{oecd.year.max()}"
    )
else:
    print("  OECD download failed — chart 4 will be skipped.")


# ─────────────────────────────────────────────────────────────────────────────
# 5. WID.world — bottom 50% pre-tax national income share  (major economies)
#    We pull pre-downloaded country CSVs from the WID bulk endpoint.
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] Downloading WID.world bottom-50% income shares…")

WID_COUNTRIES = {
    "US": "USA",
    "GB": "UK",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "JP": "Japan",
    "CA": "Canada",
    "AU": "Australia",
    "SE": "Sweden",
    "NO": "Norway",
}

wid_rows = []
# WID bulk: https://wid.world/bulk_download/WID_data_<CC>.csv
# Variable of interest: sptinc992j — pre-tax national income share.
# Percentile codes: p0p50 (bottom 50%), p90p100 (top 10%), p50p90 (middle 40%).
for cc_wid, name in WID_COUNTRIES.items():
    url = f"https://wid.world/bulk_download/WID_data_{cc_wid}.csv"
    text = fetch(url, f"wid_{cc_wid}.csv")
    if not text:
        print(f"  {name:<10s} WID  FAILED")
        continue
    try:
        # WID CSVs are semicolon-delimited.
        wdf = pd.read_csv(io.StringIO(text), sep=";", low_memory=False)
    except Exception as e:
        print(f"  {name:<10s} parse fail: {e}")
        continue
    # Filter to sptincj992 (pre-tax national income share, equal-split adults).
    m = (wdf.get("variable") == "sptincj992") & (
        wdf.get("percentile").isin(["p0p50", "p50p90", "p90p100"])
    )
    sub = wdf[m][["country", "percentile", "year", "value"]].copy()
    sub["country_name"] = name
    wid_rows.append(sub)
    print(f"  {name:<10s} rows: {len(sub)}")

wid = pd.concat(wid_rows, ignore_index=True) if wid_rows else pd.DataFrame()
if not wid.empty:
    wid["year"] = pd.to_numeric(wid["year"], errors="coerce").astype("Int64")
    wid["value"] = pd.to_numeric(wid["value"], errors="coerce")
    wid = wid.dropna()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def annual(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse FRED quarterly to annual means."""
    if df.empty:
        return df
    df = df.copy()
    df["year"] = df["date"].dt.year
    return df.groupby(["group", "year"], as_index=False).value.mean()


def index_to(df: pd.DataFrame, base_year: int) -> pd.DataFrame:
    """Index each group's value series to 100 at base_year."""
    out = []
    for g, sub in df.groupby("group"):
        sub = sub.sort_values("year")
        if base_year in sub.year.values:
            b = sub.loc[sub.year == base_year, "value"].iloc[0]
        else:
            # Use earliest available year ≥ base_year.
            b = sub.loc[sub.year >= base_year, "value"].iloc[0]
        sub = sub.assign(index=100 * sub.value / b)
        out.append(sub)
    return pd.concat(out, ignore_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# CHART 78 — US real median weekly earnings by education (1982$)
# ─────────────────────────────────────────────────────────────────────────────
if not edu.empty:
    print("\n[chart 78] US real earnings by education…")
    ann = annual(edu)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left panel: raw $ levels
    ax = axes[0]
    colors = sns.color_palette("colorblind", n_colors=4)
    order = ["Less than HS", "HS graduate", "Some college", "Bachelor's+"]
    for g, c in zip(order, colors):
        sub = ann[ann.group == g].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub.year, sub.value, lw=2.2, label=g, color=c)
    ax.set_title(
        "US real median weekly earnings by education\n(constant 2024 $ via CPI-U; workers 25+)"
    )
    ax.set_ylabel("Real median usual weekly earnings ($)")
    ax.set_xlabel("Year")
    ax.legend(loc="upper left", frameon=True)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))

    # Right panel: indexed to 2000 = 100
    ax = axes[1]
    idx = index_to(ann, 2000)
    for g, c in zip(order, colors):
        sub = idx[idx.group == g].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub.year, sub["index"], lw=2.2, label=g, color=c)
    ax.axhline(100, color="grey", lw=0.8, ls="--", alpha=0.7)
    ax.set_title("Indexed to 2000 = 100\n(makes relative trajectories comparable)")
    ax.set_ylabel("Index (2000 = 100)")
    ax.set_xlabel("Year")
    ax.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(
        CHART_DIR / "78_us_earnings_by_education.png", dpi=140, bbox_inches="tight"
    )
    plt.close(fig)

# ─────────────────────────────────────────────────────────────────────────────
# CHART 79 — US real earnings by gender
# ─────────────────────────────────────────────────────────────────────────────
if not gen.empty:
    print("[chart 79] US real earnings by gender…")
    ann = annual(gen)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    ax = axes[0]
    colors = {"Men (16+)": "#1f77b4", "Women (16+)": "#e377c2"}
    for g in ["Men (16+)", "Women (16+)"]:
        sub = ann[ann.group == g].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub.year, sub.value, lw=2.4, label=g, color=colors[g])
    ax.set_title(
        "US real median weekly earnings by gender\n(1982–84 CPI-adjusted $; workers 16+)"
    )
    ax.set_ylabel("Real median usual weekly earnings ($)")
    ax.legend(loc="lower right", frameon=True)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    ax.set_xlabel("Year")

    ax = axes[1]
    idx = index_to(ann, 1980)
    for g in ["Men (16+)", "Women (16+)"]:
        sub = idx[idx.group == g].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub.year, sub["index"], lw=2.4, label=g, color=colors[g])
    ax.axhline(100, color="grey", lw=0.8, ls="--", alpha=0.7)
    ax.set_title("Indexed to earliest available year = 100")
    ax.set_ylabel("Index (base year = 100)")
    ax.legend(loc="upper left", frameon=True)
    ax.set_xlabel("Year")

    plt.tight_layout()
    fig.savefig(
        CHART_DIR / "79_us_earnings_by_gender.png", dpi=140, bbox_inches="tight"
    )
    plt.close(fig)

# ─────────────────────────────────────────────────────────────────────────────
# CHART 80 — US real earnings by race/ethnicity
# ─────────────────────────────────────────────────────────────────────────────
if not race.empty:
    print("[chart 80] US real earnings by race/ethnicity…")
    ann = annual(race)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    order = ["Asian", "White", "Black", "Hispanic"]
    palette = dict(zip(order, sns.color_palette("colorblind", n_colors=4)))

    ax = axes[0]
    for g in order:
        sub = ann[ann.group == g].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub.year, sub.value, lw=2.2, label=g, color=palette[g])
    ax.set_title("US real median weekly earnings by race/ethnicity\n(workers 16+)")
    ax.set_ylabel("Real median usual weekly earnings ($)")
    ax.legend(loc="upper left", frameon=True)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    ax.set_xlabel("Year")

    # Right: index to earliest common year
    ax = axes[1]
    if not ann.empty:
        earliest = int(ann.groupby("group").year.min().max())
        idx = index_to(ann[ann.year >= earliest], earliest)
        for g in order:
            sub = idx[idx.group == g].sort_values("year")
            if sub.empty:
                continue
            ax.plot(sub.year, sub["index"], lw=2.2, label=g, color=palette[g])
        ax.axhline(100, color="grey", lw=0.8, ls="--", alpha=0.7)
        ax.set_title(f"Indexed to {earliest} = 100")
        ax.set_ylabel(f"Index ({earliest} = 100)")
        ax.legend(loc="upper left", frameon=True)
        ax.set_xlabel("Year")

    plt.tight_layout()
    fig.savefig(CHART_DIR / "80_us_earnings_by_race.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

# ─────────────────────────────────────────────────────────────────────────────
# CHART 81 — Cross-country real average wages (OECD, 2022 PPP $)
# ─────────────────────────────────────────────────────────────────────────────
if not oecd.empty:
    print("[chart 81] Cross-country real average wages…")
    # Keep a curated set of major rich economies.
    WANT = {
        "USA": "United States",
        "GBR": "United Kingdom",
        "DEU": "Germany",
        "FRA": "France",
        "ITA": "Italy",
        "JPN": "Japan",
        "CAN": "Canada",
        "AUS": "Australia",
        "SWE": "Sweden",
        "NOR": "Norway",
    }
    sub = oecd[oecd.cc.isin(WANT)].copy()
    sub["country"] = sub.cc.map(WANT)
    sub = sub.groupby(["country", "year"], as_index=False).value.mean()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8))

    # Left: raw level in constant 2022 PPP USD
    ax = axes[0]
    palette = dict(
        zip(
            sorted(sub.country.unique()),
            sns.color_palette("tab10", n_colors=sub.country.nunique()),
        )
    )
    for c, grp in sub.groupby("country"):
        grp = grp.sort_values("year")
        ax.plot(grp.year, grp.value, lw=2.0, label=c, color=palette[c])
    ax.set_title("Real average annual wages\n(constant 2022 prices, 2022 USD PPPs)")
    ax.set_ylabel("Real annual wage (USD PPP)")
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    ax.legend(loc="best", ncol=2, fontsize=8, frameon=True)
    ax.set_xlabel("Year")

    # Right: indexed to 1990 = 100 to compare trajectories
    ax = axes[1]
    idx_rows = []
    for c, grp in sub.groupby("country"):
        grp = grp.sort_values("year")
        if grp.empty:
            continue
        base_year = max(1990, int(grp.year.min()))
        if base_year not in grp.year.values:
            continue
        base = grp.loc[grp.year == base_year, "value"].iloc[0]
        grp = grp.assign(index=100 * grp.value / base)
        idx_rows.append(grp)
    if idx_rows:
        idx = pd.concat(idx_rows, ignore_index=True)
        for c, grp in idx.groupby("country"):
            ax.plot(grp.year, grp["index"], lw=2.0, label=c, color=palette[c])
        ax.axhline(100, color="grey", lw=0.8, ls="--", alpha=0.7)
        ax.set_title(
            "Indexed to 1990 = 100\n(how much have real wages grown since 1990?)"
        )
        ax.set_ylabel("Index (1990 = 100)")
        ax.legend(loc="best", ncol=2, fontsize=8, frameon=True)
        ax.set_xlabel("Year")

    plt.tight_layout()
    fig.savefig(
        CHART_DIR / "81_crosscountry_real_wages.png", dpi=140, bbox_inches="tight"
    )
    plt.close(fig)

# ─────────────────────────────────────────────────────────────────────────────
# CHART 82 — Bottom-50% pre-tax income share, major economies (WID)
# ─────────────────────────────────────────────────────────────────────────────
if not wid.empty:
    print("[chart 82] Bottom-50% income share by country…")
    wanted_countries = list(WID_COUNTRIES.values())
    b50 = wid[(wid.percentile == "p0p50") & (wid.country_name.isin(wanted_countries))]

    fig, ax = plt.subplots(figsize=(11, 6))
    palette = dict(
        zip(
            sorted(b50.country_name.unique()),
            sns.color_palette("tab10", n_colors=b50.country_name.nunique()),
        )
    )
    for c, grp in b50.groupby("country_name"):
        grp = grp.sort_values("year")
        grp = grp[(grp.year >= 1980) & (grp.year <= 2024)]
        if grp.empty:
            continue
        ax.plot(grp.year, 100 * grp.value, lw=2.0, label=c, color=palette[c])
    ax.set_title(
        "Bottom 50% share of pre-tax national income, major economies\n"
        "(WID.world, sptinc992j — how much of pre-tax income accrues to the bottom half?)"
    )
    ax.set_ylabel("Share of pre-tax national income (%)")
    ax.set_xlabel("Year")
    ax.legend(loc="best", ncol=2, fontsize=9, frameon=True)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    plt.tight_layout()
    fig.savefig(
        CHART_DIR / "82_bottom50_income_share.png", dpi=140, bbox_inches="tight"
    )
    plt.close(fig)


print("\nDone. Charts written to charts/78 … 82.")
