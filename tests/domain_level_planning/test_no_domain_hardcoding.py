from __future__ import annotations

import ast
import json
from pathlib import Path

from domain_level_planning.atomic_module_synthesis import (
	synthesize_atomic_minimal_literal_module_library,
)
from domain_level_planning.evidence_module import (
	compile_moose_readable_policy_to_minimal_module_asl_library,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_domain_level_planning_production_code_has_no_blocksworld_special_cases() -> None:
	forbidden_tokens = (
		"blocksworld",
		"blocks_4",
		"stack(",
		"unstack(",
		"pick-up",
		"put-down",
		"arm-empty",
		"on-table",
	)
	paths = tuple(
		path
		for path in (PROJECT_ROOT / "src" / "domain_level_planning").glob("*.py")
		if path.name != "__init__.py"
	)

	violations: list[str] = []
	for path in paths:
		text = path.read_text(encoding="utf-8").lower()
		for token in forbidden_tokens:
			if token in text:
				violations.append(f"{path.name}:{token}")

	assert violations == []


def test_full_test_runner_contains_only_the_dfa_transition_wrapper_path() -> None:
	text = (
		PROJECT_ROOT / "scripts" / "run_full_test_jason_validation.py"
	).read_text(encoding="utf-8")
	removed_alternative_paths = (
		"linear_single_body_wrapper_lines",
		"compact_recursive_completion_wrapper_lines",
		"_monotonic_guard_transition_wrapper_lines",
		"per_test_guard_trans_replay_without_json_metadata",
	)

	assert all(name not in text for name in removed_alternative_paths)
	assert '"wrapper_mode": "dfa_guard_transition_replay"' in text


def test_compiler_rules_contain_no_benchmark_or_fluent_name_literals() -> None:
	forbidden_exact_literals = {
		"barman",
		"ferry",
		"gripper",
		"logistics",
		"miconic",
		"rovers",
		"satellite",
		"transport",
		"depots",
		"blocksworld",
		"clear",
		"holding",
		"handempty",
		"lifting",
		"available",
		"served",
		"at-robby",
		"communicated_image_data",
		"have_image",
		"contains",
		"pogo_sticks_to_make",
		"stack",
		"unstack",
		"load-truck",
		"unload-truck",
	}
	compiler_paths = (
		PROJECT_ROOT / "src" / "domain_level_planning" / "atomic_module_synthesis.py",
		PROJECT_ROOT / "src" / "domain_level_planning" / "evidence_module.py",
		PROJECT_ROOT / "src" / "domain_level_planning" / "certified_effects.py",
		PROJECT_ROOT / "src" / "domain_level_planning" / "temporal_goal_appender.py",
		PROJECT_ROOT / "src" / "temporal_specification" / "prediction_validation.py",
		PROJECT_ROOT / "src" / "evaluation" / "temporal_goal_validation.py",
		PROJECT_ROOT / "src" / "evaluation" / "temporal_validation_batch.py",
		PROJECT_ROOT / "src" / "evaluation" / "temporal_benchmark.py",
		PROJECT_ROOT / "src" / "evaluation" / "temporal_benchmark_release.py",
	)
	violations: list[str] = []
	for path in compiler_paths:
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
		for node in ast.walk(tree):
			if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
				continue
			if node.value.lower() in forbidden_exact_literals:
				violations.append(f"{path.name}:{node.lineno}:{node.value}")

	assert violations == []


def test_atomic_synthesis_is_invariant_under_vocabulary_alpha_renaming(
	tmp_path: Path,
) -> None:
	first_domain = _write_alpha_renamed_domain(
		tmp_path / "first.pddl",
		domain_name="first",
		context_predicate="ready",
		goal_predicate="done",
		action_name="finish",
	)
	second_domain = _write_alpha_renamed_domain(
		tmp_path / "second.pddl",
		domain_name="second",
		context_predicate="enabled",
		goal_predicate="completed",
		action_name="commit",
	)

	first = synthesize_atomic_minimal_literal_module_library(
		domain_file=first_domain,
		seed_predicates=("done",),
		source_backend="test",
		source_name="alpha-first",
	)
	second = synthesize_atomic_minimal_literal_module_library(
		domain_file=second_domain,
		seed_predicates=("completed",),
		source_backend="test",
		source_name="alpha-second",
	)

	assert _plan_structure_profile(first) == _plan_structure_profile(second)
	assert (
		first.metadata["atomic_module_synthesis"]["raw_candidate_count"]
		== second.metadata["atomic_module_synthesis"]["raw_candidate_count"]
	)


def test_atomic_synthesis_is_invariant_under_action_parameter_permutation(
	tmp_path: Path,
) -> None:
	first_domain = tmp_path / "first-order.pddl"
	second_domain = tmp_path / "second-order.pddl"
	first_domain.write_text(
		"""
(define (domain first-order)
 (:requirements :strips)
 (:predicates (ready ?resource ?item) (done ?item))
 (:action finish
  :parameters (?resource ?item)
  :precondition (ready ?resource ?item)
  :effect (done ?item))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	second_domain.write_text(
		"""
(define (domain second-order)
 (:requirements :strips)
 (:predicates (ready ?resource ?item) (done ?item))
 (:action finish
  :parameters (?item ?resource)
  :precondition (ready ?resource ?item)
  :effect (done ?item))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	first = synthesize_atomic_minimal_literal_module_library(
		domain_file=first_domain,
		seed_predicates=("done",),
		source_backend="test",
		source_name="first-order",
	)
	second = synthesize_atomic_minimal_literal_module_library(
		domain_file=second_domain,
		seed_predicates=("done",),
		source_backend="test",
		source_name="second-order",
	)

	assert _plan_structure_profile(first) == _plan_structure_profile(second)
	assert first.metadata["atomic_module_synthesis"]["selector_optimization_cost"] == (
		second.metadata["atomic_module_synthesis"]["selector_optimization_cost"]
	)


def test_atomic_synthesis_ignores_unreferenced_static_vocabulary(tmp_path: Path) -> None:
	base_domain = _write_alpha_renamed_domain(
		tmp_path / "base.pddl",
		domain_name="base",
		context_predicate="ready",
		goal_predicate="done",
		action_name="finish",
	)
	extended_domain = tmp_path / "extended.pddl"
	extended_domain.write_text(
		base_domain.read_text(encoding="utf-8").replace(
			"(done ?x - item)",
			"(done ?x - item)\n\t\t  (unreferenced ?x - item)",
		).replace("(domain base)", "(domain extended)"),
		encoding="utf-8",
	)

	base = synthesize_atomic_minimal_literal_module_library(
		domain_file=base_domain,
		seed_predicates=("done",),
		source_backend="test",
		source_name="base",
	)
	extended = synthesize_atomic_minimal_literal_module_library(
		domain_file=extended_domain,
		seed_predicates=("done",),
		source_backend="test",
		source_name="extended",
	)

	assert _plan_structure_profile(base) == _plan_structure_profile(extended)
	assert {plan.trigger.symbol for plan in extended.plans} == {"done"}


def test_atomic_compilation_is_invariant_under_evidence_object_renaming(
	tmp_path: Path,
) -> None:
	domain_file = _write_alpha_renamed_domain(
		tmp_path / "object-renaming.pddl",
		domain_name="object-renaming",
		context_predicate="ready",
		goal_predicate="done",
		action_name="finish",
	)
	first_policy = """
 precedence : (1, 1, 0, 0)
       vars : item0
     s_cond : (ready item0)
     g_cond : (done item0)
    actions : (finish item0)
"""
	second_policy = first_policy.replace("item0", "artifact_object_27")

	first = compile_moose_readable_policy_to_minimal_module_asl_library(
		first_policy,
		domain_file=domain_file,
		domain_name="object-renaming",
		source_name="first-object-name",
	)
	second = compile_moose_readable_policy_to_minimal_module_asl_library(
		second_policy,
		domain_file=domain_file,
		domain_name="object-renaming",
		source_name="second-object-name",
	)

	assert _plan_structure_profile(first) == _plan_structure_profile(second)
	assert first.metadata["atomic_module_synthesis"]["selector_optimization_cost"] == (
		second.metadata["atomic_module_synthesis"]["selector_optimization_cost"]
	)


def _write_alpha_renamed_domain(
	path: Path,
	*,
	domain_name: str,
	context_predicate: str,
	goal_predicate: str,
	action_name: str,
) -> Path:
	path.write_text(
		f"""
		(define (domain {domain_name})
		 (:requirements :strips :typing)
		 (:types item)
		 (:predicates
		  ({context_predicate} ?x - item)
		  ({goal_predicate} ?x - item)
		 )
		 (:action {action_name}
		  :parameters (?x - item)
		  :precondition ({context_predicate} ?x)
		  :effect ({goal_predicate} ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	return path


def _plan_structure_profile(library) -> tuple[tuple[object, ...], ...]:
	return tuple(
		sorted(
			(
				len(plan.trigger.arguments),
				len(plan.context),
				tuple(step.kind for step in plan.body),
				len(plan.binding_certificate),
			)
			for plan in library.plans
		)
	)


def test_paper_experiment_scripts_use_registry_instead_of_embedded_domain_rows() -> None:
	"""Final-data scripts should not encode benchmark-specific PDDL rows."""

	forbidden_tokens = (
		"/".join(("src", "domains", "blocksworld", "")),
		"/".join(("src", "domains", "lab" + "workflow")),
		"/".join(("src", "domains", "marsrover")),
		"blocks_4_on_2",
	)
	paths = (
		PROJECT_ROOT / "scripts" / "run_final_paper_data.py",
		PROJECT_ROOT / "scripts" / "gp_backend_audit.py",
		PROJECT_ROOT / "scripts" / "materialize_achievement_benchmarks.py",
	)

	violations: list[str] = []
	for path in paths:
		text = path.read_text(encoding="utf-8")
		for token in forbidden_tokens:
			if token in text:
				violations.append(f"{path.name}:{token}")

	assert violations == []


def test_obsolete_generated_benchmark_implementation_names_are_absent() -> None:
	"""Deprecated generated benchmark artifacts should not re-enter current code."""

	forbidden_tokens = (
		"blocksworld_qclear",
		"blocksworld_qon",
		"blocksworld_qbw",
		"run_blocks_train_experiment",
		"learner_sketches_blocksworld_blocks_4_on_2",
		"/".join(("src", "domains", "blocksworld", "")),
		"/".join(("src", "domains", "marsrover")),
		"fixed train/test snapshot",
	)
	scan_roots = (
		PROJECT_ROOT / "README.md",
		PROJECT_ROOT / "TO-DO-LIST.md",
		PROJECT_ROOT / "scripts",
		PROJECT_ROOT / "src",
		PROJECT_ROOT / "tests",
		PROJECT_ROOT / "paper_artifacts",
	)
	suffixes = {".bib", ".json", ".md", ".py", ".txt"}

	paths: list[Path] = []
	for root in scan_roots:
		if root.is_file():
			paths.append(root)
		else:
			paths.extend(path for path in root.rglob("*") if path.is_file())

	violations: list[str] = []
	for path in paths:
		if path == Path(__file__).resolve():
			continue
		if path.suffix and path.suffix.lower() not in suffixes:
			continue
		relative = path.relative_to(PROJECT_ROOT)
		text = path.read_text(encoding="utf-8", errors="ignore")
		for token in forbidden_tokens:
			if token in text or token in str(relative):
				violations.append(f"{relative}:{token}")

	assert violations == []


def test_benchmark_registry_uses_literature_property_groups() -> None:
	"""Benchmark groups should describe literature properties, not task stories."""

	registry_root = PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals"
	expected_groups = {
		"esho_classical_domains",
		"numeric_fluent_domains",
		"feature_definable_serialized_width_domains",
	}
	control = json.loads((registry_root / "registry.json").read_text(encoding="utf-8"))

	assert set(control["selected_benchmark_property_group_ids"]) == expected_groups
	assert "selected_goal_property_group_ids" not in control

	records = [
		json.loads(path.read_text(encoding="utf-8"))
		for path in registry_root.glob("*/*/benchmark.json")
	]
	assert len(records) == 16
	assert {record["benchmark_property_group_id"] for record in records} == expected_groups
	for record in records:
		assert "goal_property_group_id" not in record


def test_batch_scripts_default_to_selected_registry_domains() -> None:
	"""Long-running batch defaults should not drift from the selected registry."""

	from scripts import run_full_test_jason_validation
	from scripts import run_moose_faithful_e2e
	from scripts import run_timestamped_moose_asl_batch

	registry_root = PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals"
	control = json.loads((registry_root / "registry.json").read_text(encoding="utf-8"))
	selected_domain_ids = tuple(control["selected_domain_ids"])

	assert run_moose_faithful_e2e.DEFAULT_DOMAINS == selected_domain_ids
	assert run_timestamped_moose_asl_batch.DEFAULT_DOMAINS == selected_domain_ids
	assert run_full_test_jason_validation.DEFAULT_DOMAINS == selected_domain_ids
	assert "blocks" not in selected_domain_ids
	assert "blocksworld-clear" in selected_domain_ids
	assert "blocksworld-on" in selected_domain_ids
	assert "blocksworld-tower" in selected_domain_ids


def test_depots_small_instance_split_uses_half_train_data() -> None:
	"""Depots has few source instances, so keep its training evidence at half."""

	from scripts.materialize_achievement_benchmarks import _domain_specs

	depots_spec = next(spec for spec in _domain_specs() if spec.domain_id == "depots")
	assert depots_spec.train_ratio == 1 / 2
	assert "1/2" in depots_spec.split_policy

	depots_root = PROJECT_ROOT / "src" / "domains" / "depots"
	source = json.loads((depots_root / "source.json").read_text(encoding="utf-8"))
	train_names = tuple(path.name for path in sorted((depots_root / "train").glob("*.pddl")))
	test_names = tuple(path.name for path in sorted((depots_root / "test").glob("*.pddl")))

	assert source["train_count"] == 11
	assert source["test_count"] == 11
	assert train_names == tuple(f"p{index:02d}.pddl" for index in range(1, 12))
	assert test_names == tuple(f"p{index:02d}.pddl" for index in range(12, 23))
