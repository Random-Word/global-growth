#!/usr/bin/env python3
"""Analysis 31: infrastructure accounting and food-input scenarios.

This is a transparent scenario model, not an optimization or forecast. It pools
two physical systems because construction, recycling, food production, land
restoration, nutrients, and water all compete for energy and implementation
capacity.

The infrastructure module is a dynamic stock-flow identity by World Bank region
and sector. The food module is a bounded region-level accounting exercise built
from country observations. Neither module claims subnational spatial resolution.

Core infrastructure equations (region r, sector s, year t):
    S[r,s,t+1] = S[r,s,t] + I[r,s,t] - D[r,s,t]
    D[r,s,t]   = S[r,s,t] / L[s]
    R[r,s,t]   = D[r,s,t] * collection[t] * recovery[t]
    V[r,s,t]   = I[r,s,t] - min(I[r,s,t], R[r,s,t])
    E[r,s,t]   = V[r,s,t] * e_virgin[s] + R_used[r,s,t] * e_recycled[s]

Core food equations (region r, 2050 scenario q):
    crop_req = crop_0 * demand * (1 - feed_share*diet_shift)
               * (1 - feed_share*alt_protein) / yield_multiplier
    pasture_req = pasture_0 * demand * (1 - diet_shift) * (1 - alt_protein)
    N_req = N_0 * (crop_req/crop_0) * (1 - N_efficiency)
    P_req = P_0 * (crop_req/crop_0) * (1 - P_efficiency)
    water_pressure_index = stress_0 * (crop_req/crop_0)
                           * (1 - irrigation_efficiency)

Important limits:
- Nitrogen is synthetic fertilizer input, not total industrial + intentional
    biological fixation. These outputs do not test the 62 Tg N/yr planetary
    boundary (~190 Tg N/yr current total in Richardson 2023). Legacy output
    filenames containing 'food_boundary' are retained only for link compatibility.
- Country material footprint (MF/RMC, trade-adjusted) is unavailable in the
  repository's OWID series; only World MF is available. Regional material
  observations are DMC and are explicitly labelled territorial/direct-trade.
- Food observations are country data aggregated to World Bank regions. Water
  stress is an area-weighted pressure index, not a volumetric water balance.
- Infrastructure stocks and 2050 population factors are broad literature-
  anchored scenario assumptions, not observations. All such rows are labelled.
- The baseline does not assume cultivated meat, precision fermentation, or
  nitrogen-fixing cereals. Alternative protein appears only in a separately
  labelled speculative sensitivity.

Outputs:
- data/processed/ecological_stock_flow_assumptions.csv
- data/processed/ecological_stock_flow_region_sector_year.csv
- data/processed/ecological_stock_flow_summary.csv
- data/processed/ecological_stock_flow_footprint_baseline.csv
- data/processed/food_boundary_observed_baseline.csv
- data/processed/food_boundary_assumptions.csv
- data/processed/food_boundary_scenarios.csv
- data/processed/food_boundary_sensitivity.csv
- charts/131_infrastructure_stock_path.png
- charts/132_virgin_recycled_energy.png
- charts/133_regional_transition_speed.png
- charts/134_food_boundary_regions.png
- charts/135_food_boundary_scenarios.png
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from ecological_safeguards import NITROGEN_SCOPE

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
RAW_ECO = RAW / "ecological_extension"
for directory in (PROC, CHARTS, RAW_ECO):
    directory.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="colorblind")
plt.rcParams.update(
    {
        "figure.figsize": (13, 7),
        "font.size": 10,
        "axes.titlesize": 13,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)

START_YEAR = 2025
END_YEAR = 2060
FOOD_HORIZON = 2050

REGION_ORDER = [
    "East Asia & Pacific",
    "Europe & Central Asia",
    "Latin America & Caribbean",
    "Middle East, North Africa, Afghanistan & Pakistan",
    "North America",
    "South Asia",
    "Sub-Saharan Africa",
]
REGION_SHORT = {
    "East Asia & Pacific": "EAP",
    "Europe & Central Asia": "ECA",
    "Latin America & Caribbean": "LAC",
    "Middle East, North Africa, Afghanistan & Pakistan": "MENA",
    "North America": "NAM",
    "South Asia": "SAS",
    "Sub-Saharan Africa": "SSA",
}


def value_column(frame: pd.DataFrame) -> str:
    """Return the sole non-identifier column in an OWID Grapher export."""
    identifiers = {"Entity", "Code", "Year", "Day"}
    values = [column for column in frame.columns if column not in identifiers]
    if len(values) != 1:
        raise ValueError(f"Expected one value column, found {values}")
    return values[0]


def fetch_owid(slug: str) -> pd.DataFrame:
    """Load a cached OWID Grapher file, downloading it once if necessary."""
    cache = RAW_ECO / f"owid_{slug}.csv"
    if cache.exists() and cache.stat().st_size > 100:
        return pd.read_csv(cache)
    url = (
        f"https://ourworldindata.org/grapher/{slug}.csv"
        "?v=1&csvType=full&useColumnShortNames=false"
    )
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    frame = pd.read_csv(io.StringIO(response.text))
    frame.to_csv(cache, index=False)
    return frame


def load_population() -> pd.DataFrame:
    """Latest observed WDI population for World Bank country codes."""
    payload = json.loads((RAW / "wdi_population.json").read_text())
    rows = pd.DataFrame(payload[1])
    rows = rows[rows["value"].notna()].copy()
    rows["year"] = rows["date"].astype(int)
    rows["population"] = rows["value"].astype(float)
    rows = rows.sort_values("year").groupby("countryiso3code", as_index=False).tail(1)
    return rows[["countryiso3code", "year", "population"]].rename(
        columns={"countryiso3code": "country_code", "year": "population_year"}
    )


def latest_country_values(frame: pd.DataFrame, output_name: str) -> pd.DataFrame:
    """Latest nonmissing country observation, retaining its observation year."""
    column = value_column(frame)
    data = frame[
        frame["Code"].notna()
        & frame["Code"].str.fullmatch(r"[A-Z]{3}")
        & frame[column].notna()
    ].copy()
    data = data.sort_values("Year").groupby("Code", as_index=False).tail(1)
    return data[["Code", "Year", column]].rename(
        columns={
            "Code": "country_code",
            "Year": f"{output_name}_year",
            column: output_name,
        }
    )


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return float("nan")
    return float(np.average(values[valid], weights=weights[valid]))


# ---------------------------------------------------------------------------
# Shared observed baselines and explicitly labelled assumptions
# ---------------------------------------------------------------------------

COUNTRY_LOOKUP = pd.read_csv(RAW / "wb_country_regions.csv")
COUNTRY_LOOKUP["region"] = COUNTRY_LOOKUP["region"].str.strip()
COUNTRY_LOOKUP["income"] = COUNTRY_LOOKUP["income"].str.strip()
COUNTRY_LOOKUP = COUNTRY_LOOKUP[COUNTRY_LOOKUP["region"].isin(REGION_ORDER)]
POPULATION = load_population()
COUNTRIES = COUNTRY_LOOKUP.merge(POPULATION, on="country_code", how="left")

# Rounded 2025->2050 factors, used as scenario assumptions rather than forecasts.
# They reproduce only the broad UN WPP regional pattern and deliberately avoid
# spurious country-level projection precision.
POPULATION_2050_FACTOR = {
    "East Asia & Pacific": 1.02,
    "Europe & Central Asia": 0.97,
    "Latin America & Caribbean": 1.10,
    "Middle East, North Africa, Afghanistan & Pakistan": 1.32,
    "North America": 1.12,
    "South Asia": 1.18,
    "Sub-Saharan Africa": 1.65,
}

INCOME_STOCK_TPC = {
    "Low income": {"Buildings": 28.0, "Transport": 8.0, "Utilities": 7.0},
    "Lower middle income": {"Buildings": 52.0, "Transport": 17.0, "Utilities": 13.0},
    "Upper middle income": {"Buildings": 92.0, "Transport": 31.0, "Utilities": 22.0},
    "High income": {"Buildings": 140.0, "Transport": 55.0, "Utilities": 35.0},
}
INCOME_TARGET_TPC = {
    "Low income": {"Buildings": 85.0, "Transport": 30.0, "Utilities": 24.0},
    "Lower middle income": {"Buildings": 100.0, "Transport": 37.0, "Utilities": 28.0},
    "Upper middle income": {"Buildings": 118.0, "Transport": 44.0, "Utilities": 31.0},
    "High income": {"Buildings": 140.0, "Transport": 55.0, "Utilities": 35.0},
}
SECTOR_ASSUMPTIONS = {
    "Buildings": {
        "lifetime": 70.0,
        "virgin_energy_gj_t": 1.20,
        "recycled_energy_gj_t": 0.45,
    },
    "Transport": {
        "lifetime": 50.0,
        "virgin_energy_gj_t": 2.20,
        "recycled_energy_gj_t": 0.80,
    },
    "Utilities": {
        "lifetime": 45.0,
        "virgin_energy_gj_t": 3.20,
        "recycled_energy_gj_t": 1.15,
    },
}
STOCK_SCENARIOS = {
    "slow_transition": {
        "completion_year": 2060,
        "collection_start": 0.55,
        "collection_end": 0.75,
        "recovery_start": 0.65,
        "recovery_end": 0.78,
    },
    "central_transition": {
        "completion_year": 2050,
        "collection_start": 0.60,
        "collection_end": 0.88,
        "recovery_start": 0.68,
        "recovery_end": 0.88,
    },
    "fast_transition": {
        "completion_year": 2040,
        "collection_start": 0.65,
        "collection_end": 0.94,
        "recovery_start": 0.72,
        "recovery_end": 0.93,
    },
}


def region_income_weighted_stock(
    region: str, sector: str, mapping: dict[str, dict[str, float]]
) -> float:
    data = COUNTRIES[
        (COUNTRIES["region"] == region)
        & COUNTRIES["population"].notna()
        & COUNTRIES["income"].isin(mapping)
    ]
    mapped = data["income"].map(lambda income: mapping[str(income)][sector])
    return weighted_mean(mapped, data["population"])


def save_stock_assumptions() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for income, sectors in INCOME_STOCK_TPC.items():
        for sector, value in sectors.items():
            rows.append(
                {
                    "module": "infrastructure",
                    "parameter": "initial_covered_stock_t_per_capita",
                    "region_or_income": income,
                    "sector_or_scenario": sector,
                    "value": value,
                    "unit": "t/cap",
                    "evidence_class": "literature_anchored_scenario_assumption",
                    "source_or_rationale": "Broad stock ranges from economy-wide material-stock literature; covered infrastructure only.",
                }
            )
    for income, sectors in INCOME_TARGET_TPC.items():
        for sector, value in sectors.items():
            rows.append(
                {
                    "module": "infrastructure",
                    "parameter": "target_covered_stock_t_per_capita",
                    "region_or_income": income,
                    "sector_or_scenario": sector,
                    "value": value,
                    "unit": "t/cap",
                    "evidence_class": "scenario_assumption",
                    "source_or_rationale": "Convergence toward service-providing infrastructure, not universal high-income consumption.",
                }
            )
    for sector, assumptions in SECTOR_ASSUMPTIONS.items():
        for parameter, value in assumptions.items():
            rows.append(
                {
                    "module": "infrastructure",
                    "parameter": parameter,
                    "region_or_income": "all",
                    "sector_or_scenario": sector,
                    "value": value,
                    "unit": "years" if parameter == "lifetime" else "GJ/t",
                    "evidence_class": "literature_anchored_scenario_assumption",
                    "source_or_rationale": "Rounded service lives and embodied-energy ranges; sensitivity represented by transition scenarios.",
                }
            )
    for scenario, assumptions in STOCK_SCENARIOS.items():
        for parameter, value in assumptions.items():
            rows.append(
                {
                    "module": "infrastructure",
                    "parameter": parameter,
                    "region_or_income": "all",
                    "sector_or_scenario": scenario,
                    "value": value,
                    "unit": "year" if parameter == "completion_year" else "fraction",
                    "evidence_class": "scenario_assumption",
                    "source_or_rationale": "Bounded transition-speed and circularity sensitivity; not an estimated probability.",
                }
            )
    for region, factor in POPULATION_2050_FACTOR.items():
        rows.append(
            {
                "module": "shared",
                "parameter": "population_2050_factor",
                "region_or_income": region,
                "sector_or_scenario": "all",
                "value": factor,
                "unit": "2050 / observed-baseline population",
                "evidence_class": "literature_anchored_scenario_assumption",
                "source_or_rationale": "Rounded UN-WPP-like regional factor; held constant after 2050.",
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(PROC / "ecological_stock_flow_assumptions.csv", index=False)
    return result


def infrastructure_stock_flow() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate covered infrastructure stocks under three transition speeds."""
    region_population = COUNTRIES.groupby("region", as_index=True)["population"].sum()
    rows: list[dict[str, object]] = []
    for scenario, assumptions in STOCK_SCENARIOS.items():
        for region in REGION_ORDER:
            population_0 = float(region_population[region])
            factor_2050 = POPULATION_2050_FACTOR[region]
            annual_population_growth = (
                factor_2050 ** (1 / (FOOD_HORIZON - START_YEAR)) - 1
            )
            for sector, sector_assumptions in SECTOR_ASSUMPTIONS.items():
                stock_pc_0 = region_income_weighted_stock(
                    region, sector, INCOME_STOCK_TPC
                )
                stock_pc_target = region_income_weighted_stock(
                    region, sector, INCOME_TARGET_TPC
                )
                stock = stock_pc_0 * population_0
                for year in range(START_YEAR, END_YEAR + 1):
                    years_elapsed = year - START_YEAR
                    population = population_0 * (1 + annual_population_growth) ** min(
                        years_elapsed, FOOD_HORIZON - START_YEAR
                    )
                    completion_year = int(assumptions["completion_year"])
                    progress = np.clip(
                        (year + 1 - START_YEAR) / (completion_year - START_YEAR), 0, 1
                    )
                    target_pc = stock_pc_0 + progress * (stock_pc_target - stock_pc_0)
                    desired_closing_stock = target_pc * population
                    demolition = stock / sector_assumptions["lifetime"]
                    gross_additions = max(
                        desired_closing_stock - stock + demolition, 0.0
                    )
                    circular_progress = np.clip(
                        years_elapsed / (END_YEAR - START_YEAR), 0, 1
                    )
                    collection = assumptions["collection_start"] + circular_progress * (
                        assumptions["collection_end"] - assumptions["collection_start"]
                    )
                    recovery = assumptions["recovery_start"] + circular_progress * (
                        assumptions["recovery_end"] - assumptions["recovery_start"]
                    )
                    secondary_available = demolition * collection * recovery
                    secondary_used = min(gross_additions, secondary_available)
                    virgin = gross_additions - secondary_used
                    recycling_losses = demolition - secondary_available
                    unused_secondary = max(secondary_available - secondary_used, 0.0)
                    energy_ej = (
                        virgin * sector_assumptions["virgin_energy_gj_t"]
                        + secondary_used * sector_assumptions["recycled_energy_gj_t"]
                    ) / 1e9
                    closing_stock = stock + gross_additions - demolition
                    rows.append(
                        {
                            "scenario": scenario,
                            "region": region,
                            "region_short": REGION_SHORT[region],
                            "sector": sector,
                            "year": year,
                            "population_bn": population / 1e9,
                            "opening_stock_gt": stock / 1e9,
                            "closing_stock_gt": closing_stock / 1e9,
                            "closing_stock_t_per_capita": closing_stock / population,
                            "target_stock_t_per_capita": stock_pc_target,
                            "gross_additions_gt": gross_additions / 1e9,
                            "demolition_gt": demolition / 1e9,
                            "secondary_available_gt": secondary_available / 1e9,
                            "secondary_used_gt": secondary_used / 1e9,
                            "virgin_material_gt": virgin / 1e9,
                            "recycling_losses_gt": recycling_losses / 1e9,
                            "unused_secondary_gt": unused_secondary / 1e9,
                            "process_energy_ej": energy_ej,
                            "collection_rate": collection,
                            "recovery_rate": recovery,
                            "completion_year_assumption": completion_year,
                            "stock_basis": "covered infrastructure scenario stock; not observed total anthropogenic stock",
                        }
                    )
                    stock = closing_stock
    panel = pd.DataFrame(rows)
    panel.to_csv(PROC / "ecological_stock_flow_region_sector_year.csv", index=False)

    summary_rows: list[dict[str, object]] = []
    for scenario, data in panel.groupby("scenario"):
        through_2050 = data[data["year"] <= FOOD_HORIZON]
        peak_virgin = data.groupby("year")["virgin_material_gt"].sum()
        peak_energy = data.groupby("year")["process_energy_ej"].sum()
        year_2050 = data[data["year"] == FOOD_HORIZON]
        summary_rows.append(
            {
                "scenario": scenario,
                "cumulative_gross_additions_2025_2050_gt": through_2050[
                    "gross_additions_gt"
                ].sum(),
                "cumulative_virgin_material_2025_2050_gt": through_2050[
                    "virgin_material_gt"
                ].sum(),
                "cumulative_secondary_used_2025_2050_gt": through_2050[
                    "secondary_used_gt"
                ].sum(),
                "cumulative_recycling_losses_2025_2050_gt": through_2050[
                    "recycling_losses_gt"
                ].sum(),
                "cumulative_process_energy_2025_2050_ej": through_2050[
                    "process_energy_ej"
                ].sum(),
                "peak_annual_virgin_gt": peak_virgin.max(),
                "peak_annual_virgin_year": int(peak_virgin.idxmax()),
                "peak_annual_process_energy_ej": peak_energy.max(),
                "peak_annual_process_energy_year": int(peak_energy.idxmax()),
                "secondary_share_of_additions_2050": year_2050[
                    "secondary_used_gt"
                ].sum()
                / year_2050["gross_additions_gt"].sum(),
                "covered_stock_2050_gt": year_2050["closing_stock_gt"].sum(),
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(PROC / "ecological_stock_flow_summary.csv", index=False)
    return panel, summary


def footprint_baseline() -> pd.DataFrame:
    """Observed DMC by region plus the only available trade-adjusted MF row."""
    dmc = pd.read_csv(RAW / "owid_dmc_per_capita.csv")
    dmc_latest = latest_country_values(dmc, "dmc_t_per_capita")
    data = COUNTRIES.merge(dmc_latest, on="country_code", how="left")
    rows: list[dict[str, object]] = []
    for region, group in data.groupby("region"):
        rows.append(
            {
                "region": region,
                "observation_year_min": group["dmc_t_per_capita_year"].min(),
                "observation_year_max": group["dmc_t_per_capita_year"].max(),
                "material_value_t_per_capita": weighted_mean(
                    group["dmc_t_per_capita"], group["population"]
                ),
                "accounting_basis": "DMC: territorial extraction plus direct imports minus direct exports",
                "trade_adjusted": False,
                "coverage_note": "Country DMC available; upstream raw-material equivalents embodied in trade are excluded.",
            }
        )
    mf = pd.read_csv(RAW / "owid_material_footprint_per_capita.csv")
    mf_column = value_column(mf)
    world = mf[mf["Entity"] == "World"].sort_values("Year").iloc[-1]
    rows.append(
        {
            "region": "World",
            "observation_year_min": int(world["Year"]),
            "observation_year_max": int(world["Year"]),
            "material_value_t_per_capita": float(world[mf_column]),
            "accounting_basis": "MF/RMC: consumption-based raw-material equivalents",
            "trade_adjusted": True,
            "coverage_note": "Repository OWID series exposes World only; no region-level trade-adjusted footprint is inferred.",
        }
    )
    result = pd.DataFrame(rows)
    result.to_csv(PROC / "ecological_stock_flow_footprint_baseline.csv", index=False)
    return result


# ---------------------------------------------------------------------------
# Regional food-boundary accounting
# ---------------------------------------------------------------------------

FOOD_DATASETS = {
    "cereal_yield_t_ha": "cereal-yield",
    "nitrogen_kg_ha": "nitrogen-fertilizer-application-per-hectare-of-cropland",
    "phosphate_p2o5_kg_ha": "phosphate-application-per-hectare-of-cropland",
    "water_stress_pct": "freshwater-withdrawals-as-a-share-of-internal-resources",
    "agricultural_land_pct": "share-of-land-area-used-for-agriculture",
    "cropland_ha": "cropland-area",
    "land_area_sq_km": "land-area-km",
}

CLIMATE_YIELD_PENALTY = {
    "East Asia & Pacific": 0.06,
    "Europe & Central Asia": 0.04,
    "Latin America & Caribbean": 0.07,
    "Middle East, North Africa, Afghanistan & Pakistan": 0.10,
    "North America": 0.05,
    "South Asia": 0.09,
    "Sub-Saharan Africa": 0.12,
}

# All levers are fractions by 2050. The first three scenarios assume no
# undeployed breakthrough. Alternative protein is isolated as speculative.
FOOD_SCENARIOS = {
    "trend_no_new_policy": {
        "yield_gain": 0.15,
        "waste_reduction": 0.00,
        "ruminant_diet_reduction": 0.00,
        "nitrogen_efficiency": 0.00,
        "phosphorus_efficiency": 0.00,
        "irrigation_efficiency": 0.00,
        "alternative_protein_replacement": 0.00,
        "evidence_class": "baseline_no_breakthrough",
    },
    "proven_measures": {
        "yield_gain": 0.20,
        "waste_reduction": 0.10,
        "ruminant_diet_reduction": 0.25,
        "nitrogen_efficiency": 0.15,
        "phosphorus_efficiency": 0.15,
        "irrigation_efficiency": 0.10,
        "alternative_protein_replacement": 0.00,
        "evidence_class": "deployed_or_commercial_levers",
    },
    "high_ambition_no_breakthrough": {
        "yield_gain": 0.30,
        "waste_reduction": 0.20,
        "ruminant_diet_reduction": 0.50,
        "nitrogen_efficiency": 0.30,
        "phosphorus_efficiency": 0.25,
        "irrigation_efficiency": 0.20,
        "alternative_protein_replacement": 0.00,
        "evidence_class": "ambitious_adoption_no_undeployed_breakthrough",
    },
    "speculative_alt_protein": {
        "yield_gain": 0.25,
        "waste_reduction": 0.15,
        "ruminant_diet_reduction": 0.35,
        "nitrogen_efficiency": 0.20,
        "phosphorus_efficiency": 0.20,
        "irrigation_efficiency": 0.15,
        "alternative_protein_replacement": 0.30,
        "evidence_class": "speculative_undeployed_at_required_scale",
    },
}

FEED_SHARE_OF_CROPLAND = 0.35
CALORIE_DEMAND_FACTOR = {
    "East Asia & Pacific": 1.02,
    "Europe & Central Asia": 1.00,
    "Latin America & Caribbean": 1.02,
    "Middle East, North Africa, Afghanistan & Pakistan": 1.04,
    "North America": 1.00,
    "South Asia": 1.05,
    "Sub-Saharan Africa": 1.08,
}


def food_observed_baseline() -> pd.DataFrame:
    latest_frames = []
    for output_name, slug in FOOD_DATASETS.items():
        latest_frames.append(latest_country_values(fetch_owid(slug), output_name))
    country = COUNTRIES.copy()
    for frame in latest_frames:
        country = country.merge(frame, on="country_code", how="left")

    rows: list[dict[str, object]] = []
    for region, data in country.groupby("region"):
        region = str(region)
        cropland_total = data["cropland_ha"].sum(min_count=1)
        country_ag_land_ha = (
            data["land_area_sq_km"] * 100 * data["agricultural_land_pct"] / 100
        )
        ag_land_mha = country_ag_land_ha.sum(min_count=1) / 1e6
        cropland_mha = cropland_total / 1e6
        # Enforce physical consistency if source vintages or coverage differ.
        ag_land_mha = max(ag_land_mha, cropland_mha)
        n_kg_ha = weighted_mean(data["nitrogen_kg_ha"], data["cropland_ha"])
        p_kg_ha = weighted_mean(data["phosphate_p2o5_kg_ha"], data["cropland_ha"])
        water = weighted_mean(data["water_stress_pct"], data["cropland_ha"])
        cereal_yield = weighted_mean(data["cereal_yield_t_ha"], data["cropland_ha"])
        years = [
            column
            for column in data.columns
            if column.endswith("_year") and column != "population_year"
        ]
        observed_years = data[years].stack().dropna()
        row: dict[str, object] = {
            "region": region,
            "region_short": REGION_SHORT[region],
            "population_bn": data["population"].sum() / 1e9,
            "population_observation_year_min": data["population_year"].min(),
            "population_observation_year_max": data["population_year"].max(),
            "ecological_observation_year_min": observed_years.min(),
            "ecological_observation_year_max": observed_years.max(),
            "cereal_yield_t_ha": cereal_yield,
            "nitrogen_kg_ha_cropland": n_kg_ha,
            "phosphate_p2o5_kg_ha_cropland": p_kg_ha,
            "water_stress_pct_area_weighted": water,
            "agricultural_land_mha": ag_land_mha,
            "cropland_mha": cropland_mha,
            "pasture_and_other_ag_land_mha": max(ag_land_mha - cropland_mha, 0),
            "synthetic_nitrogen_tg": n_kg_ha * cropland_total / 1e9,
            "nitrogen_metric_limit": NITROGEN_SCOPE,
            "planetary_boundary_test_valid": False,
            "phosphate_p2o5_tg": p_kg_ha * cropland_total / 1e9,
            "spatial_resolution": "World Bank region; country observations aggregated, no subnational grid",
            "water_metric_limit": "cropland-area-weighted national stress ratio; not a volumetric water balance",
            "phosphorus_metric_limit": "fertilizer P2O5 application, not elemental-P flow to oceans",
        }
        for metric_name in FOOD_DATASETS:
            year_column = f"{metric_name}_year"
            row[f"{metric_name}_year_min"] = data[year_column].min()
            row[f"{metric_name}_year_max"] = data[year_column].max()
        rows.append(row)
    result = pd.DataFrame(rows).sort_values("region")
    result.to_csv(PROC / "food_boundary_observed_baseline.csv", index=False)
    return result


def save_food_assumptions() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scenario, assumptions in FOOD_SCENARIOS.items():
        for parameter, value in assumptions.items():
            if parameter == "evidence_class":
                continue
            rows.append(
                {
                    "scenario": scenario,
                    "parameter": parameter,
                    "region": "all",
                    "central_value": value,
                    "unit": "fraction by 2050",
                    "evidence_class": assumptions["evidence_class"],
                    "source_or_rationale": "Bounded scenario lever; sensitivity scales central lever by 0.75-1.25.",
                }
            )
    for region in REGION_ORDER:
        rows.extend(
            [
                {
                    "scenario": "all",
                    "parameter": "population_2050_factor",
                    "region": region,
                    "central_value": POPULATION_2050_FACTOR[region],
                    "unit": "2050 / baseline population",
                    "evidence_class": "literature_anchored_scenario_assumption",
                    "source_or_rationale": "Rounded UN-WPP-like regional factor.",
                },
                {
                    "scenario": "all",
                    "parameter": "calorie_demand_factor",
                    "region": region,
                    "central_value": CALORIE_DEMAND_FACTOR[region],
                    "unit": "2050 / baseline per-capita demand",
                    "evidence_class": "scenario_assumption",
                    "source_or_rationale": "Small nutrition convergence allowance; not a meat-demand extrapolation.",
                },
                {
                    "scenario": "all",
                    "parameter": "climate_yield_penalty",
                    "region": region,
                    "central_value": CLIMATE_YIELD_PENALTY[region],
                    "unit": "fraction by 2050",
                    "evidence_class": "literature_anchored_scenario_assumption",
                    "source_or_rationale": "Rounded regional penalty consistent with repo-cited global and tropical crop-loss ranges.",
                },
            ]
        )
    rows.append(
        {
            "scenario": "all",
            "parameter": "feed_share_of_cropland",
            "region": "all",
            "central_value": FEED_SHARE_OF_CROPLAND,
            "unit": "fraction",
            "evidence_class": "literature_anchored_scenario_assumption",
            "source_or_rationale": "Rounded global share; held constant because region-specific feed land is unavailable.",
        }
    )
    result = pd.DataFrame(rows)
    result["nitrogen_metric_limit"] = NITROGEN_SCOPE
    result["planetary_boundary_test_valid"] = False
    result.to_csv(PROC / "food_boundary_assumptions.csv", index=False)
    return result


def evaluate_food_scenario(
    baseline: pd.Series,
    scenario_name: str,
    sensitivity: str = "central",
) -> dict[str, object]:
    assumptions = FOOD_SCENARIOS[scenario_name]
    lever_scale = {"low_lever": 0.75, "central": 1.0, "high_lever": 1.25}[sensitivity]
    climate_scale = {"low_lever": 1.25, "central": 1.0, "high_lever": 0.75}[sensitivity]

    def lever(name: str) -> float:
        return min(float(assumptions[name]) * lever_scale, 0.95)

    region = str(baseline["region"])
    total_demand = POPULATION_2050_FACTOR[region] * CALORIE_DEMAND_FACTOR[region]
    yield_multiplier = max(
        1 + lever("yield_gain") - CLIMATE_YIELD_PENALTY[region] * climate_scale,
        0.5,
    )
    demand_after_waste = total_demand * (1 - lever("waste_reduction"))
    diet_shift = lever("ruminant_diet_reduction")
    alternative_protein = lever("alternative_protein_replacement")
    crop_multiplier = (
        demand_after_waste
        * (1 - FEED_SHARE_OF_CROPLAND * diet_shift)
        * (1 - FEED_SHARE_OF_CROPLAND * alternative_protein)
        / yield_multiplier
    )
    pasture_multiplier = (
        demand_after_waste * (1 - diet_shift) * (1 - alternative_protein)
    )
    crop_required = baseline["cropland_mha"] * crop_multiplier
    pasture_required = baseline["pasture_and_other_ag_land_mha"] * pasture_multiplier
    total_required = crop_required + pasture_required
    baseline_land = baseline["agricultural_land_mha"]
    n_required = (
        baseline["synthetic_nitrogen_tg"]
        * crop_multiplier
        * (1 - lever("nitrogen_efficiency"))
    )
    p_required = (
        baseline["phosphate_p2o5_tg"]
        * crop_multiplier
        * (1 - lever("phosphorus_efficiency"))
    )
    water_pressure = (
        baseline["water_stress_pct_area_weighted"]
        * crop_multiplier
        * (1 - lever("irrigation_efficiency"))
    )
    return {
        "scenario": scenario_name,
        "sensitivity": sensitivity,
        "evidence_class": assumptions["evidence_class"],
        "region": region,
        "region_short": baseline["region_short"],
        "population_2050_factor": POPULATION_2050_FACTOR[region],
        "total_food_demand_factor_before_levers": total_demand,
        "effective_yield_multiplier": yield_multiplier,
        "cereal_yield_2050_t_ha": baseline["cereal_yield_t_ha"] * yield_multiplier,
        "cropland_required_mha": crop_required,
        "pasture_other_required_mha": pasture_required,
        "agricultural_land_required_mha": total_required,
        "land_change_vs_baseline_mha": total_required - baseline_land,
        "land_available_for_restoration_mha": max(baseline_land - total_required, 0),
        "additional_land_pressure_mha": max(total_required - baseline_land, 0),
        "synthetic_nitrogen_required_tg": n_required,
        "nitrogen_metric_limit": NITROGEN_SCOPE,
        "planetary_boundary_test_valid": False,
        "nitrogen_change_vs_baseline_pct": 100
        * (n_required / baseline["synthetic_nitrogen_tg"] - 1),
        "phosphate_p2o5_required_tg": p_required,
        "phosphate_change_vs_baseline_pct": 100
        * (p_required / baseline["phosphate_p2o5_tg"] - 1),
        "water_stress_pressure_index_pct": water_pressure,
        "water_pressure_change_vs_baseline_pct": 100
        * (water_pressure / baseline["water_stress_pct_area_weighted"] - 1),
        "yield_gain_assumption": lever("yield_gain"),
        "waste_reduction_assumption": lever("waste_reduction"),
        "ruminant_diet_reduction_assumption": diet_shift,
        "nitrogen_efficiency_assumption": lever("nitrogen_efficiency"),
        "phosphorus_efficiency_assumption": lever("phosphorus_efficiency"),
        "irrigation_efficiency_assumption": lever("irrigation_efficiency"),
        "alternative_protein_replacement_assumption": alternative_protein,
        "climate_yield_penalty_assumption": CLIMATE_YIELD_PENALTY[region]
        * climate_scale,
        "model_scope": "region-level bounded scenario; not subnational spatial optimization",
    }


def food_scenarios(baseline: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = [
        evaluate_food_scenario(row, scenario, "central")
        for _, row in baseline.iterrows()
        for scenario in FOOD_SCENARIOS
    ]
    scenarios = pd.DataFrame(rows)
    scenarios.to_csv(PROC / "food_boundary_scenarios.csv", index=False)

    sensitivity_rows = [
        evaluate_food_scenario(row, scenario, sensitivity)
        for _, row in baseline.iterrows()
        for scenario in FOOD_SCENARIOS
        for sensitivity in ("low_lever", "central", "high_lever")
    ]
    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(PROC / "food_boundary_sensitivity.csv", index=False)
    return scenarios, sensitivity


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def chart_131(panel: pd.DataFrame) -> None:
    data = panel[panel["scenario"] == "central_transition"]
    totals = data.groupby(["year", "sector"], as_index=False)["closing_stock_gt"].sum()
    fig, ax = plt.subplots(figsize=(12, 7))
    pivot = totals.pivot(index="year", columns="sector", values="closing_stock_gt")
    ax.stackplot(
        pivot.index, *[pivot[column] for column in pivot.columns], labels=pivot.columns
    )
    ax.set_ylabel("Covered infrastructure stock (Gt)")
    ax.set_xlabel("Year")
    ax.set_title(
        "Chart 131: Building service-providing stocks creates a long material pulse"
    )
    ax.legend(loc="upper left")
    ax.text(
        0.01,
        0.02,
        "Scenario stocks are literature-anchored ranges, not observed inventories.\n"
        "Identity: closing stock = opening stock + additions − depreciation.",
        transform=ax.transAxes,
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "131_infrastructure_stock_path.png")
    plt.close(fig)


def chart_132(panel: pd.DataFrame) -> None:
    annual = panel.groupby(["scenario", "year"], as_index=False)[
        ["virgin_material_gt", "secondary_used_gt", "process_energy_ej"]
    ].sum()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    colors = {
        "slow_transition": "#0072B2",
        "central_transition": "#009E73",
        "fast_transition": "#D55E00",
    }
    for scenario_value, data in annual.groupby("scenario"):
        scenario = str(scenario_value)
        axes[0].plot(
            data["year"],
            data["virgin_material_gt"],
            label=scenario.replace("_", " "),
            color=colors[scenario],
        )
        axes[1].plot(
            data["year"],
            data["process_energy_ej"],
            label=scenario.replace("_", " "),
            color=colors[scenario],
        )
    axes[0].set_title("Annual virgin construction material")
    axes[0].set_ylabel("Gt/year")
    axes[1].set_title("Process energy for additions")
    axes[1].set_ylabel("EJ/year")
    for ax in axes:
        ax.set_xlabel("Year")
        ax.legend(fontsize=9)
    fig.suptitle(
        "Chart 132: Faster convergence raises the near-term virgin-material and energy peaks",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "132_virgin_recycled_energy.png")
    plt.close(fig)


def chart_133(panel: pd.DataFrame) -> None:
    data = panel[(panel["scenario"] == "central_transition") & (panel["year"] == 2050)]
    regional = data.groupby(["region", "region_short"], as_index=False).agg(
        virgin_gt=("virgin_material_gt", "sum"),
        secondary_gt=("secondary_used_gt", "sum"),
        additions_gt=("gross_additions_gt", "sum"),
        energy_ej=("process_energy_ej", "sum"),
    )
    regional["secondary_share"] = regional["secondary_gt"] / regional["additions_gt"]
    regional = regional.sort_values("virgin_gt")
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.barh(
        regional["region_short"], regional["virgin_gt"], label="Virgin", color="#D55E00"
    )
    ax.barh(
        regional["region_short"],
        regional["secondary_gt"],
        left=regional["virgin_gt"],
        label="Secondary used",
        color="#009E73",
    )
    ax.set_xlabel("Material additions in 2050 (Gt/year)")
    ax.set_title(
        "Chart 133: Regional transition burdens differ; scrap supply lags new stock formation"
    )
    ax.legend()
    ax.set_xlim(0, regional["additions_gt"].max() * 1.12)
    for index, (_, row) in enumerate(regional.reset_index(drop=True).iterrows()):
        ax.text(
            row["additions_gt"] + 0.01,
            index,
            f"{row['secondary_share']:.0%} secondary",
            va="center",
            fontsize=8,
        )
    ax.text(
        0.99,
        0.02,
        "Regional baselines are territorial DMC, not trade-adjusted footprints.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "133_regional_transition_speed.png")
    plt.close(fig)


def chart_134(food: pd.DataFrame) -> None:
    scenario = food[food["scenario"] == "proven_measures"].copy()
    scenario = scenario.sort_values("land_change_vs_baseline_mha")
    colors = np.where(scenario["land_change_vs_baseline_mha"] > 0, "#D55E00", "#009E73")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].barh(
        scenario["region_short"], scenario["land_change_vs_baseline_mha"], color=colors
    )
    axes[0].axvline(0, color="black", lw=1)
    axes[0].set_xlabel("2050 land change vs observed baseline (Mha)")
    axes[0].set_title("Agricultural land: expansion (+) or restoration potential (−)")
    axes[1].scatter(
        scenario["nitrogen_change_vs_baseline_pct"],
        scenario["water_pressure_change_vs_baseline_pct"],
        s=np.maximum(scenario["agricultural_land_required_mha"], 20),
        c=scenario["land_change_vs_baseline_mha"],
        cmap="RdYlGn_r",
        edgecolor="black",
        alpha=0.8,
    )
    for _, row in scenario.iterrows():
        axes[1].annotate(
            row["region_short"],
            (
                row["nitrogen_change_vs_baseline_pct"],
                row["water_pressure_change_vs_baseline_pct"],
            ),
            xytext=(4, 4),
            textcoords="offset points",
        )
    axes[1].axhline(0, color="gray", lw=1)
    axes[1].axvline(0, color="gray", lw=1)
    axes[1].set_xlabel("Synthetic-N change (%)")
    axes[1].set_ylabel("Water-pressure-index change (%)")
    axes[1].set_title("Joint nutrient/water pressure (bubble = land required)")
    axes[1].margins(x=0.08, y=0.08)
    fig.suptitle(
        "Chart 134: Proven measures help, but population and climate pressure remain region-specific",
        fontweight="bold",
    )
    fig.text(
        0.99,
        0.01,
        "Synthetic N is not total fixation; no PB test. Water is an area-weighted index, not a water balance.",
        ha="right",
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "134_food_boundary_regions.png")
    plt.close(fig)


def chart_135(
    food: pd.DataFrame, sensitivity: pd.DataFrame, baseline: pd.DataFrame
) -> None:
    base_land = baseline["agricultural_land_mha"].sum()
    base_n = baseline["synthetic_nitrogen_tg"].sum()
    base_p = baseline["phosphate_p2o5_tg"].sum()
    base_water = np.average(
        baseline["water_stress_pct_area_weighted"], weights=baseline["cropland_mha"]
    )
    global_rows: list[dict[str, object]] = []
    for (scenario, sensitivity_name), data in sensitivity.groupby(
        ["scenario", "sensitivity"]
    ):
        global_rows.append(
            {
                "scenario": scenario,
                "sensitivity": sensitivity_name,
                "Land": data["agricultural_land_required_mha"].sum() / base_land,
                "Synthetic N": data["synthetic_nitrogen_required_tg"].sum() / base_n,
                "Phosphate (P2O5)": data["phosphate_p2o5_required_tg"].sum() / base_p,
                "Water pressure": np.average(
                    data["water_stress_pressure_index_pct"],
                    weights=data["cropland_required_mha"],
                )
                / base_water,
            }
        )
    global_sensitivity = pd.DataFrame(global_rows)
    plot = global_sensitivity[global_sensitivity["sensitivity"] == "central"].set_index(
        "scenario"
    )
    plot = plot.loc[list(FOOD_SCENARIOS)]
    fig, ax = plt.subplots(figsize=(13, 7))
    x = np.arange(len(plot))
    width = 0.19
    for offset, metric in enumerate(
        ["Land", "Synthetic N", "Phosphate (P2O5)", "Water pressure"]
    ):
        lower = global_sensitivity.groupby("scenario")[metric].min().reindex(plot.index)
        upper = global_sensitivity.groupby("scenario")[metric].max().reindex(plot.index)
        central = plot[metric]
        yerr = np.vstack([central - lower, upper - central])
        ax.bar(
            x + (offset - 1.5) * width,
            central,
            width,
            yerr=yerr,
            capsize=3,
            label=metric,
        )
    ax.axhline(
        1, color="black", linestyle="--", lw=1, label="Observed baseline pressure"
    )
    ax.set_xticks(x)
    ax.set_xticklabels([name.replace("_", "\n") for name in plot.index])
    ax.set_ylabel("2050 pressure / observed baseline")
    ax.set_title(
        "Chart 135: No-breakthrough food pathways reduce some pressures; alternative protein is sensitivity only"
    )
    ax.legend(ncol=5, fontsize=8, loc="upper center")
    ax.text(
        0.99,
        0.02,
        "Whiskers: bounded 0.75–1.25× lever sensitivity. Alternative protein is speculative.\n"
        "Synthetic N is not total fixation: no planetary-boundary compliance test.\n"
        "Water is an area-weighted pressure index; P is fertilizer P2O5, not ocean flow.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "135_food_boundary_scenarios.png")
    plt.close(fig)


def print_results(
    stock_summary: pd.DataFrame, food: pd.DataFrame, baseline: pd.DataFrame
) -> None:
    print("\n" + "=" * 78)
    print("ANALYSIS 31: COUPLED ECOLOGICAL ACCOUNTING")
    print("=" * 78)
    print("\nInfrastructure stock-flow, 2025-2050:")
    print(
        stock_summary[
            [
                "scenario",
                "cumulative_virgin_material_2025_2050_gt",
                "cumulative_secondary_used_2025_2050_gt",
                "cumulative_process_energy_2025_2050_ej",
                "peak_annual_virgin_gt",
                "peak_annual_virgin_year",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:,.2f}")
    )
    print("\nFood-input scenarios, global region-sum (2050); NOT boundary tests:")
    records = []
    for scenario, data in food.groupby("scenario", sort=False):
        records.append(
            {
                "scenario": scenario,
                "land_required_mha": data["agricultural_land_required_mha"].sum(),
                "restoration_potential_mha": data[
                    "land_available_for_restoration_mha"
                ].sum(),
                "additional_land_pressure_mha": data[
                    "additional_land_pressure_mha"
                ].sum(),
                "synthetic_n_tg": data["synthetic_nitrogen_required_tg"].sum(),
                "phosphate_p2o5_tg": data["phosphate_p2o5_required_tg"].sum(),
            }
        )
    print(
        pd.DataFrame(records).to_string(
            index=False, float_format=lambda value: f"{value:,.2f}"
        )
    )
    print("\nObserved regional baseline totals:")
    print(f"  Agricultural land: {baseline['agricultural_land_mha'].sum():,.0f} Mha")
    print(
        f"  Synthetic N represented: {baseline['synthetic_nitrogen_tg'].sum():,.1f} Tg/yr"
    )
    print(
        f"  Phosphate represented: {baseline['phosphate_p2o5_tg'].sum():,.1f} Tg P2O5/yr"
    )
    print(
        "\nLimits: regional rather than subnational; water is an index; country MF unavailable;"
    )
    print(
        "infrastructure stocks and projection factors are assumptions, not observed inventories."
    )


def main() -> None:
    if "--food-only" in sys.argv:
        # Local baseline reuse avoids re-downloading observations or rerunning
        # the infrastructure module for a label/scope correction.
        food_baseline = pd.read_csv(PROC / "food_boundary_observed_baseline.csv")
        food_baseline["nitrogen_metric_limit"] = NITROGEN_SCOPE
        food_baseline["planetary_boundary_test_valid"] = False
        food_baseline.to_csv(PROC / "food_boundary_observed_baseline.csv", index=False)
        save_food_assumptions()
        food, sensitivity = food_scenarios(food_baseline)
        chart_134(food)
        chart_135(food, sensitivity, food_baseline)
        print(NITROGEN_SCOPE)
        return
    save_stock_assumptions()
    stock_panel, stock_summary = infrastructure_stock_flow()
    footprint_baseline()
    food_baseline = food_observed_baseline()
    save_food_assumptions()
    food, sensitivity = food_scenarios(food_baseline)
    chart_131(stock_panel)
    chart_132(stock_panel)
    chart_133(stock_panel)
    chart_134(food)
    chart_135(food, sensitivity, food_baseline)
    print_results(stock_summary, food, food_baseline)


if __name__ == "__main__":
    main()
