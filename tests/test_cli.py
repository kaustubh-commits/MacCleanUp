"""Tests for the CLI entry point.

Tests use ``argv`` injection to avoid polluting ``sys.argv``.
No stdout mocking — test exit codes and call flow instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.main import main, _parse_args, EXIT_SUCCESS, EXIT_CANCELLED, EXIT_INVALID_ARGS


class TestParseArgs:
    """Argument parsing should handle valid and invalid inputs."""

    def test_path_required(self) -> None:
        with pytest.raises(SystemExit):
            _parse_args([])

    def test_minimal_args(self) -> None:
        args = _parse_args(["/tmp"])
        assert args.path == "/tmp"
        assert args.execute is False
        assert args.dry_run is False
        assert args.verbose is False

    def test_verbose_flag(self) -> None:
        args = _parse_args(["/tmp", "--verbose"])
        assert args.verbose is True

    def test_verbose_short_flag(self) -> None:
        args = _parse_args(["/tmp", "-v"])
        assert args.verbose is True

    def test_execute_flag(self) -> None:
        args = _parse_args(["/tmp", "--execute"])
        assert args.execute is True

    def test_dry_run_flag(self) -> None:
        args = _parse_args(["/tmp", "--dry-run"])
        assert args.dry_run is True

    def test_destination_override(self) -> None:
        args = _parse_args(["/tmp", "--destination", "/custom/path"])
        assert args.destination == Path("/custom/path")

    def test_destination_default(self) -> None:
        args = _parse_args(["/tmp"])
        assert args.destination == Path.home() / "MacCleanUp" / "Archive"


class TestMain:
    """CLI entry point should handle errors and flow correctly."""

    def test_invalid_path_exits_with_error(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["/nonexistent_path_macleanup_test"])
        assert exc.value.code == EXIT_INVALID_ARGS

    def test_nonexistent_name_exits_with_error(self) -> None:
        """A name that doesn't exist under home should also fail."""
        with pytest.raises(SystemExit) as exc:
            main(["nonexistent_dir_macleanup_xyz789"])
        assert exc.value.code == EXIT_INVALID_ARGS

    def test_help_prints_and_exits(self) -> None:
        with pytest.raises(SystemExit) as exc:
            _parse_args(["--help"])
        assert exc.value.code == 0

    def test_analyze_directory_valid(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        # Should not raise — analysis completes without execution
        try:
            main([str(tmp_path)])
        except SystemExit as e:
            pytest.fail(f"main() raised SystemExit unexpectedly: {e.code}")

    def test_verbose_directory_valid(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        # --verbose should also complete without error
        try:
            main([str(tmp_path), "--verbose"])
        except SystemExit as e:
            pytest.fail(f"main() raised SystemExit unexpectedly: {e.code}")
