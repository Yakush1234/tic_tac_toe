"""Immutable coordinates, game settings, and board snapshots."""

from dataclasses import dataclass
from typing import Self

from backend.domain.enums import BoardSize, BotMode, Mark

type BoardSnapshot = tuple[tuple[Mark, ...], ...]


@dataclass(frozen=True, slots=True)
class Position:
    """Zero-based row and column of a cell."""

    row: int
    column: int

    def __post_init__(self: Self) -> None:
        """Require integer coordinates; the board checks their bounds."""
        if type(self.row) is not int or type(self.column) is not int:
            raise TypeError("Coordinates must be integers")


@dataclass(frozen=True, slots=True)
class GameSettings:
    """Board size and bot mode fixed for the duration of a game."""

    size: BoardSize = BoardSize.THREE
    bot_mode: BotMode = BotMode.RANDOM

    def __post_init__(self: Self) -> None:
        """Check that the board size and bot mode are supported."""
        if not isinstance(self.size, BoardSize):
            raise ValueError("Unsupported board size")
        if not isinstance(self.bot_mode, BotMode):
            raise ValueError("Unknown bot mode")
