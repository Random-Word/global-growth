#!/usr/bin/env python3
"""One-off: append Malawi (MWI) WDI rows to wdi_development_theories.csv.

Mirrors the long format (cc,year,value,indicator,country) of the existing file.
oda_pct_gni_donor is a donor-side metric and is intentionally not fetched for a
recipient country like Malawi.
"""

import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
CSV = BASE / "data" / "raw" / "wdi_development_theories.csv"

CODES = {
    "gdppc_ppp": "NY.GDP.PCAP.PP.CD",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "gross_fixed_capital_pct_gdp": "NE.GDI.FTOT.ZS",
    "gross_savings_pct_gdp": "NY.GNS.ICTR.ZS",
    "trade_pct_gdp": "NE.TRD.GNFS.ZS",
    "fdi_pct_gdp": "BX.KLT.DINV.WD.GD.ZS",
    "fertility_rate": "SP.DYN.TFRT.IN",
    "primary_completion": "SE.PRM.CMPT.ZS",
    "tertiary_enrollment": "SE.TER.ENRR",
    "oda_net_current_usd": "DT.ODA.ODAT.CD",
    "remittances_pct_gdp": "BX.TRF.PWKR.DT.GD.ZS",
    "pop_growth": "SP.POP.GROW",
    "edu_spending_pct_gdp": "SE.XPD.TOTL.GD.ZS",
}

rows = []
counts: dict[str, int] = {}
for name, code in CODES.items():
    url = (
        f"https://api.worldbank.org/v2/country/MWI/indicator/{code}"
        "?date=1960:2025&per_page=20000&format=json"
    )
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()  # fail loudly on HTTP errors
    js = resp.json()
    n = 0
    if len(js) >= 2 and js[1]:
        for o in js[1]:
            if o["value"] is None:
                continue
            rows.append(
                {
                    "cc": "MWI",
                    "year": int(o["date"]),
                    "value": float(o["value"]),
                    "indicator": name,
                    "country": "Malawi",
                }
            )
            n += 1
    else:
        print(f"  WARNING: no data returned for {name} ({code})")
    counts[name] = n
    print(f"{name:32s} {n:4d} rows")
    time.sleep(0.2)

print("\n── row counts by indicator ──")
for name, n in counts.items():
    print(f"{name:32s} {n:4d}")

new = pd.DataFrame(rows)
d = pd.read_csv(CSV)
d = d[d.cc != "MWI"]  # idempotent re-run
out = pd.concat([d, new], ignore_index=True)
out.to_csv(CSV, index=False)
print(f"\nappended {len(new)} MWI rows; total countries {out.cc.nunique()}")
print(f"MWI year range {int(new.year.min())}-{int(new.year.max())}")
