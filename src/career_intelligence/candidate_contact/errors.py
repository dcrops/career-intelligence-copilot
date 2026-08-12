"""Errors for owner candidate-contact configuration."""

from __future__ import annotations


class CandidateContactConfigError(Exception):
    """Raised when owner contact configuration is missing or incomplete."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
