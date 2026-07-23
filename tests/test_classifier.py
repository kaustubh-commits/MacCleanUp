"""Tests for the Classifier module.

No filesystem interaction — the classify function is pure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.classifier import classify
from models.analysis import AnalysisResult
from models.category import FileCategory
from models.metadata import FileMetadata


class TestClassify:
    """classify() should map extensions to FileCategory correctly."""

    def make_metadata(self, path: str, is_directory: bool = False) -> FileMetadata:
        return FileMetadata(
            path=Path(path),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
            is_directory=is_directory,
        )

    def test_jpg_is_image(self) -> None:
        result = classify(self.make_metadata("/photo.jpg"))
        assert result.category == FileCategory.IMAGE

    def test_png_is_image(self) -> None:
        result = classify(self.make_metadata("/image.png"))
        assert result.category == FileCategory.IMAGE

    def test_mp4_is_video(self) -> None:
        result = classify(self.make_metadata("/video.mp4"))
        assert result.category == FileCategory.VIDEO

    def test_zip_is_archive(self) -> None:
        result = classify(self.make_metadata("/archive.zip"))
        assert result.category == FileCategory.ARCHIVE

    def test_pdf_is_pdf(self) -> None:
        result = classify(self.make_metadata("/doc.pdf"))
        assert result.category == FileCategory.PDF

    def test_py_is_project(self) -> None:
        result = classify(self.make_metadata("/script.py"))
        assert result.category == FileCategory.PROJECT

    def test_unknown_extension_is_unknown(self) -> None:
        result = classify(self.make_metadata("/weird.xyz"))
        assert result.category == FileCategory.UNKNOWN

    def test_readme_no_extension_is_unknown(self) -> None:
        result = classify(self.make_metadata("/README"))
        assert result.category == FileCategory.UNKNOWN

    def test_uppercase_extension_normalized(self) -> None:
        result = classify(self.make_metadata("/photo.JPG"))
        assert result.category == FileCategory.IMAGE

    def test_confidence_known_is_one(self) -> None:
        result = classify(self.make_metadata("/doc.pdf"))
        assert result.confidence == 1.0

    def test_confidence_unknown_is_zero(self) -> None:
        result = classify(self.make_metadata("/strange.xyz"))
        assert result.confidence == 0.0

    def test_returns_analysis_result(self) -> None:
        result = classify(self.make_metadata("/test.txt"))
        assert isinstance(result, AnalysisResult)

    def test_metadata_preserved(self) -> None:
        meta = self.make_metadata("/photo.jpg")
        result = classify(meta)
        assert result.metadata is meta

    def test_gitignore_unknown(self) -> None:
        result = classify(self.make_metadata("/.gitignore"))
        assert result.category == FileCategory.UNKNOWN

    def test_empty_extension_unknown(self) -> None:
        result = classify(self.make_metadata("/Makefile"))
        assert result.category == FileCategory.UNKNOWN

    def test_directory_is_unknown(self) -> None:
        """Directories have no meaningful extension -> UNKNOWN."""
        result = classify(self.make_metadata("/some_dir", is_directory=True))
        assert result.category == FileCategory.UNKNOWN
        assert result.confidence == 0.0

    def test_directory_with_extension_ignores_it(self) -> None:
        """Even if a directory name looks like it has an extension, treat as UNKNOWN."""
        result = classify(self.make_metadata("/images.tar", is_directory=True))
        assert result.category == FileCategory.UNKNOWN
        assert result.confidence == 0.0