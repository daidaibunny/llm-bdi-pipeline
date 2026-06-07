"""Configuration management for optional language-model integrations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_LANGUAGE_MODEL_BASE_URL = "https://api.deepseek.com"
DEFAULT_LANGUAGE_MODEL_NAME = "deepseek-v4-pro"
DEFAULT_LTLF_GENERATION_TIMEOUT_SECONDS = 1000
DEFAULT_LTLF_GENERATION_SESSION_ID = "ltlf-generation"


class Config:
	"""Configuration manager for shared language-model settings."""

	def __init__(self) -> None:
		self._load_env()

	def _load_env(self) -> None:
		env_path = Path(__file__).parent.parent.parent / ".env"
		if env_path.exists():
			with open(env_path, "r") as handle:
				self._merge_env_lines(handle)

	def _merge_env_lines(self, lines: Iterable[str]) -> None:
		"""Merge dotenv-style lines without overriding explicit shell environment."""

		for raw_line in lines:
			line = raw_line.strip()
			if not line or line.startswith("#"):
				continue
			key, value = line.split("=", 1)
			os.environ.setdefault(key.strip(), value.strip())

	@staticmethod
	def _first_env(*names: str, default: Optional[str] = None) -> Optional[str]:
		for name in names:
			value = os.getenv(name)
			if value is not None and value.strip():
				return value
		return default

	@property
	def language_model_api_key(self) -> Optional[str]:
		return self._first_env("LANGUAGE_MODEL_API_KEY")

	@property
	def language_model_model(self) -> str:
		return self._first_env(
			"LANGUAGE_MODEL_MODEL",
			default=DEFAULT_LANGUAGE_MODEL_NAME,
		) or DEFAULT_LANGUAGE_MODEL_NAME

	@property
	def language_model_base_url(self) -> Optional[str]:
		return self._first_env(
			"LANGUAGE_MODEL_BASE_URL",
			default=DEFAULT_LANGUAGE_MODEL_BASE_URL,
		)

	@property
	def ltlf_generation_api_key(self) -> Optional[str]:
		return self._first_env("LTLF_GENERATION_API_KEY", "LANGUAGE_MODEL_API_KEY")

	@property
	def ltlf_generation_model(self) -> str:
		return self._first_env(
			"LTLF_GENERATION_MODEL",
			"LANGUAGE_MODEL_MODEL",
			default=DEFAULT_LANGUAGE_MODEL_NAME,
		) or DEFAULT_LANGUAGE_MODEL_NAME

	@property
	def ltlf_generation_timeout(self) -> int:
		return max(
			int(
				os.getenv(
					"LTLF_GENERATION_TIMEOUT",
					str(DEFAULT_LTLF_GENERATION_TIMEOUT_SECONDS),
				),
			),
			1,
		)

	@property
	def ltlf_generation_max_tokens(self) -> int:
		return max(int(os.getenv("LTLF_GENERATION_MAX_TOKENS", "12000")), 1)

	@property
	def ltlf_generation_base_url(self) -> Optional[str]:
		return self._first_env(
			"LTLF_GENERATION_BASE_URL",
			"LANGUAGE_MODEL_BASE_URL",
			default=DEFAULT_LANGUAGE_MODEL_BASE_URL,
		)

	@property
	def ltlf_generation_session_id(self) -> str:
		return os.getenv("LTLF_GENERATION_SESSION_ID", DEFAULT_LTLF_GENERATION_SESSION_ID)


config = Config()


def get_config() -> Config:
	"""Get the global configuration instance."""

	return config
