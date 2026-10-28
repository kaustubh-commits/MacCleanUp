"""
pipeline — application composition layer.

Composes existing modules into meaningful workflows without introducing
new domain logic.

Public API
---------
analyze_directory(root) -> ReviewModel
    Scan, classify, and plan an entire directory.

execute_review(items, destination, dry_run) -> ExecutionReport
    Execute approved recommendations. Thin wrapper around executor.
"""

from __future__ import annotations

from pathlib import Path

from core.classifier import classify
from core.executor import execute as _execute
from core.planner import plan
from core.review_builder import build_review as _build_review
from core.scanner import scan
from models.execution import ExecutionReport
from models.review import ReviewItem, ReviewModel


def analyze_directory(root: Path) -> ReviewModel:
    """Scan, classify, and plan an entire directory.

    Parameters
    ----------
    root : Path
        Absolute path to the directory to analyze.

    Returns
    -------
    ReviewModel
        Immutable snapshot of the scan. Contains files only — the
        scanner traverses directories but does not report them.

    Raises
    ------
    ValueError
        If *root* is not an absolute path, does not exist, or is not
        a directory. (Propagated from scanner.)
    """
    scan_result = scan(root)

    items: list[ReviewItem] = []
    for entry in scan_result.entries:
        analysis = classify(entry)
        recommendation = plan(analysis)
        items.append(ReviewItem(analysis, recommendation))

    return _build_review(items)


def execute_review(
    items: list[ReviewItem],
    destination: Path,
    dry_run: bool = False,
) -> ExecutionReport:
    """Execute approved recommendations.

    Parameters
    ----------
    items : list[ReviewItem]
        Review items to process. Only items with an actionable
        recommendation (e.g. MOVE) will be executed — the executor
        dispatches internally based on SuggestedAction.
    destination : Path
        Root directory for MOVE operations. Files are moved to
        ``destination / src.name`` (flat layout).
    dry_run : bool
        If True, log intended actions without modifying the filesystem.

    Returns
    -------
    ExecutionReport
        Immutable historical record with one result per item.
    """
    return _execute(items, destination, dry_run=dry_run)