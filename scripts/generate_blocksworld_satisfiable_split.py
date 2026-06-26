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
DEFAULT_BLOCK_COUNTS = (50, 60, 70, 80, 90, 100, 110, 120, 130, 140)


def main() -> None:
	"""Generate deterministic PDDL problems for larger satisfiable evaluation."""

	parser = argparse.ArgumentParser(
		description="Generate satisfiable Blocksworld full-tower PDDL problems.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=DEFAULT_OUTPUT_DIR,
		help="Directory where generated PDDL problems should be written.",
	)
	parser.add_argument(
		"--block-counts",
		default=",".join(str(count) for count in DEFAULT_BLOCK_COUNTS),
		help="Comma-separated object counts, one generated problem per count.",
	)
	args = parser.parse_args()

	files = generate_satisfiable_split(
		output_dir=args.output_dir,
		block_counts=parse_block_counts(args.block_counts),
	)
	print(f"wrote {len(files)} satisfiable Blocksworld problems to {args.output_dir}")


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
