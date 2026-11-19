"""Contract for choosing a bot move."""

from typing import Protocol, Self

from backend.domain.enums import Mark
from backend.domain.values import BoardSnapshot, Position


class BotStrategy(Protocol):
    """Select a legal move for the bot from the current board position."""

    def choose_move(self: Self, board: BoardSnapshot, mark: Mark) -> Position:
        """Return an empty cell for the given mark on a board with a legal move."""
        ...
