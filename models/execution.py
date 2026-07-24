"""
Execution models — the output of the Executor.

ExecutionReport describes what happened during execution.
It does not determine success or failure — callers interpret the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from models.review import ReviewItem


class ExecutionStatus(Enum):
    """The outcome of a single file execution.

    Members
    -------
    SUCCESS : The operation completed successfully.
    SKIPPED : The operation was intentionally skipped (collision, LEAVE, etc.).
    FAILED  : The operation could not be completed due to an error.
    """

    SUCCESS = auto()
    SKIPPED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class ExecutionResult:
    """The outcome of executing a single review item.

    Fields
    ------
    item : ReviewItem
        The review item that was executed. Provides full provenance
        (source path, category, recommendation, reason, etc.).
    status : ExecutionStatus
        Machine-readable outcome. Use this for program logic,
        not the message string.
    message : str | None
        Human-readable context about the outcome.
        Explains *why* something succeeded, was skipped, or failed.
        Not intended for program logic.
    """

    item: ReviewItem
    status: ExecutionStatus
    message: str | None = None


@dataclass(frozen=True)
class ExecutionReport:
    """An immutable historical record of an execution batch.

    Fields
    ------
    results : tuple[ExecutionResult, ...]
        One result per review item, in the original traversal order.

    Notes
    -----
    ExecutionReport describes what happened. It does not compute
    summaries — callers derive counts and totals from the raw results.
    """

    results: tuple[ExecutionResult, ...]