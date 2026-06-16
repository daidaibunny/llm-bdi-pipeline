"""
Adapters for external generalized-planning learner backends.

These adapters keep paper code outside the main source tree while giving the
pipeline reproducible commands and parseable sketch outputs.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_BACKEND_ROOT = Path(__file__).resolve().parents[2] / ".external" / "gp-backends"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAX_RSS_GB = 16.0
DEFAULT_POLL_SECONDS = 5.0

PINNED_BACKENDS = (
	{
		"name": "learner-sketches",
		"url": "https://github.com/bonetblai/learner-sketches.git",
		"commit": "7a7ea6a6356035afa16ed958b53d8edc86994e0a",
	},
	{
		"name": "h-policy-learner",
		"url": "https://github.com/drexlerd/h-policy-learner.git",
		"commit": "03e345537208ab804c1f4958bf183b65d4863a62",
	},
	{
		"name": "d2l",
		"url": "https://github.com/rleap-project/d2l.git",
		"commit": "0620e169c894d79b3c84f435dba1462996f7c270",
	},
)

BACKEND_RESEARCH_PROFILES = {
	"learner-sketches": {
		"paper_role": "serialized-width sketch learner for qualitative DLPlan policies",
		"preferred_use": "external learned sketch evidence for conservative feature binding",
		"input_artifacts": (
			"PDDL domain",
			"training PDDL problems",
			"width bound",
		),
		"output_artifacts": (
			"feature_rule_policy",
			"raw_policy",
			"minimized_policy",
		),
		"reusable_evidence": (
			"Layer B/C sketch evidence",
			"DLPlan feature vocabulary",
			"qualitative feature conditions and effects",
		),
		"known_failure_modes": (
			"unsupported_dlplan_feature_binding",
			"vocabulary_mismatch",
			"missing_policy_artifact",
		),
		"resource_profile": {
			"execution_environment": "local Python with resource_guard.py",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"current_consumption_role": {
			"drives_layer_b": True,
			"drives_layer_c": True,
			"consumed_by_synthesis": True,
			"consumption_mode": "parsed_bound_policy_rules",
			"blocking_gap": None,
		},
	},
	"h-policy-learner": {
		"paper_role": "hierarchical policy learner for reusable generalized policies",
		"preferred_use": "backend audit and representation baseline",
		"input_artifacts": (
			"PDDL-like benchmark tasks",
			"paper experiment scripts",
		),
		"output_artifacts": (
			"hierarchical policy",
			"experiment logs",
		),
		"reusable_evidence": (
			"policy-reuse representation baseline",
			"hierarchical policy language comparison",
		),
		"known_failure_modes": (
			"missing_backend",
			"unmapped_policy_language",
			"environment_reproduction_gap",
		),
		"resource_profile": {
			"execution_environment": "paper scripts; guarded before long runs",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"current_consumption_role": {
			"drives_layer_b": False,
			"drives_layer_c": False,
			"consumed_by_synthesis": False,
			"consumption_mode": "audit_only_representation_baseline",
			"blocking_gap": "no_verified_policy_to_lifted_asl_adapter",
		},
	},
	"d2l": {
		"paper_role": "description-logic policy learner baseline",
		"preferred_use": "feature-learning and generalized-policy baseline audit",
		"input_artifacts": (
			"paper benchmark selector",
			"Docker/apptainer-compatible environment",
		),
		"output_artifacts": (
			"description_logic_policy",
			"experiment logs",
		),
		"reusable_evidence": (
			"description-logic feature templates",
			"generalized-policy baseline behavior",
		),
		"known_failure_modes": (
			"pin_mismatch",
			"docker_image_missing",
			"unmapped_policy_language",
		),
		"resource_profile": {
			"execution_environment": "Docker linux/amd64 paper environment",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"current_consumption_role": {
			"drives_layer_b": False,
			"drives_layer_c": False,
			"consumed_by_synthesis": False,
			"consumption_mode": "audit_only_feature_policy_baseline",
			"blocking_gap": "no_verified_d2l_policy_parser_or_asl_binding",
		},
	},
}


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


@dataclass(frozen=True)
class LearnerSketchesRunConfig:
	"""Configuration for one guarded learner-sketches training run."""

	domain_file: str | Path
	problems_directory: str | Path
	workspace: str | Path
	width: int = 1
	python_executable: str | Path | None = None
	max_states_per_instance: int = 10000
	max_time_per_instance: int = 10000
	max_rss_gb: float = DEFAULT_MAX_RSS_GB
	poll_seconds: float = DEFAULT_POLL_SECONDS
	timeout_seconds: int | None = None
	additional_booleans: tuple[str, ...] = ()
	additional_numericals: tuple[str, ...] = ()
	use_resource_guard: bool = True


@dataclass(frozen=True)
class LearnerSketchesRunResult:
	"""Result of one learner-sketches training run and discovered policies."""

	command: tuple[str, ...]
	workspace: Path
	returncode: int
	policy_file: Path | None
	raw_policy_file: Path | None
	stdout: str
	stderr: str

	@property
	def succeeded(self) -> bool:
		return self.returncode == 0 and self.policy_file is not None

	def to_dict(self) -> dict[str, object]:
		return {
			"command": list(self.command),
			"workspace": str(self.workspace),
			"returncode": self.returncode,
			"policy_file": str(self.policy_file) if self.policy_file is not None else None,
			"raw_policy_file": (
				str(self.raw_policy_file)
				if self.raw_policy_file is not None
				else None
			),
			"stdout": self.stdout,
			"stderr": self.stderr,
			"succeeded": self.succeeded,
		}


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


def backend_audit_matrix(
	*,
	root: str | Path = DEFAULT_BACKEND_ROOT,
) -> tuple[dict[str, object], ...]:
	"""Return paper-backend audit evidence without running external learners."""

	entries: list[dict[str, object]] = []
	for backend in PINNED_BACKENDS:
		manifest = discover_backend_manifest(
			root=root,
			name=backend["name"],
			url=backend["url"],
			commit=backend["commit"],
		)
		profile = BACKEND_RESEARCH_PROFILES[manifest.name]
		pin_status = _pin_status(manifest)
		failures = _backend_failure_modes(manifest=manifest, pin_status=pin_status)
		entries.append(
			{
				"name": manifest.name,
				"url": manifest.url,
				"path": str(manifest.path),
				"expected_commit": manifest.expected_commit,
				"observed_commit": manifest.observed_commit,
				"present": manifest.present,
				"pin_status": pin_status,
				"paper_role": profile["paper_role"],
				"preferred_use": profile["preferred_use"],
				"input_artifacts": list(profile["input_artifacts"]),
				"output_artifacts": list(profile["output_artifacts"]),
				"reusable_evidence": list(profile["reusable_evidence"]),
				"failure_modes": failures,
				"known_failure_modes": list(profile["known_failure_modes"]),
				"resource_profile": dict(profile["resource_profile"]),
				"current_consumption_role": dict(profile["current_consumption_role"]),
			},
		)
	return tuple(entries)


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


def run_learner_sketches(
	*,
	manifest: BackendManifest,
	config: LearnerSketchesRunConfig,
	env: Mapping[str, str] | None = None,
) -> LearnerSketchesRunResult:
	"""Run learner-sketches with guards and return the minimized policy artifact."""

	runner = GPBackendRunner(manifest)
	workspace = Path(config.workspace)
	workspace.mkdir(parents=True, exist_ok=True)
	python_executable = (
		config.python_executable
		if config.python_executable is not None
		else _default_backend_python(manifest)
	)
	command = runner.learner_sketches_command(
		domain_file=config.domain_file,
		problems_directory=config.problems_directory,
		workspace=workspace,
		python_executable=python_executable,
		width=config.width,
		max_states_per_instance=config.max_states_per_instance,
		max_time_per_instance=config.max_time_per_instance,
		additional_booleans=config.additional_booleans,
		additional_numericals=config.additional_numericals,
	)
	if config.use_resource_guard:
		command = runner.guarded_command(
			command,
			label=f"learner-sketches:{workspace.name}",
			max_rss_gb=config.max_rss_gb,
			poll_seconds=config.poll_seconds,
			timeout_seconds=config.timeout_seconds,
		)
	process = subprocess.run(
		command,
		check=False,
		capture_output=True,
		text=True,
		env=dict(env) if env is not None else None,
	)
	policy_file = discover_learner_sketches_policy_file(workspace, width=config.width)
	raw_policy_file = discover_learner_sketches_policy_file(
		workspace,
		width=config.width,
		minimized=False,
	)
	return LearnerSketchesRunResult(
		command=command,
		workspace=workspace,
		returncode=process.returncode,
		policy_file=policy_file,
		raw_policy_file=raw_policy_file,
		stdout=process.stdout,
		stderr=process.stderr,
	)


def discover_learner_sketches_policy_file(
	workspace: str | Path,
	*,
	width: int,
	minimized: bool = True,
) -> Path | None:
	"""Return learner-sketches policy file path if the expected artifact exists."""

	output_dir = Path(workspace) / "output"
	name = f"sketch_minimized_{width}.txt" if minimized else f"sketch_{width}.txt"
	path = output_dir / name
	return path if path.exists() else None


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


def _pin_status(manifest: BackendManifest) -> str:
	if not manifest.present:
		return "missing"
	if manifest.observed_commit is None:
		return "unknown"
	if manifest.observed_commit.startswith(manifest.expected_commit[:12]):
		return "ok"
	return "mismatch"


def _backend_failure_modes(
	*,
	manifest: BackendManifest,
	pin_status: str,
) -> list[str]:
	failures: list[str] = []
	if not manifest.present:
		failures.append("missing_backend")
	elif pin_status == "mismatch":
		failures.append("pin_mismatch")
	elif pin_status == "unknown":
		failures.append("unknown_git_commit")
	return failures


def _default_backend_python(manifest: BackendManifest) -> str:
	candidates = (
		manifest.path.parent / ".venv" / "bin" / "python",
		manifest.path / ".venv" / "bin" / "python",
	)
	for candidate in candidates:
		if candidate.exists():
			return str(candidate)
	return shutil.which("python3") or "python3"
