#!/usr/bin/env python3
"""Analysis 26: withdrawn joint-probability synthesis (compatibility entry point).

The legacy nitrogen marginal mixed incompatible flows and boundary definitions.
Calling it a judgmental prior did not validate the resulting joint or partial-
success probabilities. The old Monte Carlo model is retired, not recalibrated.
Its source remains in version history; no numeric fallback is provided here.

Default execution overwrites both legacy CSVs and charts 114/115 with withdrawal
notices and returns normally so sequential analysis pipelines can continue.
No upstream data are read, including stale copies of the invalid nitrogen table.
"""

from pathlib import Path

from ecological_safeguards import JOINT_REASON, withdrawal_chart, withdrawn_table

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"


def main() -> None:
    """Publish status-only artifacts; never infer replacement probabilities."""
    PROC.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    for name in ("scenario_joint_probability.csv", "scenario_claim_mapping.csv"):
        withdrawn_table(JOINT_REASON).to_csv(PROC / name, index=False)
    for name, title in (
        (
            "114_joint_scenario_probability.png",
            "Chart 114: Joint probability withdrawn",
        ),
        (
            "115_conditions_met_distribution.png",
            "Chart 115: Conditions-met distribution withdrawn",
        ),
    ):
        withdrawal_chart(CHARTS / name, title, JOINT_REASON)
    print("Analysis 26: joint and partial-success probabilities WITHDRAWN.")
    print(JOINT_REASON)
    print("Saved status-only CSVs and withdrawal notices for charts 114/115.")


if __name__ == "__main__":
    main()
