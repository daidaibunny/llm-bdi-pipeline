from __future__ import annotations

import subprocess
import sys
import time


def test_resource_guard_allows_small_command() -> None:
	result = subprocess.run(
		(
			sys.executable,
			"scripts/resource_guard.py",
			"--max-rss-gb",
			"1",
			"--poll-seconds",
			"0.1",
			"--",
			sys.executable,
			"-c",
			"print('ok')",
		),
		check=False,
		capture_output=True,
		text=True,
	)

	assert result.returncode == 0
	assert "ok" in result.stdout


def test_resource_guard_returns_promptly_with_default_poll_interval() -> None:
	started = time.monotonic()
	result = subprocess.run(
		(
			sys.executable,
			"scripts/resource_guard.py",
			"--max-rss-gb",
			"1",
			"--",
			sys.executable,
			"-c",
			"pass",
		),
		check=False,
		capture_output=True,
		text=True,
		timeout=3,
	)

	assert result.returncode == 0
	assert time.monotonic() - started < 2.0


def test_resource_guard_stops_command_over_memory_limit() -> None:
	result = subprocess.run(
		(
			sys.executable,
			"scripts/resource_guard.py",
			"--max-rss-gb",
			"0.001",
			"--poll-seconds",
			"0.1",
			"--label",
			"unit-test",
			"--",
			sys.executable,
			"-c",
			"import time; data = bytearray(20 * 1024 * 1024); time.sleep(5)",
		),
		check=False,
		capture_output=True,
		text=True,
		timeout=10,
	)

	assert result.returncode == 124
	assert "unit-test" in result.stderr
	assert "memory limit exceeded" in result.stderr
