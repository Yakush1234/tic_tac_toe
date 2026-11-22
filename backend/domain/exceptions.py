"""Errors raised when a participant attempts an illegal move."""


class InvalidMoveError(ValueError):
    """The requested placement violates the rules of the current game."""
