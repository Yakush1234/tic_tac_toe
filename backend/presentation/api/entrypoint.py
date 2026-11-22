"""Build and serve the game API."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.application.game_repository import GameNotFoundError, RepositoryFullError
from backend.application.games import GameService
from backend.config.logging_config import configure_logging
from backend.config.settings import Settings
from backend.domain.enums import BotMode
from backend.domain.exceptions import InvalidMoveError
from backend.domain.random_bot import RandomBot
from backend.domain.smart_bot import SmartBot
from backend.infrastructure.memory_game_repository import MemoryGameRepository
from backend.presentation.api.rest.exceptions import (
    game_not_found,
    internal_error,
    move_conflict,
    storage_full,
)
from backend.presentation.api.rest.routers import router

FRONTEND_DIR: Path = Path(__file__).resolve().parents[3] / "frontend"


def game_page() -> FileResponse:
    """Serve the browser entry page."""
    return FileResponse(FRONTEND_DIR / "index.html")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an API instance with its own game repository and shared service."""
    if settings is None:
        settings = Settings()
    configure_logging(settings)
    app: FastAPI = FastAPI(title=settings.app_title)
    app.state.game_service = GameService(
        MemoryGameRepository(settings.max_games),
        {
            BotMode.RANDOM: RandomBot(),
            BotMode.SMART: SmartBot(settings.bot_search_budget_ms),
        },
    )
    app.add_exception_handler(GameNotFoundError, game_not_found)
    app.add_exception_handler(InvalidMoveError, move_conflict)
    app.add_exception_handler(RepositoryFullError, storage_full)
    app.add_exception_handler(Exception, internal_error)
    app.include_router(router)
    if settings.serve_frontend:
        app.add_api_route("/", game_page, methods=["GET"], include_in_schema=False)
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="frontend")
    return app


def run() -> None:
    """Serve the game API with Uvicorn."""
    settings: Settings = Settings()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        workers=1,
        access_log=False,
    )
