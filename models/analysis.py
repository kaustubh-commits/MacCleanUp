"""
AnalysisResult — the output of the Classifier.

Maps a FileMetadata to a FileCategory with a confidence score.
Contains no recommendation — that is the Planner's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.metadata import FileMetadata
from models.category import FileCategory


@dataclass(frozen=True)
class AnalysisResult:
    """The result of classifying a single filesystem entry.

    Fields
    ------
    metadata : FileMetadata
        The file that was classified.
    category : FileCategory
        The category assigned by the Classifier.
    confidence : float
        How confident the Classifier is in this assignment.
        Ranges from 0.0 (not confident) to 1.0 (certain).
    """

    metadata: FileMetadata
    category: FileCategory
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got: {self.confidence}"
            )