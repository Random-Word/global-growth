#!/usr/bin/env python3
"""Analysis 34: global sensitivity and interaction analysis for scenario models.

This module replaces one-at-a-time lever changes with joint quasi-random draws.
It deliberately separates:
* empirical/measurement uncertainty (for example observed initial welfare),
* structural assumptions (for example incidence allocation and stock lifetime),
* policy implementation levers (delivery, recycling, diet, efficiency), and
* normative choices (discount rates and thresholds).

The sampled distributions are transparent stress ranges, not posterior beliefs
and not forecasts. Sobol first-order and total-order indices are estimated with
a pick-freeze design using scrambled Sobol sequences. Bootstrap intervals
measure Monte Carlo stability only. Reversal frequencies mean the share of the
specified parameter space satisfying a condition, not a real-world probability.
Food nitrogen outputs are synthetic fertilizer inputs only. Numerical 44/62 Tg
benchmarks are illustrative input targets, never planetary-boundary tests.

Outputs:
- data/processed/global_sensitivity_parameter_registry.csv
- data/processed/global_sensitivity_sobol_indices.csv
- data/processed/global_sensitivity_output_distributions.csv
- data/processed/global_sensitivity_interactions.csv
- data/processed/global_sensitivity_reversal_regions.csv
- data/processed/global_sensitivity_method_limits.csv
- charts/141_global_sensitivity_rankings.png
- charts/142_global_sensitivity_reversal_regions.png
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Callable

from ecological_safeguards import NITROGEN_SCOPE

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import qmc

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
PROC.mkdir(exist_ok=True)
CHARTS.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", palette="colorblind")
N = 4096
SEED = 34
BOOTSTRAPS = 200
CENTRAL_YEAR0_TRANSFER_TRILLION = 3.3806497
CENTRAL_YEAR2050_TRANSFER_TRILLION = 0.8664567
CENTRAL_NET_DELIVERY = 0.85 * (1 - 0.00) * (1 - 0.02)


@dataclass(frozen=True)
class Parameter:
    module: str
    name: str
    low: float
    high: float
    central: float
    uncertainty_class: str
    unit: str
    distribution: str = "uniform stress range"


PARAMETERS = [
    # Transfer model: broad but bounded ranges spanning existing scenarios.
    Parameter(
        "transfer", "growth", 0.010, 0.045, 0.025, "structural", "annual fraction"
    ),
    Parameter(
        "transfer",
        "bottom60_capture",
        0.20,
        0.50,
        0.35,
        "structural",
        "share of welfare increment",
    ),
    Parameter(
        "transfer",
        "admin_delivery",
        0.65,
        1.00,
        0.85,
        "policy_implementation",
        "fraction",
    ),
    Parameter(
        "transfer", "behavioral_offset", 0.00, 0.15, 0.00, "structural", "fraction"
    ),
    Parameter(
        "transfer", "local_price_leakage", 0.00, 0.15, 0.02, "structural", "fraction"
    ),
    Parameter(
        "transfer", "discount_rate", 0.01, 0.06, 0.03, "normative", "annual fraction"
    ),
    Parameter(
        "transfer",
        "initial_gap_scale",
        0.85,
        1.15,
        1.00,
        "measurement",
        "baseline multiplier",
    ),
    # Infrastructure global stock-flow approximation.
    Parameter(
        "infrastructure",
        "initial_stock_scale",
        0.80,
        1.20,
        1.00,
        "measurement",
        "multiplier",
    ),
    Parameter(
        "infrastructure",
        "target_stock_scale",
        0.85,
        1.15,
        1.00,
        "structural",
        "multiplier",
    ),
    Parameter(
        "infrastructure",
        "population_scale",
        0.90,
        1.10,
        1.00,
        "empirical_projection",
        "multiplier",
    ),
    Parameter(
        "infrastructure",
        "completion_year",
        2040,
        2060,
        2050,
        "policy_implementation",
        "year",
    ),
    Parameter("infrastructure", "lifetime", 40, 80, 55, "structural", "years"),
    Parameter(
        "infrastructure",
        "collection_2050",
        0.65,
        0.95,
        0.88,
        "policy_implementation",
        "fraction",
    ),
    Parameter(
        "infrastructure",
        "recovery_2050",
        0.65,
        0.95,
        0.88,
        "policy_implementation",
        "fraction",
    ),
    Parameter("infrastructure", "virgin_energy", 1.0, 3.5, 2.0, "engineering", "GJ/t"),
    Parameter(
        "infrastructure", "recycled_energy", 0.35, 1.25, 0.75, "engineering", "GJ/t"
    ),
    # Food model, joint global approximation around observed regional totals.
    Parameter(
        "food",
        "population_demand",
        1.05,
        1.40,
        1.22,
        "empirical_projection",
        "2050/baseline",
    ),
    Parameter(
        "food", "calorie_demand", 1.00, 1.10, 1.04, "structural", "2050/baseline"
    ),
    Parameter(
        "food", "yield_gain", 0.10, 0.35, 0.20, "policy_implementation", "fraction"
    ),
    Parameter(
        "food", "climate_yield_penalty", 0.03, 0.18, 0.09, "structural", "fraction"
    ),
    Parameter(
        "food", "waste_reduction", 0.00, 0.30, 0.10, "policy_implementation", "fraction"
    ),
    Parameter(
        "food",
        "ruminant_diet_reduction",
        0.00,
        0.60,
        0.25,
        "policy_implementation",
        "fraction",
    ),
    Parameter(
        "food",
        "nitrogen_efficiency",
        0.00,
        0.40,
        0.15,
        "policy_implementation",
        "fraction",
    ),
    Parameter(
        "food",
        "irrigation_efficiency",
        0.00,
        0.30,
        0.10,
        "policy_implementation",
        "fraction",
    ),
    Parameter(
        "food",
        "alternative_protein",
        0.00,
        0.35,
        0.00,
        "speculative_policy",
        "fraction",
    ),
    Parameter(
        "food", "feed_share", 0.25, 0.45, 0.35, "measurement", "cropland fraction"
    ),
]


def save(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    if "module" in frame.columns:
        food = frame["module"].eq("food")
        frame.loc[food, "nitrogen_metric_limit"] = NITROGEN_SCOPE
        frame.loc[food, "planetary_boundary_test_valid"] = False
    frame.to_csv(PROC / name, index=False)
    print(f"  saved {name}: {len(frame):,} rows")
    return frame


def registry() -> pd.DataFrame:
    frame = pd.DataFrame([p.__dict__ for p in PARAMETERS])
    frame["range_interpretation"] = (
        "bounded stress range; not a probability distribution"
    )
    return save(frame, "global_sensitivity_parameter_registry.csv")


def transform(unit: np.ndarray, parameters: list[Parameter]) -> np.ndarray:
    low = np.array([p.low for p in parameters])
    high = np.array([p.high for p in parameters])
    return low + unit * (high - low)


def transfer_model(x: np.ndarray) -> np.ndarray:
    """Scale Analysis 29's central mixed-transfer path through joint levers."""
    growth, capture, delivery, behavior, prices, discount, gap_scale = x.T
    years = np.arange(26)[None, :]
    # Calibrated so central growth/capture reproduces Analysis 29's decline from
    # $3.381T gross outlay in 2025 to $0.866T in 2050.
    central_closure = 1 - (
        CENTRAL_YEAR2050_TRANSFER_TRILLION / CENTRAL_YEAR0_TRANSFER_TRILLION
    ) ** (1 / 25)
    closure = np.clip(
        central_closure * (growth[:, None] / 0.025) * (capture[:, None] / 0.35), 0, 0.12
    )
    remaining = (1 - closure) ** years
    net_delivery = delivery * (1 - behavior) * (1 - prices)
    annual = (
        CENTRAL_YEAR0_TRANSFER_TRILLION
        * gap_scale[:, None]
        * remaining
        * (CENTRAL_NET_DELIVERY / net_delivery[:, None])
    )
    pv = (annual / (1 + discount[:, None]) ** years).sum(axis=1)
    end = annual[:, -1]
    return np.column_stack([pv, end])


def infrastructure_model(x: np.ndarray) -> np.ndarray:
    initial_s, target_s, pop_s, completion, lifetime, collection, recovery, e_v, e_r = (
        x.T
    )
    initial_stock = 1250 * initial_s
    target_stock = 1745 * target_s * pop_s
    years = np.arange(2025, 2051)
    stock = initial_stock.copy()
    cumulative_virgin = np.zeros(len(x))
    cumulative_energy = np.zeros(len(x))
    for year in years:
        progress = np.clip((year + 1 - 2025) / (completion - 2025), 0, 1)
        desired = initial_stock + progress * (target_stock - initial_stock)
        demolition = stock / lifetime
        additions = np.maximum(desired - stock + demolition, 0)
        circular_progress = (year - 2025) / 35
        current_collection = 0.60 + circular_progress * (collection - 0.60)
        current_recovery = 0.68 + circular_progress * (recovery - 0.68)
        secondary = np.minimum(
            additions, demolition * current_collection * current_recovery
        )
        virgin = additions - secondary
        cumulative_virgin += virgin
        cumulative_energy += virgin * e_v + secondary * e_r
        stock = stock + additions - demolition
    return np.column_stack([cumulative_virgin, cumulative_energy])


def food_model(x: np.ndarray) -> np.ndarray:
    """Synthetic fertilizer demand only; not a total-N fixation balance."""
    pop, calories, yield_gain, climate, waste, diet, n_eff, irrigation, alt, feed = x.T
    demand = pop * calories * (1 - waste)
    yield_mult = np.maximum(1 + yield_gain - climate, 0.5)
    crop_mult = demand * (1 - feed * diet) * (1 - feed * alt) / yield_mult
    pasture_mult = demand * (1 - diet) * (1 - alt)
    # Observed baseline totals from analysis 31, approximately 1,560/3,200 Mha
    # cropland/pasture and 112 Tg synthetic N.
    land = 1560 * crop_mult + 3200 * pasture_mult
    nitrogen = 112 * crop_mult * (1 - n_eff)
    water = 100 * crop_mult * (1 - irrigation)
    return np.column_stack([land, nitrogen, water])


MODELS: dict[str, tuple[list[str], Callable[[np.ndarray], np.ndarray], list[str]]] = {
    "transfer": (
        [p.name for p in PARAMETERS if p.module == "transfer"],
        transfer_model,
        ["pv_transfer_trillion_2017ppp", "year2050_transfer_trillion_2017ppp"],
    ),
    "infrastructure": (
        [p.name for p in PARAMETERS if p.module == "infrastructure"],
        infrastructure_model,
        ["cumulative_virgin_material_gt", "cumulative_process_energy_ej"],
    ),
    "food": (
        [p.name for p in PARAMETERS if p.module == "food"],
        food_model,
        [
            "agricultural_land_required_mha",
            "synthetic_nitrogen_required_tg",
            "water_pressure_index",
        ],
    ),
}


def sobol_module(
    module: str,
    names: list[str],
    model: Callable[[np.ndarray], np.ndarray],
    outputs: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    params = [p for p in PARAMETERS if p.module == module]
    d = len(params)
    design = qmc.Sobol(2 * d, scramble=True, rng=SEED + len(module)).random_base2(
        int(np.log2(N))
    )
    a = transform(design[:, :d], params)
    b = transform(design[:, d:], params)
    ya, yb = model(a), model(b)

    index_rows = []
    interaction_rows = []
    rng = np.random.default_rng(SEED + d)
    for k, output in enumerate(outputs):
        variance = np.var(np.concatenate([ya[:, k], yb[:, k]]), ddof=1)
        first, total = [], []
        hybrids = []
        for j, name in enumerate(names):
            ab = a.copy()
            ab[:, j] = b[:, j]
            yab = model(ab)[:, k]
            hybrids.append(yab)
            s1 = 1 - np.mean((yb[:, k] - yab) ** 2) / (2 * variance)
            st = np.mean((ya[:, k] - yab) ** 2) / (2 * variance)
            first.append(s1)
            total.append(st)
            boot_s1, boot_st = [], []
            for _ in range(BOOTSTRAPS):
                ix = rng.integers(0, N, N)
                v = np.var(np.concatenate([ya[ix, k], yb[ix, k]]), ddof=1)
                boot_s1.append(1 - np.mean((yb[ix, k] - yab[ix]) ** 2) / (2 * v))
                boot_st.append(np.mean((ya[ix, k] - yab[ix]) ** 2) / (2 * v))
            index_rows.append(
                {
                    "module": module,
                    "output": output,
                    "parameter": name,
                    "first_order": s1,
                    "total_order": st,
                    "first_order_mc_low": np.quantile(boot_s1, 0.025),
                    "first_order_mc_high": np.quantile(boot_s1, 0.975),
                    "total_order_mc_low": np.quantile(boot_st, 0.025),
                    "total_order_mc_high": np.quantile(boot_st, 0.975),
                    "n_base_draws": N,
                    "interval_interpretation": "Monte Carlo stability only",
                    "near_zero_note": (
                        "small negative first-order values are finite-sample Monte Carlo artifacts"
                        if s1 < 0
                        else ""
                    ),
                }
            )
        # Largest pairwise second-order effects, estimated with a double hybrid.
        for j in range(d):
            for ell in range(j + 1, d):
                ab2 = a.copy()
                ab2[:, [j, ell]] = b[:, [j, ell]]
                y2 = model(ab2)[:, k]
                sjk = (
                    np.mean(yb[:, k] * (y2 - hybrids[j] - hybrids[ell] + ya[:, k]))
                    / variance
                )
                interaction_rows.append(
                    {
                        "module": module,
                        "output": output,
                        "parameter_1": names[j],
                        "parameter_2": names[ell],
                        "second_order": sjk,
                    }
                )

    dist_rows = []
    for matrix_name, values in [("A", ya), ("B", yb)]:
        for k, output in enumerate(outputs):
            dist_rows.append(
                {
                    "module": module,
                    "output": output,
                    "draw_matrix": matrix_name,
                    "mean": values[:, k].mean(),
                    "p05": np.quantile(values[:, k], 0.05),
                    "p25": np.quantile(values[:, k], 0.25),
                    "median": np.median(values[:, k]),
                    "p75": np.quantile(values[:, k], 0.75),
                    "p95": np.quantile(values[:, k], 0.95),
                    "minimum": values[:, k].min(),
                    "maximum": values[:, k].max(),
                    "n_draws": len(values),
                    "interpretation": "conditional distribution over specified stress ranges",
                }
            )
    return (
        pd.DataFrame(index_rows),
        pd.DataFrame(dist_rows),
        pd.DataFrame(interaction_rows),
    )


def reversal_regions() -> pd.DataFrame:
    rows = []
    # Independent larger Sobol draw for transparent threshold frequencies.
    for module, (names, model, outputs) in MODELS.items():
        params = [p for p in PARAMETERS if p.module == module]
        x = transform(
            qmc.Sobol(len(params), scramble=True, rng=SEED + 500).random_base2(15),
            params,
        )
        y = model(x)
        conditions: list[tuple[str, np.ndarray, str]]
        if module == "transfer":
            conditions = [
                (
                    "PV transfer below $40T",
                    y[:, 0] < 40,
                    "pv_transfer_trillion_2017ppp < 40",
                ),
                (
                    "2050 annual transfer below $0.5T",
                    y[:, 1] < 0.5,
                    "year2050_transfer_trillion_2017ppp < 0.5",
                ),
            ]
        elif module == "infrastructure":
            conditions = [
                (
                    "Virgin material below 900 Gt",
                    y[:, 0] < 900,
                    "cumulative_virgin_material_gt < 900",
                ),
                (
                    "Virgin material below 1,000 Gt",
                    y[:, 0] < 1000,
                    "cumulative_virgin_material_gt < 1000",
                ),
            ]
        else:
            conditions = [
                (
                    "Agricultural land no higher than baseline",
                    y[:, 0] <= 4760,
                    "agricultural_land_required_mha <= 4760",
                ),
                (
                    "Synthetic N <=62 Tg (illustrative input benchmark)",
                    y[:, 1] <= 62,
                    "synthetic_nitrogen_required_tg <= 62",
                ),
                (
                    "Synthetic N <=44 Tg (illustrative input benchmark)",
                    y[:, 1] <= 44,
                    "synthetic_nitrogen_required_tg <= 44",
                ),
            ]
        for label, mask, expression in conditions:
            rows.append(
                {
                    "module": module,
                    "condition": label,
                    "expression": expression,
                    "share_of_stress_range_draws": mask.mean(),
                    "draws_satisfying": int(mask.sum()),
                    "n_draws": len(mask),
                    "interpretation": "parameter-space robustness frequency; not real-world probability; not a planetary-boundary compliance test",
                }
            )
    return pd.DataFrame(rows)


def method_limits() -> pd.DataFrame:
    rows = [
        (
            "distributions",
            "Uniform quasi-random draws cover declared bounds.",
            "Bounds are stress ranges, not estimated probability distributions.",
        ),
        (
            "dependence",
            "Inputs vary independently in the main design.",
            "Correlated implementation capacity could widen tails; structural scenarios should be read separately.",
        ),
        (
            "Sobol intervals",
            "Bootstrap intervals resample model evaluations.",
            "They measure Monte Carlo stability, not empirical sampling or parameter uncertainty.",
        ),
        (
            "near_zero_indices",
            "Finite-sample Jansen first-order estimates may be slightly negative when the true effect is near zero.",
            "Small negative values are Monte Carlo artifacts and should be read as functionally zero; raw estimates are retained rather than silently clipped.",
        ),
        (
            "sample_size_split",
            "Sobol indices use 4,096 base draws; reversal-region validation uses an independent 32,768-draw quasi-random sample.",
            "The larger sample stabilizes threshold shares; neither sample creates empirical probabilities.",
        ),
        (
            "transfer",
            "Reduced-form path is calibrated to Analysis 29's central mixed strategy ($3.381T in 2025, $0.866T in 2050, $39.305T PV).",
            "It preserves main growth/incidence/delivery interactions but does not rerun every country-decile path or price growth-enabling investment.",
        ),
        (
            "infrastructure",
            "Global stock-flow approximation is calibrated to analysis 31 totals.",
            "Regional and sectoral composition is compressed; stock inventories remain assumed.",
        ),
        (
            "food",
            "Global aggregate approximates land, synthetic fertilizer and water-pressure identities.",
            NITROGEN_SCOPE
            + " Regional crop ecology, trade, biodiversity quality, and nutrient transport are absent. The 44/62 Tg input benchmarks are illustrative, not PB thresholds for this metric.",
        ),
        (
            "reversal_frequency",
            "Reports the fraction of the declared parameter cube meeting a threshold.",
            "It must not be described as a forecast probability or confidence level.",
        ),
    ]
    return pd.DataFrame(
        rows, columns=["issue", "implementation", "interpretation_limit"]
    )


def charts(indices: pd.DataFrame, reversals: pd.DataFrame) -> None:
    top = (
        indices.sort_values("total_order", ascending=False)
        .groupby(["module", "output"], as_index=False)
        .head(4)
        .copy()
    )
    top["label"] = top.module + ": " + top.parameter
    fig, axes = plt.subplots(1, 3, figsize=(16, 7))
    for ax, (module_value, d) in zip(axes, top.groupby("module")):
        d = d.sort_values("total_order")
        ax.barh(d.label, d.total_order, color="#3a7ca5")
        ax.set_title(str(module_value).title())
        ax.set_xlabel("Sobol total-order index")
    fig.suptitle(
        "Joint sensitivity: parameter effects (food inputs, not PB compliance)"
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "141_global_sensitivity_rankings.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(14, 6))
    d = reversals.copy()
    d["percent"] = 100 * d.share_of_stress_range_draws
    sns.barplot(data=d, x="percent", y="condition", hue="module", dodge=False, ax=ax)
    ax.set_xlabel("Share of declared stress-range draws satisfying condition (%)")
    ax.set_ylabel("")
    ax.set_title(
        "Illustrative input benchmarks—not probabilities or planetary-boundary tests"
    )
    fig.subplots_adjust(left=0.43, right=0.98, top=0.90, bottom=0.15)
    fig.savefig(CHARTS / "142_global_sensitivity_reversal_regions.png")
    plt.close(fig)


def main() -> None:
    print("Analysis 34: global sensitivity")
    if "--labels-only" in sys.argv:
        # Equations/draws are unchanged. Reuse the expensive Sobol estimates,
        # refresh scope metadata and the small independent benchmark sample.
        registry()
        for name in (
            "global_sensitivity_sobol_indices.csv",
            "global_sensitivity_output_distributions.csv",
            "global_sensitivity_interactions.csv",
        ):
            save(pd.read_csv(PROC / name), name)
        indices = pd.read_csv(PROC / "global_sensitivity_sobol_indices.csv")
        reversals = save(reversal_regions(), "global_sensitivity_reversal_regions.csv")
        save(method_limits(), "global_sensitivity_method_limits.csv")
        charts(indices, reversals)
        return
    registry()
    all_indices, all_distributions, all_interactions = [], [], []
    for module, (names, model, outputs) in MODELS.items():
        print(f"  evaluating {module} ({len(names)} parameters)")
        i, d, interactions = sobol_module(module, names, model, outputs)
        all_indices.append(i)
        all_distributions.append(d)
        all_interactions.append(interactions)
    indices = save(
        pd.concat(all_indices, ignore_index=True),
        "global_sensitivity_sobol_indices.csv",
    )
    distributions = save(
        pd.concat(all_distributions, ignore_index=True),
        "global_sensitivity_output_distributions.csv",
    )
    interactions = pd.concat(all_interactions, ignore_index=True)
    interactions["absolute_second_order"] = interactions.second_order.abs()
    interactions = save(
        interactions.sort_values("absolute_second_order", ascending=False),
        "global_sensitivity_interactions.csv",
    )
    reversals = save(reversal_regions(), "global_sensitivity_reversal_regions.csv")
    save(method_limits(), "global_sensitivity_method_limits.csv")
    charts(indices, reversals)
    print("\nTop total-order sensitivities:")
    print(
        indices.sort_values("total_order", ascending=False)
        .groupby(["module", "output"])
        .head(3)[["module", "output", "parameter", "first_order", "total_order"]]
        .to_string(index=False)
    )
    print("\nReversal-region frequencies:")
    print(
        reversals[["condition", "share_of_stress_range_draws"]].to_string(index=False)
    )
    print("\nOutput distributions:")
    print(
        distributions[distributions.draw_matrix.eq("A")][
            ["module", "output", "p05", "median", "p95"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
