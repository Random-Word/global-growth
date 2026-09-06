"""Offline regressions for Analysis 26/28; no full analysis pipeline required."""

import contextlib
import io
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import ecological_safeguards as safeguards
import run_analysis_26 as scenario
import run_analysis_28 as audit


class ProbabilityWithdrawalTests(unittest.TestCase):
    def assert_withdrawn(self, frame):
        self.assertEqual(list(frame.columns), ["status", "interpretation_limit"])
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["status"], "withdrawn")
        self.assertEqual(frame.iloc[0]["interpretation_limit"], safeguards.JOINT_REASON)
        self.assertTrue(frame.select_dtypes(include="number").empty)

    def test_analysis26_import_does_not_read_data_or_publish(self):
        with patch.object(
            pd, "read_csv", side_effect=AssertionError("data read")
        ), patch.object(
            pd.DataFrame, "to_csv", side_effect=AssertionError("CSV write")
        ), patch.object(
            safeguards, "withdrawal_chart", side_effect=AssertionError("chart write")
        ):
            namespace = runpy.run_path(str(Path(scenario.__file__)))
        self.assertTrue(callable(namespace["main"]))

    def test_analysis26_overwrites_stale_outputs_without_upstream_reads(self):
        for state in ("missing", "withdrawn", "legacy"):
            with self.subTest(
                upstream=state
            ), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "robustness_nitrogen_uncertainty.csv"
                if state == "withdrawn":
                    safeguards.withdrawn_table(safeguards.LEGACY_N_REASON).to_csv(
                        source, index=False
                    )
                elif state == "legacy":
                    pd.DataFrame(
                        [
                            {
                                "scenario": "Full stack",
                                "prob_at_or_below_Richardson_62": 0.476,
                            }
                        ]
                    ).to_csv(source, index=False)
                names = ("scenario_joint_probability.csv", "scenario_claim_mapping.csv")
                for name in names:
                    pd.DataFrame(
                        [{"joint_all": 0.018, "marginal_central": 0.264}]
                    ).to_csv(root / name, index=False)
                with patch.object(scenario, "PROC", root), patch.object(
                    scenario, "CHARTS", root
                ), patch.object(
                    pd, "read_csv", side_effect=AssertionError("upstream read")
                ), patch.object(
                    scenario, "withdrawal_chart"
                ) as chart, contextlib.redirect_stdout(
                    io.StringIO()
                ):
                    self.assertIsNone(scenario.main())
                for name in names:
                    self.assert_withdrawn(pd.read_csv(root / name))
                self.assertEqual(
                    [call.args[0].name for call in chart.call_args_list],
                    [
                        "114_joint_scenario_probability.png",
                        "115_conditions_met_distribution.png",
                    ],
                )
                for call in chart.call_args_list:
                    self.assertIn("withdrawn", call.args[1])
                    self.assertEqual(call.args[2], safeguards.JOINT_REASON)

    def test_analysis28_never_resurrects_stale_probabilities(self):
        for state in ("missing", "withdrawn", "legacy"):
            with self.subTest(
                upstream=state
            ), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "scenario_joint_probability.csv"
                if state == "withdrawn":
                    safeguards.withdrawn_table(safeguards.JOINT_REASON).to_csv(
                        source, index=False
                    )
                elif state == "legacy":
                    pd.DataFrame(
                        [{"row_type": "joint_summary", "joint_all": 0.018}]
                    ).to_csv(source, index=False)
                pd.DataFrame([{"joint_probability": 0.018}]).to_csv(
                    root / "joint_probability_audit.csv", index=False
                )
                with patch.object(audit, "PROC", root), patch.object(
                    audit, "CHARTS", root
                ), patch.object(
                    pd, "read_csv", side_effect=AssertionError("upstream read")
                ), patch.object(
                    audit, "withdrawal_chart"
                ) as chart:
                    result = audit.joint_probability_audit()
                self.assert_withdrawn(result)
                self.assert_withdrawn(pd.read_csv(root / "joint_probability_audit.csv"))
                chart.assert_called_once_with(
                    root / "121_joint_probability_assumption_range.png",
                    "Chart 121: Joint-probability assumption range withdrawn",
                    safeguards.JOINT_REASON,
                )

    def test_analysis28_default_main_accepts_withdrawn_schema(self):
        # Exercise the default orchestration/console consumer without running its
        # unrelated datasets, regressions or bootstrap. A column projection onto
        # the old probability schema here would still break sequential execution.
        frame = pd.DataFrame([{"retained": 1}])
        events = pd.DataFrame(
            [
                {
                    "investment_bucket": "high (>25%)",
                    "country_code": "KOR",
                    "scorable": True,
                    "country": "Korea",
                }
            ]
        )
        with patch.object(
            audit, "same_basis_poverty_gap", return_value=(frame, frame)
        ) as gap, patch.object(
            audit, "chart_same_basis_gap"
        ) as gap_chart, patch.object(
            audit, "fixed_window_investment_events", return_value=(events, frame)
        ) as investment, patch.object(
            audit, "chart_investment_base_rate"
        ) as investment_chart, patch.object(
            audit,
            "joint_probability_audit",
            return_value=safeguards.withdrawn_table(safeguards.JOINT_REASON),
        ) as joint, patch.object(
            audit, "pip_growth_incidence", return_value=(frame, frame)
        ) as incidence, contextlib.redirect_stdout(
            io.StringIO()
        ) as output:
            self.assertIsNone(audit.main())
        for function in (gap, investment, joint, incidence):
            function.assert_called_once_with()
        gap_chart.assert_called_once_with(frame, frame)
        investment_chart.assert_called_once_with(frame)
        self.assertIn("WITHDRAWN", output.getvalue())
        self.assertIn("Korea", output.getvalue())

    def test_analysis28_independent_helpers_retained(self):
        self.assertEqual(audit.investment_bucket(14.9), "low (<15%)")
        self.assertEqual(audit.investment_bucket(25), "medium (15-25%)")
        self.assertEqual(audit.investment_bucket(25.1), "high (>25%)")
        runs = audit.contiguous_regimes(
            pd.Series([30.0, 31.0, 32.0, 20.0], index=[2000, 2001, 2003, 2004])
        )
        self.assertEqual(
            runs,
            [
                ("high (>25%)", [2000, 2001]),
                ("high (>25%)", [2003]),
                ("medium (15-25%)", [2004]),
            ],
        )
        self.assertAlmostEqual(audit.cagr(100, 121, 2), 10)

    def test_sequential_entry_points_return_and_refresh_only_owned_artifacts(self):
        # No input data exist in this isolated repo. Running the full Analysis 28
        # by mistake therefore fails rather than quietly doing expensive work.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "analysis"
            scripts.mkdir()
            for module in (scenario, audit, safeguards):
                source = module.__file__
                assert source is not None
                shutil.copyfile(source, scripts / Path(source).name)
            charts = root / "charts"
            charts.mkdir()
            sentinel = charts / "118_same_basis_poverty_gap.png"
            sentinel.write_bytes(b"unrelated artifact must not change")
            runner = (
                "import runpy, sys; "
                "sys.argv = ['run_analysis_26.py']; "
                "runpy.run_path('run_analysis_26.py', run_name='__main__'); "
                "sys.argv = ['run_analysis_28.py', '--corrections-only']; "
                "runpy.run_path('run_analysis_28.py', run_name='__main__'); "
                "print('SEQUENTIAL_PIPELINE_CONTINUED')"
            )
            for _ in range(2):  # Repeated refresh is safe and deterministic.
                result = subprocess.run(
                    [sys.executable, "-c", runner],
                    cwd=scripts,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("SEQUENTIAL_PIPELINE_CONTINUED", result.stdout)
                self.assertNotIn("Traceback", result.stderr)
            proc = root / "data" / "processed"
            self.assertEqual(
                {path.name for path in proc.iterdir()},
                {
                    "scenario_joint_probability.csv",
                    "scenario_claim_mapping.csv",
                    "joint_probability_audit.csv",
                },
            )
            for path in proc.iterdir():
                self.assert_withdrawn(pd.read_csv(path))
            self.assertEqual(
                {path.name for path in charts.iterdir()},
                {
                    sentinel.name,
                    "114_joint_scenario_probability.png",
                    "115_conditions_met_distribution.png",
                    "121_joint_probability_assumption_range.png",
                },
            )
            for path in charts.iterdir():
                if path != sentinel:
                    self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                    self.assertGreater(path.stat().st_size, 1000)
            self.assertEqual(
                sentinel.read_bytes(), b"unrelated artifact must not change"
            )


if __name__ == "__main__":
    unittest.main()
