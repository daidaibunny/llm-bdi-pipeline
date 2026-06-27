from __future__ import annotations

import os
from pathlib import Path
import sys
import time

from low_level_planning import FastDownwardPlanner, FastDownwardPlannerConfig
from low_level_planning.pddl_goal import write_goal_problem_variant


def test_goal_problem_variant_reuses_init_and_replaces_goal(tmp_path: Path) -> None:
	base_problem = tmp_path / "problem.pddl"
	base_problem.write_text(
		"""
		(define (problem p1)
		 (:domain BLOCKS)
		 (:objects b1 b2 - block)
		 (:init (handempty) (ontable b1) (clear b1))
		 (:goal (and (ontable b2)))
		)
		""",
		encoding="utf-8",
	)

	generated = write_goal_problem_variant(
		base_problem_file=base_problem,
		goal_literals=("on(b1, b2)", "not clear(b2)"),
		output_file=tmp_path / "generated.pddl",
	)

	text = generated.read_text(encoding="utf-8")
	assert "(:init" in text
	assert "(handempty)" in text
	assert "(on b1 b2)" in text
	assert "(not (clear b2))" in text
	assert "(ontable b2)" not in text


def test_fast_downward_planner_parses_driver_plan_file(tmp_path: Path) -> None:
	driver = tmp_path / "fake-fast-downward.py"
	driver.write_text(
		"""#!/usr/bin/env python3
import sys
from pathlib import Path

plan_file = Path(sys.argv[sys.argv.index("--plan-file") + 1])
plan_file.write_text("(pick-up b1)\\n(stack b1 b2)\\n; cost = 2\\n", encoding="utf-8")
sys.exit(0)
""",
		encoding="utf-8",
	)
	os.chmod(driver, 0o755)
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text("(define (domain BLOCKS))", encoding="utf-8")
	base_problem = tmp_path / "problem.pddl"
	base_problem.write_text(
		"""
		(define (problem p1)
		 (:domain BLOCKS)
		 (:objects b1 b2 - block)
		 (:init (handempty))
		 (:goal (and (handempty)))
		)
		""",
		encoding="utf-8",
	)

	result = FastDownwardPlanner(
		FastDownwardPlannerConfig(executable=str(driver)),
	).solve_transition_goal(
		domain_file=domain_file,
		base_problem_file=base_problem,
		goal_literals=("on(b1, b2)",),
		work_dir=tmp_path / "work",
		task_name="transition",
	)

	assert result.success is True
	assert [action.name for action in result.actions] == ["pick-up", "stack"]
	assert result.actions[1].arguments == ("b1", "b2")


def test_fast_downward_planner_records_missing_executable(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text("(define (domain BLOCKS))", encoding="utf-8")
	base_problem = tmp_path / "problem.pddl"
	base_problem.write_text(
		"""
		(define (problem p1)
		 (:domain BLOCKS)
		 (:objects b1 b2 - block)
		 (:init (handempty))
		 (:goal (and (handempty)))
		)
		""",
		encoding="utf-8",
	)

	result = FastDownwardPlanner(
		FastDownwardPlannerConfig(executable=str(tmp_path / "missing-driver")),
	).solve_transition_goal(
		domain_file=domain_file,
		base_problem_file=base_problem,
		goal_literals=("on(b1, b2)",),
		work_dir=tmp_path / "work",
		task_name="transition",
	)

	assert result.success is False
	assert "Fast Downward executable not found" in str(result.error)
	assert result.generated_problem_file is not None


def test_fast_downward_timeout_terminates_search_process_group(tmp_path: Path) -> None:
	marker = tmp_path / "orphan-child-marker.txt"
	driver = tmp_path / "slow-fast-downward.py"
	driver.write_text(
		f"""#!/usr/bin/env python3
import subprocess
import sys
import time

subprocess.Popen([
	sys.executable,
	"-c",
	"import pathlib, time; time.sleep(0.8); pathlib.Path({str(marker)!r}).write_text('orphan', encoding='utf-8')",
])
time.sleep(10)
""",
		encoding="utf-8",
	)
	os.chmod(driver, 0o755)
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text("(define (domain BLOCKS))", encoding="utf-8")
	base_problem = tmp_path / "problem.pddl"
	base_problem.write_text(
		"""
		(define (problem p1)
		 (:domain BLOCKS)
		 (:objects b1 b2 - block)
		 (:init (handempty))
		 (:goal (and (handempty)))
		)
		""",
		encoding="utf-8",
	)

	result = FastDownwardPlanner(
		FastDownwardPlannerConfig(executable=str(driver), timeout_seconds=0.2),
	).solve_transition_goal(
		domain_file=domain_file,
		base_problem_file=base_problem,
		goal_literals=("on(b1, b2)",),
		work_dir=tmp_path / "work",
		task_name="transition",
	)
	time.sleep(1.0)

	assert result.success is False
	assert "Fast Downward timed out after 0.2 seconds" in str(result.error)
	assert not marker.exists()
