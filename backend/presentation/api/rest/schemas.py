"""Request schemas for the game REST API."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.enums import BoardSize, BotMode


class ErrorResponse(BaseModel):
    """Public description of a game operation failure."""

    detail: str


class StartGameRequest(BaseModel):
    """Settings for a new game and the optional game it replaces."""

    model_config = ConfigDict(extra="forbid")
    size: BoardSize = BoardSize.THREE
    bot_mode: BotMode = BotMode.RANDOM
    previous_id: UUID | None = None


class MoveRequest(BaseModel):
    """Zero-based coordinates of the human move."""

    model_config = ConfigDict(extra="forbid")
    row: Annotated[int, Field(strict=True, ge=0)]
    column: Annotated[int, Field(strict=True, ge=0)]
