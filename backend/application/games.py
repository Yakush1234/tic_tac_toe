"""Create, retrieve, and play games through the domain and repository contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self
from uuid import UUID

from backend.application.game_repository import GameRepository
from backend.domain.entities.game import Game
from backend.domain.enums import BotMode, Mark, Player
from backend.domain.interfaces.bot_strategy import BotStrategy
from backend.domain.values import BoardSnapshot, GameSettings, Position


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
        self._play_bot_turn(game)
        game_id: UUID = self._repository.create(game, previous_id)
        return GameSnapshot.from_game(game_id, game)

    def get_game(self: Self, game_id: UUID) -> GameSnapshot:
        """Read the latest committed state without advancing the game."""
        return GameSnapshot.from_game(game_id, self._repository.get(game_id))

    def play_move(self: Self, game_id: UUID, position: Position) -> "GameSnapshot":
        """Commit the human move and any bot reply together."""
        game: Game
        with self._repository.edit(game_id) as game:
            game.play(Player.HUMAN, position)
            self._play_bot_turn(game)
            snapshot: GameSnapshot = GameSnapshot.from_game(game_id, game)
        return snapshot

    def _play_bot_turn(self: Self, game: Game) -> None:
        """Ask the selected strategy for a move only when the bot owns the turn."""
        if game.current_player is not Player.BOT:
            return
        try:
            strategy: BotStrategy = self._strategies[game.settings.bot_mode]
            position: Position = strategy.choose_move(
                game.board, game.mark_for(Player.BOT)
            )
            game.play(Player.BOT, position)
        except Exception as error:
            raise BotMoveError("The bot could not complete its move") from error
