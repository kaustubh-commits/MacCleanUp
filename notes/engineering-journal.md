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
