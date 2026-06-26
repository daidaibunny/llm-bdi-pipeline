from __future__ import annotations

from pathlib import Path

from domain_level_planning.goal_mutex import schema_goal_mutexes
from scripts.generate_blocksworld_satisfiable_split import generate_satisfiable_split
from scripts.generate_blocksworld_satisfiable_split import parse_block_counts
from utils.pddl_parser import PDDLParser


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl"
DEFAULT_SPLIT = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "satisfiable-large"


def test_satisfiable_split_generator_writes_full_tower_problems(
	tmp_path: Path,
) -> None:
	files = generate_satisfiable_split(
		output_dir=tmp_path,
		block_counts=(5, 8),
	)
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)

	assert [path.name for path in files] == ["p01.pddl", "p02.pddl"]
	for expected_count, problem_file in zip((5, 8), files):
		problem = PDDLParser.parse_problem(problem_file)
		goal_atoms = tuple(fact.to_signature() for fact in problem.goal_facts)

		assert problem.domain_name == "BLOCKS"
		assert len(problem.objects) == expected_count
		assert len(problem.goal_facts) == expected_count - 1
		assert all(atom.startswith("on(") for atom in goal_atoms)
		assert not schema_goal_mutexes(domain=domain, goal_atoms=goal_atoms)


def test_tracked_satisfiable_large_split_contains_only_consistent_tower_goals() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	files = tuple(sorted(DEFAULT_SPLIT.glob("p*.pddl")))

	assert len(files) == 10
	for problem_file in files:
		problem = PDDLParser.parse_problem(problem_file)
		goal_atoms = tuple(fact.to_signature() for fact in problem.goal_facts)

		assert problem.domain_name == "BLOCKS"
		assert len(problem.objects) >= 50
		assert all(atom.startswith("on(") for atom in goal_atoms)
		assert not schema_goal_mutexes(domain=domain, goal_atoms=goal_atoms)


def test_parse_block_counts_rejects_empty_or_tiny_tower_sizes() -> None:
	assert parse_block_counts("5, 10,15") == (5, 10, 15)

	for raw_counts in ("", "1"):
		try:
			parse_block_counts(raw_counts)
		except ValueError as error:
			assert "Blocksworld tower problems" in str(error) or (
				"At least one block count" in str(error)
			)
		else:
			raise AssertionError(f"Expected invalid block counts to fail: {raw_counts}")
