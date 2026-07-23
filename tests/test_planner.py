"""Tests for the Planner module.

The planner is a pure function. No filesystem, no mocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.action import SuggestedAction
from models.analysis import AnalysisResult
from models.category import FileCategory
from models.metadata import FileMetadata
from models.recommendation import Recommendation

from core.planner import plan


class TestPlan:
    """plan() should apply policy correctly for every FileCategory."""

    def make_result(
        self,
        category: FileCategory,
        confidence: float = 1.0,
        path: str = "/tmp/test.txt",
    ) -> AnalysisResult:
        return AnalysisResult(
            metadata=FileMetadata(
                path=Path(path),
                size=100,
                created_time=1000.0,
                modified_time=2000.0,
            ),
            category=category,
            confidence=confidence,
        )

    # =====================================================================
    # Category → action mapping (confidence = 1.0 for all)
    # =====================================================================

    def test_image_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.IMAGE))
        assert rec.action is None

    def test_video_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.VIDEO))
        assert rec.action is None

    def test_audio_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.AUDIO))
        assert rec.action is None

    def test_document_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.DOCUMENT))
        assert rec.action is None

    def test_project_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.PROJECT))
        assert rec.action is None

    def test_pdf_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.PDF))
        assert rec.action is None

    def test_temporary_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.TEMPORARY))
        assert rec.action is None

    def test_archive_returns_move(self) -> None:
        rec = plan(self.make_result(FileCategory.ARCHIVE))
        assert rec.action == SuggestedAction.MOVE
        assert "Archive" in rec.reason

    def test_installer_returns_move(self) -> None:
        rec = plan(self.make_result(FileCategory.INSTALLER))
        assert rec.action == SuggestedAction.MOVE
        assert "Installer" in rec.reason

    def test_unknown_returns_none(self) -> None:
        rec = plan(self.make_result(FileCategory.UNKNOWN))
        assert rec.action is None

    # =====================================================================
    # Confidence gate
    # =====================================================================

    def test_full_confidence_archive_returns_move(self) -> None:
        """confidence = 1.0 passes the gate."""
        rec = plan(self.make_result(FileCategory.ARCHIVE, confidence=1.0))
        assert rec.action == SuggestedAction.MOVE

    def test_sub_one_confidence_archive_returns_none(self) -> None:
        """confidence = 0.999999 is blocked by the gate."""
        rec = plan(self.make_result(FileCategory.ARCHIVE, confidence=0.999999))
        assert rec.action is None
        assert "Insufficient" in rec.reason

    def test_zero_confidence_archive_returns_none(self) -> None:
        """confidence = 0.0 is also blocked."""
        rec = plan(self.make_result(FileCategory.ARCHIVE, confidence=0.0))
        assert rec.action is None
        assert "Insufficient" in rec.reason

    # =====================================================================
    # Structural properties
    # =====================================================================

    def test_returns_recommendation(self) -> None:
        rec = plan(self.make_result(FileCategory.DOCUMENT))
        assert isinstance(rec, Recommendation)

    def test_deterministic(self) -> None:
        result = self.make_result(FileCategory.ARCHIVE)
        assert plan(result) == plan(result)

    def test_no_mutation_of_input(self) -> None:
        result = self.make_result(FileCategory.ARCHIVE)
        original = AnalysisResult(
            metadata=result.metadata,
            category=result.category,
            confidence=result.confidence,
        )
        plan(result)
        assert result == original