"""REST routes for creating, reading, and playing games."""

from uuid import UUID

from fastapi import APIRouter, status

from backend.application.games import GameSnapshot
from backend.domain.enums import BotMode
from backend.domain.values import GameSettings, Position
from backend.presentation.api.rest.dependencies import GameServiceDependency
from backend.presentation.api.rest.exceptions import MoveConflict
from backend.presentation.api.rest.schemas import MoveRequest, StartGameRequest

router: APIRouter = APIRouter(prefix="/games", tags=["games"])


@router.post("", status_code=status.HTTP_201_CREATED)
def start_game(
    service: GameServiceDependency, request: StartGameRequest = StartGameRequest()
) -> GameSnapshot:
    """Create a game and include the bot's opening move when it plays X."""
    settings: GameSettings = GameSettings(request.size, BotMode(request.bot_mode))
    return service.start_game(settings, previous_id=request.previous_id)


@router.get("/{game_id}")
def get_game(game_id: UUID, service: GameServiceDependency) -> GameSnapshot:
    """Read the most recent committed position, including a final result."""
    return service.get_game(game_id)


@router.post("/{game_id}/moves")
def play_move(
    game_id: UUID, request: MoveRequest, service: GameServiceDependency
) -> GameSnapshot:
    """Play a human move and return the board after any bot reply."""
    try:
        return service.play_move(game_id, Position(request.row, request.column))
    except ValueError as error:
        raise MoveConflict(str(error)) from error
