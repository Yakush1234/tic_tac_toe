"""Persistence boundary for game creation, reads, and atomic turns."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Self
from uuid import UUID

from backend.domain.entities.game import Game


class GameNotFoundError(LookupError):
    """The requested game is no longer available."""


class RepositoryFullError(RuntimeError):
    """The repository cannot accept another game."""


class GameRepository(ABC):
    """Serialize edits and replacements of the same game."""

    @abstractmethod
    def create(self: Self, game: Game, previous_id: UUID | None) -> UUID:
        """Store under a fresh ID and remove the previous game atomically.

        Ignore a missing previous ID. On failure, preserve the previous game.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self: Self, game_id: UUID) -> Game:
        """Return a stable committed view or raise GameNotFoundError."""
        raise NotImplementedError

    @abstractmethod
    def edit(self: Self, game_id: UUID) -> AbstractContextManager[Game]:
        """Open an isolated edit or raise GameNotFoundError for an unknown ID.

        Publish changes only on normal exit. Propagate exceptions and discard
        all partial changes. An edit must never recreate a replaced game.
        """
        raise NotImplementedError
