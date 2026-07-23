# MacCleanUp

**A transparent filesystem audit and cleanup assistant for macOS.**

Scan. Understand. Plan. Approve. Clean.

---

## Why This Exists

My Mac became cluttered over years of development. Downloads contained installers, duplicates, ZIP archives, screenshots, WhatsApp images, old study material, college PDFs, and project folders.

I could have manually sorted through thousands of files — or I could build a tool that audits the mess, explains what it found, and lets me decide what stays and what goes.

MacCleanUp is that tool.

It is **not** a file deletion utility. It is an assistant. It scans, analyzes, recommends, and organizes. The user remains in control at every step.

---

## Philosophy

| Principle | Meaning |
|---|---|
| **Safety over automation** | Dry-run by default. Never delete without asking. |
| **Transparency over magic** | Explain every recommendation. Never hide decisions. |
| **Readable over clever** | Code should be easy to read and modify. |
| **Simple over enterprise** | No unnecessary abstractions. No plugin systems. No DI. |

---

## Features (v1)

- **Filesystem scanning** — Scan any directory, with configurable exclusion patterns.
- **File classification** — Identify installers, archives, images, videos, documents, study material, projects, and more.
- **Duplicate detection** — Staged SHA-256 pipeline: group by size, filter by extension, hash only when necessary.
- **Action planning** — Build a structured plan of proposed actions (delete, move to review, ignore, report only).
- **Human-readable reports** — Storage summary, category breakdown, duplicate groups, estimated recovery.
- **Review folder** — Organize clutter into a single `Review/` folder for manual inspection in Finder.
- **Safety guarantees** — No execution without confirmation. Full audit log. Immutable scan data.

---

## Pipeline

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
DuplicateGroups  (SHA-256 verified — hashes stay here)
  │
  ▼
Planner
  │
  ▼
ActionPlan  (what should happen)
  │
  ▼
═══════════════════════════
        ScanResult
═══════════════════════════
  │                      │
  ▼                      ▼
Reporter              Executor
(display)             (perform approved actions)
                      │
                      ▼
                   Audit Log
```

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
│   ├── duplicate_detector.py SHA-256 staged duplicate detection.
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
| Review folder | Excluded from future scans |

Protected projects (never touched):
- EchoInsight
- DoodleDetective
- BinanceCLITradingBot

---

## Safety Guarantees

1. **Dry-run by default.** No filesystem changes without explicit opt-in.
2. **Explicit confirmation.** Every destructive action requires user approval.
3. **Audit log.** Every modification is timestamped and recorded.
4. **Immutable scan data.** Raw filesystem metadata never changes after capture.
5. **Executor is the only writer.** No other module has filesystem write access.

---

## Example Session

```
$ mac-cleanup scan ~/Downloads

Scanning... 1,247 files found.
Classifying... 12 categories detected.
Checking duplicates... 34 duplicate groups found (2.1 GB).
Planning...

═══════════════════════════════════════════
           MacCleanUp — Audit Report
═══════════════════════════════════════════

Storage Summary
  Total scanned:      1,247 files (8.4 GB)
  Duplicates:         34 groups (2.1 GB)
  Installers:         23 files (1.5 GB)
  Archives:           12 files (860 MB)

Category Breakdown
  Images:             312 files (1.8 GB)
  Videos:              18 files (2.4 GB)
  Documents:          240 files (890 MB)
  Installers:          23 files (1.5 GB)
  Archives:            12 files (860 MB)
  Projects:             8 files (320 MB)
  Other:              634 files (630 MB)

Duplicate Groups
  Screenshot 2024-03-12.png (×3):        12 MB
  Notes.pdf (×2):                         8 MB
  ...


═══════════════════════════════════════════
           Proposed Action Plan
═══════════════════════════════════════════

Delete (35 files):
  Office.pkg                         1.2 GB
  Discord.dmg                        340 MB
  node-v18.17.0.pkg                  85 MB
  ...

Move to Review (89 files):
  Old screenshots                     180 MB
  WhatsApp images                     420 MB
  JEE study material                  340 MB
  College reports                      90 MB

Report Only (18 files):
  Large videos                       2.4 GB

═══════════════════════════════════════════
Potential recovery:  4.3 GB

Proceed? [Y/n]
```

---

## Installation

> **Note:** Installation instructions will be added after the first release.

Currently: clone the repository and run `python cli/main.py`.

Future: Homebrew formula, pip install, standalone binary.

---

## Usage

> **Note:** Usage examples will be added after the first release.

```
mac-cleanup scan [--path <directory>]
mac-cleanup report [--format <text|json>]
```

---

## Future Roadmap

| Version | Focus |
|---|---|
| v1 | Scan, classify, detect duplicates, plan, report. Dry-run only. |
| v2 | Move to Trash, configuration file, JSON output, colourised terminal, progress indicators. |
| v3 | Undo support, HTML reports, scan history, Homebrew formula, CI/CD. |

---

## Contributing

This project is built as a learning exercise in software engineering.

**Before contributing, understand the philosophy:**
- No unnecessary abstractions.
- No enterprise architecture.
- No giant commits.
- Every change should make the code more readable, not clever.

Open an issue before opening a pull request. Let's discuss the design first.

---

## License

MIT

---

## Acknowledgements

Built for macOS because macOS deserves better filesystem tooling.