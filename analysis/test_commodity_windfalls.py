"""Offline synthetic regression tests for analysis 33; no upstream runs required."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
import statsmodels.formula.api as smf

import run_analysis_33 as analysis


def panel():
    rng = np.random.default_rng(33)
    d = pd.MultiIndex.from_product(
        [[f"C{i}" for i in range(12)], range(1990, 2008)],
        names=["country_code", "year"],
    ).to_frame(index=False)
    d["commodity_windfall_pct_gdp"] = rng.normal(size=len(d))
    d["shock_lag1"] = analysis.calendar_shift(d, "commodity_windfall_pct_gdp", -1)
    d["log_gdppc"] = 5 + 0.02 * (d["year"].to_numpy(dtype=float) - 1990) + rng.normal(0, 0.1, len(d))
    for column in ["investment", "government_revenue", "government_expense", "inflation"]:
        d[column] = 2 * d.commodity_windfall_pct_gdp + rng.normal(size=len(d))
    d["price_taker_sample"] = True
    d["commodity_export_exposure_gdp"] = 0.1
    return d


class CalendarAlignmentTests(unittest.TestCase):
    def test_shuffled_multi_country_calendar_lags_do_not_bridge_gaps(self):
        d = pd.DataFrame({
            "country_code": ["A", "B", "A", "A", "B"],
            "year": [2003, 2000, 2000, 2001, 2001],
            "value": [30, 100, 0, 10, 110],
        }, index=[9, 7, 5, 3, 1])
        shifted = analysis.calendar_shift(d, "value", -1)
        np.testing.assert_allclose(shifted, [np.nan, np.nan, np.nan, 0, 100], equal_nan=True)
        self.assertEqual(shifted.index.tolist(), d.index.tolist())
        np.testing.assert_allclose(
            analysis.calendar_shift(d, "value", 1), [np.nan, 110, 10, np.nan, np.nan], equal_nan=True,
        )
        self.assertEqual(analysis.calendar_shift(d, "value", -3).iloc[0], 0)

    def test_duplicate_keys_and_invalid_horizons_rejected(self):
        d = panel()
        with self.assertRaisesRegex(ValueError, "unique"):
            analysis.calendar_shift(pd.concat([d, d.iloc[:1]]), "inflation", -1)
        for horizon in [-1, 0.5]:
            with self.assertRaisesRegex(ValueError, "nonnegative integer"):
                analysis.add_horizon_outcomes(d, horizon)

    def test_exact_horizon_endpoints_and_complete_inflation_windows(self):
        d = panel().query("country_code == 'C0'").copy()
        elapsed = d["year"].to_numpy(dtype=float) - 1990
        d["log_gdppc"] = elapsed ** 2 / 100
        for column in ["investment", "government_revenue", "government_expense", "inflation"]:
            d[column] = elapsed ** 2
        for horizon in range(6):
            row = analysis.add_horizon_outcomes(d.sample(frac=1, random_state=2), horizon).query("year == 1993").iloc[0]
            self.assertAlmostEqual(row.lp_gdppc, (3 + horizon) ** 2 - 4)
            for target in ["lp_investment", "lp_government_revenue", "lp_government_expense"]:
                self.assertEqual(row[target], (3 + horizon) ** 2 - 4)
            self.assertEqual(row.lp_inflation, np.mean(np.arange(3, 4 + horizon) ** 2) - 4)
        gap = d[d.year.ne(1994)]
        # Missing t+1 must not silently move h=1 to the next observed year.
        self.assertTrue(np.isnan(analysis.add_horizon_outcomes(gap, 1).query("year == 1993").iloc[0].lp_gdppc))
        # GDP h=2 uses exact endpoints even with an interior gap, but inflation cannot.
        row = analysis.add_horizon_outcomes(gap, 2).query("year == 1993").iloc[0]
        self.assertEqual(row.lp_gdppc, 21)
        self.assertTrue(np.isnan(row.lp_inflation))
        self.assertTrue(np.isnan(analysis.add_horizon_outcomes(gap, 0).query("year == 1995").iloc[0].lp_gdppc))
        d.loc[d.year.eq(1994), "inflation"] = np.nan
        self.assertTrue(np.isnan(analysis.add_horizon_outcomes(d, 2).query("year == 1993").iloc[0].lp_inflation))

    def test_build_panel_uses_calendar_exposures_governance_and_shock_lags(self):
        years = [2000, 2001, 2003, 2004, 2005, 2006, 2007]
        wdi = pd.DataFrame({"country_code": "A", "country": "Alpha", "year": years})
        wdi["population"] = 100
        wdi["gdp_current_usd"] = 1000
        wdi["merchandise_exports_current_usd"] = 100
        wdi["gdppc_constant_2015usd"] = 100
        for column in ["gross_capital_formation_pct", "government_revenue_ex_grants_pct_gdp",
                       "government_expense_pct_gdp", "inflation_cpi_pct"]:
            wdi[column] = 1.0
        for composition, _ in analysis.CATEGORIES.values():
            wdi[composition] = [10, 20, 30, 40, 50, 60, 70]
        countries = pd.DataFrame({"country_code": ["A"], "region": [" R "], "income": [" I "]})
        gov = pd.DataFrame({"country_code": "A", "year": [2000, 2002, 2004],
                            "government_effectiveness_estimate": [10, 20, 30]})
        prices = pd.DataFrame({"year": years})
        for _, price in analysis.CATEGORIES.values():
            prices[price.replace("_index", "_log_change")] = 1.0
        frames = {"wdi_combined.csv": wdi, "wb_country_regions.csv": countries,
                  "fragile_state_country_year_panel.csv": gov}
        with patch.object(analysis.pd, "read_csv", side_effect=lambda p, **kw: frames[p.name].copy()), \
             patch.object(analysis, "save", side_effect=lambda frame, name: frame):
            result = analysis.build_panel(prices).set_index("year")
        # t=2005: t-5=2000, t-4=2001, t-3=2002 missing; mean of two, not row lags.
        np.testing.assert_allclose(result.loc[[2005], "fuel_export_exposure_gdp_predetermined"].to_numpy(dtype=float), [0.015])
        self.assertTrue(pd.isna(result.loc[2003, "fuel_export_exposure_gdp_predetermined"]))
        np.testing.assert_allclose(result.loc[[2006], "fuel_export_exposure_gdp_predetermined"].to_numpy(dtype=float), [0.025])
        self.assertEqual(result.loc[2005, "governance_predetermined"], 20)
        self.assertTrue(pd.isna(result.loc[2006, "governance_predetermined"]))
        self.assertTrue(pd.isna(result.loc[2003, "shock_lag1"]))
        self.assertTrue(pd.isna(result.loc[2003, "gdppc_growth_pct"]))
        self.assertTrue(pd.isna(result.loc[2001, "shock_lead1"]))


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.data = panel()
        self.model, self.used = analysis.fit_fe(self.data, "investment")

    def test_central_remains_original_country_clustered_normal_specification(self):
        original = smf.ols(
            "investment ~ commodity_windfall_pct_gdp + shock_lag1 + C(country_code) + C(year)",
            data=self.used,
        ).fit(cov_type="cluster", cov_kwds={"groups": self.used.country_code})
        np.testing.assert_allclose(self.model.params, original.params)
        np.testing.assert_allclose(self.model.cov_params(), original.cov_params())
        np.testing.assert_allclose(self.model.conf_int(), original.conf_int())
        self.assertFalse(self.model.use_t)

    def test_two_way_matches_independent_cluster_score_sandwich_and_t_intervals(self):
        x = self.model.model.exog
        score = x * np.asarray(self.model.resid)[:, None]
        bread = np.asarray(self.model.normalized_cov_params)
        n, k = x.shape

        def covariance(labels):
            codes = pd.factorize(labels)[0]
            g = len(np.unique(codes))
            sums = np.zeros((g, k))
            np.add.at(sums, codes, score)
            return bread @ (sums.T @ sums) @ bread * g / (g - 1) * (n - 1) / (n - k)

        country = covariance(self.used.country_code)
        year = covariance(self.used.year)
        intersection = covariance(pd.MultiIndex.from_frame(self.used[["country_code", "year"]]))
        expected = country + year - intersection
        shock = self.model.model.exog_names.index("commodity_windfall_pct_gdp")
        lag = self.model.model.exog_names.index("shock_lag1")
        result = analysis.two_way_sensitivity(self.model, self.used)
        self.assertAlmostEqual(result["covariance_shock_shock"], expected[shock, shock])
        self.assertAlmostEqual(result["covariance_shock_lag1"], expected[shock, lag])
        self.assertAlmostEqual(result["covariance_lag1_lag1"], expected[lag, lag])
        self.assertAlmostEqual(result["intersection_component_shock_variance"], intersection[shock, shock])
        self.assertNotAlmostEqual(result["covariance_shock_shock"], country[shock, shock])
        self.assertEqual(result["reference_df"], 11)
        se = np.sqrt(expected[shock, shock])
        self.assertAlmostEqual(result["ci_low"], result["estimate"] - student_t.ppf(0.975, 11) * se)
        self.assertAlmostEqual(result["p_value"], 2 * student_t.sf(abs(result["estimate"] / se), 11))
        self.assertIn("Few effective", result["inference_limit"])

    def test_nonpositive_two_way_variance_is_not_clipped(self):
        k = len(self.model.params)
        for variance in [-1.0, 0.0, np.nan]:
            with patch.object(analysis, "cov_cluster_2groups", return_value=(np.eye(k) * variance, np.eye(k), np.eye(k))):
                result = analysis.two_way_sensitivity(self.model, self.used)
            self.assertTrue(np.isnan(result["std_error"]))
            self.assertTrue(np.isnan(result["ci_low"]))
            self.assertTrue(np.isnan(result["p_value"]))
            self.assertIn("no_interval", result["inference_status"])

    def test_two_way_rejects_single_time_cluster(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            analysis.two_way_sensitivity(self.model, self.used.assign(year=2000))

    def test_headline_exports_match_central_samples_at_all_horizons(self):
        captured = {}
        # Eligibility hole must not alter construction of the next year's outcomes.
        self.data.loc[self.data.year.eq(1995), "commodity_export_exposure_gdp"] = 0
        with patch.object(analysis, "save", side_effect=lambda frame, name: captured.setdefault(name, frame)):
            central = analysis.local_projections(self.data)
        sensitivity = captured["commodity_windfall_two_way_sensitivity.csv"]
        self.assertEqual(len(central), 30)
        self.assertEqual(len(sensitivity), 18)
        paired = sensitivity.merge(central, on=["outcome", "horizon"], suffixes=("_two", "_central"))
        for column in ["estimate", "n_country_years", "n_countries", "n_year_clusters"]:
            np.testing.assert_allclose(paired[column + "_two"], paired[column + "_central"])
        self.assertTrue(central.covariance_type.eq("country_clustered").all())
        self.assertTrue(sensitivity.covariance_type.eq("country_year_two_way_clustered").all())
        # Independently fit a horizon-zero outcome built BEFORE filtering.
        d = analysis.add_horizon_outcomes(self.data, 0)
        eligible = d.commodity_export_exposure_gdp.gt(0.005)
        low, high = d.loc[eligible, "commodity_windfall_pct_gdp"].quantile([0.01, 0.99])
        model, _ = analysis.fit_fe(d[eligible & d.commodity_windfall_pct_gdp.between(low, high)], "lp_investment")
        reported = central.query("outcome == 'investment' and horizon == 0").iloc[0]
        self.assertAlmostEqual(reported.estimate, model.params["commodity_windfall_pct_gdp"])


class OfflineInputTests(unittest.TestCase):
    def test_missing_governance_fails_before_any_output(self):
        original = analysis.pd.read_csv

        def read(path, **kwargs):
            if path.name == "fragile_state_country_year_panel.csv":
                raise FileNotFoundError("missing governance")
            # Other inputs are irrelevant to the missing-input assertion.
            raise FileNotFoundError("synthetic absent cache")

        with patch.object(analysis.pd, "read_csv", side_effect=read), \
             patch.object(analysis, "save") as save, patch.object(analysis, "load_prices") as prices:
            with self.assertRaisesRegex(RuntimeError, "run_analysis_30.py") as error:
                analysis.main()
            self.assertIn("run_analysis_29.py", str(error.exception))
            self.assertIn("no outputs written", str(error.exception))
            save.assert_not_called()
            prices.assert_not_called()
        self.assertIs(analysis.pd.read_csv, original)

    def test_missing_workbook_has_actionable_offline_source(self):
        with patch.object(analysis.Path, "is_file", return_value=False), \
             patch.object(analysis.pd, "read_csv", side_effect=FileNotFoundError("synthetic")):
            with self.assertRaises(RuntimeError) as error:
                analysis.check_prerequisites()
        self.assertIn(analysis.PRICE_URL, str(error.exception))
        self.assertIn("manually", str(error.exception))

    def test_empty_governance_is_actionable(self):
        def read(path):
            if path.name == "fragile_state_country_year_panel.csv":
                return pd.DataFrame({"country_code": ["A"], "year": [2000],
                                     "government_effectiveness_estimate": [np.nan]})
            raise FileNotFoundError("synthetic")
        with patch.object(analysis.pd, "read_csv", side_effect=read):
            with self.assertRaisesRegex(RuntimeError, "no finite WGI"):
                analysis.check_prerequisites()

    def test_price_provenance_hash_and_gap_safe_log_changes(self):
        raw = pd.DataFrame(np.nan, index=range(12), columns=range(15))
        raw.iloc[9:, 0] = [2003, 2000, 2001]  # deliberately unsorted with a gap
        for column in [2, 6, 10, 14]:
            raw.iloc[9:, column] = [400, 100, 200]
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "prices.xlsx"
            cache.write_bytes(b"synthetic cached workbook bytes")
            with patch.object(analysis, "PRICE_FILE", cache), \
                 patch.object(analysis.pd, "read_excel", return_value=raw), \
                 patch.object(analysis, "save", side_effect=lambda frame, name: frame):
                result = analysis.load_prices().set_index("year")
            self.assertTrue(result.source_sha256.eq(hashlib.sha256(cache.read_bytes()).hexdigest()).all())
            self.assertTrue(result.source_url.eq(analysis.PRICE_URL).all())
            self.assertTrue(result.source_bytes.eq(cache.stat().st_size).all())
            self.assertAlmostEqual(result.loc[2001, "energy_price_log_change"], np.log(2))
            self.assertTrue(pd.isna(result.loc[2003, "energy_price_log_change"]))


if __name__ == "__main__":
    unittest.main()