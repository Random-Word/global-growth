#!/usr/bin/env python3
"""Analysis 32: scenario evidence audit; legacy joint calculations WITHDRAWN.

The nitrogen marginal inherited an invalid mixed-flow compliance calculation.
The numerical bounds, copula, leave-one-out and information-ranking builders
below are retained for provenance but fail closed. Default execution publishes
an unassessed nitrogen gate and explicit withdrawal records, not new probabilities.

The earlier green-growth synthesis reported a precise joint probability from
five author-assigned marginals and author-assigned Gaussian-copula loadings.
That number is not empirically identified. This extension separates three kinds
of input evidence and replaces the point probability with an unpriced scenario
framework:

1. OBSERVED FREQUENCY: repeated outcomes with a defined denominator. None of the
   five global 2050 conditions has a valid repeated historical denominator.
2. EXTERNAL/REPOSITORY BENCHMARK: measured current status, engineering target,
   or literature threshold already represented in the repository. These can
   calibrate a level or threshold, but not a probability of global success.
3. PURE AUTHOR JUDGMENT: probability ranges or dependence assumptions without a
   frequency-calibrated forecast record. These are retained only as transparent
   stress tests, never as empirical confidence intervals.

Outputs:
- data/processed/scenario_calibration_evidence_audit.csv
- data/processed/scenario_calibration_feasibility_matrix.csv
- data/processed/scenario_calibration_partial_identification.csv
- data/processed/scenario_calibration_dependence_sensitivity.csv
- data/processed/scenario_calibration_leave_one_out.csv
- data/processed/scenario_calibration_value_of_information.csv
- data/processed/scenario_calibration_break_even.csv
- data/processed/scenario_calibration_summary.csv
- charts/136_scenario_feasibility_matrix.png
- charts/137_scenario_partial_identification.png
- charts/138_scenario_value_of_information.png

Any simulated probabilities below are conditional outputs under stated author
ranges. They are not empirical estimates or empirical confidence intervals.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path

from ecological_safeguards import (
    JOINT_REASON,
    LEGACY_N_REASON,
    withdrawal_chart,
    withdrawn_table,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import norm

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
RAW = BASE / "data" / "raw"
CHARTS = BASE / "charts"
PROC.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", palette="colorblind")
plt.rcParams.update(
    {
        "figure.figsize": (12, 7),
        "font.size": 10.5,
        "axes.titlesize": 13,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)

CONDITIONS = ["carbon", "nitrogen", "biodiversity_land", "material", "political"]
LABELS = {
    "carbon": "Carbon budget",
    "nitrogen": "Nitrogen boundary",
    "biodiversity_land": "Biodiversity / land",
    "material": "Material throughput",
    "political": "Durable redistribution",
}
SHORT_LABELS = {
    "carbon": "Carbon",
    "nitrogen": "Nitrogen",
    "biodiversity_land": "Biodiversity\n& land",
    "material": "Materials",
    "political": "Redistribution",
}

# These are the ranges used by Analysis 26 for the well-below-2C five-condition
# model. Legacy provenance only; the invalid N marginal has been removed.
JUDGMENT_RANGES: dict[str, tuple[float, float]] = {
    "carbon": (0.15, 0.40),
    "nitrogen": (np.nan, np.nan),
    "biodiversity_land": (0.10, 0.35),
    "material": (0.25, 0.50),
    "political": (0.15, 0.40),
}
CENTRAL = {
    "carbon": 0.25,
    "nitrogen": np.nan,
    "biodiversity_land": 0.20,
    "material": 0.35,
    "political": 0.25,
}
LOADINGS = {
    "carbon": 0.65,
    "nitrogen": 0.45,
    "biodiversity_land": 0.50,
    "material": 0.55,
    "political": 0.70,
}

SCENARIOS: dict[str, dict[str, int]] = {
    "Current trajectory": {
        "carbon": 0,
        "nitrogen": 0,
        "biodiversity_land": 0,
        "material": 0,
        "political": 0,
    },
    "Deployment acceleration": {
        "carbon": 1,
        "nitrogen": 0,
        "biodiversity_land": 0,
        "material": 0,
        "political": 0,
    },
    "Technology + circularity": {
        "carbon": 1,
        "nitrogen": 1,
        "biodiversity_land": 0,
        "material": 1,
        "political": 0,
    },
    "Integrated global package": {
        "carbon": 1,
        "nitrogen": 1,
        "biodiversity_land": 1,
        "material": 1,
        "political": 1,
    },
}


@dataclass(frozen=True)
class EvidenceRow:
    condition: str
    observed_frequency_calibration: str
    repository_external_benchmark: str
    benchmark_kind: str
    pure_author_judgment: str
    calibrated_probability_available: bool
    status_now: str
    success_definition: str
    data_needed: str
    identification_conclusion: str


def save_csv(frame: pd.DataFrame, filename: str) -> Path:
    path = PROC / filename
    frame.to_csv(path, index=False)
    print(f"  saved {path.relative_to(BASE)} ({len(frame):,} rows)")
    return path


def load_anchors() -> dict[str, float]:
    material = pd.read_csv(PROC / "robustness_material_uncertainty.csv").set_index(
        "metric"
    )["value"]
    energy = pd.read_csv(RAW / "energy_transition" / "owid-energy-data.csv")
    world_2024 = energy[energy["country"].eq("World") & energy["year"].eq(2024)].iloc[0]
    transfer = pd.read_csv(PROC / "robustness_poverty_cost_sensitivity.csv")
    transfer_685 = transfer[
        transfer["poverty_line"].eq(6.85) & transfer["overhead_multiplier"].eq(1)
    ].iloc[0]
    return {
        "material_median": float(material["median_total_t_per_cap"]),
        "material_p10": float(material["p10_total_t_per_cap"]),
        "material_p90": float(material["p90_total_t_per_cap"]),
        "material_le_9": float(material["prob_below_9_0_t"]),
        "material_le_11": float(material["prob_below_11_0_t"]),
        "fossil_share_2024": float(world_2024["fossil_share_energy"]),
        "solar_wind_twh_2024": float(
            world_2024["solar_electricity"] + world_2024["wind_electricity"]
        ),
        "transfer_685_pct_gdp": float(transfer_685["cost_pct_world_gdp"]),
        "transfer_685_oda_coverage": float(transfer_685["oda_coverage_ratio"]),
    }


def build_evidence_audit(a: dict[str, float]) -> pd.DataFrame:
    rows = [
        EvidenceRow(
            "carbon",
            "None: one world trajectory and an unfinished 2050 outcome provide no repeated-event denominator.",
            f"Observed 2024 solar+wind generation {a['solar_wind_twh_2024']:,.0f} TWh versus repository 2030 waypoints 12,000 TWh (~2C/APS) and 16,400 TWh (1.5C/NZE); fossil share of primary energy {a['fossil_share_2024']:.1f}%.",
            "Observed trajectory + external engineering/pathway benchmark",
            "Analysis 26 assigns 0.15/0.25/0.40 for well-below-2C and copula loading 0.65.",
            False,
            "Not on the repository's 1.5C waypoint; approximately compatible with its ~2C renewables waypoint only if recent deployment continues and displaces fossil energy.",
            "Remain within a stated cumulative carbon budget while delivering the welfare pathway through 2050.",
            "A preregistered annual global pathway scorecard with emissions, fossil displacement, grids, storage, hard-sector output, and calibrated forecast errors.",
            "Benchmark-calibrated threshold, not probability-calibrated.",
        ),
        EvidenceRow(
            "nitrogen",
            "None: triangular intervention draws are parameter perturbations, not frequencies of global technology/adoption success.",
            LEGACY_N_REASON,
            "Invalid legacy comparison; no compatible model benchmark",
            "The inherited nitrogen marginal is withdrawn; it cannot price this gate.",
            False,
            "Unassessed: no valid total-N accounting model is available.",
            "Total industrial + intentional biological fixation must be modeled against a compatible control variable; Richardson 2023 reports 62 Tg/yr and about 190 Tg/yr current total.",
            "Separate gross fixation, fertilizer substitution, nutrient losses and runoff treatment; establish net effects, overlap and adoption without counting biological substitution as automatic avoided fixation.",
            "Neither compliance nor a success probability is identified.",
        ),
        EvidenceRow(
            "biodiversity_land",
            "None: no repeated global reversals comparable to a 2050-2070 halt-and-reverse endpoint.",
            "LPI is complementary biodiversity evidence, not a planetary-boundary control variable. Richardson 2023 assesses biosphere integrity and land-system change as transgressed; no local LPI boundary ratio is valid.",
            "External literature status benchmark",
            "Analysis 26 assigns 0.10/0.20/0.35 and loading 0.50; no model maps food technology or governance to reversal.",
            False,
            "Currently infeasible on measured status; future reversal is unmodeled and partly irreversible.",
            "By a fixed date, net habitat conversion is non-positive and pre-agreed biosphere/land indicators show sustained recovery with rights safeguards.",
            "Globally consistent annual habitat-condition, extinction-risk, land-use, restoration-survival, Indigenous-tenure, and food-land displacement data linked to policy exposure.",
            "Status-calibrated only; pathway and probability unpriced.",
        ),
        EvidenceRow(
            "material",
            "None: triangular category draws encode assumed ranges and have no historical forecast-validation denominator.",
            f"Post-transition scenario median {a['material_median']:.1f} t/cap (p10-p90 {a['material_p10']:.1f}-{a['material_p90']:.1f}); conditional draw shares <=9 and <=11 t/cap are {a['material_le_9']:.4f} and {a['material_le_11']:.3f}.",
            "Repository scenario + contested literature mass threshold",
            "Analysis 26 assigns an 'acceptable composition' probability of 0.25/0.35/0.50 and loading 0.55, despite lacking damage weights.",
            False,
            "A 9 t/cap mass endpoint is outside almost all scenario draws; ecological acceptability near 11 t/cap cannot be scored without composition/damage weights.",
            "Rich-world footprint reaches a declared mass or damage-weighted ceiling while welfare remains above the chosen floor.",
            "Harmonized consumption footprints by category and origin, recycling losses, rebound, and peer-reviewed damage weights tied to boundary-specific impacts.",
            "Mass scenario is bounded; ecological success is not identified.",
        ),
        EvidenceRow(
            "political",
            "No comparable observed-frequency calibration: Marshall-style episodes are selected, heterogeneous, and do not define durable global redistribution success.",
            f"Legacy approximate fiscal comparison: one-times-delivery $6.85/day gap {a['transfer_685_pct_gdp']:.2f}% of world GDP; ODA/gap scale ratio {100*a['transfer_685_oda_coverage']:.1f}%, not available financing or delivered coverage. ODA is not wholly cash transfers; vintages and nominal conversion require reconciliation. Marshall/reconstruction cases do not define a base rate.",
            "Repository fiscal arithmetic + selected historical cases",
            "Analysis 26 assigns 0.15/0.25/0.40 and the highest required-condition loading (0.70).",
            False,
            "Fiscally measurable but institutionally unpriced; no global mechanism commits the required multi-decade flow.",
            "A specified transfer/adaptation regime is funded, delivered, and sustained for a declared duration with recipient-level coverage and graduation rules.",
            "A denominator of proposed and enacted cross-border compacts, annual promised-versus-disbursed flows, durability, recipient coverage, delivery incidence, and exit/graduation outcomes.",
            "Cost-calibrated, not political-probability calibrated.",
        ),
    ]
    frame = pd.DataFrame([r.__dict__ for r in rows])
    frame["condition_label"] = frame["condition"].map(LABELS)
    frame["author_range_low"] = frame["condition"].map(
        {k: v[0] for k, v in JUDGMENT_RANGES.items()}
    )
    frame["author_range_high"] = frame["condition"].map(
        {k: v[1] for k, v in JUDGMENT_RANGES.items()}
    )
    return frame


def build_feasibility_matrix() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    notes = {
        (
            "Current trajectory",
            "carbon",
        ): "Renewables scale, but fossil primary-energy share remains ~81%; no demonstrated budget-compatible full-system path.",
        (
            "Current trajectory",
            "nitrogen",
        ): LEGACY_N_REASON,
        (
            "Current trajectory",
            "biodiversity_land",
        ): "Biosphere and land transgressions in the 2023 literature; LPI is not a PB control variable. No modeled global reversal.",
        (
            "Current trajectory",
            "material",
        ): "Global absolute material use still rises; rich-world footprint remains far above 9-11 t/cap.",
        (
            "Current trajectory",
            "political",
        ): "ODA and climate-finance delivery remain below stated commitments and modeled need.",
        (
            "Deployment acceleration",
            "carbon",
        ): "Feasible only if generation additions translate into fossil displacement, grids, storage, and hard-sector decarbonization.",
        (
            "Deployment acceleration",
            "nitrogen",
        ): LEGACY_N_REASON,
        (
            "Deployment acceleration",
            "biodiversity_land",
        ): "Clean energy alone does not release land or restore ecosystems.",
        (
            "Deployment acceleration",
            "material",
        ): "Fossil extraction falls, but rebound, construction, biomass, and metals remain unresolved.",
        (
            "Deployment acceleration",
            "political",
        ): "Domestic deployment does not create a durable cross-border transfer regime.",
        (
            "Technology + circularity",
            "carbon",
        ): "Electrification plus storage/hard-sector progress can define a pathway; cumulative budget remains binding.",
        (
            "Technology + circularity",
            "nitrogen",
        ): LEGACY_N_REASON,
        (
            "Technology + circularity",
            "biodiversity_land",
        ): "Food-land release is not sufficient without restoration, governance, and rights safeguards.",
        (
            "Technology + circularity",
            "material",
        ): "Mass endpoint near 10-12 t/cap is plausible in the repository scenario; ecological acceptability is unscored.",
        (
            "Technology + circularity",
            "political",
        ): "Technology does not fund or enforce multi-decade redistribution.",
        (
            "Integrated global package",
            "carbon",
        ): "Required and threshold-defined; feasibility depends on deployment and cumulative emissions.",
        (
            "Integrated global package",
            "nitrogen",
        ): LEGACY_N_REASON,
        (
            "Integrated global package",
            "biodiversity_land",
        ): "Required; reversal needs explicit land, restoration, and governance mechanisms.",
        (
            "Integrated global package",
            "material",
        ): "Required; must declare whether success is a mass ceiling or damage-weighted ceiling.",
        (
            "Integrated global package",
            "political",
        ): "Required; institution, burden-sharing rule, and enforcement mechanism are unspecified.",
    }
    labels = {
        0: "Fails / no pathway",
        1: "Conditional / unpriced",
        2: "Unassessed / invalid model",
    }
    for scenario, values in SCENARIOS.items():
        for condition in CONDITIONS:
            code = 2 if condition == "nitrogen" else values[condition]
            rows.append(
                {
                    "scenario": scenario,
                    "condition": condition,
                    "condition_label": LABELS[condition],
                    "feasibility_code": code,
                    "feasibility_status": labels[code],
                    "note": notes[(scenario, condition)],
                }
            )
    return pd.DataFrame(rows)


def frechet_all_bounds(probs: np.ndarray) -> tuple[float, float]:
    """Sharp no-assumption bounds for intersection of Bernoulli events."""
    return max(0.0, float(probs.sum()) - (len(probs) - 1)), float(probs.min())


def require_valid_nitrogen() -> None:
    """Fail closed rather than recycle a withdrawn N marginal as author judgment."""
    raise ValueError(JOINT_REASON)


def enumerate_range_corners() -> list[np.ndarray]:
    require_valid_nitrogen()
    return [
        np.array(values, dtype=float)
        for values in itertools.product(*[JUDGMENT_RANGES[c] for c in CONDITIONS])
    ]


def build_partial_identification() -> pd.DataFrame:
    require_valid_nitrogen()
    low = np.array([JUDGMENT_RANGES[c][0] for c in CONDITIONS])
    high = np.array([JUDGMENT_RANGES[c][1] for c in CONDITIONS])
    central = np.array([CENTRAL[c] for c in CONDITIONS])
    rows: list[dict[str, object]] = []
    for name, probs in [
        ("author_low", low),
        ("author_central", central),
        ("author_high", high),
    ]:
        lo, hi = frechet_all_bounds(probs)
        rows.extend(
            [
                {
                    "marginal_set": name,
                    "identification_assumption": "No dependence assumption (Frechet-Hoeffding)",
                    "lower_bound": lo,
                    "upper_bound": hi,
                    "point_if_applicable": np.nan,
                    "interpretation": "Sharp logical bounds given marginals; dependence unrestricted.",
                },
                {
                    "marginal_set": name,
                    "identification_assumption": "Independence imposed",
                    "lower_bound": float(np.prod(probs)),
                    "upper_bound": float(np.prod(probs)),
                    "point_if_applicable": float(np.prod(probs)),
                    "interpretation": "Conditional calculation, not empirically identified.",
                },
            ]
        )
    lo_all, _ = frechet_all_bounds(low)
    _, hi_all = frechet_all_bounds(high)
    products = [float(np.prod(p)) for p in enumerate_range_corners()]
    rows.extend(
        [
            {
                "marginal_set": "author_ranges",
                "identification_assumption": "Ranges + unrestricted dependence",
                "lower_bound": lo_all,
                "upper_bound": hi_all,
                "point_if_applicable": np.nan,
                "interpretation": "Overall partial-identification region across author ranges and all valid dependence structures.",
            },
            {
                "marginal_set": "author_ranges",
                "identification_assumption": "Ranges + independence",
                "lower_bound": min(products),
                "upper_bound": max(products),
                "point_if_applicable": np.nan,
                "interpretation": "Conditional range if independence is imposed.",
            },
        ]
    )
    return pd.DataFrame(rows)


def gaussian_joint_quadrature(probs: np.ndarray, loadings: np.ndarray) -> float:
    """Deterministic one-factor Gaussian-copula intersection probability."""
    nodes, weights = np.polynomial.hermite.hermgauss(80)
    z = np.sqrt(2.0) * nodes
    thresholds = norm.ppf(probs)
    conditional = norm.cdf(
        (thresholds[None, :] - z[:, None] * loadings[None, :])
        / np.sqrt(1.0 - loadings[None, :] ** 2)
    )
    return float(np.sum(weights * np.prod(conditional, axis=1)) / np.sqrt(np.pi))


def build_dependence_sensitivity() -> pd.DataFrame:
    require_valid_nitrogen()
    central = np.array([CENTRAL[c] for c in CONDITIONS])
    base = np.array([LOADINGS[c] for c in CONDITIONS])
    structures: dict[str, np.ndarray | None] = {
        "Frechet lower (unrestricted)": None,
        "Mixed signs": base * np.array([1, 1, -1, -1, -1]),
        "Independence": np.zeros(len(CONDITIONS)),
        "Positive loading 0.5x": np.clip(base * 0.5, -0.95, 0.95),
        "Positive loading 1.0x": np.clip(base, -0.95, 0.95),
        "Positive loading 1.3x": np.clip(base * 1.3, -0.95, 0.95),
        "Comonotonic upper bound": None,
    }
    lower, upper = frechet_all_bounds(central)
    rows: list[dict[str, object]] = []
    for name, loads in structures.items():
        if name.startswith("Frechet lower"):
            joint = lower
            kind = "sharp logical bound"
        elif name.startswith("Comonotonic"):
            joint = upper
            kind = "sharp logical bound"
        elif name == "Independence":
            joint = float(np.prod(central))
            kind = "conditional analytic calculation"
        else:
            assert loads is not None
            joint = gaussian_joint_quadrature(central, loads)
            kind = "conditional deterministic copula calculation"
        rows.append(
            {
                "dependence_structure": name,
                "joint_all": joint,
                "calculation_kind": kind,
                "empirically_calibrated": False,
                "note": "No interval is an empirical confidence interval; dependence is imposed, not estimated.",
            }
        )
    return pd.DataFrame(rows)


def build_leave_one_out() -> pd.DataFrame:
    require_valid_nitrogen()
    rows: list[dict[str, object]] = []
    central = np.array([CENTRAL[c] for c in CONDITIONS])
    full_product = float(np.prod(central))
    for i, condition in enumerate(CONDITIONS):
        remaining = np.delete(central, i)
        independent = float(np.prod(remaining))
        lo, hi = frechet_all_bounds(remaining)
        rows.append(
            {
                "omitted_condition": condition,
                "omitted_label": LABELS[condition],
                "four_condition_independent": independent,
                "increase_vs_five_condition_independent": independent - full_product,
                "ratio_vs_five_condition_independent": independent / full_product,
                "four_condition_frechet_low": lo,
                "four_condition_frechet_high": hi,
                "interpretation": "Diagnostic deletion, not a claim that the omitted condition is unnecessary.",
            }
        )
    return pd.DataFrame(rows).sort_values(
        "increase_vs_five_condition_independent", ascending=False
    )


def build_value_of_information() -> pd.DataFrame:
    require_valid_nitrogen()
    rows: list[dict[str, object]] = []
    central = np.array([CENTRAL[c] for c in CONDITIONS])
    widths = {c: JUDGMENT_RANGES[c][1] - JUDGMENT_RANGES[c][0] for c in CONDITIONS}
    # Independence derivative d(product p)/dp_i = product of all other marginals.
    # This is a transparent local sensitivity diagnostic, not an expected-value
    # calculation in dollars (the scenario is intentionally unpriced).
    for i, condition in enumerate(CONDITIONS):
        derivative = float(np.prod(np.delete(central, i)))
        low, high = JUDGMENT_RANGES[condition]
        product_low = float(
            np.prod(np.where(np.arange(len(CONDITIONS)) == i, low, central))
        )
        product_high = float(
            np.prod(np.where(np.arange(len(CONDITIONS)) == i, high, central))
        )
        decision_swing = product_high - product_low
        rows.append(
            {
                "condition": condition,
                "condition_label": LABELS[condition],
                "evidence_gap": (
                    "No calibrated probability"
                    if condition != "political"
                    else "No political base rate"
                ),
                "author_range_low": low,
                "author_range_high": high,
                "author_range_width": widths[condition],
                "local_independence_derivative": derivative,
                "independence_joint_at_low": product_low,
                "independence_joint_at_high": product_high,
                "independence_joint_swing": decision_swing,
                "voi_score": decision_swing,
                "data_priority": {
                    "carbon": "Forecast-validation panel for annual global decarbonization milestones and bottlenecks.",
                    "nitrogen": "Field/adoption distributions and overlap for every Tier-3 nitrogen lever.",
                    "biodiversity_land": "Annual global habitat-condition and restoration-outcome data linked to land/food policy.",
                    "material": "Damage-weighted category footprints, recycling losses, and rebound.",
                    "political": "Denominator and durability data for proposed, funded, disbursed, and sustained cross-border compacts.",
                }[condition],
            }
        )
    frame = (
        pd.DataFrame(rows)
        .sort_values("voi_score", ascending=False)
        .reset_index(drop=True)
    )
    frame["voi_rank"] = np.arange(1, len(frame) + 1)
    return frame


def build_break_even() -> pd.DataFrame:
    require_valid_nitrogen()
    rows: list[dict[str, object]] = []
    targets = [0.001, 0.005, 0.01, 0.025, 0.05]
    central = np.array([CENTRAL[c] for c in CONDITIONS])
    for target in targets:
        equal = target ** (1 / len(CONDITIONS))
        for i, condition in enumerate(CONDITIONS):
            other_product = float(np.prod(np.delete(central, i)))
            required = target / other_product
            rows.append(
                {
                    "target_joint": target,
                    "target_joint_pct": 100 * target,
                    "condition": condition,
                    "condition_label": LABELS[condition],
                    "required_marginal_if_others_central_independent": required,
                    "feasible_probability": required <= 1,
                    "required_marginal_interpretation": (
                        f"{100 * required:.1f}%"
                        if required <= 1
                        else f"impossible ({required:.2f} > 1)"
                    ),
                    "equal_marginal_required_if_all_equal": equal,
                    "assumption": "Independence; all non-varied marginals fixed at Analysis 26 central judgments.",
                }
            )
    return pd.DataFrame(rows)


def build_summary(
    anchors: dict[str, float],
    partial: pd.DataFrame,
    dependence: pd.DataFrame,
    leave_out: pd.DataFrame,
    voi: pd.DataFrame,
    break_even: pd.DataFrame,
) -> pd.DataFrame:
    require_valid_nitrogen()
    lookup = dependence.set_index("dependence_structure")["joint_all"]
    unrestricted = partial[
        partial["identification_assumption"].eq("Ranges + unrestricted dependence")
    ].iloc[0]
    independent_range = partial[
        partial["identification_assumption"].eq("Ranges + independence")
    ].iloc[0]
    equal_1pct = float(
        break_even[break_even["target_joint"].eq(0.01)][
            "equal_marginal_required_if_all_equal"
        ].iloc[0]
    )
    return pd.DataFrame(
        [
            {
                "metric": "calibrated_marginal_probabilities_available",
                "value": 0,
                "unit": "of 5 conditions",
                "interpretation": "No condition has a validated observed-frequency forecast calibration for the global endpoint.",
            },
            {
                "metric": "identified_joint_probability",
                "value": np.nan,
                "unit": "probability",
                "interpretation": "Not identified; report a scenario matrix and thresholds rather than a single probability.",
            },
            {
                "metric": "author_range_unrestricted_dependence_low",
                "value": unrestricted["lower_bound"],
                "unit": "probability",
                "interpretation": "Sharp lower logical bound conditional on accepting the author marginal ranges.",
            },
            {
                "metric": "author_range_unrestricted_dependence_high",
                "value": unrestricted["upper_bound"],
                "unit": "probability",
                "interpretation": "Sharp upper logical bound; equals the smallest allowed high marginal.",
            },
            {
                "metric": "author_range_independence_low",
                "value": independent_range["lower_bound"],
                "unit": "probability",
                "interpretation": "Conditional product at all low author judgments.",
            },
            {
                "metric": "author_range_independence_high",
                "value": independent_range["upper_bound"],
                "unit": "probability",
                "interpretation": "Conditional product at all high author judgments.",
            },
            {
                "metric": "conditional_scenario_mixed_sign_joint_not_calibrated",
                "value": lookup["Mixed signs"],
                "unit": "conditional scenario output",
                "interpretation": "Not a calibrated probability or confidence interval.",
            },
            {
                "metric": "conditional_scenario_independence_joint_not_calibrated",
                "value": lookup["Independence"],
                "unit": "conditional scenario output",
                "interpretation": "Analytic product of author judgments; not calibrated.",
            },
            {
                "metric": "conditional_scenario_positive_loading_joint_not_calibrated",
                "value": lookup["Positive loading 1.0x"],
                "unit": "conditional scenario output",
                "interpretation": "Deterministic copula output approximating the former headline architecture; not calibrated and dependent on the author-assigned Gaussian copula family and loadings.",
            },
            {
                "metric": "conditional_scenario_comonotonic_upper_not_calibrated",
                "value": lookup["Comonotonic upper bound"],
                "unit": "conditional scenario output",
                "interpretation": "Logical maximum intersection allowed by the central author marginals; not an empirical bound.",
            },
            {
                "metric": "largest_leave_one_out_driver",
                "value": leave_out.iloc[0]["ratio_vs_five_condition_independent"],
                "unit": "times baseline",
                "interpretation": f"Omitting {leave_out.iloc[0]['omitted_label']} changes the conditional independent product most because it has the smallest central marginal.",
            },
            {
                "metric": "highest_voi_assumption",
                "value": voi.iloc[0]["voi_score"],
                "unit": "conditional joint-probability swing",
                "interpretation": f"{voi.iloc[0]['condition_label']} has the largest one-at-a-time swing under the author range and independence.",
            },
            {
                "metric": "equal_marginal_for_1pct_joint",
                "value": equal_1pct,
                "unit": "per-condition probability",
                "interpretation": "Under independence, five equally likely conditions each need about this marginal to yield a 1% conjunction.",
            },
            {
                "metric": "nitrogen_full_stack_median",
                "value": np.nan,
                "unit": "Tg N/yr",
                "interpretation": LEGACY_N_REASON,
            },
            {
                "metric": "material_post_transition_median",
                "value": anchors["material_median"],
                "unit": "t/cap",
                "interpretation": "Repository scenario median; ecological acceptability remains unpriced.",
            },
        ]
    )


def chart_feasibility_matrix(matrix: pd.DataFrame) -> None:
    pivot = matrix.pivot(
        index="scenario", columns="condition", values="feasibility_code"
    )
    pivot = pivot.loc[list(SCENARIOS), CONDITIONS]
    fig, ax = plt.subplots(figsize=(12, 6.5))
    sns.heatmap(
        pivot,
        cmap=sns.color_palette(["#c44e52", "#f2b134", "#b0b0b0"], as_cmap=True),
        vmin=0,
        vmax=2,
        linewidths=1.5,
        linecolor="white",
        cbar=False,
        annot=np.where(
            pivot.values == 2,
            "UNASSESSED",
            np.where(pivot.values == 1, "CONDITIONAL", "NO PATH"),
        ),
        fmt="",
        annot_kws={"fontsize": 9, "fontweight": "bold"},
        ax=ax,
    )
    ax.set_xticklabels([SHORT_LABELS[c] for c in CONDITIONS], rotation=0)
    ax.set_yticklabels(list(SCENARIOS), rotation=0)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title(
        "Chart 136: Scenario feasibility replaces an unsupported point probability\n"
        "Conditional means a mechanism can be stated—not that success is probable",
        fontweight="bold",
    )
    ax.text(
        0,
        -0.18,
        "No cell is probability-calibrated. Nitrogen is unassessed: the legacy model cannot test its control variable.",
        transform=ax.transAxes,
        fontsize=9,
        color="dimgray",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "136_scenario_feasibility_matrix.png")
    plt.close(fig)


def chart_partial_identification(
    partial: pd.DataFrame, dependence: pd.DataFrame, break_even: pd.DataFrame
) -> None:
    require_valid_nitrogen()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.5))

    selected = partial[
        partial["marginal_set"].isin(["author_central", "author_ranges"])
        & partial["identification_assumption"].isin(
            [
                "No dependence assumption (Frechet-Hoeffding)",
                "Ranges + unrestricted dependence",
                "Ranges + independence",
            ]
        )
    ].copy()
    selected["label"] = selected["identification_assumption"].map(
        {
            "No dependence assumption (Frechet-Hoeffding)": "Central marginals,\ndependence unrestricted",
            "Ranges + unrestricted dependence": "Author marginal ranges,\ndependence unrestricted",
            "Ranges + independence": "Author marginal ranges,\nindependence imposed",
        }
    )
    selected = selected.drop_duplicates("label")
    y = np.arange(len(selected))
    for yi, (_, row) in enumerate(selected.iterrows()):
        ax1.hlines(
            yi,
            100 * row["lower_bound"],
            100 * row["upper_bound"],
            lw=8,
            color="#3a7ca5",
        )
        ax1.scatter(
            [100 * row["lower_bound"], 100 * row["upper_bound"]],
            [yi, yi],
            color="#1f4e66",
            s=35,
        )
    ax1.set_yticks(y)
    ax1.set_yticklabels(selected["label"])
    ax1.set_xlabel("Joint all-five result (%)")
    ax1.set_title("Partial-identification intervals")
    ax1.set_xlim(left=-0.5)
    ax1.axvline(
        1.8005,
        color="#c44e52",
        ls="--",
        lw=1.5,
        label="Former 1.80% conditional output",
    )
    ax1.legend(fontsize=8, loc="lower right")

    dep = dependence[
        dependence["dependence_structure"].isin(
            [
                "Mixed signs",
                "Independence",
                "Positive loading 0.5x",
                "Positive loading 1.0x",
                "Positive loading 1.3x",
                "Comonotonic upper bound",
            ]
        )
    ].copy()
    dep["joint_pct"] = 100 * dep["joint_all"]
    dep = dep.sort_values("joint_pct")
    ax2.barh(dep["dependence_structure"], dep["joint_pct"], color="#f2b134")
    for i, value in enumerate(dep["joint_pct"]):
        ax2.text(value + 0.25, i, f"{value:.3g}%", va="center", fontsize=8)
    ax2.set_xlabel("Conditional joint all-five result (%)")
    ax2.set_title("Dependence sensitivity at central judgments")
    ax2.set_xlim(0, max(22, dep["joint_pct"].max() * 1.18))

    fig.suptitle(
        "Chart 137: The joint result is partially identified, not precisely estimated\n"
        "Copula values are assumption sensitivity—not empirical confidence intervals",
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(CHARTS / "137_scenario_partial_identification.png")
    plt.close(fig)


def chart_value_of_information(voi: pd.DataFrame, leave_out: pd.DataFrame) -> None:
    require_valid_nitrogen()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.5))
    plot = voi.sort_values("voi_score")
    ax1.barh(plot["condition_label"], 100 * plot["voi_score"], color="#3a7ca5")
    for i, value in enumerate(100 * plot["voi_score"]):
        ax1.text(value + 0.003, i, f"{value:.3f} pp", va="center", fontsize=8)
    ax1.set_xlabel("One-at-a-time swing in independent joint (percentage points)")
    ax1.set_title("Value-of-information priority\n(range width × local influence)")

    loo = leave_out.sort_values("ratio_vs_five_condition_independent")
    ax2.barh(
        loo["omitted_label"],
        loo["ratio_vs_five_condition_independent"],
        color="#55a868",
    )
    for i, value in enumerate(loo["ratio_vs_five_condition_independent"]):
        ax2.text(value + 0.08, i, f"{value:.1f}×", va="center", fontsize=8)
    ax2.set_xlabel("Four-condition product / five-condition product")
    ax2.set_title(
        "Leave-one-assumption-out sensitivity\n(diagnostic deletion under independence)"
    )
    ax2.axvline(1, color="black", lw=1)

    fig.suptitle(
        "Chart 138: Nitrogen and biodiversity/land dominate the information agenda\n"
        "Rankings are conditional diagnostics, not monetary expected values",
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(CHARTS / "138_scenario_value_of_information.png")
    plt.close(fig)


def legacy_main() -> None:
    """Historical workflow retained for provenance; deliberately disabled."""
    require_valid_nitrogen()
    print("=" * 82)
    print("ANALYSIS 32: SCENARIO CALIBRATION, BOUNDS, AND VALUE OF INFORMATION")
    print("=" * 82)
    anchors = load_anchors()
    evidence = build_evidence_audit(anchors)
    matrix = build_feasibility_matrix()
    partial = build_partial_identification()
    dependence = build_dependence_sensitivity()
    leave_out = build_leave_one_out()
    voi = build_value_of_information()
    break_even = build_break_even()
    summary = build_summary(anchors, partial, dependence, leave_out, voi, break_even)

    save_csv(evidence, "scenario_calibration_evidence_audit.csv")
    save_csv(matrix, "scenario_calibration_feasibility_matrix.csv")
    save_csv(partial, "scenario_calibration_partial_identification.csv")
    save_csv(dependence, "scenario_calibration_dependence_sensitivity.csv")
    save_csv(leave_out, "scenario_calibration_leave_one_out.csv")
    save_csv(voi, "scenario_calibration_value_of_information.csv")
    save_csv(break_even, "scenario_calibration_break_even.csv")
    save_csv(summary, "scenario_calibration_summary.csv")

    chart_feasibility_matrix(matrix)
    chart_partial_identification(partial, dependence, break_even)
    chart_value_of_information(voi, leave_out)
    print("  saved charts/136_scenario_feasibility_matrix.png")
    print("  saved charts/137_scenario_partial_identification.png")
    print("  saved charts/138_scenario_value_of_information.png")

    dep = dependence.set_index("dependence_structure")["joint_all"]
    bounds = partial[
        partial["identification_assumption"].eq("Ranges + unrestricted dependence")
    ].iloc[0]
    indep_range = partial[
        partial["identification_assumption"].eq("Ranges + independence")
    ].iloc[0]
    print("\nIDENTIFICATION RESULT")
    print("  Empirically calibrated marginal probabilities: 0 of 5")
    print("  Empirically identified joint probability: none")
    print(
        "  Conditional on accepting author marginal ranges, unrestricted-dependence "
        f"bounds are {100*bounds['lower_bound']:.3f}% to {100*bounds['upper_bound']:.1f}%."
    )
    print(
        "  Imposing independence narrows the author-range product to "
        f"{100*indep_range['lower_bound']:.4f}% to {100*indep_range['upper_bound']:.3f}%."
    )
    print("\nDEPENDENCE SENSITIVITY AT CENTRAL AUTHOR JUDGMENTS")
    for name in [
        "Mixed signs",
        "Independence",
        "Positive loading 0.5x",
        "Positive loading 1.0x",
        "Positive loading 1.3x",
        "Comonotonic upper bound",
    ]:
        print(f"  {name:<29}: {100*dep[name]:.4f}%")
    print("  These are conditional model outputs, not empirical confidence intervals.")

    print("\nLEAVE-ONE-OUT (independence diagnostic)")
    print(
        leave_out[
            [
                "omitted_label",
                "four_condition_independent",
                "ratio_vs_five_condition_independent",
            ]
        ].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    print("\nVALUE-OF-INFORMATION RANK")
    print(
        voi[["voi_rank", "condition_label", "voi_score", "data_priority"]].to_string(
            index=False, float_format=lambda x: f"{x:.6f}"
        )
    )
    equal_1 = break_even[break_even["target_joint"].eq(0.01)][
        "equal_marginal_required_if_all_equal"
    ].iloc[0]
    print("\nBREAK-EVEN")
    print(
        f"  Under independence, a 1% all-five conjunction requires equal marginals of "
        f"{100*equal_1:.1f}% each."
    )
    print(
        "\nCONCLUSION: remove the single probability. Present the feasibility matrix, "
        "thresholds, partial-identification bounds, and the data program needed to price it."
    )


def main() -> None:
    anchors = load_anchors()
    evidence = build_evidence_audit(anchors)
    matrix = build_feasibility_matrix()
    save_csv(evidence, "scenario_calibration_evidence_audit.csv")
    save_csv(matrix, "scenario_calibration_feasibility_matrix.csv")
    chart_feasibility_matrix(matrix)
    for suffix in (
        "partial_identification",
        "dependence_sensitivity",
        "leave_one_out",
        "value_of_information",
        "break_even",
        "summary",
    ):
        save_csv(withdrawn_table(JOINT_REASON), f"scenario_calibration_{suffix}.csv")
    for filename, title in (
        (
            "137_scenario_partial_identification.png",
            "Chart 137: Joint bounds withdrawn",
        ),
        (
            "138_scenario_value_of_information.png",
            "Chart 138: Information rankings withdrawn",
        ),
    ):
        withdrawal_chart(CHARTS / filename, title, JOINT_REASON)
    print(JOINT_REASON)
    print("Nitrogen gate unassessed; no replacement marginal or joint estimate.")


if __name__ == "__main__":
    main()
