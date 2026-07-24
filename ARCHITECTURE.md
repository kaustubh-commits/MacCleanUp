# MacCleanUp — Architecture

**A transparent filesystem audit and cleanup assistant for macOS.**

---

## Philosophy

Safety over automation. Transparency over magic. Readable over clever. Simple over enterprise architecture.

Dry-run by default. Never silently modify files. Never make decisions for the user. The application assists — it never takes control.

---

## Layered Pipeline

```
User Input (CLI)
       │
       ▼
  Scanner           ─── Discovers files. Reads the filesystem.
       │
       ▼
  Classifier        ─── Determines file type (Image, Archive, etc.).
       │
       ▼
  Planner           ─── Applies policy rules. Recommends actions (Move, Leave).
       │
       ▼
  ReviewBuilder     ─── Pairs analyses with recommendations. Produces ReviewModel.
       │
       ├────► Renderer     ─── Pure function. Formats ReviewModel as terminal text.
       │
       └────► Executor     ─── Only module that modifies the filesystem.
```

Every arrow flows forward. No module reaches backward into another stage's responsibility.

---

## Module Map

```
MacCleanUp/
├── cli/
│   └── main.py              Entry point. CLI parsing, stdout, user confirmation, error boundary.
│
├── core/
│   ├── scanner.py            Filesystem traversal. Produces FileMetadata.
│   ├── classifier.py         File type identification. Pure function. Produces AnalysisResult.
│   ├── planner.py            Policy engine. Pure function. Produces Recommendation.
│   ├── review_builder.py     Aggregation. Pure function. Produces ReviewModel.
│   ├── renderer.py           Terminal output. Pure function. Returns str.
│   ├── executor.py           Filesystem operations. Only module with side effects.
│   └── pipeline.py           Application composition. Wires modules into workflows.
│
├── models/
│   ├── metadata.py           FileMetadata (immutable).
│   ├── category.py           FileCategory enum.
│   ├── analysis.py           AnalysisResult (immutable).
│   ├── action.py             SuggestedAction enum.
│   ├── recommendation.py     Recommendation (immutable).
│   ├── category_summary.py   CategorySummary, group_by_category().
│   ├── review.py             ReviewItem, ReviewModel (immutable).
│   ├── execution.py          ExecutionStatus, ExecutionResult, ExecutionReport.
│   ├── scan_error.py         ScanError model.
│   └── scanner_result.py     ScannerResult model.
│
├── utils/
│   └── formatting.py         Pure formatting functions (format_bytes, format_percentage).
│
├── tests/                    Mirrors module structure. One test file per module.
│
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md
└── LICENSE
```

---

## Module Contracts

### Scanner
- **Input:** A directory path.
- **Output:** `ScannerResult` containing `FileMetadata` entries.
- **Side effects:** Reads the filesystem. None beyond that.
- **Never:** Classifies, plans, recommends, or modifies files.

### Classifier
- **Input:** `FileMetadata`.
- **Output:** `AnalysisResult` (category + confidence score).
- **Side effects:** None. Pure function.
- **Never:** Reads the filesystem. Plans actions. Imports from Planner.

### Planner
- **Input:** `AnalysisResult`.
- **Output:** `Recommendation` (suggested action + reason).
- **Side effects:** None. Pure function.
- **Never:** Classifies files. Reads the filesystem. Decides destinations.

### ReviewBuilder
- **Input:** List of `AnalysisResult` + `Recommendation` pairs.
- **Output:** `ReviewModel` (immutable snapshot).
- **Side effects:** None. Pure function.
- **Never:** Reads the filesystem. Makes policy decisions.

### Renderer
- **Input:** `ReviewModel`.
- **Output:** Formatted terminal string.
- **Side effects:** None. Pure function.
- **Never:** Computes totals, calls the Executor, or prints.

### Executor
- **Input:** List of `ReviewItem` + destination path.
- **Output:** `ExecutionReport`.
- **Side effects:** Only module permitted to modify the filesystem.
- **Never:** Plans, classifies, prints, or prompts the user.

### Pipeline
- **Input:** CLI arguments.
- **Output:** `ReviewModel` or `ExecutionReport`.
- **Side effects:** None. Composes pure modules.
- **Never:** Prints, prompts, or modifies files.

### CLI
- **Input:** Command-line arguments.
- **Output:** Printed terminal text. Exit codes.
- **Side effects:** All I/O (stdout, stderr, stdin).
- **Never:** Classifies, plans, calculates, or modifies files.

---

## Design Decisions

### Why pure functions?
Every stage (except Scanner and Executor) is a pure function. This makes each module independently testable, deterministic, and composable. The pipeline is simply a sequence of function calls.

### Why no PipelineResult wrapper?
The two-function API (`analyze_directory` + `execute_review`) eliminates the need for a return-type wrapper. The CLI composes these naturally without an intermediate object.

### Why two render modes?
Default (concise) is a summary by category — it answers "what kinds of files are taking space?" The `--verbose` mode lists every file with its recommendation. This follows the common CLI pattern: concise by default, detailed on request.

### Why flat destination layout?
Files are moved to `destination / filename`. This is simple to reason about and avoids brittle path-computation logic. Directory structure preservation can be added later if needed.

### Why no default exclusions?
Exclusion policy is intentionally kept out of the pipeline. The Scanner accepts an `exclude_names` parameter, but v1 does not hardcode defaults. This keeps policy decisions explicit rather than hidden.

---

## What Belongs Where

| Concern | Location |
|---------|----------|
| Filesystem discovery | `scanner.py` |
| File type classification | `classifier.py` |
| Policy rules | `planner.py` |
| Data aggregation | `review_builder.py` |
| Terminal formatting | `renderer.py` |
| File move/delete | `executor.py` |
| Module orchestration | `pipeline.py` |
| Argument parsing, printing, errors | `cli/main.py` |
| Number formatting | `utils/formatting.py` |

---

## Known Limitations

### Warnings are orphaned
`ScannerResult.warnings` records symlink skips and permission errors, but these are not propagated through `ReviewModel` or the Renderer. A future version should thread warnings to the user.

### CategorySummary is mutable
`ReviewModel` is frozen, but the `CategorySummary` objects it wraps are not. This does not affect the Renderer but violates the principle of full immutability.

### No rollback
The Executor performs one-way operations. Failed moves cannot be undone automatically. The `ExecutionReport` documents what happened; manual intervention may be needed for partial failures.

---

## Safety Guarantees

1. **Preview by default.** No filesystem changes without `--execute`.
2. **Explicit confirmation.** Every destructive action requires `y/N` approval.
3. **Immutable data.** `ReviewModel` is a frozen snapshot — the original scan data is never modified.
4. **Executor is the only writer.** No other module has filesystem write access.
5. **Error capture.** All per-file errors are captured in `ExecutionResult` objects. Exceptions never bubble up for filesystem errors.

---

## Testing Philosophy

- **Pure functions** (Classifier, Planner, Renderer, formatting): Test with assertions on return values. No mocking.
- **Scanner**: Test with `tmp_path` and real files. No mocking.
- **Executor**: Mock `shutil.move` for unit tests. Use `tmp_path` for integration tests.
- **Pipeline**: Integration tests with real modules. Mock only the Executor.
- **CLI**: Inject `argv` instead of `sys.argv`. Test exit codes, not stdout strings.

---

## Why Not Enterprise Architecture?

This project intentionally avoids:
- Plugin systems
- Middleware pipelines
- Dependency injection frameworks
- Abstract base classes without proven need
- Unnecessary design patterns

Abstractions are introduced only after they solve a genuine problem. Premature abstraction adds complexity without value.