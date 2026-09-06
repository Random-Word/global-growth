"""Regression tests for measurement safeguards, with synthetic inputs only."""

import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from run_analysis_35 import (
    CORE,
    build_panel,
    fixed_core,
    window_means,
    pareto_mask,
    leave_one_out_rmse,
)


class WellbeingSafeguards(unittest.TestCase):
    def test_missing_core_is_not_a_success(self):
        frame = pd.DataFrame([{column: 1.0 for column in CORE}])
        self.assertEqual(fixed_core(frame).iloc[0], 1.0)
        frame.loc[0, CORE[0]] = np.nan
        self.assertTrue(pd.isna(fixed_core(frame).iloc[0]))

    def test_equal_domains_not_equal_indicators(self):
        frame = pd.DataFrame([{column: 1.0 for column in CORE}])
        frame.loc[
            0,
            [
                "met_water_90",
                "met_sanitation_90",
                "met_electricity_90",
                "met_clean_cooking_80",
            ],
        ] = 0.0
        self.assertAlmostEqual(fixed_core(frame).iloc[0], 0.8)

    def test_exact_windows_no_future_or_gap_fill(self):
        frame = pd.DataFrame(
            {
                "country_code": ["AAA"] * 4,
                "year": [2018, 2019, 2020, 2022],
                "x": [1.0, 2.0, 3.0, 99.0],
            }
        )
        result = window_means(frame, ["x"]).set_index("year")
        self.assertEqual(result.loc[2020, "x"], 2.0)
        self.assertTrue(pd.isna(result.loc[2022, "x"]))

    def test_duplicate_years_rejected(self):
        with self.assertRaises(ValueError):
            window_means(
                pd.DataFrame(
                    {"country_code": ["A", "A"], "year": [2020, 2020], "x": [1, 2]}
                ),
                ["x"],
            )

    def test_stale_welfare_panel_is_audited_then_rejected(self):
        countries = pd.DataFrame({"country_code": ["AAA"], "region": ["Test region"]})
        stale = pd.DataFrame({"country_code": ["AAA", "AAA"], "year": [2020, 2020]})
        with patch(
            "run_analysis_35.pd.read_csv", side_effect=[countries, stale]
        ), patch.object(pd.DataFrame, "to_csv") as audit:
            with self.assertRaisesRegex(ValueError, "rerun corrected Analysis19"):
                build_panel()
            audit.assert_called_once()
            self.assertEqual(
                audit.call_args.args[0].name, "wellbeing_validation_duplicate_audit.csv"
            )

    def test_frontier_is_multidimensional(self):
        frame = pd.DataFrame(
            {
                "life_satisfaction": [7.0, 6.0, 8.0],
                "fixed_core_score": [0.8, 0.7, 0.9],
                "consumption_co2_per_capita": [3.0, 4.0, 10.0],
            }
        )
        self.assertEqual(pareto_mask(frame).tolist(), [True, False, True])

    def test_loco_exact_line(self):
        self.assertAlmostEqual(
            leave_one_out_rmse(np.arange(10.0), 2 * np.arange(10.0) + 1), 0.0
        )


if __name__ == "__main__":
    unittest.main()
