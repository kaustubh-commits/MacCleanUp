"""Tests for the Executor module.

Unit tests mock the filesystem. Integration tests use tmp_path for real operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from models.action import SuggestedAction
from models.analysis import AnalysisResult
from models.category import FileCategory
from models.execution import ExecutionReport, ExecutionResult, ExecutionStatus
from models.metadata import FileMetadata
from models.recommendation import Recommendation
from models.review import ReviewItem

from core.executor import execute


class TestExecuteUnit:
    """Unit tests — mock shutil.move and Path.mkdir to avoid real filesystem."""

    def make_item(
        self,
        path: str,
        size: int = 100,
        category: FileCategory = FileCategory.UNKNOWN,
        action: SuggestedAction | None = None,
        reason: str = "",
    ) -> ReviewItem:
        return ReviewItem(
            analysis=AnalysisResult(
                metadata=FileMetadata(
                    path=Path(path),
                    size=size,
                    created_time=1000.0,
                    modified_time=2000.0,
                ),
                category=category,
                confidence=1.0,
            ),
            recommendation=Recommendation(action=action, reason=reason),
        )

    # =====================================================================
    # MOVE
    # =====================================================================

    @patch("shutil.move")
    @patch("pathlib.Path.mkdir")
    def test_move_success(self, mock_mkdir, mock_move) -> None:
        dest = Path("/destination")
        item = self.make_item("/source/old.zip", 500, FileCategory.ARCHIVE, SuggestedAction.MOVE)
        report = execute([item], dest, dry_run=False)
        assert len(report.results) == 1
        assert report.results[0].status is ExecutionStatus.SUCCESS
        assert "Moved to" in (report.results[0].message or "")
        mock_move.assert_called_once()

    @patch("shutil.move")
    @patch("pathlib.Path.mkdir")
    def test_move_dry_run_does_not_call_move(self, mock_mkdir, mock_move) -> None:
        dest = Path("/destination")
        item = self.make_item("/source/old.zip", 500, FileCategory.ARCHIVE, SuggestedAction.MOVE)
        report = execute([item], dest, dry_run=True)
        assert len(report.results) == 1
        assert report.results[0].status is ExecutionStatus.SUCCESS
        assert "Would move" in (report.results[0].message or "")
        assert "Would move" in report.results[0].message or ""
        mock_move.assert_not_called()

    @patch("shutil.move")
    @patch("pathlib.Path.mkdir")
    def test_move_destination_exists_is_skipped(self, mock_mkdir, mock_move) -> None:
        dest = Path("/destination")
        item = self.make_item("/source/old.zip", 500, FileCategory.ARCHIVE, SuggestedAction.MOVE)

        # Simulate that destination file already exists
        with patch("pathlib.Path.exists", return_value=True):
            report = execute([item], dest, dry_run=False)

        assert report.results[0].status is ExecutionStatus.SKIPPED
        assert "already exists" in (report.results[0].message or "")
        mock_move.assert_not_called()

    @patch("shutil.move", side_effect=PermissionError("Permission denied"))
    @patch("pathlib.Path.mkdir")
    def test_move_permission_denied(self, mock_mkdir, mock_move) -> None:
        dest = Path("/destination")
        item = self.make_item("/source/old.zip", 500, FileCategory.ARCHIVE, SuggestedAction.MOVE)
        report = execute([item], dest, dry_run=False)
        assert report.results[0].status is ExecutionStatus.FAILED
        assert "Permission" in (report.results[0].message or "")

    @patch("shutil.move", side_effect=FileNotFoundError("No such file"))
    @patch("pathlib.Path.mkdir")
    def test_move_source_not_found(self, mock_mkdir, mock_move) -> None:
        dest = Path("/destination")
        item = self.make_item("/source/missing.zip", 500, FileCategory.ARCHIVE, SuggestedAction.MOVE)
        report = execute([item], dest, dry_run=False)
        assert report.results[0].status is ExecutionStatus.FAILED
        assert "Source not found" in (report.results[0].message or "")

    # =====================================================================
    # LEAVE
    # =====================================================================

    @patch("shutil.move")
    @patch("pathlib.Path.mkdir")
    def test_leave_is_skipped(self, mock_mkdir, mock_move) -> None:
        item = self.make_item("/photo.jpg", 300, FileCategory.IMAGE, SuggestedAction.LEAVE)
        report = execute([item], Path("/dest"))
        assert report.results[0].status is ExecutionStatus.SKIPPED
        assert "No action required" in (report.results[0].message or "")
        mock_move.assert_not_called()

    # =====================================================================
    # None action
    # =====================================================================

    @patch("shutil.move")
    @patch("pathlib.Path.mkdir")
    def test_none_action_is_skipped(self, mock_mkdir, mock_move) -> None:
        item = self.make_item("/photo.jpg", 300, FileCategory.UNKNOWN, None)
        report = execute([item], Path("/dest"))
        assert report.results[0].status is ExecutionStatus.SKIPPED
        assert "No recommendation" in (report.results[0].message or "")
        mock_move.assert_not_called()

    # =====================================================================
    # Batch processing
    # =====================================================================

    @patch("shutil.move")
    @patch("pathlib.Path.mkdir")
    def test_multiple_items_all_processed(self, mock_mkdir, mock_move) -> None:
        items = [
            self.make_item("/a.zip", 200, FileCategory.ARCHIVE, SuggestedAction.MOVE),
            self.make_item("/b.jpg", 300, FileCategory.IMAGE, SuggestedAction.LEAVE),
            self.make_item("/c.dmg", 400, FileCategory.INSTALLER, SuggestedAction.MOVE),
        ]
        report = execute(items, Path("/dest"))
        assert len(report.results) == 3
        assert report.results[0].status is ExecutionStatus.SUCCESS
        assert report.results[1].status is ExecutionStatus.SKIPPED
        assert report.results[2].status is ExecutionStatus.SUCCESS
        assert mock_move.call_count == 2

    # =====================================================================
    # Structural
    # =====================================================================

    @patch("shutil.move")
    @patch("pathlib.Path.mkdir")
    def test_returns_execution_report(self, mock_mkdir, mock_move) -> None:
        item = self.make_item("/a.zip", 200, FileCategory.ARCHIVE, SuggestedAction.MOVE)
        report = execute([item], Path("/dest"))
        assert isinstance(report, ExecutionReport)

    def test_no_mutation_of_inputs(self) -> None:
        item = self.make_item("/a.zip", 200, FileCategory.ARCHIVE, SuggestedAction.MOVE)
        items = [item]
        original = (item.analysis.metadata.path, item.recommendation.action)
        with patch("shutil.move"), patch("pathlib.Path.mkdir"):
            execute(items, Path("/dest"))
        assert items[0].analysis.metadata.path == original[0]
        assert items[0].recommendation.action == original[1]


class TestExecuteIntegration:
    """Integration tests — use real filesystem via tmp_path."""

    def make_item(
        self,
        path: str,
        size: int = 100,
        category: FileCategory = FileCategory.UNKNOWN,
        action: SuggestedAction | None = None,
        reason: str = "",
    ) -> ReviewItem:
        return ReviewItem(
            analysis=AnalysisResult(
                metadata=FileMetadata(
                    path=Path(path),
                    size=size,
                    created_time=1000.0,
                    modified_time=2000.0,
                ),
                category=category,
                confidence=1.0,
            ),
            recommendation=Recommendation(action=action, reason=reason),
        )

    def test_move_file_on_real_filesystem(self, tmp_path: Path) -> None:
        src_file = tmp_path / "source" / "old.zip"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("some data")

        dest = tmp_path / "archive"
        item = self.make_item(str(src_file), 100, FileCategory.ARCHIVE, SuggestedAction.MOVE)

        report = execute([item], dest, dry_run=False)

        assert report.results[0].status is ExecutionStatus.SUCCESS
        assert (dest / "old.zip").exists()
        assert not src_file.exists()

    def test_destination_directory_created_automatically(self, tmp_path: Path) -> None:
        src_file = tmp_path / "old.zip"
        src_file.write_text("data")

        dest = tmp_path / "nested" / "archive"
        item = self.make_item(str(src_file), 100, FileCategory.ARCHIVE, SuggestedAction.MOVE)

        report = execute([item], dest, dry_run=False)

        assert report.results[0].status is ExecutionStatus.SUCCESS
        assert (dest / "old.zip").exists()

    def test_collision_is_skipped(self, tmp_path: Path) -> None:
        src_file = tmp_path / "old.zip"
        src_file.write_text("source data")

        dest = tmp_path / "archive"
        dest.mkdir(parents=True)
        existing = dest / "old.zip"
        existing.write_text("existing data")

        item = self.make_item(str(src_file), 100, FileCategory.ARCHIVE, SuggestedAction.MOVE)

        report = execute([item], dest, dry_run=False)

        assert report.results[0].status is ExecutionStatus.SKIPPED
        assert existing.read_text() == "existing data"  # untouched
        assert src_file.exists()  # original not removed

    def test_dry_run_does_not_affect_filesystem(self, tmp_path: Path) -> None:
        src_file = tmp_path / "old.zip"
        src_file.write_text("data")

        dest = tmp_path / "archive"
        item = self.make_item(str(src_file), 100, FileCategory.ARCHIVE, SuggestedAction.MOVE)

        report = execute([item], dest, dry_run=True)

        assert report.results[0].status is ExecutionStatus.SUCCESS
        assert "Would move" in (report.results[0].message or "")
        assert src_file.exists()
        assert not dest.exists()

    def test_destination_persists_after_successful_move(self, tmp_path: Path) -> None:
        """After a successful MOVE, the destination file exists and src is gone."""
        src_file = tmp_path / "old.zip"
        src_file.write_text("data")
        dest = tmp_path / "archive"
        item = self.make_item(str(src_file), 100, FileCategory.ARCHIVE, SuggestedAction.MOVE)

        report = execute([item], dest, dry_run=False)
        assert report.results[0].status is ExecutionStatus.SUCCESS
        assert (dest / "old.zip").exists()
        assert not src_file.exists()
