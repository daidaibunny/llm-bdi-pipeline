from __future__ import annotations

from evaluation.temporal_compilation import DFABuilder


def test_ordered_singleton_sequence_uses_linear_dfa_fast_path() -> None:
	atoms = tuple(f"at(ball{index},roomb)" for index in range(1, 31))
	formula = _sequence_formula(atoms)

	payload = DFABuilder().build(formula)

	assert payload["construction"] == "ordered_singleton_sequence_fast_path"
	assert payload["num_states"] == 31
	assert payload["num_transitions"] == 61
	assert payload["accepting_states"] == ["31"]
	assert payload["guarded_transitions"][0]["raw_label"] == "~at(ball1,roomb)"
	assert payload["guarded_transitions"][1]["raw_label"] == "at(ball1,roomb)"
	assert payload["guarded_transitions"][-1]["raw_label"] == "true"
	assert all(
		"&" not in transition["raw_label"] and "|" not in transition["raw_label"]
		for transition in payload["guarded_transitions"]
	)


def _sequence_formula(atoms: tuple[str, ...]) -> str:
	formula = f"F({atoms[-1]})"
	for atom in reversed(atoms[:-1]):
		formula = f"F({atom} & X({formula}))"
	return formula
