from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from domain_level_planning.atomic_module_synthesis import (
	synthesize_atomic_minimal_literal_module_library,
)
from scripts.run_full_test_jason_validation import append_guard_transition_full_test_wrappers
from scripts.run_full_test_jason_validation import apply_validation_summaries
from scripts.run_full_test_jason_validation import build_compile_atomic_library_command
from scripts.run_full_test_jason_validation import full_test_wrapper_lines
from scripts.run_full_test_jason_validation import JasonTask
from scripts.run_full_test_jason_validation import load_completed_validation_records
from scripts.run_full_test_jason_validation import prepare_domain_for_full_test
from scripts.run_full_test_jason_validation import query_entry_proposition
from scripts.run_full_test_jason_validation import resolve_batch_root
from scripts.run_full_test_jason_validation import render_fact_atom
from scripts.run_full_test_jason_validation import reported_action_count_fields
from scripts.run_full_test_jason_validation import run_jason_tasks
from scripts.run_full_test_jason_validation import safe_goal_fragment
from scripts.run_full_test_jason_validation import safe_path_fragment
from scripts.run_full_test_jason_validation import source_revision_metadata
from scripts.run_full_test_jason_validation import validate_one_task
from scripts.run_full_test_jason_validation import validation_input_fingerprint
from scripts.run_full_test_jason_validation import _jason_runtime_status_label
from scripts.run_full_test_jason_validation import _plan_verifier_status_label
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLFact


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _certified_library(domain_file: Path, *seed_predicates: str) -> PlanLibrary:
	return synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=seed_predicates,
		source_backend="test",
		source_name="test",
	)


def test_resolve_batch_root_selects_latest_timestamp(tmp_path: Path) -> None:
	(tmp_path / "20260704-120000").mkdir()
	(tmp_path / "20260705-090000").mkdir()

	resolved = resolve_batch_root(tmp_path, "latest")

	assert resolved == tmp_path / "20260705-090000"


def test_source_revision_metadata_distinguishes_tracked_and_untracked_changes(
	tmp_path: Path,
) -> None:
	import subprocess

	subprocess.run(("git", "init"), cwd=tmp_path, check=True, capture_output=True)
	subprocess.run(
		("git", "config", "user.email", "test@example.com"),
		cwd=tmp_path,
		check=True,
	)
	subprocess.run(
		("git", "config", "user.name", "Test User"),
		cwd=tmp_path,
		check=True,
	)
	tracked_file = tmp_path / "tracked.txt"
	tracked_file.write_text("baseline\n", encoding="utf-8")
	subprocess.run(("git", "add", "tracked.txt"), cwd=tmp_path, check=True)
	subprocess.run(
		("git", "commit", "-m", "test baseline"),
		cwd=tmp_path,
		check=True,
		capture_output=True,
	)

	clean = source_revision_metadata(tmp_path)
	tracked_file.write_text("changed\n", encoding="utf-8")
	(tmp_path / "untracked.txt").write_text("new\n", encoding="utf-8")
	dirty = source_revision_metadata(tmp_path)

	assert clean["available"] is True
	assert clean["tracked_changes"] is False
	assert clean["untracked_files"] is False
	assert dirty["commit"] == clean["commit"]
	assert dirty["tracked_changes"] is True
	assert dirty["untracked_files"] is True


def test_safe_goal_fragment_matches_existing_domain_goal_naming() -> None:
	assert safe_goal_fragment("domain-with-dash") == "domain_with_dash"
	assert safe_goal_fragment("blocks") == "blocks"


def test_safe_path_fragment_keeps_problem_ids_readable() -> None:
	assert safe_path_fragment("instance-26") == "instance-26"
	assert safe_path_fragment("p 01/problem") == "p_01_problem"


def test_query_entry_proposition_strips_top_level_goal_prefix() -> None:
	assert query_entry_proposition("g_miconic_test_41") == "miconic_test_41"
	assert query_entry_proposition("custom_goal") == "custom_goal_entry"


def test_render_fact_atom_matches_generated_asl_identifier_rules() -> None:
	assert render_fact_atom(PDDLFact("at-ferry", ["loc-1"])) == "at_ferry(loc_1)"
	assert render_fact_atom(PDDLFact("handempty", [])) == "handempty"


def test_full_test_compile_command_defaults_to_validated_policy_lifting(tmp_path: Path) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="validated-policy-lifting",
	)

	assert command[-2:] == ("--compiler-variant", "full")
	assert "--domain-file" in command


def test_full_test_compile_command_registers_atomic_variant(tmp_path: Path) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="validated-policy-lifting",
		compiler_variant="validated_evidence_adapter",
	)

	assert command[-2:] == (
		"--compiler-variant",
		"validated_evidence_adapter",
	)


def test_full_test_compile_command_can_request_faithful_mode(tmp_path: Path) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="faithful",
	)

	assert "--compiler-variant" not in command


def test_validation_status_labels_split_jason_and_val_outcomes() -> None:
	assert _jason_runtime_status_label({"status": "plan_verifier_failed"}) == "ok"
	assert _plan_verifier_status_label(
		{
			"status": "plan_verifier_failed",
			"plan_verifier_attempted": True,
			"plan_verifier_success": False,
		},
	) == "fail"
	assert _jason_runtime_status_label({"status": "timeout", "timed_out": True}) == "timeout"
	assert _plan_verifier_status_label({"plan_verifier_attempted": False}) == "not_attempted"


def test_full_test_wrapper_uses_guard_transition_replay(tmp_path: Path) -> None:
	asl_file = tmp_path / "plan_library.asl"
	problem_file = tmp_path / "p01.pddl"
	asl_file.write_text("/* base */\n", encoding="utf-8")
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain ferry)
		 (:objects car1 car2 loc1 loc2)
		 (:init)
		 (:goal (and (at car1 loc1) (at car2 loc2)))
		)
		""",
		encoding="utf-8",
	)

	domain_file = PROJECT_ROOT / "src" / "domains" / "ferry" / "domain.pddl"
	record = append_guard_transition_full_test_wrappers(
		domain="ferry",
		plan_library_asl=asl_file,
		problem_files=(problem_file,),
		domain_file=domain_file,
		atomic_plan_library=_certified_library(domain_file, "at"),
		max_output_bytes=1024 * 1024,
	)
	text = asl_file.read_text(encoding="utf-8")

	assert record["wrapper_mode"] == "dfa_guard_transition_replay"
	assert record["transition_controller_strategy"] == (
		"balanced_transition_repair_tree"
	)
	assert "tg_state" not in text
	assert "ferry_test_1." in text
	assert "+!g_ferry_test_1 : ferry_test_1 <-" in text
	assert "\t!g_ferry_test_1_trans_1." in text
	assert "+!g_ferry_test_1_trans_1_done : ferry_test_1 & at(car1, loc1) & at(car2, loc2) <-" in text
	assert "+!g_ferry_test_1_trans_1_repair_1_1 : ferry_test_1 & not at(car1, loc1) <-" in text
	assert "\t!at(car1, loc1)." in text
	assert "\t!g_ferry_test_1_trans_1_repair_1_2;" in text
	assert "\t!at(X, loc1);" not in text


def test_full_test_wrapper_uses_guard_transition_by_default(tmp_path: Path) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain gripper)
		 (:objects ball1 ball2 rooma roomb)
		 (:init (ball ball1) (ball ball2))
		 (:goal (and (at ball1 roomb) (at ball2 roomb)))
		)
		""",
		encoding="utf-8",
	)

	domain_file = PROJECT_ROOT / "src" / "domains" / "gripper" / "domain.pddl"
	lines, plan_count = full_test_wrapper_lines(
		domain="gripper",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=_certified_library(domain_file, "at"),
	)
	text = "\n".join(lines)

	assert plan_count == 9
	assert "+!g_gripper_test_1 : gripper_test_1 <-" in text
	assert "\t!g_gripper_test_1_trans_1." in text
	assert "\t!at(ball1, roomb)." in text
	assert "\t!at(ball2, roomb)." in text
	assert "not at(X, roomb)" not in text


def test_single_literal_guard_transition_matches_old_linear_effect(
	tmp_path: Path,
) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain miconic)
			 (:objects p1 f1 f2)
			 (:init (origin p1 f1) (destin p1 f2))
			 (:goal (and (served p1)))
			)
			""",
			encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="miconic",
		index=1,
		problem_file=problem_file,
	)
	text = "\n".join(lines)

	assert plan_count == 6
	assert "+!g_miconic_test_1 : miconic_test_1 <-" in text
	assert "\t!g_miconic_test_1_trans_1." in text
	assert "+!g_miconic_test_1_trans_1_done : miconic_test_1 & served(p1) <-" in text
	assert "+!g_miconic_test_1_trans_1_repair_1_1 : miconic_test_1 & not served(p1) <-" in text
	assert "\t!served(p1)." in text


def test_full_test_wrapper_keeps_mixed_destination_goals_in_one_transition(tmp_path: Path) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain ferry)
		 (:objects car1 car2 loc1 loc2 loc3)
		 (:init (at car1 loc1) (at car2 loc2))
		 (:goal (and (at car1 loc2) (at car2 loc3)))
		)
		""",
		encoding="utf-8",
	)

	domain_file = PROJECT_ROOT / "src" / "domains" / "ferry" / "domain.pddl"
	lines, plan_count = full_test_wrapper_lines(
		domain="ferry",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=_certified_library(domain_file, "at"),
	)
	text = "\n".join(lines)

	assert plan_count == 9
	assert "+!g_ferry_test_1 : ferry_test_1 <-" in text
	assert "\t!g_ferry_test_1_trans_1." in text
	assert "+!g_ferry_test_1_trans_1_done : ferry_test_1 & at(car1, loc2) & at(car2, loc3) <-" in text
	assert "\t!at(car1, loc2)." in text
	assert "\t!at(car2, loc3)." in text


def test_full_test_wrapper_orders_delete_threatening_goals_first(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	domain_file.write_text(
		"""
		(define (domain blocks-fragment)
		 (:requirements :strips)
		 (:predicates
		  (clear ?x)
		  (holding ?x)
		  (handempty)
		  (on ?x ?y)
		 )
		 (:action stack
		  :parameters (?x ?y)
		  :precondition (and (holding ?x) (clear ?y))
		  :effect (and (on ?x ?y) (clear ?x) (handempty) (not (holding ?x)) (not (clear ?y)))
		 )
		 (:action unstack
		  :parameters (?x ?y)
		  :precondition (and (on ?x ?y) (clear ?x) (handempty))
		  :effect (and (holding ?x) (clear ?y) (not (on ?x ?y)) (not (clear ?x)) (not (handempty)))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain blocks-fragment)
		 (:objects top middle base)
		 (:init (handempty) (clear top) (on top middle) (clear base))
		 (:goal (and (on top middle) (on middle base)))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="blocks-fragment",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=_blocks_fragment_atomic_library(),
	)
	text = "\n".join(lines)

	assert plan_count == 9
	assert text.index("not on(middle, base)") < text.index("not on(top, middle)")
	assert "+!g_blocks_fragment_test_1_trans_1_done : blocks_fragment_test_1 & on(middle, base) & on(top, middle) <-" in text


def test_full_test_wrapper_does_not_infer_semantics_from_argument_positions(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	domain_file.write_text(
		"""
		(define (domain generic-relations)
		 (:requirements :strips)
		 (:predicates (linked ?left ?right) (ready ?left ?right))
		 (:action make-linked
		  :parameters (?left ?right)
		  :precondition (ready ?left ?right)
		  :effect (linked ?left ?right)
		 )
		 (:action remove-linked
		  :parameters (?left ?right)
		  :precondition (linked ?left ?right)
		  :effect (not (linked ?left ?right))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain generic-relations)
		 (:objects a b c)
		 (:init (ready a b) (ready b c))
		 (:goal (and (linked a b) (linked b c)))
		)
		""",
		encoding="utf-8",
	)

	lines, _ = full_test_wrapper_lines(
		domain="generic-relations",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=_certified_library(domain_file, "linked"),
	)
	text = "\n".join(lines)

	assert text.index("not linked(a, b)") < text.index("not linked(b, c)")


def test_full_test_wrapper_enforces_preservation_safe_action_only_branches(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	domain_file.write_text(
		"""
		(define (domain selection)
		 (:requirements :strips)
		 (:predicates (completed ?x) (ready ?x))
		 (:action finish-safely
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (completed ?x))
		 (:action finish-by-reusing
		  :parameters (?x ?other)
		  :precondition (and (ready ?x) (completed ?other))
		  :effect (and (completed ?x) (not (completed ?other))))
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain selection)
		 (:objects first second)
		 (:init (ready first) (ready second))
		 (:goal (and (completed first) (completed second)))
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="selection",
		plans=(
			AgentSpeakPlan(
				"completed_already_true",
				AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
				("completed(X)",),
				(),
			),
			AgentSpeakPlan(
				"completed_safe",
				AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
				("ready(X)",),
				(AgentSpeakBodyStep("action", "finish-safely", ("X",)),),
			),
			AgentSpeakPlan(
				"completed_unsafe",
				AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
				("ready(X)", "completed(Y)"),
				(AgentSpeakBodyStep("action", "finish-by-reusing", ("X", "Y")),),
			),
		),
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="selection",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=library,
	)
	text = "\n".join(lines)

	assert plan_count == 11
	assert "finish_safely" in text
	assert "finish_by_reusing" not in text
	assert "!g_selection_test_1_trans_1_selected_completed(first)." in text
	assert "!g_selection_test_1_trans_1_selected_completed(second)." in text


def test_full_test_wrapper_finds_threats_beyond_two_producer_layers(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	domain_file.write_text(
		"""
		(define (domain deep-threat)
		 (:requirements :strips)
		 (:predicates
		  (goal ?x) (stage1 ?x) (stage2 ?x) (stage3 ?x)
		  (protected ?x) (seed ?x)
		 )
		 (:action achieve-goal
		  :parameters (?x)
		  :precondition (stage1 ?x)
		  :effect (goal ?x)
		 )
		 (:action make-stage1
		  :parameters (?x)
		  :precondition (stage2 ?x)
		  :effect (stage1 ?x)
		 )
		 (:action make-stage2
		  :parameters (?x)
		  :precondition (stage3 ?x)
		  :effect (stage2 ?x)
		 )
		 (:action make-stage3
		  :parameters (?x)
		  :precondition (seed ?x)
		  :effect (and (stage3 ?x) (not (protected ?x)))
		 )
		 (:action restore-protected
		  :parameters (?x)
		  :precondition (seed ?x)
		  :effect (protected ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain deep-threat)
		 (:objects item)
		 (:init (seed item))
		 (:goal (and (protected item) (goal item)))
		)
		""",
		encoding="utf-8",
	)

	lines, _ = full_test_wrapper_lines(
		domain="deep-threat",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=_certified_library(domain_file, "goal", "protected"),
	)
	text = "\n".join(lines)

	assert text.index("not goal(item)") < text.index("not protected(item)")


def test_full_test_wrapper_keeps_ground_constants_distinct_from_schema_variables(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	domain_file.write_text(
		"""
		(define (domain blocks-fragment)
		 (:requirements :strips)
		 (:predicates
		  (clear ?x)
		  (holding ?x)
		  (handempty)
		  (on ?x ?y)
		 )
		 (:action stack
		  :parameters (?x ?y)
		  :precondition (and (holding ?x) (clear ?y))
		  :effect (and (on ?x ?y) (clear ?x) (handempty)
		   (not (holding ?x)) (not (clear ?y)))
		 )
		 (:action unstack
		  :parameters (?x ?y)
		  :precondition (and (on ?x ?y) (clear ?x) (handempty))
		  :effect (and (holding ?x) (clear ?y) (not (on ?x ?y))
		   (not (clear ?x)) (not (handempty)))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain blocks-fragment)
		 (:objects top x middle base)
		 (:init (handempty) (clear top) (on top x) (clear base))
		 (:goal (and (on top x) (on x middle) (on middle base)))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="blocks-fragment",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=_blocks_fragment_atomic_library(),
	)
	text = "\n".join(lines)

	assert plan_count == 12
	assert (
		"+!g_blocks_fragment_test_1_trans_1_done : blocks_fragment_test_1 "
		"& on(middle, base) & on(x, middle) & on(top, x) <-"
	) in text


def _blocks_fragment_atomic_library() -> PlanLibrary:
	return PlanLibrary(
		domain_name="blocks-fragment",
		plans=(
			AgentSpeakPlan(
				plan_name="clear_via_unstack",
				trigger=AgentSpeakTrigger("achievement_goal", "clear", ("X",)),
				context=("on(Y, X)", "clear(Y)"),
				body=(AgentSpeakBodyStep("action", "unstack", ("Y", "X")),),
			),
			AgentSpeakPlan(
				plan_name="holding_via_clear_and_unstack",
				trigger=AgentSpeakTrigger("achievement_goal", "holding", ("X",)),
				context=("on(X, Z)",),
				body=(
					AgentSpeakBodyStep("subgoal", "clear", ("X",)),
					AgentSpeakBodyStep("action", "unstack", ("X", "Z")),
				),
			),
			AgentSpeakPlan(
				plan_name="on_via_preparation",
				trigger=AgentSpeakTrigger("achievement_goal", "on", ("X", "Y")),
				body=(
					AgentSpeakBodyStep("subgoal", "clear", ("X",)),
					AgentSpeakBodyStep("subgoal", "holding", ("X",)),
					AgentSpeakBodyStep("action", "stack", ("X", "Y")),
				),
			),
		),
	)


def test_full_test_wrapper_uses_only_guard_transition_replay_for_monotonic_goals(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	domain_file.write_text(
		"""
		(define (domain delivery-fragment)
		 (:requirements :strips)
		 (:predicates (holding ?x) (at ?x ?y))
		 (:action place
		  :parameters (?x ?y)
		  :precondition (holding ?x)
		  :effect (and (at ?x ?y) (not (holding ?x)))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain delivery-fragment)
		 (:objects item1 item2 loc1 loc2)
		 (:init (holding item1) (holding item2))
		 (:goal (and (at item1 loc1) (at item2 loc2)))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="delivery-fragment",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=_certified_library(domain_file, "at"),
	)
	text = "\n".join(lines)

	assert plan_count == 9
	assert "_repair_1_2" in text
	assert (
		"+!g_delivery_fragment_test_1_trans_1_done : delivery_fragment_test_1 "
		"& at(item1, loc1) & at(item2, loc2) <-"
	) in text


def test_full_test_wrapper_uses_module_local_delete_certificate(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	domain_file.write_text(
		"""
		(define (domain relocation-fragment)
		 (:requirements :strips)
		 (:predicates (at ?x ?y))
		 (:action relocate
		  :parameters (?x ?from ?to)
		  :precondition (at ?x ?from)
		  :effect (and (at ?x ?to) (not (at ?x ?from)))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain relocation-fragment)
		 (:objects item1 item2 loc1 loc2)
		 (:init (at item1 loc1) (at item2 loc1))
		 (:goal (and (at item1 loc2) (at item2 loc2)))
		)
		""",
		encoding="utf-8",
	)
	atomic_library = PlanLibrary(
		domain_name="relocation-fragment",
		plans=(
			AgentSpeakPlan(
				plan_name="at_via_relocate",
				trigger=AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
				context=("at(X, A)",),
				body=(AgentSpeakBodyStep("action", "relocate", ("X", "A", "Y")),),
			),
		),
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="relocation-fragment",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		atomic_plan_library=atomic_library,
	)
	text = "\n".join(lines)

	assert plan_count == 9
	assert "_repair_1_2" in text

	conflicting_problem_file = tmp_path / "p02.pddl"
	conflicting_problem_file.write_text(
		"""
		(define (problem p02)
		 (:domain relocation-fragment)
		 (:objects item1 loc1 loc2)
		 (:init (at item1 loc1))
		 (:goal (and (at item1 loc1) (at item1 loc2)))
		)
		""",
		encoding="utf-8",
	)
	with pytest.raises(
		ValueError,
		match="functionally_inconsistent_conjunctive_transition",
	):
		full_test_wrapper_lines(
			domain="relocation-fragment",
			index=2,
			problem_file=conflicting_problem_file,
			domain_file=domain_file,
			atomic_plan_library=atomic_library,
		)


def test_full_test_wrapper_accepts_numeric_equality_goal(tmp_path: Path) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain numeric-minecraft)
		 (:objects cell0)
		 (:init (= (pogo-sticks-to-make) 4))
		 (:goal (= (pogo-sticks-to-make) 0))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="numeric-minecraft",
		index=1,
		problem_file=problem_file,
	)
	text = "\n".join(lines)

	assert plan_count == 6
	assert "+!g_numeric_minecraft_test_1 : numeric_minecraft_test_1 <-" in text
	assert "\t!g_numeric_minecraft_test_1_trans_1." in text
	assert text.count("!pogo_sticks_to_make(0)") == 1
	assert "pogo_sticks_to_make(0) <-" in text
	assert "\t!pogo_sticks_to_make(0)." in text


def test_full_test_wrapper_rejects_uncertified_mixed_numeric_conjunction(
	tmp_path: Path,
) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain numeric-transport)
		 (:objects truck1 package1)
		 (:init (= (capacity truck1) 2))
		 (:goal (and (in package1 truck1) (= (capacity truck1) 1)))
		)
		""",
		encoding="utf-8",
	)

	with pytest.raises(ValueError, match="uncertified_numeric_conjunctive_transition"):
		full_test_wrapper_lines(
			domain="numeric-transport",
			index=1,
			problem_file=problem_file,
		)


def test_full_test_wrapper_rejects_unsupported_numeric_goal_comparator(
	tmp_path: Path,
) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain numeric-transport)
		 (:objects truck1)
		 (:init (= (capacity truck1) 2))
		 (:goal (>= (capacity truck1) 1))
		)
		""",
		encoding="utf-8",
	)

	try:
		full_test_wrapper_lines(
			domain="numeric-transport",
			index=1,
			problem_file=problem_file,
		)
	except ValueError as error:
		assert "unsupported numeric goal comparator" in str(error)
	else:
		raise AssertionError("Expected unsupported numeric comparator to be rejected.")


def test_apply_validation_summaries_marks_domain_failed_when_any_test_fails() -> None:
	summary = {
		"domains": {
			"ferry": {"success": True},
			"barman": {"success": True},
		},
	}

	apply_validation_summaries(
		summary=summary,
		domains=("ferry", "barman"),
		validation_records=(
			{
				"domain": "ferry",
				"success": True,
				"plan_verifier_success": True,
				"plan_verifier_attempted": True,
			},
			{
				"domain": "barman",
				"success": False,
				"plan_verifier_success": None,
				"plan_verifier_attempted": False,
			},
		),
	)

	assert summary["domains"]["ferry"]["success"] is True
	assert summary["domains"]["ferry"]["validation_success"] is True
	assert summary["domains"]["barman"]["success"] is False
	assert summary["domains"]["barman"]["validation_success"] is False
	assert summary["domains"]["barman"]["jason_validation"]["failure_count"] == 1


def test_reported_action_count_uses_plan_trace_when_stdout_is_truncated(
	tmp_path: Path,
) -> None:
	plan_trace = tmp_path / "jason_plan.plan"
	plan_trace.write_text("(a)\n(b)\n(c)\n(d)\n", encoding="utf-8")

	fields = reported_action_count_fields(
		payload={
			"action_count": 3,
			"timed_out": False,
			"exit_code": 0,
			"output_summary": {"has_execute_success": True},
		},
		plan_trace_path=plan_trace,
	)

	assert fields["action_count"] == 4
	assert fields["observed_action_prefix_count"] == 3
	assert fields["plan_trace_action_count"] == 4
	assert fields["action_count_complete"] is True
	assert fields["action_count_source"] == "plan_trace"


def test_reported_action_count_ignores_plan_trace_for_failed_execution(
	tmp_path: Path,
) -> None:
	plan_trace = tmp_path / "jason_plan.plan"
	plan_trace.write_text("(a)\n(b)\n(c)\n(d)\n", encoding="utf-8")

	fields = reported_action_count_fields(
		payload={
			"action_count": 3,
			"timed_out": False,
			"exit_code": 0,
			"output_summary": {"has_execute_success": False},
		},
		plan_trace_path=plan_trace,
	)

	assert fields["action_count"] is None
	assert fields["observed_action_prefix_count"] == 3
	assert fields["plan_trace_action_count"] == 4
	assert fields["action_count_complete"] is False
	assert fields["action_count_source"] == "unknown_incomplete_execution"


def test_reported_action_count_marks_timeout_without_trace_as_unknown(
	tmp_path: Path,
) -> None:
	plan_trace = tmp_path / "jason_plan.plan"
	plan_trace.write_text("", encoding="utf-8")

	fields = reported_action_count_fields(
		payload={
			"action_count": 3,
			"timed_out": True,
			"exit_code": None,
			"output_summary": {"has_execute_success": False},
		},
		plan_trace_path=plan_trace,
	)

	assert fields["action_count"] is None
	assert fields["observed_action_prefix_count"] == 3
	assert fields["plan_trace_action_count"] == 0
	assert fields["action_count_complete"] is False
	assert fields["action_count_source"] == "unknown_timeout"


def test_prepare_domain_can_filter_test_problem_names(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_root = tmp_path / "src" / "domains" / "ferry"
	(domain_root / "test").mkdir(parents=True)
	(domain_root / "domain.pddl").write_text("(define (domain ferry))\n", encoding="utf-8")
	for name in ("p2_01.pddl", "p2_02.pddl", "p1_01.pddl"):
		(domain_root / "test" / name).write_text(
			"""
			(define (problem probe)
			 (:domain ferry)
			 (:goal (and (at car1 loc1)))
			)
			""",
			encoding="utf-8",
		)
	batch_root = tmp_path / "batch"
	(batch_root / "run_logs" / "ferry").mkdir(parents=True)
	(batch_root / "run_logs" / "ferry" / "ferry.model.readable").write_text(
		"policy\n",
		encoding="utf-8",
	)

	def fake_command(
		*,
		readable_policy,
		domain_file,
		domain,
		library_root,
		atomic_library_mode,
		compiler_variant,
	):
		assert compiler_variant is None
		return ("true",)

	def fake_run_logged_command(command, *, stdout_file, stderr_file, timeout_seconds):
		plan_dir = tmp_path / "run" / "domain_libraries" / "ferry"
		plan_dir.mkdir(parents=True, exist_ok=True)
		(plan_dir / "plan_library.asl").write_text("/* base */\n", encoding="utf-8")
		(plan_dir / "plan_library.json").write_text(
			json.dumps(PlanLibrary(domain_name="ferry", plans=()).to_dict()),
			encoding="utf-8",
		)

		class Result:
			success = True

			def to_dict(self):
				return {"success": True}

		return Result()

	monkeypatch.setattr("scripts.run_full_test_jason_validation.PROJECT_ROOT", tmp_path)
	monkeypatch.setattr(
		"scripts.run_full_test_jason_validation.build_compile_atomic_library_command",
		fake_command,
	)
	monkeypatch.setattr(
		"scripts.run_full_test_jason_validation.run_logged_command",
		fake_run_logged_command,
	)

	record, tasks = prepare_domain_for_full_test(
		domain="ferry",
		batch_root=batch_root,
		run_root=tmp_path / "run",
		timeout_seconds=1,
		atomic_library_mode="validated-policy-lifting",
		write_domain_long_asl=False,
		max_domain_long_asl_bytes=1024,
		test_name_regex=r"^p2_0[12]\.pddl$",
	)

	assert record["success"] is True
	assert [task.problem_file.name for task in tasks] == ["p2_01.pddl", "p2_02.pddl"]


def test_docker_val_wrapper_builds_large_stack_validate_binary() -> None:
	script = Path("scripts/validate_with_docker_val.sh").read_text(encoding="utf-8")

	assert "VAL_PARSER_STACK_DEPTH" in script
	assert "YYMAXDEPTH" in script
	assert "tmp/val-large-stack" in script
	assert ".build.lock" in script
	assert "VAL_SOURCE_ROOT" in script
	assert '"$VAL_SOURCE_ROOT:/val-source:ro"' in script
	assert "SOURCE_DIR=/val-source" in script


def test_validate_one_task_embeds_runtime_asl_without_extra_plan_library_file(
	tmp_path: Path,
	monkeypatch,
) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain gripper)
		 (:objects ball1 rooma roomb)
		 (:init)
		 (:goal (and (at ball1 roomb)))
		)
		""",
		encoding="utf-8",
	)
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text("(define (domain gripper))\n", encoding="utf-8")
	plan_library_asl = tmp_path / "domain_plan_library.asl"
	plan_library_asl.write_text("/* base */\n", encoding="utf-8")
	output_dir = tmp_path / "out"
	captured: dict[str, object] = {}

	class FakeRunner:
		def __init__(self, **kwargs):
			captured["init"] = kwargs

		def validate(self, **kwargs):
			captured["validate"] = kwargs

			class Result:
				def to_dict(self):
					return {
						"success": True,
						"status": "success",
						"timed_out": False,
						"exit_code": 0,
						"action_count": 1,
							"plan_verifier": {
								"success": True,
								"attempted": True,
								"available": True,
							},
							"artifacts": {
								"plan_trace": "trace.plan",
								"committed_plan_trace": "committed.plan",
								"plan_verifier_stdout": "val.stdout",
								"plan_verifier_stderr": "val.stderr",
							},
							"output_summary": {"has_execute_success": True},
							"error": None,
						}

			return Result()

	monkeypatch.setattr("scripts.run_full_test_jason_validation.JasonPlanLibraryRunner", FakeRunner)
	task = JasonTask(
		domain="gripper",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		plan_library_asl=plan_library_asl,
		base_plan_library_asl_text="/* base */",
		goal_name="g_gripper_test_1",
		output_dir=output_dir,
	)

	record = validate_one_task(
		task,
		classpath="fake-classpath",
		compiled_environment_dirs={},
		timeout_seconds=1,
		jason_java_stack_size="64m",
		plan_verifier_command=None,
		require_plan_verifier=False,
		plan_verifier_timeout_seconds=1,
		write_per_test_runtime_asl=False,
	)

	validate_kwargs = captured["validate"]
	assert record["success"] is True
	assert record["runtime_plan_library_asl"] is None
	assert record["runtime_plan_library_embedded_in_agentspeak"] is True
	assert not (output_dir / "plan_library.asl").exists()
	assert validate_kwargs["plan_library_asl"] == plan_library_asl
	assert "!g_gripper_test_1_trans_1." in validate_kwargs["plan_library_asl_text"]
	assert "!at(ball1, roomb)." in validate_kwargs["plan_library_asl_text"]


def test_run_jason_tasks_appends_progress_records_without_rewriting_summary(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	plan_library_asl = tmp_path / "plan_library.asl"
	domain_file.write_text("(define (domain ferry))\n", encoding="utf-8")
	problem_file.write_text("(define (problem p01) (:domain ferry))\n", encoding="utf-8")
	plan_library_asl.write_text("/* base */\n", encoding="utf-8")
	task = JasonTask(
		domain="ferry",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		plan_library_asl=plan_library_asl,
		base_plan_library_asl_text="/* base */",
		goal_name="g_ferry_test_1",
		output_dir=tmp_path / "jason" / "ferry" / "test_0001_p01",
	)
	summary = {"validations": []}
	summary_file = tmp_path / "summary.json"

	monkeypatch.setattr(
		"scripts.run_full_test_jason_validation.prepare_shared_jason_environments",
		lambda **kwargs: {},
	)
	monkeypatch.setattr(
		"scripts.run_full_test_jason_validation.validate_one_task",
		lambda *args, **kwargs: {
			"domain": "ferry",
			"test_index": 1,
			"goal_name": "g_ferry_test_1",
			"success": True,
			"status": "success",
			"timed_out": False,
			"action_count": 1,
			"plan_verifier_attempted": True,
			"plan_verifier_success": True,
		},
	)

	records = run_jason_tasks(
		tasks=(task,),
		classpath="fake-classpath",
		run_root=tmp_path,
		num_workers=1,
		timeout_seconds=1,
		jason_java_stack_size="64m",
		plan_verifier_command=None,
		require_plan_verifier=True,
		plan_verifier_timeout_seconds=1,
		write_per_test_runtime_asl=False,
		summary=summary,
		summary_file=summary_file,
	)

	jsonl_file = tmp_path / "validation_results.jsonl"
	lines = jsonl_file.read_text(encoding="utf-8").splitlines()
	assert records[0]["success"] is True
	assert len(lines) == 1
	assert json.loads(lines[0])["goal_name"] == "g_ferry_test_1"
	assert summary["validation_results_jsonl"] == str(jsonl_file)
	assert not summary_file.exists()


def test_completed_validation_records_require_exact_input_fingerprint(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "p01.pddl"
	plan_library_asl = tmp_path / "plan_library.asl"
	domain_file.write_text("(define (domain ferry))\n", encoding="utf-8")
	problem_file.write_text("(define (problem p01) (:domain ferry))\n", encoding="utf-8")
	plan_library_asl.write_text("/* base */\n", encoding="utf-8")
	task = JasonTask(
		domain="ferry",
		index=1,
		problem_file=problem_file,
		domain_file=domain_file,
		plan_library_asl=plan_library_asl,
		base_plan_library_asl_text="/* base */",
		goal_name="g_ferry_test_1",
		output_dir=tmp_path / "jason/ferry/test_0001_p01",
		runtime_wrapper_text="ferry_test_1.\n+!g_ferry_test_1 : ferry_test_1 <- true.",
	)
	record = {
		"domain": "ferry",
		"test_index": 1,
		"goal_name": "g_ferry_test_1",
		"status": "success",
		"success": True,
		"input_fingerprint": validation_input_fingerprint(task),
	}
	task.output_dir.mkdir(parents=True)
	(task.output_dir / "validation_record.json").write_text(
		json.dumps(record),
		encoding="utf-8",
	)

	completed = load_completed_validation_records((task,))
	assert tuple(completed.values()) == (record,)

	problem_file.write_text("(define (problem changed) (:domain ferry))\n", encoding="utf-8")
	assert load_completed_validation_records((task,)) == {}


def test_parser_order_batch_allows_native_plan_verifier_command_override() -> None:
	script = Path("scripts/run_parser_order_full_val_batch.sh").read_text(encoding="utf-8")

	assert 'PLAN_VERIFIER_COMMAND="${PLAN_VERIFIER_COMMAND:-bash $PROJECT_ROOT/scripts/validate_with_docker_val.sh}"' in script
	assert '--plan-verifier-command "$PLAN_VERIFIER_COMMAND"' in script


def test_parser_order_batch_keeps_per_test_asl_without_domain_long_asl() -> None:
	script = Path("scripts/run_parser_order_full_val_batch.sh").read_text(encoding="utf-8")

	assert "--write-per-test-runtime-asl" in script
	assert "--write-domain-long-asl" not in script


def test_parser_order_batch_defaults_match_paper_budget_and_local_parallelism() -> None:
	script = Path("scripts/run_parser_order_full_val_batch.sh").read_text(encoding="utf-8")

	assert 'WORKERS="${WORKERS:-6}"' in script
	assert 'MOOSE_WORKERS="${MOOSE_WORKERS:-1}"' in script
	assert 'MOOSE_SEEDS="${MOOSE_SEEDS:-0 1 2 3 4}"' in script
	assert 'MOOSE_SEED_PARALLELISM="${MOOSE_SEED_PARALLELISM:-5}"' in script
	assert 'JASON_WORKERS="${JASON_WORKERS:-$WORKERS}"' in script
	assert 'seed_batch_id="${BATCH_ID}-seed${seed}"' in script
	assert 'seed_validation_run_id="${VALIDATION_RUN_ID}-seed${seed}"' in script
	assert '--random-seed "$seed"' in script
	assert '--batch-id "$seed_batch_id"' in script
	assert 'run_moose_seed "$seed" &' in script
	assert 'run_validation_seed "$seed"' in script
	assert 'run_validation_seed "$seed" &' not in script
	assert '"evidence_merged": False' in script
	assert 'TRAIN_TIMEOUT_SECONDS="${TRAIN_TIMEOUT_SECONDS:-43200}"' in script
	assert 'JASON_JAVA_STACK_SIZE="${JASON_JAVA_STACK_SIZE:-64m}"' in script
	assert "moose_train_timeout_seconds=$TRAIN_TIMEOUT_SECONDS" in script


def test_parser_order_batch_has_valid_bash_syntax() -> None:
	result = subprocess.run(
		("bash", "-n", "scripts/run_parser_order_full_val_batch.sh"),
		check=False,
		capture_output=True,
		text=True,
	)

	assert result.returncode == 0, result.stderr


def test_parser_order_batch_rejects_internal_moose_parallelism() -> None:
	result = subprocess.run(
		("bash", "scripts/run_parser_order_full_val_batch.sh", "ferry"),
		check=False,
		capture_output=True,
		text=True,
		env={
			"PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
			"MOOSE_WORKERS": "2",
		},
	)

	assert result.returncode == 2
	assert "MOOSE_WORKERS must be 1" in result.stderr


@pytest.mark.parametrize(
	("override", "expected_error"),
	(
		(
			{"MOOSE_SEEDS": "0 1 2 3"},
			"MOOSE_SEEDS must contain exactly five",
		),
		(
			{"MOOSE_SEEDS": "0 1 2 3 3"},
			"MOOSE_SEEDS must not contain duplicate seed 3",
		),
		(
			{"MOOSE_RANDOM_SEED": "0"},
			"MOOSE_RANDOM_SEED is obsolete",
		),
	),
)
def test_parser_order_batch_rejects_nonstandard_seed_protocol(
	override: dict[str, str],
	expected_error: str,
) -> None:
	environment = {
		"PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
		**override,
	}

	result = subprocess.run(
		("bash", "scripts/run_parser_order_full_val_batch.sh", "ferry"),
		check=False,
		capture_output=True,
		text=True,
		env=environment,
	)

	assert result.returncode == 2
	assert expected_error in result.stderr
