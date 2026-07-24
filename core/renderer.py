"""
render — pure function transforming ReviewModel into a formatted terminal string.

Single responsibility: layout. No calculations, no filesystem, no policy.

Two presentation modes:
- Default (verbose=False): concise summary, fits on one screen.
- Verbose (verbose=True): full per-file listing with reasons.
"""

from __future__ import annotations

from collections import defaultdict

from models.action import SuggestedAction
from models.review import ReviewModel, ReviewItem

from utils.formatting import format_bytes


_HEADER_SEP = "═" * 47
_SECTION_SEP = "─" * 47


def render(review: ReviewModel, verbose: bool = False, use_color: bool = False) -> str:
    """Render a completed review as a human-readable string.

    Parameters
    ----------
    review : ReviewModel
        The immutable review snapshot to display.
    verbose : bool
        If True, show a detailed per-file listing. Default is a concise summary.
    use_color : bool
        If True, wrap section headers with ANSI bold codes.

    Returns
    -------
    str
        Formatted terminal output. No trailing newline.
    """
    if verbose:
        sections = [
            _render_header(review, use_color),
            _render_categories(review, use_color),
            _render_recommendations_verbose(review, use_color),
            _render_footer(review, use_color),
        ]
    else:
        sections = [
            _render_header(review, use_color),
            _render_categories(review, use_color),
            _render_recommendations_summary(review, use_color),
            _render_footer(review, use_color),
        ]
    return "\n\n".join(s for s in sections if s)


# =========================================================================
# Shared helpers
# =========================================================================


def _bold(text: str, use_color: bool) -> str:
    if use_color:
        return f"\033[1m{text}\033[0m"
    return text


def _cyan(text: str, use_color: bool) -> str:
    if use_color:
        return f"\033[96m{text}\033[0m"
    return text


def _green(text: str, use_color: bool) -> str:
    if use_color:
        return f"\033[92m{text}\033[0m"
    return text


def _group_recommendations_by_category(
    items: tuple[ReviewItem, ...],
) -> list[tuple[str, list[ReviewItem], int]]:
    """Group actionable items (MOVE) by category name, sorted by total size descending.

    Returns list of (category_name, items, total_size).
    """
    groups: dict[str, list[ReviewItem]] = defaultdict(list)
    for item in items:
        if item.recommendation.action is SuggestedAction.MOVE:
            groups[item.analysis.category.name].append(item)

    result: list[tuple[str, list[ReviewItem], int]] = []
    for cat_name, cat_items in groups.items():
        total = sum(i.analysis.metadata.size for i in cat_items)
        result.append((cat_name, cat_items, total))

    result.sort(key=lambda x: x[2], reverse=True)
    return result


# =========================================================================
# Default (concise) section builders
# =========================================================================


def _render_header(review: ReviewModel, use_color: bool) -> str:
    lines = [
        _cyan("Scan Summary", use_color),
        _HEADER_SEP,
        f"Scanned {_bold(str(review.total_files), use_color)} files "
        f"({_bold(format_bytes(review.total_size), use_color)})",
    ]
    return "\n".join(lines)


def _render_categories(review: ReviewModel, use_color: bool) -> str:
    if not review.categories:
        return ""

    lines = [
        _cyan("Files by Category", use_color),
        _SECTION_SEP,
    ]

    for summary in review.categories:
        lines.append(
            f"  {summary.category.name:<12} {str(summary.count):>5} files  "
            f"{format_bytes(summary.total_size):>10}"
        )

    return "\n".join(lines)


def _render_recommendations_summary(review: ReviewModel, use_color: bool) -> str:
    """Concise recommendations section — grouped by category, total only."""
    groups = _group_recommendations_by_category(review.items)

    if not groups:
        return ""

    lines = [
        _cyan("Recommendations", use_color),
        _SECTION_SEP,
    ]

    for cat_name, items, total_size in groups:
        lines.append(
            f"  {cat_name:<12} {str(len(items)):>5} files  "
            f"{format_bytes(total_size):>10}"
        )

    return "\n".join(lines)


def _render_footer(review: ReviewModel, use_color: bool) -> str:
    reclaimable = review.reclaimable_size
    color_fn = _green if reclaimable == 0 else _bold
    lines = [
        _cyan("Summary", use_color),
        _HEADER_SEP,
        f"Reclaimable space: {color_fn(format_bytes(reclaimable), use_color)}",
    ]
    if reclaimable > 0:
        lines.append("Use --execute to apply these recommendations.")
    return "\n".join(lines)


# =========================================================================
# Verbose (detailed) section builders
# =========================================================================


def _render_recommendations_verbose(review: ReviewModel, use_color: bool) -> str:
    """Detailed recommendations section — every file listed with reason."""
    items = review.items

    if not items:
        return ""

    # Group by action
    move_items = [i for i in items if i.recommendation.action is SuggestedAction.MOVE]
    delete_items = [i for i in items if i.recommendation.action is SuggestedAction.DELETE]
    none_items = [i for i in items if i.recommendation.action is None]

    action_groups: list[tuple[str, list[ReviewItem]]] = []
    if move_items:
        action_groups.append(("MOVE", move_items))
    if delete_items:
        action_groups.append(("DELETE", delete_items))
    if none_items:
        action_groups.append(("NO ACTION", none_items))

    if not action_groups:
        return ""

    lines = [
        _cyan("Recommendations", use_color),
        _HEADER_SEP,
    ]

    for action_name, group in action_groups:
        group.sort(key=lambda i: i.analysis.metadata.size, reverse=True)
        total_group = sum(i.analysis.metadata.size for i in group)
        lines.append(
            f"\n  {action_name} ({len(group)} files, {format_bytes(total_group)})"
        )
        for item in group:
            size_str = format_bytes(item.analysis.metadata.size)
            name = item.analysis.metadata.name
            reason = item.recommendation.reason
            lines.append(f"    {size_str:>10}  {name}")
            if reason:
                lines.append(f"                {reason}")

    return "\n".join(lines)