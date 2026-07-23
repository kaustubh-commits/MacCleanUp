"""
CategorySummary — a grouping of AnalysisResults by FileCategory.

This is a pure data transformation. The UI renders it. The Reporter formats it.
No module should compute per-category totals inline — use this instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.category import FileCategory
from models.analysis import AnalysisResult


@dataclass
class CategorySummary:
    """Aggregated view of all files in a single category.

    Fields
    ------
    category : FileCategory
        The category being summarised.
    count : int
        Number of files in this category.
    total_size : int
        Combined size of all files in this category, in bytes.
    files : list[AnalysisResult]
        The individual analysis results for this category.
    """

    category: FileCategory
    count: int
    total_size: int
    files: list[AnalysisResult]


def group_by_category(results: list[AnalysisResult]) -> list[CategorySummary]:
    """Group a list of AnalysisResults by FileCategory.

    Returns summaries sorted by total_size descending (largest first).
    Categories with no files are not included.
    """
    groups: dict[FileCategory, list[AnalysisResult]] = {}

    for result in results:
        groups.setdefault(result.category, []).append(result)

    summaries = []
    for category, files in groups.items():
        total_size = sum(f.metadata.size for f in files)
        summaries.append(
            CategorySummary(
                category=category,
                count=len(files),
                total_size=total_size,
                files=files,
            )
        )

    summaries.sort(key=lambda s: s.total_size, reverse=True)
    return summaries