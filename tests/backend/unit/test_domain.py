"""Verify the board, game outcomes, and domain input validation."""

from typing import cast

import pytest

from backend.domain.entities.board import Board
from backend.domain.entities.game import Game
from backend.domain.enums import BoardSize, BotMode, Mark, Player
from backend.domain.exceptions import InvalidMoveError
from backend.domain.values import GameSettings, Position


@pytest.mark.parametrize("size", list(BoardSize))
@pytest.mark.parametrize("direction", ["row", "column", "diagonal", "antidiagonal"])
def test__full_line_is_required(size: BoardSize, direction: str) -> None:
    """Recognize all winning directions only after the final mark."""
    board: Board = Board(size)
    n: int = size.value
    lines: dict[str, list[Position]] = {
        "row": [Position(0, i) for i in range(n)],
        "column": [Position(i, 0) for i in range(n)],
        "diagonal": [Position(i, i) for i in range(n)],
        "antidiagonal": [Position(i, n - i - 1) for i in range(n)],
    }
    assert not board.has_winning_line(Mark.E)
    for position in lines[direction][:-1]:
        board.place(position, Mark.X)
    assert not board.has_winning_line(Mark.X)
    board.place(lines[direction][-1], Mark.X)
    assert board.has_winning_line(Mark.X)
    assert not board.has_winning_line(Mark.O)


@pytest.mark.parametrize(
    ("position", "mark", "reason"),
    [
        (Position(-1, 0), Mark.X, "outside"),
        (Position(0, -1), Mark.X, "outside"),
        (Position(3, 0), Mark.X, "outside"),
        (Position(0, 3), Mark.X, "outside"),
        (Position(0, 0), Mark.O, "occupied"),
        (Position(1, 0), Mark.E, "must place X or O"),
    ],
)
def test__invalid_placement_is_atomic(
    position: Position, mark: Mark, reason: str
) -> None:
    """Reject invalid placements without changing any cells."""
    board: Board = Board(BoardSize.THREE)
    board.place(Position(0, 0), Mark.X)
    before = board.snapshot()
    with pytest.raises(InvalidMoveError, match=reason):
        board.place(position, mark)
    assert board.snapshot() == before


@pytest.mark.parametrize("first", list(Player))
def test__x_starts_and_turns_alternate(first: Player) -> None:
    """Enforce the assigned starting player and preserve snapshots."""
    game: Game = Game(x_player=first)
    before = game.board
    assert game.mark_for(first) is Mark.X
    assert game.mark_for(first.opponent) is Mark.O
    with pytest.raises(InvalidMoveError, match="other player's turn"):
        game.play(first.opponent, Position(0, 0))
    assert game.board == before
    game.play(first, Position(0, 0))
    assert before[0][0] is Mark.E
    assert game.board[0][0] is Mark.X
    assert game.current_player is first.opponent


@pytest.mark.parametrize(
    ("moves", "winner"),
    [
        ((0, 3, 1, 4, 2), Player.HUMAN),
        ((0, 3, 1, 4, 8, 5), Player.BOT),
        ((0, 1, 2, 4, 3, 5, 7, 6, 8), None),
        ((0, 1, 4, 2, 5, 3, 7, 6, 8), Player.HUMAN),
    ],
    ids=["human-win", "bot-win", "draw", "win-on-last-cell"],
)
def test__terminal_outcome(moves: tuple[int, ...], winner: Player | None) -> None:
    """Report the deciding outcome and reject any further move."""
    game: Game = Game(x_player=Player.HUMAN)
    for index in moves:
        player: Player | None = game.current_player
        assert player is not None
        game.play(player, Position(*divmod(index, 3)))
    assert game.current_player is None
    assert game.winner is winner
    assert game.is_draw is (winner is None)
    with pytest.raises(InvalidMoveError, match="ended"):
        game.play(Player.HUMAN, Position(2, 2))


@pytest.mark.parametrize("coordinate", [True, "1", 1.5, None])
def test__coordinate_type(coordinate: object) -> None:
    """Require integer coordinates before a move reaches the board."""
    with pytest.raises(TypeError, match="integers"):
        Position(cast(int, coordinate), 0)


def test__unsupported_domain_values() -> None:
    """Reject values outside the domain enums."""
    with pytest.raises(ValueError, match="board size"):
        Board(cast(BoardSize, 6))
    with pytest.raises(ValueError, match="board size"):
        GameSettings(cast(BoardSize, 6))
    with pytest.raises(ValueError, match="bot mode"):
        GameSettings(bot_mode=cast(BotMode, "unknown"))
    with pytest.raises(ValueError, match="Unknown player"):
        Game(x_player=cast(Player, "unknown"))
    with pytest.raises(ValueError, match="Unknown player"):
        Game().mark_for(cast(Player, "unknown"))
