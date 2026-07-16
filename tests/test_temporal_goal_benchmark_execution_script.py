from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from domain_level_planning import AtomicCompilerVariant
from domain_level_planning import TemporalCompilerVariant
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from scripts.run_controller_structure_smoke_ablation import _paired_trace_equivalent
from scripts.run_temporal_goal_benchmark_execution import (
	benchmark_prediction,
)
from scripts.run_temporal_goal_benchmark_execution import controller_structure_metrics
from scripts.run_temporal_goal_benchmark_execution import execution_status
from scripts.run_temporal_goal_benchmark_execution import load_completed_records
from scripts.run_temporal_goal_benchmark_execution import summarize_execution_records
from scripts.run_temporal_goal_benchmark_execution import TemporalExecutionTask
from scripts.run_temporal_goal_benchmark_execution import (
	temporal_execution_input_fingerprint,
)
from scripts.run_temporal_goal_benchmark_execution import verify_invocation_binding


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_shell_entrypoint_accepts_no_domain_arguments_on_bash_3(
	tmp_path: Path,
) -> None:
	bin_dir = tmp_path / "bin"
	bin_dir.mkdir()
	capture_file = tmp_path / "uv-arguments.txt"
	fake_uv = bin_dir / "uv"
	fake_uv.write_text(
		'#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$CAPTURE_FILE"\n',
		encoding="utf-8",
	)
	fake_uv.chmod(0o755)
	fake_mona = bin_dir / "mona"
	fake_mona.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
	fake_mona.chmod(0o755)
	environment = {
		**os.environ,
		"PATH": f"{bin_dir}:{os.environ['PATH']}",
		"CAPTURE_FILE": str(capture_file),
		"MONA_BIN": str(fake_mona),
		"RUN_ID": "shell-no-domain-test",
	}

	completed = subprocess.run(
		("bash", "scripts/run_temporal_goal_benchmark_execution.sh"),
		cwd=PROJECT_ROOT,
		env=environment,
		capture_output=True,
		text=True,
		check=False,
	)

	assert completed.returncode == 0, completed.stderr
	arguments = capture_file.read_text(encoding="utf-8").splitlines()
	assert arguments[:3] == [
		"run",
		"python",
		"scripts/run_temporal_goal_benchmark_execution.py",
	]
	assert "--domain" not in arguments
	assert arguments[arguments.index("--temporal-compiler-variant") + 1] == (
		"certified_balanced"
	)


def test_registered_experiment_variants_have_short_report_names() -> None:
	assert [variant.display_name for variant in AtomicCompilerVariant] == [
		"Evidence Only",
		"Direct Producers",
		"Maximum Feasible",
		"Full GP2PL",
	]


def test_temporal_resume_requires_exact_case_inputs(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	library_json = tmp_path / "plan_library.json"
	library_asl = tmp_path / "plan_library.asl"
	domain_file.write_text("domain", encoding="utf-8")
	problem_file.write_text("problem", encoding="utf-8")
	library_json.write_text("{}", encoding="utf-8")
	library_asl.write_text("query.", encoding="utf-8")
	goal_case = SimpleNamespace(to_dict=lambda: {"goal_name": "g_query"})
	task = TemporalExecutionTask(
		domain="tiny",
		sample_id="tiny__p01__ordered_two",
		profile="ordered_two",
		domain_file=domain_file,
		problem_file=problem_file,
		plan_library_json=library_json,
		plan_library_asl=library_asl,
		goal_case=goal_case,
		benchmark_case={"problem_file": "problem.pddl"},
		audit_row={"binding": {"X": "a"}},
		output_dir=tmp_path / "case",
	)
	task.output_dir.mkdir()
	variant = TemporalCompilerVariant.CERTIFIED_BALANCED
	fingerprint = temporal_execution_input_fingerprint(
		task,
		compiler_variant=variant,
	)
	(task.output_dir / "result.json").write_text(
		json.dumps(
			{
				"sample_id": task.sample_id,
				"status": "success",
				"input_fingerprint": fingerprint,
			},
		),
		encoding="utf-8",
	)

	completed = load_completed_records((task,), compiler_variant=variant)
	assert tuple(completed) == (task.sample_id,)

	library_asl.write_text("changed.", encoding="utf-8")
	assert load_completed_records((task,), compiler_variant=variant) == {}


def test_controller_structure_metrics_excludes_support_helper_plan_fanout() -> None:
	base_plan = AgentSpeakPlan(
		"done_via_finish",
		AgentSpeakTrigger("achievement_goal", "done", ("X",)),
		("ready(X)",),
		(AgentSpeakBodyStep("action", "finish", ("X",)),),
	)
	query_plans = (
		AgentSpeakPlan(
			"g_query_trans",
			AgentSpeakTrigger("achievement_goal", "g_query_trans", ()),
			("query",),
			(AgentSpeakBodyStep("subgoal", "g_query_left", ()),),
			binding_certificate=({"wrapper_role": "transition_flat_repair"},),
		),
		AgentSpeakPlan(
			"g_query_trans_done",
			AgentSpeakTrigger("achievement_goal", "g_query_trans", ()),
			("query", "done(a)"),
			(),
			binding_certificate=({"wrapper_role": "transition_flat_done"},),
		),
		*(
			AgentSpeakPlan(
				f"g_query_support_{index}",
				AgentSpeakTrigger("achievement_goal", "g_query_support", ()),
				("query",),
				(AgentSpeakBodyStep("action", f"support_{index}", ()),),
				binding_certificate=({"wrapper_role": "preservation_support"},),
			)
			for index in range(3)
		),
	)
	base = PlanLibrary(domain_name="tiny", plans=(base_plan,))
	updated = PlanLibrary(domain_name="tiny", plans=(base_plan, *query_plans))

	metrics = controller_structure_metrics(base, updated)

	assert metrics["controller_plan_count"] == 5
	assert metrics["max_trigger_fanout"] == 2
	assert metrics["controller_context_literal_count"] == 6
	assert metrics["controller_body_step_count"] == 4
	assert metrics["max_controller_body_steps"] == 1
	assert metrics["controller_asl_bytes"] > 0
	assert [variant.display_name for variant in TemporalCompilerVariant] == [
		"Unprotected Serialization",
		"Certified Flat",
		"Certified Linear",
		"Certified Balanced",
		"Module-Return Monitor",
	]


def test_controller_smoke_requires_cross_variant_trace_equivalence() -> None:
	records = [
		{
			"size": 32,
			"repeat": 1,
			"variant": variant.value,
			"action_count": 32,
			"trace_sha256": "same-trace",
		}
		for variant in (
			TemporalCompilerVariant.CERTIFIED_FLAT,
			TemporalCompilerVariant.CERTIFIED_LINEAR,
			TemporalCompilerVariant.CERTIFIED_BALANCED,
		)
	]

	assert _paired_trace_equivalent(records) is True
	records[-1]["trace_sha256"] = "different-trace"
	assert _paired_trace_equivalent(records) is False


def test_benchmark_prediction_preserves_predicate_and_numeric_atoms() -> None:
	prediction = benchmark_prediction(
		"numeric_ferry_p0_03",
		{
			"ltlf_formula": "F(a0 & X(F(a1)))",
			"atoms": [
				{
					"symbol": "a0",
					"kind": "predicate",
					"predicate": "at-ferry",
					"args": ["X"],
				},
				{
					"symbol": "a1",
					"kind": "numeric_equality",
					"function": "ferry-capacity",
					"args": [],
					"value": 3,
				},
			],
			"declared_parameters": [{"name": "X", "pddl_type": "location"}],
			"constraints": [],
		},
	)

	assert prediction.sample_id == "numeric_ferry_p0_03"
	assert prediction.atoms[0].semantic_key == (
		"predicate",
		"at-ferry",
		("X",),
		None,
	)
	assert prediction.atoms[1].semantic_key == (
		"numeric_equality",
		"ferry-capacity",
		(),
		3,
	)


def test_verify_invocation_binding_rejects_release_audit_mismatch() -> None:
	with pytest.raises(ValueError, match="invocation binding differs"):
		verify_invocation_binding(
			sample_id="tiny_p01",
			benchmark_case={"bindings": {"X": "a"}},
			audit_row={"assignment": {"X": "b"}},
		)


def test_summarize_execution_records_keeps_failure_stages_distinct() -> None:
	summary = summarize_execution_records(
		(
			{
				"domain": "tiny",
				"profile": "ordered_two_milestone",
				"status": "success",
				"success": True,
			},
			{
				"domain": "tiny",
				"profile": "persistence_until",
				"status": "unsupported_temporal_controller",
				"success": False,
			},
			{
				"domain": "other",
				"profile": "ordered_two_milestone",
				"status": "jason_timeout",
				"success": False,
			},
		),
	)

	assert summary["total"] == 3
	assert summary["success_count"] == 1
	assert summary["status_counts"] == {
		"jason_timeout": 1,
		"success": 1,
		"unsupported_temporal_controller": 1,
	}
	assert summary["domains"]["tiny"]["success_count"] == 1
	assert summary["profiles"]["persistence_until"]["success_count"] == 0


def test_execution_status_accepts_only_certified_zero_action_without_val() -> None:
	payload = {
		"replay_valid": True,
		"val_attempted": False,
		"val_success": None,
		"gold_accepted": True,
		"prediction_accepted": True,
		"action_count": 0,
		"state_count": 1,
		"legality_certificate": "vacuous_zero_action_pddl_replay",
	}

	assert execution_status(payload) == "success"
	assert execution_status({**payload, "action_count": 1}) == "val_unavailable"
	assert execution_status({**payload, "state_count": 2}) == "val_unavailable"
