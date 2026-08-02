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
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 60.0

    # --- Tavily search --------------------------------------------------------
    tavily_api_key: str = ""
    tavily_timeout_seconds: float = 20.0
    tavily_max_results: int = 5
    # Prefer official hosts when searching (comma-separated include domains).
    tavily_include_domains: str = "isa.go.jp,moj.go.jp,gov,go.jp"

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
