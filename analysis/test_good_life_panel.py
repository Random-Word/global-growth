"""Synthetic regression tests for analysis 19's country-year panel joins."""

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import run_analysis_19 as analysis


class GoodLifePanelTests(unittest.TestCase):
    def setUp(self):
        aliases = {
            "CZE": ("Czechia", "Czech Republic"),
            "TUR": ("Turkiye", "Turkey"),
            "VNM": ("Viet Nam", "Vietnam"),
        }
        wdi, extended, pip = [], [], []
        for code, (country, alias) in aliases.items():
            for year in (2010, 2017, 2018, 2020):
                key = {"country_code": code, "year": year}
                wdi.append(
                    {
                        **key,
                        "country": country,
                        "population": 100.0,
                        "life_expectancy": 75.0,
                        "gdppc_ppp_current": 15000.0,
                    }
                )
                extended.extend(
                    [
                        {
                            **key,
                            "country": country,
                            "basic_water_access_pct": 95.0,
                            "basic_sanitation_pct": np.nan,
                        },
                        {
                            **key,
                            "country": alias,
                            "basic_water_access_pct": np.nan,
                            "basic_sanitation_pct": 80.0,
                        },
                    ]
                )
                pip.append(
                    {
                        "country_code": code,
                        "reporting_year": year,
                        "reporting_level": "national",
                        "mean": 12.0,
                        "median": 10.0,
                        "gini": 0.3,
                        "decile1": 0.02,
                        "decile2": 0.03,
                        "decile3": 0.04,
                        "decile4": 0.05,
                        "reporting_pop": 100.0,
                        "welfare_type": "consumption",
                        "headcount": 0.5,
                        "poverty_gap": 0.2,
                    }
                )
        self.wdi = pd.DataFrame(wdi)
        self.extended = pd.DataFrame(extended)
        self.pip = pd.DataFrame(pip)

    def read_csv(self, path):
        if path.name == "wdi_combined.csv":
            return self.wdi.copy()
        if path.name == "good_life_wdi_extended.csv":
            return self.extended.copy()
        return self.pip.copy()

    def load_panel(self):
        with patch.object(
            analysis.pd, "read_csv", side_effect=self.read_csv
        ), patch.object(analysis.Path, "exists", return_value=True):
            return analysis.load_panel()

    def test_aliases_coalesce_before_scoring_without_multiplying_population(self):
        panel, lines = self.load_panel()
        self.assertEqual(len(panel), 12)
        self.assertFalse(panel.duplicated(["country_code", "year"]).any())
        self.assertEqual(panel.analysis_population.sum(), 1200.0)
        self.assertEqual(lines, [2.15, 3.65, 6.85, 10.0, 15.0, 20.0, 25.0])
        self.assertTrue(panel.basic_water_access_pct.eq(95.0).all())
        self.assertTrue(panel.basic_sanitation_pct.eq(80.0).all())
        self.assertEqual(panel.country.tolist(), self.wdi.country.tolist())
        scored, _ = analysis.add_outcome_scores(panel)
        self.assertTrue(scored.good_life_indicators_available.eq(3).all())
        np.testing.assert_allclose(scored.good_life_score, 2 / 3)

    def test_alias_input_order_does_not_change_panel(self):
        first, _ = self.load_panel()
        self.extended = self.extended.iloc[::-1].copy()
        second, _ = self.load_panel()
        pd.testing.assert_frame_equal(first, second)

    def test_equal_overlapping_values_and_all_missing_columns_are_preserved(self):
        self.extended["basic_water_access_pct"] = 95.0
        self.extended["child_stunting_pct"] = np.nan
        panel, _ = self.load_panel()
        self.assertEqual(len(panel), 12)
        self.assertTrue(panel.basic_water_access_pct.eq(95.0).all())
        self.assertTrue(panel.child_stunting_pct.isna().all())

    def test_conflicting_extended_values_are_rejected_not_averaged(self):
        self.extended.loc[1, "basic_water_access_pct"] = 94.0
        with self.assertRaisesRegex(ValueError, "basic_water_access_pct"):
            self.load_panel()

    def test_missing_extended_key_is_rejected(self):
        for key in ("country_code", "year"):
            with self.subTest(key=key):
                original = self.extended
                self.extended = original.copy()
                self.extended[key] = self.extended[key].astype(object)
                self.extended.loc[0, key] = None
                with self.assertRaises(ValueError):
                    self.load_panel()
                self.extended = original

    def test_duplicate_base_wdi_key_is_rejected(self):
        self.wdi = pd.concat([self.wdi, self.wdi.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            self.load_panel()

    def test_conflicting_pip_concepts_or_values_are_rejected(self):
        for column, value in (("welfare_type", "income"), ("median", 11.0)):
            with self.subTest(column=column):
                original = self.pip
                duplicate = original.iloc[[0]].copy()
                duplicate[column] = value
                self.pip = pd.concat([original, duplicate], ignore_index=True)
                with self.assertRaises(ValueError):
                    self.load_panel()
                self.pip = original

    def test_exact_pip_duplicates_do_not_multiply_rows(self):
        self.pip = pd.concat([self.pip, self.pip.iloc[[0]]], ignore_index=True)
        panel, _ = self.load_panel()
        self.assertEqual(len(panel), 12)
        self.assertFalse(panel.duplicated(["country_code", "year"]).any())

    def test_welfare_type_switch_is_preserved_without_interpolation(self):
        self.pip = self.pip[self.pip.reporting_year.ne(2018)].copy()
        self.pip.loc[self.pip.reporting_year.eq(2020), "welfare_type"] = "income"
        panel, _ = self.load_panel()
        self.assertTrue(
            panel.loc[panel.year.eq(2017), "welfare_type"].eq("consumption").all()
        )
        self.assertTrue(
            panel.loc[panel.year.eq(2020), "welfare_type"].eq("income").all()
        )
        gap = panel[panel.year.eq(2018)]
        self.assertTrue(
            gap[["pip_median_daily", "welfare_type", "pip_headcount_10"]]
            .isna()
            .all()
            .all()
        )


if __name__ == "__main__":
    unittest.main()
