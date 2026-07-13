from __future__ import annotations

import json
from pathlib import Path

import pytest

from domain_level_planning import AtomicCompilerVariant
from domain_level_planning import TemporalCompilerVariant
from scripts.run_paired_compiler_experiments import build_atomic_run_command
from scripts.run_paired_compiler_experiments import build_evidence_run_command
from scripts.run_paired_compiler_experiments import build_registered_case_contract
from scripts.run_paired_compiler_experiments import build_temporal_run_command
from scripts.run_paired_compiler_experiments import RegisteredRun
from scripts.run_paired_compiler_experiments import registered_run_summary_complete
from scripts.run_paired_compiler_experiments import apply_common_target_coverage
from scripts.run_paired_compiler_experiments import atomic_library_metrics
from scripts.run_paired_compiler_experiments import execution_metrics
from scripts.run_paired_compiler_experiments import pairing_outcome
from scripts.run_paired_compiler_experiments import parse_seed_batch_assignments
from scripts.run_paired_compiler_experiments import resolve_temporal_atomic_input
from scripts.run_paired_compiler_experiments import validate_atomic_pairing
from scripts.run_paired_compiler_experiments import validate_seed_batch_manifest
from scripts.run_paired_compiler_experiments import validate_temporal_pairing
from scripts.run_paired_compiler_experiments import validate_resume_manifest


def test_parse_seed_batch_assignments_requires_unique_integer_seeds() -> None:
	assert parse_seed_batch_assignments(("0=batch-a", "4=batch-e")) == {
		0: "batch-a",
		4: "batch-e",
	}
	with pytest.raises(ValueError, match="duplicate seed"):
		parse_seed_batch_assignments(("0=batch-a", "0=batch-b"))
	with pytest.raises(ValueError, match="SEED=BATCH_ID"):
		parse_seed_batch_assignments(("batch-a",))


def test_validate_seed_batch_manifest_rejects_mislabeled_seed(tmp_path: Path) -> None:
	batch_root = tmp_path / "seed-zero"
	batch_root.mkdir()
	(batch_root / "batch_manifest.json").write_text(
		"""
{
  "timestamp_id": "seed-zero",
  "domains": ["ferry"],
  "settings": {
    "random_seed": 4,
    "num_workers": 1,
    "num_permutations": 3,
    "goal_max_size": 1,
    "train_timeout_seconds": 43200,
    "max_rss_gb": 16.0
  }
}
""".strip(),
		encoding="utf-8",
	)

	with pytest.raises(ValueError, match="assigned seed 0"):
		validate_seed_batch_manifest(
			batch_root=batch_root,
			seed=0,
			domains=("ferry",),
		)


def test_validate_seed_batch_manifest_fingerprints_complete_evidence(
	tmp_path: Path,
) -> None:
	batch_root = tmp_path / "seed-zero"
	artifact_root = batch_root / "run_logs/ferry"
	artifact_root.mkdir(parents=True)
	(batch_root / "batch_manifest.json").write_text(
		"""
{
  "timestamp_id": "seed-zero",
  "domains": ["ferry"],
  "settings": {
    "random_seed": 0,
    "num_workers": 1,
    "num_permutations": 3,
    "goal_max_size": 1,
    "train_timeout_seconds": 43200,
    "max_rss_gb": 16.0
  }
}
""".strip(),
		encoding="utf-8",
	)
	(artifact_root / "ferry.model").write_bytes(b"model")

	with pytest.raises(ValueError, match="readable policy"):
		validate_seed_batch_manifest(
			batch_root=batch_root,
			seed=0,
			domains=("ferry",),
		)

	(artifact_root / "ferry.model.readable").write_text("policy", encoding="utf-8")
	metadata = validate_seed_batch_manifest(
		batch_root=batch_root,
		seed=0,
		domains=("ferry",),
	)

	assert len(metadata["artifact_sha256"]) == 64
	assert metadata["artifacts"][0]["domain"] == "ferry"
	assert len(metadata["artifacts"][0]["model_sha256"]) == 64
	assert len(metadata["artifacts"][0]["readable_policy_sha256"]) == 64


def test_all_stage_temporal_input_is_current_seed_zero_full_compiler(
	tmp_path: Path,
) -> None:
	input_record = resolve_temporal_atomic_input(
		stage="all",
		run_id="paper",
		atomic_output_root=tmp_path / "atomic",
		evidence_batch_root=tmp_path / "batches",
		requested_batch_id=None,
		seed_batches={0: "seed-zero", 1: "seed-one"},
	)

	assert input_record.batch_root == tmp_path / "atomic"
	assert input_record.batch_id == "paper-seed0-full"
	assert input_record.evidence_batch_id == "seed-zero"
	assert input_record.provenance == "same_run_seed0_full_compiler"

	with pytest.raises(ValueError, match="temporal-batch-id.*temporal-only"):
		resolve_temporal_atomic_input(
			stage="all",
			run_id="paper",
			atomic_output_root=tmp_path / "atomic",
			evidence_batch_root=tmp_path / "batches",
			requested_batch_id="stale-batch",
			seed_batches={0: "seed-zero"},
		)


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
	assert "--resume" in command


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
	assert "--resume" in command


def test_resume_manifest_requires_same_registered_contract() -> None:
	existing = {
		"source_revision": {"commit": "abc", "tracked_changes": False},
		"domains": ["ferry"],
		"registered_seeds": [0, 1, 2, 3, 4],
		"case_contract": {"achievement": {"sha256": "a"}},
		"seed_batch_manifests": {"0": {"artifact_sha256": "b"}},
		"temporal_atomic_input": {"batch_id": "paper-seed0-full"},
		"num_workers": 6,
		"timeout_seconds": 1800,
		"jason_java_stack_size": "64m",
		"runs": [{"run_id": "paper-seed0-full"}],
	}
	validate_resume_manifest(existing, dict(existing))

	changed = {**existing, "num_workers": 12}
	with pytest.raises(ValueError, match="resume contract mismatch.*num_workers"):
		validate_resume_manifest(existing, changed)


def test_registered_run_resume_requires_complete_matching_revision(
	tmp_path: Path,
) -> None:
	revision = {
		"available": True,
		"commit": "abc",
		"tracked_changes": False,
		"untracked_files": False,
	}
	summary_file = tmp_path / "summary.json"
	run = RegisteredRun(
		stage="Atomic",
		method="Full Compiler",
		variant="full",
		run_id="paper-seed0-full",
		command=("python", "child.py"),
		summary_file=summary_file,
		seed=0,
	)
	assert not registered_run_summary_complete(run, expected_revision=revision)

	summary_file.write_text(
		json.dumps({"source_revision": revision}),
		encoding="utf-8",
	)
	assert not registered_run_summary_complete(run, expected_revision=revision)

	summary_file.write_text(
		json.dumps({"source_revision": revision, "completed_at": "now"}),
		encoding="utf-8",
	)
	assert registered_run_summary_complete(run, expected_revision=revision)
	with pytest.raises(ValueError, match="source revision"):
		registered_run_summary_complete(
			run,
			expected_revision={**revision, "tracked_changes": True},
		)


def test_registered_case_contract_covers_all_selected_test_and_temporal_cases(
	tmp_path: Path,
) -> None:
	for domain, domain_text, problem_name in (
		(
			"classical",
			"(define (domain classical) (:requirements :strips) "
			"(:predicates (done)) (:action finish :parameters () "
			":precondition (and) :effect (done)))",
			"p1.pddl",
		),
		(
			"numeric",
			"(define (domain numeric) (:requirements :strips :numeric-fluents) "
			"(:predicates (done)) (:functions (level)) "
			"(:action finish :parameters () :precondition (and) "
			":effect (and (done) (increase (level) 1))))",
			"n1.pddl",
		),
	):
		domain_root = tmp_path / "src/domains" / domain
		(domain_root / "test").mkdir(parents=True)
		(domain_root / "domain.pddl").write_text(domain_text, encoding="utf-8")
		(domain_root / "test" / problem_name).write_text("problem", encoding="utf-8")
	benchmark_root = tmp_path / "benchmark"
	benchmark_root.mkdir()
	(benchmark_root / "benchmark.json").write_text(
		'{"domains":{"classical":{"cases":{"s1":{}}},'
		'"numeric":{"cases":{"s2":{}}}}}',
		encoding="utf-8",
	)

	contract = build_registered_case_contract(
		project_root=tmp_path,
		benchmark_root=benchmark_root,
		domains=("classical", "numeric"),
	)

	assert contract["achievement"]["count"] == 2
	assert contract["temporal"]["count"] == 2
	assert contract["external"]["raw_moose"]["count"] == 2
	assert contract["external"]["lama"]["count"] == 1
	assert contract["external"]["enhsp_hmrphj"]["count"] == 1


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
				"controller_fingerprint": "controller",
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
						{
							"sample_id": "ferry-1",
							"dfa_fingerprint": "different",
							"controller_fingerprint": "controller",
						},
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
						{
							"sample_id": "ferry-1",
							"dfa_fingerprint": None,
							"controller_fingerprint": "controller",
						},
					],
				},
			),
		)
	with pytest.raises(ValueError, match="missing controller fingerprint"):
		validate_temporal_pairing(
			(
				*other_runs[:-1],
				{
					**other_runs[-1],
					"results": [
						{
							"sample_id": "ferry-1",
							"dfa_fingerprint": "dfa",
							"controller_fingerprint": None,
						},
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
					"predicate": "done",
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
		"module_predicates": ("done",),
		"declared_producible_target_predicates": ("done",),
		"producible_target_denominator_available": True,
		"producible_target_count": 1,
		"covered_target_count": 1,
		"module_closure_complete": True,
		"context_literal_count": 3,
		"body_step_count": 2,
		"primitive_action_step_count": 1,
		"subgoal_step_count": 1,
		"asl_bytes": 30,
	}


def test_common_target_coverage_uses_full_compiler_pddl_denominator() -> None:
	runs = []
	for variant, modules, declared in (
		("validated_evidence_adapter", ("at",), ()),
		("action_only_closure", ("at", "free"), ()),
		("maximal_certified_program", ("at", "free"), ()),
		("full", ("at", "free"), ("at", "free")),
	):
		runs.append(
			{
				"seed": 0,
				"variant": variant,
				"domains": {
					"toy": {
						"library_metrics": {
							"module_predicates": modules,
							"declared_producible_target_predicates": declared,
							"producible_target_denominator_available": variant == "full",
						},
					},
				},
			},
		)

	normalized = apply_common_target_coverage(runs)
	by_variant = {row["variant"]: row for row in normalized}
	evidence_metrics = by_variant["validated_evidence_adapter"]["domains"]["toy"][
		"library_metrics"
	]
	full_metrics = by_variant["full"]["domains"]["toy"]["library_metrics"]

	assert evidence_metrics["producible_target_count"] == 2
	assert evidence_metrics["covered_target_count"] == 1
	assert evidence_metrics["module_closure_complete"] is False
	assert full_metrics["producible_target_count"] == 2
	assert full_metrics["covered_target_count"] == 2
	assert full_metrics["module_closure_complete"] is True


def test_common_target_coverage_rejects_missing_full_denominator() -> None:
	with pytest.raises(ValueError, match="missing full compiler target denominator"):
		apply_common_target_coverage(
			(
				{
					"seed": 0,
					"variant": "full",
					"domains": {
						"toy": {
							"library_metrics": {
								"module_predicates": ("at",),
								"declared_producible_target_predicates": (),
								"producible_target_denominator_available": False,
							},
						},
					},
				},
			),
		)


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
