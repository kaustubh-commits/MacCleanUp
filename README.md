# MacCleanUp

**A transparent filesystem audit and cleanup assistant for macOS.**

```bash
pip install mac-cleanup
maccleanup Downloads
```

```
Scan Summary
═══════════════════════════════════════════════
Scanned 127 files (4.5 GB)

Files by Category
────────────────────────────────────────────────
  IMAGE           12 files      2.1 GB
  PROJECT          2 files    980.4 MB
  DOCUMENT         1 files    420.5 MB
  ARCHIVE         22 files      4.7 GB
  INSTALLER        5 files      3.8 GB

Recommendations
────────────────────────────────────────────────
  ARCHIVE         22 files      4.7 GB
  INSTALLER        5 files      3.8 GB

Summary
═══════════════════════════════════════════════
Reclaimable space: 8.5 GB
Use --execute to apply these recommendations.
```

## Philosophy

Safety over automation. Transparency over magic. Readable over clever.

Dry-run by default. Never silently delete. Never make decisions for the user. MacCleanUp assists — it never takes control.

## Quick Start

```bash
# Install
pip install mac-cleanup

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