# Engineering Journal

## Commit 1 — Initialize MacCleanUp project architecture

**Date:** 2026-07-23

**Summary:** Project scaffold with directory structure, package init files, `pyproject.toml`, `.gitignore`, `LICENSE` (MIT), `ARCHITECTURE.md`, and `README.md`. No implementation yet.

---

## Commit 2 — FileMetadata

**Date:** 2026-07-23

**Summary:** Implemented the `FileMetadata` immutable domain model — the foundational data type of the application.

### Why we designed it this way

FileMetadata needed to be the single source of truth for raw filesystem facts. Every downstream module (Scanner, Classifier, DuplicateDetector, Planner) depends on it. Making it immutable ensures that once a file is discovered, its metadata cannot be accidentally mutated by any later stage. This eliminates an entire class of bugs.

### Key design decisions

1. **Four fields only.** `path`, `size`, `created_time`, `modified_time`. Everything else (`name`, `extension`, `parent`) is derived from `path`. This prevents inconsistency between stored and derived values.

2. **Directories are included.** Added `is_directory: bool = False`. The Scanner encounters both files and directories during traversal. Filtering them out at the Scanner level would make the Scanner's implementation more awkward. Instead, the model faithfully represents filesystem entries, and downstream consumers (Classifier, DuplicateDetector) choose to skip directories.

3. **Minimal validation.** Only `path` must be absolute and `size` must be non-negative. Timestamps are accepted exactly as the OS reports them — even if `modified_time < created_time` or timestamps are in the future. Filesystems are messy (Time Machine, git, SMB, exFAT), and rejecting files with "impossible" timestamps would make the tool unreliable.

4. **No `__str__` override.** The default `__repr__` from `@dataclass(frozen=True)` is sufficient until we know exactly what display format we need.

5. **Extension normalization.** `extension` returns `path.suffix.lower()`. This ensures "Photo.JPG" and "photo.jpg" have the same extension, which matters for classification and duplicate detection.

### What we rejected

- **Storing `name` and `extension` as fields.** They are fully derivable from `path`. Storing them would create a risk of inconsistency.
- **Aggressive timestamp validation.** Rejected because the real filesystem doesn't respect "logical" timestamp ordering.
- **Separate model for directories.** Rejected because it would complicate the Scanner. A single `is_directory` flag is simpler.

### Engineering lesson learned

The domain model is where simplicity matters most. A model that is too complex propagates that complexity to every module that uses it. A model that is too simple can be extended later. The asymmetry between these two outcomes means we should err on the side of simplicity for foundational models.

The most time-consuming part of this commit was not the implementation (~40 lines) but the boundary decision: what does NOT belong in FileMetadata. Every field we keep out is a field we never have to maintain.

---

## Commit 3 — Scanner

**Date:** 2026-07-23

**Summary:** Implemented the Scanner — filesystem traversal and metadata collection using `os.scandir()`. Produces `ScannerResult` containing `FileMetadata` objects and `ScanError` warnings.

### Why we designed it this way

The Scanner is the first module that touches the real filesystem. Every correctness guarantee downstream depends on the Scanner faithfully representing what's on disk. This made us prioritise:

- **Error resilience.** One permission-denied directory should not abort a scan of 50,000 files. The Scanner continues, records a `ScanError`, and proceeds.
- **Separation of concerns.** The Scanner knows nothing about classification, duplicate detection, or policy. It receives exclusion names and uses them blindly.
- **Honest representation.** Directories are included in the output. Downstream consumers choose to ignore them; the Scanner doesn't filter them out.

### Key design decisions

1. **`os.scandir()` over `os.walk()` or `Path.rglob()`.** scandir exposes `DirEntry` objects that carry `entry.stat()` with zero extra syscalls (the kernel returns stat data during the directory read). More importantly, it gives us per-entry error handling — a single unreadable file doesn't crash the walk.

2. **All symlinks are skipped with a warning.** Following symlinks to files is harmless, but following symlinks to directories creates cycle risk and can pull the scanner outside the intended subtree. The v1 policy is simple and absolute: every symlink is recorded as a `ScanError`. If users report a need for following symlinks, we add it in v2.

3. **Name-based exclusions, not path-based.** Passing `{".git", ".venv", "__MACOSX"}` is simpler and covers real-world cases. A `.git` anywhere in the tree is skipped — you don't need to know its full path. Project-specific protections (EchoInsight, etc.) are handled by Policy at the Planner stage.

4. **`ScannerResult` is NOT `ScanResult`.** The architecture intentionally separates them. `ScannerResult` represents only filesystem discovery. The application's final `ScanResult` lives later in the pipeline, assembled after classification, duplicate detection, and planning.

5. **`ScanError` is a separate model.** Not embedded in `ScannerResult`. A per-error domain object (`path`, `message`) can be reused by other modules that need to record non-fatal problems.

### What we rejected

- **Generator-based API.** Returning a generator would delay error collection and complicate the `scan()` contract. A `ScannerResult` with `list[FileMetadata]` is simpler and fast enough for personal use.
- **Async/threaded scanning.** Single-threaded `os.scandir()` completes a 50,000-file scan in under 2 seconds on modern Macs. Threading adds race conditions and complexity for zero benefit.
- **Glob pattern exclusions.** Name-based exact matching covers all real cases we could identify. Pattern matching can be layered on later if needed.

### Engineering lesson learned

The hardest part of the Scanner wasn't the traversal logic — it was deciding what the Scanner should NOT do. Every time we considered adding a feature (hash during scan? follow symlinks? resolve unicode? validate timestamps?), the question "does this belong in discovery?" kept us honest.

The symlink decision was the most debated. The extreme position ("follow nothing") creates the simplest, most predictable behaviour. Users who need symlink following can contribute it as a clearly scoped v2 feature.

### Lessons Learned

- **What surprised us:** `entry.is_symlink()` on macOS returns `True` for dangling symlinks instead of raising `OSError`. The `except OSError` path we wrote for dangling symlinks was never triggered. This is macOS-specific behaviour — Linux raises `OSError` for `is_symlink()` on dangling links. We fixed the warning path to handle both cases.
- **What became simpler than expected:** Permission error handling. `os.scandir()` raises `PermissionError` at the directory level, not per-file. A single `try/except PermissionError` around `os.scandir(path)` catches the common case (a directory you can't enter). Per-file permission errors are handled by `entry.stat()` failing.
- **What assumption turned out to be wrong:** We initially assumed the Scanner should not record symlinks as warnings — just skip them silently. But during implementation, we realised that "silent skipping" violates the philosophy of transparency. The user should know if their scan excluded entries. This matches the project's core principle: "The application assists. It never hides decisions."

---

## Commit 4 — Shared Data Models

**Date:** 2026-07-23

**Summary:** Defined the shared vocabulary of the application — FileCategory, SuggestedAction, AnalysisResult, Recommendation, and CategorySummary — as standalone dataclasses and enums before implementing the Classifier or Planner.

### Why we designed it this way

API-first engineering. The Classifier, Planner, UI, and Executor all depend on these types. Defining them upfront prevents two engineers from producing incompatible objects and makes the module interfaces explicit before implementation begins.

### Key design decisions

1. **FileCategory is an enum, not a string.** String-based categories introduce typos, inconsistent casing, and non-exhaustive matching. An enum gives compiler-checked exhaustiveness and a single source of truth.

2. **SuggestedAction is its own file, separate from Recommendation.** Actions appear in recommendations, audit entries, CleanupAction, and CLI prompts. Keeping them separate prevents circular imports and keeps the domain language clean.

3. **Recommendation.action is Optional.** The Planner may decline to make a recommendation (e.g., for UNKNOWN files with low confidence). `None` is explicit: "I don't know." No UNCERTAIN enum member needed — the absence of a value is the signal.

4. **CategorySummary is a pure data transformation.** The UI should render data, not compute it. The `group_by_category()` function is a pure function: input analysis results, output sorted summaries. Testable without rendering.

5. **AnalysisResult is frozen.** Once a file is classified, that classification should not change accidentally. Frozen dataclass enforces this at runtime.

### What we rejected

- **SuggestedAction.UNCERTAIN.** The user explicitly rejected this: "absence of value" via `Optional[SuggestedAction]` is clearer than an enum member meaning "uncertain."
- **Storing analysis or recommendation inside FileMetadata.** FileMetadata remains purely objective filesystem facts.
- **Splitting CLI prematurely.** The UI module is deferred until it naturally grows large enough to justify the split.

### Dependency graph enforced

```
category.py           → nothing
action.py             → nothing
analysis.py           → metadata.py, category.py
recommendation.py     → action.py
category_summary.py   → category.py, analysis.py
```

Nothing in `models/` imports from `core/` or `cli/`.

### Engineering lesson learned

Defining the vocabulary before implementing behaviour is uncomfortable — it feels like you're not making progress. But it surfaces design disagreements early (at the type level) rather than during integration (at the runtime level). The discussion about `SuggestedAction.UNCERTAIN` vs `Optional[SuggestedAction]` was resolved in five minutes because the model was concrete enough to debate.

---

## Commit 5 — Classifier

**Date:** 2026-07-24

**Summary:** Implemented the Classifier — a pure function mapping `FileMetadata → AnalysisResult`. The first piece of domain intelligence: converting objective filesystem facts into semantic understanding.

### Key design decisions

1. **Pure function, not a class.** No state, no configuration object. `classify(metadata) -> AnalysisResult`.
2. **Extension-based mapping via dict.** A private `_EXTENSION_MAP` dict maps `.jpg → IMAGE`, `.zip → ARCHIVE`, etc. No if/elif chain.
3. **Encapsulated extension lookup.** Uses `metadata.extension` rather than `metadata.path.suffix.lower()`, keeping normalization logic in one place.
4. **Directories are UNKNOWN.** Early return for `is_directory` — prevents directory names with extensions (e.g., `images.tar`) from being classified.
5. **Confidence is binary for v1:** `1.0` for known extensions, `0.0` for unknown.

### Engineering note

The hardest decision was what NOT to classify. `.gitignore` has an extension but it's not meaningful — the Classifier correctly returns UNKNOWN. `README` has no extension — also UNKNOWN. The classifier doesn't try to be smarter than its extension map.

---

## Commit 6 — Planner

**Date:** 2026-07-24

**Summary:** Implemented the Planner — a pure function mapping `AnalysisResult → Recommendation`. Converts semantic understanding into a recommendation via policy table.

### Key design decisions

1. **Tuple-based policy table.** `_POLICY[FileCategory] = (SuggestedAction, reason)` couples the action with its human-readable explanation.
2. **Only ARCHIVE and INSTALLER trigger MOVE.** Everything else defaults to no action. Conservative by design.
3. **Confidence gate.** If `confidence < 1.0`, action is always `None`. This protects against future confidence evolution.
4. **No recommendation carries a destination.** The Planner says *what* should happen, not *where*. Destination is execution context.

### Why this commit matters

After Commit 6, the full reasoning pipeline exists: Scanner → Classifier → Planner. The application can now look at a file, understand what it is, and decide what to suggest.

---

## Commit 7 — Review Builder

**Date:** 2026-07-24

**Summary:** Introduced `ReviewItem` (orchestration pair of AnalysisResult + Recommendation) and `ReviewModel` (immutable snapshot). Transforms individual decisions into a reviewable report.

### Key design decisions

1. **ReviewItem is an orchestration type, not a domain model.** It pairs but doesn't embed — AnalysisResult and Recommendation remain independent.
2. **ReviewModel uses tuples, not lists.** Full immutability: frozen dataclass + tuple collections.
3. **Snapshot semantics.** `build_review()` copies inputs immediately — caller mutations don't affect the review.
4. **Reuses `group_by_category()`.** No duplicate aggregation logic.
5. **`reclaimable_size` only counts MOVE recommendations.** A single derived field that the renderer and CLI both need.

---

## Commit 8 — Renderer + Formatting

**Date:** 2026-07-24

**Summary:** Built the presentation layer. `render(review) -> str` is a pure function. Introduced `utils/formatting.py` for reusable number-to-string functions.

### Architecture review insight

The most valuable design decision was keeping formatting utilities (`format_bytes`, `format_percentage`) in their own module rather than inside the renderer. This means a future JSON exporter or GUI can reuse them without importing from the renderer module.

### Key design decisions

1. **One public function, four private section builders.** `_render_header`, `_render_categories`, `_render_recommendations`, `_render_footer`. No exported internals.
2. **No `_FormatContext` abstraction.** Premature — a single `use_color` boolean threaded through function signatures is fine.
3. **Renderer performs zero calculations.** All data comes from ReviewModel.

---

## Commit 9 — Executor

**Date:** 2026-07-24

**Summary:** The execution layer — the only module that modifies the filesystem. Receives `ReviewItem`s and a destination path, dispatches internally based on `SuggestedAction`.

### Architecture review insight

The key design debate was "who owns the destination path?" Three options were considered:
1. **Parameter on `execute()`** — chosen for v1. Simplest, and destination is execution context, not policy.
2. **Inside `Recommendation`** — rejected. The Planner recommends *what*, not *where*.
3. **In a separate execution policy** — deferred. Could be introduced if per-file routing becomes necessary.

### Key design decisions

1. **Internal dispatch by SuggestedAction.** The Executor receives all ReviewItems and dispatches internally — MOVE, DELETE, LEAVE, or None. The CLI doesn't pre-filter.
2. **Flat layout.** `destination / src.name`. No brittle relative path computation.
3. **Collision policy: SKIP.** Never overwrite. Record in report.
4. **All per-file errors captured in ExecutionResult.** Never raised. The Executor continues across failures.
5. **`dry_run` inside `execute()`.** Single source of truth ensures the dry-run path and the execution path can never diverge.

### Module invariant

```python
"""
The Executor never decides. It only executes decisions that have already been made.
"""
```

---

## Commit 10 — Application Composition & CLI

**Date:** 2026-07-24

**Summary:** Wired all modules into a usable application. No new domain logic — just orchestration.

### Key design decisions

1. **Two functions, not one.** `analyze_directory(root) -> ReviewModel` (pure) and `execute_review(items, destination, dry_run) -> ExecutionReport` (thin wrapper). No `run()` function with an `execute` boolean flag mixing pure and impure concerns.
2. **No PipelineResult wrapper.** The two-function API naturally eliminates the need.
3. **No rendering in pipeline.** Pipeline returns data. CLI calls `render()` + `print()`. The Renderer stays independent.
4. **Single error boundary in CLI.** `ValueError → exit 2`, `Exception → exit 3`. Pipeline lets exceptions propagate.
5. **Exit codes:** 0 = success, 1 = cancelled, 2 = invalid args, 3 = runtime error.
6. **`pyproject.toml` entry point:** `maccleanup = cli.main:main`.

### Directory filtering decision

The pipeline does not filter directories. They remain in ReviewModel with UNKNOWN category and no action. The renderer displays them in `total_files` but they never appear in recommendations. This is intentional and documented — changing it would require deciding whether `total_files` means "filesystem entries" or "actionable files."

---

## Commit 11 — UX Polish & Documentation

**Date:** 2026-07-24

**Summary:** The final polish pass. Improved the renderer with two-mode output (concise + verbose), added beginner-friendly path resolution, and wrote comprehensive documentation.

### Key design decisions

1. **Two render modes.** `verbose=False` (default) shows a concise summary by category. `verbose=True` shows every file with its recommendation. Follows the CLI convention: concise by default, detailed on request.
2. **Recommendations grouped by category, not action.** Users think in terms of "what kinds of files" not "what actions apply." ARCHIVE and INSTALLER both trigger MOVE, but showing them by category gives more useful information.
3. **No percentages.** Users care about counts and sizes. Percentages made the report look analytical rather than actionable.
4. **`_resolve_path()` in CLI.** Accepts `Downloads`, `~/Downloads`, and `/absolute/path`. Stays entirely in the CLI layer — the pipeline never knows about path resolution.
5. **Color auto-detection.** `sys.stdout.isatty()` controls the default. `use_color` is still an explicit parameter — the test suite passes `use_color=False` to guarantee plain-text output.

### Final project state

```
Filesystem → Scanner → FileMetadata → Classifier → AnalysisResult → Planner → Recommendation
                                                                                     ↓
                                                                              ReviewItem
                                                                                     ↓
                                                                              ReviewBuilder
                                                                                     ↓
                                                                              ReviewModel
                                                                               /        \
                                                                              /          \
                                                                             ↓            ↓
                                                                        Renderer      Executor
                                                                             ↓            ↓
                                                                       CLI (stdout)  ExecutionReport
```

**191 tests, all passing, zero regressions across 11 commits.**

### What was intentionally deferred

- **Warning propagation.** `ScannerResult.warnings` exists but never reaches the user. Should be addressed before v2.
- **CategorySummary mutability.** ReviewModel is frozen but the summaries it wraps are not. A small refactor commit could fix this.
- **Default exclusions.** No hardcoded exclusion set. The Scanner accepts `exclude_names` but the CLI doesn't pass any by default.
- **Folder picker for `maccleanup` without arguments.** A native macOS dialog would be a nice v2 enhancement.
- **Progress indicators and logging.** The pipeline is fast enough that progress bars aren't needed for v1.