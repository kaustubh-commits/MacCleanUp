# MacCleanUp — Architecture

**A transparent filesystem audit and cleanup assistant for macOS.**

---

## Philosophy

Safety over automation.  
Transparency over magic.  
Readable over clever.  
Simple over enterprise architecture.

Dry-run by default. Never silently delete. Never make decisions for the user.  
The application assists. It never takes control.

---

## High-Level Pipeline

```
User
  │
  ▼
Scanner
  │
  ▼
FileMetadata  (immutable — raw filesystem data)
  │
  ▼
Classifier
  │
  ▼
AnalysisResult  (derived — category, confidence, recommendation)
  │
  ▼
DuplicateDetector
  │
  ▼
DuplicateGroups  (SHA-256 verified groups — hashes stay here)
  │
  ▼
Planner
  │
  ▼
ActionPlan  (what should happen)
  │
  ▼
══════════════════════════════
        ScanResult
══════════════════════════════
  │                      │
  ▼                      ▼
Reporter              Executor
(display)             (perform approved actions)
                      │
                      ▼
                   Audit Log
```

`ScanResult` is the final product of the pipeline. Both the Reporter and the Executor read from it — the Reporter to display, the Executor to execute the approved `ActionPlan`.

---

## Project Structure

```
MacCleanUp/
├── cli/
│   └── main.py              Entry point. CLI parsing. Workflow invocation.
│
├── core/
│   ├── scanner.py            Filesystem traversal. Produces FileMetadata.
│   ├── classifier.py         File type identification. Produces AnalysisResult.
│   ├── duplicate_detector.py SHA-256 staged duplicate detection. Produces DuplicateGroups.
│   ├── planner.py            Builds ActionPlan from analysis + policy.
│   └── executor.py           Only module that modifies the filesystem.
│
├── models/
│   ├── metadata.py           FileMetadata (immutable).
│   ├── analysis.py           AnalysisResult, DuplicateGroup.
│   ├── actions.py            ActionPlan, CleanupAction.
│   └── scan_result.py        ScanResult — final pipeline output.
│
├── report/
│   └── reporter.py           Human-readable output generation.
│
├── config/
│   └── policy.py             Cleanup rules, exclusion patterns, thresholds.
│
├── utils/
│   └── helpers.py            Small reusable functions (formatting, display).
│
├── tests/                    Mirrors module structure.
├── pyproject.toml
├── README.md
├── LICENSE
└── ARCHITECTURE.md
```

---

## Module Responsibilities

### Scanner
- Only responsibility: discover files on the filesystem.
- Produces immutable `FileMetadata` objects — no derived fields, no hashes.
- Accepts a directory path and exclusion patterns (from policy).
- Does **not** classify, hash, delete, or print.

### FileMetadata
- Pure filesystem facts: name, extension, path, size, created_at, modified_at.
- **Immutable** — once created, never changes.
- Contains no analysis, no category, no hash.

### Classifier
- Receives `FileMetadata`, determines what kind of file it is.
- Produces `AnalysisResult` with: category, confidence, recommendation, reason.
- Categories include: Installer, Archive, Image, Video, Study Material, Document, Project, Temporary File, etc.
- Does **not** compute hashes, does **not** modify files.

### DuplicateDetector
- Only module that computes SHA-256 hashes.
- Staged pipeline:
  1. Group by file size.
  2. Filter by extension.
  3. Read contents → compute SHA-256.
  4. Create `DuplicateGroup` objects.
- Hashes exist **only** inside this module — they are a duplicate-detection concern, not a property of every file.

### Planner
- Receives: `AnalysisResult`s, `DuplicateGroup`s, `Policy`.
- Produces an `ActionPlan` — a collection of proposed actions.
- Decides **what should happen**, never executes.
- Actions include: Delete, Move to Review, Ignore, Report Only.

### ActionPlan
- A structured collection of proposed `CleanupAction` items.
- Presented to the user for review before any execution.
- Contains: proposed deletes, moves, ignores, and their total estimated recovery.

### ScanResult
- The final output of the analysis pipeline.
- Contains: scanned `FileMetadata`s, duplicate groups, `ActionPlan`, statistics, warnings, potential storage recovery.
- Both the Reporter and the Executor consume this object.

### Reporter
- Generates human-readable output from `ScanResult`.
- Shows: storage summary, category breakdown, duplicate groups, recommendations, estimated recovery.
- Does **not** modify anything.

### Executor
- The **only** module permitted to modify the filesystem.
- Receives an approved `ActionPlan`.
- Operations: Move, Move to Trash, Delete.
- Every destructive action requires explicit user confirmation.
- Logs every modification to the audit log.

### Policy
- Central location for cleanup rules and application behaviour.
- Controls: what to do with each category, exclusion patterns, file size thresholds, safety modes.
- Changing policy never requires changing scanner, classifier, or planner logic.

### Helpers
- Small, reusable functions: human-readable file sizes, date formatting, terminal colours, prompt helpers.
- If this file grows too large, it is split into focused modules — not before.

---

## Cleanup Policy (Version 1)

| Category | Action |
|---|---|
| Duplicate (SHA-256 verified) | Delete after confirmation |
| Installer (.dmg, .pkg) | Delete after confirmation |
| ZIP archive | Recommend deletion after extraction |
| Large video | Report only |
| Project folder | Move to Review |
| `.git` directory | Never touch |
| `.venv` directory | Report separately |
| Hidden / system file | Ignore |
| WhatsApp Image | Move to Review |
| Screenshot | Move to Review |
| JEE / Study Material | Move to Review |
| College PDF / Report | Move to Review |
| EchoInsight | Never touch |
| DoodleDetective | Never touch |
| BinanceCLITradingBot | Never touch |
| Review folder | Excluded from future scans |

---

## The Review Folder

Instead of forcing deletion, MacCleanUp can organize clutter into a `Review/` folder on the Desktop:

```
Desktop/
└── Review/
    ├── Screenshots/
    ├── WhatsApp Images/
    ├── Study Material/
    └── Misc/
```

This gives the user a single place to manually review organized files inside Finder.

The Review folder is excluded from future scans to prevent double-counting.

---

## Safety Guarantees

1. **Dry-run by default.** No filesystem changes without explicit opt-in.
2. **Explicit confirmation.** Every destructive action requires user approval.
3. **Audit log.** Every modification is timestamped and recorded.
4. **Immutable scan data.** Raw filesystem metadata never changes after capture.
5. **Executor is the only writer.** No other module has filesystem write access.

---

## Audit Log

Format: JSON Lines (`audit.jsonl`), one JSON object per line.

```json
{"timestamp": "2026-07-23T10:00:00", "action": "delete", "path": "/Users/kaustubh/Downloads/Office.pkg", "size": 1500000000}
```

This enables transparency, rollback planning, and future undo support.

---

## Future Roadmap

| Version | Focus |
|---|---|
| v1 | Scan, classify, detect duplicates, plan, report. Dry-run only. |
| v2 | Move to Trash, configuration file, JSON output, colourised terminal, progress indicators. |
| v3 | Undo support, HTML reports, scan history, Homebrew formula, CI/CD. |

---

## Git Strategy

- One module per commit.
- Small, focused commits with clear messages.
- No giant commits.
- Suggested progression: `FileMetadata` → `Scanner` → Scanner tests → `Classifier` → `DuplicateDetector` → `Planner` → ...

---

## Why No Enterprise Architecture?

This project intentionally avoids:

- Plugin systems
- Middleware pipelines
- Dependency injection
- Abstract base classes without a proven need
- Unnecessary design patterns

Abstractions are introduced only after they solve a genuine problem. Premature abstraction adds complexity without value, and this project values readability and approachability above theoretical purity.