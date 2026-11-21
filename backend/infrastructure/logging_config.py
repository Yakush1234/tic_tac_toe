"""Configure diagnostic output for the backend logger hierarchy."""

import logging


def configure_logging(level: int | str = logging.INFO) -> None:
    """Write backend events to stderr once per record at the selected level."""
    backend_logger: logging.Logger = logging.getLogger("backend")
    backend_logger.setLevel(level)
    backend_logger.propagate = False
    if any(handler.name == "backend.stderr" for handler in backend_logger.handlers):
        return
    handler: logging.StreamHandler = logging.StreamHandler()
    handler.name = "backend.stderr"
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    backend_logger.addHandler(handler)
