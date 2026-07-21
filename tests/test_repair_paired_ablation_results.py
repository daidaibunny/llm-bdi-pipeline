from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.repair_paired_ablation_results import repair_paired_results
from scripts.repair_paired_ablation_results import replace_temporal_results
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
	first_repair = json.loads(paired_file.read_text(encoding="utf-8"))
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
	assert json.loads(paired_file.read_text(encoding="utf-8")) == first_repair


def test_replace_temporal_results_updates_only_the_semantic_case(
	tmp_path: Path,
) -> None:
	paired_file = tmp_path / "paired_results.json"
	failed = {
		"sample_id": "logistics_p0_24",
		"domain": "logistics",
		"profile": "same_state_with_negation",
		"goal_name": "g_logistics_p0_24",
		"temporal_compiler_variant": "certified_balanced",
		"status": "jason_failed",
		"success": False,
		"duration_seconds": 3.0,
		"controller_plan_count": 12,
		"max_trigger_fanout": 2,
	}
	sibling = {
		"sample_id": "logistics_p0_25",
		"domain": "logistics",
		"profile": "same_state_with_negation",
		"goal_name": "g_logistics_p0_25",
		"temporal_compiler_variant": "certified_balanced",
		"status": "success",
		"success": True,
		"duration_seconds": 3.0,
		"action_count": 2,
		"controller_plan_count": 13,
		"max_trigger_fanout": 2,
		"execution_validation": {
			"val_attempted": True,
			"val_success": True,
			"gold_accepted": True,
			"prediction_accepted": True,
		},
	}
	unaffected_run = {
		"variant": "dfa_aware_unprotected",
		"method": "Unprotected Serialization",
		"parameters": {"jason_timeout_seconds": 1800},
		"results": [{**sibling, "temporal_compiler_variant": "dfa_aware_unprotected"}],
		"aggregate": {"success_count": 1, "total": 1},
		"execution_metrics": {"valid_trace_count": 1},
	}
	paired = {
		"run_id": "paper",
		"timeout_seconds": 1800,
		"temporal_runs": [
			{
				"variant": "certified_balanced",
				"method": "Certified Balanced",
				"parameters": {"jason_timeout_seconds": 1800},
				"results": [failed, sibling],
				"aggregate": {"success_count": 1, "total": 2},
				"execution_metrics": {"valid_trace_count": 1},
			},
			unaffected_run,
		],
	}
	paired_file.write_text(json.dumps(paired), encoding="utf-8")
	replacement_file = tmp_path / "replacement.json"
	replacement_file.write_text(
		json.dumps(
			{
				"run_id": "final-logistics-p0-24-certified-balanced",
				"temporal_compiler_variant": "certified_balanced",
				"results": [
					{
						**failed,
						"status": "success",
						"success": True,
						"jason_status": "success",
						"duration_seconds": 1.5,
						"action_count": 1,
						"controller_plan_count": 14,
						"execution_validation": {
							"action_count": 1,
							"replay_valid": True,
							"val_attempted": True,
							"val_success": True,
							"gold_accepted": True,
							"prediction_accepted": True,
						},
					},
				],
			},
		),
		encoding="utf-8",
	)

	report = replace_temporal_results(paired_file, [replacement_file])
	updated = json.loads(paired_file.read_text(encoding="utf-8"))
	balanced = updated["temporal_runs"][0]

	assert report["replaced_case_count"] == 1
	assert balanced["results"][0]["status"] == "success"
	assert balanced["results"][0]["action_count"] == 1
	assert balanced["results"][1] == sibling
	assert balanced["aggregate"]["success_count"] == 2
	assert balanced["execution_metrics"]["valid_trace_count"] == 2
	assert balanced["execution_metrics"]["par2_seconds"] == 2.25
	assert updated["temporal_runs"][1] == unaffected_run
	assert updated["incremental_result_updates"] == [
		{
			"domain": "logistics",
			"sample_id": "logistics_p0_24",
			"source_run_id": "final-logistics-p0-24-certified-balanced",
			"status": "success",
			"variant": "certified_balanced",
		},
	]
