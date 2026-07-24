"""
execute — the Execution Layer of MacCleanUp.

The Executor never decides. It only executes decisions that have already been made.
It performs filesystem operations (move, delete) as instructed by the Planner.

ExecutionReport describes what happened. It does not determine success or failure.
Callers interpret the report.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from models.action import SuggestedAction
from models.execution import ExecutionReport, ExecutionResult, ExecutionStatus
from models.review import ReviewItem


def execute(
    items: list[ReviewItem],
    destination: Path,
    dry_run: bool = False,
) -> ExecutionReport:
    """Execute recommendations for a list of review items.

    Parameters
    ----------
    items : list[ReviewItem]
        Review items to process. All items are processed regardless of
        their recommendation — the function dispatches internally based
        on ``SuggestedAction``.
    destination : Path
        Root directory for MOVE operations. Files are moved to
        ``destination / src.name`` (flat layout).
    dry_run : bool
        If True, log intended actions without performing them.

    Returns
    -------
    ExecutionReport
        Immutable historical record with one result per item.
        The report is always produced — partial failures are captured
        inside individual ``ExecutionResult`` objects, not as exceptions.

    Notes
    -----
    - Collisions: if ``destination / src.name`` exists, the file is SKIPPED.
    - Permissions: permission errors are captured as FAILED, never raised.
    - The Executor never prints, logs, or formats output.
    """
    results: list[ExecutionResult] = []

    for item in items:
        action = item.recommendation.action

        if action is SuggestedAction.MOVE:
            result = _execute_move(item, destination, dry_run)
        elif action is SuggestedAction.DELETE:
            result = _execute_delete(item, dry_run)
        elif action is SuggestedAction.LEAVE:
            result = _skip(item, "No action required.")
        else:
            result = _skip(item, "No recommendation.")

        results.append(result)

    return ExecutionReport(results=tuple(results))


# =========================================================================
# Private helpers — one per action type
# =========================================================================


def _execute_move(
    item: ReviewItem,
    destination: Path,
    dry_run: bool,
) -> ExecutionResult:
    """Move a file to the destination directory (flat layout)."""
    src = item.analysis.metadata.path
    dest = destination / src.name

    if dry_run:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.SUCCESS,
            message=f"Would move to {dest}",
        )

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            return ExecutionResult(
                item=item,
                status=ExecutionStatus.SKIPPED,
                message=f"Destination already exists: {dest}",
            )

        shutil.move(str(src), str(dest))
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.SUCCESS,
            message=f"Moved to {dest}",
        )

    except PermissionError as e:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.FAILED,
            message=f"Permission denied: {e}",
        )
    except FileNotFoundError as e:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.FAILED,
            message=f"Source not found: {e}",
        )
    except OSError as e:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.FAILED,
            message=f"Filesystem error: {e}",
        )


def _execute_delete(item: ReviewItem, dry_run: bool) -> ExecutionResult:
    """Permanently remove a file.

    NOTE: DELETE is structurally implemented but not yet used by the Planner.
    The Planner currently only recommends MOVE, LEAVE, or None.
    """
    if dry_run:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.SUCCESS,
            message="Would delete",
        )

    try:
        item.analysis.metadata.path.unlink(missing_ok=False)
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.SUCCESS,
            message="Deleted",
        )
    except PermissionError as e:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.FAILED,
            message=f"Permission denied: {e}",
        )
    except FileNotFoundError as e:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.FAILED,
            message=f"Source not found: {e}",
        )
    except OSError as e:
        return ExecutionResult(
            item=item,
            status=ExecutionStatus.FAILED,
            message=f"Filesystem error: {e}",
        )


def _skip(item: ReviewItem, reason: str) -> ExecutionResult:
    """Record a SKIPPED result for items that require no action."""
    return ExecutionResult(
        item=item,
        status=ExecutionStatus.SKIPPED,
        message=reason,
    )