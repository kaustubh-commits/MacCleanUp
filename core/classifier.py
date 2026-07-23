"""
classify — pure function mapping FileMetadata → AnalysisResult.

Single responsibility: determine what kind of file something is.
No filesystem access, no side effects, no recommendations.
"""

from __future__ import annotations

from models.analysis import AnalysisResult
from models.category import FileCategory
from models.metadata import FileMetadata


_EXTENSION_MAP: dict[str, FileCategory] = {
    ".jpg": FileCategory.IMAGE,
    ".jpeg": FileCategory.IMAGE,
    ".png": FileCategory.IMAGE,
    ".gif": FileCategory.IMAGE,
    ".webp": FileCategory.IMAGE,
    ".heic": FileCategory.IMAGE,
    ".mp4": FileCategory.VIDEO,
    ".mov": FileCategory.VIDEO,
    ".mkv": FileCategory.VIDEO,
    ".avi": FileCategory.VIDEO,
    ".mp3": FileCategory.AUDIO,
    ".wav": FileCategory.AUDIO,
    ".flac": FileCategory.AUDIO,
    ".m4a": FileCategory.AUDIO,
    ".zip": FileCategory.ARCHIVE,
    ".rar": FileCategory.ARCHIVE,
    ".7z": FileCategory.ARCHIVE,
    ".tar": FileCategory.ARCHIVE,
    ".gz": FileCategory.ARCHIVE,
    ".pdf": FileCategory.PDF,
    ".pkg": FileCategory.INSTALLER,
    ".dmg": FileCategory.INSTALLER,
    ".app": FileCategory.INSTALLER,
    ".doc": FileCategory.DOCUMENT,
    ".docx": FileCategory.DOCUMENT,
    ".txt": FileCategory.DOCUMENT,
    ".md": FileCategory.DOCUMENT,
    ".rtf": FileCategory.DOCUMENT,
    ".py": FileCategory.PROJECT,
    ".js": FileCategory.PROJECT,
    ".ts": FileCategory.PROJECT,
    ".java": FileCategory.PROJECT,
    ".cpp": FileCategory.PROJECT,
    ".c": FileCategory.PROJECT,
    ".go": FileCategory.PROJECT,
    ".rs": FileCategory.PROJECT,
}

_Known: float = 1.0
_Unknown: float = 0.0


def classify(metadata: FileMetadata) -> AnalysisResult:
    """Classify a single filesystem entry into a FileCategory.

    Parameters
    ----------
    metadata : FileMetadata
        The file to classify. Uses ``metadata.extension`` for lookup.

    Returns
    -------
    AnalysisResult
        Immutable result with category and confidence.

    Notes
    -----
    For v1, only the last suffix is considered (``Path.suffix``).
    Double extensions like ``.tar.gz`` are not fully resolved.
    """
    if metadata.is_directory:
        return AnalysisResult(
            metadata=metadata,
            category=FileCategory.UNKNOWN,
            confidence=_Unknown,
        )

    category = _EXTENSION_MAP.get(metadata.extension, FileCategory.UNKNOWN)
    confidence = _Known if category is not FileCategory.UNKNOWN else _Unknown
    return AnalysisResult(
        metadata=metadata,
        category=category,
        confidence=confidence,
    )
