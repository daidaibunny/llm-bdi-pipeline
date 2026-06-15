from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning.gp_backends import (
	BackendManifest,
	GPBackendRunner,
	SketchCondition,
	SketchEffect,
	SketchPolicy,
	SketchRule,
	discover_backend_manifest,
	parse_dlplan_policy,
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
