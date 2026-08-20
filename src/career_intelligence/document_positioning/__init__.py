"""Document positioning design types (M0).

Public surface is the capability catalogue and classification semantics.
``PositioningPlan`` is specified in docs and must not be imported from here
until M1.
"""

from .catalogue import classify_requirement, normalise_label, resolve_identity
from .models import RequirementClassification, SupportStatus

__all__ = [
    "RequirementClassification",
    "SupportStatus",
    "classify_requirement",
    "normalise_label",
    "resolve_identity",
]
