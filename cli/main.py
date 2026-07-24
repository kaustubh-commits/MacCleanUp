"""
CLI entry point for MacCleanUp.

Owns:
- argparse
- stdout / stderr
- user confirmation
- exit codes
- error boundary

Owns nothing related to domain logic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.pipeline import analyze_directory, execute_review
from core.renderer import render

EXIT_SUCCESS = 0
EXIT_CANCELLED = 1
EXIT_INVALID_ARGS = 2
EXIT_ERROR = 3


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="maccleanup",
        description="A transparent filesystem audit and cleanup assistant for macOS.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Directory to analyze and clean up.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the recommended actions (move files).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run execution logic without modifying the filesystem.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path.home() / "MacCleanUp" / "Archive",
        help="Destination directory for moved files (default: ~/MacCleanUp/Archive).",
    )
    return parser.parse_args(argv)


def _print_execution_summary(report) -> None:
    """Print a brief summary of the execution report."""
    results = report.results
    succeeded = sum(1 for r in results if r.status.name == "SUCCESS")
    skipped = sum(1 for r in results if r.status.name == "SKIPPED")
    failed = sum(1 for r in results if r.status.name == "FAILED")

    print()
    print("═" * 47)
    print("Execution Complete")
    print("═" * 47)
    print(f"  SUCCESS:  {succeeded}")
    print(f"  SKIPPED:  {skipped}")
    print(f"  FAILED:   {failed}")
    if failed > 0:
        print()
        for r in results:
            if r.status.name == "FAILED":
                print(f"  {r.item.analysis.metadata.name}: {r.message}")


def main(argv: list[str] | None = None) -> None:
    """Main entry point for MacCleanUp CLI.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments. ``None`` uses ``sys.argv[1:]``.
    """
    try:
        args = _parse_args(argv)
        root = args.path.resolve()

        if not root.is_dir():
            print(f"Error: {root} is not a directory or does not exist.", file=sys.stderr)
            sys.exit(EXIT_INVALID_ARGS)

        # --- Analysis phase ---
        review = analyze_directory(root)

        # --- Render and display ---
        output = render(review)
        print(output)

        # --- Execution phase (optional) ---
        if args.execute:
            response = input("\nProceed with moving files? [y/N] ").strip().lower()
            if response != "y":
                print("Cancelled.")
                sys.exit(EXIT_CANCELLED)

            report = execute_review(
                list(review.items),
                destination=args.destination,
                dry_run=args.dry_run,
            )
            _print_execution_summary(report)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_INVALID_ARGS)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)