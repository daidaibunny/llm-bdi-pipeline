"""
Adapters for external generalized-planning learner backends.

These adapters keep paper code outside the main source tree while giving the
pipeline reproducible commands and parseable sketch outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_BACKEND_ROOT = Path(__file__).resolve().parents[2] / ".external" / "gp-backends"


@dataclass(frozen=True)
class BackendManifest:
	"""Pinned metadata for one external generalized-planning backend."""

	name: str
	path: Path
	url: str
	expected_commit: str
	present: bool
	observed_commit: str | None = None


@dataclass(frozen=True)
class SketchPolicy:
	"""Small parsed view of a DLPlan policy sketch file."""

	features: Mapping[str, str]
	rules: tuple[str, ...]


def discover_backend_manifest(
	*,
	root: str | Path = DEFAULT_BACKEND_ROOT,
	name: str,
	url: str,
	commit: str,
) -> BackendManifest:
	"""Return local status for a pinned external backend."""

	root_path = Path(root)
	backend_path = root_path / name
	observed_commit = _observed_git_commit(backend_path)
	return BackendManifest(
		name=name,
		path=backend_path,
		url=url,
		expected_commit=commit,
		present=backend_path.exists(),
		observed_commit=observed_commit,
	)


class GPBackendRunner:
	"""Build reproducible invocations for external generalized-planning code."""

	def __init__(self, manifest: BackendManifest) -> None:
		self.manifest = manifest

	def learner_sketches_command(
		self,
		*,
		domain_file: str | Path,
		problems_directory: str | Path,
		workspace: str | Path,
		python_executable: str | Path = "python3",
		width: int = 1,
		max_states_per_instance: int = 10000,
		max_time_per_instance: int = 10000,
		additional_booleans: Sequence[str] = (),
		additional_numericals: Sequence[str] = (),
	) -> tuple[str, ...]:
		"""Command for the ICAPS sketch learner backend."""

		self._require_backend()
		command: list[str] = [
			str(python_executable),
			str(self.manifest.path / "learning" / "main.py"),
			"--domain_filepath",
			str(Path(domain_file)),
			"--problems_directory",
			str(Path(problems_directory)),
			"--workspace",
			str(Path(workspace)),
			"--width",
			str(width),
			"--max_num_states_per_instance",
			str(max_states_per_instance),
			"--max_time_per_instance",
			str(max_time_per_instance),
		]
		if additional_booleans:
			command.append("--additional_booleans")
			command.extend(additional_booleans)
		if additional_numericals:
			command.append("--additional_numericals")
			command.extend(additional_numericals)
		return tuple(command)

	def h_policy_learner_command(
		self,
		*,
		experiment_script: str,
	) -> tuple[str, ...]:
		"""Command for a pinned hierarchical-policy learner experiment script."""

		self._require_backend()
		script_path = self.manifest.path / "learning" / "experiments" / "scripts" / experiment_script
		return ("bash", str(script_path))

	def _require_backend(self) -> None:
		if not self.manifest.present:
			raise FileNotFoundError(
				f"External GP backend '{self.manifest.name}' is not installed at "
				f"{self.manifest.path}. Expected {self.manifest.url} at "
				f"{self.manifest.expected_commit}.",
			)


def parse_dlplan_policy(policy_text: str) -> SketchPolicy:
	"""Parse the feature table and rule forms from a DLPlan policy string."""

	features: dict[str, str] = {}
	for feature_id, feature_repr in re.findall(r'\((\d+)\s+"([^"]+)"\)', policy_text):
		features[feature_id] = feature_repr
	rules = tuple(_extract_top_level_rules(policy_text))
	return SketchPolicy(features=features, rules=rules)


def _extract_top_level_rules(policy_text: str) -> tuple[str, ...]:
	rules: list[str] = []
	index = 0
	while True:
		start = policy_text.find("(:rule", index)
		if start == -1:
			break
		depth = 0
		end = start
		for end in range(start, len(policy_text)):
			char = policy_text[end]
			if char == "(":
				depth += 1
			elif char == ")":
				depth -= 1
				if depth == 0:
					rules.append(" ".join(policy_text[start : end + 1].split()))
					break
		index = end + 1
	return tuple(rules)


def _observed_git_commit(path: Path) -> str | None:
	head_file = path / ".git" / "HEAD"
	if not head_file.exists():
		return None
	head = head_file.read_text(encoding="utf-8").strip()
	if head.startswith("ref:"):
		ref = head.removeprefix("ref:").strip()
		ref_file = path / ".git" / ref
		if ref_file.exists():
			return ref_file.read_text(encoding="utf-8").strip()
	return head or None
