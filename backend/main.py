"""Initialize the backend runtime."""

from os import environ

from backend.infrastructure.logging_config import configure_logging

configure_logging(environ.get("BACKEND_LOG_LEVEL", "INFO").upper())
