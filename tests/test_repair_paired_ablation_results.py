from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.repair_paired_ablation_results import repair_paired_results
from scripts.repair_paired_ablation_results import transition_repair_fanout_from_asl


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_repair_script_runs_as_a_direct_cli() -> None:
	completed = subprocess.run(
		(sys.executable, "scripts/repair_paired_ablation_results.py", "--help"),
		cwd=PROJECT_ROOT,
		capture_output=True,
		text=True,
		check=False,
	)

	assert completed.returncode == 0, completed.stderr


def test_transition_repair_fanout_ignores_query_support_helpers() -> None:
	asl = """
+!g_query_trans_1 : query & done <- true.
+!g_query_trans_1 : query & not first <- !first.
+!g_query_trans_1 : query & not second <- !second.
+!g_query_support : query & option_a <- action_a.
+!g_query_support : query & option_b <- action_b.
+!g_query_support : query & option_c <- action_c.
+!g_query_support : query & option_d <- action_d.
"""

	assert transition_repair_fanout_from_asl(asl) == 3


def test_repair_paired_results_replaces_derived_fanout_everywhere(
	tmp_path: Path,
) -> None:
	run_root = tmp_path / "paper"
	child_root = run_root / "temporal_runs/paper-certified_balanced"
	case_root = child_root / "cases/toy/toy_p1"
	(case_root / "jason").mkdir(parents=True)
	(case_root / "jason/agentspeak_generated.asl").write_text(
		"""
+!g_toy_p1_trans_1_repair_1_1 : toy_p1 & done <- true.
+!g_toy_p1_trans_1_repair_1_1 : toy_p1 & not done <- !done.
+!g_toy_p1_support : toy_p1 & a <- action_a.
+!g_toy_p1_support : toy_p1 & b <- action_b.
+!g_toy_p1_support : toy_p1 & c <- action_c.
""",
		encoding="utf-8",
	)
	result = {
		"sample_id": "toy_p1",
		"domain": "toy",
		"output_dir": str(case_root),
		"max_trigger_fanout": 3,
	}
	(case_root / "result.json").write_text(
		json.dumps(result),
		encoding="utf-8",
	)
	child_summary = {
		"run_id": "paper-certified_balanced",
		"results": [result],
	}
	(child_root / "summary.json").write_text(
		json.dumps(child_summary),
		encoding="utf-8",
	)
	paired_file = run_root / "paired_results.json"
	paired_file.write_text(
		json.dumps(
			{
				"run_id": "paper",
				"atomic_runs": [],
				"temporal_runs": [
					{
						"variant": "certified_balanced",
						"results": [result],
						"execution_metrics": {"maximum_trigger_fanout": 3},
					},
				],
			},
		),
		encoding="utf-8",
	)

	repair_paired_results(paired_file)
	first_repair = paired_file.read_bytes()
	repair_paired_results(paired_file)

	paired = json.loads(paired_file.read_text(encoding="utf-8"))
	child = json.loads((child_root / "summary.json").read_text(encoding="utf-8"))
	case = json.loads((case_root / "result.json").read_text(encoding="utf-8"))
	assert paired["temporal_runs"][0]["results"][0]["max_trigger_fanout"] == 2
	assert paired["temporal_runs"][0]["execution_metrics"][
		"maximum_trigger_fanout"
	] == 2
	assert child["results"][0]["max_trigger_fanout"] == 2
	assert case["max_trigger_fanout"] == 2
	assert case["trigger_fanout_scope"] == "transition_repair_controller"
	assert paired["method_source_equivalence"]["status"] == "confirmed"
	assert paired_file.read_bytes() == first_repair
