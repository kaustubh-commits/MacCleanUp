"""Tests for the Renderer module.

The renderer is a pure function. No filesystem, no mocks, no stdout.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.action import SuggestedAction
from models.analysis import AnalysisResult
from models.category import FileCategory
from models.category_summary import CategorySummary
from models.metadata import FileMetadata
from models.recommendation import Recommendation
from models.review import ReviewItem, ReviewModel

from core.renderer import render


class TestRender:
    """render() should produce a formatted string from a ReviewModel."""

    def make_empty_review(self) -> ReviewModel:
        return ReviewModel(
            total_files=0,
            total_size=0,
            categories=(),
            items=(),
            reclaimable_size=0,
        )

    def make_review(
        self,
        items: list[ReviewItem],
    ) -> ReviewModel:
        from core.review_builder import build_review

        return build_review(items)

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
        reason: str = "",
    ) -> Recommendation:
        return Recommendation(action=action, reason=reason)

    def make_item(
        self,
        path: str,
        size: int,
        category: FileCategory = FileCategory.UNKNOWN,
        action: SuggestedAction | None = None,
        reason: str = "",
    ) -> ReviewItem:
        return ReviewItem(
            analysis=self.make_analysis(path, size, category),
            recommendation=self.make_recommendation(action, reason),
        )

    def test_empty_review(self) -> None:
        review = self.make_empty_review()
        output = render(review)
        assert "0 files" in output
        assert "Reclaimable" in output

    def test_header_present(self) -> None:
        items = [self.make_item("/a.txt", 100)]
        review = self.make_review(items)
        output = render(review)
        assert "Scan Summary" in output
        assert "Scanned 1 files (100 B)" in output

    def test_categories_section(self) -> None:
        items = [
            self.make_item("/a.jpg", 500, FileCategory.IMAGE),
            self.make_item("/b.pdf", 200, FileCategory.PDF),
        ]
        review = self.make_review(items)
        output = render(review)
        assert "Files by Category" in output
        assert "IMAGE" in output
        assert "PDF" in output

    def test_recommendations_section(self) -> None:
        items = [
            self.make_item(
                "/archive.zip",
                500,
                FileCategory.ARCHIVE,
                SuggestedAction.MOVE,
                "Archive files are good candidates for review.",
            ),
            self.make_item("/photo.jpg", 300, FileCategory.IMAGE),
        ]
        review = self.make_review(items)
        output = render(review)
        assert "Recommendations" in output
        assert "MOVE (1 files, 500 B)" in output
        assert "archive.zip" in output
        assert "Archive files are good candidates" in output

    def test_reclaimable_in_footer(self) -> None:
        items = [
            self.make_item(
                "/archive.zip",
                500,
                FileCategory.ARCHIVE,
                SuggestedAction.MOVE,
            ),
        ]
        review = self.make_review(items)
        output = render(review)
        assert "Reclaimable space: 500 B" in output

    def test_no_colors_in_plain_text(self) -> None:
        review = self.make_empty_review()
        output = render(review, use_color=False)
        assert "\033" not in output

    def test_deterministic(self) -> None:
        items = [
            self.make_item("/a.txt", 100, FileCategory.DOCUMENT),
            self.make_item("/b.zip", 200, FileCategory.ARCHIVE, SuggestedAction.MOVE),
        ]
        review = self.make_review(items)
        assert render(review) == render(review)

    def test_categories_sorted_by_size_descending(self) -> None:
        items = [
            self.make_item("/small.pdf", 10, FileCategory.PDF),
            self.make_item("/large.zip", 9000, FileCategory.ARCHIVE),
            self.make_item("/medium.jpg", 500, FileCategory.IMAGE),
        ]
        review = self.make_review(items)
        output = render(review)
        # The categories section should list ARCHIVE first (9000), then IMAGE (500), then PDF (10)
        arch_idx = output.index("ARCHIVE")
        img_idx = output.index("IMAGE")
        pdf_idx = output.index("PDF")
        assert arch_idx < img_idx < pdf_idx

    def test_recommendations_sorted_by_size_descending(self) -> None:
        items = [
            self.make_item(
                "/small.zip",
                100,
                FileCategory.ARCHIVE,
                SuggestedAction.MOVE,
                "Archive files are good candidates for review.",
            ),
            self.make_item(
                "/large.zip",
                500,
                FileCategory.ARCHIVE,
                SuggestedAction.MOVE,
                "Archive files are good candidates for review.",
            ),
        ]
        review = self.make_review(items)
        output = render(review)
        # large.zip should appear before small.zip
        large_idx = output.index("large.zip")
        small_idx = output.index("small.zip")
        assert large_idx < small_idx