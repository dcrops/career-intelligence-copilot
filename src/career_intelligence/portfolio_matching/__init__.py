"""Public API for the portfolio-matching capability (FR-004)."""

from .errors import ErrorDetail, PortfolioMatchingError, PortfolioMatchingValidationError
from .models import (
    JobEvidenceRef,
    PortfolioMatch,
    ProfileEvidenceRef,
    RankedPortfolioProject,
    RankingFactor,
)
from .service import PortfolioMatchingService

__all__ = [
    "ErrorDetail",
    "JobEvidenceRef",
    "PortfolioMatch",
    "PortfolioMatchingError",
    "PortfolioMatchingService",
    "PortfolioMatchingValidationError",
    "ProfileEvidenceRef",
    "RankedPortfolioProject",
    "RankingFactor",
]
