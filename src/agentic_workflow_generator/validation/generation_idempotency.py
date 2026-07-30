"""Pure generation-idempotency snapshot comparison."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_workflow_generator.domain import Diagnostic

MISSING_AFTER_DIAGNOSTIC = "AWG-GENERATION-IDEMPOTENCY-001"
ADDED_AFTER_DIAGNOSTIC = "AWG-GENERATION-IDEMPOTENCY-002"
CHANGED_AFTER_DIAGNOSTIC = "AWG-GENERATION-IDEMPOTENCY-003"


@dataclass(frozen=True, slots=True)
class GenerationSnapshotFile:
    """One immutable generated-file snapshot record."""

    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class GenerationSnapshot:
    """Deterministic snapshot of generated repository state."""

    files: tuple[GenerationSnapshotFile, ...]

    @property
    def file_count(self) -> int:
        """Return the number of files in the snapshot."""

        return len(self.files)


@dataclass(frozen=True, slots=True)
class GenerationIdempotencyResult:
    """Deterministic comparison of two generation snapshots."""

    before: GenerationSnapshot
    after: GenerationSnapshot
    missing_after: tuple[str, ...]
    added_after: tuple[str, ...]
    changed_after: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_idempotent(self) -> bool:
        """Return whether generation preserved every snapshot file."""

        return not self.diagnostics

    @property
    def checked_file_count(self) -> int:
        """Return the number of files in the post-generation snapshot."""

        return self.after.file_count


def compare_generation_snapshots(
    before: GenerationSnapshot,
    after: GenerationSnapshot,
) -> GenerationIdempotencyResult:
    """Compare deterministic snapshots without side effects."""

    before_by_path = {
        item.path: item.sha256
        for item in before.files
    }
    after_by_path = {
        item.path: item.sha256
        for item in after.files
    }

    before_paths = set(before_by_path)
    after_paths = set(after_by_path)

    missing_after = tuple(
        sorted(before_paths - after_paths)
    )
    added_after = tuple(
        sorted(after_paths - before_paths)
    )
    changed_after = tuple(
        sorted(
            path
            for path in before_paths & after_paths
            if before_by_path[path] != after_by_path[path]
        )
    )

    diagnostics = (
        tuple(
            _diagnostic(
                MISSING_AFTER_DIAGNOSTIC,
                path,
                "missing after generation",
            )
            for path in missing_after
        )
        + tuple(
            _diagnostic(
                ADDED_AFTER_DIAGNOSTIC,
                path,
                "added after generation",
            )
            for path in added_after
        )
        + tuple(
            _diagnostic(
                CHANGED_AFTER_DIAGNOSTIC,
                path,
                "changed after generation",
            )
            for path in changed_after
        )
    )

    return GenerationIdempotencyResult(
        before=before,
        after=after,
        missing_after=missing_after,
        added_after=added_after,
        changed_after=changed_after,
        diagnostics=diagnostics,
    )


def _diagnostic(
    code: str,
    path: str,
    message: str,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        source_path=path,
        related_identities=(path,),
    )
