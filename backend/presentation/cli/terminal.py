"""Translate terminal input and output to the shared game scenarios."""

from collections.abc import Callable
from typing import Self
from uuid import UUID

from backend.application.games import BotMoveError, GameService, GameSnapshot
from backend.domain.enums import BoardSize, BotMode, Mark, Player
from backend.domain.exceptions import InvalidMoveError
from backend.domain.values import GameSettings, Position


class _QuitSessionError(Exception):
    """The player entered the quit command."""


class TerminalGame:
    """Interact with one human player for the lifetime of a terminal session."""

    def __init__(
        self: Self,
        service: GameService,
        read: Callable[[str], str] = input,
        write: Callable[[str], None] = print,
    ) -> None:
        """Bind the game service and the terminal input and output functions."""
        self._service: GameService = service
        self._read: Callable[[str], str] = read
        self._write: Callable[[str], None] = write

    def run(self: Self) -> None:
        """Start games until the player declines a replay or quits."""
        self._write("Tic-tac-toe. Enter q at any prompt to quit.")
        settings: GameSettings = GameSettings()
        previous_id: UUID | None = None
        try:
            while True:
                settings = self._read_settings(settings)
                try:
                    game: GameSnapshot = self._service.start_game(
                        settings, previous_id=previous_id
                    )
                except BotMoveError:
                    self._write("The bot could not start the game. Please try again.")
                    continue
                previous_id = game.game_id
                self._play(game)
                if not self._choose(
                    "Play again [y/N]: ", {"y": True, "n": False, "": False}
                ):
                    break
        except (_QuitSessionError, EOFError, KeyboardInterrupt):
            pass
        self._write("Goodbye.")

    def _read_settings(self: Self, defaults: GameSettings) -> GameSettings:
        """Read the board size and bot mode with defaults from the last selection."""
        sizes: dict[str, BoardSize] = {str(size.value): size for size in BoardSize}
        modes: dict[str, BotMode] = {mode.value: mode for mode in BotMode}
        size: BoardSize = self._choose(
            f"Board size (3/4/5) [{defaults.size.value}]: ",
            {**sizes, "": defaults.size},
        )
        mode: BotMode = self._choose(
            f"Bot mode (random/smart) [{defaults.bot_mode.value}]: ",
            {**modes, "": defaults.bot_mode},
        )
        return GameSettings(size, mode)

    def _choose[T](self: Self, prompt: str, options: dict[str, T]) -> T:
        """Repeat the current prompt until the player chooses an available option."""
        while True:
            entry: str = self._read(prompt).strip().lower()
            if entry == "q":
                raise _QuitSessionError
            if entry in options:
                return options[entry]
            self._write("Invalid choice. Please try again.")

    def _play(self: Self, game: GameSnapshot) -> None:
        """Read separate row and column selections and print each saved board."""
        size: int = game.settings.size.value
        coordinates: dict[str, int] = {str(index + 1): index for index in range(size)}
        self._write(f"You play as {game.human_mark.value}.")
        self._show_board(game)
        while game.current_player is Player.HUMAN:
            row: int = self._choose(f"Row (1-{size}): ", coordinates)
            column: int = self._choose(f"Column (1-{size}): ", coordinates)
            try:
                game = self._service.play_move(game.game_id, Position(row, column))
            except InvalidMoveError as error:
                self._write(str(error))
            except BotMoveError:
                self._write("The bot could not reply. Please try the move again.")
            else:
                self._show_board(game)

        if game.is_draw:
            self._write("Draw.")
        elif game.winner is Player.HUMAN:
            self._write("You won.")
        elif game.winner is Player.BOT:
            self._write("The bot won.")

    def _show_board(self: Self, game: GameSnapshot) -> None:
        """Print a numbered board, using a dot for each empty cell."""
        columns: str = " ".join(str(index + 1) for index in range(len(game.board)))
        lines: list[str] = [f"  {columns}"]
        for row, cells in enumerate(game.board, start=1):
            marks: str = " ".join(
                "." if cell is Mark.E else cell.value for cell in cells
            )
            lines.append(f"{row} {marks}")
        self._write("\n".join(lines))
