from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning import AtomicCompilerVariant
from domain_level_planning import TemporalCompilerVariant
from scripts.run_paired_compiler_experiments import build_atomic_run_command
from scripts.run_paired_compiler_experiments import build_evidence_run_command
from scripts.run_paired_compiler_experiments import build_temporal_run_command
from scripts.run_paired_compiler_experiments import atomic_library_metrics
from scripts.run_paired_compiler_experiments import execution_metrics
from scripts.run_paired_compiler_experiments import pairing_outcome
from scripts.run_paired_compiler_experiments import parse_seed_batch_assignments
from scripts.run_paired_compiler_experiments import validate_atomic_pairing
from scripts.run_paired_compiler_experiments import validate_temporal_pairing


def test_parse_seed_batch_assignments_requires_unique_integer_seeds() -> None:
	assert parse_seed_batch_assignments(("0=batch-a", "4=batch-e")) == {
		0: "batch-a",
		4: "batch-e",
	}
	with pytest.raises(ValueError, match="duplicate seed"):
		parse_seed_batch_assignments(("0=batch-a", "0=batch-b"))
	with pytest.raises(ValueError, match="SEED=BATCH_ID"):
		parse_seed_batch_assignments(("batch-a",))


def test_atomic_command_selects_exact_registered_variant(tmp_path: Path) -> None:
	command = build_atomic_run_command(
		project_root=tmp_path,
		batch_root=tmp_path / "batches",
		batch_id="seed-zero",
		output_root=tmp_path / "outputs",
		run_id="paper-seed0-evidence-adapter",
		variant=AtomicCompilerVariant.VALIDATED_EVIDENCE_ADAPTER,
		domains=("ferry", "gripper"),
		num_workers=6,
		timeout_seconds=1800,
		java_stack_size="64m",
		plan_verifier_command="Validate {domain} {problem} {plan}",
	)

	assert command[0:2] == ("uv", "run")
	assert command[command.index("--compiler-variant") + 1] == (
		"validated_evidence_adapter"
	)
	assert command.count("--domain") == 2
	assert "--suppress-final-summary-json" in command


def test_evidence_command_uses_one_internal_worker_and_isolated_seed(tmp_path: Path) -> None:
	command = build_evidence_run_command(
		project_root=tmp_path,
		batch_root=tmp_path / "batches",
		batch_id="paper-seed3",
		seed=3,
		domains=("ferry",),
	)

	assert command[command.index("--num-workers") + 1] == "1"
	assert command[command.index("--random-seed") + 1] == "3"
	assert command[command.index("--train-timeout-seconds") + 1] == "43200"
	assert "--skip-temporal-append" in command


def test_temporal_command_selects_exact_registered_variant(tmp_path: Path) -> None:
	command = build_temporal_run_command(
		project_root=tmp_path,
		benchmark_root=tmp_path / "benchmark",
		batch_root=tmp_path / "batches",
		batch_id="full-atomic",
		output_root=tmp_path / "outputs",
		run_id="paper-completion-monitor",
		variant=TemporalCompilerVariant.COMPLETION_BOUNDARY_MONITOR,
		domains=("ferry",),
		num_workers=6,
		timeout_seconds=1800,
		java_stack_size="64m",
		plan_verifier_command="Validate {domain} {problem} {plan}",
	)

	assert command[command.index("--temporal-compiler-variant") + 1] == (
		"completion_boundary_monitor"
	)
	assert command[command.index("--benchmark-root") + 1] == str(
		tmp_path / "benchmark",
	)


def test_atomic_pairing_checks_readable_and_normalized_evidence_hashes() -> None:
	runs = (
		{
			"seed": 0,
			"variant": "validated_evidence_adapter",
			"domains": {
				"ferry": {
					"readable_policy_sha256": "raw",
					"evidence_program_fingerprint": "normalized",
				},
			},
		},
		{
			"seed": 0,
			"variant": "action_only_closure",
			"domains": {
				"ferry": {
					"readable_policy_sha256": "raw",
					"evidence_program_fingerprint": "normalized",
				},
			},
		},
		{
			"seed": 0,
			"variant": "maximal_certified_program",
			"domains": {
				"ferry": {
					"readable_policy_sha256": "raw",
					"evidence_program_fingerprint": "normalized",
				},
			},
		},
		{
			"seed": 0,
			"variant": "full",
			"domains": {
				"ferry": {
					"readable_policy_sha256": "raw",
					"evidence_program_fingerprint": "normalized",
				},
			},
		},
	)

	assert validate_atomic_pairing(runs)["paired"] is True
	with pytest.raises(ValueError, match="normalized evidence fingerprint"):
		validate_atomic_pairing(
			(
				*runs[:-1],
				{
					**runs[-1],
					"domains": {
						"ferry": {
							"readable_policy_sha256": "raw",
							"evidence_program_fingerprint": "different",
						},
					},
				},
			),
		)
	with pytest.raises(ValueError, match="normalized evidence fingerprint"):
		validate_atomic_pairing(
			(
				*runs[:-1],
				{
					**runs[-1],
					"domains": {
						"ferry": {
							"readable_policy_sha256": "raw",
							"evidence_program_fingerprint": None,
						},
					},
				},
			),
		)


def test_temporal_pairing_checks_benchmark_library_and_dfa_hashes() -> None:
	base = {
		"variant": "certified_flat",
		"benchmark_sha256": "benchmark",
		"atomic_library_inputs": {
			"ferry": {
				"plan_library_json_sha256": "library",
				"plan_library_asl_sha256": "asl",
			},
		},
		"results": [
			{
				"sample_id": "ferry-1",
				"dfa_fingerprint": "dfa",
			},
		],
	}
	other_runs = (
		{**base, "variant": "dfa_aware_unprotected"},
		base,
		{**base, "variant": "certified_balanced"},
		{**base, "variant": "completion_boundary_monitor"},
	)

	assert validate_temporal_pairing(other_runs)["paired"] is True
	with pytest.raises(ValueError, match="DFA fingerprint"):
		validate_temporal_pairing(
			(
				*other_runs[:-1],
				{
					**other_runs[-1],
					"results": [
						{"sample_id": "ferry-1", "dfa_fingerprint": "different"},
					],
				},
			),
		)
	with pytest.raises(ValueError, match="sample matrix incomplete"):
		validate_temporal_pairing(
			(
				*other_runs[:-1],
				{
					**other_runs[-1],
					"results": [],
				},
			),
		)
	with pytest.raises(ValueError, match="missing DFA fingerprint"):
		validate_temporal_pairing(
			(
				*other_runs[:-1],
				{
					**other_runs[-1],
					"results": [
						{"sample_id": "ferry-1", "dfa_fingerprint": None},
					],
				},
			),
		)


def test_pairing_outcome_persists_incomplete_matrix_as_infrastructure_failure() -> None:
	def reject(_runs: object) -> dict[str, object]:
		raise ValueError("controlled hash mismatch")

	outcome, failure = pairing_outcome(
		label="Atomic",
		runs=({"variant": "full"},),
		validator=reject,
	)

	assert outcome == {
		"paired": False,
		"error": "controlled hash mismatch",
	}
	assert failure == {
		"stage": "Pairing",
		"method": "Atomic",
		"error": "controlled hash mismatch",
	}


def test_atomic_library_metrics_are_table_ready(tmp_path: Path) -> None:
	library_file = tmp_path / "plan_library.json"
	asl_file = tmp_path / "plan_library.asl"
	library_file.write_text(
		"""
{
  "plans": [
    {"context": ["ready(X)"], "body": []},
    {
      "context": ["not ready(X)", "obj_tp(X, item)"],
      "body": [{"kind": "subgoal"}, {"kind": "action"}]
    }
  ],
  "metadata": {
    "atomic_module_synthesis": {
      "raw_candidate_count": 5,
      "candidate_source_counts": {
        "validated_evidence": 2,
        "schema": 4
      },
      "module_predicates": ["done"],
      "predicate_roles": [
        {
          "role": "producible_fluent",
          "expected_module": true,
          "emitted_module": true
        }
      ]
    }
  }
}
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	asl_file.write_text("+!done(X) : ready(X) <- true.\n", encoding="utf-8")

	metrics = atomic_library_metrics(library_file, asl_file)

	assert metrics == {
		"candidate_count": 5,
		"evidence_candidate_count": 2,
		"schema_candidate_count": 4,
		"selected_branch_count": 2,
		"module_count": 1,
		"producible_target_count": 1,
		"covered_target_count": 1,
		"module_closure_complete": True,
		"context_literal_count": 3,
		"body_step_count": 2,
		"primitive_action_step_count": 1,
		"subgoal_step_count": 1,
		"asl_bytes": 30,
	}


def test_execution_metrics_use_par2_for_every_unsolved_case() -> None:
	metrics = execution_metrics(
		(
			{
				"success": True,
				"plan_verifier_success": True,
				"duration_seconds": 4.0,
				"action_count": 3,
				"status": "success",
			},
			{
				"success": False,
				"timed_out": False,
				"duration_seconds": 2.0,
				"status": "failed",
			},
		),
		timeout_seconds=10,
	)

	assert metrics["success_count"] == 1
	assert metrics["valid_trace_count"] == 1
	assert metrics["par2_seconds"] == 12.0
	assert metrics["median_action_count"] == 3
