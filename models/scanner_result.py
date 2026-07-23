"""
ScannerResult — the output of a single scan operation.

This represents only filesystem discovery. It is NOT the application's
final ScanResult. The orchestration layer later assembles the final
ScanResult after classification, duplicate detection, and planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from models.metadata import FileMetadata
from models.scan_error import ScanError


@dataclass
class ScannerResult:
    """The outcome of a filesystem scan.

    Contains everything the Scanner discovered — entries it successfully
    read and warnings for entries it could not process.

    Fields
    ------
    root : Path
        The root directory that was scanned.
    entries : list[FileMetadata]
        All filesystem entries discovered during the scan (files and
        directories). Empty if nothing was found.
    warnings : list[ScanError]
        Non-fatal errors encountered during traversal (permission denied,
        broken symlinks, etc.). Empty if the scan completed without issues.
    """

    root: Path
    entries: list[FileMetadata] = field(default_factory=list)
    warnings: list[ScanError] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        """Number of entries that are regular files (not directories)."""
        return sum(1 for e in self.entries if not e.is_directory)

    @property
    def total_directories(self) -> int:
        """Number of entries that are directories."""
        return sum(1 for e in self.entries if e.is_directory)

    @property
    def total_size(self) -> int:
        """Total size of all entries in bytes.

        Note: For directories this includes the stat-reported size
        (typically 4096 on macOS), not recursive subtree sizes.
        """
        return sum(e.size for e in self.entries)