from __future__ import annotations

from evaluation.temporal_compilation import DFABuilder
import pytest


def test_ordered_singleton_sequence_always_uses_ltlf2dfa_converter() -> None:
	atoms = tuple(f"at(ball{index},roomb)" for index in range(1, 31))
	formula = _sequence_formula(atoms)
	builder = DFABuilder()
	converter = _RecordingConverter()
	builder.converter = converter

	payload = builder.build(formula)

	assert converter.formulas == [formula]
	assert payload["construction"] == "generic_ltlf2dfa"
	assert payload["initial_state"] == "1"
	assert payload["accepting_states"] == ["2"]
	assert payload["guarded_transitions"][0]["raw_label"] == "p1"


@pytest.mark.parametrize("formula", ("F(done", "F(done))"))
def test_dfa_builder_rejects_unbalanced_formula_instead_of_repairing(formula: str) -> None:
	with pytest.raises(ValueError, match="unbalanced parentheses"):
		DFABuilder().build(formula)


class _RecordingConverter:
	def __init__(self) -> None:
		self.formulas: list[str] = []

	def convert(self, formula: str):
		self.formulas.append(formula)
		return (
			"digraph MONA_DFA { init -> 1; 1 -> 2; }",
			{
				"construction": "generic_ltlf2dfa",
				"num_states": 2,
				"num_transitions": 1,
				"initial_state": "1",
				"accepting_states": ("2",),
				"guarded_transitions": (
					{"source_state": "1", "target_state": "2", "raw_label": "p1"},
				),
			},
		)


def _sequence_formula(atoms: tuple[str, ...]) -> str:
	formula = f"F({atoms[-1]})"
	for atom in reversed(atoms[:-1]):
		formula = f"F({atom} & X({formula}))"
	return formula
