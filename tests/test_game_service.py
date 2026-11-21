"""Exercise complete application turns against an isolated test repository."""

# Use standard-library unittest assertions throughout this suite.
# ruff: noqa: PT009, PT027

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from typing import Self
from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from backend.application.game_repository import GameNotFoundError
from backend.application.games import BotMoveError, GameService, GameSnapshot
from backend.domain.entities.game import Game
from backend.domain.enums import BoardSize, BotMode, Mark, Player
from backend.domain.interfaces.bot_strategy import BotStrategy
from backend.domain.values import GameSettings, Position


class FakeRepository:
    """Single-threaded transactional storage for use-case tests."""

    def __init__(self: Self) -> None:
        """Start with no saved games."""
        self.games: dict[UUID, Game] = {}

    def create(self: Self, game: Game, previous_id: UUID | None) -> UUID:
        """Publish the prepared game and forget its predecessor."""
        game_id: UUID = uuid4()
        self.games[game_id] = game
        if previous_id is not None:
            self.games.pop(previous_id, None)
        return game_id

    def get(self: Self, game_id: UUID) -> Game:
        """Read an independent copy of the stored game."""
        try:
            return deepcopy(self.games[game_id])
        except KeyError as error:
            raise GameNotFoundError(game_id) from error

    @contextmanager
    def edit(self: Self, game_id: UUID) -> Iterator[Game]:
        """Commit the working copy only if the operation succeeds."""
        game: Game = self.get(game_id)
        yield game
        self.games[game_id] = game


class GameServiceTests(TestCase):
    """Verify observable results, bot dispatch, and rollback."""

    def setUp(self: Self) -> None:
        """Use separate controllable strategies and a fresh repository."""
        self.random: Mock = Mock(spec=BotStrategy)
        self.smart: Mock = Mock(spec=BotStrategy)
        self.service: GameService = GameService(
            FakeRepository(), {BotMode.RANDOM: self.random, BotMode.SMART: self.smart}
        )

    def start(
        self: Self,
        first: Player = Player.HUMAN,
        *,
        settings: GameSettings = GameSettings(),
        previous_id: UUID | None = None,
    ) -> GameSnapshot:
        """Start with a deterministic assignment of X."""
        with patch("backend.domain.entities.game.choice", return_value=first):
            return self.service.start_game(settings, previous_id=previous_id)

    def test_openings_and_replacement(self: Self) -> None:
        """A stale ID is harmless and the chosen strategy makes the opening move."""
        old: GameSnapshot = self.start(previous_id=uuid4())
        self.assertEqual(old.settings, GameSettings())
        self.assertEqual(old.human_mark, Mark.X)
        self.assertTrue(all(cell is Mark.E for row in old.board for cell in row))
        settings: GameSettings = GameSettings(BoardSize.FOUR, BotMode.SMART)
        self.smart.choose_move.return_value = Position(0, 3)
        new: GameSnapshot = self.start(
            Player.BOT, settings=settings, previous_id=old.game_id
        )
        self.assertNotEqual(old.game_id, new.game_id)
        self.assertEqual(new.board[0][3], Mark.X)
        self.assertEqual(new.human_mark, Mark.O)
        self.assertEqual(new.current_player, Player.HUMAN)
        self.assertEqual(self.service.get_game(new.game_id), new)
        self.smart.choose_move.assert_called_once_with(((Mark.E,) * 4,) * 4, Mark.X)
        self.random.choose_move.assert_not_called()
        with self.assertRaises(GameNotFoundError):
            self.service.get_game(old.game_id)
        with self.assertRaises(GameNotFoundError):
            self.service.play_move(old.game_id, Position(0, 0))

    def test_bot_failures_preserve_game(self: Self) -> None:
        """A failed replacement or reply leaves the last committed state intact."""
        old: GameSnapshot = self.start()
        self.random.choose_move.side_effect = RuntimeError("Search failed")
        with self.assertRaises(BotMoveError):
            self.start(Player.BOT, previous_id=old.game_id)
        self.assertEqual(self.service.get_game(old.game_id), old)
        self.random.choose_move.side_effect = None
        self.random.choose_move.return_value = Position(0, 0)
        with self.assertRaises(BotMoveError):
            self.service.play_move(old.game_id, Position(0, 0))
        self.assertEqual(self.service.get_game(old.game_id), old)
        self.random.choose_move.return_value = Position(1, 1)
        updated: GameSnapshot = self.service.play_move(old.game_id, Position(0, 0))
        self.assertEqual(updated.board[0][0], Mark.X)
        self.assertEqual(updated.board[1][1], Mark.O)
        with self.assertRaises(ValueError):
            self.service.play_move(old.game_id, Position(1, 1))
        self.assertEqual(self.service.get_game(old.game_id), updated)
        self.assertEqual(self.random.choose_move.call_count, 3)

    def test_terminal_positions(self: Self) -> None:
        """Human wins, bot wins, and draws stop play at the deciding move."""
        cases: tuple[tuple[tuple[int, ...], tuple[int, ...], Player | None], ...] = (
            ((0, 1, 2), (3, 4), Player.HUMAN),
            ((0, 1, 8), (3, 4, 5), Player.BOT),
            ((0, 2, 3, 7, 8), (1, 4, 5, 6), None),
        )
        for human_moves, bot_moves, winner in cases:
            with self.subTest(winner=winner):
                state: GameSnapshot = self.start()
                self.random.choose_move.reset_mock()
                self.random.choose_move.side_effect = [
                    Position(*divmod(i, 3)) for i in bot_moves
                ]
                for cell in human_moves:
                    state = self.service.play_move(
                        state.game_id, Position(*divmod(cell, 3))
                    )
                self.assertIs(state.winner, winner)
                self.assertEqual(state.is_draw, winner is None)
                self.assertIsNone(state.current_player)
                with self.assertRaises(ValueError):
                    self.service.play_move(state.game_id, Position(0, 0))
                self.assertEqual(self.service.get_game(state.game_id), state)
                self.assertEqual(self.random.choose_move.call_count, len(bot_moves))
