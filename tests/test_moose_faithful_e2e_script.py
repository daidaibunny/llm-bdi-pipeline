from __future__ import annotations

import json
from pathlib import Path

from scripts.run_moose_faithful_e2e import first_n_test_instances
from scripts.run_moose_faithful_e2e import append_problem_goal_wrappers_to_library
from scripts.run_moose_faithful_e2e import compile_moose_atomic_library_command
from scripts.run_moose_faithful_e2e import materialize_moose_compatible_pddl
from scripts.run_moose_faithful_e2e import moose_policy_command
from scripts.run_moose_faithful_e2e import moose_train_command
from scripts.run_moose_faithful_e2e import natural_sort_key
from scripts.run_moose_faithful_e2e import normalise_pddl_for_moose
from scripts.run_moose_faithful_e2e import selected_query_append_mode
from scripts.run_moose_faithful_e2e import sequential_eventually_formula
from scripts.run_moose_faithful_e2e import write_test_goal_dataset
from scripts.run_timestamped_moose_asl_batch import batch_manifest
from scripts.run_timestamped_moose_asl_batch import build_moose_batch_command
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary


def test_natural_sort_selects_first_split_instances(tmp_path: Path) -> None:
	for filename in ("instance-100.pddl", "instance-69.pddl", "instance-70.pddl"):
		(tmp_path / filename).write_text("(define (problem p))", encoding="utf-8")

	selected = first_n_test_instances(tmp_path, count=2)

	assert [path.name for path in selected] == ["instance-69.pddl", "instance-70.pddl"]
	assert sorted(tmp_path.glob("*.pddl"), key=natural_sort_key)[-1].name == "instance-100.pddl"


def test_sequential_eventually_formula_has_singleton_progress_atoms() -> None:
	formula = sequential_eventually_formula(("on(a,b)", "on(b,c)", "clear(a)"))

	assert formula == "F(on(a,b) & X(F(on(b,c) & X(F(clear(a))))))"
	assert " & X(" in formula


def test_write_test_goal_dataset_uses_grounded_problem_goals(tmp_path: Path) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain blocks)
		 (:objects a b c)
		 (:init)
		 (:goal (and (on a b) (on b c)))
		)
		""",
		encoding="utf-8",
	)
	output_file = tmp_path / "goals.json"

	write_test_goal_dataset(
		domain_name="blocksworld-tower",
		problem_files=(problem_file,),
		output_file=output_file,
	)

	payload = json.loads(output_file.read_text(encoding="utf-8"))
	case = payload["cases"]["query_1"]

	assert payload["domain"] == "blocksworld-tower"
	assert case["goal_name"] == "g_blocksworld_tower_test_1"
	assert case["ltlf_formula"] == "F(on(a,b) & X(F(on(b,c))))"
	assert case["atoms"] == ["on(a,b)", "on(b,c)"]


def test_selected_query_append_mode_detects_numeric_problem_goals(tmp_path: Path) -> None:
	problem_file = tmp_path / "numeric.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain numeric-minecraft)
		 (:objects)
		 (:init (= (pogo_sticks_to_make) 2))
		 (:goal (= (pogo_sticks_to_make) 0))
		)
		""",
		encoding="utf-8",
	)

	mode = selected_query_append_mode((problem_file,))

	assert mode == "evaluation_pddl_goal_wrapper_bridge"


def test_append_problem_goal_wrappers_handles_numeric_only_goal(tmp_path: Path) -> None:
	library_root = tmp_path / "libraries"
	library_dir = library_root / "numeric-minecraft"
	library_dir.mkdir(parents=True)
	base_library = PlanLibrary(
		domain_name="numeric-minecraft",
		plans=(
			AgentSpeakPlan(
				plan_name="pogo_already_target_0",
				trigger=AgentSpeakTrigger(
					"achievement_goal",
					"pogo_sticks_to_make",
					("0",),
				),
				context=("pogo_sticks_to_make(N)", "N == 0"),
				body=(),
			),
			AgentSpeakPlan(
				plan_name="pogo_via_craft",
				trigger=AgentSpeakTrigger(
					"achievement_goal",
					"pogo_sticks_to_make",
					("0",),
				),
				context=("pogo_sticks_to_make(N)", "N > 0"),
				body=(
					AgentSpeakBodyStep("action", "craft_wooden_pogo"),
					AgentSpeakBodyStep("subgoal", "pogo_sticks_to_make", ("0",)),
				),
			),
		),
	)
	(library_dir / "plan_library.json").write_text(
		json.dumps(base_library.to_dict(), indent=2) + "\n",
		encoding="utf-8",
	)
	(library_dir / "artifact_metadata.json").write_text("{}\n", encoding="utf-8")
	problem_file = tmp_path / "numeric.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain numeric-minecraft)
		 (:objects)
		 (:init (= (pogo_sticks_to_make) 2))
		 (:goal (= (pogo_sticks_to_make) 0))
		)
		""",
		encoding="utf-8",
	)

	result = append_problem_goal_wrappers_to_library(
		domain_name="numeric-minecraft",
		problem_files=(problem_file,),
		library_root=library_root,
	)

	asl = (library_dir / "plan_library.asl").read_text(encoding="utf-8")
	payload = json.loads((library_dir / "plan_library.json").read_text(encoding="utf-8"))

	assert result["success"] is True
	assert result["mode"] == "evaluation_pddl_goal_wrapper_bridge"
	assert "numeric_minecraft_test_1." in asl
	assert "+!g_numeric_minecraft_test_1 : numeric_minecraft_test_1 <-" in asl
	assert "\t!g_numeric_minecraft_test_1_trans_1." in asl
	assert "\t!pogo_sticks_to_make(0);" in asl
	assert payload["initial_beliefs"] == ["numeric_minecraft_test_1"]
	assert (
		payload["metadata"]["evaluation_pddl_goal_wrapper_bridge"]["final_query_contract"]
		== "validated_lifted_ltlf_json_to_ltlf2dfa_to_guard_transition_append"
	)
	assert (
		payload["plans"][-1]["binding_certificate"][0]["artifact_family"]
		== "temporal_goal_dfa_append"
	)


def test_moose_train_command_uses_full_train_split(tmp_path: Path) -> None:
	command = moose_train_command(
		domain_file=tmp_path / "domain.pddl",
		train_dir=tmp_path / "train",
		model_file=tmp_path / "domain.model",
		random_seed=7,
		num_workers=8,
		num_permutations=3,
		goal_max_size=1,
		runtime="local",
	)

	assert str(tmp_path / "train") in command
	assert "--num-training" in command
	assert command[command.index("--num-training") + 1] == "-1"
	assert "--num-validation" in command
	assert command[command.index("--num-validation") + 1] == "-1"
	assert "--goal-max-size" in command
	assert command[command.index("--goal-max-size") + 1] == "1"


def test_moose_train_command_wraps_docker_exact_runtime() -> None:
	project_domain = Path.cwd() / "src" / "domains" / "ferry" / "domain.pddl"
	project_train = Path.cwd() / "src" / "domains" / "ferry" / "train"
	project_model = Path.cwd() / "tmp" / "model.model"

	command = moose_train_command(
		domain_file=project_domain,
		train_dir=project_train,
		model_file=project_model,
		random_seed=0,
		num_workers=8,
		num_permutations=3,
		goal_max_size=1,
		runtime="docker",
		max_rss_gb=16,
	)

	assert command[:2] == ("docker", "run")
	assert "--memory=16g" in command
	assert "moose-exact-ubuntu22:local" in command
	assert "/project/src/domains/ferry/domain.pddl" in command[-1]
	assert "/project/src/domains/ferry/train" in command[-1]


def test_moose_policy_command_docker_runtime_does_not_need_local_scorpion() -> None:
	project_model = Path.cwd() / "tmp" / "model.model"
	project_domain = Path.cwd() / "tmp" / "moose_compatible_pddl" / "domain.pddl"
	project_problem = Path.cwd() / "tmp" / "moose_compatible_pddl" / "test" / "p01.pddl"
	project_plan = Path.cwd() / "tmp" / "policy.plan"

	command = moose_policy_command(
		model_file=project_model,
		domain_file=project_domain,
		problem_file=project_problem,
		plan_file=project_plan,
		bound=5000,
		runtime="docker",
		max_rss_gb=16,
	)

	command_text = " ".join(command)

	assert "/work/moose.sif" in command_text
	assert ".external/moose/ext/planners/scorpion/scorpion.sif" not in command_text
	assert "/project/tmp/moose_compatible_pddl/domain.pddl" in command_text
	assert "/project/tmp/moose_compatible_pddl/test/p01.pddl" in command_text


def test_timestamped_batch_command_generates_isolated_library_root(
	tmp_path: Path,
) -> None:
	class Args:
		num_workers = 4
		num_permutations = 3
		goal_max_size = 1
		atomic_library_mode = "faithful"
		max_rss_gb = 16
		train_timeout_seconds = 1800
		dump_timeout_seconds = 300
		append_timeout_seconds = 300
		jason_timeout_seconds = 90
		moose_plan_timeout_seconds = 120
		moose_plan_bound = 5000
		run_jason_validation = False
		run_moose_policy_validation = False
		skip_temporal_append = False

	batch_root = tmp_path / "20260704-101112"
	command = build_moose_batch_command(
		args=Args(),
		domains=("blocksworld-clear", "depots"),
		batch_root=batch_root,
	)
	manifest = batch_manifest(
		args=Args(),
		domains=("blocksworld-clear", "depots"),
		timestamp_id="20260704-101112",
		batch_root=batch_root,
		command=command,
	)

	command_text = " ".join(command)

	assert "--num-workers 4" in command_text
	assert "--atomic-library-mode faithful" in command_text
	assert "--skip-jason-validation" in command
	assert "--skip-moose-policy-validation" in command
	assert str(batch_root / "domain_libraries") in command
	assert manifest["settings"]["temporal_append_in_stage1"] is True
	assert manifest["settings"]["test_query_count_per_domain"] == 2
	assert manifest["expected_asl_files"] == [
		str(batch_root / "domain_libraries" / "blocksworld-clear" / "plan_library.asl"),
		str(batch_root / "domain_libraries" / "depots" / "plan_library.asl"),
	]
	assert manifest["settings"]["domain_execution"] == "sequential"
	assert manifest["settings"]["atomic_library_backend"] == "native_moose_train_dump_policy"


def test_validated_policy_lifting_batch_mode_is_explicitly_threaded(
	tmp_path: Path,
) -> None:
	class Args:
		num_workers = 4
		num_permutations = 3
		goal_max_size = 1
		atomic_library_mode = "validated-policy-lifting"
		max_rss_gb = 16
		train_timeout_seconds = 1800
		dump_timeout_seconds = 300
		append_timeout_seconds = 300
		jason_timeout_seconds = 90
		moose_plan_timeout_seconds = 120
		moose_plan_bound = 5000
		run_jason_validation = False
		run_moose_policy_validation = False
		skip_temporal_append = False

	batch_root = tmp_path / "20260704-101113"
	command = build_moose_batch_command(
		args=Args(),
		domains=("blocksworld-tower",),
		batch_root=batch_root,
	)
	manifest = batch_manifest(
		args=Args(),
		domains=("blocksworld-tower",),
		timestamp_id="20260704-101113",
		batch_root=batch_root,
		command=command,
	)

	command_text = " ".join(command)

	assert "--atomic-library-mode validated-policy-lifting" in command_text
	assert manifest["settings"]["atomic_library_mode"] == "validated-policy-lifting"
	assert manifest["settings"]["atomic_library_backend"] == (
		"validated_policy_lifting_and_asl_compilation"
	)


def test_timestamped_batch_can_generate_atomic_libraries_without_first2_append(
	tmp_path: Path,
) -> None:
	class Args:
		num_workers = 4
		num_permutations = 3
		goal_max_size = 1
		atomic_library_mode = "validated-policy-lifting"
		max_rss_gb = 16
		train_timeout_seconds = 1800
		dump_timeout_seconds = 300
		append_timeout_seconds = 300
		jason_timeout_seconds = 90
		moose_plan_timeout_seconds = 120
		moose_plan_bound = 5000
		run_jason_validation = False
		run_moose_policy_validation = False
		skip_temporal_append = True

	batch_root = tmp_path / "20260706-101113"
	command = build_moose_batch_command(
		args=Args(),
		domains=("logistics",),
		batch_root=batch_root,
	)
	manifest = batch_manifest(
		args=Args(),
		domains=("logistics",),
		timestamp_id="20260706-101113",
		batch_root=batch_root,
		command=command,
	)

	assert "--skip-temporal-append" in command
	assert manifest["settings"]["temporal_append_in_stage1"] is False
	assert manifest["settings"]["test_query_count_per_domain"] == 0


def test_validated_policy_lifting_compile_command_uses_semantic_cli_flag(
	tmp_path: Path,
) -> None:
	command = compile_moose_atomic_library_command(
		readable_policy_file=tmp_path / "blocks.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain_name="blocksworld-tower",
		library_root=tmp_path / "libraries",
		atomic_library_mode="validated-policy-lifting",
	)

	assert "--validated-policy-lifting" in command
	assert "--minimal-modules" not in command


def test_normalise_pddl_for_moose_lowercases_keywords_and_adds_typing() -> None:
	text = """
	(DEFINE (DOMAIN SAMPLE)
	 (:requirements :strips)
	 (:TYPES block)
	 (:predicates (clear ?x - block))
	)
	"""

	normalised = normalise_pddl_for_moose(text)

	assert "(define (domain sample)" in normalised
	assert "(:types block)" in normalised
	assert ":typing" in normalised


def test_materialize_moose_compatible_pddl_normalizes_blocks_style_init(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	train_dir = tmp_path / "train"
	test_file = tmp_path / "test.pddl"
	output_root = tmp_path / "compat"
	train_dir.mkdir()
	domain_file.write_text(
		"""
		(DEFINE (DOMAIN BLOCKS)
		 (:requirements :strips :typing)
		 (:types block)
		 (:predicates (clear ?x - block))
		)
		""",
		encoding="utf-8",
	)
	(train_dir / "instance-1.pddl").write_text(
		"""
		(define (problem BLOCKS-4-0)
		 (:domain BLOCKS)
		 (:objects A B - block)
		 (:INIT (CLEAR A) (CLEAR B))
		 (:goal (AND (CLEAR A)))
		)
		""",
		encoding="utf-8",
	)
	test_file.write_text(
		"""
		(define (problem BLOCKS-4-1)
		 (:domain BLOCKS)
		 (:objects A B - block)
		 (:INIT (CLEAR A) (CLEAR B))
		 (:goal (AND (CLEAR B)))
		)
		""",
		encoding="utf-8",
	)

	compat = materialize_moose_compatible_pddl(
		domain_file=domain_file,
		train_dir=train_dir,
		test_instances=(test_file,),
		output_root=output_root,
	)

	train_text = (output_root / "train" / "instance-1.pddl").read_text(
		encoding="utf-8",
	)
	test_text = (output_root / "test" / "test.pddl").read_text(encoding="utf-8")

	assert compat["domain_file"] == str(output_root / "domain.pddl")
	assert compat["train_count"] == 1
	assert "(:init" in train_text
	assert "(:goal (and" in train_text
	assert ":INIT" not in train_text
	assert "(clear a)" in train_text
	assert "(:init" in test_text
	assert ":INIT" not in test_text
