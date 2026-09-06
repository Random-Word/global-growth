#!/usr/bin/env python3
"""Validate local Markdown links and key generated analysis outputs."""

from pathlib import Path
import argparse
import re
import subprocess
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--publication", action="store_true", help="Also require linked source/charts in the Git index; data caches remain intentionally excluded")
args = parser.parse_args()
indexed = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=BASE).decode().split("\0")) if args.publication else set()
missing: list[tuple[str, str]] = []
for filename in ["README.md", "CLAIMS_EVIDENCE_APPENDIX.md", "WELLBEING_VALIDATION.md"]:
    text = (BASE / filename).read_text()
    for target in re.findall(r"!?\[[^]]*\]\(([^)#]+)(?:#[^)]*)?\)", text):
        if not target.startswith(("http://", "https://", "mailto:")):
            decoded = target.replace("%20", " ")
            if not (BASE / decoded).exists():
                missing.append((filename, target))
            elif args.publication and not decoded.startswith("data/") and decoded not in indexed:
                missing.append((filename, f"not staged/tracked: {target}"))
if args.publication:
    for number in range(1, 36):
        script = "analysis/run_analysis.py" if number == 1 else f"analysis/run_analysis_{number}.py"
        if script not in indexed:
            missing.append(("numbered pipeline", script))
print("missing_links", missing)
if missing:
    raise SystemExit(1)

outputs = [
    "dynamic_transfer_baseline_countries.csv",
    "dynamic_transfer_baseline_summary.csv",
    "dynamic_transfer_pip_reconciliation.csv",
    "dynamic_transfer_strategy_summary.csv",
    "dynamic_transfer_method_limits.csv",
    "fragile_state_group_summary.csv",
    "causal_development_estimates.csv",
    "causal_development_synthetic_fit.csv",
    "causal_development_method_limits.csv",
    "commodity_windfall_local_projections.csv",
    "commodity_windfall_two_way_sensitivity.csv",
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

estimates = pd.read_csv(BASE / "data/processed/causal_development_estimates.csv")
sparse = estimates.loc[estimates.status.eq("insufficient_support")]
assert sparse[["point_estimate", "ci_low", "ci_high"]].isna().all().all()
assert (sparse.n_events < sparse.required_events).all()
central = pd.read_csv(BASE / "data/processed/commodity_windfall_local_projections.csv")
sensitivity = pd.read_csv(BASE / "data/processed/commodity_windfall_two_way_sensitivity.csv")
assert central.covariance_type.eq("country_clustered").all()
assert sensitivity.covariance_type.eq("country_year_two_way_clustered").all()
assert not sensitivity.duplicated(["outcome", "horizon"]).any()
paired = sensitivity.merge(central, on=["outcome", "horizon"], validate="one_to_one", suffixes=("_two_way", "_country"))
assert len(paired) == len(sensitivity) == 18
assert (paired.estimate_two_way - paired.estimate_country).abs().lt(1e-9).all()
print("sparse-case and covariance consistency checks passed")
if args.publication:
    print("Publication source/chart links are staged or tracked. Raw/processed cache links require local regeneration, as documented.")
