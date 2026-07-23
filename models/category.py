"""
FileCategory — the vocabulary for classifying filesystem entries.

Every FileMetadata discovered by the Scanner receives exactly one category
from this enum. No other representation of "what kind of file this is"
should exist in the codebase.
"""

from __future__ import annotations

from enum import Enum, auto


class FileCategory(Enum):
    """Broad category describing the type of a filesystem entry.

    These categories exist to help the user understand what kind of files
    they have. They are intentionally broad — the Planner and the user
    decide what to do, not the category system.

    Members
    -------
    IMAGE       : Photographs, screenshots, graphics (jpg, png, gif, svg, etc.)
    VIDEO       : Video files (mp4, mov, avi, mkv, etc.)
    AUDIO       : Music, podcasts, sound files (mp3, wav, flac, aac, etc.)
    PDF         : PDF documents exclusively
    ARCHIVE     : Compressed files (zip, tar, gz, rar, 7z, etc.)
    INSTALLER   : Software installers (dmg, pkg, app, etc.)
    DOCUMENT    : Text documents, spreadsheets, notes (docx, xlsx, txt, md, etc.)
    PROJECT     : Source code projects, notebooks (py, ipynb, js, java, etc.)
    TEMPORARY   : Cache files, partial downloads, temp files
    UNKNOWN     : Files that do not match any known category
    """

    IMAGE = auto()
    VIDEO = auto()
    AUDIO = auto()
    PDF = auto()
    ARCHIVE = auto()
    INSTALLER = auto()
    DOCUMENT = auto()
    PROJECT = auto()
    TEMPORARY = auto()
    UNKNOWN = auto()