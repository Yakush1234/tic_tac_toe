"""FastAPI dependencies supplied to game endpoints."""

from typing import Annotated, cast

from fastapi import Depends, Request

from backend.application.games import GameService


def get_game_service(request: Request) -> GameService:
    """Resolve the service configured for the current application."""
    return cast(GameService, request.app.state.game_service)


GameServiceDependency = Annotated[GameService, Depends(get_game_service)]
