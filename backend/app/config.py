from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tennis Scouting Agent API"
    app_env: str = "dev"
    openai_api_key: Optional[str] = None
    postgres_url: str = "postgresql+psycopg://localhost:5432/tennis_scout"
    openai_model: str = "gpt-4o-mini"
    tennis_api_key: Optional[str] = None
    tennis_api_host: str = "tennis-api-atp-wta-itf.p.rapidapi.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
