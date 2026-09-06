"""Offline section-6 refresh and legacy denominator regressions."""

from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import run_analysis_18 as analysis


PREDICTORS = [
    "gross_capital_formation_pct", "fertility_rate", "trade_pct_gdp",
    "fdi_pct_gdp", "primary_completion_pct", "tax_revenue_pct_gdp",
]


def fixture():
    rng = np.random.default_rng(18)
    rows = []
    expected = []
    for index in range(24):
        code = f"C{index:02d}"
        gdp = 1000 * np.exp(np.cumsum(rng.normal(0.025, 0.02, 31)))
        values = rng.normal(size=(31, len(PREDICTORS)))
        if index == 0:
            values[:5, 0] = np.nan  # Complete-case exclusion, not imputation.
        for offset, year in enumerate(range(1990, 2021)):
            rows.append({
                "country_code": code, "country": code, "year": year,
                "gdppc_constant_2015usd": gdp[offset],
                **dict(zip(PREDICTORS, values[offset])),
            })
        for offset in (0, 10, 20):
            if index == 0 and offset == 0:
                continue
            expected.append({
                "country_code": code, "country": code,
                "start_year": 1990 + offset,
                "annual_growth": (gdp[offset + 10] / gdp[offset]) ** (1 / 10) - 1,
                **{name: float(pd.Series(values[offset:offset + 5, i]).mean())
                   for i, name in enumerate(PREDICTORS)},
            })
    wdi = pd.DataFrame(rows)
    metadata = pd.DataFrame({"country_code": wdi["country_code"].unique()})
    aggregate = wdi[wdi["country_code"].eq("C01")].assign(country_code="AFW")
    return pd.concat([wdi, aggregate], ignore_index=True), metadata, pd.DataFrame(expected)


class Analysis18Tests(unittest.TestCase):
    def test_exact_spells_and_clustered_coefficients(self):
        wdi, metadata, expected = fixture()
        original = wdi.copy(deep=True)
        saved = {}
        with patch.object(analysis, "save_table", side_effect=lambda df, name: saved.update({name: df.copy()})), patch.object(analysis.plt, "savefig"):
            analysis.refresh_development_only(wdi, metadata)
        actual = saved["robustness_development_growth_spells.csv"]
        pd.testing.assert_frame_equal(actual.reset_index(drop=True), expected, check_exact=True)
        pd.testing.assert_frame_equal(wdi, original, check_exact=True)
        self.assertEqual(len(actual), 71)
        self.assertNotIn("AFW", set(actual["country_code"]))
        self.assertEqual(set(actual["start_year"]), {1990, 2000, 2010})

        model_data = expected.copy()
        for name in PREDICTORS:
            model_data[f"z_{name}"] = (model_data[name] - model_data[name].mean()) / model_data[name].std()
        model = smf.ols(
            "annual_growth ~ " + " + ".join(f"z_{name}" for name in PREDICTORS) + " + C(start_year)",
            data=model_data,
        ).fit(cov_type="cluster", cov_kwds={"groups": model_data["country_code"]})
        expected_coefficients = pd.DataFrame([
            {
                "term": name,
                "std_coeff_annual_growth_pct_points": model.params[f"z_{name}"] * 100,
                "ci_low": (model.params[f"z_{name}"] - 1.96 * model.bse[f"z_{name}"]) * 100,
                "ci_high": (model.params[f"z_{name}"] + 1.96 * model.bse[f"z_{name}"]) * 100,
                "p_value": model.pvalues[f"z_{name}"],
                "n_spells": int(model.nobs), "r_squared": float(model.rsquared),
            }
            for name in PREDICTORS
        ])
        pd.testing.assert_frame_equal(saved["robustness_development_correlates.csv"], expected_coefficients, check_exact=True)

    def test_flag_reads_only_offline_development_inputs_and_preserves_other_outputs(self):
        wdi, metadata, _ = fixture()
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            for name in ("BASE", "PROC", "RAW", "CHARTS"):
                stack.enter_context(patch.object(analysis, name, root))
            inputs = {root / "wdi_combined.csv": wdi, root / "wb_country_regions.csv": metadata}
            reader = stack.enter_context(patch.object(analysis.pd, "read_csv", side_effect=lambda path: inputs[path].copy()))
            stack.enter_context(patch.object(analysis, "main", side_effect=AssertionError("legacy path called")))
            stack.enter_context(patch.object(analysis, "refresh_nitrogen_only", side_effect=AssertionError("nitrogen path called")))
            stack.enter_context(patch.object(sys, "argv", ["run_analysis_18.py", "--development-only"]))
            sentinels = ["robustness_claim_confidence.csv", "robustness_good_life_thresholds.csv", "robustness_nitrogen_uncertainty.csv", "92_poverty_cost_sensitivity.png"]
            for name in sentinels:
                (root / name).write_bytes(b"preserve exactly")
            analysis.run_cli()
            self.assertEqual([call.args[0] for call in reader.call_args_list], list(inputs))
            self.assertEqual({path.name for path in root.iterdir()}, set(sentinels) | {
                "robustness_development_growth_spells.csv",
                "robustness_development_correlates.csv", "96_development_correlates.png",
            })
            for name in sentinels:
                self.assertEqual((root / name).read_bytes(), b"preserve exactly")
            self.assertTrue((root / "96_development_correlates.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_zero_denominator_fails_before_monetary_output(self):
        # Exercise the real section-2 guard, with synthetic inputs only. Never
        # run the legacy calculation on the repository's monetary caches.
        wdi = pd.DataFrame([{
            "country_code": "WLD", "year": 2020,
            "gdp_current_usd": 100, "gdp_ppp_current": 200,
            "gdppc_ppp_current": 10000, "gdppc_constant_2015usd": 5000,
            "life_expectancy": 70, "under5_mortality": 20,
            "electricity_access_pct": 95, "basic_water_access_pct": 95,
        }])
        regional = pd.DataFrame([{
            "region_code": "WLD", "reporting_year": 2020,
            "poverty_gap": 0.1, "headcount": 0.2, "reporting_pop": 100,
        }])
        for code, gap in (("UNMATCHED", 0.1), ("WLD", 0.0)):
            with self.subTest(code=code), ExitStack() as stack:
                country = regional.drop(columns="region_code").assign(country_code=code, poverty_gap=gap)
                stack.enter_context(patch.object(analysis.pd, "read_csv", side_effect=[wdi, regional, country]))
                saved = stack.enter_context(patch.object(analysis, "save_table"))
                stack.enter_context(patch.object(analysis.plt, "savefig"))
                stack.enter_context(patch.object(analysis, "nitrogen_withdrawal", side_effect=AssertionError("continued after guard")))
                with self.assertRaisesRegex(ValueError, r"No matched PIP price-basis observations.*--development-only"):
                    analysis.main()
                self.assertEqual([call.args[1] for call in saved.call_args_list], [
                    "robustness_claim_confidence.csv", "robustness_good_life_thresholds.csv",
                ])


if __name__ == "__main__":
    unittest.main()