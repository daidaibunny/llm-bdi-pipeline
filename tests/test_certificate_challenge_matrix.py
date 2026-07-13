from __future__ import annotations

from scripts.run_certificate_challenge_matrix import CHALLENGE_CASES
from scripts.run_certificate_challenge_matrix import METAMORPHIC_CASES
from scripts.run_certificate_challenge_matrix import build_case_command


def test_certificate_matrix_covers_registered_failure_families() -> None:
	assert {case.family for case in CHALLENGE_CASES} == {
		"Binding",
		"Preparation",
		"Progress",
		"Release",
		"Threat",
		"Negative Guard",
		"Numeric Progress",
	}
	assert {case.family for case in METAMORPHIC_CASES} == {
		"Vocabulary Renaming",
		"Parameter Permutation",
		"Object Renaming",
		"Irrelevant Fluent",
		"Negative Renaming",
		"Progress Renaming",
	}


def test_certificate_case_command_runs_one_exact_node() -> None:
	case = CHALLENGE_CASES[0]
	command = build_case_command(case)

	assert command[:4] == ("uv", "run", "pytest", case.node_id)
	assert command[-1] == "--tb=short"
