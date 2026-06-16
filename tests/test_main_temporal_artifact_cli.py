from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_builds_domain_level_temporal_artifact(tmp_path: Path) -> None:
	domain_file, problem_file = _write_tiny_domain_and_problem(tmp_path)
	query_dataset = _write_query_dataset(tmp_path)
	output_root = tmp_path / "artifact"

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"build-temporal-domain-artifact",
			"--domain-file",
			str(domain_file),
			"--training-problem",
			str(problem_file),
			"--query-dataset",
			str(query_dataset),
			"--query-domain",
			"tiny",
			"--query-id",
			"query_1",
			"--output-root",
			str(output_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)

	assert result["success"] is True
	assert Path(result["artifact_paths"]["plan_library_asl"]).exists()
	assert Path(result["artifact_paths"]["dfa_progress_requests"]).exists()
	requests = json.loads(
		Path(result["artifact_paths"]["dfa_progress_requests"]).read_text(
			encoding="utf-8",
		),
	)
	asl = Path(result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")

	assert requests["query_1"][0]["goal_facts"] == ["goal_done"]
	assert "transition_" not in asl
	assert "achieve_" not in asl
	assert "dfa_state" not in asl


def _write_tiny_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (and (not (ready)) (done))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem tiny-p1)
		 (:domain tiny)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_query_dataset(tmp_path: Path) -> Path:
	query_dataset = tmp_path / "queries_LTLf.json"
	query_dataset.write_text(
		json.dumps(
			{
				"domains": {
					"tiny": {
						"cases": {
							"query_1": {
								"instruction": "Eventually finish.",
								"problem_file": "problem.pddl",
								"ltlf_formula": "F(done)",
							},
						},
					},
				},
			},
		),
		encoding="utf-8",
	)
	return query_dataset
