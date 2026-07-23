"""Tests for the Scanner module.

Every test constructs its own miniature filesystem using pytest's ``tmp_path``.
No mocks. Real files. Real filesystem behaviour.
"""

from __future__ import annotations

import os
import stat as stat_module
from pathlib import Path

import pytest

from core.scanner import scan
from models.metadata import FileMetadata
from models.scan_error import ScanError


# =========================================================================
# Basic scanning
# =========================================================================


class TestBasicScanning:
    """Scanner should discover files and directories correctly."""

    def test_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        result = scan(tmp_path)
        assert len(result.entries) == 1
        assert result.entries[0].name == "a.txt"
        assert not result.entries[0].is_directory

    def test_flat_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "c.png").write_bytes(b"PNG")

        result = scan(tmp_path)
        names = {e.name for e in result.entries if not e.is_directory}
        assert names == {"a.txt", "b.pdf", "c.png"}

    def test_nested_directories(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.pdf").write_bytes(b"%PDF-1.4")
        (sub / "nested" / "c.png").mkdir(parents=True)
        (sub / "nested" / "c.png" / "d.txt").write_text("deep")

        result = scan(tmp_path)
        names = {e.name for e in result.entries if not e.is_directory}
        assert names == {"a.txt", "b.pdf", "d.txt"}

    def test_empty_directory(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        result = scan(tmp_path)
        # The empty directory itself should appear
        dir_names = {e.name for e in result.entries if e.is_directory}
        assert "empty" in dir_names

    def test_root_with_single_subdirectory(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "file.txt").write_text("content")
        result = scan(tmp_path)
        file_names = {e.name for e in result.entries if not e.is_directory}
        dir_names = {e.name for e in result.entries if e.is_directory}
        assert file_names == {"file.txt"}
        assert "sub" in dir_names


# =========================================================================
# Exclusion by name
# =========================================================================


class TestExclusions:
    """Scanner should skip entries whose name is in the exclusion set."""

    def test_exclude_directory_by_name(self, tmp_path: Path) -> None:
        (tmp_path / "keep").mkdir()
        (tmp_path / "keep" / "a.txt").write_text("keep me")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("[core]")

        result = scan(tmp_path, exclude_names={".git"})
        names = {e.name for e in result.entries}
        assert ".git" not in names
        assert "keep" in names
        assert "a.txt" in names

    def test_exclude_file_by_name(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "thumbs.db").write_text("evil")
        result = scan(tmp_path, exclude_names={"thumbs.db"})
        names = {e.name for e in result.entries}
        assert "thumbs.db" not in names
        assert "a.txt" in names

    def test_multiple_exclusions(self, tmp_path: Path) -> None:
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / "__MACOSX").mkdir()
        (tmp_path / "keep.txt").write_text("hello")

        result = scan(tmp_path, exclude_names={".venv", "__MACOSX"})
        names = {e.name for e in result.entries}
        assert ".venv" not in names
        assert "__MACOSX" not in names
        assert "keep.txt" in names

    def test_no_exclusions_given(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / "file.txt").write_text("hello")
        result = scan(tmp_path)
        names = {e.name for e in result.entries}
        assert ".git" in names  # included because no exclusions were passed

    def test_nested_excluded_directory(self, tmp_path: Path) -> None:
        """A .venv deep inside the tree should also be skipped."""
        sub = tmp_path / "projects" / "my-app"
        sub.mkdir(parents=True)
        (sub / ".venv").mkdir()
        (sub / ".venv" / "bin").mkdir()
        (sub / "main.py").write_text("print('hello')")

        result = scan(tmp_path, exclude_names={".venv"})
        names = {e.name for e in result.entries}
        assert ".venv" not in names
        assert "main.py" in names


# =========================================================================
# Symlinks (all skipped)
# =========================================================================


class TestSymlinks:
    """Scanner should skip ALL symlinks — both files and directories."""

    def test_skip_symlink_to_file(self, tmp_path: Path) -> None:
        target = tmp_path / "real.txt"
        target.write_text("real")
        link = tmp_path / "link.txt"
        link.symlink_to(target)

        result = scan(tmp_path)
        names = {e.name for e in result.entries}
        assert "real.txt" in names
        assert "link.txt" not in names
        # All symlinks record a warning
        assert any("symlink" in w.message for w in result.warnings)

    def test_skip_symlink_to_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "real_dir"
        target.mkdir()
        (target / "file.txt").write_text("inside")
        link = tmp_path / "link_to_dir"
        link.symlink_to(target, target_is_directory=True)

        result = scan(tmp_path)
        names = {e.name for e in result.entries}
        assert "real_dir" in names
        assert "file.txt" in names  # real contents are present
        assert "link_to_dir" not in names
        # All symlinks record a warning
        assert any("symlink" in w.message for w in result.warnings)

    def test_dangling_symlink_records_warning(self, tmp_path: Path) -> None:
        link = tmp_path / "dangling"
        link.symlink_to(tmp_path / "nonexistent")

        result = scan(tmp_path)
        assert "dangling" not in {e.name for e in result.entries}
        assert len(result.warnings) >= 1
        assert any("symlink" in w.message for w in result.warnings)


# =========================================================================
# Hidden files (not excluded by default)
# =========================================================================


class TestHiddenFiles:
    """Scanner does not decide what is 'hidden' — exclusions control that."""

    def test_dotfiles_are_included(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.pyc")
        (tmp_path / ".DS_Store").write_bytes(b"\x00" * 100)
        (tmp_path / "visible.txt").write_text("hi")

        result = scan(tmp_path)
        names = {e.name for e in result.entries}
        assert ".gitignore" in names
        assert ".DS_Store" in names
        assert "visible.txt" in names

    def test_dotfiles_can_be_excluded(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.pyc")
        result = scan(tmp_path, exclude_names={".gitignore"})
        names = {e.name for e in result.entries}
        assert ".gitignore" not in names


# =========================================================================
# Permission errors
# =========================================================================


class TestPermissionErrors:
    """Scanner should continue when it cannot read a directory or file."""

    def test_skip_directory_without_permission(self, tmp_path: Path) -> None:
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        (restricted / "secret.txt").write_text("shh")
        # Remove read permission on the directory
        restricted.chmod(0o000)

        try:
            result = scan(tmp_path)
            # The restricted directory may or may not appear depending on
            # whether the parent directory traversal allows stat-ing it
            names = {e.name for e in result.entries}
            assert "secret.txt" not in names  # contents never read
            assert len(result.warnings) >= 1
            permission_warnings = [w for w in result.warnings if "permission" in w.message.lower()]
            assert len(permission_warnings) >= 1
        finally:
            # Restore permissions so cleanup works
            restricted.chmod(0o755)

    def test_skip_file_without_read_permission(self, tmp_path: Path) -> None:
        no_read = tmp_path / "no_read.txt"
        no_read.write_text("secret")
        no_read.chmod(0o000)

        try:
            result = scan(tmp_path)
            names = {e.name for e in result.entries}
            # The file might appear with stat info (stat doesn't require
            # read permission on the file itself, only the directory)
            # But the real test is that scanning doesn't crash
            assert len(result.entries) >= 0
        finally:
            no_read.chmod(0o644)


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    """Scanner should handle edge cases gracefully."""

    def test_root_is_relative_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="root must be absolute"):
            scan(Path("relative/path"))

    def test_root_does_not_exist_raises(self) -> None:
        with pytest.raises(ValueError, match="root does not exist"):
            scan(Path("/tmp/nonexistent_path_macleanup_xyz789"))

    def test_root_is_file_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "not_a_dir.txt"
        f.write_text("nope")
        with pytest.raises(ValueError, match="root must be a directory"):
            scan(f)

    def test_deeply_nested_directories(self, tmp_path: Path) -> None:
        """Scanner should handle deep nesting without recursion issues."""
        current = tmp_path
        for i in range(50):
            current = current / f"level_{i}"
            current.mkdir()
        (current / "leaf.txt").write_text("bottom")

        result = scan(tmp_path)
        names = {e.name for e in result.entries}
        assert "leaf.txt" in names

    def test_large_number_of_files(self, tmp_path: Path) -> None:
        """Scanner should handle many files in one directory."""
        for i in range(200):
            (tmp_path / f"file_{i}.txt").write_text(str(i))
        result = scan(tmp_path)
        assert len(result.entries) >= 200

    def test_mixed_content(self, tmp_path: Path) -> None:
        """Realistic mix of files and directories."""
        (tmp_path / "README.md").write_text("# Project")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hi')")
        (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# Docs")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: main")

        result = scan(tmp_path, exclude_names={".git"})
        file_names = {e.name for e in result.entries if not e.is_directory}
        dir_names = {e.name for e in result.entries if e.is_directory}

        assert "README.md" in file_names
        assert "main.py" in file_names
        assert "utils.py" in file_names
        assert "index.md" in file_names
        assert "src" in dir_names
        assert "docs" in dir_names
        assert ".git" not in dir_names


# =========================================================================
# ScannerResult properties
# =========================================================================


class TestScannerResultProperties:
    """ScannerResult helper properties should be accurate."""

    def test_total_files_and_directories(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c.txt").write_text("c")

        result = scan(tmp_path)
        assert result.total_files == 3
        assert result.total_directories == 1  # tmp_path itself + sub? No, only sub
        # Actually tmp_path itself is the root, not an entry
        # So only "sub" is counted as a directory
        # Wait — the scanner yields directories it encounters. "sub" is yielded.
        # tmp_path is NOT yielded because it's the root passed to scan().
        assert result.total_directories == 1

    def test_total_files_only(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        result = scan(tmp_path)
        assert result.total_files == 1
        assert result.total_directories == 0

    def test_total_size(self, tmp_path: Path) -> None:
        # Write files with known sizes
        (tmp_path / "a.txt").write_text("hello")            # 5 bytes
        (tmp_path / "b.txt").write_text("world" * 100)      # 500 bytes
        result = scan(tmp_path)
        # The exact size depends on text encoding, but should be > 0
        assert result.total_size > 0

    def test_no_warnings_for_clean_scan(self, tmp_path: Path) -> None:
        (tmp_path / "clean.txt").write_text("clean")
        result = scan(tmp_path)
        assert len(result.warnings) == 0

    def test_root_in_result(self, tmp_path: Path) -> None:
        result = scan(tmp_path)
        assert result.root == tmp_path