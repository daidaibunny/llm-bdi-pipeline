"""Small external VAL/IPC verifier adapter for temporal trace validation."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


_SUCCESS_MARKERS = ("plan valid", "successful plans: 1", "plan executed successfully")
_FAILURE_MARKERS = (
	"plan invalid",
	"plan failed",
	"failed plans",
	"not valid",
	"goal not satisfied",
	"precondition not satisfied",
	"precondition failed",
	"violated precondition",
	"unsuccessful",
)


@dataclass(frozen=True)
class ExternalPlanVerifierResult:
	"""Auditable external verifier outcome with persisted stdout and stderr."""

	attempted: bool
	available: bool
	success: bool | None
	timed_out: bool
	exit_code: int | None
	command: tuple[str, ...]
	stdout_file: str
	stderr_file: str
	error: str | None = None


def run_external_plan_verifier(
	*,
	domain_file: str | Path,
	problem_file: str | Path,
	plan_file: str | Path,
	output_dir: str | Path,
	command: Sequence[str] | str | None = None,
	timeout_seconds: int = 1800,
) -> ExternalPlanVerifierResult:
	"""Run one VAL/IPC-style command without interpreting the temporal goal."""

	command_prefix = _normalize_command(command) or _discover_command()
	output = Path(output_dir).resolve()
	output.mkdir(parents=True, exist_ok=True)
	stdout_file = output / "plan_verifier_stdout.txt"
	stderr_file = output / "plan_verifier_stderr.txt"
	if command_prefix is None:
		error = "No VAL/IPC plan verifier was configured or found on PATH."
		stdout_file.write_text("", encoding="utf-8")
		stderr_file.write_text(error + "\n", encoding="utf-8")
		return ExternalPlanVerifierResult(
			attempted=False,
			available=False,
			success=None,
			timed_out=False,
			exit_code=None,
			command=(),
			stdout_file=str(stdout_file),
			stderr_file=str(stderr_file),
			error=error,
		)
	executable = command_prefix[0]
	if shutil.which(executable) is None and not Path(executable).is_file():
		error = f"Plan verifier executable is unavailable: {executable}"
		stdout_file.write_text("", encoding="utf-8")
		stderr_file.write_text(error + "\n", encoding="utf-8")
		return ExternalPlanVerifierResult(
			attempted=False,
			available=False,
			success=None,
			timed_out=False,
			exit_code=None,
			command=command_prefix,
			stdout_file=str(stdout_file),
			stderr_file=str(stderr_file),
			error=error,
		)
	full_command = (
		*command_prefix,
		str(Path(domain_file).resolve()),
		str(Path(problem_file).resolve()),
		str(Path(plan_file).resolve()),
	)
	try:
		with stdout_file.open("w", encoding="utf-8") as stdout_handle, stderr_file.open(
			"w",
			encoding="utf-8",
		) as stderr_handle:
			completed = subprocess.run(
				full_command,
				stdout=stdout_handle,
				stderr=stderr_handle,
				text=True,
				timeout=max(1, int(timeout_seconds)),
				check=False,
			)
	except subprocess.TimeoutExpired:
		return ExternalPlanVerifierResult(
			attempted=True,
			available=True,
			success=False,
			timed_out=True,
			exit_code=None,
			command=full_command,
			stdout_file=str(stdout_file),
			stderr_file=str(stderr_file),
			error=f"Plan verifier exceeded {timeout_seconds} seconds.",
		)
	output_text = "\n".join(
		(
			stdout_file.read_text(encoding="utf-8", errors="replace"),
			stderr_file.read_text(encoding="utf-8", errors="replace"),
		)
	).lower()
	success = (
		completed.returncode == 0
		and not any(marker in output_text for marker in _FAILURE_MARKERS)
		and any(marker in output_text for marker in _SUCCESS_MARKERS)
	)
	return ExternalPlanVerifierResult(
		attempted=True,
		available=True,
		success=success,
		timed_out=False,
		exit_code=completed.returncode,
		command=full_command,
		stdout_file=str(stdout_file),
		stderr_file=str(stderr_file),
		error=None if success else "External plan verifier did not accept the trace.",
	)


def _normalize_command(command: Sequence[str] | str | None) -> tuple[str, ...] | None:
	if command is None:
		return None
	items = tuple(shlex.split(command)) if isinstance(command, str) else tuple(map(str, command))
	return items or None


def _discover_command() -> tuple[str, ...] | None:
	for env_name in ("VAL_VALIDATE_BIN", "VAL_BIN", "IPC_VALIDATE_BIN"):
		configured = _normalize_command(os.getenv(env_name))
		if configured:
			return configured
	for executable in ("Validate", "validate", "VAL"):
		path = shutil.which(executable)
		if path:
			return (path,)
	return None
