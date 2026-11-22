"""Serve isolated FastAPI applications over loopback for HTTP integration tests."""

import socket
from collections.abc import Iterator
from threading import Thread
from time import monotonic, sleep

import pytest
import uvicorn

from backend.config.settings import Settings
from backend.domain.enums import Player
from backend.presentation.api.entrypoint import create_app


@pytest.fixture
def api_port(monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    """Run an isolated, single-slot server on an OS-assigned port."""
    monkeypatch.setattr("backend.domain.entities.game.choice", lambda _: Player.HUMAN)
    settings: Settings = Settings(
        app_title="Test Game",
        max_games=1,
        bot_search_budget_ms=0,
        serve_frontend=False,
        log_level="INFO",
    )
    server: uvicorn.Server = uvicorn.Server(
        uvicorn.Config(create_app(settings), log_level="critical", access_log=False)
    )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port: int = listener.getsockname()[1]
        thread: Thread = Thread(
            target=server.run, kwargs={"sockets": [listener]}, daemon=True
        )
        thread.start()
        try:
            deadline: float = monotonic() + 5
            while not server.started and thread.is_alive() and monotonic() < deadline:
                sleep(0.01)
            assert server.started, "The test HTTP server did not start"
            yield port
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive(), "The test HTTP server did not stop"
