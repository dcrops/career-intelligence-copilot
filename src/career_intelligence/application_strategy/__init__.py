"""Public API for the application-strategy capability (FR-005 Phase A)."""

from .context import SearchOperatingContext
from .errors import (
    ApplicationStrategyError,
    ApplicationStrategyValidationError,
    ErrorDetail,
)
from .models import (
    ApplicationStrategy,
    ApplicationTier,
    EffortLevel,
    JobEvidenceRef,
    ManualCheck,
    NextAction,
    NextActionKind,
    PortfolioEmphasis,
    PracticalValue,
    ProfileEvidenceRef,
    PursuitPosture,
    StrategyEvidenceRef,
    StrategyReason,
    StrategyRiskOrGap,
)
from .service import ApplicationStrategyService

__all__ = [
    "ApplicationStrategy",
    "ApplicationStrategyError",
    "ApplicationStrategyService",
    "ApplicationStrategyValidationError",
    "ApplicationTier",
    "EffortLevel",
    "ErrorDetail",
    "JobEvidenceRef",
    "ManualCheck",
    "NextAction",
    "NextActionKind",
    "PortfolioEmphasis",
    "PracticalValue",
    "ProfileEvidenceRef",
    "PursuitPosture",
    "SearchOperatingContext",
    "StrategyEvidenceRef",
    "StrategyReason",
    "StrategyRiskOrGap",
]
