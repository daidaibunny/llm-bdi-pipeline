from __future__ import annotations

from pathlib import Path

import temporal_input.nl_benchmark as nl_benchmark
from temporal_input.nl_benchmark import BuildConfig
from temporal_input.nl_benchmark import build_domain_nl_manifest
from temporal_input.nl_benchmark import build_problem_candidates


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOMAINS_ROOT = PROJECT_ROOT / "src" / "domains"


def test_problem_build_reuses_one_initial_state_for_all_witnesses(
	monkeypatch,
) -> None:
	domain_dir = DOMAINS_ROOT / "blocksworld-on"
	original = nl_benchmark._initial_state
	call_count = 0

	def counted_initial_state(problem):
		nonlocal call_count
		call_count += 1
		return original(problem)

	monkeypatch.setattr(nl_benchmark, "_initial_state", counted_initial_state)
	build_problem_candidates(
		domain_file=domain_dir / "domain.pddl",
		problem_file=domain_dir / "test" / "p-50-0.pddl",
		config=BuildConfig(),
	)

	assert call_count == 1


def test_blocks_candidates_use_legal_non_repeating_two_step_witness() -> None:
	domain_dir = DOMAINS_ROOT / "blocksworld-on"
	candidates = build_problem_candidates(
		domain_file=domain_dir / "domain.pddl",
		problem_file=domain_dir / "test" / "p-50-0.pddl",
		config=BuildConfig(),
	)

	assert candidates
	assert {candidate.profile for candidate in candidates} == {
		"same_state_conjunction",
		"same_state_with_negation",
		"ordered_two_milestone",
		"ordered_three_milestone",
		"persistence_until",
	}
	candidate = next(
		item for item in candidates if item.profile == "ordered_two_milestone"
	)
	assert len(candidate.actions) == 2
	assert len(set(candidate.state_fingerprints)) == 3
	assert candidate.profile == "ordered_two_milestone"
	assert candidate.source_text.endswith(".")
	assert "strictly later state" in candidate.source_text
	assert candidate.witness_valid is True


def test_barman_candidate_uses_declared_subtypes_without_exposing_binding() -> None:
	domain_dir = DOMAINS_ROOT / "barman"
	candidates = build_problem_candidates(
		domain_file=domain_dir / "domain.pddl",
		problem_file=domain_dir / "test" / "p0_01.pddl",
		config=BuildConfig(),
	)

	assert candidates
	candidate = candidates[0]
	assert candidate.variables
	assert all(variable.pddl_type for variable in candidate.variables)
	assert not any(
		object_name in candidate.source_text
		for object_name in candidate.assignment.values()
	)
	assert set(candidate.assignment) == {variable.name for variable in candidate.variables}
	persistence = next(
		item for item in candidates if item.profile == "persistence_until"
	)
	assert "at every state before the first state where" in persistence.source_text
	assert "holds continues to hold" not in persistence.source_text
	assert "holds holds" not in persistence.source_text


def test_numeric_minecraft_candidates_record_numeric_state_changes() -> None:
	domain_dir = DOMAINS_ROOT / "numeric-minecraft"
	candidates = build_problem_candidates(
		domain_file=domain_dir / "domain.pddl",
		problem_file=domain_dir / "test" / "p0_01.pddl",
		config=BuildConfig(),
	)

	assert candidates
	assert any(
		any(atom.kind == "numeric_equality" for atom in candidate.atoms)
		for candidate in candidates
	)


def test_domain_manifest_has_one_public_row_per_test_problem() -> None:
	domain_dir = DOMAINS_ROOT / "depots"
	manifest = build_domain_nl_manifest(
		domain_dir=domain_dir,
		config=BuildConfig(),
	)

	test_files = sorted((domain_dir / "test").glob("*.pddl"))
	assert len(manifest.public_rows) == len(test_files)
	assert len({row.sample_id for row in manifest.public_rows}) == len(test_files)
	assert {row.problem_file for row in manifest.public_rows} == {
		str(path.relative_to(PROJECT_ROOT)) for path in test_files
	}
	assert all(row.status == "constructed_temporal_query" for row in manifest.public_rows)
	assert all(row.source_text for row in manifest.public_rows)
	assert all(row.gold_formula_ast is None for row in manifest.public_rows)
	assert all(
		set(row.to_public_dict()).isdisjoint(
			{
				"gold_atoms",
				"gold_formula_ast",
				"assignment",
				"witness_actions",
				"state_fingerprints",
			},
		)
		for row in manifest.public_rows
	)
	assert len(manifest.audit_rows) == len(test_files)
	assert all(row.gold_atoms for row in manifest.audit_rows)
	assert all(row.gold_formula_ast is not None for row in manifest.audit_rows)


def test_selection_is_equivariant_under_action_and_predicate_renaming(
	tmp_path: Path,
) -> None:
	original = _write_renaming_fixture(
		tmp_path / "original",
		predicates=("seedp", "markp", "donep"),
		actions=("begin_a", "finish_a", "reset_a"),
	)
	renamed = _write_renaming_fixture(
		tmp_path / "renamed",
		predicates=("renp", "renq", "renr"),
		actions=("ren_a", "ren_b", "ren_c"),
	)
	injected = _write_renaming_fixture(
		tmp_path / "injected",
		predicates=("seedp", "markp", "donep"),
		actions=("begin_a", "finish_a", "reset_a"),
		inject_irrelevant_static=True,
	)

	original_row = build_domain_nl_manifest(
		domain_dir=original,
		config=BuildConfig(),
	).public_rows[0]
	renamed_row = build_domain_nl_manifest(
		domain_dir=renamed,
		config=BuildConfig(),
	).public_rows[0]
	injected_row = build_domain_nl_manifest(
		domain_dir=injected,
		config=BuildConfig(),
	).public_rows[0]
	normalized_renamed_text = renamed_row.source_text
	assert normalized_renamed_text is not None
	for renamed_symbol, original_symbol in zip(
		("renp", "renq", "renr"),
		("seedp", "markp", "donep"),
	):
		normalized_renamed_text = normalized_renamed_text.replace(
			renamed_symbol,
			original_symbol,
		)

	assert original_row.profile == renamed_row.profile
	assert original_row.source_text == normalized_renamed_text
	assert original_row.declared_parameters == renamed_row.declared_parameters
	assert original_row.constraints == renamed_row.constraints
	assert original_row.profile == injected_row.profile
	assert original_row.source_text == injected_row.source_text


def _write_renaming_fixture(
	root: Path,
	*,
	predicates: tuple[str, str, str],
	actions: tuple[str, str, str],
	inject_irrelevant_static: bool = False,
) -> Path:
	seed, marked, done = predicates
	begin, finish, reset = actions
	extra_predicate = "(unused_static ?x - item) " if inject_irrelevant_static else ""
	extra_fact = "(unused_static object1) " if inject_irrelevant_static else ""
	(root / "test").mkdir(parents=True)
	(root / "domain.pddl").write_text(
		f"""
(define (domain rename-fixture)
  (:requirements :strips :typing)
  (:types item)
  (:predicates {extra_predicate}({seed} ?x - item) ({marked} ?x - item) ({done} ?x - item))
  (:action {begin}
    :parameters (?x - item)
    :precondition ({seed} ?x)
    :effect (and (not ({seed} ?x)) ({marked} ?x)))
  (:action {finish}
    :parameters (?x - item)
    :precondition ({marked} ?x)
    :effect (and (not ({marked} ?x)) ({done} ?x)))
  (:action {reset}
    :parameters (?x - item)
    :precondition ({done} ?x)
    :effect (and (not ({done} ?x)) ({seed} ?x))))
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	(root / "test" / "p01.pddl").write_text(
		f"""
(define (problem rename-p01)
  (:domain rename-fixture)
  (:objects object1 - item)
  (:init {extra_fact}({seed} object1))
  (:goal ({done} object1)))
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	return root
