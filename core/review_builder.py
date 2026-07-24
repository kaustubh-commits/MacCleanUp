"""
build_review — pure function transforming paired analyses + recommendations
into an immutable ReviewModel snapshot.

No filesystem access, no formatting, no output.
"""

from __future__ import annotations

from models.action import SuggestedAction
from models.category_summary import group_by_category
from models.review import ReviewItem, ReviewModel


def build_review(items: list[ReviewItem]) -> ReviewModel:
    """Build an immutable review snapshot from paired analyses and recommendations.

    Parameters
    ----------
    items : list[ReviewItem]
        Paired analysis and recommendation for each scanned file.

    Returns
    -------
    ReviewModel
        An immutable snapshot containing totals, category summaries,
        individual items, and reclaimable size.
    """
    # Snapshot inputs immediately — the caller's list is not our concern.
    items = tuple(items)

    total_files = len(items)
    total_size = sum(item.analysis.metadata.size for item in items)

    analyses = [item.analysis for item in items]
    categories = tuple(group_by_category(analyses))

    reclaimable_size = sum(
        item.analysis.metadata.size
        for item in items
        if item.recommendation.action is SuggestedAction.MOVE
    )

    return ReviewModel(
        total_files=total_files,
        total_size=total_size,
        categories=categories,
        items=items,
        reclaimable_size=reclaimable_size,
    )