"""Process-local storage for committed games and isolated turns."""

from collections.abc import Generator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Self
from uuid import UUID, uuid4

from backend.application.game_repository import (
    GameNotFoundError,
    GameRepository,
    RepositoryFullError,
)
from backend.domain.entities.game import Game


@dataclass(slots=True)
class _Entry:
    """Committed game and the lock shared by editors of this game."""

    game: Game
    edit_lock: Lock = field(default_factory=Lock)


class MemoryGameRepository(GameRepository):
    """Keep independent games in memory for the lifetime of this instance."""

    def __init__(self: Self, max_games: int | None = None) -> None:
        """Start an empty repository."""
        self._entries: dict[UUID, _Entry] = {}
        self._lock: Lock = Lock()
        self._max_games: int | None = max_games

    def create(self: Self, game: Game, previous_id: UUID | None = None) -> UUID:
        """Store a detached game and retire its predecessor in one operation."""
        entry: _Entry = _Entry(deepcopy(game))
        with self._lock:
            replacing: bool = previous_id is not None and previous_id in self._entries
            if (
                not replacing
                and self._max_games is not None
                and len(self._entries) >= self._max_games
            ):
                raise RepositoryFullError("Game storage is full")
            game_id: UUID = uuid4()
            while game_id in self._entries or game_id == previous_id:
                game_id = uuid4()
            self._entries[game_id] = entry
            if previous_id is not None:
                self._entries.pop(previous_id, None)
        return game_id

    def _lookup(self: Self, game_id: UUID) -> _Entry:
        """Find a live entry while the caller holds the repository lock."""
        try:
            return self._entries[game_id]
        except KeyError:
            raise GameNotFoundError(game_id) from None

    def get(self: Self, game_id: UUID) -> Game:
        """Return a detached copy of the last committed position."""
        with self._lock:
            committed: Game = self._lookup(game_id).game
        return deepcopy(committed)

    @contextmanager
    def edit(self: Self, game_id: UUID) -> Generator[Game, None, None]:
        """Publish a successful turn only while the original game still exists."""
        with self._lock:
            entry: _Entry = self._lookup(game_id)
        with entry.edit_lock:
            working: Game = self.get(game_id)
            yield working
            committed: Game = deepcopy(working)
            with self._lock:
                if self._entries.get(game_id) is not entry:
                    raise GameNotFoundError(game_id)
                entry.game = committed
