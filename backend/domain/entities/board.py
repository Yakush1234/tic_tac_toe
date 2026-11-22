"""Cell placement and winning lines on a square board."""

from typing import Self

from backend.domain.enums import BoardSize, Mark
from backend.domain.exceptions import InvalidMoveError
from backend.domain.values import BoardSnapshot, Position


def has_winning_line(cells: BoardSnapshot, mark: Mark) -> bool:
    """Check the full rows, columns and corner-to-corner diagonals for a mark."""
    if mark is Mark.E:
        return False
    indices: range = range(len(cells))
    return (
        any(all(cell is mark for cell in row) for row in cells)
        or any(all(row[col] is mark for row in cells) for col in indices)
        or all(cells[i][i] is mark for i in indices)
        or all(cells[i][-1 - i] is mark for i in indices)
    )


class Board:
    """Square grid that holds marks and detects completed lines."""

    def __init__(self: Self, size: BoardSize) -> None:
        """Create an empty board of the given size."""
        if not isinstance(size, BoardSize):
            raise ValueError("Unsupported board size")
        self._cells: list[list[Mark]] = [
            [Mark.E] * size.value for _ in range(size.value)
        ]

    def snapshot(self: Self) -> BoardSnapshot:
        """Return an immutable row-by-row copy of the current cells."""
        return tuple(tuple(row) for row in self._cells)

    def place(self: Self, position: Position, mark: Mark) -> None:
        """Place a mark in an empty cell or raise ValueError for an invalid move."""
        if mark not in (Mark.X, Mark.O):
            raise InvalidMoveError("A move must place X or O")
        row: int = position.row
        column: int = position.column
        n: int = len(self._cells)
        if not (0 <= row < n and 0 <= column < n):
            raise InvalidMoveError("Cell is outside the board")
        if self._cells[row][column] is not Mark.E:
            raise InvalidMoveError("Cell is already occupied")
        self._cells[row][column] = mark

    def has_winning_line(self: Self, mark: Mark) -> bool:
        """Check whether the mark fills a row, column, or corner-to-corner diagonal."""
        return has_winning_line(self.snapshot(), mark)

    def is_full(self: Self) -> bool:
        """Return whether every cell is occupied by a player."""
        return all(Mark.E not in row for row in self._cells)
