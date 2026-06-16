from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_blocksworld_first20_script_writes_reproducible_json_report(
	tmp_path: Path,
) -> None:
	output = tmp_path / "blocksworld-smoke.json"

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_blocksworld_first20_experiment.py"),
			"--output",
			str(output),
			"--train-count",
			"1",
			"--eval-count",
			"2",
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	report = json.loads(output.read_text(encoding="utf-8"))
	assert report["experiment_name"] == "blocksworld-first20"
	assert report["experiment_protocol"]["scope"] == (
		"bounded_domain_level_lifted_asl_evaluation"
	)
	assert report["experiment_protocol"]["runtime_planner"] == "none"
	assert report["experiment_protocol"]["baselines"] == []
	assert report["experiment_protocol"]["ablations"] == []
	assert report["train_problem_count"] == 1
	assert report["evaluation_problem_count"] == 2
	assert report["coverage"]["solved_count"] == 2
	assert report["coverage"]["failed_count"] == 0
	assert report["failure_analysis"]["failed_problem_count"] == 0
	assert report["failure_analysis"]["failure_reason_counts"] == {}
	assert report["failure_analysis"]["step_count_summary"]["max"] >= 0
	assert report["domain_level_contract"]["passed"] is True
	assert report["domain_level_contract"]["goal_descriptor_usage"]["read_only"] is True
	assert report["domain_level_contract"]["goal_descriptor_usage"][
		"context_descriptors"
	]
	assert report["no_synthetic_names"] is True
	assert report["generated_output_audit"]["passed"] is True
	assert report["generated_output_audit"]["no_synthetic_names"] is True
	assert report["generated_output_audit"]["no_grounded_plan_terms"] is True
	assert report["generated_output_audit"]["violation_count"] == 0
	assert report["generated_output_audit"]["violations"] == []
	assert set(report["generated_output_audit"]["checked_layers"]) >= {
		"no_initial_beliefs",
		"no_synthetic_names",
		"goal_descriptors_read_only",
		"plan_head_subset",
		"body_step_subset",
		"context_subset",
		"declared_pddl_symbols",
		"lifted_plan_heads",
		"lifted_body_calls",
		"lifted_contexts",
	}
	assert report["plan_library"]["primitive_action_call_count"] > 0
	assert report["plan_library"]["subgoal_call_count"] > 0
	assert report["plan_library"]["asl_line_count"] > 0
	assert report["learning_audit"]["layer_b_atomic_modules"][
		"atomic_action_strategy_group_count"
	] > 0
	assert report["learning_audit"]["layer_c_goal_composer"][
		"composer_candidate_count"
	] > 0
	assert report["runtime_seconds"]["synthesis"] >= 0
	assert report["runtime_seconds"]["evaluation_total"] >= 0
	assert len(report["runtime_seconds"]["evaluation_by_problem"]) == 2
	assert "+!g : goal_on" in report["asl"]
