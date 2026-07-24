"""
ReviewItem and ReviewModel — orchestration types for the review stage.

ReviewItem pairs an AnalysisResult with its Recommendation.
ReviewModel is an immutable snapshot of a complete scan review.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.analysis import AnalysisResult
from models.category_summary import CategorySummary
from models.recommendation import Recommendation


@dataclass(frozen=True)
class ReviewItem:
    """A paired analysis and recommendation for a single file.

    Exists purely for orchestration. Not a domain concept — just a
    bundle created at the review stage when both pieces are needed.
    """

    analysis: AnalysisResult
    recommendation: Recommendation


@dataclass(frozen=True)
class ReviewModel:
    """An organized, immutable snapshot of a scan review.

    Fields
    ------
    total_files : int
        Number of files in the review.
    total_size : int
        Total size of all files in bytes.
    categories : tuple[CategorySummary, ...]
        Per-category summaries, sorted by total_size descending.
    items : tuple[ReviewItem, ...]
        Individual file analyses paired with their recommendations.
    reclaimable_size : int
        Total bytes of files recommended for MOVE.
    """

    total_files: int
    total_size: int
    categories: tuple[CategorySummary, ...]
    items: tuple[ReviewItem, ...]
    reclaimable_size: int