from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

from low_level_planning.models import LowLevelAction
from scripts import generate_domain_level_baselines
from scripts import run_final_paper_data as final_paper_data
from scripts.generate_domain_level_baselines import generate_classical_planner_baseline
from scripts.generate_domain_level_baselines import generate_moose_status_baseline
from scripts.run_final_paper_data import load_final_paper_manifest
from scripts.run_final_paper_data import validate_final_paper_package
from scripts.run_final_paper_data import write_final_paper_configs
from domain_level_planning import architecture_gap_summary
from domain_level_planning import domain_level_architecture_contract
from domain_level_planning.benchmark_registry import load_achievement_benchmark_registry
from domain_level_planning.experiments import format_comparison_latex_macros


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SELECTED_BENCHMARK_DOMAINS = {
	"ferry",
	"gripper",
	"miconic",
	"logistics",
	"blocks",
	"8puzzle-1tile",
}
EXPECTED_BENCHMARK_SOURCE_NAMES = {
	"potassco/pddl-instances",
	"DillonZChen/moose-dataset",
	"bonetblai/learner-policies-from-examples",
}


def _minimal_artifact_manifest(
	*,
	report_count: int,
	baseline_count: int,
	paper_table_row_count: int,
) -> dict[str, object]:
	return {
		"artifact_id": "unit-test-artifact",
		"schema_version": 1,
		"commands": {
			"generate": "generate",
			"validate": "validate",
			"tests": "tests",
			"paper": "paper",
		},
		"resource_policy": {
			"external_generalized_planning_memory_limit_gib": 16,
			"external_generalized_planning_requires_resource_guard": True,
			"library_runtime_full_trace_planner": False,
		},
		"external_setup": {
			"commands": {
				"backend_status": "status",
				"learner_sketches_commands": "commands",
				"learner_sketches_summary": "summary",
			},
			"resource_guarded_command_generators": [
				"uv run python scripts/resource_guard.py ...",
			],
			"pinned_repositories": [],
		},
		"expected_package": {
			"report_count": report_count,
			"baseline_count": baseline_count,
			"paper_table_row_count": paper_table_row_count,
		},
		"expected_library_rows": [
			{
				"label": "resource_dependency_counterexample_refinement_stress",
				"solved": "5/5",
				"coverage_percent": 100.0,
				"runtime_planner": "none",
			},
			{
				"label": "no_layer_c_with_refinement_resource_dependency_stress",
				"solved": "0/5",
				"coverage_percent": 0.0,
				"runtime_planner": "none",
			},
			{
				"label": "no_counterexample_refinement_resource_dependency_stress",
				"solved": "0/5",
				"coverage_percent": 0.0,
				"runtime_planner": "none",
			},
		],
		"expected_baseline_rows": [
			{
				"macro_id": "blocks_train_fast_downward_lama_per_problem",
				"solved": "2/2",
				"runtime_planner": "offline_baseline_only",
			},
			{
				"macro_id": "blocks_external_policy_audit",
				"solved": "0/2",
				"runtime_planner": "not_runtime_executed",
			},
		],
	}


def _write_artifact_manifest_copy(output_dir: Path, manifest: dict[str, object]) -> None:
	(output_dir / "artifact-manifest.json").write_text(
		json.dumps(manifest, indent=2, sort_keys=True),
		encoding="utf-8",
	)


def _write_minimal_validated_package(
	output_dir: Path,
	manifest: dict[str, object],
) -> Path:
	comparison = {
		"report_count": 2,
		"baseline_count": 2,
		"paper_table_rows": [
			{
				"row_type": "library",
				"label": "paper_external_sketch_blocks_train",
				"macro_id": "paper_external_sketch_blocks_train",
				"solved": "2/2",
				"coverage_percent": 100.0,
				"runtime_planner": "none",
				"paper_profile_ready": True,
				"plan_count": 4,
				"mechanism_summary": "enabled: external_sketch_evidence",
			},
			{
				"row_type": "library",
				"label": "resource_dependency_counterexample_refinement_stress",
				"macro_id": "resource_dependency_counterexample_refinement_stress",
				"solved": "5/5",
				"coverage_percent": 100.0,
				"runtime_planner": "none",
				"paper_profile_ready": False,
				"plan_count": 4,
				"mechanism_summary": "enabled: counterexample_refinement",
			},
			{
				"row_type": "library",
				"label": "no_layer_c_with_refinement_resource_dependency_stress",
				"macro_id": "no_layer_c_with_refinement_resource_dependency_stress",
				"solved": "0/5",
				"coverage_percent": 0.0,
				"runtime_planner": "none",
				"paper_profile_ready": False,
				"plan_count": 3,
				"mechanism_summary": "disabled: layer_c_ordering",
			},
			{
				"row_type": "library",
				"label": "no_counterexample_refinement_resource_dependency_stress",
				"macro_id": "no_counterexample_refinement_resource_dependency_stress",
				"solved": "0/5",
				"coverage_percent": 0.0,
				"runtime_planner": "none",
				"paper_profile_ready": False,
				"plan_count": 3,
				"mechanism_summary": "disabled: counterexample_refinement",
			},
			{
				"row_type": "baseline",
				"label": "fast_downward_lama_per_problem",
				"macro_id": "blocks_train_fast_downward_lama_per_problem",
				"solved": "2/2",
				"coverage_percent": 100.0,
				"runtime_planner": "offline_baseline_only",
				"plan_count": None,
				"notes": "per_problem_trace_baseline; not a domain-level library",
				"mechanism_summary": "baseline",
			},
			{
				"row_type": "baseline",
				"label": "raw_external_policy_audit",
				"macro_id": "blocks_external_policy_audit",
				"solved": "0/2",
				"coverage_percent": 0.0,
				"runtime_planner": "not_runtime_executed",
				"plan_count": None,
				"notes": "domain-level artifact audit",
				"mechanism_summary": "baseline",
			},
		],
	}
	(output_dir / "comparison.json").write_text(
		json.dumps(comparison, indent=2),
		encoding="utf-8",
	)
	_write_artifact_manifest_copy(output_dir, manifest)
	current_gap_summary = architecture_gap_summary(
		domain_level_architecture_contract().gaps,
	)
	for name in ("main", "ablation", "limitation"):
		summary_dir = output_dir / f"{name}-matrix"
		summary_dir.mkdir(parents=True)
		report_file = summary_dir / f"{name}-report.json"
		report_file.write_text(
			json.dumps(
				{
					"coverage": {"solved_count": 1, "failed_count": 0},
					"generated_output_audit": {"passed": True},
					"synthesis_report": {
						"architecture_gap_summary": current_gap_summary,
					},
				},
				indent=2,
			),
			encoding="utf-8",
		)
		(summary_dir / "matrix-summary.json").write_text(
			json.dumps(
				{
					"matrix_name": f"paper-final-{name}",
					"experiment_count": 1,
					"succeeded_count": 1,
					"failed_count": 0,
					"rows": [
						{
							"experiment_name": f"{name}-report",
							"report_file": str(report_file),
							"status": "succeeded",
						},
					],
				},
			),
			encoding="utf-8",
		)
	macro_file = output_dir / "results.tex"
	macro_file.write_text(
		format_comparison_latex_macros(comparison),
		encoding="utf-8",
	)
	return macro_file


def _write_latex_main_with_embedded_macros(
	tmp_path: Path,
	macro_file: Path,
	monkeypatch,
) -> None:
	macro_block = macro_file.read_text(encoding="utf-8").rstrip()
	main_file = tmp_path / "main.tex"
	main_file.write_text(
		"\n".join(
			(
				final_paper_data.RESULT_MACRO_START,
				macro_block,
				final_paper_data.RESULT_MACRO_END,
				"",
			),
		),
		encoding="utf-8",
	)
	monkeypatch.setattr(final_paper_data, "FINAL_PAPER_MAIN", main_file)


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


def test_domain_support_taxonomy_is_complete_and_manifested() -> None:
	taxonomy_path = PROJECT_ROOT / "paper_artifacts/domain_support_taxonomy.json"
	taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
	manifest = load_final_paper_manifest()

	assert taxonomy["schema_version"] == 3
	assert taxonomy["scope"] == (
		"achievement_goal_atomic_templates_with_temporal_extended_goal_wrappers"
	)
	assert "does not claim a new universal generalized planner" in taxonomy["claim_statement"]
	assert "singleton literals" in taxonomy["claim_statement"]
	assert "potassco/pddl-instances" in taxonomy["selection_principle"]
	assert "moose-dataset" in taxonomy["selection_principle"]
	assert "learner-policies-from-examples" in taxonomy["selection_principle"]
	assert "floor(2/3 * N)" in taxonomy["selection_principle"]
	assert taxonomy["paper_core_domains"] == [
		"blocks",
		"8puzzle-1tile",
	]
	assert taxonomy["domain_count_assessment"][
		"current_strict_main_standard_domain_count"
	] == 6
	assert taxonomy["domain_count_assessment"][
		"revision_needed_for_broad_gp_claim"
	] is False
	assert taxonomy["domain_count_assessment"]["broad_universal_gp_claim"] is False
	assert taxonomy["selected_goal_property_group_count"] == 3
	assert taxonomy["selected_goal_specification_layer_count"] == 2
	assert set(taxonomy["selected_standard_domain_targets"]) == SELECTED_BENCHMARK_DOMAINS
	assert taxonomy["benchmark_source"]["name"] == (
		"selected reputable generalized-planning benchmark sources"
	)
	assert set(
		record["name"]
		for record in taxonomy["benchmark_sources"]
	) == EXPECTED_BENCHMARK_SOURCE_NAMES
	goal_layers = {
		layer["id"]: layer
		for layer in taxonomy["goal_specification_layers"]
	}
	assert set(goal_layers) == {
		"achievement_goal_layer",
		"temporal_extended_goal_layer",
	}
	assert goal_layers["achievement_goal_layer"]["status"] == (
		"current_primary_scope"
	)
	assert "PDDL problem goals" in goal_layers["achievement_goal_layer"][
		"pddl_relation"
	]
	assert goal_layers["temporal_extended_goal_layer"]["status"] == "query_specific_scope"
	assert "not a domain class" in goal_layers[
		"temporal_extended_goal_layer"
	]["paper_use"]

	literature = taxonomy["literature"]
	assert literature
	manifest_inputs = {
		str(record["path"])
		for record in manifest["required_repository_inputs"]
		if bool(record.get("tracked"))
	}
	assert str(taxonomy_path.relative_to(PROJECT_ROOT)) in manifest_inputs

	for key, record in literature.items():
		assert key
		assert record["title"]
		assert record["url"].startswith("https://")
		local_pdf = PROJECT_ROOT / record["local_pdf"]
		assert local_pdf.is_file()
		assert local_pdf.read_bytes().startswith(b"%PDF-")
		assert str(local_pdf.relative_to(PROJECT_ROOT)) in manifest_inputs

	property_ids = set()
	for formal_property in taxonomy["formal_properties"]:
		property_ids.add(formal_property["id"])
		assert formal_property["name"]
		assert formal_property["definition"]
		assert formal_property["paper_use"]
		assert formal_property["literature_basis"]
		for literature_key in formal_property["literature_basis"]:
			assert literature_key in literature

	assert {
		"multi_object_template_composition",
		"safe_asl_compilability",
		"singleton_goal_regression_suitability",
		"structural_temporalization_need",
	} <= property_ids

	prior_practice = taxonomy["prior_benchmark_practice"]
	assert len(prior_practice) >= 5
	practice_by_id = {record["id"]: record for record in prior_practice}
	assert practice_by_id["moose_goal_regression"]["evaluated_domain_count"][
		"main_classical_domains"
	] == 8
	assert practice_by_id["moose_goal_regression"]["evaluated_domain_count"][
		"ipc_property_probe_domains"
	] == 38
	assert practice_by_id["learning_sketches_bounded_width"][
		"evaluated_domain_count"
	]["learning_domains"] == 9
	assert practice_by_id["d2l_feature_definable_policies"][
		"evaluated_domain_count"
	]["problem_classes"] == 9
	assert practice_by_id["pg3_lifted_decision_lists"]["evaluated_domain_count"][
		"domains"
	] == 6
	assert practice_by_id["bfgp_program_synthesis"]["evaluated_domain_count"][
		"domains"
	] == 13
	for record in prior_practice:
		assert record["property_axis"]
		assert record["domains"]
		assert record["selection_style"]
		assert record["implication_for_this_paper"]
		for literature_key in record["literature_basis"]:
			assert literature_key in literature

	support_levels = {
		"main_claim",
		"planned_claim_target",
	}
	group_ids = set()
	target_domains = set()
	for goal_property_group in taxonomy["goal_property_groups"]:
		group_ids.add(goal_property_group["id"])
		assert goal_property_group["name"]
		assert goal_property_group["formal_membership"]
		assert goal_property_group["prior_property_basis"]
		assert goal_property_group["domain_examples"]
		assert goal_property_group["target_paper_domains"]
		assert goal_property_group["paper_role"]
		assert goal_property_group["current_evidence"]
		assert goal_property_group["support_level"] in support_levels
		assert goal_property_group["backend_route"].startswith("not_by_group")
		target_domains.update(goal_property_group["target_paper_domains"])
		for property_key in goal_property_group["prior_property_basis"]:
			assert property_key in property_ids

	assert {
		"singleton_regression_friendly_classical_goals",
		"multi_object_classical_achievement_goals",
		"structural_temporalized_achievement_goals",
	} == group_ids
	assert SELECTED_BENCHMARK_DOMAINS <= target_domains

	groups_by_id = {
		goal_property_group["id"]: goal_property_group
		for goal_property_group in taxonomy["goal_property_groups"]
	}
	assert groups_by_id[
		"structural_temporalized_achievement_goals"
	]["support_level"] == "main_claim"
	assert groups_by_id[
		"structural_temporalized_achievement_goals"
	]["target_paper_domains"] == [
		"blocks",
		"8puzzle-1tile",
	]
	assert groups_by_id[
		"singleton_regression_friendly_classical_goals"
	]["target_paper_domains"] == ["ferry", "miconic"]
	assert groups_by_id[
		"multi_object_classical_achievement_goals"
	]["target_paper_domains"] == ["gripper", "logistics"]

	boundary_records = {
		record["id"]: record
		for record in taxonomy["excluded_or_boundary_domains"]
	}
	assert "transport" in boundary_records["route_or_resource_boundary"]["domains"]
	assert "depots" in boundary_records["route_or_resource_boundary"]["domains"]
	assert boundary_records["route_or_resource_boundary"]["current_project_domains"] == []
	assert "numeric transport" in boundary_records["numeric_goal_boundary"][
		"domains"
	]

	evaluation_policy = taxonomy["evaluation_policy"]
	assert (
		"without runtime full-trace planning"
	) in evaluation_policy["main_claim_requires"]
	assert any(
		"Raw external GP policies" in item
		for item in evaluation_policy["not_counted_as_main_claim"]
	)


def test_achievement_benchmark_registry_matches_selected_domain_taxonomy() -> None:
	taxonomy = json.loads(
		(PROJECT_ROOT / "paper_artifacts/domain_support_taxonomy.json").read_text(
			encoding="utf-8",
		),
	)
	manifest = load_final_paper_manifest()
	registry = load_achievement_benchmark_registry()

	assert registry.control["goal_specification_layer"] == "achievement_goal_layer"
	assert registry.control["future_goal_specification_layers"] == [
		"temporal_extended_goal_layer",
	]
	assert len(registry.selected_records()) == 6
	assert {
		record.domain_id for record in registry.selected_records()
	} == set(taxonomy["selected_standard_domain_targets"])
	assert registry.control["benchmark_source"]["name"] == (
		"selected reputable generalized-planning benchmark sources"
	)
	assert set(
		record["name"]
		for record in registry.control["benchmark_sources"]
	) == EXPECTED_BENCHMARK_SOURCE_NAMES

	group_to_domains: dict[str, set[str]] = {}
	for record in registry.selected_records():
		group_to_domains.setdefault(record.goal_property_group_id, set()).add(record.domain_id)
	assert group_to_domains == {
			"singleton_regression_friendly_classical_goals": {
				"ferry",
				"miconic",
			},
			"multi_object_classical_achievement_goals": {
				"gripper",
				"logistics",
			},
			"structural_temporalized_achievement_goals": {
				"blocks",
				"8puzzle-1tile",
			},
		}

	assert all(
		str(record.payload["goal_specification_layer"]) == "achievement_goal_layer"
		for record in registry.records
	)
	for record in registry.selected_records():
		domain_root = PROJECT_ROOT / "src" / "domains" / record.domain_id
		assert (domain_root / "domain.pddl").is_file()
		source_snapshot = json.loads(
			(domain_root / "source.json").read_text(encoding="utf-8"),
		)
		assert len(tuple((domain_root / "train").glob("*.pddl"))) == source_snapshot[
			"train_count"
		]
		assert len(tuple((domain_root / "test").glob("*.pddl"))) == source_snapshot[
			"test_count"
		]
		assert source_snapshot["train_count"] == int(source_snapshot["instance_count"] * (2 / 3))
		assert source_snapshot["test_count"] == (
			source_snapshot["instance_count"] - source_snapshot["train_count"]
		)
		assert record.payload["source"]["name"] in EXPECTED_BENCHMARK_SOURCE_NAMES
		assert record.payload["source"]["url"].startswith("https://")
		assert record.payload["source"]["commit"]
		assert source_snapshot["source"] == record.payload["source"]["name"]
		assert source_snapshot["source_url"] == record.payload["source"]["url"]
		assert source_snapshot["source_commit"] == record.payload["source"]["commit"]

	manifest_inputs = {
		str(record["path"])
		for record in manifest["required_repository_inputs"]
		if bool(record.get("tracked"))
	}
	assert "src/domain_level_planning/benchmark_registry.py" in manifest_inputs
	assert "src/benchmark_registry/achievement_goals" in manifest_inputs


def test_final_paper_config_splits_main_ablation_and_limitations(
	tmp_path: Path,
) -> None:
	manifest = load_final_paper_manifest()
	output_dir = tmp_path / "paper-final"
	configs = write_final_paper_configs(output_dir, manifest=manifest)

	main = json.loads(configs["main"].read_text(encoding="utf-8"))
	ablation = json.loads(configs["ablation"].read_text(encoding="utf-8"))
	limitation = json.loads(configs["limitation"].read_text(encoding="utf-8"))

	assert main["matrix_name"] == "paper-final-main-library"
	assert ablation["matrix_name"] == "paper-final-ablations"
	assert limitation["matrix_name"] == "paper-final-limitations"
	assert json.loads(
		(output_dir / "artifact-manifest.json").read_text(encoding="utf-8"),
	) == manifest

	main_experiments = tuple(main["experiments"])
	assert {str(item["name"]) for item in main_experiments} == {
		f"{domain_id}-ipc-full-main"
		for domain_id in SELECTED_BENCHMARK_DOMAINS
	}
	assert {
		str(item["domain_file"])
		for item in main_experiments
	} == {
		f"src/domains/{domain_id}/domain.pddl"
		for domain_id in SELECTED_BENCHMARK_DOMAINS
	}
	for experiment in main_experiments:
		domain_id = str(experiment["name"]).removesuffix("-ipc-full-main")
		assert experiment["train_base"] == f"src/domains/{domain_id}/train"
		assert experiment["eval_base"] == f"src/domains/{domain_id}/test"
		assert experiment["train_glob"] == "*.pddl"
		assert experiment["eval_glob"] == "*.pddl"
		assert experiment["synthesis_profile"] == "bootstrap"
		assert experiment["use_synthesis_planner_traces"] is True
		assert experiment["synthesis_planner_executable"] == "fast-downward/fast-downward.py"
		assert experiment["synthesis_planner_timeout_seconds"] == 60
	assert ablation["experiments"] == []
	assert limitation["experiments"] == []


def test_final_paper_package_validator_accepts_complete_package(
	tmp_path: Path,
	monkeypatch,
) -> None:
	manifest = _minimal_artifact_manifest(
		report_count=2,
		baseline_count=2,
		paper_table_row_count=6,
	)
	macro_file = _write_minimal_validated_package(tmp_path, manifest)
	_write_latex_main_with_embedded_macros(tmp_path, macro_file, monkeypatch)

	validation = validate_final_paper_package(
		tmp_path,
		macro_file=macro_file,
		manifest=manifest,
	)

	assert validation["check_count"] >= 16
	assert validation["comparison_file"] == str(tmp_path / "comparison.json")


def test_final_paper_package_validator_rejects_external_pin_mismatch(
	tmp_path: Path,
) -> None:
	manifest = _minimal_artifact_manifest(
		report_count=2,
		baseline_count=2,
		paper_table_row_count=6,
	)
	pinned_repo = tmp_path / "pinned-backend"
	pinned_repo.mkdir()
	subprocess.run(("git", "init"), cwd=pinned_repo, check=True, stdout=subprocess.DEVNULL)
	subprocess.run(
		("git", "config", "user.email", "test@example.org"),
		cwd=pinned_repo,
		check=True,
	)
	subprocess.run(
		("git", "config", "user.name", "Test User"),
		cwd=pinned_repo,
		check=True,
	)
	(pinned_repo / "README").write_text("backend\n", encoding="utf-8")
	subprocess.run(("git", "add", "README"), cwd=pinned_repo, check=True)
	subprocess.run(
		("git", "commit", "-m", "init"),
		cwd=pinned_repo,
		check=True,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
	)
	manifest["external_setup"]["pinned_repositories"] = [
		{
			"name": "test-backend",
			"path": str(pinned_repo),
			"commit": "0" * 40,
			"validate_head": True,
		},
	]
	macro_file = _write_minimal_validated_package(tmp_path, manifest)

	try:
		validate_final_paper_package(
			tmp_path,
			macro_file=macro_file,
			manifest=manifest,
		)
	except ValueError as error:
		assert "external pinned repository head matches manifest" in str(error)
	else:
		raise AssertionError("external pin mismatch should be rejected")


def test_final_paper_package_validator_rejects_stale_architecture_reports(
	tmp_path: Path,
) -> None:
	manifest = _minimal_artifact_manifest(
		report_count=1,
		baseline_count=1,
		paper_table_row_count=6,
	)
	comparison = {
		"report_count": 1,
		"baseline_count": 1,
		"paper_table_rows": [
			{
				"row_type": "library",
				"label": "paper_external_sketch_blocks_train",
				"macro_id": "paper_external_sketch_blocks_train",
				"solved": "1/1",
				"coverage_percent": 100.0,
				"runtime_planner": "none",
				"paper_profile_ready": True,
				"plan_count": 2,
				"mechanism_summary": "enabled: external_sketch_evidence",
			},
			{
				"row_type": "library",
				"label": "resource_dependency_counterexample_refinement_stress",
				"macro_id": "resource_dependency_counterexample_refinement_stress",
				"solved": "5/5",
				"coverage_percent": 100.0,
				"runtime_planner": "none",
				"paper_profile_ready": False,
				"plan_count": 2,
				"mechanism_summary": "enabled: counterexample_refinement",
			},
			{
				"row_type": "library",
				"label": "no_layer_c_with_refinement_resource_dependency_stress",
				"macro_id": "no_layer_c_with_refinement_resource_dependency_stress",
				"solved": "0/5",
				"coverage_percent": 0.0,
				"runtime_planner": "none",
				"paper_profile_ready": False,
				"plan_count": 1,
				"mechanism_summary": "disabled: layer_c_ordering",
			},
			{
				"row_type": "library",
				"label": "no_counterexample_refinement_resource_dependency_stress",
				"macro_id": "no_counterexample_refinement_resource_dependency_stress",
				"solved": "0/5",
				"coverage_percent": 0.0,
				"runtime_planner": "none",
				"paper_profile_ready": False,
				"plan_count": 1,
				"mechanism_summary": "disabled: counterexample_refinement",
			},
			{
				"row_type": "baseline",
				"label": "fast_downward_lama_per_problem",
				"macro_id": "blocks_train_fast_downward_lama_per_problem",
				"solved": "2/2",
				"coverage_percent": 100.0,
				"runtime_planner": "offline_baseline_only",
				"notes": "per_problem_trace_baseline; not a domain-level library",
				"mechanism_summary": "baseline",
			},
			{
				"row_type": "baseline",
				"label": "raw_external_policy_audit",
				"macro_id": "blocks_external_policy_audit",
				"solved": "0/2",
				"coverage_percent": 0.0,
				"runtime_planner": "not_runtime_executed",
				"notes": "domain-level artifact audit",
				"mechanism_summary": "baseline",
			},
		],
	}
	(tmp_path / "comparison.json").write_text(
		json.dumps(comparison, indent=2),
		encoding="utf-8",
	)
	macro_file = tmp_path / "results.tex"
	macro_file.write_text(
		format_comparison_latex_macros(comparison),
		encoding="utf-8",
	)
	_write_artifact_manifest_copy(tmp_path, manifest)
	for name in ("main", "ablation", "limitation"):
		summary_dir = tmp_path / f"{name}-matrix"
		summary_dir.mkdir(parents=True)
		report_file = summary_dir / f"{name}-report.json"
		report_file.write_text(
			json.dumps(
				{
					"coverage": {"solved_count": 1, "failed_count": 0},
					"generated_output_audit": {"passed": True},
					"synthesis_report": {
						"architecture_gap_summary": {"partially_done": 99},
					},
				},
			),
			encoding="utf-8",
		)
		(summary_dir / "matrix-summary.json").write_text(
			json.dumps(
				{
					"matrix_name": f"paper-final-{name}",
					"experiment_count": 1,
					"succeeded_count": 1,
					"failed_count": 0,
					"rows": [
						{
							"experiment_name": f"{name}-report",
							"report_file": str(report_file),
							"status": "succeeded",
						},
					],
				},
			),
			encoding="utf-8",
		)

	try:
		validate_final_paper_package(
			tmp_path,
			macro_file=macro_file,
			manifest=manifest,
		)
	except ValueError as error:
		assert "report architecture contract is current" in str(error)
	else:
		raise AssertionError("stale architecture report should be rejected")
