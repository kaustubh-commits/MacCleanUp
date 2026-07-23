"""
ScanError — a warning recorded by the Scanner when it cannot read an entry.

Errors are not fatal. The Scanner continues traversal and collects errors
so the Reporter can display them. One inaccessible file should never stop
a scan of thousands of files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScanError:
    """A non-fatal warning recorded during filesystem traversal.

    The Scanner encountered an entry it could not process but continued
    the scan. Errors are collected in ScannerResult.warnings.

    Fields
    ------
    path : Path
        The path that caused the error.
    message : str
        A human-readable description of the problem (e.g., "permission denied",
        "broken symlink", "file not found").
    """

    path: Path
    message: str