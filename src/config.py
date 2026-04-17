"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://sreality:sreality_pass@localhost:5432/sreality_tracker"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Dashboard
    app_password: str = "changeme"

    # Scraper
    scrape_interval_hours: int = 24
    request_delay_min: float = 1.5
    request_delay_max: float = 3.0

    # Sreality API
    sreality_api_base: str = "https://www.sreality.cz/api/cs/v2"
    sreality_per_page: int = 60

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
