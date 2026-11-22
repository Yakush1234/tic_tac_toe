"""Tactical move selection and exact minimax search on a three-by-three board."""

from collections.abc import Iterator
from functools import cache
from typing import Self

from backend.domain.entities.board import has_winning_line
from backend.domain.enums import Mark
from backend.domain.values import BoardSnapshot, Position


def _empty_cells(board: BoardSnapshot) -> Iterator[Position]:
    """Yield legal destinations in stable row-major order."""
    for row, cells in enumerate(board):
        for column, cell in enumerate(cells):
            if cell is Mark.E:
                yield Position(row, column)


def _after_move(board: BoardSnapshot, move: Position, mark: Mark) -> BoardSnapshot:
    """Return a hypothetical position with one empty cell filled."""
    row: tuple[Mark, ...] = board[move.row]
    updated: tuple[Mark, ...] = (*row[: move.column], mark, *row[move.column + 1 :])
    return (*board[: move.row], updated, *board[move.row + 1 :])


class SmartBot:
    """Play perfect three-by-three games and use immediate tactics on larger boards."""

    def choose_move(self: Self, board: BoardSnapshot, mark: Mark) -> Position:
        """Take a win, block a threat, then select the best available continuation."""
        moves: list[Position] = list(_empty_cells(board))
        if not moves:
            raise ValueError("The board has no empty cells")
        if mark not in (Mark.X, Mark.O):
            raise ValueError("A move must place X or O")
        opponent: Mark = Mark.O if mark is Mark.X else Mark.X
        for candidate in (mark, opponent):
            for move in moves:
                if has_winning_line(_after_move(board, move, candidate), candidate):
                    return move

        if len(board) != 3 or len(moves) == 1:
            return moves[0]

        @cache
        def score(state: BoardSnapshot, turn: Mark) -> int:
            """Score the position for the side to move under optimal play."""
            previous: Mark = Mark.O if turn is Mark.X else Mark.X
            if has_winning_line(state, previous):
                return -1
            if all(Mark.E not in row for row in state):
                return 0
            best: int = -1
            for reply in _empty_cells(state):
                value: int = -score(_after_move(state, reply, turn), previous)
                best = max(best, value)
                if best == 1:
                    return best
            return best

        return max(
            moves, key=lambda move: -score(_after_move(board, move, mark), opponent)
        )
