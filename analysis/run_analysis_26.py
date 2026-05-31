#!/usr/bin/env python3
"""Analysis 26: Scenario-weighted JOINT-probability synthesis.

PURPOSE -- discipline the composition-fallacy optimism in the report.

WHAT THIS ESTIMATES (the explicit target / the bar being cleared)
-----------------------------------------------------------------
This script estimates the probability of a STRINGENT, FULL-PACKAGE success:
"a good life delivered within ALL salient planetary boundaries AND with durable
cross-border redistribution that actually delivers the transfers." It is the
probability that the *whole optimistic package holds at once*.

It is NOT the probability of every morally-relevant or partial version of "good
life within constraints." Weaker versions of the claim -- e.g. "stay within MOST
boundaries", "a good life within boundaries for SOME populations", or "within a
~2C (rather than 1.5C) carbon envelope" -- are strictly easier and are captured
here by (a) the PARTIAL-SUCCESS metric P(>=k of the required conditions) and
(b) the looser carbon interpretations. Read the headline as: the full stringent
package is FRAGILE / unlikely to all hold at once -- NOT "the optimistic case is
virtually impossible." Positive correlation between conditions RAISES the joint
(it helps the optimist); partial success is materially more attainable.

STRUCTURE OF THE MODEL
----------------------
A transparent Monte Carlo joint-scenario model using a shared-latent-factor
(one-factor Gaussian copula) correlation structure. The shared latent factor is
the common techno-institutional / energy-abundance capacity that drives several
conditions at once. We compare independence vs positive vs mixed-sign
correlation, across optimistic / central / pessimistic marginal assumption sets,
and across three carbon-target interpretations (1.5C strict, well-below-2C, ~2C).

KEY MODELLING DECISIONS (review-driven)
---------------------------------------
1. CLAIM MAPPING. Each condition carries why-it-is-necessary, a success horizon,
   and a ROLE in {required, substitutable, enabler}. Printed + saved to a
   companion CSV (scenario_claim_mapping.csv).
2. C6 DOUBLE-COUNT. Energy abundance (C6) is largely a COMMON CAUSE of C1/C4 and
   loads heavily on the same latent factor. Requiring it as a *separate* AND-
   condition mechanically deflates the joint. PRIMARY HEADLINE is therefore the
   5-condition model (C1-C5) where C6 is retained only as part of the shared
   latent factor (it still drives the correlation, it is just not a separate
   required gate). The 6-condition model is reported as a SENSITIVITY.
3. CARBON DISAMBIGUATION. C1 is split into 1.5C (strict), well-below-2C, and ~2C
   interpretations with different priors. Current solar/wind trajectory (APS-
   style) is roughly compatible with ~1.7-2C but short of 1.5C, so the ~2C prior
   is HIGHER than the 1.5C prior. We do not import 1.5C pessimism into a
   "well-below-2C" label.
4. REPO-ANCHORED PRIORS ARE JUDGMENTAL. Nitrogen and material marginals are
   judgmental priors ANCHORED BY repo data and boundary-stringency, NOT direct
   probability read-outs of a single CSV cell. See the per-condition notes.
5. CORRELATION SENSITIVITY + TRADEOFFS. Low / central / high latent-loading
   sensitivity PLUS a MIXED-SIGN scenario in which some conditions are
   NEGATIVELY correlated (tradeoffs). Negative correlations LOWER the joint --
   the honest counterweight to the positive-correlation lift.
6. ANALYTIC INDEPENDENCE + MC UNCERTAINTY. The independence joint-all is computed
   ANALYTICALLY (exact product of marginals / Poisson-binomial), not from the
   rare MC tail. Correlated MC joint probabilities carry a 95% Monte Carlo CI and
   use N_DRAWS = 1,000,000.

Outputs:
- charts/114_joint_scenario_probability.png
- charts/115_conditions_met_distribution.png
- data/processed/scenario_joint_probability.csv
- data/processed/scenario_claim_mapping.csv
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)

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

RNG = np.random.default_rng(20260531)
N_DRAWS = 1_000_000  # large enough for stable rare-tail MC + tight CIs

# ---------------------------------------------------------------------------
# Repo data ANCHORS (used to *inform* judgmental priors, not read off directly).
# ---------------------------------------------------------------------------
NITRO = pd.read_csv(PROC / "robustness_nitrogen_uncertainty.csv")
_fullstack = NITRO[NITRO["scenario"].str.contains("Full stack")].iloc[0]
# Stringency ladder for nitrogen (full Tier-3 stack), straight from the repo:
NITRO_RICHARDSON_62 = float(
    _fullstack["prob_at_or_below_Richardson_62"]
)  # ~0.476 (loosest boundary)
NITRO_INTERMEDIATE_44 = float(
    _fullstack["prob_at_or_below_intermediate_44"]
)  # ~0.053 (intermediate)
NITRO_ROCKSTROM_35 = float(
    _fullstack["prob_at_or_below_Rockstrom_35"]
)  # ~0.007 (strictest)

MATERIAL = pd.read_csv(PROC / "robustness_material_uncertainty.csv").set_index(
    "metric"
)["value"]
MAT_BELOW_11 = float(MATERIAL.get("prob_below_11_0_t", 0.4425))  # ~0.44  P(<=11 t/cap)
MAT_BELOW_9 = float(MATERIAL.get("prob_below_9_0_t", 0.00038))  # ~0.0004 P(<=9 t/cap)


# ---------------------------------------------------------------------------
# Condition definitions. Each marginal is (low, central, high) where "high" is
# the optimistic assumption and "low" is pessimistic. ALL marginals are
# JUDGMENTAL PRIORS; some are anchored by repo data / boundary stringency.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Condition:
    key: str
    label: str
    low: float
    central: float
    high: float
    weight: (
        float  # central latent-factor loading (0-1 magnitude); sign set per-scenario
    )
    role: str  # required | substitutable | enabler
    horizon: str  # success horizon
    why: str  # why necessary for the stringent full package
    source: str = field(default="")


CONDITIONS = [
    # C1 CARBON -- default numbers here are the WELL-BELOW-2C interpretation; the
    # 1.5C and ~2C interpretations OVERRIDE these via CARBON_VARIANTS below. The
    # report notes the 1.5C budget is ~6-10yr from exhaustion at current
    # emissions and fossil fuels remain ~82% of primary energy, while current
    # solar/wind (APS) trajectory is roughly ~1.7-2C compatible. Strong latent
    # loading: carbon success rides the same techno-institutional / energy
    # capacity as the others.
    Condition(
        "C1_carbon",
        "Carbon: stay within target budget",
        0.15,
        0.25,
        0.40,
        0.65,
        role="required",
        horizon="2050 (cumulative budget)",
        why="exceeding the carbon budget breaches the climate boundary outright",
        source="IPCC AR6 / IEA; default label = WELL-BELOW-2C (see CARBON_VARIANTS)",
    ),
    # C2 NITROGEN -- JUDGMENTAL PRIOR anchored by the repo nitrogen ladder.
    # The repo gives, for the full Tier-3 stack, P(meet boundary) at three
    # stringencies: Richardson-62 = 0.476, intermediate-44 = 0.053,
    # Rockstrom-35 = 0.007. The central 0.264 is a MIDPOINT ACROSS STRINGENCIES
    # (not one fixed success definition); high = loosest (Richardson-62),
    # low = intermediate-44. This is a prior over "which boundary stringency
    # ultimately governs", not a CSV read-out of a single success probability.
    Condition(
        "C2_nitrogen",
        "Nitrogen: full Tier-3 stack meets boundary",
        round(NITRO_INTERMEDIATE_44, 3),
        round(0.5 * (NITRO_INTERMEDIATE_44 + NITRO_RICHARDSON_62), 3),
        round(NITRO_RICHARDSON_62, 3),
        0.45,
        role="required",
        horizon="2050 (ag-system overhaul)",
        why="nitrogen boundary already breached; reactive-N must fall sharply",
        source="judgmental prior anchored by repo nitrogen stringency ladder "
        "(Richardson-62 0.476 / intermediate-44 0.053 / Rockstrom-35 0.007)",
    ),
    # C3 BIODIVERSITY / LAND -- judgmental. Land-system change and biosphere
    # integrity boundaries are ALREADY breached; halting and reversing is slow,
    # partly irreversible, weakly governed.
    Condition(
        "C3_biodiversity",
        "Biodiversity/land: halt & reverse breach",
        0.10,
        0.20,
        0.35,
        0.50,
        role="required",
        horizon="2050-2070 (slow, partly irreversible)",
        why="biosphere-integrity loss is partly irreversible; a good life needs "
        "functioning ecosystems",
        source="Richardson 2023: land & biosphere boundaries already breached",
    ),
    # C4 MATERIAL / CIRCULARITY -- JUDGMENTAL PRIOR anchored by the repo material
    # distribution. Repo shows post-transition throughput ~11 t/cap median with
    # P(<=11) ~ 0.44 and P(<=9) ~ 0.0004. The 0.25/0.35/0.50 range is a PRIOR
    # over "ecologically ACCEPTABLE composition" (a stricter, composition-aware
    # target), NOT a CSV read-out of P(<=11) or P(<=9).
    Condition(
        "C4_material",
        "Material: acceptable rich-world throughput/composition",
        0.25,
        0.35,
        0.50,
        0.55,
        role="required",
        horizon="2050 (circular-economy build-out)",
        why="material throughput must fall to an ecologically acceptable "
        "composition, not just below a tonnage cap",
        source="judgmental prior over 'acceptable composition'; anchored by repo "
        "material dist (P<=11t=0.44, P<=9t=0.0004) but NOT a CSV read-out",
    ),
    # C5 POLITICAL CONTAINMENT / SOVEREIGNTY -- the report's OWN weakest link.
    # Durable cross-border redistribution + governance to actually deliver the
    # transfers; historically rare, bounded, contingent.
    Condition(
        "C5_political",
        "Political: durable cross-border redistribution",
        0.15,
        0.25,
        0.40,
        0.70,
        role="required",
        horizon="multi-decade (sustained transfer regime)",
        why="without durable transfers the 'redistribution' leg of the claim "
        "never delivers",
        source="report sovereignty/fragility + Marshall reconstruction analysis",
    ),
    # C6 ENERGY ABUNDANCE ENABLER -- clean energy scaled enough to power
    # circularity, ag-tech and growth at once. This is largely a COMMON CAUSE of
    # C1/C4, hence its high latent loading. ROLE = enabler: in the PRIMARY model
    # it is NOT a separate required gate (that would double-count); it is kept as
    # part of the shared latent factor that correlates C1-C5. In the 6-condition
    # SENSITIVITY it is promoted to a required gate.
    Condition(
        "C6_energy",
        "Energy: clean abundance enabler scaled",
        0.20,
        0.35,
        0.55,
        0.80,
        role="enabler",
        horizon="2040-2050 (build-out)",
        why="cheap clean energy is the common cause enabling carbon AND material "
        "AND ag-tech success (not an independent gate)",
        source="common-cause enabler; latent-only in primary, required in sensitivity",
    ),
]

KEY_TO_IDX = {c.key: i for i, c in enumerate(CONDITIONS)}
N_COND = len(CONDITIONS)
ASSUMPTION_SETS = ["pessimistic", "central", "optimistic"]

# Primary required set = the 5 substantive conditions; C6 is latent-only.
REQUIRED_5 = [
    KEY_TO_IDX[k]
    for k in (
        "C1_carbon",
        "C2_nitrogen",
        "C3_biodiversity",
        "C4_material",
        "C5_political",
    )
]
REQUIRED_6 = list(range(N_COND))

# ---------------------------------------------------------------------------
# Carbon-target interpretations. Stricter target => lower success prior. APS /
# current renewable trajectory is ~1.7-2C compatible but short of 1.5C, so the
# ~2C prior is the highest of the three.
# ---------------------------------------------------------------------------
CARBON_VARIANTS = {
    "1.5C_strict": dict(
        low=0.05,
        central=0.10,
        high=0.20,
        label="1.5C (strict)",
        note="budget ~6-10yr from exhaustion at current emissions; very low prior",
    ),
    "well_below_2C": dict(
        low=0.15,
        central=0.25,
        high=0.40,
        label="well-below-2C",
        note="Paris-consistent NZE-style pathway; feasible but far off trajectory",
    ),
    "around_2C": dict(
        low=0.30,
        central=0.45,
        high=0.60,
        label="~2C",
        note="APS / current solar+wind trajectory roughly ~1.7-2C compatible",
    ),
}
PRIMARY_CARBON = "well_below_2C"


def marginals(assumption: str, carbon_variant: str) -> np.ndarray:
    attr = {"pessimistic": "low", "central": "central", "optimistic": "high"}[
        assumption
    ]
    p = np.array([getattr(c, attr) for c in CONDITIONS], dtype=float)
    p[KEY_TO_IDX["C1_carbon"]] = CARBON_VARIANTS[carbon_variant][attr]
    return p


def base_loadings() -> np.ndarray:
    return np.clip(np.array([c.weight for c in CONDITIONS]), 0.0, 0.95)


def scaled_loadings(scale: float) -> np.ndarray:
    """Latent-factor loadings scaled for low/central/high correlation sensitivity."""
    return np.clip(base_loadings() * scale, -0.95, 0.95)


def mixed_sign_loadings() -> np.ndarray:
    """Tradeoff scenario: some conditions NEGATIVELY loaded on the shared factor.

    Tradeoffs encoded (negative pairwise correlation with the positive bloc):
      - land-intensive mitigation / biofuels  vs  biodiversity  (C3 negative)
      - cheap energy -> rebound throughput     vs  material      (C4 negative)
      - growth-first coalitions                vs  redistribution (C5 negative)
    Carbon (C1), nitrogen ag-tech (C2) and energy (C6) stay positively loaded.
    corr(i,j) = w_i * w_j, so opposite-sign loadings => negative correlation.
    """
    w = base_loadings().copy()
    w[KEY_TO_IDX["C3_biodiversity"]] *= -1.0
    w[KEY_TO_IDX["C4_material"]] *= -1.0
    w[KEY_TO_IDX["C5_political"]] *= -1.0
    return np.clip(w, -0.95, 0.95)


# ---------------------------------------------------------------------------
# One-factor Gaussian copula Monte Carlo.
#   underlying_i = w_i * Z + sqrt(1 - w_i^2) * E_i   (unit variance, corr=w_i*w_j)
#   success_i = 1[ underlying_i <= Phi^{-1}(p_i) ]   -> marginal exactly p_i.
# Signed w_i allow negative correlations. w_i = 0 -> independence.
# ---------------------------------------------------------------------------
def simulate(probs: np.ndarray, w: np.ndarray, n: int = N_DRAWS) -> np.ndarray:
    thresholds = norm.ppf(probs)
    z = RNG.standard_normal((n, 1))
    e = RNG.standard_normal((n, N_COND))
    underlying = w * z + np.sqrt(1.0 - w**2) * e
    return underlying <= thresholds  # (n, N_COND) boolean


def mc_summary(success: np.ndarray, required_idx: list[int]) -> dict:
    req = success[:, required_idx]
    k = len(required_idx)
    n_met = req.sum(axis=1)
    n = len(n_met)
    joint = float((n_met == k).mean())
    se = float(np.sqrt(joint * (1.0 - joint) / n))
    out = {
        "joint_all": joint,
        "joint_all_ci_lo": max(0.0, joint - 1.96 * se),
        "joint_all_ci_hi": joint + 1.96 * se,
        "joint_all_se": se,
        "expected_met": float(n_met.mean()),
        "n_required": k,
        "dist": np.bincount(n_met, minlength=k + 1) / n,
    }
    for j in range(1, k + 1):
        out[f"prob_ge_{j}"] = float((n_met >= j).mean())
    return out


def poisson_binomial(probs: np.ndarray) -> np.ndarray:
    """Exact distribution of #successes for INDEPENDENT Bernoulli(probs)."""
    dist = np.array([1.0])
    for p in probs:
        dist = np.convolve(dist, [1.0 - p, p])
    return dist


def analytic_independence(probs: np.ndarray, required_idx: list[int]) -> dict:
    """Exact independence joint-all = product of marginals (+ exact P>=k)."""
    p = probs[required_idx]
    k = len(required_idx)
    dist = poisson_binomial(p)
    out = {
        "joint_all": float(np.prod(p)),  # exact product -- not an MC tail estimate
        "expected_met": float(p.sum()),
        "n_required": k,
        "dist": dist,
    }
    for j in range(1, k + 1):
        out[f"prob_ge_{j}"] = float(dist[j:].sum())
    return out


# ===========================================================================
# RUN GRID
# ===========================================================================
w_central = scaled_loadings(1.0)

# --- Primary + sensitivity grid: carbon x assumption x {5-cond, 6-cond} ------
# For each (carbon, assumption) we simulate ONCE (central loading, all 6
# conditions) and derive both the 5-condition primary and 6-condition
# sensitivity. Independence is ANALYTIC.
grid: dict[tuple, dict] = {}
for carbon in CARBON_VARIANTS:
    for aset in ASSUMPTION_SETS:
        p = marginals(aset, carbon)
        success = simulate(p, w_central)
        for req_name, req_idx in (("5cond", REQUIRED_5), ("6cond", REQUIRED_6)):
            grid[(carbon, aset, req_name, "correlated")] = mc_summary(success, req_idx)
            grid[(carbon, aset, req_name, "independent")] = analytic_independence(
                p, req_idx
            )

# --- Correlation-sign sensitivity (central assumptions, primary carbon, 5-cond)
p_primary = marginals("central", PRIMARY_CARBON)
corr_sens = {
    "independent_analytic": analytic_independence(p_primary, REQUIRED_5),
    "low_loading": mc_summary(simulate(p_primary, scaled_loadings(0.5)), REQUIRED_5),
    "central_loading": mc_summary(
        simulate(p_primary, scaled_loadings(1.0)), REQUIRED_5
    ),
    "high_loading": mc_summary(simulate(p_primary, scaled_loadings(1.3)), REQUIRED_5),
    "mixed_sign_tradeoffs": mc_summary(
        simulate(p_primary, mixed_sign_loadings()), REQUIRED_5
    ),
}

# ===========================================================================
# BUILD CSVs
# ===========================================================================
# Companion claim-mapping CSV.
claim_rows = []
for c in CONDITIONS:
    claim_rows.append(
        {
            "condition": c.key,
            "label": c.label,
            "role": c.role,
            "success_horizon": c.horizon,
            "why_necessary": c.why,
            "marginal_low": c.low,
            "marginal_central": c.central,
            "marginal_high": c.high,
            "latent_loading_central": c.weight,
            "prior_type": (
                "judgmental prior (repo-anchored)"
                if c.key in ("C2_nitrogen", "C4_material")
                else "judgmental prior"
            ),
            "source_note": c.source,
        }
    )
claim_df = pd.DataFrame(claim_rows)
claim_csv = PROC / "scenario_claim_mapping.csv"
claim_df.to_csv(claim_csv, index=False)

# Main joint-probability CSV.
rows: list[dict] = []
# (a) condition marginals (with claim-mapping fields folded in for convenience).
for c in CONDITIONS:
    rows.append(
        {
            "row_type": "condition_marginal",
            "condition": c.key,
            "label": c.label,
            "role": c.role,
            "success_horizon": c.horizon,
            "marginal_low": c.low,
            "marginal_central": c.central,
            "marginal_high": c.high,
            "latent_loading": c.weight,
            "prior_type": (
                "judgmental prior (repo-anchored)"
                if c.key in ("C2_nitrogen", "C4_material")
                else "judgmental prior"
            ),
            "source_note": c.source,
        }
    )
# (b) carbon variant definitions.
for cv, d in CARBON_VARIANTS.items():
    rows.append(
        {
            "row_type": "carbon_variant_def",
            "condition": cv,
            "label": d["label"],
            "marginal_low": d["low"],
            "marginal_central": d["central"],
            "marginal_high": d["high"],
            "source_note": d["note"],
        }
    )
# (c) main grid joint summaries.
for carbon in CARBON_VARIANTS:
    for aset in ASSUMPTION_SETS:
        for req_name in ("5cond", "6cond"):
            for struct in ("independent", "correlated"):
                r = grid[(carbon, aset, req_name, struct)]
                k = r["n_required"]
                rows.append(
                    {
                        "row_type": "joint_summary",
                        "condition": f"{carbon}/{aset}/{req_name}/{struct}",
                        "label": f"{CARBON_VARIANTS[carbon]['label']} | {aset} | "
                        f"{req_name} | {struct}",
                        "carbon_variant": carbon,
                        "assumption_set": aset,
                        "required_set": req_name,
                        "structure": (
                            "independent (analytic)"
                            if struct == "independent"
                            else "correlated (MC)"
                        ),
                        "is_primary": (req_name == "5cond" and struct == "correlated"),
                        "joint_all": r["joint_all"],
                        "joint_all_ci_lo": r.get("joint_all_ci_lo", np.nan),
                        "joint_all_ci_hi": r.get("joint_all_ci_hi", np.nan),
                        "expected_conditions_met": r["expected_met"],
                        "n_required": k,
                        "prob_ge_3": r.get("prob_ge_3", np.nan),
                        "prob_ge_4": r.get("prob_ge_4", np.nan),
                        "prob_ge_5": r.get("prob_ge_5", np.nan),
                    }
                )
# (d) correlation-sign sensitivity (central, primary carbon, 5-cond).
for name, r in corr_sens.items():
    rows.append(
        {
            "row_type": "correlation_sensitivity",
            "condition": f"{PRIMARY_CARBON}/central/5cond/{name}",
            "label": f"{CARBON_VARIANTS[PRIMARY_CARBON]['label']} | central | 5cond | {name}",
            "carbon_variant": PRIMARY_CARBON,
            "assumption_set": "central",
            "required_set": "5cond",
            "structure": name,
            "joint_all": r["joint_all"],
            "joint_all_ci_lo": r.get("joint_all_ci_lo", np.nan),
            "joint_all_ci_hi": r.get("joint_all_ci_hi", np.nan),
            "expected_conditions_met": r["expected_met"],
            "n_required": r["n_required"],
            "prob_ge_3": r.get("prob_ge_3", np.nan),
            "prob_ge_4": r.get("prob_ge_4", np.nan),
            "prob_ge_5": r.get("prob_ge_5", np.nan),
        }
    )

out_df = pd.DataFrame(rows)
out_csv = PROC / "scenario_joint_probability.csv"
out_df.to_csv(out_csv, index=False)

# ===========================================================================
# CHART 114 -- 5-cond PRIMARY + 6-cond sensitivity across carbon variants
# (central assumptions). Grouped bars per carbon interpretation.
# ===========================================================================
fig, ax = plt.subplots(figsize=(13, 7.5))
carbon_order = ["1.5C_strict", "well_below_2C", "around_2C"]
x = np.arange(len(carbon_order))
bw = 0.26

vals_5_indep = [
    grid[(cv, "central", "5cond", "independent")]["joint_all"] for cv in carbon_order
]
vals_5_corr = [
    grid[(cv, "central", "5cond", "correlated")]["joint_all"] for cv in carbon_order
]
ci_lo = [
    grid[(cv, "central", "5cond", "correlated")]["joint_all_ci_lo"]
    for cv in carbon_order
]
ci_hi = [
    grid[(cv, "central", "5cond", "correlated")]["joint_all_ci_hi"]
    for cv in carbon_order
]
vals_6_corr = [
    grid[(cv, "central", "6cond", "correlated")]["joint_all"] for cv in carbon_order
]

ax.bar(
    x - bw,
    vals_5_indep,
    width=bw,
    color="#8172b3",
    alpha=0.65,
    hatch="//",
    edgecolor="white",
    label="5-cond joint-all (independent, analytic)",
)
corr_err = [
    np.array(vals_5_corr) - np.array(ci_lo),
    np.array(ci_hi) - np.array(vals_5_corr),
]
ax.bar(
    x,
    vals_5_corr,
    width=bw,
    color="#55a868",
    yerr=corr_err,
    capsize=4,
    ecolor="#2e5b3a",
    label="5-cond joint-all (correlated, MC + 95% CI)  [PRIMARY]",
)
ax.bar(
    x + bw,
    vals_6_corr,
    width=bw,
    color="#dd8452",
    alpha=0.85,
    label="6-cond joint-all (correlated, sensitivity)",
)

for xi, v in zip(x - bw, vals_5_indep):
    ax.text(
        xi,
        v,
        f"{v:.4f}",
        ha="center",
        va="bottom",
        fontsize=8,
        rotation=90,
        color="#5a4a8a",
    )
for xi, v in zip(x, vals_5_corr):
    ax.text(
        xi,
        v,
        f"{v:.3f}",
        ha="center",
        va="bottom",
        fontsize=8,
        rotation=90,
        color="#2e5b3a",
    )
for xi, v in zip(x + bw, vals_6_corr):
    ax.text(
        xi,
        v,
        f"{v:.4f}",
        ha="center",
        va="bottom",
        fontsize=8,
        rotation=90,
        color="#a0522d",
    )

# Reference: weakest single marginal (central, primary carbon).
weakest = marginals("central", PRIMARY_CARBON)[REQUIRED_5].min()
ax.axhline(
    weakest,
    color="#c44e52",
    ls=":",
    lw=1.4,
    label=f"weakest single marginal (central) = {weakest:.2f}",
)

ax.set_xticks(x)
ax.set_xticklabels([CARBON_VARIANTS[cv]["label"] for cv in carbon_order], fontsize=11)
ax.set_xlabel("Carbon-target interpretation (stricter -> lower prior)")
ax.set_ylabel("Joint probability (full package holds at once)")
ax.set_title(
    "Joint 'good life within ALL boundaries + durable redistribution' is FRAGILE\n"
    "PRIMARY = 5-condition correlated (C6 latent-only); 6-condition shown as sensitivity"
)
ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
ax.set_ylim(0, max(max(vals_5_corr), weakest) * 1.35)
fig.tight_layout()
fig.savefig(CHARTS / "114_joint_scenario_probability.png")
plt.close(fig)

# ===========================================================================
# CHART 115 -- conditions-met distribution (PRIMARY 5-cond, central, primary carbon)
# ===========================================================================
prim_corr = grid[(PRIMARY_CARBON, "central", "5cond", "correlated")]
prim_indep = grid[(PRIMARY_CARBON, "central", "5cond", "independent")]
dist_corr = prim_corr["dist"]
dist_indep = prim_indep["dist"]
ks = np.arange(len(REQUIRED_5) + 1)

fig, ax = plt.subplots(figsize=(12, 7))
bw = 0.4
ax.bar(
    ks - bw / 2,
    dist_indep,
    width=bw,
    color="#8172b3",
    alpha=0.75,
    label="independent (analytic, central)",
)
ax.bar(
    ks + bw / 2, dist_corr, width=bw, color="#dd8452", label="correlated (MC, central)"
)
for ki, di in zip(ks, dist_corr):
    if di > 0.005:
        ax.text(
            ki + bw / 2,
            di + 0.004,
            f"{di:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#a0522d",
        )

kreq = len(REQUIRED_5)
ax.axvline(
    kreq, color="#c44e52", ls="--", lw=1.5, label=f"all {kreq} (full stringent package)"
)
ax.axvspan(2.5, kreq + 0.5, color="#55a868", alpha=0.10, label=">=3 (partial success)")
ymax = max(dist_corr.max(), dist_indep.max())
ax.text(
    kreq,
    ymax * 0.92,
    f"P(all)={prim_corr['joint_all']:.3f}",
    ha="right",
    va="top",
    fontsize=10,
    color="#c44e52",
)
ax.text(
    3.0,
    ymax * 0.80,
    f"P(>=3)={prim_corr['prob_ge_3']:.3f}",
    ha="left",
    va="top",
    fontsize=10,
    color="#2e7d32",
)

ax.set_xlabel("Number of (5 required) conditions met")
ax.set_ylabel("Probability")
ax.set_title(
    "Conditions-met distribution (PRIMARY 5-cond, central, well-below-2C)\n"
    "Partial success is materially more attainable than the full package"
)
ax.set_xticks(ks)
ax.legend(loc="upper right", fontsize=9)
fig.tight_layout()
fig.savefig(CHARTS / "115_conditions_met_distribution.png")
plt.close(fig)

# ===========================================================================
# CONSOLE REPORT
# ===========================================================================
print("=" * 78)
print("ANALYSIS 26 -- Scenario-weighted JOINT-probability synthesis")
print("=" * 78)
print("\nTARGET: probability the STRINGENT FULL PACKAGE holds at once --")
print(
    "  'good life within ALL salient boundaries + durable cross-border redistribution'."
)
print("  Partial / weaker versions are captured by P(>=k) and looser carbon labels.\n")

print("CLAIM-MAPPING TABLE (role / horizon / why-necessary):")
print(f"  {'cond':16s} {'role':12s} {'central':>7s} {'w':>5s}  horizon")
for c in CONDITIONS:
    print(f"  {c.key:16s} {c.role:12s} {c.central:7.3f} {c.weight:5.2f}  {c.horizon}")
    print(f"     why: {c.why}")
print(f"  (full mapping + prior_type saved to {claim_csv.name})\n")

print("CARBON INTERPRETATIONS (central prior, stricter -> lower):")
for cv in carbon_order:
    print(
        f"  {CARBON_VARIANTS[cv]['label']:16s} central={CARBON_VARIANTS[cv]['central']:.2f}"
        f"  | {CARBON_VARIANTS[cv]['note']}"
    )

print("\n" + "-" * 78)
print("PRIMARY HEADLINE: 5-condition correlated joint-all (central), by carbon target")
print("-" * 78)
print(f"  {'carbon':16s} {'5c indep':>10s} {'5c CORR (95% CI)':>26s} {'6c corr':>10s}")
for cv in carbon_order:
    gi = grid[(cv, "central", "5cond", "independent")]["joint_all"]
    gc = grid[(cv, "central", "5cond", "correlated")]
    g6 = grid[(cv, "central", "6cond", "correlated")]["joint_all"]
    ci = f"{gc['joint_all']:.4f} [{gc['joint_all_ci_lo']:.4f},{gc['joint_all_ci_hi']:.4f}]"
    print(f"  {CARBON_VARIANTS[cv]['label']:16s} {gi:10.5f} {ci:>26s} {g6:10.5f}")

weakest = marginals("central", PRIMARY_CARBON)[REQUIRED_5].min()
prim = grid[(PRIMARY_CARBON, "central", "5cond", "correlated")]
print(f"\nWeakest single required marginal (central, well-below-2C) = {weakest:.3f}")
print(
    f"  -> primary 5-cond correlated joint-all = {prim['joint_all']:.4f} "
    f"(~{weakest / max(prim['joint_all'], 1e-9):.0f}x smaller than the weakest single "
    f"condition: composition fallacy)."
)
print(
    "  -> positive correlation RAISES the joint vs independence (helps the optimist):"
)
for cv in carbon_order:
    gi = grid[(cv, "central", "5cond", "independent")]["joint_all"]
    gc = grid[(cv, "central", "5cond", "correlated")]["joint_all"]
    print(
        f"       {CARBON_VARIANTS[cv]['label']:14s} corr/indep = {gc / max(gi, 1e-12):5.1f}x "
        f"({gi:.5f} -> {gc:.4f})"
    )

print("\n" + "-" * 78)
print("CORRELATION-SIGN SENSITIVITY (central, well-below-2C, 5-cond)")
print("-" * 78)
for name in (
    "independent_analytic",
    "low_loading",
    "central_loading",
    "high_loading",
    "mixed_sign_tradeoffs",
):
    r = corr_sens[name]
    ci = (
        f" [{r['joint_all_ci_lo']:.4f},{r['joint_all_ci_hi']:.4f}]"
        if "joint_all_ci_lo" in r
        else "  (exact)"
    )
    print(f"  {name:22s} joint-all = {r['joint_all']:.4f}{ci}")
mix = corr_sens["mixed_sign_tradeoffs"]["joint_all"]
cen = corr_sens["central_loading"]["joint_all"]
print(
    f"  -> MIXED-SIGN tradeoffs LOWER the joint: {cen:.4f} (positive) -> {mix:.4f} "
    f"(mixed) = {mix / max(cen, 1e-12):.2f}x."
)
print(
    "     (negative correlations are the honest counter to the positive-correlation lift.)"
)

print("\n" + "-" * 78)
print("PARTIAL SUCCESS (more attainable than the full package), 5-cond central:")
print("-" * 78)
for cv in carbon_order:
    gc = grid[(cv, "central", "5cond", "correlated")]
    print(
        f"  {CARBON_VARIANTS[cv]['label']:16s} "
        f"E[met]={gc['expected_met']:.2f}/5  "
        f"P(>=3)={gc['prob_ge_3']:.3f}  P(>=4)={gc['prob_ge_4']:.3f}  "
        f"P(all 5)={gc['joint_all']:.4f}"
    )

print("\n" + "-" * 78)
print("METHOD NOTES:")
print(
    "  - Independence joint-all is ANALYTIC (exact product of marginals), not an MC tail."
)
print(f"  - Correlated joint probabilities are MC with N_DRAWS={N_DRAWS:,} + 95% CI.")
print(
    "  - C6 (energy) is an ENABLER / common cause: latent-only in the PRIMARY 5-cond model,"
)
print(
    "    promoted to a required gate only in the 6-cond SENSITIVITY (which double-counts)."
)
print(
    "  - Nitrogen & material marginals are JUDGMENTAL priors anchored by repo data, not"
)
print("    direct CSV read-outs.")
print(
    "\nCONCLUSION: the full STRINGENT package is FRAGILE -- unlikely to all hold at once --"
)
print(
    "  NOT 'virtually impossible'. Positive correlation RAISES the joint (helps the optimist);"
)
print(
    "  negative tradeoff correlations lower it; and PARTIAL success (>=k) is materially more"
)
print("  attainable, which is the relevant metric for weaker versions of the claim.")
print(f"\nWrote: {out_csv}")
print(f"Wrote: {claim_csv}")
print("Wrote: charts/114_joint_scenario_probability.png")
print("Wrote: charts/115_conditions_met_distribution.png")
