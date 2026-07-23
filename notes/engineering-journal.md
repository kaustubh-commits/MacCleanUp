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