"""Create, retrieve, and play games through the domain and repository contracts."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Self
from uuid import UUID

from backend.application.game_repository import GameRepository
from backend.domain.entities.game import Game
from backend.domain.enums import BotMode, Mark, Player
from backend.domain.interfaces.bot_strategy import BotStrategy
from backend.domain.values import BoardSnapshot, GameSettings, Position

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GameSnapshot:
    """Game state visible to the client after a completed operation."""

    game_id: UUID
    settings: GameSettings
    board: BoardSnapshot
    human_mark: Mark
    current_player: Player | None
    winner: Player | None
    is_draw: bool

    @classmethod
    def from_game(cls: type[Self], game_id: UUID, game: Game) -> Self:
        """Capture the current state without exposing the mutable game."""
        return cls(
            game_id=game_id,
            settings=game.settings,
            board=game.board,
            human_mark=game.mark_for(Player.HUMAN),
            current_player=game.current_player,
            winner=game.winner,
            is_draw=game.is_draw,
        )


class BotMoveError(RuntimeError):
    """The configured strategy could not complete a legal bot move."""


class GameService:
    """Coordinate player actions with bot strategies and game storage."""

    def __init__(
        self: Self,
        repository: GameRepository,
        strategies: Mapping[BotMode, BotStrategy],
    ) -> None:
        """Bind the repository and strategies used by these scenarios."""
        self._repository: GameRepository = repository
        self._strategies: dict[BotMode, BotStrategy] = dict(strategies)

    def start_game(
        self: Self,
        settings: GameSettings = GameSettings(),
        *,
        previous_id: UUID | None = None,
    ) -> GameSnapshot:
        """Prepare the opening position before replacing any previous game."""
        game: Game = Game(settings)
        bot_ms: float | None = self._play_bot_turn(game)
        game_id: UUID = self._repository.create(game, previous_id)
        snapshot: GameSnapshot = GameSnapshot.from_game(game_id, game)
        ref: str = game_id.hex[:8]
        logger.info(
            "Game started game=%s previous=%s size=%d mode=%s x_player=%s",
            ref,
            previous_id.hex[:8] if previous_id else "-",
            settings.size.value,
            settings.bot_mode.value,
            Player.HUMAN.value if snapshot.human_mark is Mark.X else Player.BOT.value,
        )
        if bot_ms is not None:
            logger.debug("Opening bot move game=%s search_ms=%.2f", ref, bot_ms)
        return snapshot

    def get_game(self: Self, game_id: UUID) -> GameSnapshot:
        """Read the latest committed state without advancing the game."""
        return GameSnapshot.from_game(game_id, self._repository.get(game_id))

    def play_move(self: Self, game_id: UUID, position: Position) -> "GameSnapshot":
        """Commit the human move and any bot reply together."""
        game: Game
        with self._repository.edit(game_id) as game:
            game.play(Player.HUMAN, position)
            bot_ms: float | None = self._play_bot_turn(game)
            snapshot: GameSnapshot = GameSnapshot.from_game(game_id, game)
        ref: str = game_id.hex[:8]
        logger.debug(
            "Move committed game=%s row=%d column=%d bot_search_ms=%s",
            ref,
            position.row,
            position.column,
            f"{bot_ms:.2f}" if bot_ms is not None else "-",
        )
        if snapshot.current_player is None:
            logger.info(
                "Game finished game=%s winner=%s",
                ref,
                snapshot.winner.value if snapshot.winner else "draw",
            )
        return snapshot

    def _play_bot_turn(self: Self, game: Game) -> float | None:
        """Apply the bot reply and return search time in milliseconds, if it played."""
        if game.current_player is not Player.BOT:
            return None
        try:
            strategy: BotStrategy = self._strategies[game.settings.bot_mode]
            started: float = perf_counter()
            position: Position = strategy.choose_move(
                game.board, game.mark_for(Player.BOT)
            )
            elapsed_ms: float = (perf_counter() - started) * 1000
            game.play(Player.BOT, position)
            return elapsed_ms
        except Exception as error:
            raise BotMoveError("The bot could not complete its move") from error
