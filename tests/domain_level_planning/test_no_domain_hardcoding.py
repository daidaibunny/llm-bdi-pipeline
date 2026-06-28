from __future__ import annotations

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
		"src/domains/blocksworld",
		"src/domains/labworkflow",
		"src/domains/transport",
		"src/domains/satellite",
		"src/domains/marsrover",
		"blocks_4_on_2",
	)
	paths = (
		PROJECT_ROOT / "scripts" / "run_final_paper_data.py",
		PROJECT_ROOT / "scripts" / "run_domain_level_experiment_matrix.py",
	)

	violations: list[str] = []
	for path in paths:
		text = path.read_text(encoding="utf-8")
		for token in forbidden_tokens:
			if token in text:
				violations.append(f"{path.name}:{token}")

	assert violations == []
