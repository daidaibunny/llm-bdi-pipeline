"""Configuration tests for shared language-model settings."""

from __future__ import annotations

import sys
from pathlib import Path

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
	sys.path.insert(0, _src_dir)

from utils.config import Config


def test_ltlf_generation_config_reads_stage_specific_fields(monkeypatch):
	monkeypatch.setattr(Config, "_load_env", lambda self: None)
	monkeypatch.setenv("LANGUAGE_MODEL_API_KEY", "sk-shared")
	monkeypatch.setenv("LANGUAGE_MODEL_MODEL", "provider/shared-model")
	monkeypatch.setenv("LANGUAGE_MODEL_BASE_URL", "https://api.shared.example/v1")
	monkeypatch.setenv("LTLF_GENERATION_API_KEY", "sk-ltlf")
	monkeypatch.setenv("LTLF_GENERATION_MODEL", "provider/ltlf-model")
	monkeypatch.setenv("LTLF_GENERATION_TIMEOUT", "120")
	monkeypatch.setenv("LTLF_GENERATION_MAX_TOKENS", "2048")
	monkeypatch.setenv("LTLF_GENERATION_BASE_URL", "https://api.ltlf.example/v1")
	monkeypatch.setenv("LTLF_GENERATION_SESSION_ID", "ltlf-session")

	config = Config()

	assert config.language_model_api_key == "sk-shared"
	assert config.language_model_model == "provider/shared-model"
	assert config.language_model_base_url == "https://api.shared.example/v1"
	assert config.ltlf_generation_api_key == "sk-ltlf"
	assert config.ltlf_generation_model == "provider/ltlf-model"
	assert config.ltlf_generation_timeout == 120
	assert config.ltlf_generation_max_tokens == 2048
	assert config.ltlf_generation_base_url == "https://api.ltlf.example/v1"
	assert config.ltlf_generation_session_id == "ltlf-session"


def test_ltlf_generation_falls_back_to_shared_language_model_config(monkeypatch):
	monkeypatch.setattr(Config, "_load_env", lambda self: None)
	monkeypatch.setenv("LANGUAGE_MODEL_API_KEY", "sk-shared")
	monkeypatch.setenv("LANGUAGE_MODEL_MODEL", "provider/shared-model")
	monkeypatch.setenv("LANGUAGE_MODEL_BASE_URL", "https://api.shared.example/v1")
	monkeypatch.delenv("LTLF_GENERATION_API_KEY", raising=False)
	monkeypatch.delenv("LTLF_GENERATION_MODEL", raising=False)
	monkeypatch.delenv("LTLF_GENERATION_BASE_URL", raising=False)

	config = Config()

	assert config.ltlf_generation_api_key == "sk-shared"
	assert config.ltlf_generation_model == "provider/shared-model"
	assert config.ltlf_generation_base_url == "https://api.shared.example/v1"


def test_ltlf_generation_defaults(monkeypatch):
	monkeypatch.setattr(Config, "_load_env", lambda self: None)
	monkeypatch.delenv("LANGUAGE_MODEL_MODEL", raising=False)
	monkeypatch.delenv("LANGUAGE_MODEL_BASE_URL", raising=False)
	monkeypatch.delenv("LTLF_GENERATION_TIMEOUT", raising=False)
	monkeypatch.delenv("LTLF_GENERATION_MAX_TOKENS", raising=False)

	config = Config()

	assert config.ltlf_generation_model == "deepseek-v4-pro"
	assert config.ltlf_generation_base_url == "https://api.deepseek.com"
	assert config.ltlf_generation_timeout == 1000
	assert config.ltlf_generation_max_tokens == 12000
