from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_domain_level_planning_production_code_has_no_blocksworld_special_cases() -> None:
	forbidden_tokens = (
		"blocksworld",
		"blocks_4",
		"stack(",
		"unstack(",
		"pick-up",
		"put-down",
		"arm-empty",
		"on-table",
	)
	paths = tuple(
		path
		for path in (PROJECT_ROOT / "src" / "domain_level_planning").glob("*.py")
		if path.name != "__init__.py"
	)

	violations: list[str] = []
	for path in paths:
		text = path.read_text(encoding="utf-8").lower()
		for token in forbidden_tokens:
			if token in text:
				violations.append(f"{path.name}:{token}")

	assert violations == []


def test_paper_experiment_scripts_use_registry_instead_of_embedded_domain_rows() -> None:
	"""Final-data scripts should not encode benchmark-specific PDDL rows."""

	forbidden_tokens = (
		"/".join(("src", "domains", "blocksworld", "")),
		"/".join(("src", "domains", "lab" + "workflow")),
		"/".join(("src", "domains", "marsrover")),
		"blocks_4_on_2",
	)
	paths = (
		PROJECT_ROOT / "scripts" / "run_final_paper_data.py",
		PROJECT_ROOT / "scripts" / "gp_backend_audit.py",
		PROJECT_ROOT / "scripts" / "materialize_achievement_benchmarks.py",
	)

	violations: list[str] = []
	for path in paths:
		text = path.read_text(encoding="utf-8")
		for token in forbidden_tokens:
			if token in text:
				violations.append(f"{path.name}:{token}")

	assert violations == []


def test_obsolete_generated_benchmark_implementation_names_are_absent() -> None:
	"""Deprecated generated benchmark artifacts should not re-enter current code."""

	forbidden_tokens = (
		"blocksworld_qclear",
		"blocksworld_qon",
		"blocksworld_qbw",
		"run_blocks_train_experiment",
		"learner_sketches_blocksworld_blocks_4_on_2",
		"/".join(("src", "domains", "blocksworld", "")),
		"/".join(("src", "domains", "marsrover")),
		"fixed train/test snapshot",
	)
	scan_roots = (
		PROJECT_ROOT / "README.md",
		PROJECT_ROOT / "TO-DO-LIST.md",
		PROJECT_ROOT / "scripts",
		PROJECT_ROOT / "src",
		PROJECT_ROOT / "tests",
		PROJECT_ROOT / "latex_code" / "aamas_method_paper" / "sections",
		PROJECT_ROOT / "paper_artifacts",
	)
	suffixes = {".bib", ".json", ".md", ".py", ".tex", ".txt"}

	paths: list[Path] = []
	for root in scan_roots:
		if root.is_file():
			paths.append(root)
		else:
			paths.extend(path for path in root.rglob("*") if path.is_file())

	violations: list[str] = []
	for path in paths:
		if path == Path(__file__).resolve():
			continue
		if path.suffix and path.suffix.lower() not in suffixes:
			continue
		relative = path.relative_to(PROJECT_ROOT)
		text = path.read_text(encoding="utf-8", errors="ignore")
		for token in forbidden_tokens:
			if token in text or token in str(relative):
				violations.append(f"{relative}:{token}")

	assert violations == []


def test_benchmark_registry_uses_literature_property_groups() -> None:
	"""Benchmark groups should describe literature properties, not task stories."""

	registry_root = PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals"
	expected_groups = {
		"esho_classical_domains",
		"numeric_fluent_domains",
		"feature_definable_serialized_width_domains",
	}
	control = json.loads((registry_root / "registry.json").read_text(encoding="utf-8"))

	assert set(control["selected_benchmark_property_group_ids"]) == expected_groups
	assert "selected_goal_property_group_ids" not in control

	records = [
		json.loads(path.read_text(encoding="utf-8"))
		for path in registry_root.glob("*/*/benchmark.json")
	]
	assert len(records) == 16
	assert {record["benchmark_property_group_id"] for record in records} == expected_groups
	for record in records:
		assert "goal_property_group_id" not in record
