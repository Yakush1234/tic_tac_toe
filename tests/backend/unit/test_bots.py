"""Verify legal move selection, immediate tactics, and exact play."""

from copy import deepcopy

import pytest

from backend.domain.entities.game import Game
from backend.domain.enums import Mark, Player
from backend.domain.interfaces.bot_strategy import BotStrategy
from backend.domain.random_bot import RandomBot
from backend.domain.smart_bot import SmartBot
from backend.domain.values import BoardSnapshot, Position


@pytest.mark.parametrize("bot", [RandomBot(), SmartBot()], ids=["random", "smart"])
def test__full_board_has_no_move(bot: BotStrategy) -> None:
    """Reject a board without a legal destination."""
    board: BoardSnapshot = ((Mark.X, Mark.O, Mark.X),) * 3
    with pytest.raises(ValueError, match="no empty cells"):
        bot.choose_move(board, Mark.O)


@pytest.mark.parametrize("size", [3, 4, 5])
@pytest.mark.parametrize("bot", [RandomBot(), SmartBot()], ids=["random", "smart"])
def test__single_free_cell(bot: BotStrategy, size: int) -> None:
    """Return the only available position on each supported size."""
    board: BoardSnapshot = tuple(
        tuple(Mark.E if (row, col) == (size - 1, 0) else Mark.X for col in range(size))
        for row in range(size)
    )
    assert bot.choose_move(board, Mark.O) == Position(size - 1, 0)


@pytest.mark.parametrize("size", [3, 4, 5])
@pytest.mark.parametrize("threat", [Mark.X, Mark.O])
def test__smart_fills_gap_in_winning_line(size: int, threat: Mark) -> None:
    """Win or block by filling an interior gap in a diagonal."""
    board: BoardSnapshot = tuple(
        tuple(threat if row == col and row != 1 else Mark.E for col in range(size))
        for row in range(size)
    )
    assert SmartBot(search_budget_ms=0).choose_move(board, Mark.X) == Position(1, 1)


@pytest.mark.parametrize("size", [3, 4, 5])
def test__smart_prioritizes_own_win(size: int) -> None:
    """Win even when the opponent also threatens to complete a line."""
    board: BoardSnapshot = (
        (*((Mark.O,) * (size - 1)), Mark.E),
        (*((Mark.X,) * (size - 1)), Mark.E),
        *(((Mark.E,) * size,) * (size - 2)),
    )
    assert SmartBot().choose_move(board, Mark.X) == Position(1, size - 1)


@pytest.mark.parametrize("size", [4, 5])
def test__smart_keeps_last_complete_search(
    size: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the completed depth-one move when the next iteration times out."""
    board: BoardSnapshot = ((Mark.E,) * size,) * size
    clock = iter([0.0] * (1 + size * size) + [1.0])
    monkeypatch.setattr("backend.domain.smart_bot.monotonic", lambda: next(clock))
    expected: Position = Position(0, 0) if size == 4 else Position(2, 2)
    assert SmartBot().choose_move(board, Mark.X) == expected


@pytest.mark.parametrize("size", [4, 5])
def test__smart_zero_budget_has_legal_fallback(size: int) -> None:
    """Return an empty cell when there is no time to search."""
    board: BoardSnapshot = ((Mark.E,) * size,) * size
    position: Position = SmartBot(search_budget_ms=0).choose_move(board, Mark.X)
    assert board[position.row][position.column] is Mark.E


def test__smart_rejects_invalid_inputs() -> None:
    """Refuse negative budgets and the empty-cell symbol as a player mark."""
    with pytest.raises(ValueError, match="nonnegative"):
        SmartBot(search_budget_ms=-1)
    with pytest.raises(ValueError, match="must place X or O"):
        SmartBot().choose_move(((Mark.E,) * 3,) * 3, Mark.E)


def _check_human_replies(game: Game, bot: SmartBot) -> None:
    """Explore every human move against the bot's actual choice."""
    if game.current_player is None:
        assert game.winner is Player.BOT or game.is_draw
        return
    if game.current_player is Player.BOT:
        game.play(Player.BOT, bot.choose_move(game.board, game.mark_for(Player.BOT)))
        _check_human_replies(game, bot)
        return
    for row, line in enumerate(game.board):
        for column, cell in enumerate(line):
            if cell is Mark.E:
                branch: Game = deepcopy(game)
                branch.play(Player.HUMAN, Position(row, column))
                _check_human_replies(branch, bot)


@pytest.mark.parametrize("first", list(Player))
def test__smart_cannot_lose_on_three_by_three(first: Player) -> None:
    """Check all human replies when the bot plays either mark."""
    _check_human_replies(Game(x_player=first), SmartBot())
