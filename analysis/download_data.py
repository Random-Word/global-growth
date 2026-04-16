#!/usr/bin/env python3
"""Download datasets for global development analysis."""
import os, json, time, io, sys
import requests
import pandas as pd

BASE = "/Users/rstory/Repositories/global-growth"
RAW = os.path.join(BASE, "data", "raw")
PROC = os.path.join(BASE, "data", "processed")
os.makedirs(RAW, exist_ok=True)
os.makedirs(PROC, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "GlobalGrowthAnalysis/1.0"})


def cached_get(url, filename, timeout=120, binary=True):
    """Download URL to RAW dir; skip if cached and non-empty."""
    path = os.path.join(RAW, filename)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        print(f"  [cached] {filename}")
        with open(path, "rb" if binary else "r") as f:
            return f.read()
    print(f"  Downloading {filename}...")
    resp = session.get(url, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    content = resp.content if binary else resp.text
    with open(path, "wb" if binary else "w") as f:
        f.write(content)
    print(f"    -> {len(resp.content)/1024:.0f} KB")
    return content


# ============================================================
# 1. WORLD BANK WDI
# ============================================================
print("=" * 60)
print("WORLD BANK WDI INDICATORS")
print("=" * 60)

WDI = {
    "NY.GDP.MKTP.CD": "gdp_current_usd",
    "NY.GDP.MKTP.PP.CD": "gdp_ppp_current",
    "NY.GDP.MKTP.KD": "gdp_constant_2015usd",
    "NY.GDP.MKTP.PP.KD": "gdp_ppp_constant_2021",
    "NY.GDP.PCAP.PP.CD": "gdppc_ppp_current",
    "NY.GDP.PCAP.KD": "gdppc_constant_2015usd",
    "SP.POP.TOTL": "population",
    "SI.POV.GINI": "gini",
    "SP.DYN.LE00.IN": "life_expectancy",
    "SH.DYN.MORT": "under5_mortality",
    "NV.IND.MANF.ZS": "manufacturing_va_pct",
    # Development anatomy indicators
    "EG.ELC.ACCS.ZS": "electricity_access_pct",
    "SH.H2O.BASW.ZS": "basic_water_access_pct",
    "SH.STA.BASS.ZS": "basic_sanitation_pct",
    "SE.PRM.CMPT.ZS": "primary_completion_pct",
    "SE.SEC.ENRR": "secondary_enrollment_pct",
    "SE.ADT.LITR.ZS": "adult_literacy_pct",
    "SH.XPD.CHEX.PC.CD": "health_expenditure_pc",
    "NY.GNS.ICTR.ZS": "gross_savings_pct_gdp",
    "NE.GDI.FTOT.ZS": "gross_capital_formation_pct",
    "NV.AGR.TOTL.ZS": "agriculture_va_pct",
    "NV.SRV.TOTL.ZS": "services_va_pct",
    "SP.DYN.TFRT.IN": "fertility_rate",
    "IT.NET.USER.ZS": "internet_users_pct",
    "BX.KLT.DINV.WD.GD.ZS": "fdi_pct_gdp",
    "GC.TAX.TOTL.GD.ZS": "tax_revenue_pct_gdp",
    "NE.TRD.GNFS.ZS": "trade_pct_gdp",
}

all_wdi = []
for code, name in WDI.items():
    cache_file = f"wdi_{name}.json"
    cache_path = os.path.join(RAW, cache_file)

    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100:
        print(f"  [cached] {name}")
        with open(cache_path) as f:
            data = json.load(f)
    else:
        print(f"  Fetching {name} ({code})...")
        # Fetch up to 2 pages (20k records each) to cover all countries×years
        url = f"https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=20000&date=1960:2025"
        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            with open(cache_path, "w") as f:
                json.dump(data, f)
            time.sleep(0.5)
        except Exception as e:
            print(f"    FAILED: {e}")
            continue

    if isinstance(data, list) and len(data) >= 2 and data[1]:
        count = 0
        for r in data[1]:
            if r.get("value") is not None and r.get("countryiso3code"):
                all_wdi.append(
                    {
                        "country_code": r["countryiso3code"],
                        "country": r["country"]["value"],
                        "year": int(r["date"]),
                        "indicator": name,
                        "value": float(r["value"]),
                    }
                )
                count += 1
        print(f"    -> {count} obs")
    else:
        print(f"    -> No data")

if all_wdi:
    df_long = pd.DataFrame(all_wdi)
    df_wide = df_long.pivot_table(
        index=["country_code", "country", "year"], columns="indicator", values="value"
    ).reset_index()
    df_wide.columns.name = None
    out = os.path.join(PROC, "wdi_combined.csv")
    df_wide.to_csv(out, index=False)
    print(f"\n  -> Combined WDI: {len(df_wide)} rows, saved to wdi_combined.csv")

# ============================================================
# 2. WORLD BANK PIP (Poverty & Inequality Platform)
# ============================================================
print("\n" + "=" * 60)
print("WORLD BANK PIP POVERTY DATA")
print("=" * 60)

pip_base = "https://api.worldbank.org/pip/v1"
povlines = [2.15, 3.65, 6.85, 10.0]

for pl in povlines:
    # Country-level with gap-filling
    fname = f"pip_country_{pl}.csv"
    try:
        cached_get(
            f"{pip_base}/pip?country=all&year=all&povline={pl}&fill_gaps=true&format=csv",
            fname,
            timeout=180,
        )
        time.sleep(1.5)
    except Exception as e:
        print(f"    FAILED pip country {pl}: {e}")

    # Regional aggregates
    fname_r = f"pip_regional_{pl}.csv"
    try:
        cached_get(
            f"{pip_base}/pip-grp?group=wb&year=all&povline={pl}&format=csv",
            fname_r,
            timeout=60,
        )
        time.sleep(1.5)
    except Exception as e:
        print(f"    FAILED pip regional {pl}: {e}")

# ============================================================
# 3. MADDISON PROJECT DATABASE 2023
# ============================================================
print("\n" + "=" * 60)
print("MADDISON PROJECT DATABASE 2023")
print("=" * 60)

mpd_path = os.path.join(RAW, "maddison_mpd2023.xlsx")
if not (os.path.exists(mpd_path) and os.path.getsize(mpd_path) > 1000):
    for url in [
        "https://dataverse.nl/api/access/datafile/421302",
        "https://www.rug.nl/ggdc/historicaldevelopment/maddison/data/mpd2023.xlsx",
    ]:
        try:
            cached_get(url, "maddison_mpd2023.xlsx", timeout=120)
            # Verify it's a valid Excel file
            if os.path.getsize(mpd_path) > 1000:
                break
        except Exception as e:
            print(f"    Failed {url}: {e}")
else:
    print(f"  [cached] maddison_mpd2023.xlsx")

# Process Maddison if we have it
if os.path.exists(mpd_path) and os.path.getsize(mpd_path) > 1000:
    try:
        xls = pd.ExcelFile(mpd_path)
        print(f"  Sheets: {xls.sheet_names}")
        # The main data is usually in 'Full data' sheet
        for sheet in ["Full data", "data", "Sheet1", xls.sheet_names[0]]:
            if sheet in xls.sheet_names:
                df_mad = pd.read_excel(mpd_path, sheet_name=sheet)
                df_mad.to_csv(os.path.join(PROC, "maddison.csv"), index=False)
                print(f"  -> Maddison: {len(df_mad)} rows from sheet '{sheet}'")
                print(f"     Columns: {list(df_mad.columns)}")
                break
    except Exception as e:
        print(f"  Failed to parse Maddison: {e}")

# ============================================================
# 4. PENN WORLD TABLE 10.01
# ============================================================
print("\n" + "=" * 60)
print("PENN WORLD TABLE 10.01")
print("=" * 60)

pwt_path = os.path.join(RAW, "pwt1001.xlsx")
if not (os.path.exists(pwt_path) and os.path.getsize(pwt_path) > 1000):
    try:
        cached_get(
            "https://dataverse.nl/api/access/datafile/354098",
            "pwt1001.xlsx",
            timeout=180,
        )
    except Exception as e:
        print(f"  FAILED: {e}")
else:
    print(f"  [cached] pwt1001.xlsx")

if os.path.exists(pwt_path) and os.path.getsize(pwt_path) > 1000:
    try:
        xls = pd.ExcelFile(pwt_path)
        print(f"  Sheets: {xls.sheet_names}")
        for sheet in ["Data", "data", xls.sheet_names[0]]:
            if sheet in xls.sheet_names:
                df_pwt = pd.read_excel(pwt_path, sheet_name=sheet)
                df_pwt.to_csv(os.path.join(PROC, "pwt.csv"), index=False)
                print(f"  -> PWT: {len(df_pwt)} rows from sheet '{sheet}'")
                print(f"     Columns: {list(df_pwt.columns)[:15]}...")
                break
    except Exception as e:
        print(f"  Failed to parse PWT: {e}")

# ============================================================
# 5. OUR WORLD IN DATA - CO2
# ============================================================
print("\n" + "=" * 60)
print("OUR WORLD IN DATA")
print("=" * 60)

try:
    cached_get(
        "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv",
        "owid_co2.csv",
    )
except Exception as e:
    print(f"  FAILED OWID CO2: {e}")

# ============================================================
# 6. OECD REVENUE STATISTICS (Total Tax Revenue as % of GDP)
# ============================================================
print("\n" + "=" * 60)
print("OECD REVENUE STATISTICS — TOTAL TAX REVENUE (% GDP)")
print("=" * 60)

oecd_tax_path = os.path.join(PROC, "oecd_tax_revenue_pct_gdp.csv")
if os.path.exists(oecd_tax_path) and os.path.getsize(oecd_tax_path) > 100:
    print(f"  [cached] oecd_tax_revenue_pct_gdp.csv")
else:
    print("  Downloading OECD total tax/GDP from SDMX API...")
    oecd_dfs = []
    oecd_datasets = [
        ("DSD_REV_COMP_OECD@DF_RSOECD", "OECD"),
        ("DSD_REV_COMP_LAC@DF_RSLAC", "LAC"),
        ("DSD_REV_COMP_AFRICA@DF_RSAFRICA", "Africa"),
        ("DSD_REV_COMP_ASAP@DF_RSASAP", "Asia-Pacific"),
        ("DSD_REV_COMP_GLOBAL@DF_RSGLOBAL", "Global"),
    ]
    for ds_id, label in oecd_datasets:
        url = (
            f"https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,{ds_id},/"
            f".TAX_REV.S13._T..PT_B1GQ.A"
            f"?startPeriod=1965&endPeriod=2025&dimensionAtObservation=AllDimensions"
        )
        try:
            r = session.get(
                url,
                headers={"Accept": "application/vnd.sdmx.data+csv;version=2.0.0"},
                timeout=120,
            )
            if r.status_code == 200:
                df_oecd = pd.read_csv(io.StringIO(r.text))
                df_oecd["source"] = label
                n = df_oecd["REF_AREA"].nunique()
                print(f"    {label}: {len(df_oecd)} rows, {n} countries")
                oecd_dfs.append(df_oecd)
            else:
                print(f"    {label}: HTTP {r.status_code}")
            time.sleep(1)
        except Exception as e:
            print(f"    {label}: FAILED {e}")

    if oecd_dfs:
        oecd_all = pd.concat(oecd_dfs, ignore_index=True)
        oecd_all = oecd_all.drop_duplicates(
            subset=["REF_AREA", "TIME_PERIOD"], keep="first"
        )
        # Simplify to just the columns we need
        oecd_out = oecd_all[["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]].copy()
        oecd_out.columns = ["country_code", "year", "total_tax_pct_gdp"]
        oecd_out = oecd_out.dropna(subset=["total_tax_pct_gdp"])
        oecd_out.to_csv(oecd_tax_path, index=False)
        print(
            f"  -> OECD tax/GDP: {len(oecd_out)} rows, {oecd_out['country_code'].nunique()} countries"
        )
    else:
        print("  -> FAILED: no OECD data downloaded")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("DOWNLOAD SUMMARY")
print("=" * 60)
for label, d in [("Raw", RAW), ("Processed", PROC)]:
    print(f"\n{label} ({d}):")
    if os.path.exists(d):
        for f in sorted(os.listdir(d)):
            s = os.path.getsize(os.path.join(d, f))
            print(f"  {f:45s} {s/1024:>8.0f} KB")
    else:
        print("  (empty)")

print("\nDone!")
