#!/usr/bin/env python3
"""Download expanded inputs for the good-life threshold analysis.

This script keeps the broader downloader stable and fetches only the extra
outcome and resource measures needed for Analysis 19.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
RAW.mkdir(exist_ok=True, parents=True)
PROC.mkdir(exist_ok=True, parents=True)

session = requests.Session()
session.headers.update({"User-Agent": "GlobalGrowthAnalysis/1.0"})


def cached_get(
    url: str, filename: str, timeout: int = 120, binary: bool = True
) -> bytes | str:
    path = RAW / filename
    if path.exists() and path.stat().st_size > 100:
        print(f"  [cached] {filename}")
        mode = "rb" if binary else "r"
        with path.open(mode) as handle:
            return handle.read()

    print(f"  Downloading {filename}...")
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    content = response.content if binary else response.text
    mode = "wb" if binary else "w"
    with path.open(mode) as handle:
        handle.write(content)
    print(f"    -> {len(response.content) / 1024:.0f} KB")
    return content


WDI_EXTENDED = {
    # Resource measures
    "NE.CON.PRVT.PP.CD": "household_consumption_ppp_current",
    "NE.CON.PRVT.PC.KD": "household_consumption_pc_constant_2015usd",
    "NE.CON.TOTL.PC.KD": "final_consumption_pc_constant_2015usd",
    # Health and survival
    "SH.STA.MMRT": "maternal_mortality_per_100k",
    "SH.DYN.NMRT": "neonatal_mortality_per_1000",
    "SP.DYN.IMRT.IN": "infant_mortality_per_1000",
    "SH.STA.BRTC.ZS": "skilled_birth_attendance_pct",
    "SH.IMM.MEAS": "measles_immunization_pct",
    "SH.IMM.IDPT": "dpt_immunization_pct",
    # Nutrition
    "SN.ITK.DEFC.ZS": "undernourishment_pct",
    "SH.STA.STNT.ZS": "child_stunting_pct",
    "SH.STA.WAST.ZS": "child_wasting_pct",
    # Basic infrastructure and environment
    "EG.CFT.ACCS.ZS": "clean_cooking_access_pct",
    "EN.ATM.PM25.MC.M3": "pm25_exposure_ugm3",
    # Safety and human capital
    "VC.IHR.PSRC.P5": "homicide_per_100k",
    "HD.HCI.OVRL": "human_capital_index",
    "HD.HCI.LAYS": "learning_adjusted_years_school",
    "HD.HCI.EYRS": "expected_years_school",
    "HD.HCI.HLOS": "harmonized_test_score",
}


def fetch_wdi_extended() -> pd.DataFrame:
    print("=" * 70)
    print("WORLD BANK WDI: EXPANDED GOOD-LIFE INDICATORS")
    print("=" * 70)

    records: list[dict[str, object]] = []
    for code, name in WDI_EXTENDED.items():
        cache_file = f"wdi_good_life_{name}.json"
        cache_path = RAW / cache_file
        if cache_path.exists() and cache_path.stat().st_size > 100:
            print(f"  [cached] {name}")
            with cache_path.open() as handle:
                data = json.load(handle)
        else:
            print(f"  Fetching {name} ({code})...")
            url = (
                "https://api.worldbank.org/v2/country/all/indicator/"
                f"{code}?format=json&per_page=20000&date=1960:2025"
            )
            try:
                response = session.get(url, timeout=60)
                response.raise_for_status()
                data = response.json()
                with cache_path.open("w") as handle:
                    json.dump(data, handle)
                time.sleep(0.4)
            except Exception as exc:
                print(f"    FAILED: {exc}")
                continue

        count = 0
        if isinstance(data, list) and len(data) >= 2 and data[1]:
            for row in data[1]:
                value = row.get("value")
                code3 = row.get("countryiso3code")
                if value is None or not code3:
                    continue
                records.append(
                    {
                        "country_code": code3,
                        "country": row["country"]["value"],
                        "year": int(row["date"]),
                        "indicator": name,
                        "value": float(value),
                    }
                )
                count += 1
        print(f"    -> {count:,} obs")

    long = pd.DataFrame(records)
    if long.empty:
        print("  -> No WDI records downloaded")
        return long

    long.to_csv(PROC / "good_life_wdi_extended_long.csv", index=False)
    wide = long.pivot_table(
        index=["country_code", "country", "year"], columns="indicator", values="value"
    ).reset_index()
    wide.columns.name = None
    wide.to_csv(PROC / "good_life_wdi_extended.csv", index=False)
    print(
        f"\n  -> Extended WDI: {len(wide):,} rows, "
        f"{wide['country_code'].nunique():,} economies, saved to good_life_wdi_extended.csv"
    )
    return wide


def fetch_pip_extra_lines() -> None:
    print("\n" + "=" * 70)
    print("WORLD BANK PIP: HIGHER WELFARE BENCHMARK LINES")
    print("=" * 70)

    pip_base = "https://api.worldbank.org/pip/v1"
    for poverty_line in [2.15, 3.65, 6.85, 10.0, 15.0, 20.0, 25.0]:
        for endpoint, suffix, timeout in [
            ("pip", "country", 300),
            ("pip-grp", "regional", 240),
        ]:
            if endpoint == "pip":
                url = (
                    f"{pip_base}/{endpoint}?country=all&year=all&"
                    f"povline={poverty_line}&fill_gaps=true&format=csv"
                )
            else:
                url = (
                    f"{pip_base}/{endpoint}?group=wb&year=all&"
                    f"povline={poverty_line}&format=csv"
                )
            filename = f"pip_{suffix}_{poverty_line}.csv"
            try:
                cached_get(url, filename, timeout=timeout)
                time.sleep(1.0)
            except Exception as exc:
                print(f"    FAILED pip {suffix} {poverty_line}: {exc}")


def fetch_owid_grapher() -> None:
    print("\n" + "=" * 70)
    print("OUR WORLD IN DATA GRAPHER: WELLBEING CONTEXT")
    print("=" * 70)

    grapher_files = {
        "happiness-cantril-ladder": "good_life_owid_cantril_ladder.csv",
        "human-development-index": "good_life_owid_hdi.csv",
    }
    for slug, filename in grapher_files.items():
        url = f"https://ourworldindata.org/grapher/{slug}.csv"
        try:
            cached_get(url, filename, timeout=90)
            df = pd.read_csv(RAW / filename)
            df.to_csv(PROC / filename, index=False)
            print(f"    -> {len(df):,} rows copied to processed/{filename}")
        except Exception as exc:
            print(f"    FAILED {slug}: {exc}")


def main() -> None:
    fetch_wdi_extended()
    fetch_pip_extra_lines()
    fetch_owid_grapher()
    print("\nDone.")


if __name__ == "__main__":
    main()
