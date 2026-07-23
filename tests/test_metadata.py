"""Tests for FileMetadata domain model."""

from __future__ import annotations

from pathlib import Path

import pytest

from models.metadata import FileMetadata


class TestFileMetadataCreation:
    """FileMetadata should be constructable with valid arguments."""

    def test_create_file(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/Downloads/file.txt"),
            size=1024,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.path == Path("/Users/test/Downloads/file.txt")
        assert meta.size == 1024
        assert meta.created_time == 1000.0
        assert meta.modified_time == 2000.0
        assert meta.is_directory is False

    def test_create_directory(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/Downloads/Project"),
            size=4096,
            created_time=1000.0,
            modified_time=2000.0,
            is_directory=True,
        )
        assert meta.is_directory is True

    def test_create_empty_file(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/empty.txt"),
            size=0,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.size == 0


class TestFileMetadataImmutability:
    """FileMetadata must be immutable after construction."""

    def test_cannot_modify_path(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/fixed.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        with pytest.raises(AttributeError):
            meta.path = Path("/tmp/changed.txt")  # type: ignore[misc]

    def test_cannot_modify_size(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/fixed.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        with pytest.raises(AttributeError):
            meta.size = 200  # type: ignore[misc]

    def test_cannot_modify_is_directory(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/fixed.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        with pytest.raises(AttributeError):
            meta.is_directory = True  # type: ignore[misc]


class TestFileMetadataValidation:
    """FileMetadata should enforce its invariants."""

    def test_relative_path_raises(self) -> None:
        with pytest.raises(ValueError, match="path must be absolute"):
            FileMetadata(
                path=Path("relative/file.txt"),
                size=100,
                created_time=1000.0,
                modified_time=2000.0,
            )

    def test_negative_size_raises(self) -> None:
        with pytest.raises(ValueError, match="size must be non-negative"):
            FileMetadata(
                path=Path("/tmp/file.txt"),
                size=-1,
                created_time=1000.0,
                modified_time=2000.0,
            )

    def test_zero_size_is_valid(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/empty.txt"),
            size=0,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.size == 0

    def test_large_size_is_valid(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/large.bin"),
            size=10_000_000_000,  # 10 GB, fits in Python int
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.size == 10_000_000_000


class TestFileMetadataProperties:
    """Derived properties should behave correctly."""

    def test_name(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/Downloads/report.pdf"),
            size=500,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.name == "report.pdf"

    def test_name_directory(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/Downloads/Project"),
            size=4096,
            created_time=1000.0,
            modified_time=2000.0,
            is_directory=True,
        )
        assert meta.name == "Project"

    def test_extension(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/archive.zip"),
            size=500,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.extension == ".zip"

    def test_extension_lowercased(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/Photo.JPG"),
            size=500,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.extension == ".jpg"

    def test_extension_none_for_directory(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/Downloads/Stuff"),
            size=4096,
            created_time=1000.0,
            modified_time=2000.0,
            is_directory=True,
        )
        assert meta.extension == ""

    def test_extension_empty_for_no_extension(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/Makefile"),
            size=200,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.extension == ""

    def test_parent(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/Downloads/paper.pdf"),
            size=500,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.parent == Path("/Users/test/Downloads")

    def test_parent_root(self) -> None:
        meta = FileMetadata(
            path=Path("/file.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.parent == Path("/")


class TestFileMetadataEdgeCases:
    """Edge cases for filesystem oddities."""

    def test_hidden_file(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/.gitignore"),
            size=50,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.name == ".gitignore"
        assert meta.extension == ""

    def test_file_with_multiple_dots(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/archive.tar.gz"),
            size=500,
            created_time=1000.0,
            modified_time=2000.0,
        )
        # path.suffix returns only the last suffix
        assert meta.extension == ".gz"

    def test_file_with_spaces_in_name(self) -> None:
        meta = FileMetadata(
            path=Path("/Users/test/My Document.pdf"),
            size=500,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert meta.name == "My Document.pdf"
        assert meta.extension == ".pdf"

    def test_modified_earlier_than_created_is_accepted(self) -> None:
        """OS-reported timestamps can be 'wrong'. We trust the OS."""
        meta = FileMetadata(
            path=Path("/tmp/unusual.txt"),
            size=100,
            created_time=5000.0,  # created later than modified
            modified_time=1000.0,  # modified earlier
        )
        assert meta.created_time == 5000.0
        assert meta.modified_time == 1000.0

    def test_future_timestamp_is_accepted(self) -> None:
        """Future timestamps can occur (NTP, Time Machine, etc.). We accept them."""
        future = 9999999999.0  # year 2286
        meta = FileMetadata(
            path=Path("/tmp/future.txt"),
            size=100,
            created_time=future,
            modified_time=1000.0,
        )
        assert meta.created_time == future


class TestFileMetadataEqualityAndHashing:
    """FileMetadata should be usable in sets and dicts."""

    def test_equality(self) -> None:
        a = FileMetadata(
            path=Path("/tmp/a.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        b = FileMetadata(
            path=Path("/tmp/a.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert a == b

    def test_inequality(self) -> None:
        a = FileMetadata(
            path=Path("/tmp/a.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        b = FileMetadata(
            path=Path("/tmp/b.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        assert a != b

    def test_hashable(self) -> None:
        a = FileMetadata(
            path=Path("/tmp/a.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        b = FileMetadata(
            path=Path("/tmp/b.txt"),
            size=200,
            created_time=3000.0,
            modified_time=4000.0,
        )
        s = {a, b}
        assert len(s) == 2
        assert a in s

    def test_used_as_dict_key(self) -> None:
        meta = FileMetadata(
            path=Path("/tmp/key.txt"),
            size=100,
            created_time=1000.0,
            modified_time=2000.0,
        )
        d = {meta: "found"}
        assert d[meta] == "found"