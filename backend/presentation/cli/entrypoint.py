"""Run a standalone terminal game with an in-memory repository."""

from backend.application.games import GameService
from backend.domain.enums import BotMode
from backend.domain.random_bot import RandomBot
from backend.domain.smart_bot import SmartBot
from backend.infrastructure.memory_game_repository import MemoryGameRepository
from backend.presentation.cli.terminal import TerminalGame


def run() -> None:
    """Build the game service and start the terminal session."""
    service: GameService = GameService(
        MemoryGameRepository(),
        {BotMode.RANDOM: RandomBot(), BotMode.SMART: SmartBot()},
    )
    TerminalGame(service).run()


if __name__ == "__main__":
    run()
