"""Supported board sizes, marks, participants, and bot modes."""

from enum import Enum
from typing import Self


class BoardSize(Enum):
    """Side length of a supported square board, in cells."""

    _value_: int

    THREE = 3
    FOUR = 4
    FIVE = 5


class Mark(Enum):
    """Symbol a player places in an empty cell."""

    _value_: str

    X = "X"
    O = "O"


class Player(Enum):
    """Participant whose mark is assigned when a game starts."""

    _value_: str

    HUMAN = "human"
    BOT = "bot"

    @property
    def opponent(self: Self) -> "Player":
        """Return the other participant in this game."""
        return Player.BOT if self is Player.HUMAN else Player.HUMAN


class BotMode(Enum):
    """Move selection mode chosen for a game."""

    _value_: str

    RANDOM = "random"
    SMART = "smart"
