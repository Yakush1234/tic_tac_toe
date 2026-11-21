"""Translate game failures into REST responses."""

from typing import Self

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


async def game_not_found(request: Request, error: Exception) -> JSONResponse:
    """Report a missing or replaced game without exposing its identifier."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Game not found"}
    )


class MoveConflict(HTTPException):
    """A move that the current game state does not allow."""

    def __init__(self: Self, reason: str) -> None:
        """Return the domain's reason for rejecting the move."""
        super().__init__(status.HTTP_409_CONFLICT, detail=reason)
