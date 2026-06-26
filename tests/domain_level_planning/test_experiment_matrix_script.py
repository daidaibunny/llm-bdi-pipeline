from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from scripts.run_domain_level_experiment_matrix import _preset_config
from scripts.run_domain_level_experiment_matrix import run_experiment_matrix


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_experiment_matrix_script_writes_success_failure_and_comparison_rows(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_negative_goal_case(tmp_path)
	config = tmp_path / "matrix.json"
	output_dir = tmp_path / "matrix-output"
	lab_root = PROJECT_ROOT / "src" / "domains" / "labworkflow"
	config.write_text(
		json.dumps(
			{
				"matrix_name": "test-paper-grade-matrix",
				"experiments": [
					{
						"name": "labworkflow-refinement-matrix",
						"domain_file": str(lab_root / "domain.pddl"),
						"train_problems": [str(lab_root / "problems" / "p01.pddl")],
						"eval_problems": [
							str(lab_root / "problems" / "p01.pddl"),
							str(lab_root / "problems" / "p02.pddl"),
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
		(output_dir / "labworkflow-refinement-matrix.json").read_text(encoding="utf-8"),
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

	assert success_report["matrix_status"] == "succeeded"
	assert success_report["coverage"]["solved_count"] == 2
	assert success_report["refinement_analysis"]["converged"] is True
	assert failure_report["matrix_status"] == "failed"
	assert failure_report["coverage"]["failed_count"] == 1
	assert failure_report["paper_quality_summary"]["blocking_failure_count"] == 1
	assert failure_report["error"]["type"] == "ValueError"
	assert "unsupported_negative_goal" in failure_report["error"]["message"] or (
		"negative problem goals are not supported" in failure_report["error"]["message"]
	)


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
	assert {
		"src/domains/blocksworld/domain.pddl",
		"src/domains/labworkflow/domain.pddl",
		"src/domains/transport/domain.pddl",
		"src/domains/satellite/domain.pddl",
		"src/domains/marsrover/domain.pddl",
	}.issubset(domain_files)
	assert "blocksworld-paper-external-on2" in experiment_names
	assert "blocksworld-bootstrap-train1-all30" in experiment_names
	assert "blocksworld-paper-external-on2-all30" in experiment_names
	assert "transport-bootstrap-train3-first10" in experiment_names
	assert "satellite-bootstrap-train3-first10" in experiment_names
	assert "marsrover-bootstrap-train3-first10" in experiment_names
	assert all("achieve" not in name for name in experiment_names)

	expanded_rows = {
		str(item["name"]): item for item in experiments
	}
	assert expanded_rows["blocksworld-bootstrap-train1-all30"]["train_count"] == 1
	assert expanded_rows["blocksworld-bootstrap-train1-all30"]["eval_count"] == 30
	assert expanded_rows["blocksworld-paper-external-on2-all30"]["eval_count"] == 30
	assert (
		expanded_rows["blocksworld-paper-external-on2-all30"]["synthesis_profile"]
		== "paper"
	)
	assert (
		expanded_rows["blocksworld-paper-external-on2-all30"][
			"evaluation_timeout_seconds"
		]
		== 30
	)
	assert expanded_rows["blocksworld-paper-external-on2-all30"]["timeout_seconds"] == 900
	assert expanded_rows["transport-bootstrap-train3-first10"]["eval_count"] == 10
	assert expanded_rows["satellite-bootstrap-train3-first10"]["eval_count"] == 10
	assert expanded_rows["marsrover-bootstrap-train3-first10"]["eval_count"] == 10


def test_experiment_matrix_writes_diagnostic_row_when_entry_times_out(
	tmp_path: Path,
	monkeypatch,
) -> None:
	lab_root = PROJECT_ROOT / "src" / "domains" / "labworkflow"
	output_dir = tmp_path / "matrix-output"
	config = {
		"matrix_name": "timeout-matrix",
		"experiments": [
			{
				"name": "slow-entry",
				"domain_file": str(lab_root / "domain.pddl"),
				"train_problems": [str(lab_root / "problems" / "p01.pddl")],
				"eval_problems": [str(lab_root / "problems" / "p01.pddl")],
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
