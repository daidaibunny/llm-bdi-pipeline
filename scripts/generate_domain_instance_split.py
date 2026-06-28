#!/usr/bin/env python3
"""Generate a deterministic 2/3-train / 1/3-test split of domain instances.

The training instances are used to synthesize the domain-level AgentSpeak(L) plan
library; the held-out test instances supply the goals (converted to LTLf by the
NL-to-LTLf generator) that check whether the library actually works.

The split is deterministic: problems are natural-sorted, the first ~2/3 become the
training set, and the remaining ~1/3 become the held-out test set. A configurable
prefix of the test set is marked as intended temporal-extended-goal (TEG) cases,
since the PDDL itself carries no temporal structure.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOMAINS_ROOT = PROJECT_ROOT / "src" / "domains"
DEFAULT_DOMAINS = ("blocksworld", "marsrover", "satellite", "transport")
DEFAULT_OUTPUT = PROJECT_ROOT / "src" / "benchmark_data" / "instance_split.json"
_NATURAL_TOKEN_PATTERN = re.compile(r"(\d+)")


def natural_sort_key(text: str) -> tuple[tuple[int, object], ...]:
	"""Stable natural-order key so p2 sorts before p10 (no external dependency).

	Each token is wrapped with a type rank (0 for numbers, 1 for text) so numeric
	and textual segments never compare across types, even when a filename starts
	with a digit.
	"""

	return tuple(
		(0, int(token)) if token.isdigit() else (1, token)
		for token in _NATURAL_TOKEN_PATTERN.split(str(text))
		if token != ""
	)


def split_problem_files(
	problem_files: Sequence[Path],
	*,
	train_ratio: float = 2.0 / 3.0,
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
	"""Split natural-sorted problem files into (train, test) by the given ratio."""

	ordered = tuple(sorted(problem_files, key=lambda path: natural_sort_key(path.name)))
	total = len(ordered)
	if total == 0:
		return (), ()
	train_count = round(total * train_ratio)
	train_count = max(1, min(train_count, total - 1)) if total > 1 else total
	return ordered[:train_count], ordered[train_count:]


def build_domain_split(
	*,
	domain: str,
	domains_root: Path,
	train_ratio: float,
	teg_count: int,
) -> dict[str, object]:
	"""Build the train/test split manifest entry for one domain."""

	problems_dir = domains_root / domain / "problems"
	if not problems_dir.is_dir():
		raise FileNotFoundError(f"Missing problems directory for domain {domain!r}: {problems_dir}")
	problem_files = tuple(problems_dir.glob("*.pddl"))
	if not problem_files:
		raise ValueError(f"No PDDL problems found for domain {domain!r} under {problems_dir}")
	train, test = split_problem_files(problem_files, train_ratio=train_ratio)
	teg_test = test[: max(0, teg_count)]
	return {
		"domain": domain,
		"domain_file": _relative(domains_root / domain / "domain.pddl"),
		"train": [_relative(path) for path in train],
		"test": [_relative(path) for path in test],
		"teg_test": [_relative(path) for path in teg_test],
		"train_count": len(train),
		"test_count": len(test),
	}


def _relative(path: Path) -> str:
	resolved = path.resolve()
	try:
		return str(resolved.relative_to(PROJECT_ROOT))
	except ValueError:
		return str(resolved)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--domain",
		action="append",
		default=[],
		help="Domain name to split. Repeat for multiple; defaults to the four supported domains.",
	)
	parser.add_argument(
		"--domains-root",
		type=Path,
		default=DEFAULT_DOMAINS_ROOT,
		help="Root directory containing <domain>/problems/*.pddl.",
	)
	parser.add_argument(
		"--train-ratio",
		type=float,
		default=2.0 / 3.0,
		help="Fraction of instances used for training (default 2/3).",
	)
	parser.add_argument(
		"--teg-count",
		type=int,
		default=2,
		help="Number of leading held-out test cases marked as intended TEG goals.",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=DEFAULT_OUTPUT,
		help="Output split-manifest JSON path.",
	)
	args = parser.parse_args()

	domains = tuple(args.domain) or DEFAULT_DOMAINS
	domains_root = args.domains_root.resolve()
	manifest = {
		"version": 1,
		"split_kind": "deterministic_natural_sort_train_test",
		"train_ratio": args.train_ratio,
		"domains": {
			domain: build_domain_split(
				domain=domain,
				domains_root=domains_root,
				train_ratio=args.train_ratio,
				teg_count=args.teg_count,
			)
			for domain in domains
		},
	}
	output_path = args.output.resolve()
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
	for domain, entry in manifest["domains"].items():
		print(f"{domain}: train={entry['train_count']} test={entry['test_count']}")
	print(f"wrote {output_path}")


if __name__ == "__main__":
	main()
