from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for candidate in (PROJECT_ROOT, SRC_ROOT, SCRIPTS_ROOT):
	if str(candidate) not in sys.path:
		sys.path.insert(0, str(candidate))

from generate_domain_instance_split import (  # noqa: E402
	natural_sort_key,
	split_problem_files,
)
from generate_ltlf_dataset import generate_ltlf_dataset  # noqa: E402
from temporal_specification import (  # noqa: E402
	TemporalSpecificationRecord,
	validate_predicate_grounded_temporal_specification,
)


def test_natural_sort_orders_numbers_naturally() -> None:
	names = ["p10.pddl", "p2.pddl", "p1.pddl"]
	assert sorted(names, key=natural_sort_key) == ["p1.pddl", "p2.pddl", "p10.pddl"]


def test_natural_sort_handles_digit_leading_names() -> None:
	names = ["10.pddl", "p1.pddl", "2.pddl"]
	# must not raise on mixed leading-digit vs leading-text names
	ordered = sorted(names, key=natural_sort_key)
	assert ordered[0] == "2.pddl"
	assert "p1.pddl" in ordered


def test_split_is_two_thirds_one_third_and_deterministic() -> None:
	files = [Path(f"p{index:02d}.pddl") for index in range(1, 31)]
	train, test = split_problem_files(files)
	assert len(train) == 20
	assert len(test) == 10
	# contiguous, ordered, disjoint
	assert train[0].name == "p01.pddl"
	assert test[0].name == "p21.pddl"
	assert set(train).isdisjoint(set(test))
	# deterministic
	assert split_problem_files(list(reversed(files))) == (train, test)


def test_split_keeps_at_least_one_train_and_test_for_small_sets() -> None:
	train, test = split_problem_files([Path("p1.pddl"), Path("p2.pddl")])
	assert len(train) >= 1 and len(test) >= 1


class _FakeGenerator:
	"""Offline stand-in: emits a fixed fluent conjunction, validated for real."""

	def __init__(self, **_kwargs) -> None:
		pass

	def generate(self, *, domain, instruction, instruction_id=None, problem_file=None):
		record = TemporalSpecificationRecord(
			instruction_id or "query",
			instruction,
			"on(b4, b2) & on(b3, b1)",
			(),
			problem_file=problem_file,
		)
		return validate_predicate_grounded_temporal_specification(record, domain=domain)


def test_dataset_builder_emits_fluent_atoms(tmp_path) -> None:
	output = tmp_path / "queries_LTLf.json"
	report = generate_ltlf_dataset(
		query_domains=["blocksworld"],
		query_ids=["query_1"],
		regenerate_existing=True,
		generator_factory=_FakeGenerator,
		output=output,
	)
	assert report["generated"] == 1
	payload = json.loads(output.read_text(encoding="utf-8"))
	assert payload["atom_vocabulary"] == "pddl_fluents"
	case = payload["domains"]["blocksworld"]["cases"]["query_1"]
	assert case["ltlf_formula"] == "on(b4, b2) & on(b3, b1)"
	assert case["atoms"] == ["on(b4, b2)", "on(b3, b1)"]
	# no action-style atoms leak into the generated dataset
	assert "do_put_on" not in case["ltlf_formula"]


def test_dataset_builder_reuses_existing_unless_regenerate(tmp_path) -> None:
	output = tmp_path / "queries_LTLf.json"
	generate_ltlf_dataset(
		query_domains=["blocksworld"],
		query_ids=["query_1"],
		regenerate_existing=True,
		generator_factory=_FakeGenerator,
		output=output,
	)
	report = generate_ltlf_dataset(
		query_domains=["blocksworld"],
		query_ids=["query_1"],
		regenerate_existing=False,
		generator_factory=_FakeGenerator,
		output=output,
	)
	assert report["reused"] == 1
	assert report["generated"] == 0
