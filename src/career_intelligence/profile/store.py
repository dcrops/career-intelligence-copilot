"""Persistence boundary for career profiles."""

from typing import Protocol

from .models import CareerProfile


class ProfileStore(Protocol):
    def load(self) -> CareerProfile:
        """Load and validate a career profile."""

    def save(self, profile: CareerProfile) -> None:
        """Persist a validated career profile."""
