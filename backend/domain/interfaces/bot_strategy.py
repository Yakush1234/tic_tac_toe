"""Contract for choosing a bot move."""

from abc import ABC, abstractmethod
from typing import Self

from backend.domain.enums import Mark
from backend.domain.values import BoardSnapshot, Position


class BotStrategy(ABC):
    """Select a legal move for the bot from the current board position."""

    @abstractmethod
    def choose_move(self: Self, board: BoardSnapshot, mark: Mark) -> Position:
        """Return an empty cell for the given mark on a board with a legal move."""
        raise NotImplementedError
