"""Application settings, loaded from the environment (prefix ``TORII_AI_``)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# One env file for the whole monorepo (see /.env.example at the repo root) — this file lives
# at apps/ai/src/torii_ai/config.py, five levels below the root regardless of CWD. In the
# container only `apps/ai` is unpacked, at /app, so there is no fifth level and no env file to
# read: settings come from the environment (compose `env_file:`) instead.
_MODULE_PATH = Path(__file__).resolve()
_REPO_ROOT_ENV_FILE = _MODULE_PATH.parents[4] / ".env" if len(_MODULE_PATH.parents) > 4 else None


class Settings(BaseSettings):
    """Runtime configuration for the Torii AI service."""

    model_config = SettingsConfigDict(
        env_prefix="TORII_AI_",
        env_file=_REPO_ROOT_ENV_FILE,
        extra="ignore",
    )

    service_name: str = "torii-ai"
    log_level: str = "INFO"
    docs_enabled: bool = True

    # --- Groq (OpenAI-compatible) ---------------------------------------------
    # Groq retires model names on its own schedule, and a retired name answers 404
    # model_not_found rather than degrading — so when a call starts failing that way, check
    # https://console.groq.com/docs/models rather than the code. Both names below were
    # current at 2026-08.
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"
    # Optional non-reasoning model used for structured extraction. Reasoning models
    # (e.g. qwen3.6-27b) emit large <think> blocks that exceed the Groq TPM ceiling on
    # multi-page scrapes and truncate before producing JSON; a direct extractor avoids that.
    groq_extract_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 60.0
    # Explicit completion budget — reasoning models emit <think> blocks and otherwise
    # truncate before producing JSON; keep (input + max_tokens) under the Groq TPM limit.
    groq_max_tokens: int = 8000

    # --- NVIDIA NIM (OpenAI-compatible) ----------------------------------------
    nvidia_api_key: str = ""
    nvidia_model: str = "openai/gpt-oss-120b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_max_tokens: int = 4096
    nvidia_timeout_seconds: float = 120.0

    # --- Tavily search --------------------------------------------------------
    tavily_api_key: str = ""
    tavily_timeout_seconds: float = 20.0
    tavily_max_results: int = 5
    # Prefer official hosts when searching (comma-separated include domains).
    tavily_include_domains: str = "isa.go.jp,moj.go.jp,gov,go.jp"

    # --- Scraper budget -------------------------------------------------------
    # Page cap and per-page char cap keep the extraction prompt under the LLM's
    # token-per-minute ceiling; identical bodies are deduplicated by hash.
    scrape_max_pages: int = 6
    scrape_page_chars: int = 2500

    # --- System of record -----------------------------------------------------
    api_base_url: str = "http://localhost:8000"
    service_token: str = ""
    api_timeout_seconds: float = 10.0

    # Session cookie Secure flag (false for local http://).
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
