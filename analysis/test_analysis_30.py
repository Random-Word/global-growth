"""Offline regressions for Analysis 30 donor eligibility and diagnostic metadata."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import run_analysis_30 as analysis
from matplotlib.figure import Figure


class Analysis30Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        output_patch = patch.object(analysis, "PROC", Path(self.temp.name))
        output_patch.start()
        self.addCleanup(output_patch.stop)
        chart_patch = patch.object(analysis, "CHARTS", Path(self.temp.name))
        chart_patch.start()
        self.addCleanup(chart_patch.stop)
        network_patch = patch.object(
            analysis.requests, "get", side_effect=AssertionError("Offline tests only")
        )
        network_patch.start()
        self.addCleanup(network_patch.stop)
        self.onsets = pd.DataFrame([{"country_code": "T", "onset_year": 2000}])

    def panel(self):
        rows = []
        for index, code in enumerate(["T", "BAD", "C0", "C1", "C2", "C3", "C4"]):
            for event_time in range(-5, 6):
                rows.append(
                    {
                        "country_code": code,
                        "country": code,
                        "region": "Region A",
                        "year": 2000 + event_time,
                        "developing_below_50pct_us": True,
                        "log_gdppc": 8 + max(index - 1, 0) * 0.1 + 0.02 * event_time,
                        "gdppc_growth_pct": 2.0,
                        "gross_capital_formation_pct": (
                            30.0 if code == "T" and event_time >= 0 else 18.0
                        ),
                        "trade_pct_gdp": 40.0 + max(index - 1, 0),
                        "fertility_rate": 3.0,
                        "government_effectiveness_score": 45.0,
                    }
                )
        return pd.DataFrame(rows)

    def change_investment(self, panel, event_time, value):
        panel.loc[
            panel.country_code.eq("BAD") & panel.year.eq(2000 + event_time),
            "gross_capital_formation_pct",
        ] = value

    def test_synthetic_excludes_high_investment_at_every_window_year(self):
        # A single threshold crossing need not produce a sustained onset.
        # In particular +5 reproduces the PHL/KIR endpoint leak.
        for event_time in range(-5, 6):
            with self.subTest(event_time=event_time):
                panel = self.panel()
                self.change_investment(panel, event_time, 25.01)
                _, fits = analysis.synthetic_control_like(panel, self.onsets)
                self.assertEqual(len(fits), 1)
                self.assertEqual(fits.iloc[0].n_donors, 5)
                self.assertNotIn("BAD", fits.iloc[0].donor_country_codes.split(";"))

    def test_synthetic_requires_observed_finite_investment_through_horizon_end(self):
        for event_time in (-5, 0, 5):
            for value in (np.nan, np.inf, -np.inf):
                with self.subTest(event_time=event_time, value=value):
                    panel = self.panel()
                    self.change_investment(panel, event_time, value)
                    _, fits = analysis.synthetic_control_like(panel, self.onsets)
                    self.assertEqual(fits.iloc[0].n_donors, 5)
                    self.assertNotIn("BAD", fits.iloc[0].donor_country_codes.split(";"))

    def test_synthetic_accepts_exact_threshold_and_exports_same_region_pool(self):
        panel = self.panel()
        panel.loc[panel.country_code.eq("BAD"), "gross_capital_formation_pct"] = 25.0
        _, fits = analysis.synthetic_control_like(panel, self.onsets)
        fit = fits.iloc[0]
        self.assertEqual(fit.n_donors, 6)
        self.assertIn("BAD", fit.donor_country_codes.split(";"))
        self.assertEqual(fit.donor_regions.split(";"), ["Region A"] * 6)
        self.assertEqual(fit.region, fit.treated_region)
        self.assertEqual(fit.largest_weight_region, fit.treated_region)
        self.assertIn("-5..+5 inclusive", fit.method_note)

    def test_synthetic_keeps_region_and_minimum_donor_restrictions(self):
        panel = self.panel()
        panel.loc[panel.country_code.eq("BAD"), "region"] = "Region B"
        _, fits = analysis.synthetic_control_like(panel, self.onsets)
        self.assertEqual(fits.iloc[0].n_donors, 5)
        self.assertNotIn("BAD", fits.iloc[0].donor_country_codes.split(";"))
        panel = panel[panel.country_code.ne("C4")]
        trajectories, fits = analysis.synthetic_control_like(panel, self.onsets)
        self.assertTrue(fits.empty)
        self.assertTrue(trajectories.empty)

    def test_window_requires_each_year_once_not_just_correct_row_count(self):
        group = self.panel().query("country_code == 'BAD'").copy()
        for pre_years in (3, 5):
            for event_time in (-pre_years, 0, 5):
                with self.subTest(pre_years=pre_years, event_time=event_time):
                    missing = group[group.year.ne(2000 + event_time)]
                    self.assertFalse(
                        analysis.has_clean_investment_window(missing, 2000, pre_years)
                    )
                    # Duplicate an in-window year to conceal the missing row count.
                    duplicate = group[group.year.eq(2001)]
                    malformed = pd.concat([missing, duplicate], ignore_index=True)
                    self.assertFalse(
                        analysis.has_clean_investment_window(malformed, 2000, pre_years)
                    )
            duplicate = pd.concat([group, group[group.year.eq(2001)]])
            self.assertFalse(analysis.has_clean_investment_window(duplicate, 2000, pre_years))

    def test_clean_window_does_not_filter_outside_its_endpoints(self):
        group = self.panel().query("country_code == 'BAD'").copy()
        for pre_years in (3, 5):
            outside = pd.concat(
                [
                    group,
                    pd.DataFrame(
                        {
                            "year": [2000 - pre_years - 1, 2006],
                            "gross_capital_formation_pct": [100.0, np.nan],
                        }
                    ),
                ]
            )
            self.assertTrue(analysis.has_clean_investment_window(outside, 2000, pre_years))

    def test_clean_window_rejects_nullable_missing_investment(self):
        group = self.panel().query("country_code == 'BAD'").copy()
        group["gross_capital_formation_pct"] = group["gross_capital_formation_pct"].astype("Float64")
        group.loc[group.year.eq(2005), "gross_capital_formation_pct"] = pd.NA
        for pre_years in (3, 5):
            self.assertFalse(analysis.has_clean_investment_window(group, 2000, pre_years))

    def test_matched_distance_remains_region_blind_and_exports_control_region(self):
        panel = self.panel()
        panel.loc[panel.country_code.eq("BAD"), "region"] = "Region B"
        matches, _ = analysis.match_investment_events(panel, self.onsets)
        match = matches.iloc[0]
        self.assertEqual(match.control_country_code, "BAD")
        self.assertEqual(match.match_distance, 0.0)
        self.assertEqual(match.region, match.treated_region)
        self.assertEqual(match.treated_region, "Region A")
        self.assertEqual(match.control_region, "Region B")
        self.assertFalse(match.same_region)

    def test_matched_controls_share_clean_window_rule(self):
        for event_time in range(-3, 6):
            for value in (25.01, np.nan):
                with self.subTest(event_time=event_time, value=value):
                    panel = self.panel()
                    self.change_investment(panel, event_time, value)
                    matches, _ = analysis.match_investment_events(panel, self.onsets)
                    self.assertNotEqual(matches.iloc[0].control_country_code, "BAD")
        panel = self.panel()
        self.change_investment(panel, 5, 25.0)
        matches, _ = analysis.match_investment_events(panel, self.onsets)
        self.assertEqual(matches.iloc[0].control_country_code, "BAD")

    def test_diagnostic_status_and_deprecated_aliases(self):
        for p_value, expected, label in (
            (0.019, False, "rejected at 10%"),
            (0.099, False, "rejected at 10%"),
            (0.10, True, "not rejected at 10%"),
            (0.8, True, "not rejected at 10%"),
            (np.nan, None, "unavailable (non-finite p-value)"),
            (np.inf, None, "unavailable (non-finite p-value)"),
        ):
            with self.subTest(p_value=p_value):
                diagnostic = analysis.pre_period_balance_diagnostic(p_value)
                self.assertEqual(diagnostic["pre_period_balance_status"], label)
                self.assertIs(diagnostic["pre_period_balance_not_rejected_10pct"], expected)
                self.assertIs(diagnostic["pretrend_passes_10pct"], expected)
                np.testing.assert_equal(
                    diagnostic["pre_period_balance_joint_p_value"],
                    diagnostic["pretrend_joint_p_value"],
                )
                self.assertIn("not proof", diagnostic["pre_period_balance_note"])
                self.assertIn("Deprecated", diagnostic["pretrend_note"])

    def test_actual_wald_is_balance_not_slope_and_status_follows_p_value(self):
        noise = np.random.default_rng(30).normal(size=(6, 9))
        balanced = np.vstack([noise, -noise])
        for offset, rejected in ((0.0, False), (4.0, True)):
            with self.subTest(offset=offset):
                events = pd.DataFrame(
                    [
                        {
                            "pair_id": f"T{i}_2000",
                            "treated_country_code": f"T{i}",
                            "event_time": event_time,
                            "difference_pp": balanced[i, event_time + 3] + offset,
                        }
                        for i in range(12)
                        for event_time in range(-3, 6)
                    ]
                )
                summary = pd.DataFrame({"event_time": range(-3, 6)})
                with patch.object(analysis, "BOOTSTRAPS", 20):
                    estimates, diagnostics = analysis.matched_estimates(events, summary)
                self.assertAlmostEqual(diagnostics["pre_slope_pp_per_year"], 0.0)
                self.assertEqual(diagnostics["pre_period_balance_joint_p_value"] < 0.1, rejected)
                label = "rejected at 10%" if rejected else "not rejected at 10%"
                for status in estimates.causal_status:
                    self.assertIn("pre-period balance " + label, status)
                    self.assertIn("not identified", status)
                    self.assertIn("parallel trends not established", status)
                    self.assertNotIn("failed joint pre-trend", status)
                saved = pd.read_csv(analysis.PROC / "causal_development_event_study.csv")
                self.assertTrue(saved.pre_period_balance_status.eq(label).all())
                np.testing.assert_allclose(
                    saved.pre_period_balance_joint_p_value, saved.pretrend_joint_p_value
                )

    def test_method_metadata_describes_implemented_matching_and_balance(self):
        limits = analysis.method_limits().set_index("requested_element")
        matched = limits.loc["matched event study", "reason_or_limit"]
        assert isinstance(matched, str)
        self.assertIn("Region is neither a distance feature nor an exact restriction", matched)
        for feature in analysis.MATCH_FEATURES:
            self.assertIn(feature, matched)
        for phrase in ("treated_region", "control_region", "-3..+5 inclusive", "not parallel trends"):
            self.assertIn(phrase, matched)
        synthetic = limits.loc["synthetic-control-like comparison", "reason_or_limit"]
        assert isinstance(synthetic, str)
        for phrase in (
            "Same-region", "-5..+5 inclusive",
            f"at least {analysis.MIN_SYNTHETIC_DONORS}", "post-onset investment",
            "full nonnegative donor weights", "diagnostic-only",
        ):
            self.assertIn(phrase, synthetic)
        self.assertEqual(limits.loc["synthetic-control-like comparison", "status"], "not_evaluated")

    def synthetic_cases(self, count):
        trajectories, fits = analysis.synthetic_control_like(self.panel(), self.onsets)
        if count == 0:
            return trajectories.iloc[:0].copy(), fits.iloc[:0].copy()
        return tuple(
            pd.concat(
                [frame.assign(treated_country_code=f"T{i}") for i in range(count)],
                ignore_index=True,
            )
            for frame in (trajectories, fits)
        )

    def test_sparse_aggregates_have_status_counts_and_no_numbers_or_bootstrap(self):
        self.assertEqual(analysis.MIN_SYNTHETIC_CASES, 5)
        self.assertEqual(analysis.MIN_SYNTHETIC_DONORS, 5)
        for count in (0, 1, 2, 4):
            with self.subTest(count=count):
                trajectories, fits = self.synthetic_cases(count)
                with patch.object(analysis.np.random, "default_rng") as rng:
                    estimates = analysis.synthetic_estimate(trajectories, fits)
                    rng.return_value.choice.assert_not_called()
                self.assertEqual(len(estimates), 2)
                self.assertTrue(estimates.status.eq("insufficient_support").all())
                self.assertTrue(estimates.n_events.eq(count).all())
                self.assertTrue(estimates.required_events.eq(5).all())
                self.assertTrue(estimates[["point_estimate", "ci_low", "ci_high"]].isna().all().all())
                self.assertTrue(estimates.reporting_note.str.contains("diagnostic-only").all())
                # Round-trip uses blank numeric cells, not zero-valued sentinels.
                path = analysis.PROC / "causal_development_estimates.csv"
                estimates.to_csv(path, index=False)
                saved = pd.read_csv(path)
                self.assertTrue(saved[["point_estimate", "ci_low", "ci_high"]].isna().all().all())

    def test_supported_aggregate_and_sparse_fit_subset_are_gated_independently(self):
        trajectories, fits = self.synthetic_cases(5)
        # Keep only two cases under the 5% pre-fit cutoff.
        fits.loc[fits.index >= 2, "pre_rmspe_pct"] = 6.0
        with patch.object(analysis, "BOOTSTRAPS", 20):
            estimates = analysis.synthetic_estimate(trajectories, fits)
        full, subset = estimates.iloc[0], estimates.iloc[1]
        self.assertEqual(full.status, "estimated_with_diagnostic")
        self.assertEqual(full.n_events, 5)
        self.assertTrue(np.isfinite(full[["point_estimate", "ci_low", "ci_high"]].to_numpy(dtype=float)).all())
        self.assertIn("not causal", full.reporting_note)
        self.assertEqual(subset.status, "insufficient_support")
        self.assertEqual(subset.n_events, 2)
        self.assertTrue(subset[["point_estimate", "ci_low", "ci_high"]].isna().all())
        fits["pre_rmspe_pct"] = 1.0
        with patch.object(analysis, "BOOTSTRAPS", 20):
            supported = analysis.synthetic_estimate(trajectories, fits)
        self.assertTrue(supported.status.eq("estimated_with_diagnostic").all())
        self.assertTrue(supported[["point_estimate", "ci_low", "ci_high"]].notna().all().all())

    def test_diagnostic_exports_include_full_aligned_weights_and_reconstruct_gap(self):
        panel = self.panel()
        trajectories, fits = analysis.synthetic_control_like(panel, self.onsets)
        fit = fits.iloc[0]
        codes = fit.donor_country_codes.split(";")
        weights = np.array([float(w) for w in fit.donor_weights.split(";")])
        self.assertEqual(len(codes), fit.n_donors)
        self.assertEqual(len(weights), fit.n_donors)
        self.assertEqual(len(fit.donor_regions.split(";")), fit.n_donors)
        self.assertTrue((weights >= 0).all())
        self.assertAlmostEqual(weights.sum(), 1.0)
        self.assertAlmostEqual(weights.max(), fit.largest_weight)
        self.assertEqual(codes[int(weights.argmax())], fit.largest_weight_country)
        self.assertAlmostEqual(1 / (weights ** 2).sum(), fit.effective_donors)
        logs = panel.pivot(index="country_code", columns="year", values="log_gdppc")
        synthetic = weights @ logs.loc[codes].to_numpy()
        actual = logs.loc["T"].to_numpy()
        expected = 100 * (np.exp((actual - actual[4]) - (synthetic - synthetic[4])) - 1)
        np.testing.assert_allclose(trajectories.actual_minus_synthetic_pct, expected)
        for name, expected_rows in (("synthetic_controls", 11), ("synthetic_fit", 1)):
            saved = pd.read_csv(analysis.PROC / f"causal_development_{name}.csv")
            self.assertEqual(len(saved), expected_rows)
            self.assertTrue(saved.reporting_scope.eq("diagnostic_only").all())
            self.assertTrue(saved.aggregate_status.eq("insufficient_support").all())
            self.assertTrue(saved.retained_cases.eq(1).all())
            self.assertTrue(saved.required_cases.eq(5).all())

    def test_zero_cases_overwrite_old_diagnostic_exports_with_readable_headers(self):
        analysis.synthetic_control_like(self.panel(), self.onsets)
        # Only four potential donors remain: no fit is permissible.
        panel = self.panel()[~self.panel().country_code.isin(["C3", "C4"])]
        trajectories, fits = analysis.synthetic_control_like(panel, self.onsets)
        self.assertTrue(fits.empty)
        self.assertTrue(trajectories.empty)
        for name in ("synthetic_controls", "synthetic_fit"):
            saved = pd.read_csv(analysis.PROC / f"causal_development_{name}.csv")
            self.assertTrue(saved.empty)
            self.assertIn("reporting_scope", saved.columns)
        estimates = analysis.synthetic_estimate(trajectories, fits)
        self.assertTrue(estimates.status.eq("insufficient_support").all())

    def test_chart_sparse_notice_and_normal_diagnostic_caption(self):
        for count in (0, 2, 5):
            with self.subTest(count=count):
                trajectories, fits = self.synthetic_cases(count)
                with patch.object(Figure, "savefig", autospec=True) as save:
                    analysis.chart_synthetic(trajectories, fits)
                fig = save.call_args.args[0]
                texts = "\n".join(text.get_text() for text in fig.texts)
                texts += "\n" + "\n".join(
                    text.get_text() for ax in fig.axes for text in ax.texts
                )
                self.assertIn(f"Retained cases: {count}", texts)
                self.assertIn("diagnostic-only", texts)
                if count < 5:
                    self.assertIn("Required cases: 5", texts)
                    self.assertIn("Insufficient support", texts)
                    self.assertIn("withdrawn", texts)
                    self.assertIn("No aggregate effect", texts)
                    self.assertFalse(any(ax.lines or ax.collections for ax in fig.axes))
                else:
                    self.assertIn("required cases: 5", texts)
                    self.assertIn("not an experiment", texts)
                    self.assertNotIn("withdrawn", texts)
                    self.assertTrue(any(ax.lines for ax in fig.axes))

    def test_sparse_chart_replaces_stale_file(self):
        trajectories, fits = self.synthetic_cases(2)
        path = analysis.CHARTS / "130_causal_development_synthetic_control.png"
        path.write_bytes(b"stale aggregate chart")
        analysis.chart_synthetic(trajectories, fits)
        self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_main_completes_sparse_publication_and_overwrites_old_outputs(self):
        panel = self.panel()
        treated = panel[panel.country_code.eq("T")]
        panel = pd.concat([
            panel[panel.country_code.ne("T")],
            treated.assign(country_code="T0"),
            treated.assign(country_code="T1"),
        ], ignore_index=True)
        onsets = pd.DataFrame({"country_code": ["T0", "T1"], "onset_year": [2000, 2000]})
        summary = pd.DataFrame(columns=[
            "regime", "n_spells", "n_countries", "mean_outcome_growth_pct",
            "growth_cluster_ci_low", "growth_cluster_ci_high", "success_rate_ge_3pct",
            "adjusted_difference_vs_stable_pp", "adjusted_ci_low", "adjusted_ci_high",
        ])
        sensitivity = pd.DataFrame(columns=["capacity_cutoff", "conflict_definition"])
        matched_rows = pd.DataFrame({
            "method": ["matched_event_study_post_level", "matched_event_study_did"],
            "point_estimate": [2.0, 3.0], "ci_low": [1.0, 2.0], "ci_high": [3.0, 4.0],
        })
        replacements = {
            "build_country_year_panel": (panel, pd.DataFrame()),
            "build_fixed_window_spells": pd.DataFrame(),
            "summarize_regimes": summary,
            "definition_sensitivity": sensitivity,
            "chart_fragile_regimes": None,
            "chart_fragile_sensitivity": None,
            "clean_investment_onsets": onsets,
            "match_investment_events": (pd.DataFrame(index=range(6)), pd.DataFrame()),
            "bootstrap_event_series": pd.DataFrame(),
            "matched_estimates": (matched_rows, {}),
        }
        for name in ("estimates", "method_limits", "synthetic_controls", "synthetic_fit"):
            (analysis.PROC / f"causal_development_{name}.csv").write_text("stale aggregate\n10.85\n")
        chart_path = analysis.CHARTS / "130_causal_development_synthetic_control.png"
        chart_path.write_bytes(b"stale chart")
        with ExitStack() as stack:
            for name, result in replacements.items():
                stack.enter_context(patch.object(analysis, name, return_value=result))
            matched_chart = stack.enter_context(patch.object(analysis, "chart_matched_event"))
            stack.enter_context(patch("builtins.print"))
            analysis.main()
        matched_chart.assert_called_once()
        estimates = pd.read_csv(analysis.PROC / "causal_development_estimates.csv")
        pd.testing.assert_frame_equal(estimates.iloc[:2][matched_rows.columns], matched_rows)
        synthetic = estimates.iloc[2:]
        self.assertTrue(synthetic.status.eq("insufficient_support").all())
        self.assertTrue(synthetic.n_events.eq(2).all())
        self.assertTrue(synthetic[["point_estimate", "ci_low", "ci_high"]].isna().all().all())
        fits = pd.read_csv(analysis.PROC / "causal_development_synthetic_fit.csv")
        trajectories = pd.read_csv(analysis.PROC / "causal_development_synthetic_controls.csv")
        self.assertEqual(len(fits), 2)
        self.assertEqual(len(trajectories), 22)
        self.assertTrue(fits.reporting_scope.eq("diagnostic_only").all())
        limits = pd.read_csv(analysis.PROC / "causal_development_method_limits.csv").set_index("requested_element")
        self.assertEqual(limits.loc["synthetic-control-like comparison", "status"], "insufficient_support")
        self.assertTrue(chart_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_method_limits_and_notice_use_current_counts_and_threshold(self):
        trajectories, fits = self.synthetic_cases(2)
        with patch.object(analysis, "MIN_SYNTHETIC_CASES", 7):
            estimates = analysis.synthetic_estimate(trajectories, fits)
            limits = analysis.method_limits(estimates).set_index("requested_element")
            row = limits.loc["synthetic-control-like comparison"]
            self.assertEqual(row["status"], "insufficient_support")
            self.assertIn("Retained cases: 2; required cases: 7", row["reason_or_limit"])
            self.assertIn("confidence intervals withheld", row["reason_or_limit"])
            with patch.object(Figure, "savefig", autospec=True) as save:
                analysis.chart_synthetic(trajectories, fits)
            fig = save.call_args.args[0]
            texts = "\n".join(text.get_text() for ax in fig.axes for text in ax.texts)
            self.assertIn("Retained cases: 2 | Required cases: 7", texts)
        trajectories, fits = self.synthetic_cases(5)
        with patch.object(analysis, "BOOTSTRAPS", 20):
            estimates = analysis.synthetic_estimate(trajectories, fits)
        limits = analysis.method_limits(estimates).set_index("requested_element")
        row = limits.loc["synthetic-control-like comparison"]
        self.assertEqual(row["status"], "estimated_with_diagnostic")
        self.assertIn("Retained cases: 5; required cases: 5", row["reason_or_limit"])
        self.assertNotIn("withheld", row["reason_or_limit"])


if __name__ == "__main__":
    unittest.main()