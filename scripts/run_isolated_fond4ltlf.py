#!/usr/bin/env python3
"""Run pinned FOND4LTLf with a per-case ltlf2dfa/MONA workspace."""

from __future__ import annotations

from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
	"""Redirect ltlf2dfa's fixed automa.mona path, then invoke the official CLI."""

	arguments = list(sys.argv[1:] if argv is None else argv)
	if len(arguments) < 3 or arguments[0] != "--runtime-dir":
		raise SystemExit(
			"usage: run_isolated_fond4ltlf.py --runtime-dir DIR <fond4ltlf args>",
		)
	runtime_dir = Path(arguments[1]).expanduser().resolve()
	runtime_dir.mkdir(parents=True, exist_ok=True)

	# ltlf2dfa 1.0.2 writes every translation to PACKAGE_DIR/automa.mona.
	# Changing this module global preserves the pinned implementation while giving
	# each process a private file, so independent compiler calls cannot overwrite
	# one another's formula.
	from ltlf2dfa import ltlf2dfa as ltlf2dfa_backend

	ltlf2dfa_backend.PACKAGE_DIR = str(runtime_dir)

	from fond4ltlf.__main__ import main as fond4ltlf_main

	fond4ltlf_main.main(
		args=arguments[2:],
		prog_name="fond4ltlf",
		standalone_mode=False,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
