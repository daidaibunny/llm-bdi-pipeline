#!/usr/bin/env python3
"""Run a command with a hard process-tree memory and optional time guard."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Sequence


BYTES_PER_GIB = 1024**3


@dataclass(frozen=True)
class ProcessMemory:
	"""Resident memory usage for a monitored process tree."""

	root_pid: int
	process_count: int
	rss_bytes: int


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--max-rss-gb", type=float, required=True)
	parser.add_argument("--poll-seconds", type=float, default=5.0)
	parser.add_argument("--timeout-seconds", type=float)
	parser.add_argument("--label", default="guarded-command")
	parser.add_argument("command", nargs=argparse.REMAINDER)
	args = parser.parse_args()

	command = tuple(args.command)
	if command and command[0] == "--":
		command = command[1:]
	if not command:
		parser.error("a command after -- is required")
	if args.max_rss_gb <= 0:
		parser.error("--max-rss-gb must be positive")
	if args.poll_seconds <= 0:
		parser.error("--poll-seconds must be positive")
	if args.timeout_seconds is not None and args.timeout_seconds <= 0:
		parser.error("--timeout-seconds must be positive when provided")

	return run_guarded(
		command=command,
		max_rss_bytes=int(args.max_rss_gb * BYTES_PER_GIB),
		poll_seconds=args.poll_seconds,
		timeout_seconds=args.timeout_seconds,
		label=args.label,
	)


def run_guarded(
	*,
	command: Sequence[str],
	max_rss_bytes: int,
	poll_seconds: float,
	timeout_seconds: float | None,
	label: str,
) -> int:
	"""Run command and stop it if its process tree exceeds resource limits."""

	started_at = time.monotonic()
	process = subprocess.Popen(
		tuple(command),
		start_new_session=True,
	)
	try:
		while True:
			return_code = process.poll()
			if return_code is not None:
				return return_code

			memory = process_tree_memory(process.pid)
			if memory.rss_bytes > max_rss_bytes:
				_stop_process_group(process)
				_write_guard_message(
					label=label,
					reason="memory limit exceeded",
					memory=memory,
					limit_bytes=max_rss_bytes,
					elapsed_seconds=time.monotonic() - started_at,
				)
				return 124

			if timeout_seconds is not None and time.monotonic() - started_at > timeout_seconds:
				_stop_process_group(process)
				_write_guard_message(
					label=label,
					reason="timeout exceeded",
					memory=memory,
					limit_bytes=max_rss_bytes,
					elapsed_seconds=time.monotonic() - started_at,
				)
				return 124

			wait_seconds = poll_seconds
			if timeout_seconds is not None:
				remaining = timeout_seconds - (time.monotonic() - started_at)
				wait_seconds = min(wait_seconds, max(remaining, 0.001))
			try:
				return process.wait(timeout=wait_seconds)
			except subprocess.TimeoutExpired:
				continue
	finally:
		if process.poll() is None:
			_stop_process_group(process)


def process_tree_memory(root_pid: int) -> ProcessMemory:
	"""Return total resident memory for root_pid and descendants."""

	rows = _process_rows()
	children_by_parent: dict[int, list[int]] = {}
	rss_by_pid: dict[int, int] = {}
	for pid, parent_pid, rss_kib in rows:
		children_by_parent.setdefault(parent_pid, []).append(pid)
		rss_by_pid[pid] = rss_kib * 1024

	stack = [root_pid]
	seen: set[int] = set()
	total_rss = 0
	while stack:
		pid = stack.pop()
		if pid in seen:
			continue
		seen.add(pid)
		total_rss += rss_by_pid.get(pid, 0)
		stack.extend(children_by_parent.get(pid, ()))
	return ProcessMemory(
		root_pid=root_pid,
		process_count=len(seen),
		rss_bytes=total_rss,
	)


def _process_rows() -> tuple[tuple[int, int, int], ...]:
	result = subprocess.run(
		("ps", "-axo", "pid=,ppid=,rss="),
		check=True,
		capture_output=True,
		text=True,
	)
	rows: list[tuple[int, int, int]] = []
	for line in result.stdout.splitlines():
		parts = line.split()
		if len(parts) != 3:
			continue
		try:
			rows.append((int(parts[0]), int(parts[1]), int(parts[2])))
		except ValueError:
			continue
	return tuple(rows)


def _stop_process_group(process: subprocess.Popen[bytes]) -> None:
	try:
		os.killpg(process.pid, signal.SIGTERM)
	except ProcessLookupError:
		return
	try:
		process.wait(timeout=10)
		return
	except subprocess.TimeoutExpired:
		pass
	try:
		os.killpg(process.pid, signal.SIGKILL)
	except ProcessLookupError:
		return
	process.wait(timeout=10)


def _write_guard_message(
	*,
	label: str,
	reason: str,
	memory: ProcessMemory,
	limit_bytes: int,
	elapsed_seconds: float,
) -> None:
	print(
		(
			f"[resource_guard] {label}: {reason}; "
			f"rss={memory.rss_bytes / BYTES_PER_GIB:.2f}GiB; "
			f"limit={limit_bytes / BYTES_PER_GIB:.2f}GiB; "
			f"processes={memory.process_count}; "
			f"elapsed={elapsed_seconds:.1f}s"
		),
		file=sys.stderr,
		flush=True,
	)


if __name__ == "__main__":
	sys.exit(main())
