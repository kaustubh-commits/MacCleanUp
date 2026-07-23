"""
Recommendation — the output of the Planner.

Suggests what should happen to a classified file. The recommendation is
advisory — the user makes the final decision.

The Planner may choose not to make a recommendation if it has insufficient
information. In that case, ``action`` is ``None`` and the UI presents the
file without a suggestion.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.action import SuggestedAction


@dataclass(frozen=True)
class Recommendation:
    """A suggestion for what to do with a single file.

    Fields
    ------
    action : SuggestedAction | None
        The suggested action. ``None`` means the Planner has no
        recommendation (insufficient confidence, unknown file type, etc.).
    reason : str
        A human-readable explanation of why this recommendation was made.
        Should be meaningful to the end user even when ``action`` is ``None``
        (e.g. "Insufficient information to make a recommendation.").
    """

    action: SuggestedAction | None
    reason: str