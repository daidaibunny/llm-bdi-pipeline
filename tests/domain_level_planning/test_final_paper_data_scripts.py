from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace

from low_level_planning.models import LowLevelAction
from scripts import generate_domain_level_baselines
from scripts.generate_domain_level_baselines import generate_classical_planner_baseline
from scripts.generate_domain_level_baselines import generate_moose_status_baseline
from scripts.run_final_paper_data import write_final_paper_configs


def test_moose_status_baseline_imports_completed_reproduction_rows(
	tmp_path: Path,
) -> None:
	status_file = tmp_path / "status.csv"
	with status_file.open("w", encoding="utf-8", newline="") as handle:
		writer = csv.DictWriter(handle, fieldnames=("seed", "problem", "status"))
		writer.writeheader()
		writer.writerow({"seed": "0", "problem": "p01", "status": "ok"})
		writer.writerow({"seed": "0", "problem": "p02", "status": "fail"})

	record = generate_moose_status_baseline(
		label="blocksworld_moose_probe",
		status_file=status_file,
	)

	assert record["label"] == "blocksworld_moose_probe"
	assert record["solver_family"] == "moose_generalized_planner"
	assert record["domain_level_artifact"] is True
	assert record["comparison_scope"] == "generalized_planning_reproduction"
	assert record["solved_count"] == 1
	assert record["failed_count"] == 1
	assert record["coverage_ratio"] == 0.5
	assert record["validation"]["row_count"] == 2


def test_classical_baseline_accepts_locally_valid_plan_after_planner_exit_warning(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain warning-plan)
		 (:requirements :strips)
		 (:predicates (ready ?x) (done ?x))
		 (:action finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem warning-plan-p1)
		 (:domain warning-plan)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)

	class FakePlanner:
		def __init__(self, _config):
			pass

		def solve_transition_goal(self, **_kwargs):
			return SimpleNamespace(
				success=False,
				actions=(LowLevelAction("finish", ("a",)),),
				plan_file=str(tmp_path / "warning.plan"),
				error="Fast Downward failed with exit code 36.",
			)

	monkeypatch.setattr(generate_domain_level_baselines, "FastDownwardPlanner", FakePlanner)

	record = generate_classical_planner_baseline(
		domain_file=domain_file,
		problem_files=(problem_file,),
		planner_executable="fake-fast-downward",
		timeout_seconds=1,
		work_dir=tmp_path / "work",
	)
	result = record["validation"]["problem_results"][0]

	assert record["solved_count"] == 1
	assert record["failed_count"] == 0
	assert result["validation"] == "strips_simulator_valid"
	assert result["planner_error"] == "Fast Downward failed with exit code 36."


def test_final_paper_config_splits_main_ablation_and_limitations(
	tmp_path: Path,
) -> None:
	configs = write_final_paper_configs(tmp_path / "paper-final")

	main = json.loads(configs["main"].read_text(encoding="utf-8"))
	ablation = json.loads(configs["ablation"].read_text(encoding="utf-8"))
	limitation = json.loads(configs["limitation"].read_text(encoding="utf-8"))

	assert main["matrix_name"] == "paper-final-main-library"
	assert ablation["matrix_name"] == "paper-final-ablations"
	assert limitation["matrix_name"] == "paper-final-limitations"

	main_rows = {row["name"]: row for row in main["experiments"]}
	assert "blocksworld-paper-external-on2-first20" in main_rows
	assert "blocksworld-paper-external-on2-satisfiable-large" in main_rows
	assert "blocksworld-paper-external-on2-satisfiable-mixed-large" in main_rows
	assert "labworkflow-counterexample-refinement-final" in main_rows
	assert main_rows["blocksworld-paper-external-on2-first20"]["synthesis_profile"] == (
		"paper"
	)
	assert main_rows["blocksworld-paper-external-on2-first20"]["baseline_json"]
	assert main_rows["blocksworld-paper-external-on2-first20"][
		"external_sketch_policies"
	] == [
		(
			"blocks_4_on_2=.external/gp-backends/learner-sketches/learning/"
			"workspace-2024-09-24-tractable/blocks_4_on_2/output/"
			"sketch_minimized_2.txt"
		),
	]

	ablation_names = {row["name"] for row in ablation["experiments"]}
	assert "blocksworld-no-external-sketch-first20" in ablation_names
	assert "labworkflow-no-layer-c-no-refinement" in ablation_names
	assert "labworkflow-no-counterexample-refinement" in ablation_names
	assert "transport-no-offline-trace-evidence-first10" in ablation_names

	limitation_names = {row["name"] for row in limitation["experiments"]}
	assert "transport-bootstrap-train3-first10-limitation" in limitation_names
	assert "marsrover-trace-evidence-train1-first10" in limitation_names
	marsrover_row = next(
		row
		for row in limitation["experiments"]
		if row["name"] == "marsrover-trace-evidence-train1-first10"
	)
	assert marsrover_row["train_count"] == 1
	assert marsrover_row["evaluation_timeout_seconds"] == 15
	assert marsrover_row["use_synthesis_planner_traces"] is True
	assert marsrover_row["ablation_label"] == "marsrover_trace_evidence_fragment"
