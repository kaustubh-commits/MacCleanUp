"""
SuggestedAction — the vocabulary of operations MacCleanUp can perform.

This enum is the shared language between the Planner (which recommends),
the UI (which asks), the Executor (which performs), and the audit log
(which records). Every action in the system uses these values.
"""

from __future__ import annotations

from enum import Enum, auto


class SuggestedAction(Enum):
    """The set of possible actions MacCleanUp can recommend or perform.

    Members
    -------
    DELETE  : Permanently remove the file.
    MOVE    : Relocate the file to a user-chosen destination.
    LEAVE   : Take no action. The file stays in place.
    """

    DELETE = auto()
    MOVE = auto()
    LEAVE = auto()