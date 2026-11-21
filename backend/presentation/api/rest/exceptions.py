"""Translate game failures into REST responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse


async def game_not_found(request: Request, error: Exception) -> JSONResponse:
    """Report a missing or replaced game without exposing its identifier."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Game not found"}
    )


async def move_conflict(request: Request, error: Exception) -> JSONResponse:
    """Expose the reason for a rejected human move."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)}
    )


async def storage_full(request: Request, error: Exception) -> JSONResponse:
    """Report that the process has reached its configured game limit."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(error)}
    )


async def internal_error(request: Request, error: Exception) -> JSONResponse:
    """Keep internal details in the ASGI server's exception log."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
