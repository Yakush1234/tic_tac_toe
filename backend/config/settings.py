"""Validated runtime settings shared by the API and logging setup."""

from logging import getLevelNamesMapping
from typing import Self

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read backend settings at startup with optional BACKEND_ overrides."""

    model_config = SettingsConfigDict(env_prefix="BACKEND_", frozen=True)

    app_title: str = "Tic-Tac-Toe"
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
