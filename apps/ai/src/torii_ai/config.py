"""Application settings, loaded from the environment (prefix ``TORII_AI_``)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Torii AI service."""

    model_config = SettingsConfigDict(
        env_prefix="TORII_AI_",
        env_file=".env",
        extra="ignore",
    )

    service_name: str = "torii-ai"
    log_level: str = "INFO"
    docs_enabled: bool = True

    # --- Groq (OpenAI-compatible) ---------------------------------------------
    groq_api_key: str = ""
    groq_model: str = "qwen-qwq-32b"
    # Optional non-reasoning model used for structured extraction. Reasoning models
    # (e.g. qwen3.6-27b) emit large <think> blocks that exceed the Groq TPM ceiling on
    # multi-page scrapes and truncate before producing JSON; a direct extractor avoids that.
    groq_extract_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 60.0
    # Explicit completion budget — reasoning models emit <think> blocks and otherwise
    # truncate before producing JSON; keep (input + max_tokens) under the Groq TPM limit.
    groq_max_tokens: int = 8000

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
