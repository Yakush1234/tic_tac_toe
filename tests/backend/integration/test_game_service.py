"""Exercise use cases against the transactional in-memory repository."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Self, override
from uuid import UUID, uuid4

import pytest

from backend.application.game_repository import GameNotFoundError
from backend.application.games import BotMoveError, GameService, GameSnapshot
from backend.domain.entities.game import Game
from backend.domain.enums import BotMode, Mark, Player
from backend.domain.exceptions import InvalidMoveError
from backend.domain.interfaces.bot_strategy import BotStrategy
from backend.domain.values import BoardSnapshot, Position
from backend.infrastructure.memory_game_repository import MemoryGameRepository


class ScriptedBot(BotStrategy):
    """Replay predetermined positions or raise a supplied failure."""

    def __init__(self: Self) -> None:
        """Start with a single legal reply."""
        self.replies: list[Position | Exception] = [Position(1, 1)]

    @override
    def choose_move(self: Self, board: BoardSnapshot, mark: Mark) -> Position:
        """Return the next queued position."""
        reply: Position | Exception = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def bot() -> ScriptedBot:
    """Create an independent bot script for each test."""
    return ScriptedBot()


@pytest.fixture
def service(
    game_repository: MemoryGameRepository,
    bot: ScriptedBot,
    monkeypatch: pytest.MonkeyPatch,
) -> GameService:
    """Wire up a predictable human opening and scriptable bot."""
    monkeypatch.setattr("backend.domain.entities.game.choice", lambda _: Player.HUMAN)
    return GameService(game_repository, {BotMode.RANDOM: bot})


@pytest.mark.parametrize("cause", [TimeoutError, InvalidMoveError, IndexError])
def test__failed_reply_rolls_back(
    service: GameService, bot: ScriptedBot, cause: type[Exception]
) -> None:
    """Keep a committed snapshot when the bot fails, then accept a retry."""
    pending: GameSnapshot = service.start_game()
    move: Position = Position(0, 0)
    if cause is InvalidMoveError:
        bot.replies[:] = [move]
    elif cause is IndexError:
        bot.replies.clear()
    else:
        bot.replies[:] = [TimeoutError("Search failed")]
    with pytest.raises(BotMoveError) as error:
        service.play_move(pending.game_id, move)
    assert isinstance(error.value.__cause__, cause)
    assert service.get_game(pending.game_id) == pending
    bot.replies.append(Position(1, 1))
    updated: GameSnapshot = service.play_move(pending.game_id, move)
    assert updated.board[0][0] is updated.human_mark
    assert updated.board[1][1] is Mark.O
    assert updated.current_player is Player.HUMAN
    assert service.get_game(updated.game_id) == updated


@pytest.mark.parametrize(
    ("human_moves", "bot_moves", "winner"),
    [
        ((0, 1, 2), (3, 4), Player.HUMAN),
        ((0, 1, 8), (3, 4, 5), Player.BOT),
        ((0, 2, 3, 7, 8), (1, 4, 5, 6), None),
    ],
)
def test__service_stops_at_the_deciding_move(
    service: GameService,
    bot: ScriptedBot,
    human_moves: tuple[int, ...],
    bot_moves: tuple[int, ...],
    winner: Player | None,
) -> None:
    """Commit the result with exactly the scripted number of bot replies."""
    game: GameSnapshot = service.start_game()
    bot.replies[:] = [Position(*divmod(index, 3)) for index in bot_moves]
    for index in human_moves:
        game = service.play_move(game.game_id, Position(*divmod(index, 3)))
    assert game.winner is winner
    assert game.is_draw is (winner is None)
    assert game.current_player is None
    assert bot.replies == []
    assert service.get_game(game.game_id) == game


def test__failed_bot_opening_keeps_previous_game(
    service: GameService, bot: ScriptedBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retain the existing game if its replacement cannot be opened."""
    original: GameSnapshot = service.start_game(previous_id=uuid4())
    monkeypatch.setattr("backend.domain.entities.game.choice", lambda _: Player.BOT)
    bot.replies[:] = [TimeoutError("Search failed")]
    with pytest.raises(BotMoveError):
        service.start_game(previous_id=original.game_id)
    assert service.get_game(original.game_id) == original


def test__repository_isolates_committed_state(
    game_repository: MemoryGameRepository,
) -> None:
    """Detach created, returned, and edited objects from stored state."""
    game: Game = Game(x_player=Player.HUMAN)
    game_id: UUID = game_repository.create(game)
    game.play(Player.HUMAN, Position(0, 0))
    fetched: Game = game_repository.get(game_id)
    assert fetched.board[0][0] is Mark.E
    fetched.play(Player.HUMAN, Position(0, 1))
    with game_repository.edit(game_id) as working:
        assert working.board[0][1] is Mark.E
        working.play(Player.HUMAN, Position(1, 1))
        assert game_repository.get(game_id).board[1][1] is Mark.E
    working.play(Player.BOT, Position(0, 0))
    assert game_repository.get(game_id).board[1][1] is Mark.X
    assert game_repository.get(game_id).board[0][0] is Mark.E


def test__replacement_cannot_be_undone_by_concurrent_edit(
    game_repository: MemoryGameRepository,
) -> None:
    """Prevent a delayed commit from restoring a retired game."""
    game_id: UUID = game_repository.create(Game(x_player=Player.HUMAN))
    entered: Event = Event()
    release: Event = Event()

    def edit() -> None:
        """Hold a working copy while another thread replaces the game."""
        with game_repository.edit(game_id) as working:
            working.play(Player.HUMAN, Position(0, 0))
            entered.set()
            assert release.wait(5)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(edit)
        try:
            assert entered.wait(5)
            next_id: UUID = game_repository.create(Game(), previous_id=game_id)
        finally:
            release.set()
        with pytest.raises(GameNotFoundError):
            future.result(timeout=5)
    with pytest.raises(GameNotFoundError):
        game_repository.get(game_id)
    assert all(
        cell is Mark.E for row in game_repository.get(next_id).board for cell in row
    )


def test__concurrent_edits_see_previous_commit(
    game_repository: MemoryGameRepository,
) -> None:
    """Start the second edit from the state committed by the first."""
    game_id: UUID = game_repository.create(Game(x_player=Player.HUMAN))
    attempting_edit: Event = Event()

    def edit_reply() -> None:
        """Apply a bot reply that requires the human's committed move."""
        attempting_edit.set()
        with game_repository.edit(game_id) as game:
            assert game.board[0][0] is Mark.X
            game.play(Player.BOT, Position(1, 1))

    with ThreadPoolExecutor(max_workers=1) as executor:
        with game_repository.edit(game_id) as game:
            game.play(Player.HUMAN, Position(0, 0))
            reply = executor.submit(edit_reply)
            assert attempting_edit.wait(5)
        reply.result(timeout=5)

    committed: Game = game_repository.get(game_id)
    assert committed.board[0][0] is Mark.X
    assert committed.board[1][1] is Mark.O
    assert committed.current_player is Player.HUMAN
