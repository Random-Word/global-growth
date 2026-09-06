"""Pure/offline regressions for Analysis 29 accounting and diagnostic labels."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import run_analysis_29 as analysis


def survey(code="AAA", year=2010, population=100.0, **changes):
    incomes = np.arange(1.0, 11.0)
    row = {
        "country_code": code, "country_name": code,
        "reporting_year": year, "survey_year": year + 0.25,
        "reporting_level": "national", "distribution_type": "micro",
        "is_interpolated": False, "estimation_type": "survey",
        "welfare_type": "consumption", "gini": 0.3,
        "mean": incomes.mean(), "reporting_pop": population,
        "reporting_gdp": 10000.0, "poverty_line": 2.15,
        "poverty_gap": 0.1, "headcount": 0.2,
        **dict(zip(analysis.DECILES, incomes / incomes.sum())),
    }
    row.update(changes)
    return row


def wdi_rows():
    return pd.DataFrame([
        {"country_code": "AAA", "year": 1999, "tax_revenue_pct_gdp": 99.0},
        {"country_code": "AAA", "year": 2000, "tax_revenue_pct_gdp": 15.0},
        {"country_code": "AAA", "year": 2010, "tax_revenue_pct_gdp": np.nan},
        {"country_code": "AAA", "year": 2011, "tax_revenue_pct_gdp": 90.0},
        {"country_code": "BBB", "year": 2025, "tax_revenue_pct_gdp": 20.0},
    ])


class DecileAccountingTests(unittest.TestCase):
    def test_exact_growth_mass_and_requested_capture(self):
        initial = np.arange(1.0, 11.0)
        original = initial.copy()
        mean0 = float(initial.mean())
        for capture in (0.0, 0.25, 0.35, 0.45, 0.60, 1.0):
            for growth in (0.0, 0.025, 0.04):
                for index in (0, 1, 25):
                    with self.subTest(capture=capture, growth=growth, index=index):
                        result = analysis.projected_decile_incomes(
                            initial, mean0, index, growth, capture
                        )
                        increment = mean0 * ((1 + growth) ** index - 1)
                        delta = result - initial
                        self.assertAlmostEqual(delta[:6].sum() / 10, capture * increment)
                        self.assertAlmostEqual(delta[6:].sum() / 10, (1 - capture) * increment)
                        self.assertAlmostEqual(result.mean(), mean0 * (1 + growth) ** index)
                        np.testing.assert_allclose(delta[:6], capture * increment / 0.6, atol=1e-14)
                        np.testing.assert_allclose(delta[6:], (1 - capture) * increment / 0.4, atol=1e-14)
                        np.testing.assert_array_equal(initial, original)
                        self.assertFalse(np.shares_memory(initial, result))

    def test_equal_absolute_increments_are_not_proportional_growth(self):
        initial = np.arange(1.0, 11.0)
        result = analysis.projected_decile_incomes(initial, 5.5, 1, 0.1, 0.6)
        np.testing.assert_allclose(result - initial, 0.55)
        self.assertFalse(np.allclose(result, initial * 1.1))

    def test_share_rounding_is_not_silently_renormalized(self):
        initial = np.arange(1.0, 11.0) * 1.001
        result = analysis.projected_decile_incomes(initial, 5.5, 3, 0.025, 0.35)
        self.assertAlmostEqual(result.mean(), initial.mean() + 5.5 * (1.025**3 - 1))
        np.testing.assert_array_equal(
            analysis.projected_decile_incomes(initial, 5.5, 0, 0.025, 0.35), initial
        )

    def test_gap_headcount_units_and_strict_line_boundary(self):
        incomes = np.array([0.0, 1.0, analysis.LINE] + [10.0] * 7)
        gap, headcount = analysis.decile_poverty_metrics(incomes, 100.0)
        self.assertEqual(gap, (analysis.LINE + analysis.LINE - 1) * 10 * 365)
        self.assertEqual(headcount, 20.0)
        self.assertEqual(
            analysis.decile_poverty_metrics(np.maximum(incomes, analysis.LINE), 100.0),
            (0.0, 0.0),
        )

    def test_gap_understates_but_headcount_can_err_in_either_direction(self):
        for upper, expected_headcount in ((1.5, 2.0), (2.5, 0.0)):
            with self.subTest(upper=upper):
                people = np.array([0.0, upper * analysis.LINE] + [3 * analysis.LINE] * 18)
                means = people.reshape(10, 2).mean(axis=1)
                gap, headcount = analysis.decile_poverty_metrics(means, 20.0)
                true_gap = np.maximum(analysis.LINE - people, 0).sum() * 365
                self.assertLess(gap, true_gap)
                self.assertEqual((people < analysis.LINE).sum(), 1)
                self.assertEqual(headcount, expected_headcount)


class BaselineVintageTests(unittest.TestCase):
    def countries(self):
        return analysis.prepare_dynamic_countries(
            pd.DataFrame([survey(), survey("BBB", 2025, 300.0)]), wdi_rows()
        )

    def test_latest_eligible_selection_preserves_2010_floor_and_raw_years(self):
        pip = pd.DataFrame([
            survey(year=2009), survey(), survey("BBB", 2024), survey("BBB", 2025),
            survey("OLD", 2009), survey("REG", 2025, reporting_level="urban"),
            survey("INT", 2025, is_interpolated=True),
            survey("BAD", 2025, decile1=np.nan),
        ])
        before = pip.copy(deep=True)
        countries = analysis.prepare_dynamic_countries(pip, wdi_rows())
        self.assertEqual(countries.country_code.tolist(), ["AAA", "BBB"])
        self.assertEqual(countries.reporting_year.tolist(), [2010, 2025])
        self.assertEqual(countries.baseline_survey_year.tolist(), [2010.25, 2025.25])
        self.assertEqual(countries.baseline_age_years.tolist(), [15, 0])
        self.assertTrue(countries.scenario_start_year.eq(2025).all())
        pd.testing.assert_frame_equal(pip, before)

    def test_tax_value_and_actual_year_share_the_same_inclusive_lookback(self):
        countries = self.countries()
        self.assertEqual(countries.tax_revenue_pct_gdp.tolist(), [15.0, 20.0])
        self.assertEqual(countries.tax_rate_observation_year.tolist(), [2000.0, 2025.0])
        self.assertEqual(countries.tax_rate_age_years.tolist(), [25.0, 0.0])
        self.assertEqual(countries.tax_rate_lag_from_reporting_year.tolist(), [10.0, 0.0])
        np.testing.assert_array_equal(countries.baseline_gdp_ppp_year, [1e6, 3e6])
        np.testing.assert_array_equal(countries.tax_revenue_ppp_year, [150000.0, 600000.0])
        self.assertEqual(analysis.match_prior_wdi(wdi_rows(), "AAA", 2010, "tax_revenue_pct_gdp"), 15.0)
        value, year = analysis.match_prior_wdi_observation(
            wdi_rows(), "MISSING", 2025, "tax_revenue_pct_gdp"
        )
        self.assertTrue(np.isnan(value) and np.isnan(year))

    def test_summary_uses_population_weights_not_country_counts(self):
        summary = analysis.baseline_summary(self.countries())
        self.assertEqual(summary["baseline_reporting_year_min"], 2010)
        self.assertEqual(summary["baseline_reporting_year_max"], 2025)
        self.assertEqual(summary["survey_le_2019_countries"], 1)
        self.assertEqual(summary["survey_le_2019_population_share"], 0.25)
        self.assertEqual(summary["population_weighted_baseline_age_years"], 3.75)

    def test_scenario_preserves_accounting_and_exports_vintages(self):
        countries = self.countries()
        detail, summary = analysis.run_dynamic_scenario(countries, "central", analysis.SCENARIOS["central"])
        self.assertEqual(len(detail), 2 * 26 * 3)
        for row in detail.itertuples():
            source = countries[countries.country_code.eq(row.country_code)].iloc[0]
            initial = source[analysis.DECILES].to_numpy(dtype=float) * source["mean"] * 10
            assert isinstance(row.year, int)
            i = row.year - 2025
            growth = 0.0 if row.strategy == "permanent_transfer" else 0.025
            income = analysis.projected_decile_incomes(initial, source["mean"], i, growth, 0.35)
            gap, head = analysis.decile_poverty_metrics(income, source.reporting_pop)
            self.assertEqual(row.net_poverty_gap_annual_2017ppp, gap)
            self.assertEqual(row.people_below_before_transfer, head)
            self.assertEqual(row.survey_year, row.baseline_reporting_year)
            self.assertEqual(row.baseline_survey_year, source.survey_year)
            self.assertEqual(row.baseline_basis, analysis.BASELINE_BASIS)
            self.assertEqual(row.poverty_measure_method, analysis.POVERTY_METHOD)
            self.assertEqual(row.tax_revenue_annual_2017ppp, source.tax_revenue_ppp_year * (1 + growth) ** i)
            if row.strategy == "inclusive_growth_no_transfer":
                self.assertEqual(row.gross_transfer_outlay_annual_2017ppp, 0.0)
                self.assertEqual(row.people_below_after_policy, head)
            else:
                self.assertEqual(row.gross_transfer_outlay_annual_2017ppp, gap / (0.85 * 0.98))
                self.assertEqual(row.people_below_after_policy, 0.0)
        self.assertTrue(summary.baseline_reporting_year_min.eq(2010).all())
        self.assertTrue(summary.poverty_measure_method.eq(analysis.POVERTY_METHOD).all())

    def test_method_limits_explicitly_cover_legacy_names_and_approximations(self):
        limits = analysis.dynamic_method_limits().set_index("element")
        self.assertIn("scenario 2025, not observed common-year", str(limits.loc["baseline vintage", "status"]))
        self.assertIn("headcount can err either way", str(limits.loc["decile poverty and closure", "interpretation_limit"]))
        self.assertIn("not observed 2050 revenue", str(limits.loc["GDP and tax capacity", "interpretation_limit"]))
        self.assertIn("not demonstrated PIP closure", str(limits.loc["decile poverty and closure", "interpretation_limit"]))


class CachedBenchmarkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cache = Path(temp.name) / "pip_country_6.85.csv"
        self.countries = analysis.prepare_dynamic_countries(
            pd.DataFrame([survey(), survey("BBB", 2025, 300.0)]), wdi_rows()
        )

    def benchmark(self):
        # Synthetic test fixture only; no empirical benchmark is invented.
        return pd.DataFrame([
            survey(poverty_line=6.85, poverty_gap=0.25, headcount=0.65),
            survey("BBB", 2025, 300.0, poverty_line=6.85, poverty_gap=0.3, headcount=0.7),
        ])

    def test_absent_cache_does_not_read_or_download_and_keeps_benchmark_missing(self):
        with patch.object(pd, "read_csv", side_effect=AssertionError("No cache read expected")):
            result = analysis.reconcile_cached_pip(self.countries, self.cache)
        self.assertTrue(result.pip_headcount.isna().all())
        self.assertTrue(result.benchmark_status.eq("unavailable: cache absent").all())
        summary = analysis.reconciliation_summary(result)
        self.assertEqual(summary["benchmark_matched_countries"], 0)
        self.assertTrue(np.isnan(summary["matched_pip_headcount"]))

    def test_verified_subset_uses_same_population_for_both_metrics(self):
        self.benchmark().iloc[:1].to_csv(self.cache, index=False)
        before = self.countries.copy(deep=True)
        result = analysis.reconcile_cached_pip(self.countries, self.cache)
        pd.testing.assert_frame_equal(self.countries, before)
        self.assertEqual(result.iloc[0].pip_gap_annual_2017ppp, 0.25 * 100 * 6.85 * 365)
        self.assertEqual(result.iloc[0].pip_headcount, 65.0)
        self.assertTrue(np.isnan(result.iloc[1].pip_headcount))
        summary = analysis.reconciliation_summary(result)
        self.assertEqual(summary["benchmark_matched_countries"], 1)
        self.assertEqual(summary["benchmark_matched_population_share"], 0.25)
        self.assertEqual(summary["matched_decile_headcount"], result.iloc[0].decile_headcount)
        self.assertEqual(summary["matched_pip_headcount"], 65.0)

    def test_rejects_nonmatching_or_unverified_cache_rows_without_calibration(self):
        for column, value in (
            ("poverty_line", 8.3), ("reporting_year", 2011),
            ("reporting_level", "urban"), ("welfare_type", "income"),
            ("distribution_type", "group"), ("is_interpolated", True),
            ("is_interpolated", np.nan), ("estimation_type", "extrapolation"),
            ("mean", 5.6), ("reporting_pop", 101), ("reporting_gdp", 11000),
            ("poverty_gap", np.nan), ("headcount", 1.1),
        ):
            with self.subTest(column=column, value=value):
                benchmark = self.benchmark()
                if column == "is_interpolated":
                    benchmark[column] = benchmark[column].astype("boolean")
                benchmark.loc[0, column] = value
                benchmark.to_csv(self.cache, index=False)
                result = analysis.reconcile_cached_pip(self.countries, self.cache)
                self.assertTrue(np.isnan(result.iloc[0].pip_headcount))
                self.assertAlmostEqual(result.iloc[1].pip_headcount, 210.0)

    def test_duplicate_keys_and_missing_schema_are_not_silently_accepted(self):
        benchmark = self.benchmark()
        pd.concat([benchmark, benchmark.iloc[:1]]).to_csv(self.cache, index=False)
        result = analysis.reconcile_cached_pip(self.countries, self.cache)
        self.assertTrue(np.isnan(result.iloc[0].pip_headcount))
        self.assertAlmostEqual(result.iloc[1].pip_headcount, 210.0)
        benchmark.drop(columns="reporting_gdp").to_csv(self.cache, index=False)
        result = analysis.reconcile_cached_pip(self.countries, self.cache)
        self.assertTrue(result.pip_headcount.isna().all())


if __name__ == "__main__":
    unittest.main()