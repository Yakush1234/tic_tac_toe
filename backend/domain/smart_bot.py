"""Exact three-by-three play and time-bounded search on larger boards."""

from collections.abc import Iterator
from functools import cache
from time import monotonic
from typing import Self, override

from backend.domain.entities.board import has_winning_line
from backend.domain.enums import Mark
from backend.domain.interfaces.bot_strategy import BotStrategy
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


def _evaluate(board: BoardSnapshot, mark: Mark, opponent: Mark) -> int:
    """Score open lines from the current player's perspective."""
    n: int = len(board)
    lines: tuple[tuple[Mark, ...], ...] = (
        *board,
        *zip(*board, strict=True),
        tuple(board[i][i] for i in range(n)),
        tuple(board[i][-1 - i] for i in range(n)),
    )
    total: int = 0
    for line in lines:
        own: int = line.count(mark)
        other: int = line.count(opponent)
        if own and not other:
            total += 4**own
        elif other and not own:
            total -= 4**other
    return total


def _search_large_board(
    board: BoardSnapshot,
    moves: list[Position],
    mark: Mark,
    opponent: Mark,
    deadline: float,
) -> Position:
    """Keep the best move from the last completed alpha-beta search depth."""
    # A terminal win outweighs every possible open-line score on a 5x5 board.
    win: int = 1_000_000

    def score(
        state: BoardSnapshot,
        turn: Mark,
        previous: Mark,
        depth: int,
        alpha: int,
        beta: int,
    ) -> int:
        """Return a negamax score, or interrupt the iteration at its deadline."""
        if monotonic() >= deadline:
            raise TimeoutError
        if has_winning_line(state, previous):
            return -win
        if depth == 0:
            return _evaluate(state, turn, previous)
        best: int = -win
        for reply in _empty_cells(state):
            value: int = -score(
                _after_move(state, reply, turn),
                previous,
                turn,
                depth - 1,
                -beta,
                -alpha,
            )
            best = max(best, value)
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best

    chosen: Position = moves[0]
    for depth in range(1, len(moves) + 1):
        candidate: Position = chosen
        highest: int = -win - 1
        try:
            for move in moves:
                value: int = -score(
                    _after_move(board, move, mark),
                    opponent,
                    mark,
                    depth - 1,
                    -win - 1,
                    -highest,
                )
                if value > highest:
                    candidate, highest = move, value
        except TimeoutError:
            break
        chosen = candidate
        if highest == win:
            break
    return chosen


class SmartBot(BotStrategy):
    """Play perfect three-by-three games and search larger boards within a budget."""

    def __init__(self: Self, search_budget_ms: int = 200) -> None:
        """Set the per-move budget for larger boards in milliseconds."""
        if search_budget_ms < 0:
            raise ValueError("Search budget must be nonnegative")
        self._budget_seconds: float = search_budget_ms / 1000

    @override
    def choose_move(self: Self, board: BoardSnapshot, mark: Mark) -> Position:
        """Take a win, block a threat, then select the best available continuation."""
        deadline: float = monotonic() + self._budget_seconds
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

        if len(moves) == 1:
            return moves[0]
        if len(board) != 3:
            return _search_large_board(board, moves, mark, opponent, deadline)

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
