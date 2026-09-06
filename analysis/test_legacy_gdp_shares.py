"""Focused offline regressions; never import or run the full legacy pipeline."""

import ast
import contextlib
import io
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import unittest
from unittest.mock import Mock, patch

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import requests


ANALYSIS = Path(__file__).resolve().parent
SOURCE = (ANALYSIS / "run_analysis.py").read_text()
CHART_NAMES = {"00_summary_dashboard.png", "06_redistribution_cost.png"}


def section(start, end):
    """Extract complete top-level statements between existing section headers."""
    return SOURCE[SOURCE.index(start):SOURCE.index(end)]


def helpers(root: Path) -> dict[str, Any]:
    # The script intentionally still executes the main pipeline at top level.
    # Load only its setup/helper definitions, with a relocated __file__.
    namespace: dict[str, Any] = {
        "__file__": str(root / "analysis" / "run_analysis.py"),
        "__name__": "legacy_regression_helpers",
    }
    prefix = SOURCE[:SOURCE.index("# LOAD DATA")]
    exec(compile(prefix, str(ANALYSIS / "run_analysis.py"), "exec"), namespace)
    return namespace


class LegacyGdpShareTests(unittest.TestCase):
    def test_both_roots_follow_script_location_not_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "relocated publication"
            for filename in ("run_analysis.py", "download_data.py"):
                with self.subTest(filename=filename):
                    tree = ast.parse((ANALYSIS / filename).read_text())
                    assignments: list[ast.stmt] = [
                        node for node in tree.body
                        if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id in {"BASE", "RAW", "PROC", "CHARTS"}
                                for t in node.targets)
                    ]
                    namespace = {
                        "os": os,
                        "__file__": str(root / "analysis" / filename),
                    }
                    exec(compile(ast.Module(body=assignments, type_ignores=[]), filename, "exec"), namespace)
                    self.assertEqual(Path(namespace["BASE"]), root)
                    self.assertEqual(Path(namespace["RAW"]), root / "data" / "raw")
                    self.assertEqual(Path(namespace["PROC"]), root / "data" / "processed")

    def test_corrections_cli_reads_no_data_and_uses_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "analysis" / "run_analysis.py"
            script.parent.mkdir()
            shutil.copyfile(ANALYSIS / script.name, script)
            output = io.StringIO()
            with patch.object(sys, "argv", [str(script), "--corrections-only"]), patch.object(
                pd, "read_csv", side_effect=AssertionError("data read")
            ), patch.object(
                requests.Session, "request", side_effect=AssertionError("network request")
            ), patch(
                "socket.create_connection", side_effect=AssertionError("network connection")
            ), contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as result:
                runpy.run_path(str(script), run_name="__main__")
            self.assertEqual(result.exception.code, 0)
            self.assertNotIn("Loading data", output.getvalue())
            self.assertIn("WITHDRAWN", output.getvalue())
            self.assertFalse((root / "data").exists())
            self.assertEqual({p.name for p in (root / "charts").iterdir()}, CHART_NAMES)

    def test_relocated_cli_replaces_only_owned_charts_repeatably(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "analysis" / "run_analysis.py"
            script.parent.mkdir()
            shutil.copyfile(ANALYSIS / script.name, script)
            charts = root / "charts"
            charts.mkdir()
            sentinel = charts / "118_same_basis_poverty_gap.png"
            sentinel.write_bytes(b"unrelated user artifact")
            for filename in CHART_NAMES:
                (charts / filename).write_bytes(b"stale GDP-share chart")
            first = None
            for _ in range(2):
                result = subprocess.run(
                    [sys.executable, str(script), "--corrections-only"],
                    cwd=root, capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                current = {name: (charts / name).read_bytes() for name in CHART_NAMES}
                for content in current.values():
                    self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))
                    self.assertGreater(len(content), 1000)
                if first is not None:
                    self.assertEqual(current, first)
                first = current
            self.assertEqual(sentinel.read_bytes(), b"unrelated user artifact")
            self.assertEqual({p.name for p in charts.iterdir()}, CHART_NAMES | {sentinel.name})
            self.assertFalse((root / "data").exists())

    def test_notices_have_no_estimates_and_fit_inside_the_figure(self):
        with tempfile.TemporaryDirectory() as directory:
            namespace = helpers(Path(directory))
            seen = []

            def inspect_figure(fig, *args, **kwargs):
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                texts = [text for ax in fig.axes for text in [ax.title, *ax.texts]]
                text = "\n".join(item.get_text() for item in texts)
                seen.append(text)
                self.assertIn("WITHDRAWN", text)
                self.assertIn("2017-PPP", text)
                self.assertIn("constant-2015 market-US$", text)
                self.assertIn("Analysis 28 / Chart 118", text)
                self.assertIn("not causal attribution", text)
                self.assertNotIn("%", text)
                boxes = [item.get_window_extent(renderer) for item in texts]
                for box in boxes:
                    self.assertGreaterEqual(box.x0, fig.bbox.x0)
                    self.assertGreaterEqual(box.y0, fig.bbox.y0)
                    self.assertLessEqual(box.x1, fig.bbox.x1)
                    self.assertLessEqual(box.y1, fig.bbox.y1)
                for left, box in enumerate(boxes):
                    for other in boxes[left + 1:]:
                        self.assertFalse(box.overlaps(other), "notice text overlaps")
                for ax in fig.axes:
                    self.assertEqual(len(ax.lines) + len(ax.collections) + len(ax.tables), 0)

            with patch.object(Figure, "savefig", autospec=True, side_effect=inspect_figure):
                for filename in CHART_NAMES:
                    namespace["refresh_withdrawn_chart"](filename)
            self.assertEqual(len(seen), 2)
            cost = next(text for text in seen if "Chart 06:" in text)
            self.assertIn("years-of-growth estimate are withdrawn", cost)
            self.assertIn("nominal-military-spending", cost)
            self.assertIn("assumption, not an estimated program cost", cost)

    def test_render_failure_preserves_previous_artifact_and_cleans_tempfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            namespace = helpers(root)
            charts = root / "charts"
            target = charts / "06_redistribution_cost.png"
            target.write_bytes(b"previous complete artifact")
            before_figures = plt.get_fignums()

            def fail_after_partial_write(fig, path):
                Path(path).write_bytes(b"partial image")
                raise OSError("simulated render failure")

            with patch.object(Figure, "savefig", autospec=True, side_effect=fail_after_partial_write):
                with self.assertRaisesRegex(OSError, "simulated render failure"):
                    namespace["refresh_withdrawn_chart"](target.name)
            self.assertEqual(target.read_bytes(), b"previous complete artifact")
            self.assertEqual(list(charts.iterdir()), [target])
            self.assertEqual(plt.get_fignums(), before_figures)

    def test_normal_chart_consumers_and_summary_do_not_reuse_legacy_ratios(self):
        cost = section("# ANALYSIS 6:", "# ANALYSIS 7:")
        summary = SOURCE[SOURCE.index("# SUMMARY DASHBOARD"):]
        tree = ast.parse(cost + "\n" + summary)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertTrue(names.isdisjoint({"results_a1", "gap", "gap685", "gap_copy"}))
        self.assertNotIn("gap_pct_gdp", cost + summary)
        with tempfile.TemporaryDirectory() as directory, patch("builtins.print") as printed:
            namespace = {"os": os, "CHARTS": directory, "GDP_SHARE_WITHDRAWAL": "WITHDRAWN"}
            with patch.dict(namespace, {"refresh_withdrawn_chart": Mock()}) as scope:
                exec(compile(tree, "legacy_consumers", "exec"), scope)
                calls = scope["refresh_withdrawn_chart"].call_args_list
            self.assertEqual([call.args[0] for call in calls], ["06_redistribution_cost.png", "00_summary_dashboard.png"])
            text = "\n".join(str(call.args[0]) for call in printed.call_args_list)
            self.assertIn("GDP SHARES — WITHDRAWN", text)
            self.assertIn("not causal attribution", text)
            for old_claim in ("CONFIRMED", "<1%", "~3-5%", "cheap BECAUSE", "made redistribution cheaper"):
                self.assertNotIn(old_claim, text)

    def test_all_remaining_ratio_access_is_confined_to_labelled_analysis1(self):
        beginning = SOURCE[:SOURCE.index("# ANALYSIS 1:")]
        remaining = SOURCE[SOURCE.index("# ANALYSIS 2:"):]
        for fragment in (beginning, remaining):
            tree = ast.parse(fragment)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    self.assertNotEqual(node.id, "results_a1")
                if isinstance(node, ast.Constant):
                    self.assertNotEqual(node.value, "gap_pct_gdp")

    def test_analysis1_labels_and_console_never_present_ratio_as_gdp_share(self):
        # Synthetic values exercise presentation only, not replacement estimates.
        regional = pd.DataFrame({
            "region_code": ["WLD", "WLD", "EAS"],
            "reporting_year": [2000, 2020, 2020],
            "poverty_gap": [0.1, 0.05, 0.9],
            "reporting_pop": [1e9, 2e9, 1e9],
            "pop_in_poverty": [0.3e9, 0.4e9, 0.8e9],
        })
        with tempfile.TemporaryDirectory() as directory:
            namespace = helpers(Path(directory))
            namespace.update({
                "np": np, "pd": pd, "plt": plt,
                "wdi": pd.DataFrame({
                    "country_code": ["WLD", "WLD"], "year": [2000, 2020],
                    "gdp_constant_2015usd": [1e13, 2e13],
                }),
                "pip_regional": {str(line): regional for line in (2.15, 3.65, 6.85, 10.0)},
            })
            seen = []

            def inspect_legacy(fig, *args, **kwargs):
                seen.append("\n".join(
                    [text.get_text() for text in fig.texts]
                    + [ax.get_title() for ax in fig.axes]
                    + [ax.get_ylabel() for ax in fig.axes]
                    + [label for ax in fig.axes for label in ax.get_legend_handles_labels()[1]]
                ))

            output = io.StringIO()
            with patch.object(Figure, "savefig", autospec=True, side_effect=inspect_legacy), contextlib.redirect_stdout(output):
                exec(compile(section("# ANALYSIS 1:", "# ANALYSIS 2:"), "analysis1", "exec"), namespace)
            self.assertEqual(len(seen), 2)
            for text in seen:
                self.assertIn("LEGACY MIXED-BASIS", text)
                self.assertIn("x100; not a valid GDP share", text)
                self.assertNotIn("Gap as % of GDP", text)
            self.assertNotIn("% of GDP", output.getvalue())
            self.assertNotIn("ppt", output.getvalue())
            self.assertIn("GDP-share levels and changes WITHDRAWN", output.getvalue())
            for frame in namespace["results_a1"].values():
                self.assertEqual(list(frame["year"]), [2000, 2020])


if __name__ == "__main__":
    unittest.main()