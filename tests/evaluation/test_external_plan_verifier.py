from __future__ import annotations

import sys
from pathlib import Path

from evaluation.external_plan_verifier import run_external_plan_verifier


def test_relative_verifier_command_keeps_caller_working_directory(
	tmp_path: Path,
	monkeypatch,
) -> None:
	monkeypatch.chdir(tmp_path)
	verifier = tmp_path / "verifier.py"
	verifier.write_text(
		"import sys\nassert len(sys.argv) == 4\nprint('Plan valid')\n",
		encoding="utf-8",
	)
	for name in ("domain.pddl", "problem.pddl", "plan.plan"):
		(tmp_path / name).write_text("placeholder\n", encoding="utf-8")

	result = run_external_plan_verifier(
		domain_file="domain.pddl",
		problem_file="problem.pddl",
		plan_file="plan.plan",
		output_dir=tmp_path / "artifacts",
		command=f"{sys.executable} verifier.py",
	)

	assert result.success is True
	assert result.exit_code == 0
