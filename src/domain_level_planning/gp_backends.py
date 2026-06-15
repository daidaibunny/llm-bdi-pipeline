"""
Adapters for external generalized-planning learner backends.

These adapters keep paper code outside the main source tree while giving the
pipeline reproducible commands and parseable sketch outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_BACKEND_ROOT = Path(__file__).resolve().parents[2] / ".external" / "gp-backends"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAX_RSS_GB = 16.0
DEFAULT_POLL_SECONDS = 5.0


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
class SketchFeature:
	"""One boolean or numerical feature from an external sketch learner."""

	identifier: str
	kind: str
	expression: str


@dataclass(frozen=True)
class SketchCondition:
	"""One qualitative feature condition in a sketch rule."""

	operator: str
	feature_id: str


@dataclass(frozen=True)
class SketchEffect:
	"""One qualitative feature effect in a sketch rule."""

	operator: str
	feature_id: str


@dataclass(frozen=True)
class SketchRule:
	"""Parsed view of a learner-sketches rule."""

	conditions: tuple[SketchCondition, ...]
	effects: tuple[SketchEffect, ...]
	raw: str


@dataclass(frozen=True)
class SketchPolicy:
	"""Small parsed view of a DLPlan policy sketch file."""

	features: Mapping[str, str]
	rules: tuple[str, ...]
	boolean_features: Mapping[str, str] = field(default_factory=dict)
	numerical_features: Mapping[str, str] = field(default_factory=dict)
	parsed_rules: tuple[SketchRule, ...] = ()


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

	def guarded_command(
		self,
		command: Sequence[str | Path],
		*,
		label: str,
		max_rss_gb: float = DEFAULT_MAX_RSS_GB,
		poll_seconds: float = DEFAULT_POLL_SECONDS,
		timeout_seconds: int | None = None,
	) -> tuple[str, ...]:
		"""Wrap an external learner invocation in the local resource guard."""

		self._require_backend()
		guard: list[str] = [
			"uv",
			"run",
			"python",
			str(PROJECT_ROOT / "scripts" / "resource_guard.py"),
			"--max-rss-gb",
			str(max_rss_gb),
			"--poll-seconds",
			str(poll_seconds),
			"--label",
			label,
		]
		if timeout_seconds is not None:
			guard.extend(("--timeout-seconds", str(timeout_seconds)))
		guard.append("--")
		guard.extend(str(item) for item in command)
		return tuple(guard)

	def h_policy_learner_command(
		self,
		*,
		experiment_script: str,
	) -> tuple[str, ...]:
		"""Command for a pinned hierarchical-policy learner experiment script."""

		self._require_backend()
		script_path = self.manifest.path / "learning" / "experiments" / "scripts" / experiment_script
		return ("bash", str(script_path))

	def d2l_command(
		self,
		*,
		experiment: str,
		python_executable: str | Path = "python3",
		steps: Sequence[int] = (),
	) -> tuple[str, ...]:
		"""Command for a D2L experiment such as blocks:clear."""

		self._require_backend()
		command: list[str] = [
			str(python_executable),
			str(self.manifest.path / "experiments" / "run.py"),
			experiment,
		]
		command.extend(str(step) for step in steps)
		return tuple(command)

	def d2l_docker_run_command(
		self,
		*,
		experiment: str,
		image: str = "d2l-official-env:local",
		workspace: str | Path,
		platform: str = "linux/amd64",
	) -> tuple[str, ...]:
		"""Docker invocation for the D2L paper environment."""

		self._require_backend()
		return (
			"docker",
			"run",
			"--rm",
			"--platform",
			platform,
			"-v",
			f"{self.manifest.path}:/workspace/d2l",
			"-v",
			f"{Path(workspace)}:/workspace/d2l/workspace",
			image,
			experiment,
		)

	def _require_backend(self) -> None:
		if not self.manifest.present:
			raise FileNotFoundError(
				f"External GP backend '{self.manifest.name}' is not installed at "
				f"{self.manifest.path}. Expected {self.manifest.url} at "
				f"{self.manifest.expected_commit}.",
			)


def parse_dlplan_policy(policy_text: str) -> SketchPolicy:
	"""Parse the feature table and rule forms from a DLPlan policy string."""

	boolean_features = _extract_features(policy_text, "booleans")
	numerical_features = _extract_features(policy_text, "numericals")
	features = {
		**boolean_features,
		**numerical_features,
	}
	rules = tuple(_extract_top_level_rules(policy_text))
	return SketchPolicy(
		features=features,
		rules=rules,
		boolean_features=boolean_features,
		numerical_features=numerical_features,
		parsed_rules=tuple(_parse_rule(rule) for rule in rules),
	)


def _extract_features(policy_text: str, section_name: str) -> dict[str, str]:
	section = _extract_form(policy_text, f"(:{section_name}")
	if not section:
		return {}
	return {
		feature_id: feature_repr
		for feature_id, feature_repr in re.findall(
			r'\(([A-Za-z_][A-Za-z0-9_]*|\d+)\s+"([^"]+)"\)',
			section,
		)
	}


def _parse_rule(rule_text: str) -> SketchRule:
	return SketchRule(
		conditions=tuple(
			SketchCondition(operator=operator, feature_id=feature_id)
			for operator, feature_id in _extract_feature_atoms(rule_text, "conditions")
		),
		effects=tuple(
			SketchEffect(operator=operator, feature_id=feature_id)
			for operator, feature_id in _extract_feature_atoms(rule_text, "effects")
		),
		raw=" ".join(rule_text.split()),
	)


def _extract_feature_atoms(rule_text: str, section_name: str) -> tuple[tuple[str, str], ...]:
	section = _extract_form(rule_text, f"(:{section_name}")
	if not section:
		return ()
	return tuple(
		(operator, feature_id)
		for operator, feature_id in re.findall(
			r'\(:([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*|\d+)\)',
			section,
		)
	)


def _extract_form(text: str, marker: str) -> str:
	start = text.find(marker)
	if start == -1:
		return ""
	depth = 0
	in_string = False
	escaped = False
	for index in range(start, len(text)):
		character = text[index]
		if escaped:
			escaped = False
			continue
		if character == "\\" and in_string:
			escaped = True
			continue
		if character == '"':
			in_string = not in_string
			continue
		if in_string:
			continue
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0:
				return text[start : index + 1]
	return ""


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
