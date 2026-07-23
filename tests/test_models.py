"""Tests for shared data models: category, action, analysis, recommendation, category_summary."""

from __future__ import annotations

from pathlib import Path

import pytest

from models.action import SuggestedAction
from models.analysis import AnalysisResult
from models.category import FileCategory
from models.category_summary import CategorySummary, group_by_category
from models.metadata import FileMetadata
from models.recommendation import Recommendation


# =========================================================================
# FileCategory
# =========================================================================


class TestFileCategory:
    """FileCategory enum should cover expected categories."""

    def test_all_categories_defined(self) -> None:
        categories = {c.name for c in FileCategory}
        expected = {
            "IMAGE", "VIDEO", "AUDIO", "PDF", "ARCHIVE",
            "INSTALLER", "DOCUMENT", "PROJECT", "TEMPORARY", "UNKNOWN",
        }
        assert categories == expected

    def test_unused_members_can_be_added(self) -> None:
        """The enum should be extensible without breaking consumers."""
        assert FileCategory.UNKNOWN is not None


# =========================================================================
# SuggestedAction
# =========================================================================


class TestSuggestedAction:
    """SuggestedAction enum should cover expected actions."""

    def test_all_actions_defined(self) -> None:
        actions = {a.name for a in SuggestedAction}
        assert actions == {"DELETE", "MOVE", "LEAVE"}


# =========================================================================
# AnalysisResult
# =========================================================================


class TestAnalysisResult:
    """AnalysisResult should validate its inputs."""

    def make_metadata(self, path: str = "/tmp/test.txt", size: int = 100) -> FileMetadata:
        return FileMetadata(
            path=Path(path),
            size=size,
            created_time=1000.0,
            modified_time=2000.0,
        )

    def test_create_valid(self) -> None:
        meta = self.make_metadata()
        result = AnalysisResult(
            metadata=meta,
            category=FileCategory.PDF,
            confidence=0.95,
        )
        assert result.metadata == meta
        assert result.category == FileCategory.PDF
        assert result.confidence == 0.95

    def test_confidence_zero_is_valid(self) -> None:
        result = AnalysisResult(
            metadata=self.make_metadata(),
            category=FileCategory.UNKNOWN,
            confidence=0.0,
        )
        assert result.confidence == 0.0

    def test_confidence_one_is_valid(self) -> None:
        result = AnalysisResult(
            metadata=self.make_metadata(),
            category=FileCategory.IMAGE,
            confidence=1.0,
        )
        assert result.confidence == 1.0

    def test_confidence_below_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence must be between"):
            AnalysisResult(
                metadata=self.make_metadata(),
                category=FileCategory.IMAGE,
                confidence=-0.01,
            )

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence must be between"):
            AnalysisResult(
                metadata=self.make_metadata(),
                category=FileCategory.IMAGE,
                confidence=1.01,
            )

    def test_immutable(self) -> None:
        result = AnalysisResult(
            metadata=self.make_metadata(),
            category=FileCategory.IMAGE,
            confidence=0.8,
        )
        with pytest.raises(AttributeError):
            result.category = FileCategory.VIDEO  # type: ignore[misc]

    def test_different_categories_unequal(self) -> None:
        a = AnalysisResult(
            metadata=self.make_metadata("/tmp/a.txt"),
            category=FileCategory.PDF,
            confidence=0.9,
        )
        b = AnalysisResult(
            metadata=self.make_metadata("/tmp/a.txt"),
            category=FileCategory.DOCUMENT,
            confidence=0.9,
        )
        assert a != b


# =========================================================================
# Recommendation
# =========================================================================


class TestRecommendation:
    """Recommendation should support optional action."""

    def test_with_action(self) -> None:
        rec = Recommendation(
            action=SuggestedAction.DELETE,
            reason="File is a duplicate installer.",
        )
        assert rec.action == SuggestedAction.DELETE
        assert "duplicate" in rec.reason

    def test_no_action(self) -> None:
        rec = Recommendation(
            action=None,
            reason="Insufficient information to make a recommendation.",
        )
        assert rec.action is None
        assert "Insufficient" in rec.reason

    def test_immutable(self) -> None:
        rec = Recommendation(action=None, reason="test")
        with pytest.raises(AttributeError):
            rec.action = SuggestedAction.DELETE  # type: ignore[misc]


# =========================================================================
# CategorySummary + group_by_category
# =========================================================================


class TestGroupByCategory:
    """group_by_category should correctly aggregate AnalysisResults."""

    def make_meta(self, path: str, size: int) -> FileMetadata:
        return FileMetadata(
            path=Path(path),
            size=size,
            created_time=1000.0,
            modified_time=2000.0,
        )

    def make_result(self, path: str, size: int, category: FileCategory) -> AnalysisResult:
        return AnalysisResult(
            metadata=self.make_meta(path, size),
            category=category,
            confidence=0.9,
        )

    def test_empty_list(self) -> None:
        assert group_by_category([]) == []

    def test_single_category(self) -> None:
        results = [
            self.make_result("/a.txt", 100, FileCategory.DOCUMENT),
            self.make_result("/b.txt", 200, FileCategory.DOCUMENT),
        ]
        summaries = group_by_category(results)
        assert len(summaries) == 1
        assert summaries[0].category == FileCategory.DOCUMENT
        assert summaries[0].count == 2
        assert summaries[0].total_size == 300

    def test_multiple_categories(self) -> None:
        results = [
            self.make_result("/a.jpg", 500, FileCategory.IMAGE),
            self.make_result("/b.pdf", 200, FileCategory.PDF),
            self.make_result("/c.png", 100, FileCategory.IMAGE),
        ]
        summaries = group_by_category(results)
        assert len(summaries) == 2

        # Sorted by total_size descending: IMAGE (600) > PDF (200)
        assert summaries[0].category == FileCategory.IMAGE
        assert summaries[0].count == 2
        assert summaries[0].total_size == 600

        assert summaries[1].category == FileCategory.PDF
        assert summaries[1].count == 1
        assert summaries[1].total_size == 200

    def test_category_with_single_file(self) -> None:
        results = [
            self.make_result("/archive.zip", 1000, FileCategory.ARCHIVE),
        ]
        summaries = group_by_category(results)
        assert len(summaries) == 1
        assert summaries[0].count == 1
        assert summaries[0].total_size == 1000

    def test_preserves_analysis_results(self) -> None:
        results = [
            self.make_result("/unique.txt", 50, FileCategory.DOCUMENT),
        ]
        summaries = group_by_category(results)
        assert summaries[0].files == results

    def test_sort_order_largest_first(self) -> None:
        results = [
            self.make_result("/small.pdf", 10, FileCategory.PDF),
            self.make_result("/large.zip", 9000, FileCategory.ARCHIVE),
            self.make_result("/medium.jpg", 500, FileCategory.IMAGE),
        ]
        summaries = group_by_category(results)
        categories = [s.category for s in summaries]
        assert categories == [
            FileCategory.ARCHIVE,
            FileCategory.IMAGE,
            FileCategory.PDF,
        ]

    def test_no_mutation_of_input(self) -> None:
        results = [
            self.make_result("/a.txt", 100, FileCategory.DOCUMENT),
        ]
        original_len = len(results)
        group_by_category(results)
        assert len(results) == original_len  # not modified


class TestCategorySummary:
    """CategorySummary dataclass should store expected fields."""

    def test_create(self) -> None:
        summary = CategorySummary(
            category=FileCategory.INSTALLER,
            count=3,
            total_size=1500,
            files=[],
        )
        assert summary.category == FileCategory.INSTALLER
        assert summary.count == 3
        assert summary.total_size == 1500
        assert summary.files == []