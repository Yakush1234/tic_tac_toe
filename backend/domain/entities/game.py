"""Turn order, mark assignment, and game outcomes."""

from secrets import choice
from typing import Self

from backend.domain.entities.board import Board
from backend.domain.enums import Mark, Player
from backend.domain.values import BoardSnapshot, GameSettings, Position


class Game:
    """A two-player game in which X starts and participants alternate turns."""

    def __init__(
        self: Self, settings: GameSettings = GameSettings(), *, x_player: Player | None = None
    ) -> None:
        """Start a game, assigning X at random unless its owner is supplied."""
        if x_player is None:
            x_player = choice(tuple(Player))
        elif not isinstance(x_player, Player):
            raise ValueError("Unknown player")
        self._settings: GameSettings = settings
        self._board: Board = Board(settings.size)
        self._x_player: Player = x_player
        self._current_player: Player | None = x_player
        self._winner: Player | None = None

    @property
    def settings(self: Self) -> GameSettings:
        """Return the settings selected when this game started."""
        return self._settings

    @property
    def board(self: Self) -> BoardSnapshot:
        """Return an immutable snapshot of the board after the latest move."""
        return self._board.snapshot()

    @property
    def current_player(self: Self) -> Player | None:
        """Return the player to move, or None after the game ends."""
        return self._current_player

    @property
    def winner(self: Self) -> Player | None:
        """Return the winner, or None for an ongoing or drawn game."""
        return self._winner

    @property
    def is_draw(self: Self) -> bool:
        """Return whether the board filled up without a winning line."""
        return self._current_player is None and self._winner is None

    def mark_for(self: Self, player: Player) -> Mark:
        """Return the mark assigned to this participant for this game."""
        if not isinstance(player, Player):
            raise ValueError("Unknown player")
        return Mark.X if player is self._x_player else Mark.O

    def play(self: Self, player: Player, position: Position) -> None:
        """Apply a legal move, then record a win or draw or pass the turn."""
        if self._current_player is None:
            raise ValueError("The game has ended")
        if player is not self._current_player:
            raise ValueError("It is the other player's turn")

        mark: Mark = self.mark_for(player)
        self._board.place(position, mark)
        if self._board.has_winning_line(mark):
            self._winner = player
            self._current_player = None
        elif self._board.is_full():
            self._current_player = None
        else:
            self._current_player = player.opponent
