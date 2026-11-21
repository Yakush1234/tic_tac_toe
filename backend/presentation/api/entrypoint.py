"""Build and serve the game API."""

import uvicorn
from fastapi import FastAPI

from backend.application.game_repository import GameNotFoundError
from backend.application.games import GameService
from backend.config.logging_config import configure_logging
from backend.config.settings import Settings
from backend.domain.enums import BotMode
from backend.domain.random_bot import RandomBot
from backend.infrastructure.memory_game_repository import MemoryGameRepository
from backend.presentation.api.rest.exceptions import game_not_found
from backend.presentation.api.rest.routers import router


def create_app() -> FastAPI:
    """Build an API instance with its own game repository and shared service."""
    settings: Settings = Settings()
    configure_logging(settings)
    app: FastAPI = FastAPI(title=settings.app_title)
    app.state.game_service = GameService(
        MemoryGameRepository(), {BotMode.RANDOM: RandomBot()}
    )
    app.add_exception_handler(GameNotFoundError, game_not_found)
    app.include_router(router)
    return app


def run() -> None:
    """Serve the game API with Uvicorn."""
    uvicorn.run(create_app())
