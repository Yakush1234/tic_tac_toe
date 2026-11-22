"""Validated runtime settings shared by the API and logging setup."""

from logging import getLevelNamesMapping
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read backend settings from the process environment and optional .env file."""

    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_title: str = "Tic-Tac-Toe"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    serve_frontend: bool = True
    max_games: int = Field(default=10_000, gt=0)
    bot_search_budget_ms: int = Field(default=200, ge=0, lt=1000)
    log_level: str = "INFO"
    log_format: str = "%(asctime)s %(levelname)s %(name)s %(message)s"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls: type[Self], value: str) -> str:
        """Normalize the configured level and reject unknown logging names."""
        level: str = value.upper()
        if level not in getLevelNamesMapping():
            raise ValueError("Unknown logging level")
        return level
