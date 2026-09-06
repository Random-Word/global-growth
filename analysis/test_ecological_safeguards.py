"""Focused offline regression tests; never execute the full analysis pipelines."""

import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import ecological_safeguards as safeguards
import run_analysis_18 as nitrogen
import run_analysis_32 as joint
import run_analysis_34 as sensitivity


class EcologicalSafeguardTests(unittest.TestCase):
    def test_scorecard_counts_processes_not_nutrient_components(self):
        rows = safeguards.PB_2023
        self.assertEqual(len(rows), 9)
        self.assertEqual(sum(status == "Transgressed" for _, status in rows), 6)
        names = [name for name, _ in rows]
        self.assertIn("Biogeochemical flows (N and P)", names)
        self.assertIn("Atmospheric aerosol loading", names)
        self.assertIn("Novel entities", names)
        self.assertFalse(any("Living Planet Index" in name for name in names))

    def test_withdrawal_has_no_numeric_compliance_fields(self):
        frame = safeguards.withdrawn_table(safeguards.LEGACY_N_REASON)
        self.assertEqual(list(frame.columns), ["status", "interpretation_limit"])
        self.assertEqual(frame.iloc[0]["status"], "withdrawn")
        for text in ("biological", "runoff", "gross fixation"):
            self.assertIn(text, frame.iloc[0]["interpretation_limit"].lower())

    def test_nitrogen_only_refresh_preserves_other_claim_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = pd.DataFrame(
                [
                    {"claim": "Other agent's welfare row", "status": "keep"},
                    {"claim": "Nitrogen old compliance claim", "status": "old"},
                ]
            )
            original.to_csv(root / "robustness_claim_confidence.csv", index=False)
            with patch.object(nitrogen, "PROC", root), patch.object(
                nitrogen, "BASE", root
            ), patch.object(nitrogen, "CHARTS", root):
                nitrogen.refresh_nitrogen_only()
            after = pd.read_csv(root / "robustness_claim_confidence.csv")
            self.assertEqual(after.iloc[0]["status"], "keep")
            self.assertEqual(after.iloc[0]["claim"], original.iloc[0]["claim"])
            self.assertEqual(
                after.iloc[1]["status"], "Unresolved; invalid compliance test"
            )
            result = pd.read_csv(root / "robustness_nitrogen_uncertainty.csv")
            self.assertEqual(result.iloc[0]["status"], "withdrawn")

    def test_all_nitrogen_gates_are_unassessed(self):
        matrix = joint.build_feasibility_matrix()
        rows = matrix[matrix["condition"].eq("nitrogen")]
        self.assertEqual(len(rows), 4)
        self.assertTrue(rows["feasibility_code"].eq(2).all())
        self.assertTrue(rows["note"].str.startswith("WITHDRAWN").all())

    def test_legacy_joint_builders_fail_closed(self):
        for builder in (
            joint.enumerate_range_corners,
            joint.build_partial_identification,
            joint.build_dependence_sensitivity,
            joint.build_leave_one_out,
            joint.build_value_of_information,
            joint.build_break_even,
            joint.legacy_main,
        ):
            with self.subTest(builder=builder.__name__):
                with self.assertRaisesRegex(ValueError, "WITHDRAWN"):
                    builder()
        self.assertTrue(np.isnan(joint.CENTRAL["nitrogen"]))

    def test_synthetic_benchmarks_are_not_compliance_tests(self):
        rows = sensitivity.reversal_regions()
        n_rows = rows[rows["expression"].str.startswith("synthetic_nitrogen")]
        self.assertEqual(len(n_rows), 2)
        self.assertTrue(
            n_rows["condition"].str.contains("illustrative input benchmark").all()
        )
        self.assertTrue(
            n_rows["interpretation"]
            .str.contains("not a planetary-boundary compliance test")
            .all()
        )

    def test_regional_food_equation_retained_with_scope_limit(self):
        # Extract only the pure scenario function/constants, avoiding module-level
        # baseline file reads. This tests the actual producer on a tiny fixture.
        source = Path(__file__).with_name("run_analysis_31.py")
        tree = ast.parse(source.read_text())
        wanted = {
            "FOOD_SCENARIOS",
            "POPULATION_2050_FACTOR",
            "CALORIE_DEMAND_FACTOR",
            "CLIMATE_YIELD_PENALTY",
            "FEED_SHARE_OF_CROPLAND",
        }
        nodes: list[ast.stmt] = [
            node
            for node in tree.body
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "evaluate_food_scenario"
            )
            or (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id in wanted for t in node.targets
                )
            )
        ]
        namespace = {"pd": pd, "NITROGEN_SCOPE": safeguards.NITROGEN_SCOPE}
        exec(
            compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"),
            namespace,
        )
        baseline = pd.Series(
            {
                "region": "North America",
                "region_short": "NAM",
                "cropland_mha": 100,
                "pasture_and_other_ag_land_mha": 200,
                "agricultural_land_mha": 300,
                "synthetic_nitrogen_tg": 10,
                "phosphate_p2o5_tg": 5,
                "water_stress_pct_area_weighted": 20,
                "cereal_yield_t_ha": 4,
            }
        )
        row = namespace["evaluate_food_scenario"](baseline, "proven_measures")
        expected = 10 * (1.12 * 0.9 * (1 - 0.35 * 0.25) / 1.15) * 0.85
        self.assertAlmostEqual(row["synthetic_nitrogen_required_tg"], expected)
        self.assertFalse(row["planetary_boundary_test_valid"])
        self.assertEqual(row["nitrogen_metric_limit"], safeguards.NITROGEN_SCOPE)

    def test_energy_producer_has_no_unsupported_numeric_series(self):
        source = Path(__file__).with_name("run_analysis_17.py").read_text()
        self.assertNotIn('"share_final"', source)
        self.assertNotIn('"lcos":', source)
        self.assertIn("LCOS_REASON", source)
        self.assertIn("FINAL_ENERGY_REASON", source)
        self.assertIn("not final-energy consumption", safeguards.FINAL_ENERGY_REASON)
        self.assertIn("$/kWh", safeguards.LCOS_REASON)
        self.assertIn("$/MWh", safeguards.LCOS_REASON)

    def test_material_random_stream_not_changed_by_nitrogen_withdrawal(self):
        old = np.random.default_rng(42)
        for low, mode, high in (
            (5, 10, 15),
            (15, 25, 40),
            (5, 12, 20),
            (0, 10, 20),
            (0, 20, 40),
            (2, 8, 15),
        ):
            old.triangular(low, mode, high, 50_000)
        new = np.random.default_rng(42)
        new.random(6 * 50_000)
        np.testing.assert_array_equal(old.random(100), new.random(100))

    def test_currency_units_render_as_plain_text(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(safeguards.plt, "close"):
                safeguards.withdrawal_chart(
                    Path(directory) / "notice.png",
                    "Units",
                    safeguards.LCOS_REASON,
                )
                fig = safeguards.plt.gcf()
            try:
                text = fig.axes[0].texts[0]
                self.assertFalse(text.get_parse_math())
                self.assertIn("$/kWh", text.get_text())
                self.assertIn("$/MWh", text.get_text())
            finally:
                safeguards.plt.close(fig)


if __name__ == "__main__":
    unittest.main()
