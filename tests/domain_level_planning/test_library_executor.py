from __future__ import annotations

from pathlib import Path

from domain_level_planning.library_executor import evaluate_library_on_problem
from domain_level_planning.library_synthesis import synthesize_domain_level_asl_library
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_ROOT = PROJECT_ROOT / "src" / "domains" / "blocksworld"
BLOCKS_DOMAIN = BLOCKS_ROOT / "domain.pddl"
BLOCKS_PROBLEMS = tuple(sorted((BLOCKS_ROOT / "problems").glob("p*.pddl")))


def test_lifted_blocksworld_library_from_one_training_problem_solves_first_20() -> None:
	plan_library = synthesize_domain_level_asl_library(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_PROBLEMS[0],),
	).plan_library
	asl = render_plan_library_asl(plan_library)

	assert len(plan_library.plans) == 29
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl

	results = tuple(
		evaluate_library_on_problem(
			plan_library=plan_library,
			domain_file=BLOCKS_DOMAIN,
			problem_file=problem_file,
			max_steps=10000,
			max_depth=1000,
		)
		for problem_file in BLOCKS_PROBLEMS[:20]
	)

	assert [result.problem_name for result in results] == [
		f"p{index:02d}"
		for index in range(1, 21)
	]
	assert all(result.solved for result in results), [
		(result.problem_name, result.failure_reason)
		for result in results
		if not result.solved
	]
	assert [len(result.steps) for result in results] == [
		12,
		18,
		28,
		34,
		38,
		62,
		68,
		88,
		68,
		74,
		94,
		90,
		92,
		88,
		110,
		112,
		134,
		136,
		128,
		182,
	]
