"""
FileMetadata — immutable domain model for a single filesystem entry.

Represents the objective facts about a file or directory discovered by the
Scanner at scan time. Contains no derived analysis — no category, no hash,
no recommendation.

This is the foundational model of the application. Every downstream module
depends on it. Keep it simple, keep it immutable, keep it clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileMetadata:
    """Immutable metadata for a single filesystem entry.

    Represents exactly one filesystem object (file or directory) discovered
    by the Scanner. All fields are set at construction time and never mutated.

    Fields
    ------
    path : Path
        Absolute path to the filesystem entry.
    size : int
        Size in bytes. Non-negative. For directories this is the stat-reported
        size (often 4096 on macOS), not the recursive subtree size.
    created_time : float
        Unix epoch timestamp of creation (st_birthtime on macOS).
        Accepted exactly as reported by the OS — no validation against
        modified_time or current time.
    modified_time : float
        Unix epoch timestamp of last modification (st_mtime).
        Accepted exactly as reported by the OS.
    is_directory : bool
        True if this entry is a directory, False if it is a file.

    Properties
    ----------
    name : str
        The filename or directory name (path.name).
    extension : str
        Lowercased file suffix (path.suffix.lower()). Empty string for
        directories and files without extensions.
    parent : Path
        The parent directory path (path.parent).
    """

    path: Path
    size: int
    created_time: float
    modified_time: float
    is_directory: bool = False

    def __post_init__(self) -> None:
        if not self.path.is_absolute():
            raise ValueError(
                f"path must be absolute, got: {self.path}"
            )
        if self.size < 0:
            raise ValueError(
                f"size must be non-negative, got: {self.size}"
            )

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()

    @property
    def parent(self) -> Path:
        return self.path.parent