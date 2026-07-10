from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from domain_level_planning.evidence_module import (
	audit_moose_atomic_library_quality,
	compile_policy_evidence_program_to_minimal_module_asl_library,
	compile_moose_readable_policy_to_minimal_module_asl_library,
	compile_moose_readable_policy_to_asl_library,
	evidence_program_from_moose_readable_policy,
	parse_moose_readable_policy,
	policy_program_from_moose_readable_policy,
)
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld-tower" / "domain.pddl"
DEPOTS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl"
LOGISTICS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "logistics" / "domain.pddl"
NUMERIC_FERRY_DOMAIN = PROJECT_ROOT / "src" / "domains" / "numeric-ferry" / "domain.pddl"
NUMERIC_MINECRAFT_DOMAIN = PROJECT_ROOT / "src" / "domains" / "numeric-minecraft" / "domain.pddl"


FERRY_READABLE_POLICY = """
 precedence : (1, 1, 0, 0)
       vars : car0 location0
     s_cond : (at-ferry location0) (on car0)
     g_cond : (at car0 location0)
    actions : (debark car0 location0)

 precedence : (1, 3, 0, 0)
       vars : car0 location0 location1
     s_cond : (at car0 location0) (at-ferry location0) (empty-ferry)
     g_cond : (at car0 location1)
    actions : (board car0 location0) (sail location0 location1) (debark car0 location1)
"""


BLOCKS_READABLE_POLICY = """
 precedence : (1, 1, 0, 0)
       vars : block0 block1
     s_cond : (clear block0) (ontable block0) (handempty) (clear block1)
     g_cond : (on block0 block1)
    actions : (pick-up block0) (stack block0 block1)
"""


LOGISTICS_INTERMODAL_READABLE_POLICY = """
 precedence : (1, 6, 0, 0)
       vars : airplane0 city0 location0 location1 location2 package0 truck0
     s_cond : (at airplane0 location0) (at package0 location0) (at truck0 location1) (has-airport location0) (has-airport location1) (in-city location1 city0) (in-city location2 city0)
     g_cond : (at package0 location2)
	    actions : (load-airplane package0 airplane0 location0) (fly-airplane airplane0 location0 location1) (unload-airplane package0 airplane0 location1) (load-truck package0 truck0 location1) (drive-truck truck0 location1 location2 city0) (unload-truck package0 truck0 location2)
	"""


DEPOTS_CLEAR_WITH_PARKING_READABLE_POLICY = """
 precedence : (1, 2, 0, 0)
       vars : hoist0 crate0 crate1 place0 surface0
     s_cond : (hoist hoist0) (crate crate0) (surface crate1) (place place0) (at hoist0 place0) (available hoist0) (at crate0 place0) (on crate0 crate1) (clear crate0) (at surface0 place0) (clear surface0) (surface surface0)
     g_cond : (clear crate1)
    actions : (lift hoist0 crate0 crate1 place0) (drop hoist0 crate0 surface0 place0)
"""


NUMERIC_FERRY_READABLE_POLICY = """
 precedence : (1, 1, 0, 0)
       vars : car0 location0
     s_cond : (at-ferry location0) (on car0) (>= (ferry-capacity) 1)
     g_cond : (at car0 location0)
    actions : (debark car0 location0)
"""


NUMERIC_MINECRAFT_READABLE_POLICY = """
 precedence : (1, 1, 0, 0)
       vars :
     s_cond : (>= (count_planks_in_inventory) 2) (>= (count_sack_polyisoprene_pellets_in_inventory) 1) (>= (count_stick_in_inventory) 4) (>= (pogo_sticks_to_make) 0) (position crafting_table)
     g_cond : (= (pogo_sticks_to_make__ug) 0)
    actions : (craft_wooden_pogo)
"""


NUMERIC_MINECRAFT_STICK_THEN_POGO_POLICY = """
 precedence : (1, 2, 0, 0)
       vars :
     s_cond : (>= (count_planks_in_inventory) 2) (>= (count_sack_polyisoprene_pellets_in_inventory) 1) (>= (count_stick_in_inventory) 0) (>= (pogo_sticks_to_make) 0) (position crafting_table)
     g_cond : (= (pogo_sticks_to_make__ug) 0)
    actions : (craft_stick) (craft_wooden_pogo)
"""


NUMERIC_MINECRAFT_MOVE_TO_CONSTANT_POLICY = """
 precedence : (1, 4, 0, 0)
       vars : cell0 crafting_table
     s_cond : (>= (count_log_in_inventory) 1) (>= (count_planks_in_inventory) -2) (>= (count_sack_polyisoprene_pellets_in_inventory) 1) (>= (count_stick_in_inventory) 0) (>= (pogo_sticks_to_make) 0) (position cell0)
     g_cond : (= (pogo_sticks_to_make__ug) 0)
    actions : (tp_to cell0 crafting_table) (craft_plank) (craft_stick) (craft_wooden_pogo)
"""


NUMERIC_MINECRAFT_MOVE_TO_VARIABLE_POLICY = """
 precedence : (1, 10, 0, 0)
       vars : cell0 cell1 crafting_table
     s_cond : (>= (count_log_in_inventory) 1) (>= (count_planks_in_inventory) 1) (>= (count_sack_polyisoprene_pellets_in_inventory) 0) (>= (count_stick_in_inventory) 1) (>= (count_tree_tap_in_inventory) 0) (>= (pogo_sticks_to_make) 0) (position cell0) (tree_cell cell1)
     g_cond : (= (pogo_sticks_to_make__ug) 0)
    actions : (tp_to cell0 crafting_table) (craft_plank) (craft_tree_tap) (tp_to crafting_table cell1) (place_tree_tap cell1) (break cell1) (tp_to cell1 crafting_table) (craft_plank) (craft_stick) (craft_wooden_pogo)
"""


NUMERIC_MINECRAFT_THREE_CELL_POLICY = """
 precedence : (1, 15, 0, 0)
       vars : cell0 cell1 cell2 crafting_table
     s_cond : (>= (count_log_in_inventory) 0) (>= (count_planks_in_inventory) -2) (>= (count_sack_polyisoprene_pellets_in_inventory) 0) (>= (count_stick_in_inventory) -3) (>= (count_tree_tap_in_inventory) 0) (>= (pogo_sticks_to_make) 0) (position cell0) (tree_cell cell0) (tree_cell cell1) (tree_cell cell2)
     g_cond : (= (pogo_sticks_to_make__ug) 0)
    actions : (break cell0) (tp_to cell0 cell1) (craft_plank) (craft_stick) (break cell1) (tp_to cell1 crafting_table) (craft_plank) (craft_tree_tap) (tp_to crafting_table cell2) (place_tree_tap cell2) (break cell2) (tp_to cell2 crafting_table) (craft_plank) (craft_stick) (craft_wooden_pogo)
"""


def test_parse_moose_readable_policy_extracts_lifted_rules() -> None:
	rules = parse_moose_readable_policy(FERRY_READABLE_POLICY)

	assert len(rules) == 2
	assert rules[0].variables == ("car0", "location0")
	assert rules[0].goal_conditions[0].predicate == "at"
	assert rules[0].goal_conditions[0].arguments == ("car0", "location0")
	assert rules[1].actions[0].predicate == "board"
	assert rules[1].actions[-1].arguments == ("car0", "location1")


def test_parse_moose_readable_policy_extracts_numeric_conditions() -> None:
	rules = parse_moose_readable_policy(NUMERIC_FERRY_READABLE_POLICY)

	assert len(rules) == 1
	assert rules[0].state_conditions == (
		rules[0].state_conditions[0],
		rules[0].state_conditions[1],
	)
	assert [condition.to_signature() for condition in rules[0].state_numeric_conditions] == [
		"ferry-capacity >= 1",
	]
	assert rules[0].goal_conditions[0].predicate == "at"
	assert rules[0].goal_numeric_conditions == ()


def test_parse_moose_readable_policy_ignores_dump_logs() -> None:
	rules = parse_moose_readable_policy(
		"""
		[INFO t=1.2573s] PLAN OPTIONS:
		model_file          blocks.model
		dump_policy         True
		precedence : (1, 1, 0, 0)
		      vars : block0 block1
		    s_cond : (clear block1) (holding block0)
		    g_cond : (on block0 block1)
		   actions : (stack block0 block1)

		len(policy)=1
		""",
	)

	assert len(rules) == 1
	assert rules[0].goal_conditions[0].predicate == "on"


def test_moose_readable_policy_becomes_lifted_policy_program() -> None:
	program = policy_program_from_moose_readable_policy(
		FERRY_READABLE_POLICY,
		domain_name="ferry",
		source_name="ferry-seed0",
		policy_file=Path("ferry-seed0.model.readable"),
	)

	assert program.backend_name == "moose"
	assert program.representation == "moose_first_order_decision_list"
	assert len(program.rules) == 2
	assert program.modules[0].goal_symbol == "at"
	assert program.rules[0].effects == (
		("primitive_action:debark(Car0, Location0)", "call"),
	)


def test_moose_readable_policy_compiles_to_atomic_asl_library() -> None:
	library = compile_moose_readable_policy_to_asl_library(
		FERRY_READABLE_POLICY,
		domain_name="ferry",
		source_name="ferry-seed0",
	)
	asl = render_plan_library_asl(library)

	assert [plan.trigger.symbol for plan in library.plans] == ["at", "at"]
	assert library.plans[0].trigger.arguments == ("Car0", "Location0")
	assert library.plans[1].context == (
		"at(Car0, Location0)",
		"at-ferry(Location0)",
		"empty-ferry",
	)
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	assert "+!at(Car0, Location1)" in asl
	assert "\tboard(Car0, Location0);" in asl
	assert "\tsail(Location0, Location1);" in asl
	assert "\tdebark(Car0, Location1)." in asl
	assert library.metadata["library_quality"]["artifact_classification"] == (
		"atomic_template_library"
	)
	assert library.metadata["library_quality"]["library_profile"] == (
		"action_only_atomic_template_library"
	)
	assert library.metadata["library_quality"]["plan_template_kind_counts"] == {
		"action_only_plan_template": 2,
	}
	assert library.metadata["library_quality"]["compact_recursive_module_ready"] is False
	assert library.metadata["library_quality"]["faithful_decision_list_ready"] is True


def test_moose_quality_audit_flags_large_raw_macro_policies() -> None:
	library = compile_moose_readable_policy_to_asl_library(
		"\n\n".join(FERRY_READABLE_POLICY.strip() for _ in range(6)),
		domain_name="ferry",
		source_name="oversized",
	)

	report = audit_moose_atomic_library_quality(plans=library.plans)

	assert report.plan_count == 12
	assert report.singleton_macro_library_ready is False
	assert report.compact_recursive_module_ready is False
	assert report.faithful_decision_list_ready is True
	assert report.artifact_classification == "atomic_template_library"
	assert report.library_profile == "action_only_atomic_template_library"
	assert report.plan_template_kind_counts == {"action_only_plan_template": 12}
	assert any("Plan count exceeds" in warning for warning in report.warnings)


def test_moose_readable_policy_compiles_to_minimal_recursive_module_library() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		BLOCKS_READABLE_POLICY,
		domain_file=BLOCKS_DOMAIN,
		domain_name="blocksworld-tower",
		source_name="blocks-seed0",
		policy_file=Path("blocks-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert len(library.plans) >= 17
	assert {plan.trigger.symbol for plan in library.plans} == {
		"clear",
		"handempty",
		"holding",
		"on",
		"ontable",
	}
	assert library.metadata["source_seed_predicates"] == ["on"]
	assert library.metadata["source_raw_rule_count"] == 1
	assert library.metadata["library_quality"]["artifact_classification"] == (
		"atomic_template_library"
	)
	assert library.metadata["library_quality"]["library_profile"] == (
		"mixed_atomic_template_library"
	)
	assert (
		library.metadata["library_quality"]["plan_template_kind_counts"][
			"subgoal_decomposed_plan_template"
		]
		> 0
	)
	selector_report = library.metadata["atomic_module_synthesis"]
	assert selector_report["selector_backend"] == "clingo_asp_minimize"
	assert selector_report["raw_candidate_count"] >= selector_report["plan_count"]
	assert 0 < selector_report["selector_obligation_count"] <= (
		selector_report["raw_candidate_count"]
	)
	assert len(selector_report["selected_branch_ids"]) == selector_report["plan_count"]
	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(X)" in asl
	assert "obj_tp(X, block) & on(Y, X) & obj_tp(Y, block) & not clear(Y)" in asl
	assert "+!clear(X) : obj_tp(X, block) & not handempty" in asl
	assert "\t!handempty;" in asl
	assert "\t!on(Y, X);" not in asl
	assert "+!holding(X) : holding(X)" in asl
	assert "type_" not in asl


def test_evidence_program_decouples_moose_adapter_from_compiler() -> None:
	evidence_program = evidence_program_from_moose_readable_policy(
		BLOCKS_READABLE_POLICY,
		source_name="blocks-seed0",
		policy_file=Path("blocks-seed0.model.readable"),
	)

	library = compile_policy_evidence_program_to_minimal_module_asl_library(
		evidence_program,
		domain_file=BLOCKS_DOMAIN,
		domain_name="blocksworld-tower",
	)

	assert evidence_program.source_provider == "moose"
	assert evidence_program.representation == "moose_readable_first_order_decision_list"
	assert library.metadata["evidence_module"] == {
		"source_provider": "moose",
		"source_name": "blocks-seed0",
		"representation": "moose_readable_first_order_decision_list",
		"policy_file": "blocks-seed0.model.readable",
		"rule_count": 1,
	}
	assert library.metadata["source_seed_predicates"] == ["on"]
	assert library.metadata["atomic_module_synthesis"]["selector_backend"] == (
		"clingo_asp_minimize"
	)
	selector_report = library.metadata["atomic_module_synthesis"]
	assert selector_report["selection_scope"] == (
		"joint_schema_and_validated_evidence_candidates"
	)
	assert selector_report["candidate_source_counts"]["validated_evidence"] == 1
	assert selector_report["evidence_obligation_count"] == 1
	assert library.metadata["validated_policy_lifting"]["selection_stage"] == (
		"joint_clingo_certified_candidate_selection"
	)


def test_evidence_compiler_preserves_validated_logistics_intermodal_macro() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		LOGISTICS_INTERMODAL_READABLE_POLICY,
		domain_file=LOGISTICS_DOMAIN,
		domain_name="logistics",
		source_name="logistics-seed0",
		policy_file=Path("logistics-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert "obj_tp(X, package)" in asl
	assert "obj_tp(Y, location)" in asl
	assert "obj_tp(Z, airplane)" in asl
	assert "obj_tp(D, truck)" in asl
	assert "X \\== Y" not in asl
	assert "\tload_airplane(X, Z, B);" in asl
	assert "\tfly_airplane(Z, B, C);" in asl
	assert "\tunload_airplane(X, Z, C);" in asl
	assert "\tload_truck(X, D, C);" in asl
	assert "\tdrive_truck(D, C, Y, A);" in asl
	assert "\tunload_truck(X, D, Y)." in asl
	assert "type_" not in asl
	assert library.metadata["validated_policy_lifting"]["validated_macro_count"] == 1
	assert library.metadata["validated_policy_lifting"]["invalid_macro_count"] == 0
	assert library.metadata["library_quality"]["artifact_classification"] == (
		"atomic_template_library"
	)
	assert library.metadata["moose_macro_library_quality"]["subgoal_step_count"] == 0
	assert library.metadata["library_quality"]["subgoal_step_count"] > 0
	assert library.metadata["library_quality"]["library_profile"] == (
		"mixed_atomic_template_library"
	)
	first_moose_macro_index = next(
		index
		for index, plan in enumerate(library.plans)
		if plan.plan_name.startswith("moose_reduced_logistics_seed0_rule_")
	)
	first_subgoal_index = next(
		index
		for index, plan in enumerate(library.plans)
		if any(step.kind == "subgoal" for step in plan.body)
	)
	assert first_moose_macro_index < first_subgoal_index
	assert "block0" not in asl


def test_evidence_compiler_adds_positive_precondition_preservation_guards() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		DEPOTS_CLEAR_WITH_PARKING_READABLE_POLICY,
		domain_file=DEPOTS_DOMAIN,
		domain_name="depots",
		source_name="depots-seed0",
		policy_file=Path("depots-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)
	plan = next(
		item for item in library.plans if item.plan_name == "moose_reduced_depots_seed0_rule_1"
	)
	certificate = dict(plan.binding_certificate[0])

	assert "B != Z" in certificate["schema_binding_guards"]
	assert "B \\== Z" in asl
	assert "\tlift(Y, Z, X, A);" in asl
	assert "\tdrop(Y, Z, B, A)." in asl


def test_evidence_compiler_preserves_numeric_macro_contexts() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		NUMERIC_FERRY_READABLE_POLICY,
		domain_file=NUMERIC_FERRY_DOMAIN,
		domain_name="numeric-ferry",
		source_name="numeric-ferry-seed0",
		policy_file=Path("numeric-ferry-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert "ferry_capacity(N)" in asl
	assert "N >= 1" in asl
	assert " & ferry_capacity <-" not in asl
	assert " & ferry_capacity &" not in asl
	assert library.metadata["validated_policy_lifting"]["validated_macro_count"] == 1
	assert library.metadata["validated_policy_lifting"]["invalid_macro_count"] == 0


def test_evidence_compiler_compiles_numeric_resource_goal_module() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		NUMERIC_MINECRAFT_READABLE_POLICY,
		domain_file=NUMERIC_MINECRAFT_DOMAIN,
		domain_name="numeric-minecraft",
		source_name="numeric-minecraft-seed0",
		policy_file=Path("numeric-minecraft-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert "+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N == 0 <-" in asl
	assert "+!pogo_sticks_to_make(0) :" in asl
	assert "pogo_sticks_to_make(N)" in asl
	assert "N > 0" in asl
	assert "count_planks_in_inventory(M)" in asl
	assert "count_planks_in_inventory(N)" not in asl
	assert "count_planks_in_inventory" in asl
	assert "N >= -2" not in asl
	assert "\tcraft_wooden_pogo." in asl
	assert "\t!pogo_sticks_to_make(0)." not in asl
	assert "pogo_sticks_to_make__ug" not in asl
	assert library.metadata["source_seed_predicates"] == []
	assert library.metadata["source_numeric_goal_functions"] == ["pogo_sticks_to_make"]
	assert library.metadata["validated_policy_lifting"]["validated_numeric_macro_count"] == 1
	selector_report = library.metadata["atomic_module_synthesis"]
	assert selector_report["selector_backend"] == "clingo_asp_minimize"
	assert selector_report["selection_scope"] == (
		"joint_schema_and_validated_evidence_candidates"
	)
	assert selector_report["candidate_source_counts"]["validated_evidence"] == 2
	assert selector_report["evidence_obligation_count"] == 2
	assert library.metadata["validated_policy_lifting"]["selection_stage"] == (
		"joint_clingo_certified_candidate_selection"
	)


def test_numeric_macro_contexts_account_for_prior_numeric_effects() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		NUMERIC_MINECRAFT_STICK_THEN_POGO_POLICY,
		domain_file=NUMERIC_MINECRAFT_DOMAIN,
		domain_name="numeric-minecraft",
		source_name="numeric-minecraft-seed0",
		policy_file=Path("numeric-minecraft-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert "count_planks_in_inventory(M)" in asl
	assert "M >= 4" in asl
	assert "count_stick_in_inventory(K)" in asl
	assert "K >= 0" in asl
	assert "\tcraft_stick;" in asl
	assert "\tcraft_wooden_pogo." in asl
	assert library.metadata["validated_policy_lifting"]["validated_numeric_macro_count"] == 1
	assert library.metadata["library_quality"]["library_profile"] == (
		"numeric_resource_atomic_template_library"
	)
	assert library.metadata["library_quality"]["plan_template_kind_counts"] == {
		"numeric_already_true_plan_template": 1,
		"numeric_resource_progress_plan_template": 1,
	}


def test_evidence_compiler_preserves_pddl_constants_in_numeric_macros() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		NUMERIC_MINECRAFT_MOVE_TO_CONSTANT_POLICY,
		domain_file=NUMERIC_MINECRAFT_DOMAIN,
		domain_name="numeric-minecraft",
		source_name="numeric-minecraft-seed0",
		policy_file=Path("numeric-minecraft-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert "\ttp_to(X, crafting_table);" in asl
	assert "obj_tp(crafting_table, cell)" not in asl
	assert "X \\== crafting_table" in asl
	assert "\ttp_to(X, Y);" not in asl
	assert library.metadata["validated_policy_lifting"]["validated_numeric_macro_count"] == 1


def test_evidence_compiler_adds_negative_precondition_binding_guards() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		NUMERIC_MINECRAFT_MOVE_TO_VARIABLE_POLICY,
		domain_file=NUMERIC_MINECRAFT_DOMAIN,
		domain_name="numeric-minecraft",
		source_name="numeric-minecraft-seed0",
		policy_file=Path("numeric-minecraft-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert "\ttp_to(X, crafting_table);" in asl
	assert "\ttp_to(crafting_table, Y);" in asl
	assert "\ttp_to(Y, crafting_table);" in asl
	assert "X \\== crafting_table" in asl
	assert "Y \\== crafting_table" in asl
	assert library.metadata["validated_policy_lifting"]["validated_numeric_macro_count"] == 1


def test_evidence_compiler_emits_only_schema_required_alias_guards() -> None:
	library = compile_moose_readable_policy_to_minimal_module_asl_library(
		NUMERIC_MINECRAFT_THREE_CELL_POLICY,
		domain_file=NUMERIC_MINECRAFT_DOMAIN,
		domain_name="numeric-minecraft",
		source_name="numeric-minecraft-seed0",
		policy_file=Path("numeric-minecraft-seed0.model.readable"),
	)
	asl = render_plan_library_asl(library)

	assert "X \\== Y" in asl
	assert "X \\== Z" in asl
	assert "Y \\== Z" in asl
	assert "X \\== crafting_table" in asl
	assert "Y \\== crafting_table" in asl
	assert "Z \\== crafting_table" in asl
	plan = next(
		item
		for item in library.plans
		if item.plan_name == "moose_numeric_numeric_minecraft_seed0_rule_1"
	)
	certificate = dict(plan.binding_certificate[0])
	assert "evidence_distinctness_guards" not in certificate
	assert certificate["schema_binding_guards"]
	assert library.metadata["validated_policy_lifting"]["validated_numeric_macro_count"] == 1


def test_moose_readable_compile_asl_cli_materializes_atomic_library(
	tmp_path: Path,
) -> None:
	policy_file = tmp_path / "ferry-seed0.model.readable"
	output_dir = tmp_path / "atomic-library"
	policy_file.write_text(FERRY_READABLE_POLICY, encoding="utf-8")

	result = subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "gp_backend_audit.py"),
			"moose-readable-compile-asl",
			"--policy-file",
			str(policy_file),
			"--domain-name",
			"ferry",
			"--output-dir",
			str(output_dir),
		),
		check=True,
		capture_output=True,
		text=True,
	)

	library_json = json.loads(
		(output_dir / "plan_library.json").read_text(encoding="utf-8"),
	)
	metadata = json.loads(
		(output_dir / "atomic_library_metadata.json").read_text(encoding="utf-8"),
	)
	asl = (output_dir / "plan_library.asl").read_text(encoding="utf-8")

	assert "wrote atomic ASL library" in result.stdout
	assert library_json["domain_name"] == "ferry"
	assert len(library_json["plans"]) == 2
	assert metadata["evidence_provider"] == "moose"
	assert metadata["compiled_singleton_rule_count"] == 2
	assert metadata["library_quality"]["artifact_classification"] == (
		"atomic_template_library"
	)
	assert metadata["library_quality"]["library_profile"] == (
		"action_only_atomic_template_library"
	)
	assert "+!at(Car0, Location1)" in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl


def test_moose_readable_compile_asl_cli_materializes_minimal_modules(
	tmp_path: Path,
) -> None:
	policy_file = tmp_path / "blocks-seed0.model.readable"
	output_dir = tmp_path / "minimal-module-library"
	policy_file.write_text(BLOCKS_READABLE_POLICY, encoding="utf-8")

	result = subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "gp_backend_audit.py"),
			"moose-readable-compile-asl",
			"--policy-file",
			str(policy_file),
			"--domain-file",
			str(BLOCKS_DOMAIN),
			"--domain-name",
			"blocksworld-tower",
			"--validated-policy-lifting",
			"--output-dir",
			str(output_dir),
		),
		check=True,
		capture_output=True,
		text=True,
	)

	library_json = json.loads(
		(output_dir / "plan_library.json").read_text(encoding="utf-8"),
	)
	metadata = json.loads(
		(output_dir / "atomic_library_metadata.json").read_text(encoding="utf-8"),
	)
	asl = (output_dir / "plan_library.asl").read_text(encoding="utf-8")

	assert "wrote atomic ASL library" in result.stdout
	assert library_json["domain_name"] == "blocksworld-tower"
	assert len(library_json["plans"]) >= 17
	assert metadata["minimal_modules"] is True
	assert metadata["validated_policy_lifting"] is True
	assert metadata["source_raw_rule_count"] == 1
	assert metadata["library_quality"]["artifact_classification"] == (
		"atomic_template_library"
	)
	assert metadata["library_quality"]["library_profile"] == (
		"mixed_atomic_template_library"
	)
	assert metadata["atomic_module_synthesis"]["selector_backend"] == "clingo_asp_minimize"
	assert 0 < metadata["atomic_module_synthesis"]["selector_obligation_count"] <= (
		metadata["atomic_module_synthesis"]["raw_candidate_count"]
	)
	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(X)" in asl
	assert "+!clear(X) : obj_tp(X, block) & not handempty" in asl
	assert "+!holding(X) : holding(X)" in asl
	assert "type_" not in asl
