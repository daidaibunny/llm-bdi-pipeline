#!/usr/bin/env python3
"""
Generate a deterministic satisfiable Blocksworld tower-evaluation split.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "satisfiable-large"
DEFAULT_MIXED_OUTPUT_DIR = (
	PROJECT_ROOT / "src" / "domains" / "blocksworld" / "satisfiable-mixed-large"
)
DEFAULT_BLOCK_COUNTS = (50, 60, 70, 80, 90, 100, 110, 120, 130, 140)
DEFAULT_MIXED_BLOCK_COUNTS = (20, 30, 40, 50, 60, 70, 80, 90, 100, 110)


def main() -> None:
	"""Generate deterministic PDDL problems for larger satisfiable evaluation."""

	parser = argparse.ArgumentParser(
		description="Generate satisfiable Blocksworld full-tower PDDL problems.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=None,
		help="Directory where generated PDDL problems should be written.",
	)
	parser.add_argument(
		"--variant",
		choices=("full-tower", "mixed"),
		default="full-tower",
		help="Problem split shape to generate.",
	)
	parser.add_argument(
		"--block-counts",
		default=None,
		help="Comma-separated object counts, one generated problem per count.",
	)
	parser.add_argument(
		"--target-tower-count",
		type=int,
		default=3,
		help="Number of target towers for the mixed split.",
	)
	args = parser.parse_args()

	if args.variant == "mixed":
		output_dir = args.output_dir or DEFAULT_MIXED_OUTPUT_DIR
		block_counts = parse_block_counts(
			args.block_counts
			or ",".join(str(count) for count in DEFAULT_MIXED_BLOCK_COUNTS),
		)
		files = generate_satisfiable_mixed_split(
			output_dir=output_dir,
			block_counts=block_counts,
			target_tower_count=args.target_tower_count,
		)
	else:
		output_dir = args.output_dir or DEFAULT_OUTPUT_DIR
		block_counts = parse_block_counts(
			args.block_counts
			or ",".join(str(count) for count in DEFAULT_BLOCK_COUNTS),
		)
		files = generate_satisfiable_split(
			output_dir=output_dir,
			block_counts=block_counts,
		)
	print(f"wrote {len(files)} satisfiable Blocksworld problems to {output_dir}")


def parse_block_counts(raw_counts: str) -> tuple[int, ...]:
	"""Parse and validate comma-separated positive block counts."""

	counts: list[int] = []
	for raw_item in str(raw_counts or "").split(","):
		text = raw_item.strip()
		if not text:
			continue
		count = int(text)
		if count < 2:
			raise ValueError("Blocksworld tower problems require at least two blocks.")
		counts.append(count)
	if not counts:
		raise ValueError("At least one block count is required.")
	return tuple(counts)


def generate_satisfiable_split(
	*,
	output_dir: str | Path,
	block_counts: Sequence[int] = DEFAULT_BLOCK_COUNTS,
) -> tuple[Path, ...]:
	"""Write one deterministic full-tower problem per requested object count."""

	destination = Path(output_dir)
	destination.mkdir(parents=True, exist_ok=True)
	files: list[Path] = []
	for index, block_count in enumerate(tuple(block_counts or ()), start=1):
		if block_count < 2:
			raise ValueError("Blocksworld tower problems require at least two blocks.")
		problem_file = destination / f"p{index:02d}.pddl"
		problem_file.write_text(
			render_satisfiable_tower_problem(
				problem_name=f"bw-sat-large-{index:02d}",
				block_count=block_count,
			),
			encoding="utf-8",
		)
		files.append(problem_file)
	return tuple(files)


def generate_satisfiable_mixed_split(
	*,
	output_dir: str | Path,
	block_counts: Sequence[int] = DEFAULT_MIXED_BLOCK_COUNTS,
	target_tower_count: int = 3,
) -> tuple[Path, ...]:
	"""Write deterministic mixed initial-state and multi-tower goal problems."""

	destination = Path(output_dir)
	destination.mkdir(parents=True, exist_ok=True)
	files: list[Path] = []
	for index, block_count in enumerate(tuple(block_counts or ()), start=1):
		if block_count < 2:
			raise ValueError("Blocksworld tower problems require at least two blocks.")
		problem_file = destination / f"p{index:02d}.pddl"
		problem_file.write_text(
			render_satisfiable_mixed_problem(
				problem_name=f"bw-sat-mixed-large-{index:02d}",
				block_count=block_count,
				target_tower_count=target_tower_count,
			),
			encoding="utf-8",
		)
		files.append(problem_file)
	return tuple(files)


def render_satisfiable_tower_problem(
	*,
	problem_name: str,
	block_count: int,
) -> str:
	"""Render a valid STRIPS Blocksworld problem with a full tower goal."""

	if block_count < 2:
		raise ValueError("Blocksworld tower problems require at least two blocks.")
	blocks = tuple(f"b{index}" for index in range(1, block_count + 1))
	init_facts = (
		*(f"(ontable {block})" for block in blocks),
		*(f"(clear {block})" for block in blocks),
		"(handempty)",
	)
	goal_facts = tuple(
		f"(on b{index} b{index - 1})"
		for index in range(2, block_count + 1)
	)
	return "\n".join(
		(
			f"(define (problem {problem_name})",
			" (:domain BLOCKS)",
			" (:objects",
			f"  {_wrap_tokens(blocks)} - block",
			" )",
			" (:init",
			*_indent(init_facts),
			" )",
			" (:goal (and",
			*_indent(goal_facts),
			" ))",
			")",
			"",
		),
	)


def render_satisfiable_mixed_problem(
	*,
	problem_name: str,
	block_count: int,
	target_tower_count: int = 3,
) -> str:
	"""Render a valid problem with nontrivial initial towers and mixed goals."""

	if block_count < 2:
		raise ValueError("Blocksworld tower problems require at least two blocks.")
	if target_tower_count < 1:
		raise ValueError("target_tower_count must be at least one.")
	if target_tower_count > block_count:
		raise ValueError("target_tower_count cannot exceed block_count.")
	blocks = tuple(f"b{index}" for index in range(1, block_count + 1))
	target_towers = _split_evenly(blocks, target_tower_count)
	initial_tower_count = min(block_count, max(2, target_tower_count + 1))
	initial_towers = _split_evenly(_mixed_initial_order(blocks), initial_tower_count)
	init_facts = _initial_facts_from_towers(initial_towers)
	goal_facts = _goal_facts_from_towers(target_towers)
	return "\n".join(
		(
			f"(define (problem {problem_name})",
			" (:domain BLOCKS)",
			" (:objects",
			f"  {_wrap_tokens(blocks)} - block",
			" )",
			" (:init",
			*_indent(init_facts),
			" )",
			" (:goal (and",
			*_indent(goal_facts),
			" ))",
			")",
			"",
		),
	)


def _split_evenly(
	items: Sequence[str],
	part_count: int,
) -> tuple[tuple[str, ...], ...]:
	"""Split items into balanced non-empty ordered groups."""

	if part_count < 1:
		raise ValueError("part_count must be at least one.")
	if part_count > len(items):
		raise ValueError("part_count cannot exceed item count.")
	base_size, remainder = divmod(len(items), part_count)
	groups: list[tuple[str, ...]] = []
	offset = 0
	for group_index in range(part_count):
		size = base_size + (1 if group_index < remainder else 0)
		group = tuple(items[offset : offset + size])
		if not group:
			raise ValueError("balanced split produced an empty group.")
		groups.append(group)
		offset += size
	return tuple(groups)


def _mixed_initial_order(blocks: Sequence[str]) -> tuple[str, ...]:
	"""Return a deterministic order unlikely to match the final tower layout."""

	reversed_blocks = tuple(reversed(tuple(blocks)))
	return reversed_blocks[::2] + reversed_blocks[1::2]


def _initial_facts_from_towers(towers: Sequence[Sequence[str]]) -> tuple[str, ...]:
	"""Render complete Blocksworld initial facts from bottom-to-top towers."""

	facts: list[str] = ["(handempty)"]
	for tower in tuple(tuple(item for item in raw_tower) for raw_tower in towers):
		if not tower:
			continue
		facts.append(f"(ontable {tower[0]})")
		for lower, upper in zip(tower, tower[1:]):
			facts.append(f"(on {upper} {lower})")
		facts.append(f"(clear {tower[-1]})")
	return tuple(facts)


def _goal_facts_from_towers(towers: Sequence[Sequence[str]]) -> tuple[str, ...]:
	"""Render mixed ontable/on achievement goals from bottom-to-top towers."""

	facts: list[str] = []
	for tower in tuple(tuple(item for item in raw_tower) for raw_tower in towers):
		if not tower:
			continue
		facts.append(f"(ontable {tower[0]})")
		for lower, upper in zip(tower, tower[1:]):
			facts.append(f"(on {upper} {lower})")
	return tuple(facts)


def _wrap_tokens(tokens: Sequence[str], *, width: int = 90) -> str:
	lines: list[str] = []
	current = ""
	for token in tuple(tokens or ()):
		next_text = token if not current else f"{current} {token}"
		if len(next_text) > width and current:
			lines.append(current)
			current = token
			continue
		current = next_text
	if current:
		lines.append(current)
	return "\n  ".join(lines)


def _indent(lines: Iterable[str]) -> tuple[str, ...]:
	return tuple(f"  {line}" for line in lines)


if __name__ == "__main__":
	main()
