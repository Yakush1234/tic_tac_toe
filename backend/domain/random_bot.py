"""Random move selection for any supported board size."""

from secrets import choice
from typing import Self

from backend.domain.enums import Mark
from backend.domain.values import BoardSnapshot, Position


class RandomBot:
    """Choose uniformly among the empty cells."""

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
