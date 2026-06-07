"""
Fast Downward adapter used by low-level transition planning.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from utils.pddl_parser import PDDLFact

from .models import LowLevelAction, LowLevelPlanResult
from .pddl_goal import write_goal_problem_variant


@dataclass(frozen=True)
class FastDownwardPlannerConfig:
	"""Configuration for invoking the Fast Downward driver."""

	executable: str | None = None
	alias: str = "lama-first"
	timeout_seconds: int = 60


class FastDownwardPlanner:
	"""Invoke Fast Downward on generated transition-goal PDDL tasks."""

	def __init__(self, config: FastDownwardPlannerConfig | None = None) -> None:
		self.config = config or FastDownwardPlannerConfig()

	def solve_transition_goal(
		self,
		*,
		domain_file: str | Path,
		base_problem_file: str | Path,
		goal_literals: Iterable[str],
		work_dir: str | Path,
		task_name: str,
		initial_facts: Iterable[PDDLFact] | None = None,
	) -> LowLevelPlanResult:
		"""Solve a transition-level planning task with Fast Downward."""

		executable = self._resolve_executable()
		generated_problem = write_goal_problem_variant(
			base_problem_file=base_problem_file,
			goal_literals=tuple(goal_literals),
			output_file=Path(work_dir).expanduser().resolve() / f"{task_name}.pddl",
			initial_facts=tuple(initial_facts) if initial_facts is not None else None,
		)
		if executable is None:
			return LowLevelPlanResult(
				success=False,
				generated_problem_file=str(generated_problem),
				error=(
					"Fast Downward executable not found. Set FAST_DOWNWARD or pass "
					"--fast-downward."
				),
			)

		plan_file = Path(work_dir).expanduser().resolve() / f"{task_name}.plan"
		command = [
			executable,
			"--plan-file",
			str(plan_file),
			"--alias",
			self.config.alias,
			str(Path(domain_file).expanduser().resolve()),
			str(generated_problem),
		]
		try:
			completed = subprocess.run(
				command,
				check=False,
				capture_output=True,
				text=True,
				timeout=self.config.timeout_seconds,
			)
		except subprocess.TimeoutExpired as exc:
			return LowLevelPlanResult(
				success=False,
				generated_problem_file=str(generated_problem),
				plan_file=str(plan_file),
				stdout=exc.stdout or "",
				stderr=exc.stderr or "",
				error=f"Fast Downward timed out after {self.config.timeout_seconds} seconds.",
			)

		selected_plan_file = _select_plan_file(plan_file)
		actions = (
			_parse_plan_file(selected_plan_file)
			if selected_plan_file is not None
			else ()
		)
		return LowLevelPlanResult(
			success=completed.returncode == 0 and bool(actions),
			actions=actions,
			generated_problem_file=str(generated_problem),
			plan_file=str(selected_plan_file or plan_file),
			stdout=completed.stdout,
			stderr=completed.stderr,
			error=None if completed.returncode == 0 and actions else _failure_message(completed),
		)

	def _resolve_executable(self) -> str | None:
		configured = (
			self.config.executable
			or os.environ.get("FAST_DOWNWARD")
			or os.environ.get("FAST_DOWNWARD_PY")
		)
		if configured:
			path = Path(configured).expanduser()
			if path.exists():
				return str(path.resolve())
			found = shutil.which(configured)
			if found:
				return found
		for candidate in ("fast-downward.py", "fast-downward"):
			found = shutil.which(candidate)
			if found:
				return found
		return None


def _select_plan_file(plan_file: Path) -> Path | None:
	candidates = [plan_file]
	candidates.extend(sorted(plan_file.parent.glob(f"{plan_file.name}.*")))
	existing = [candidate for candidate in candidates if candidate.exists()]
	if not existing:
		return None
	return max(existing, key=lambda path: path.stat().st_mtime_ns)


def _parse_plan_file(plan_file: Path) -> Tuple[LowLevelAction, ...]:
	actions: list[LowLevelAction] = []
	for raw_line in plan_file.read_text(encoding="utf-8").splitlines():
		line = raw_line.strip()
		if not line or line.startswith(";"):
			continue
		if line.startswith("(") and line.endswith(")"):
			line = line[1:-1].strip()
		tokens = line.split()
		if not tokens:
			continue
		actions.append(LowLevelAction(name=tokens[0], arguments=tuple(tokens[1:])))
	return tuple(actions)


def _failure_message(completed: subprocess.CompletedProcess[str]) -> str:
	if completed.returncode == 0:
		return "Fast Downward finished without a parseable plan."
	return f"Fast Downward failed with exit code {completed.returncode}."
