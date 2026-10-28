# MacCleanUp

**A transparent filesystem audit and cleanup assistant for macOS.**

```bash
git clone https://github.com/kaustubh-commits/MacCleanUp.git
cd MacCleanUp
pip install .
maccleanup Downloads
```

```
Scan Summary
═══════════════════════════════════════════════
Scanned 26 files (6.5 GB)

Files by Category
───────────────────────────────────────────────
  INSTALLER        3 files      3.5 GB
  ARCHIVE          3 files      2.2 GB
  VIDEO            1 files    705.7 MB
  AUDIO            1 files     45.8 MB
  IMAGE           14 files     34.7 MB
  PDF              1 files      2.3 MB
  DOCUMENT         2 files    181.6 KB
  PROJECT          1 files      3.9 KB

Recommendations
───────────────────────────────────────────────
  INSTALLER        3 files      3.5 GB
  ARCHIVE          3 files      2.2 GB

Summary
═══════════════════════════════════════════════
Reclaimable space: 5.7 GB
Use --execute to apply these recommendations.
```

## Philosophy

Safety over automation. Transparency over magic. Readable over clever.

Dry-run by default. Never silently delete. Never make decisions for the user. MacCleanUp assists — it never takes control.

## Installation

MacCleanUp is not published on PyPI. (The `mac-cleanup` package on PyPI is an unrelated project.) Install it from source; Python 3.11+ is required:

```bash
git clone https://github.com/kaustubh-commits/MacCleanUp.git
cd MacCleanUp
python3 -m venv .venv && source .venv/bin/activate
pip install .
```

To work on the code, install it in editable mode and run the test suite:

```bash
pip install -e . pytest
python -m pytest
```

## Quick Start

```bash
# Preview what MacCleanUp would recommend
maccleanup ~/Downloads

# See every file with its recommendation
maccleanup ~/Downloads --verbose

# Actually move files (after reviewing)
maccleanup ~/Downloads --execute
```

## Command Reference

| Flag | Description |
|------|-------------|
| `path` | Directory to analyze (`~/Downloads`, `Downloads`, `.`, or absolute path) |
| `--execute` | Perform the recommended actions (move files) |
| `--dry-run` | Run execution logic without modifying the filesystem |
| `--verbose` / `-v` | Show detailed per-file listing instead of a summary |
| `--destination` | Destination for moved files (default: `~/MacCleanUp/Archive`) |

### Examples

```bash
# Beginner-friendly — accepts just the folder name
maccleanup Downloads

# Explore what's taking space in your Desktop
maccleanup ~/Desktop --verbose

# Preview execution without touching anything
maccleanup ~/Downloads --dry-run --execute

# Execute for real, send files to a custom archive
maccleanup ~/Downloads --execute --destination ~/MyArchive
```

## How It Works

```
Filesystem → Scanner → Classifier → Planner → ReviewBuilder → Renderer
                                                               → Executor
```

Each stage is independently testable, purely functional (except the Executor), and has exactly one responsibility.

| Module | Responsibility |
|--------|---------------|
| **Scanner** | Discovers files and directories |
| **Classifier** | Determines file type (Image, Archive, Installer, etc.) |
| **Planner** | Applies policy rules to recommend actions |
| **ReviewBuilder** | Organizes analyses and recommendations into a snapshot |
| **Renderer** | Formats the snapshot as human-readable output |
| **Executor** | Performs approved filesystem operations only |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed breakdown of the layered design, module contracts, and design decisions.

## License

MIT