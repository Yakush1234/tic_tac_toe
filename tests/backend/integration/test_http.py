"""Test request validation, public responses, and game recovery through HTTP."""

import json
from http.client import HTTPConnection, HTTPResponse
from uuid import uuid4

import pytest

from backend.domain.enums import Player
from backend.domain.random_bot import RandomBot
from backend.domain.values import Position


def _request(
    port: int, method: str, path: str, body: str | None = None
) -> tuple[int, bytes]:
    """Send one HTTP request and return its status and raw body."""
    connection: HTTPConnection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body, {"Content-Type": "application/json"})
        response: HTTPResponse = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


@pytest.mark.parametrize("body", [None, "", "{}"], ids=["omitted", "empty", "object"])
def test__empty_start_body_uses_defaults(api_port: int, body: str | None) -> None:
    """Create a 3×3 random game and return its complete opening snapshot."""
    status, raw = _request(api_port, "POST", "/games", body)
    assert status == 201
    snapshot = json.loads(raw)
    assert snapshot["settings"] == {"size": 3, "bot_mode": "random"}
    assert snapshot["board"] == [["E"] * 3] * 3
    assert snapshot["current_player"] == "human"
    assert snapshot["human_mark"] == "X"
    assert snapshot["winner"] is None
    assert snapshot["is_draw"] is False


@pytest.mark.parametrize("size", [3, 4, 5])
@pytest.mark.parametrize("mode", ["random", "smart"])
def test__bot_opening_and_round_trip(
    api_port: int, size: int, mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Expose the bot's opening and read back the exact committed reply."""
    monkeypatch.setattr("backend.domain.entities.game.choice", lambda _: Player.BOT)
    status, raw = _request(
        api_port, "POST", "/games", json.dumps({"size": size, "bot_mode": mode})
    )
    assert status == 201
    game = json.loads(raw)
    assert game["human_mark"] == "O"
    assert game["current_player"] == "human"
    assert game["settings"] == {"size": size, "bot_mode": mode}
    assert len(game["board"]) == size
    assert sum(line.count("X") for line in game["board"]) == 1
    path: str = f"/games/{game['game_id']}"
    row, column = next(
        (r, c)
        for r, line in enumerate(game["board"])
        for c, cell in enumerate(line)
        if cell == "E"
    )
    body: str = json.dumps({"row": row, "column": column})
    status, raw = _request(api_port, "POST", f"{path}/moves", body)
    assert status == 200
    reply = json.loads(raw)
    assert reply["board"][row][column] == "O"
    assert sum(line.count("X") for line in reply["board"]) == 2
    assert _request(api_port, "GET", path) == (200, raw)
    status, raw = _request(api_port, "POST", f"{path}/moves", body)
    assert status == 409
    assert json.loads(raw) == {"detail": "Cell is already occupied"}


@pytest.mark.parametrize(
    "body",
    [
        '{"size": 6}',
        '{"bot_mode":"unknown"}',
        '{"unexpected":1}',
        "{",
        '{"previous_id":"oops"}',
    ],
)
def test__invalid_start_body(api_port: int, body: str) -> None:
    """Reject invalid creation inputs without consuming the repository slot."""
    status, raw = _request(api_port, "POST", "/games", body)
    assert status == 422
    assert json.loads(raw)["detail"]
    assert _request(api_port, "POST", "/games")[0] == 201


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (None, 422),
        ("null", 422),
        ("{}", 422),
        ('{"row":true,"column":0}', 422),
        ('{"row":"0","column":0}', 422),
        ('{"row":-1,"column":0}', 422),
        ('{"row":0,"column":0,"player":"bot"}', 422),
        ('{"row":3,"column":0}', 409),
    ],
)
def test__invalid_move_keeps_snapshot(
    api_port: int, body: str | None, expected: int
) -> None:
    """Reject malformed and out-of-range moves without mutating the game."""
    status, original = _request(api_port, "POST", "/games")
    assert status == 201
    path: str = f"/games/{json.loads(original)['game_id']}"
    status, raw = _request(api_port, "POST", f"{path}/moves", body)
    assert status == expected
    assert json.loads(raw)["detail"]
    assert _request(api_port, "GET", path) == (200, original)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test__missing_or_invalid_game_id(api_port: int, method: str) -> None:
    """Distinguish valid but unknown IDs from malformed IDs."""
    suffix: str = "/moves" if method == "POST" else ""
    body: str | None = '{"row":0,"column":0}' if method == "POST" else None
    status, raw = _request(api_port, method, f"/games/{uuid4()}{suffix}", body)
    assert status == 404
    assert json.loads(raw) == {"detail": "Game not found"}
    assert _request(api_port, method, f"/games/invalid{suffix}", body)[0] == 422


def test__capacity_and_replacement(api_port: int) -> None:
    """Reject extra games at capacity while allowing atomic replacement."""
    status, raw = _request(api_port, "POST", "/games")
    assert status == 201
    previous: str = json.loads(raw)["game_id"]
    status, raw = _request(api_port, "POST", "/games")
    assert status == 503
    assert json.loads(raw) == {"detail": "Game storage is full"}
    status, raw = _request(
        api_port, "POST", "/games", json.dumps({"previous_id": previous})
    )
    assert status == 201
    assert json.loads(raw)["game_id"] != previous
    assert _request(api_port, "GET", f"/games/{previous}")[0] == 404


def test__bot_error_is_generic_and_does_not_commit(
    api_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hide a bot failure and preserve the complete previous HTTP snapshot."""

    def fail(*args: object) -> Position:
        """Simulate a strategy with an internal failure."""
        raise RuntimeError("private bot failure")

    status, original = _request(api_port, "POST", "/games")
    assert status == 201
    path: str = f"/games/{json.loads(original)['game_id']}"
    monkeypatch.setattr(RandomBot, "choose_move", fail)
    status, raw = _request(api_port, "POST", f"{path}/moves", '{"row":0,"column":0}')
    assert status == 500
    assert json.loads(raw) == {"detail": "Internal server error"}
    assert _request(api_port, "GET", path) == (200, original)


def test__final_http_snapshot_and_rejected_late_move(
    api_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return the winning state and reject further moves without changing it."""
    replies = iter([Position(1, 0), Position(1, 1)])
    monkeypatch.setattr(RandomBot, "choose_move", lambda *_: next(replies))
    status, raw = _request(api_port, "POST", "/games")
    assert status == 201
    path: str = f"/games/{json.loads(raw)['game_id']}"
    for column in range(3):
        status, raw = _request(
            api_port, "POST", f"{path}/moves", json.dumps({"row": 0, "column": column})
        )
        assert status == 200
    final = json.loads(raw)
    assert final["winner"] == "human"
    assert final["current_player"] is None
    assert final["is_draw"] is False
    status, error = _request(api_port, "POST", f"{path}/moves", '{"row":2,"column":0}')
    assert status == 409
    assert json.loads(error) == {"detail": "The game has ended"}
    assert _request(api_port, "GET", path) == (200, raw)
