"""Public API for ranked comparison of open opportunities (M4)."""

from .errors import (
    ErrorDetail,
    OpportunityComparisonError,
    OpportunityComparisonValidationError,
)
from .models import OpportunityComparison, RankedOpportunity
from .ranking import OPEN_STATUSES, fit_strength, is_open_opportunity, sort_key
from .service import OpportunityComparisonService

__all__ = [
    "OPEN_STATUSES",
    "ErrorDetail",
    "OpportunityComparison",
    "OpportunityComparisonError",
    "OpportunityComparisonService",
    "OpportunityComparisonValidationError",
    "RankedOpportunity",
    "fit_strength",
    "is_open_opportunity",
    "sort_key",
]
