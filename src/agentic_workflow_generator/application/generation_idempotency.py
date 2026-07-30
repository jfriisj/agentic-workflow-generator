"""Typed generation-idempotency application service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
    sha256_file,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.generation_idempotency import (
    GenerationIdempotencyResult,
    GenerationSnapshot,
    GenerationSnapshotFile,
    compare_generation_snapshots,
)

from .lockfile import generate_lockfile, validate_lockfile
from .target_materialization import materialize_targets
from .target_output_validation import validate_target_output

_BASELINE_FILES = (
    ".agentic/agentic-lock.json",
    ".agentic/generated/output-manifest.json",
)


class GenerationSnapshotError(ValueError):
    """Raised when one idempotency snapshot cannot be collected."""

    def __init__(
        self,
        phase: Literal["baseline", "post-generation"],
        reason: str,
    ) -> None:
        self.phase = phase
        super().__init__(reason)


class GenerationIdempotencyValidationError(ValueError):
    """Raised when a typed generation boundary rejects its output."""

    def __init__(
        self,
        stage: str,
        diagnostics: tuple[Diagnostic, ...],
    ) -> None:
        self.stage = stage
        self.diagnostics = diagnostics
        super().__init__(
            f"{stage} validation failed with "
            f"{len(diagnostics)} diagnostic(s)"
        )


@dataclass(frozen=True, slots=True)
class GenerationRunSummary:
    """Summary of the typed generation operations."""

    lockfile_input_count: int
    generated_target_count: int
    generated_file_count: int
    removed_file_count: int


@dataclass(frozen=True, slots=True)
class GenerationIdempotencyAnalysis:
    """Complete result from one idempotency analysis."""

    result: GenerationIdempotencyResult
    generation: GenerationRunSummary


def validate_generation_idempotency(
    paths: ProjectPaths,
) -> GenerationIdempotencyAnalysis:
    """Generate through typed services and compare before and after."""

    before = _collect_snapshot_for_phase(
        paths,
        "baseline",
    )

    lockfile = generate_lockfile(paths)
    lockfile_diagnostics = validate_lockfile(paths)

    if lockfile_diagnostics:
        raise GenerationIdempotencyValidationError(
            "lockfile",
            lockfile_diagnostics,
        )

    materialization = materialize_targets(paths)
    output_diagnostics = validate_target_output(paths)

    if output_diagnostics:
        raise GenerationIdempotencyValidationError(
            "target output",
            output_diagnostics,
        )

    after = _collect_snapshot_for_phase(
        paths,
        "post-generation",
    )

    return GenerationIdempotencyAnalysis(
        result=compare_generation_snapshots(
            before,
            after,
        ),
        generation=GenerationRunSummary(
            lockfile_input_count=lockfile.input_file_count,
            generated_target_count=materialization.target_count,
            generated_file_count=(
                materialization.generated_file_count
            ),
            removed_file_count=(
                materialization.removed_file_count
            ),
        ),
    )


def collect_generation_snapshot(
    paths: ProjectPaths,
) -> GenerationSnapshot:
    """Collect the lockfile, manifest, and manifest-declared files."""

    manifest = read_json_object(paths.manifest)
    relative_paths = set(_BASELINE_FILES)
    relative_paths.update(
        _declared_generated_paths(
            manifest,
            paths,
        )
    )

    files: list[GenerationSnapshotFile] = []

    for relative_path in sorted(relative_paths):
        absolute_path = paths.repository_path(relative_path)

        if not absolute_path.is_file():
            raise FileNotFoundError(
                "Snapshot file does not exist: "
                f"{relative_path}"
            )

        files.append(
            GenerationSnapshotFile(
                path=relative_path,
                sha256=sha256_file(absolute_path),
            )
        )

    return GenerationSnapshot(files=tuple(files))


def _collect_snapshot_for_phase(
    paths: ProjectPaths,
    phase: Literal["baseline", "post-generation"],
) -> GenerationSnapshot:
    try:
        return collect_generation_snapshot(paths)
    except (
        InfrastructureError,
        OSError,
        ValueError,
    ) as exc:
        raise GenerationSnapshotError(
            phase,
            str(exc),
        ) from exc


def _declared_generated_paths(
    manifest: JsonObject,
    paths: ProjectPaths,
) -> tuple[str, ...]:
    targets = manifest.get("targets")

    if not isinstance(targets, list):
        raise ValueError(
            f"{paths.manifest}: targets must be a list"
        )

    generated_paths: set[str] = set()

    for target in targets:
        if not isinstance(target, dict):
            raise ValueError(
                f"{paths.manifest}: targets entries must be objects"
            )

        generated_files = target.get("generatedFiles")

        if not isinstance(generated_files, list):
            raise ValueError(
                f"{paths.manifest}: target.generatedFiles "
                "must be a list"
            )

        for generated_file in generated_files:
            if not isinstance(generated_file, dict):
                raise ValueError(
                    f"{paths.manifest}: generatedFiles entries "
                    "must be objects"
                )

            raw_path = generated_file.get("path")

            if (
                not isinstance(raw_path, str)
                or not raw_path.strip()
            ):
                raise ValueError(
                    f"{paths.manifest}: generated file path "
                    "must be a non-empty string"
                )

            paths.repository_path(raw_path)
            generated_paths.add(raw_path)

    return tuple(sorted(generated_paths))
