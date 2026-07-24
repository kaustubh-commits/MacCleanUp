"""Tests for the Review Builder module.

The builder is a pure function. No filesystem, no mocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.action import SuggestedAction
from models.analysis import AnalysisResult
from models.category import FileCategory
from models.metadata import FileMetadata
from models.recommendation import Recommendation
from models.review import ReviewItem, ReviewModel
from models.category_summary import CategorySummary

from core.review_builder import build_review


class TestBuildReview:
    """build_review() should produce an immutable snapshot of a scan review."""

    def make_metadata(self, path: str, size: int) -> FileMetadata:
        return FileMetadata(
            path=Path(path),
            size=size,
            created_time=1000.0,
            modified_time=2000.0,
        )

    def make_analysis(
        self,
        path: str,
        size: int,
        category: FileCategory = FileCategory.UNKNOWN,
    ) -> AnalysisResult:
        return AnalysisResult(
            metadata=self.make_metadata(path, size),
            category=category,
            confidence=1.0,
        )

    def make_recommendation(
        self,
        action: SuggestedAction | None = None,
        reason: str = "Test reason.",
    ) -> Recommendation:
        return Recommendation(action=action, reason=reason)

    def make_item(
        self,
        path: str,
        size: int,
        category: FileCategory = FileCategory.UNKNOWN,
        action: SuggestedAction | None = None,
    ) -> ReviewItem:
        return ReviewItem(
            analysis=self.make_analysis(path, size, category),
            recommendation=self.make_recommendation(action),
        )

    # =====================================================================
    # Empty input
    # =====================================================================

    def test_empty_input(self) -> None:
        review = build_review([])
        assert review.total_files == 0
        assert review.total_size == 0
        assert review.categories == ()
        assert review.items == ()
        assert review.reclaimable_size == 0

    # =====================================================================
    # Single file
    # =====================================================================

    def test_single_file_no_recommendation(self) -> None:
        items = [self.make_item("/a.txt", 100)]
        review = build_review(items)
        assert review.total_files == 1
        assert review.total_size == 100
        assert review.reclaimable_size == 0
        assert len(review.items) == 1

    def test_single_file_move_recommendation(self) -> None:
        items = [self.make_item("/archive.zip", 500, FileCategory.ARCHIVE, SuggestedAction.MOVE)]
        review = build_review(items)
        assert review.total_files == 1
        assert review.total_size == 500
        assert review.reclaimable_size == 500

    # =====================================================================
    # Reclaimable size calculations
    # =====================================================================

    def test_multiple_move_recommendations_summed(self) -> None:
        items = [
            self.make_item("/a.zip", 200, FileCategory.ARCHIVE, SuggestedAction.MOVE),
            self.make_item("/b.dmg", 300, FileCategory.INSTALLER, SuggestedAction.MOVE),
        ]
        review = build_review(items)
        assert review.reclaimable_size == 500

    def test_no_move_recommendations_reclaimable_zero(self) -> None:
        items = [
            self.make_item("/a.jpg", 200, FileCategory.IMAGE),
            self.make_item("/b.pdf", 300, FileCategory.PDF),
        ]
        review = build_review(items)
        assert review.reclaimable_size == 0

    def test_only_move_actions_contribte_to_reclaimable(self) -> None:
        """DELETE, LEAVE, and None should not count toward reclaimable."""
        items = [
            self.make_item("/a.zip", 100, FileCategory.ARCHIVE, SuggestedAction.MOVE),
            self.make_item("/b.txt", 200, FileCategory.DOCUMENT, SuggestedAction.DELETE),
            self.make_item("/c.mp4", 300, FileCategory.VIDEO, SuggestedAction.LEAVE),
            self.make_item("/d.jpg", 400, FileCategory.IMAGE, None),
        ]
        review = build_review(items)
        # Only the MOVE item (100) contributes
        assert review.reclaimable_size == 100

    # =====================================================================
    # Category summaries
    # =====================================================================

    def test_mixed_categories_summarized(self) -> None:
        items = [
            self.make_item("/a.jpg", 500, FileCategory.IMAGE),
            self.make_item("/b.pdf", 200, FileCategory.PDF),
            self.make_item("/c.png", 100, FileCategory.IMAGE),
        ]
        review = build_review(items)
        assert len(review.categories) == 2

        # Sorted by total_size descending: IMAGE (600) > PDF (200)
        assert review.categories[0].category == FileCategory.IMAGE
        assert review.categories[0].count == 2
        assert review.categories[0].total_size == 600

        assert review.categories[1].category == FileCategory.PDF
        assert review.categories[1].count == 1
        assert review.categories[1].total_size == 200

    # =====================================================================
    # Structural
    # =====================================================================

    def test_returns_review_model(self) -> None:
        review = build_review([self.make_item("/a.txt", 100)])
        assert isinstance(review, ReviewModel)

    def test_deterministic(self) -> None:
        items = [
            self.make_item("/a.zip", 200, FileCategory.ARCHIVE, SuggestedAction.MOVE),
            self.make_item("/b.pdf", 100, FileCategory.PDF),
        ]
        assert build_review(items) == build_review(items)

    def test_no_mutation_of_inputs(self) -> None:
        items = [
            self.make_item("/a.zip", 200, FileCategory.ARCHIVE, SuggestedAction.MOVE),
        ]
        original_len = len(items)
        original_item = items[0]
        build_review(items)
        assert len(items) == original_len
        assert items[0] is original_item

    def test_snapshot_isolation(self) -> None:
        """Mutating the original list after build should not affect the review."""
        items = [
            self.make_item("/a.txt", 100),
            self.make_item("/b.txt", 200),
        ]
        review = build_review(items)
        # Mutate the original list
        items.clear()
        assert review.total_files == 2
        assert len(review.items) == 2

    def test_snapshot_isolation_reclaimable(self) -> None:
        """Mutating original items after build should not affect reclaimable."""
        item = self.make_item("/a.zip", 500, FileCategory.ARCHIVE, SuggestedAction.MOVE)
        items = [item]
        review = build_review(items)
        # Mutate the original recommendation
        items[0] = self.make_item("/a.zip", 500, FileCategory.ARCHIVE)
        assert review.reclaimable_size == 500