"""Tests for formatting utilities.

Pure number-to-string functions. No fixtures, no filesystem.
"""

from __future__ import annotations

import pytest

from utils.formatting import format_bytes, format_percentage


class TestFormatBytes:
    """format_bytes should convert byte counts to human-readable strings."""

    def test_zero_bytes(self) -> None:
        assert format_bytes(0) == "0 B"

    def test_one_byte(self) -> None:
        assert format_bytes(1) == "1 B"

    def test_1023_bytes(self) -> None:
        assert format_bytes(1023) == "1023 B"

    def test_one_kb(self) -> None:
        assert format_bytes(1024) == "1.0 KB"

    def test_one_mb(self) -> None:
        assert format_bytes(1048576) == "1.0 MB"

    def test_one_gb(self) -> None:
        assert format_bytes(1073741824) == "1.0 GB"

    def test_fractional_kb(self) -> None:
        assert format_bytes(1536) == "1.5 KB"

    def test_fractional_mb(self) -> None:
        assert format_bytes(1572864) == "1.5 MB"

    def test_large_number(self) -> None:
        assert format_bytes(5_000_000_000_000) == "4.5 TB"

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="size must be non-negative"):
            format_bytes(-1)


class TestFormatPercentage:
    """format_percentage should express part/total as a percentage."""

    def test_zero_part(self) -> None:
        assert format_percentage(0, 2000) == "0.0%"

    def test_quarter(self) -> None:
        assert format_percentage(500, 2000) == "25.0%"

    def test_half(self) -> None:
        assert format_percentage(1000, 2000) == "50.0%"

    def test_full(self) -> None:
        assert format_percentage(2000, 2000) == "100.0%"

    def test_small_fraction(self) -> None:
        assert format_percentage(1, 10000) == "0.0%"

    def test_one_digit_precision(self) -> None:
        assert format_percentage(333, 1000) == "33.3%"

    def test_negative_part_raises(self) -> None:
        with pytest.raises(ValueError, match="part must be non-negative"):
            format_percentage(-1, 100)

    def test_zero_total_raises(self) -> None:
        with pytest.raises(ValueError, match="total must be positive"):
            format_percentage(100, 0)

    def test_negative_total_raises(self) -> None:
        with pytest.raises(ValueError, match="total must be positive"):
            format_percentage(100, -1)