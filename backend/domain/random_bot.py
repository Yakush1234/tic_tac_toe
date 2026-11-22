"""Random move selection for any supported board size."""

from secrets import choice
from typing import Self, override

from backend.domain.enums import Mark
from backend.domain.interfaces.bot_strategy import BotStrategy
from backend.domain.values import BoardSnapshot, Position


class RandomBot(BotStrategy):
    """Choose uniformly among the empty cells."""

    @override
    def choose_move(self: Self, board: BoardSnapshot, mark: Mark) -> Position:
        """Return a legal position or raise ValueError when the board is full."""
        empty: list[Position] = [
            Position(row, column)
            for row, cells in enumerate(board)
            for column, cell in enumerate(cells)
            if cell is Mark.E
        ]
        if not empty:
            raise ValueError("The board has no empty cells")
        return choice(empty)
