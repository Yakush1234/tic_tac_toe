"""Shared fixtures for backend tests."""

import pytest

from backend.infrastructure.memory_game_repository import MemoryGameRepository


@pytest.fixture
def game_repository() -> MemoryGameRepository:
    """Provide an empty in-memory game repository for each test."""
    return MemoryGameRepository()
