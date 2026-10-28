"""Tests for the application composition layer.

Integration tests use real modules — no mocking of Scanner, Classifier,
Planner, or ReviewBuilder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.pipeline import analyze_directory, execute_review
from models.category import FileCategory
from models.review import ReviewModel


class TestAnalyzeDirectory:
    """analyze_directory() should compose modules correctly."""

    def test_returns_review_model(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        review = analyze_directory(tmp_path)
        assert isinstance(review, ReviewModel)

    def test_counts_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")
        review = analyze_directory(tmp_path)
        assert review.total_files == 2

    def test_excludes_directories(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        review = analyze_directory(tmp_path)
        assert review.total_files == 0

    def test_nested_subfolders_count_only_files(self, tmp_path: Path) -> None:
        (tmp_path / "photos" / "2025").mkdir(parents=True)
        (tmp_path / "photos" / "2025" / "a.jpg").write_bytes(b"\xff\xd8\xff")
        (tmp_path / "photos" / "b.jpg").write_bytes(b"\xff\xd8\xff")
        (tmp_path / "setup.dmg").write_bytes(b"dmg")

        review = analyze_directory(tmp_path)

        assert review.total_files == 3
        assert review.total_size == 9
        categories = {s.category for s in review.categories}
        assert categories == {FileCategory.IMAGE, FileCategory.INSTALLER}

    def test_files_have_categories(self, tmp_path: Path) -> None:
        (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8\xff")
        (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4")
        review = analyze_directory(tmp_path)

        categories = {s.category for s in review.categories}
        assert FileCategory.IMAGE in categories
        assert FileCategory.PDF in categories

    def test_each_file_has_recommendation(self, tmp_path: Path) -> None:
        (tmp_path / "archive.zip").write_bytes(b"PK")
        review = analyze_directory(tmp_path)
        assert len(review.items) == 1
        assert review.items[0].recommendation is not None

    def test_invalid_root_raises(self) -> None:
        with pytest.raises(ValueError, match="root must be absolute"):
            analyze_directory(Path("relative/path"))

    def test_nonexistent_root_raises(self) -> None:
        with pytest.raises(ValueError, match="root does not exist"):
            analyze_directory(Path("/tmp/nonexistent_macleanup_xyz"))

    def test_deterministic(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.jpg").write_bytes(b"\xff\xd8\xff")
        assert analyze_directory(tmp_path) == analyze_directory(tmp_path)


class TestExecuteReview:
    """execute_review() should delegate to the executor."""

    def test_returns_execution_report(self) -> None:
        from models.action import SuggestedAction
        from models.analysis import AnalysisResult
        from models.execution import ExecutionReport
        from models.metadata import FileMetadata
        from models.recommendation import Recommendation
        from models.review import ReviewItem

        item = ReviewItem(
            analysis=AnalysisResult(
                metadata=FileMetadata(
                    path=Path("/tmp/test.txt"),
                    size=100,
                    created_time=1000.0,
                    modified_time=2000.0,
                ),
                category=FileCategory.DOCUMENT,
                confidence=1.0,
            ),
            recommendation=Recommendation(action=SuggestedAction.LEAVE, reason="Test"),
        )
        report = execute_review([item], Path("/tmp/dest"), dry_run=True)
        assert isinstance(report, ExecutionReport)