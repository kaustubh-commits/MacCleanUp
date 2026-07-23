"""
Scanner — filesystem traversal and metadata collection.

Single responsibility: discover filesystem entries and convert them into
immutable FileMetadata objects.

The Scanner does NOT classify files, compute hashes, recommend actions,
or modify the filesystem. It only discovers.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from models.metadata import FileMetadata
from models.scan_error import ScanError
from models.scanner_result import ScannerResult


def scan(
    root: Path,
    exclude_names: set[str] | None = None,
) -> ScannerResult:
    """Walk *root* and produce FileMetadata for every entry discovered.

    Parameters
    ----------
    root : Path
        Absolute path to the directory to scan.
    exclude_names : set[str] | None
        Set of directory/file basenames to skip entirely (e.g.
        ``{".git", ".venv", "__MACOSX"}``). Directories matching
        an excluded name are not entered; files matching an excluded
        name are not yielded.

    Returns
    -------
    ScannerResult
        All discovered entries and any warnings collected during traversal.

    Raises
    ------
    ValueError
        If *root* is not an absolute path or does not exist.
    """
    if not root.is_absolute():
        raise ValueError(f"root must be absolute, got: {root}")

    if not root.exists():
        raise ValueError(f"root does not exist: {root}")

    if not root.is_dir():
        raise ValueError(f"root must be a directory, got: {root}")

    excludes: set[str] = exclude_names if exclude_names is not None else set()
    entries: list[FileMetadata] = []
    warnings: list[ScanError] = []

    for entry in _walk(root, excludes, warnings):
        entries.append(entry)

    return ScannerResult(
        root=root,
        entries=entries,
        warnings=warnings,
    )


def _walk(
    path: Path,
    exclude_names: set[str],
    warnings: list[ScanError],
) -> Iterator[FileMetadata]:
    """Recursively walk *path*, yielding FileMetadata objects.

    This is intentionally a private generator so that ``scan()`` can
    collect results into a list-based ScannerResult without exposing
    the generator to callers.
    """
    try:
        with os.scandir(path) as it:
            for entry in it:
                yield from _handle_entry(entry, exclude_names, warnings)
    except PermissionError:
        warnings.append(
            ScanError(
                path=path,
                message="permission denied — skipped directory",
            )
        )
    except OSError as exc:
        warnings.append(
            ScanError(
                path=path,
                message=f"could not read directory — {exc}",
            )
        )


def _handle_entry(
    entry: os.DirEntry,
    exclude_names: set[str],
    warnings: list[ScanError],
) -> Iterator[FileMetadata]:
    """Process a single DirEntry, yielding FileMetadata if appropriate.

    Responsibilities:
    - Skip symlinks (all types — we do not follow them).
    - Skip entries whose name is in the exclusion set.
    - Recurse into directories (unless excluded).
    - Yield FileMetadata for readable entries.
    - Record ScanError for entries that cannot be read.
    """
    # --- Skip symlinks entirely ---
    try:
        if entry.is_symlink():
            warnings.append(
                ScanError(
                    path=Path(entry.path),
                    message="symlink — skipped (symlinks are not followed)",
                )
            )
            return
    except OSError:
        # entry.is_symlink() can fail for dangling symlinks on some systems
        warnings.append(
            ScanError(
                path=Path(entry.path),
                message="broken symlink — skipped",
            )
        )
        return

    # --- Skip excluded names ---
    if entry.name in exclude_names:
        return

    try:
        is_dir = entry.is_dir(follow_symlinks=False)
    except OSError:
        warnings.append(
            ScanError(
                path=Path(entry.path),
                message="could not determine entry type — skipped",
            )
        )
        return

    # --- Recurse into directories ---
    if is_dir:
        yield from _walk(Path(entry.path), exclude_names, warnings)
        # Also yield the directory entry itself so it appears in results
        yield from _yield_entry(entry, is_dir=True, warnings=warnings)
        return

    # --- Yield file entry ---
    yield from _yield_entry(entry, is_dir=False, warnings=warnings)


def _yield_entry(
    entry: os.DirEntry,
    is_dir: bool,
    warnings: list[ScanError],
) -> Iterator[FileMetadata]:
    """Attempt to read metadata and yield a FileMetadata.

    If the stat call fails (e.g. file was deleted between discovery
    and stat), a warning is recorded and nothing is yielded.
    """
    try:
        stat = entry.stat(follow_symlinks=False)
    except OSError as exc:
        warnings.append(
            ScanError(
                path=Path(entry.path),
                message=f"could not read metadata — {exc}",
            )
        )
        return

    yield FileMetadata(
        path=Path(entry.path),
        size=stat.st_size,
        created_time=getattr(stat, "st_birthtime", stat.st_mtime),
        modified_time=stat.st_mtime,
        is_directory=is_dir,
    )