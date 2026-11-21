"""Configure diagnostic output for the backend logger hierarchy."""

import logging

from backend.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Write backend events to stderr once per record at the selected level."""
    backend_logger: logging.Logger = logging.getLogger("backend")
    formatter: logging.Formatter = logging.Formatter(settings.log_format)
    backend_logger.setLevel(settings.log_level)
    backend_logger.propagate = False
    for existing in backend_logger.handlers:
        if existing.name == "backend.stderr":
            existing.setFormatter(formatter)
            return
    handler: logging.StreamHandler = logging.StreamHandler()
    handler.name = "backend.stderr"
    handler.setFormatter(formatter)
    backend_logger.addHandler(handler)
