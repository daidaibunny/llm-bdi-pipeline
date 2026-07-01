from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from scripts.run_domain_level_experiment_matrix import _preset_config
from scripts.run_domain_level_experiment_matrix import run_experiment_matrix
from tests.domain_level_planning.resource_dependency_fixture import (
	write_resource_dependency_fixture,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SELECTED_BENCHMARK_DOMAINS = {
	"ferry",
	"gripper",
	"miconic",
	"logistics",
	"delivery",
	"spanner",
	"childsnack",
	"barman",
	"visitall",
	"blocks",
	"8puzzle-1tile",
	"sokoban-1stone",
}


def test_experiment_matrix_script_writes_success_failure_and_comparison_rows(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_negative_goal_case(tmp_path)
	config = tmp_path / "matrix.json"
	output_dir = tmp_path / "matrix-output"
	fixture = write_resource_dependency_fixture(tmp_path / "resource-dependency")
	config.write_text(
		json.dumps(
			{
				"matrix_name": "test-paper-grade-matrix",
				"experiments": [
					{
						"name": "resource-dependency-refinement-matrix",
						"domain_file": str(fixture.domain_file),
						"train_problems": [str(fixture.problems[0])],
						"eval_problems": [
							str(fixture.problems[0]),
							str(fixture.problems[1]),
						],
						"use_counterexample_refinement": True,
						"max_refinement_rounds": 1,
						"max_steps": 100,
						"max_depth": 50,
						"ablation_label": "bootstrap_counterexample_refinement",
					},
					{
						"name": "negative-goal-diagnostic",
						"domain_file": str(domain_file),
						"train_problems": [str(problem_file)],
						"eval_problems": [str(problem_file)],
						"ablation_label": "unsupported_goal_diagnostic",
					},
				],
			},
		),
		encoding="utf-8",
	)

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_domain_level_experiment_matrix.py"),
			"--config",
			str(config),
			"--output-dir",
			str(output_dir),
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	summary = json.loads((output_dir / "matrix-summary.json").read_text(encoding="utf-8"))
	comparison = json.loads((output_dir / "comparison.json").read_text(encoding="utf-8"))
	success_report = json.loads(
		(output_dir / "resource-dependency-refinement-matrix.json").read_text(
			encoding="utf-8",
		),
	)
	failure_report = json.loads(
		(output_dir / "negative-goal-diagnostic.json").read_text(encoding="utf-8"),
	)

	assert summary["matrix_name"] == "test-paper-grade-matrix"
	assert summary["experiment_count"] == 2
	assert summary["succeeded_count"] == 1
	assert summary["failed_count"] == 1
	assert summary["best_by_coverage"] == "bootstrap_counterexample_refinement"
	assert {row["status"] for row in summary["rows"]} == {"succeeded", "failed"}

	assert comparison["report_count"] == 2
	assert [row["label"] for row in comparison["rows"]] == [
		"bootstrap_counterexample_refinement",
		"unsupported_goal_diagnostic",
	]
	assert comparison["rows"][0]["coverage_ratio"] == 1.0
	assert comparison["rows"][1]["coverage_ratio"] == 0.0
	assert comparison["rows"][0]["enabled_mechanisms"] == [
		"counterexample_refinement",
		"layer_c_ordering",
	]
	assert comparison["rows"][1]["disabled_mechanisms"] == [
		"external_sketch_evidence",
		"counterexample_refinement",
		"offline_synthesis_planner_traces",
		"paper_profile_gate",
	]

	assert success_report["matrix_status"] == "succeeded"
	assert success_report["coverage"]["solved_count"] == 2
	assert success_report["refinement_analysis"]["converged"] is True
	assert success_report["experiment_protocol"]["mechanism_status"][
		"counterexample_refinement"
	] == "enabled"
	assert failure_report["matrix_status"] == "failed"
	assert failure_report["coverage"]["failed_count"] == 1
	assert failure_report["paper_quality_summary"]["blocking_failure_count"] == 1
	assert failure_report["experiment_protocol"]["ablations"][0][
		"mechanism_status"
	]["external_sketch_evidence"] == "disabled"
	assert failure_report["error"]["type"] == "ValueError"
	assert "unsupported_negative_goal" in failure_report["error"]["message"] or (
		"negative problem goals are not supported" in failure_report["error"]["message"]
	)


def test_experiment_matrix_removes_stale_generated_json(
	tmp_path: Path,
) -> None:
	fixture = write_resource_dependency_fixture(tmp_path / "resource-dependency")
	output_dir = tmp_path / "matrix-output"
	output_dir.mkdir()
	stale_report = output_dir / "old-development-probe.json"
	stale_report.write_text('{"stale": true}', encoding="utf-8")

	summary = run_experiment_matrix(
		config={
			"matrix_name": "stale-cleanup-matrix",
			"experiments": [
				{
					"name": "resource-dependency-refinement-matrix",
					"domain_file": str(fixture.domain_file),
					"train_problems": [str(fixture.problems[0])],
					"eval_problems": [str(fixture.problems[0])],
					"max_steps": 100,
					"max_depth": 50,
				},
			],
		},
		config_base=PROJECT_ROOT,
		output_dir=output_dir,
		continue_on_error=True,
	)

	assert summary["succeeded_count"] == 1
	assert not stale_report.exists()
	assert (output_dir / "resource-dependency-refinement-matrix.json").exists()
	assert (output_dir / "comparison.json").exists()
	assert (output_dir / "matrix-summary.json").exists()


def test_experiment_matrix_cleanup_preserves_config_file(
	tmp_path: Path,
) -> None:
	fixture = write_resource_dependency_fixture(tmp_path / "resource-dependency")
	output_dir = tmp_path / "matrix-output"
	output_dir.mkdir()
	config_file = output_dir / "config.json"
	config_file.write_text(
		json.dumps(
			{
				"matrix_name": "preserve-config-matrix",
				"experiments": [
					{
						"name": "resource-dependency-preserve-config",
						"domain_file": str(fixture.domain_file),
						"train_problems": [str(fixture.problems[0])],
						"eval_problems": [str(fixture.problems[0])],
						"max_steps": 100,
						"max_depth": 50,
					},
				],
			},
			indent=2,
		),
		encoding="utf-8",
	)
	stale_report = output_dir / "stale-report.json"
	stale_report.write_text('{"stale": true}', encoding="utf-8")

	summary = run_experiment_matrix(
		config=json.loads(config_file.read_text(encoding="utf-8")),
		config_base=PROJECT_ROOT,
		output_dir=output_dir,
		continue_on_error=True,
		preserve_files=(config_file,),
	)

	assert summary["succeeded_count"] == 1
	assert config_file.exists()
	assert not stale_report.exists()


def test_experiment_matrix_script_fail_fast_exits_on_first_error(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_negative_goal_case(tmp_path)
	config = tmp_path / "matrix.json"
	output_dir = tmp_path / "matrix-output"
	config.write_text(
		json.dumps(
			{
				"matrix_name": "test-fail-fast",
				"experiments": [
					{
						"name": "negative-goal-diagnostic",
						"domain_file": str(domain_file),
						"train_problems": [str(problem_file)],
						"eval_problems": [str(problem_file)],
					},
				],
			},
		),
		encoding="utf-8",
	)

	result = subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_domain_level_experiment_matrix.py"),
			"--config",
			str(config),
			"--output-dir",
			str(output_dir),
			"--fail-fast",
		),
		cwd=PROJECT_ROOT,
		check=False,
		capture_output=True,
		text=True,
	)

	assert result.returncode != 0
	assert "negative problem goals are not supported" in result.stderr
	assert not (output_dir / "matrix-summary.json").exists()


def test_paper_expanded_smoke_preset_covers_available_pddl_domains() -> None:
	config = _preset_config("paper-expanded-smoke")
	experiments = tuple(config["experiments"])
	experiment_names = {str(item["name"]) for item in experiments}
	domain_files = {str(item["domain_file"]) for item in experiments}

	assert config["matrix_name"] == "paper-expanded-smoke"
	assert domain_files == {
		f"src/domains/{domain_id}/domain.pddl"
		for domain_id in SELECTED_BENCHMARK_DOMAINS
	}
	assert experiment_names == {
		f"{domain_id}-ipc-full-smoke"
		for domain_id in SELECTED_BENCHMARK_DOMAINS
	}
	assert all("achieve" not in name for name in experiment_names)

	expanded_rows = {
		str(item["name"]): item for item in experiments
	}
	for domain_id in SELECTED_BENCHMARK_DOMAINS:
		row = expanded_rows[f"{domain_id}-ipc-full-smoke"]
		assert row["domain_file"] == f"src/domains/{domain_id}/domain.pddl"
		assert row["train_base"] == f"src/domains/{domain_id}/train"
		assert row["eval_base"] == f"src/domains/{domain_id}/test"
		assert row["train_glob"] == "*.pddl"
		assert row["eval_glob"] == "*.pddl"
		assert row["domain_id"] == domain_id
		assert row["benchmark_class_id"]
		assert row["synthesis_profile"] == "bootstrap"
		assert row["ablation_label"] == f"{domain_id}_ipc_full_smoke"


def test_experiment_matrix_writes_diagnostic_row_when_entry_times_out(
	tmp_path: Path,
	monkeypatch,
) -> None:
	fixture = write_resource_dependency_fixture(tmp_path / "resource-dependency")
	output_dir = tmp_path / "matrix-output"
	config = {
		"matrix_name": "timeout-matrix",
		"experiments": [
			{
				"name": "slow-entry",
				"domain_file": str(fixture.domain_file),
				"train_problems": [str(fixture.problems[0])],
				"eval_problems": [str(fixture.problems[0])],
				"timeout_seconds": 0.01,
			},
		],
	}

	def slow_entry(*args, **kwargs):
		time.sleep(1)
		return {}

	monkeypatch.setattr(
		"scripts.run_domain_level_experiment_matrix._run_matrix_entry",
		slow_entry,
	)

	summary = run_experiment_matrix(
		config=config,
		config_base=PROJECT_ROOT,
		output_dir=output_dir,
		continue_on_error=True,
	)
	report = json.loads((output_dir / "slow-entry.json").read_text(encoding="utf-8"))

	assert summary["failed_count"] == 1
	assert report["matrix_status"] == "failed"
	assert report["error"]["type"] == "TimeoutError"
	assert "timeout_seconds=0.01" in report["error"]["message"]


def _write_negative_goal_case(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain negative-goal-mini)
		 (:requirements :strips)
		 (:predicates (done ?x))
		 (:action finish
		  :parameters (?x)
		  :precondition (and)
		  :effect (done ?x))
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem negative-goal-p1)
		 (:domain negative-goal-mini)
		 (:objects a)
		 (:init (done a))
		 (:goal (and (not (done a))))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
