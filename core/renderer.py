"""
render — pure function transforming ReviewModel into a formatted terminal string.

Single responsibility: layout. No calculations, no filesystem, no policy.
"""

from __future__ import annotations

from models.action import SuggestedAction
from models.category import FileCategory
from models.review import ReviewModel

from utils.formatting import format_bytes, format_percentage


_SEPARATOR = "═" * 47


def render(review: ReviewModel, use_color: bool = False) -> str:
    """Render a completed review as a human-readable string.

    Parameters
    ----------
    review : ReviewModel
        The immutable review snapshot to display.
    use_color : bool
        If True, wrap section headers with ANSI bold codes.

    Returns
    -------
    str
        Formatted terminal output. No trailing newline.
    """
    sections = [
        _render_header(review, use_color),
        _render_categories(review, use_color),
        _render_recommendations(review, use_color),
        _render_footer(review, use_color),
    ]
    return "\n\n".join(s for s in sections if s)


# =========================================================================
# Private section builders
# =========================================================================


def _bold(text: str, use_color: bool) -> str:
    if use_color:
        return f"\033[1m{text}\033[0m"
    return text


def _render_header(review: ReviewModel, use_color: bool) -> str:
    lines = [
        _bold("Scan Summary", use_color),
        _SEPARATOR,
        f"Scanned {review.total_files} files ({format_bytes(review.total_size)})",
    ]
    return "\n".join(lines)


def _render_categories(review: ReviewModel, use_color: bool) -> str:
    if not review.categories:
        return ""

    lines = [
        _bold("Files by Category", use_color),
        _SEPARATOR,
    ]

    total = review.total_size
    for summary in review.categories:
        pct = format_percentage(summary.total_size, total) if total > 0 else "0.0%"
        lines.append(
            f"  {summary.category.name:<12} {summary.count:>5} files  "
            f"{format_bytes(summary.total_size):>10}  {pct}"
        )

    return "\n".join(lines)


def _render_recommendations(review: ReviewModel, use_color: bool) -> str:
    items = review.items

    if not items:
        return ""

    # Group by action
    move_items = [i for i in items if i.recommendation.action is SuggestedAction.MOVE]
    delete_items = [i for i in items if i.recommendation.action is SuggestedAction.DELETE]
    leave_items = [i for i in items if i.recommendation.action is SuggestedAction.LEAVE]
    none_items = [i for i in items if i.recommendation.action is None]

    action_groups: list[tuple[str, list]] = []
    if move_items:
        action_groups.append(("MOVE", move_items))
    if delete_items:
        action_groups.append(("DELETE", delete_items))
    if leave_items:
        action_groups.append(("LEAVE", leave_items))
    if none_items:
        action_groups.append(("NO ACTION", none_items))

    if not action_groups:
        return ""

    lines = [
        _bold("Recommendations", use_color),
        _SEPARATOR,
    ]

    for action_name, group in action_groups:
        # Sort by size descending
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


def _render_footer(review: ReviewModel, use_color: bool) -> str:
    lines = [
        _bold("Summary", use_color),
        _SEPARATOR,
        f"Reclaimable space: {format_bytes(review.reclaimable_size)}",
    ]
    return "\n".join(lines)