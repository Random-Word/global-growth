#!/usr/bin/env python3
"""Validate local Markdown links and key generated analysis outputs."""

from pathlib import Path
import re
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
missing: list[tuple[str, str]] = []
for filename in ["README.md", "CLAIMS_EVIDENCE_APPENDIX.md", "WELLBEING_VALIDATION.md"]:
    text = (BASE / filename).read_text()
    for target in re.findall(r"!?\[[^]]*\]\(([^)#]+)(?:#[^)]*)?\)", text):
        if not target.startswith(("http://", "https://", "mailto:")):
            decoded = target.replace("%20", " ")
            if not (BASE / decoded).exists():
                missing.append((filename, target))
print("missing_links", missing)
if missing:
    raise SystemExit(1)

outputs = [
    "commodity_windfall_local_projections.csv",
    "commodity_windfall_robustness.csv",
    "commodity_windfall_category_estimates.csv",
    "commodity_windfall_year_influence.csv",
    "global_sensitivity_sobol_indices.csv",
    "global_sensitivity_reversal_regions.csv",
    "wellbeing_validation_panel.csv",
    "wellbeing_validation_score_sensitivity.csv",
    "wellbeing_validation_resource_models.csv",
    "wellbeing_validation_within_country.csv",
    "wellbeing_validation_frontier.csv",
]
for filename in outputs:
    frame = pd.read_csv(BASE / "data" / "processed" / filename)
    if frame.empty or frame.columns.duplicated().any():
        raise ValueError(f"Invalid output: {filename}")
    print(filename, len(frame))

for filename in [
    "robustness_nitrogen_uncertainty.csv",
    "scenario_joint_probability.csv",
    "joint_probability_audit.csv",
    "scenario_calibration_partial_identification.csv",
]:
    frame = pd.read_csv(BASE / "data/processed" / filename)
    assert frame["status"].eq("withdrawn").all(), filename
    assert list(frame.select_dtypes("number").columns) == [], filename
panel = pd.read_csv(BASE / "data/processed/wellbeing_validation_panel.csv")
assert not panel.duplicated(["country_code", "year"]).any()
assert panel.life_satisfaction.between(0, 10).all()
assert (panel.year - panel.window_start).eq(2).all()
assert not panel.country_code.str.startswith("OWID").any()
print("withdrawal schemas and wellbeing measurement checks passed")
