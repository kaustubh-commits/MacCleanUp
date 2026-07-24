"""
Formatting utilities for human-readable terminal output.

Pure functions. No I/O, no state, no dependency on other project modules.
"""

from __future__ import annotations


_SUFFIXES = ("B", "KB", "MB", "GB", "TB")


def format_bytes(size: int) -> str:
    """Convert a byte count into a human-readable string.

    Parameters
    ----------
    size : int
        Size in bytes. Must be non-negative.

    Returns
    -------
    str
        Human-readable representation, e.g. ``"1.5 KB"``, ``"3.2 GB"``.

    Notes
    -----
    Uses 1024-based (binary) units. Values less than 1024 B are displayed
    as bytes without a decimal.
    """
    if size < 0:
        raise ValueError(f"size must be non-negative, got: {size}")
    if size < 1024:
        return f"{size} B"

    magnitude = 0
    remaining = size
    while remaining >= 1024 and magnitude < len(_SUFFIXES) - 1:
        remaining /= 1024
        magnitude += 1

    return f"{remaining:.1f} {_SUFFIXES[magnitude]}"


def format_percentage(part: int, total: int) -> str:
    """Express *part* as a percentage of *total*.

    Parameters
    ----------
    part : int
        The numerator. Must be non-negative.
    total : int
        The denominator. Must be positive.

    Returns
    -------
    str
        Percentage with one decimal place, e.g. ``"25.0%"``.
    """
    if part < 0:
        raise ValueError(f"part must be non-negative, got: {part}")
    if total <= 0:
        raise ValueError(f"total must be positive, got: {total}")

    return f"{(part / total) * 100:.1f}%"