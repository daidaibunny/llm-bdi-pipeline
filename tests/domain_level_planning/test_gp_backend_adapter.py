from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning.gp_backends import (
	BackendManifest,
	GPBackendRunner,
	SketchPolicy,
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
		rules=(
			'(:rule (:conditions ) (:effects (:e_n_inc 576)))',
		),
	)
