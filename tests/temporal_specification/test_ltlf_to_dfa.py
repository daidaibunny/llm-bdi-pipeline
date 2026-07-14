from __future__ import annotations

from pathlib import Path

from evaluation.temporal_compilation.ltlf_to_dfa import LTLfToDFA


def test_mona_guard_cubes_expand_into_conjunctive_transition_labels() -> None:
	converter = LTLfToDFA()
	graph = {
		"free_variables": ("do_put_on_b1_b2", "do_clear_b3"),
		"accepting_states": ("2",),
		"init_state": "1",
		"grouped_guards": {
			("1", "2"): ("10", "01"),
		},
	}

	transitions = converter._guarded_transition_records(graph)
	dot = converter._render_mona_graph_as_dot(graph)

	assert [transition["raw_label"] for transition in transitions] == [
		"do_put_on_b1_b2 & ~do_clear_b3",
		"~do_put_on_b1_b2 & do_clear_b3",
	]
	assert "|" not in dot


def test_explicit_mona_executable_does_not_depend_on_parent_path(tmp_path: Path) -> None:
	mona = tmp_path / "mona"
	mona.write_text("#!/bin/sh\n", encoding="utf-8")

	command, environment = LTLfToDFA(mona_executable=mona)._resolve_mona_runtime()

	assert command == str(mona.resolve())
	assert environment["PATH"].split(":")[0] == str(tmp_path)
