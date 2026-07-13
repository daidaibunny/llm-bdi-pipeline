from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from domain_level_planning.gp_backends import (
	BackendManifest,
	GPBackendRunner,
	LearningGeneralPoliciesRunConfig,
	LearnerSketchesRunConfig,
	SketchCondition,
	SketchEffect,
	SketchPolicy,
	SketchRule,
	backend_audit_matrix,
	backend_consumption_role,
	discover_learner_sketches_policy_file,
	discover_learning_general_policies_policy_file,
	discover_backend_manifest,
	parse_dlplan_policy,
	parse_d2l_policy,
	run_learning_general_policies,
	run_learner_sketches,
)


def test_discover_backend_manifest_reads_pinned_repository_metadata(
	tmp_path: Path,
) -> None:
	repo = tmp_path / "learner-sketches"
	repo.mkdir()
	(repo / "README.md").write_text("Sketch Learner", encoding="utf-8")
	(repo / ".git").mkdir()
	(repo / ".git" / "HEAD").write_text("7a7ea6a\n", encoding="utf-8")

	manifest = discover_backend_manifest(
		root=tmp_path,
		name="learner-sketches",
		url="https://github.com/bonetblai/learner-sketches.git",
		commit="7a7ea6a",
	)

	assert manifest.name == "learner-sketches"
	assert manifest.path == repo
	assert manifest.url == "https://github.com/bonetblai/learner-sketches.git"
	assert manifest.expected_commit == "7a7ea6a"
	assert manifest.present is True


def test_discover_backend_manifest_reports_missing_backend(tmp_path: Path) -> None:
	manifest = discover_backend_manifest(
		root=tmp_path,
		name="h-policy-learner",
		url="https://github.com/drexlerd/h-policy-learner.git",
		commit="03e3455",
	)

	assert manifest.present is False
	assert manifest.path == tmp_path / "h-policy-learner"


def test_backend_audit_matrix_reports_reusable_evidence_and_resource_profile(
	tmp_path: Path,
) -> None:
	learner = tmp_path / "learner-sketches"
	learner.mkdir()
	(learner / ".git").mkdir()
	(learner / ".git" / "HEAD").write_text(
		"7a7ea6a6356035afa16ed958b53d8edc86994e0a\n",
		encoding="utf-8",
	)
	d2l = tmp_path / "d2l"
	d2l.mkdir()
	(d2l / ".git").mkdir()
	(d2l / ".git" / "HEAD").write_text("wrong-commit\n", encoding="utf-8")
	policy_examples = tmp_path / "learner-policies-from-examples"
	policy_examples.mkdir()
	(policy_examples / ".git").mkdir()
	(policy_examples / ".git" / "HEAD").write_text(
		"9991926f7655c4b6c8dc2f0404123639e42056f2\n",
		encoding="utf-8",
	)

	matrix = backend_audit_matrix(root=tmp_path)
	by_name = {entry["name"]: entry for entry in matrix}

	assert {
		"moose",
		"learner-sketches",
		"h-policy-learner",
		"d2l",
		"learner-policies-from-examples",
		"pg3",
		"mimir-rgnn",
		"best-first-generalized-planning",
		"bfgp-pp",
		"pgp-landmarks",
		"sltp",
		"up-bfgp",
		"llm-genplan",
		"state-centric-gen-planning",
		"ipc-learning-huzar",
		"ipc-learning-pgp-baseline",
	}.issubset(set(by_name))
	assert by_name["moose"]["present"] is False
	assert by_name["moose"]["pin_status"] == "missing"
	assert by_name["moose"]["current_consumption_role"] == {
		"drives_atomic_templates": True,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": True,
		"consumption_mode": "moose_readable_policy_atomic_templates",
		"blocking_gap": None,
	}
	assert by_name["moose"]["paper_code_capability"]["status"] == (
		"confirmed_exact_reproduction_ready"
	)
	assert "./moose.sif train benchmarks/<domain>/domain.pddl" in by_name["moose"][
		"usage_entrypoints"
	]
	assert by_name["learner-sketches"]["present"] is True
	assert by_name["learner-sketches"]["pin_status"] == "ok"
	assert by_name["learner-sketches"]["paper_role"] == (
		"serialized-width sketch learner for qualitative DLPlan policies"
	)
	assert by_name["learner-sketches"]["preferred_use"] == (
		"candidate external sketch backend; current repository parses and "
		"summarizes policies but does not compile them into atomic ASL"
	)
	assert "feature_rule_policy" in by_name["learner-sketches"]["output_artifacts"]
	assert (
		"qualitative sketch-policy artifact"
		in by_name["learner-sketches"]["reusable_evidence"]
	)
	assert by_name["learner-sketches"]["resource_profile"]["default_max_rss_gb"] == 16.0
	assert by_name["learner-sketches"]["resource_profile"]["guard_required"] is True
	assert by_name["learner-sketches"]["current_consumption_role"] == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}
	assert by_name["learner-sketches"]["paper_code_capability"]["status"] == (
		"confirmed_paper_source_complete"
	)
	assert any(
		"learner-sketches-command" in entry
		for entry in by_name["learner-sketches"]["usage_entrypoints"]
	)

	assert by_name["h-policy-learner"]["present"] is False
	assert by_name["h-policy-learner"]["pin_status"] == "missing"
	assert "missing_backend" in by_name["h-policy-learner"]["failure_modes"]
	assert "hierarchical policy" in by_name["h-policy-learner"]["paper_role"]
	assert by_name["h-policy-learner"]["current_consumption_role"] == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}

	assert by_name["d2l"]["present"] is True
	assert by_name["d2l"]["pin_status"] == "mismatch"
	assert "pin_mismatch" in by_name["d2l"]["failure_modes"]
	assert "Docker" in by_name["d2l"]["resource_profile"]["execution_environment"]
	assert by_name["d2l"]["current_consumption_role"] == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}
	assert by_name["d2l"]["paper_code_capability"]["status"] == (
		"confirmed_source_complete_needs_paper_environment"
	)
	assert by_name["learner-policies-from-examples"]["pin_status"] == "ok"
	assert "KR 2025" in by_name["learner-policies-from-examples"]["paper_role"]
	assert by_name["learner-policies-from-examples"]["preferred_use"] == (
		"candidate policy-first backend for learned LiftedPolicyProgram "
		"artifacts; ASL compilation remains a verified-adapter gap"
	)
	assert (
		"Docker linux/amd64"
		in by_name["learner-policies-from-examples"]["resource_profile"][
			"execution_environment"
		]
	)
	assert (
		"native macOS is unsupported"
		in by_name["learner-policies-from-examples"]["resource_profile"][
			"execution_environment"
		]
	)
	assert any(
		"learning-general-policies-docker-command" in entry
		for entry in by_name["learner-policies-from-examples"]["usage_entrypoints"]
	)
	assert by_name["learner-policies-from-examples"]["current_consumption_role"] == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}
	assert by_name["pg3"]["current_consumption_role"] == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "audit_or_baseline_only",
		"blocking_gap": "no_verified_lifted_policy_program_adapter",
	}
	assert {
		entry["name"]
		for entry in matrix
		if "paper_code_capability" in entry
	} == set(by_name)
	assert "./run.sh" in by_name["pg3"]["usage_entrypoints"]
	assert by_name["bfgp-pp"]["current_consumption_role"]["consumed_by_atomic_library"] is False
	assert "structured generalized planning program synthesis" in by_name["bfgp-pp"][
		"paper_role"
	]
	assert by_name["state-centric-gen-planning"]["current_consumption_role"][
		"consumed_by_atomic_library"
	] is False


def test_backend_consumption_role_accepts_verified_backend_dialects() -> None:
	assert backend_consumption_role("moose") == {
		"drives_atomic_templates": True,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": True,
		"consumption_mode": "moose_readable_policy_atomic_templates",
		"blocking_gap": None,
	}
	assert backend_consumption_role("learner-sketches") == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}
	assert backend_consumption_role("h-policy-learner") == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}
	assert backend_consumption_role("d2l") == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}
	assert backend_consumption_role("learner-policies-from-examples") == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
		"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
	}
	assert backend_consumption_role("pg3") == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "audit_or_baseline_only",
		"blocking_gap": "no_verified_lifted_policy_program_adapter",
	}
	assert backend_consumption_role("unknown-paper-code") == {
		"drives_atomic_templates": False,
		"drives_temporal_wrapper": False,
		"consumed_by_atomic_library": False,
		"consumption_mode": "unknown_backend_audit_only",
		"blocking_gap": "no_pinned_backend_profile_or_verified_adapter",
	}


def test_backend_audit_status_cli_prints_matrix_entries(tmp_path: Path) -> None:
	script = Path(__file__).resolve().parents[2] / "scripts" / "gp_backend_audit.py"

	result = subprocess.run(
		(
			sys.executable,
			str(script),
			"status",
			"--backend-root",
			str(tmp_path),
		),
		check=True,
		capture_output=True,
		text=True,
	)

	assert "learner-sketches: missing; observed=unknown; pinned=missing" in result.stdout
	assert "moose: missing; observed=unknown; pinned=missing" in result.stdout
	assert "h-policy-learner: missing; observed=unknown; pinned=missing" in result.stdout
	assert "d2l: missing; observed=unknown; pinned=missing" in result.stdout
	assert (
		"learner-policies-from-examples: missing; observed=unknown; pinned=missing"
		in result.stdout
	)
	assert "pg3: missing; observed=unknown; pinned=missing" in result.stdout


def test_backend_audit_usage_cli_prints_how_to_run_backends(tmp_path: Path) -> None:
	script = Path(__file__).resolve().parents[2] / "scripts" / "gp_backend_audit.py"

	result = subprocess.run(
		(
			sys.executable,
			str(script),
			"usage",
			"--backend-root",
			str(tmp_path),
		),
		check=True,
		capture_output=True,
		text=True,
	)

	assert "pg3:" in result.stdout
	assert "moose:" in result.stdout
	assert "./moose.sif train benchmarks/<domain>/domain.pddl" in result.stdout
	assert "learner-sketches-command" in result.stdout
	assert "./run.sh" in result.stdout
	assert "bfgp-pp:" in result.stdout
	assert "./scripts/compile.sh" in result.stdout
	assert "state-centric-gen-planning:" in result.stdout
	assert "python -m code.modeling.train_lstm" in result.stdout


def test_backend_audit_capability_cli_prints_paper_code_status(
	tmp_path: Path,
) -> None:
	script = Path(__file__).resolve().parents[2] / "scripts" / "gp_backend_audit.py"

	result = subprocess.run(
		(
			sys.executable,
			str(script),
			"capability",
			"--backend-root",
			str(tmp_path),
		),
		check=True,
		capture_output=True,
		text=True,
	)

	assert "moose:" in result.stdout
	assert "status: confirmed_exact_reproduction_ready" in result.stdout
	assert "learner-sketches:" in result.stdout
	assert "status: confirmed_paper_source_complete" in result.stdout
	assert "d2l:" in result.stdout
	assert "status: confirmed_source_complete_needs_paper_environment" in result.stdout
	assert "ipc-learning-huzar:" in result.stdout
	assert "status: confirmed_competition_artifact_only" in result.stdout


def test_moose_atomic_audit_command_pins_reproduction_seed_and_workers() -> None:
	project_root = Path(__file__).resolve().parents[2]
	script = project_root / "scripts" / "gp_backend_audit.py"

	result = subprocess.run(
		(
			sys.executable,
			str(script),
			"moose-atomic-command",
			"--domain-file",
			str(project_root / "src" / "domains" / "ferry" / "domain.pddl"),
			"--training-dir",
			str(project_root / "src" / "domains" / "ferry" / "train"),
			"--save-file",
			str(project_root / "tmp" / "moose-audit-test.model"),
		),
		check=True,
		capture_output=True,
		text=True,
	)

	assert "--random-seed 0" in result.stdout
	assert "--num_workers 12" in result.stdout


def test_install_moose_backend_uses_configured_backend_root(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	from scripts import gp_backend_audit

	calls: list[tuple[str, ...]] = []

	def fake_run_git(args: tuple[str, ...], *, proxy: str | None = None) -> None:
		calls.append(args)

	monkeypatch.setattr(gp_backend_audit, "_run_git", fake_run_git)

	gp_backend_audit.install_moose_backend(tmp_path, proxy="http://127.0.0.1:10808")

	assert calls[0] == (
		"clone",
		"https://github.com/DillonZChen/moose.git",
		str(tmp_path / "moose"),
	)
	assert calls[1][:6] == (
		"-C",
		str(tmp_path / "moose"),
		"fetch",
		"--depth",
		"1",
		"origin",
	)
	assert calls[2][:3] == ("-C", str(tmp_path / "moose"), "checkout")


def test_learning_general_policies_audit_cli_prints_guarded_command(
	tmp_path: Path,
) -> None:
	script = Path(__file__).resolve().parents[2] / "scripts" / "gp_backend_audit.py"
	backend = tmp_path / "learner-policies-from-examples"
	backend.mkdir()

	result = subprocess.run(
		(
			sys.executable,
			str(script),
			"learning-general-policies-command",
			"--backend-root",
			str(tmp_path),
			"--experiment",
			"blocks_4_clear_0",
			"--timeout-seconds",
			"7",
			"--max-num-instances",
			"1",
		),
		check=True,
		capture_output=True,
		text=True,
	)

	assert "# blocks_4_clear_0" in result.stdout
	assert "resource_guard.py" in result.stdout
	assert "learner-policies-from-examples:blocks_4_clear_0" in result.stdout
	assert "learning/main.py" in result.stdout
	assert "--planner bfws" in result.stdout
	assert "--width 0" in result.stdout
	assert "--max_num_instances 1" in result.stdout


def test_learning_general_policies_docker_build_cli_prints_proxy_args(
	tmp_path: Path,
) -> None:
	script = Path(__file__).resolve().parents[2] / "scripts" / "gp_backend_audit.py"
	backend = tmp_path / "learner-policies-from-examples"
	backend.mkdir()

	result = subprocess.run(
		(
			sys.executable,
			str(script),
			"learning-general-policies-docker-build-command",
			"--backend-root",
			str(tmp_path),
			"--proxy",
			"http://host.docker.internal:10808",
		),
		check=True,
		capture_output=True,
		text=True,
	)

	assert "docker build" in result.stdout
	assert "--build-arg http_proxy=http://host.docker.internal:10808" in result.stdout
	assert "--build-arg https_proxy=http://host.docker.internal:10808" in result.stdout
	assert "docker/learning-general-policies/Dockerfile" in result.stdout


def test_learning_general_policies_summary_cli_reports_policy_program(
	tmp_path: Path,
) -> None:
	script = Path(__file__).resolve().parents[2] / "scripts" / "gp_backend_audit.py"
	backend = tmp_path / "learner-policies-from-examples"
	output = (
		tmp_path
		/ "gp-backend-audit"
		/ "learner-policies-from-examples"
		/ "blocks_4_clear_0"
		/ "output.uuid123"
	)
	backend.mkdir()
	output.mkdir(parents=True)
	(output / "sketch_minimized_0.txt").write_text(
		"""
		(:policy
		(:booleans (b_empty "b_nullary(handempty)"))
		(:numericals (n_on "n_count(c_primitive(clear,0))"))
		(:rule (:conditions (:c_b_pos b_empty)) (:effects (:e_n_inc n_on)))
		)
		""",
		encoding="utf-8",
	)

	result = subprocess.run(
		(
			sys.executable,
			str(script),
			"learning-general-policies-summary",
			"--backend-root",
			str(tmp_path),
			"--audit-output-root",
			str(tmp_path / "gp-backend-audit"),
			"--experiment",
			"blocks_4_clear_0",
		),
		check=True,
		capture_output=True,
		text=True,
	)

	assert "blocks_4_clear_0: present; width=0" in result.stdout
	assert "policy_program=ok" in result.stdout
	assert "backend=learner-policies-from-examples" in result.stdout
	assert "features=2" in result.stdout
	assert "rules=1" in result.stdout


def test_learner_sketches_command_is_reproducible(tmp_path: Path) -> None:
	backend = tmp_path / "learner-sketches"
	backend.mkdir()
	domain = tmp_path / "domain.pddl"
	problems = tmp_path / "problems"
	workspace = tmp_path / "workspace"

	manifest = BackendManifest(
		name="learner-sketches",
		path=backend,
		url="https://github.com/bonetblai/learner-sketches.git",
		expected_commit="7a7ea6a",
		present=True,
	)
	runner = GPBackendRunner(manifest)

	command = runner.learner_sketches_command(
		domain_file=domain,
		problems_directory=problems,
		workspace=workspace,
		python_executable=backend / ".venv" / "bin" / "python",
		width=1,
		max_states_per_instance=500,
		max_time_per_instance=30,
	)

	assert command == (
		str(backend / ".venv" / "bin" / "python"),
		str(backend / "learning" / "main.py"),
		"--domain_filepath",
		str(domain),
		"--problems_directory",
		str(problems),
		"--workspace",
		str(workspace),
		"--width",
		"1",
		"--max_num_states_per_instance",
		"500",
		"--max_time_per_instance",
		"30",
	)


def test_backend_runner_wraps_external_commands_with_resource_guard(tmp_path: Path) -> None:
	backend = tmp_path / "learner-sketches"
	backend.mkdir()
	manifest = BackendManifest(
		name="learner-sketches",
		path=backend,
		url="https://github.com/bonetblai/learner-sketches.git",
		expected_commit="7a7ea6a",
		present=True,
	)
	runner = GPBackendRunner(manifest)

	command = runner.guarded_command(
		("python3", "exp.py"),
		label="learner-sketches:test",
		max_rss_gb=12.5,
		poll_seconds=2.0,
		timeout_seconds=60,
	)

	assert command[:3] == ("uv", "run", "python")
	assert "scripts/resource_guard.py" in command[3]
	assert "--max-rss-gb" in command
	assert "12.5" in command
	assert "--timeout-seconds" in command
	assert "60" in command
	assert command[-3:] == ("--", "python3", "exp.py")


def test_backend_runner_fails_clearly_when_backend_is_missing(tmp_path: Path) -> None:
	manifest = BackendManifest(
		name="learner-sketches",
		path=tmp_path / "learner-sketches",
		url="https://github.com/bonetblai/learner-sketches.git",
		expected_commit="7a7ea6a",
		present=False,
	)
	runner = GPBackendRunner(manifest)

	with pytest.raises(FileNotFoundError, match="learner-sketches"):
		runner.learner_sketches_command(
			domain_file=tmp_path / "domain.pddl",
			problems_directory=tmp_path / "problems",
			workspace=tmp_path / "workspace",
		)


def test_run_learner_sketches_discovers_minimized_policy_artifact(tmp_path: Path) -> None:
	backend = tmp_path / "learner-sketches"
	learning = backend / "learning"
	learning.mkdir(parents=True)
	main = learning / "main.py"
	main.write_text(
		"""
from __future__ import annotations

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--domain_filepath")
parser.add_argument("--problems_directory")
parser.add_argument("--workspace")
parser.add_argument("--width", type=int)
parser.add_argument("--max_num_states_per_instance")
parser.add_argument("--max_time_per_instance")
args = parser.parse_args()
output = Path(args.workspace) / "output"
output.mkdir(parents=True, exist_ok=True)
(output / f"sketch_minimized_{args.width}.txt").write_text(
	'(:policy (:booleans ) (:numericals (f1 "n_count(c_primitive(done,0))")) '
	'(:rule (:conditions ) (:effects (:e_n_inc f1))))',
	encoding="utf-8",
)
(output / f"sketch_{args.width}.txt").write_text("raw", encoding="utf-8")
print("learned")
		""",
		encoding="utf-8",
	)
	manifest = BackendManifest(
		name="learner-sketches",
		path=backend,
		url="https://github.com/bonetblai/learner-sketches.git",
		expected_commit="7a7ea6a",
		present=True,
	)
	workspace = tmp_path / "workspace"

	result = run_learner_sketches(
		manifest=manifest,
		config=LearnerSketchesRunConfig(
			domain_file=tmp_path / "domain.pddl",
			problems_directory=tmp_path / "problems",
			workspace=workspace,
			width=2,
			python_executable="python3",
			use_resource_guard=False,
		),
	)

	assert result.succeeded is True
	assert result.returncode == 0
	assert result.policy_file == workspace / "output" / "sketch_minimized_2.txt"
	assert result.raw_policy_file == workspace / "output" / "sketch_2.txt"
	assert result.to_dict()["succeeded"] is True
	assert "learned" in result.stdout
	assert discover_learner_sketches_policy_file(workspace, width=2) == result.policy_file


def test_run_learner_sketches_reports_missing_policy_as_failed(tmp_path: Path) -> None:
	backend = tmp_path / "learner-sketches"
	learning = backend / "learning"
	learning.mkdir(parents=True)
	(learning / "main.py").write_text("print('no policy')\n", encoding="utf-8")
	manifest = BackendManifest(
		name="learner-sketches",
		path=backend,
		url="https://github.com/bonetblai/learner-sketches.git",
		expected_commit="7a7ea6a",
		present=True,
	)

	result = run_learner_sketches(
		manifest=manifest,
		config=LearnerSketchesRunConfig(
			domain_file=tmp_path / "domain.pddl",
			problems_directory=tmp_path / "problems",
			workspace=tmp_path / "workspace",
			python_executable="python3",
			use_resource_guard=False,
		),
	)

	assert result.returncode == 0
	assert result.policy_file is None
	assert result.succeeded is False


def test_d2l_commands_are_reproducible(tmp_path: Path) -> None:
	backend = tmp_path / "d2l"
	backend.mkdir()
	workspace = tmp_path / "workspace"
	manifest = BackendManifest(
		name="d2l",
		path=backend,
		url="https://github.com/rleap-project/d2l.git",
		expected_commit="0620e16",
		present=True,
	)
	runner = GPBackendRunner(manifest)

	assert runner.d2l_command(
		experiment="blocks:all_at_5",
		python_executable=backend / ".venv" / "bin" / "python",
		steps=(1, 2),
	) == (
		str(backend / ".venv" / "bin" / "python"),
		str(backend / "experiments" / "run.py"),
		"blocks:all_at_5",
		"1",
		"2",
	)
	assert runner.d2l_docker_run_command(
		experiment="blocks:clear",
		workspace=workspace,
	) == (
		"docker",
		"run",
		"--rm",
		"--platform",
		"linux/amd64",
		"-v",
		f"{backend}:/workspace/d2l",
		"-v",
		f"{workspace}:/workspace/d2l/workspace",
		"d2l-official-env:local",
		"blocks:clear",
	)


def test_learning_general_policies_command_is_reproducible(tmp_path: Path) -> None:
	backend = tmp_path / "learner-policies-from-examples"
	backend.mkdir()
	domain = tmp_path / "domain.pddl"
	problems = tmp_path / "problems"
	workspace = tmp_path / "workspace"
	manifest = BackendManifest(
		name="learner-policies-from-examples",
		path=backend,
		url="https://github.com/bonetblai/learner-policies-from-examples.git",
		expected_commit="9991926",
		present=True,
	)
	runner = GPBackendRunner(manifest)

	command = runner.learning_general_policies_command(
		domain_file=domain,
		problems_directory=problems,
		workspace=workspace,
		python_executable=backend / ".venv" / "bin" / "python",
		width=0,
		planner="bfws",
		max_num_instances=1,
		max_states_per_instance=250,
		max_time_per_instance=20,
		complexity_limit=5,
		feature_limit=1000,
		max_features=6,
		cost_bound=20,
	)

	assert command == (
		str(backend / ".venv" / "bin" / "python"),
		str(backend / "learning" / "main.py"),
		"--domain_filepath",
		str(domain),
		"--problems_directory",
		str(problems),
		"--workspace",
		str(workspace),
		"--width",
		"0",
		"--planner",
		"bfws",
		"--max_num_states_per_instance",
		"250",
		"--max_time_per_instance",
		"20",
		"--feature_limit",
		"1000",
		"--max_features",
		"6",
		"--cost_bound",
		"20",
		"--max_num_instances",
		"1",
		"--complexity_limit",
		"5",
	)


def test_learning_general_policies_docker_commands_are_reproducible(
	tmp_path: Path,
) -> None:
	backend = tmp_path / "learner-policies-from-examples"
	backend.mkdir()
	domain = tmp_path / "domain.pddl"
	problems = tmp_path / "problems"
	workspace = tmp_path / "workspace"
	manifest = BackendManifest(
		name="learner-policies-from-examples",
		path=backend,
		url="https://github.com/bonetblai/learner-policies-from-examples.git",
		expected_commit="9991926",
		present=True,
	)
	runner = GPBackendRunner(manifest)

	build_command = runner.learning_general_policies_docker_build_command()
	proxied_build_command = runner.learning_general_policies_docker_build_command(
		build_args={
			"http_proxy": "http://host.docker.internal:10808",
			"https_proxy": "http://host.docker.internal:10808",
		},
	)
	run_command = runner.learning_general_policies_docker_run_command(
		domain_file=domain,
		problems_directory=problems,
		workspace=workspace,
		width=0,
		planner="bfws",
		max_num_instances=1,
		max_rss_gb=16.0,
		timeout_seconds=120,
		complexity_limit=5,
	)

	assert build_command[:5] == (
		"docker",
		"build",
		"--platform",
		"linux/amd64",
		"-t",
	)
	assert any(
		"docker/learning-general-policies/Dockerfile" in item
		for item in build_command
	)
	assert "--build-arg" in proxied_build_command
	assert (
		"http_proxy=http://host.docker.internal:10808"
		in proxied_build_command
	)
	assert (
		"https_proxy=http://host.docker.internal:10808"
		in proxied_build_command
	)
	assert run_command[:6] == (
		"docker",
		"run",
		"--rm",
		"--platform",
		"linux/amd64",
		"--memory",
	)
	assert "16g" in run_command
	assert "learner-policies-from-examples-env:local" in run_command
	assert "--timeout-seconds 120" in " ".join(run_command)
	assert "--max_num_instances 1" in " ".join(run_command)
	assert "--complexity_limit 5" in " ".join(run_command)
	assert str(backend / "learning" / "main.py") in " ".join(run_command)


def test_learning_general_policies_dockerfile_pins_required_dlplan_api() -> None:
	dockerfile = (
		Path(__file__).resolve().parents[2]
		/ "docker"
		/ "learning-general-policies"
		/ "Dockerfile"
	)
	contents = dockerfile.read_text(encoding="utf-8")

	assert "dlplan==0.3.29" in contents
	assert "pymimir==0.9.62" in contents


def test_run_learning_general_policies_discovers_uuid_output_policy(
	tmp_path: Path,
) -> None:
	backend = tmp_path / "learner-policies-from-examples"
	learning = backend / "learning"
	learning.mkdir(parents=True)
	main = learning / "main.py"
	main.write_text(
		"""
from __future__ import annotations

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--domain_filepath")
parser.add_argument("--problems_directory")
parser.add_argument("--workspace")
parser.add_argument("--width", type=int)
parser.add_argument("--planner")
parser.add_argument("--max_num_states_per_instance")
parser.add_argument("--max_time_per_instance")
parser.add_argument("--feature_limit")
parser.add_argument("--max_features")
parser.add_argument("--cost_bound")
parser.add_argument("--complexity_limit", default=None)
args = parser.parse_args()
output = Path(args.workspace) / "output.uuid123"
output.mkdir(parents=True, exist_ok=True)
(output / f"sketch_minimized_{args.width}.txt").write_text(
	'(:policy (:booleans ) (:numericals (f1 "n_count(c_primitive(done,0))")) '
	'(:rule (:conditions ) (:effects (:e_n_inc f1))))',
	encoding="utf-8",
)
(output / f"sketch_{args.width}.txt").write_text("raw", encoding="utf-8")
print("learned policy-first program")
		""",
		encoding="utf-8",
	)
	manifest = BackendManifest(
		name="learner-policies-from-examples",
		path=backend,
		url="https://github.com/bonetblai/learner-policies-from-examples.git",
		expected_commit="9991926",
		present=True,
	)
	workspace = tmp_path / "workspace"

	result = run_learning_general_policies(
		manifest=manifest,
		config=LearningGeneralPoliciesRunConfig(
			domain_file=tmp_path / "domain.pddl",
			problems_directory=tmp_path / "problems",
			workspace=workspace,
			width=0,
			python_executable="python3",
			complexity_limit=3,
			use_resource_guard=False,
		),
	)

	assert result.succeeded is True
	assert result.policy_file == workspace / "output.uuid123" / "sketch_minimized_0.txt"
	assert result.raw_policy_file == workspace / "output.uuid123" / "sketch_0.txt"
	assert result.to_dict()["succeeded"] is True
	assert "policy-first" in result.stdout
	assert (
		discover_learning_general_policies_policy_file(workspace, width=0)
		== result.policy_file
	)


def test_parse_dlplan_policy_extracts_features_and_rules() -> None:
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (576 "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))"))
		(:rule (:conditions ) (:effects (:e_n_inc 576)))
		)
		""",
	)

	assert policy == SketchPolicy(
		features={
			"576": "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))",
		},
		boolean_features={},
		numerical_features={
			"576": "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))",
		},
		rules=(
			'(:rule (:conditions ) (:effects (:e_n_inc 576)))',
		),
		parsed_rules=(
			SketchRule(
				conditions=(),
				effects=(SketchEffect(operator="e_n_inc", feature_id="576"),),
				raw='(:rule (:conditions ) (:effects (:e_n_inc 576)))',
			),
		),
	)


def test_parse_learner_sketches_symbolic_feature_ids() -> None:
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans (f114 "b_nullary(arm-empty)"))
		(:numericals (f35 "n_count(r_primitive(on,0,1))"))
		(:rule (:conditions (:c_b_pos f114) (:c_n_gt f35))
			(:effects (:e_b_neg f114) (:e_n_dec f35)))
		)
		""",
	)

	assert policy.boolean_features == {"f114": "b_nullary(arm-empty)"}
	assert policy.numerical_features == {"f35": "n_count(r_primitive(on,0,1))"}
	assert policy.parsed_rules == (
		SketchRule(
			conditions=(
				SketchCondition(operator="c_b_pos", feature_id="f114"),
				SketchCondition(operator="c_n_gt", feature_id="f35"),
			),
			effects=(
				SketchEffect(operator="e_b_neg", feature_id="f114"),
				SketchEffect(operator="e_n_dec", feature_id="f35"),
			),
			raw=(
				"(:rule (:conditions (:c_b_pos f114) (:c_n_gt f35)) "
				"(:effects (:e_b_neg f114) (:e_n_dec f35)))"
			),
		),
	)


def test_parse_d2l_text_policy_converts_supported_features_to_sketch_rules() -> None:
	policy, diagnostics = parse_d2l_policy(
		"""
		Features (#: 2; total k: 2; max k = 1):
		  Num[Equal(on_g,on)] [k=1]
		  Atom[handempty] [k=1]
		Invariants:
		Policy:
		  1. Atom[handempty]>0 -> {Num[Equal(on_g,on)] INCs}
		""",
		predicate_arities={"on": 2, "handempty": 0},
	)

	assert diagnostics == ()
	assert policy.numerical_features == {
		"d2l_f1": "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))",
	}
	assert policy.boolean_features == {"d2l_f2": "b_nullary(handempty)"}
	assert policy.parsed_rules == (
		SketchRule(
			conditions=(SketchCondition(operator="c_b_pos", feature_id="d2l_f2"),),
			effects=(SketchEffect(operator="e_n_inc", feature_id="d2l_f1"),),
			raw=(
				"(:rule (:conditions (:c_b_pos d2l_f2)) "
				"(:effects (:e_n_inc d2l_f1)))"
			),
		),
	)


def test_parse_d2l_text_policy_keeps_unsupported_features_auditable() -> None:
	policy, diagnostics = parse_d2l_policy(
		"""
		Features (#: 1; total k: 7; max k = 7):
		  Num[Forall(Star(on),Equal(on_g,on))] [k=7]
		Policy:
		  1.  -> {Num[Forall(Star(on),Equal(on_g,on))] INCs}
		""",
		predicate_arities={"on": 2},
	)

	assert policy.features == {
		"d2l_f1": (
			"d2l_unsupported(Num[Forall(Star(on),Equal(on_g,on))])"
		),
	}
	assert tuple(diagnostic.reason for diagnostic in diagnostics) == (
		"unsupported_d2l_description_logic_feature",
	)
