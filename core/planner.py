"""
plan — pure function mapping AnalysisResult → Recommendation.

Single responsibility: apply policy to decide what to suggest for a file.
No filesystem access, no classification, no execution.
"""

from __future__ import annotations

from models.action import SuggestedAction
from models.analysis import AnalysisResult
from models.category import FileCategory
from models.recommendation import Recommendation


_POLICY: dict[FileCategory, tuple[SuggestedAction, str]] = {
    FileCategory.ARCHIVE: (
        SuggestedAction.MOVE,
        "Archive files are good candidates for review.",
    ),
    FileCategory.INSTALLER: (
        SuggestedAction.MOVE,
        "Installer files are good candidates for review.",
    ),
}

_DEFAULT_REASON = "No policy rule applies to this file type."
_CONFIDENCE_GATE = 1.0
_LOW_CONFIDENCE_REASON = "Insufficient confidence to make a recommendation."


def plan(result: AnalysisResult) -> Recommendation:
    """Recommend an action for a single classified file.

    Parameters
    ----------
    result : AnalysisResult
        The classifier's output for a single file.

    Returns
    -------
    Recommendation
        The suggested action (or None) with a human-readable reason.

    Notes
    -----
    The confidence gate ensures the planner only acts on files the
    classifier is certain about. Sub-1.0 confidence always yields
    ``action=None``, regardless of the policy table.
    """
    if result.confidence < _CONFIDENCE_GATE:
        return Recommendation(action=None, reason=_LOW_CONFIDENCE_REASON)

    entry = _POLICY.get(result.category)
    if entry is not None:
        action, reason = entry
        return Recommendation(action=action, reason=reason)

    return Recommendation(action=None, reason=_DEFAULT_REASON)