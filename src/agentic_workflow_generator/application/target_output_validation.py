"""Validation of committed target output against canonical rendering."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    sha256_bytes,
)
from agentic_workflow_generator.registry import ProjectPaths

from .target_materialization import (
    build_target_materialization_plan,
)

MISSING_FILE_DIAGNOSTIC = "AWG-TARGET-OUTPUT-001"
INVALID_FILE_DIAGNOSTIC = "AWG-TARGET-OUTPUT-002"
CONTENT_DRIFT_DIAGNOSTIC = "AWG-TARGET-OUTPUT-003"
UNMANAGED_FILE_DIAGNOSTIC = "AWG-TARGET-OUTPUT-004"
MANIFEST_DRIFT_DIAGNOSTIC = "AWG-TARGET-OUTPUT-005"
OBSOLETE_OUTPUT_DIAGNOSTIC = "AWG-TARGET-OUTPUT-006"


def validate_target_output(
    paths: ProjectPaths,
) -> tuple[Diagnostic, ...]:
    """Validate generated files against a canonical typed plan."""

    plan = build_target_materialization_plan(paths)
    diagnostics: list[Diagnostic] = []

    for target in plan.rendered_targets:
        for rendered_file in target.files:
            absolute_path = paths.repository_path(
                rendered_file.path
            )
            diagnostics.extend(
                _validate_file(
                    absolute_path,
                    rendered_file.path,
                    rendered_file.content,
                )
            )

    for stale_file in plan.stale_files:
        diagnostics.append(
            Diagnostic(
                code=UNMANAGED_FILE_DIAGNOSTIC,
                message=(
                    "target-owned file is not declared by the "
                    "canonical materialization plan"
                ),
                source_path=stale_file.as_posix(),
            )
        )

    diagnostics.extend(
        _validate_file(
            paths.manifest,
            paths.manifest.relative_to(paths.root),
            plan.manifest_bytes,
            manifest=True,
        )
    )

    obsolete_resolution = (
        paths.generated_root / "resolution.json"
    )

    if obsolete_resolution.exists():
        diagnostics.append(
            Diagnostic(
                code=OBSOLETE_OUTPUT_DIAGNOSTIC,
                message=(
                    "obsolete resolution output must not exist; "
                    ".agentic/agentic.json is the canonical "
                    "compiled composition"
                ),
                source_path=obsolete_resolution.relative_to(
                    paths.root
                ).as_posix(),
            )
        )

    return tuple(diagnostics)


def _validate_file(
    absolute_path: Path,
    relative_path: Path,
    expected: bytes,
    *,
    manifest: bool = False,
) -> tuple[Diagnostic, ...]:
    source_path = relative_path.as_posix()

    if absolute_path.is_symlink():
        return (
            Diagnostic(
                code=INVALID_FILE_DIAGNOSTIC,
                message="generated output must not be a symlink",
                source_path=source_path,
            ),
        )

    if not absolute_path.exists():
        return (
            Diagnostic(
                code=(
                    MANIFEST_DRIFT_DIAGNOSTIC
                    if manifest
                    else MISSING_FILE_DIAGNOSTIC
                ),
                message=(
                    "output manifest is missing"
                    if manifest
                    else "required generated file is missing"
                ),
                source_path=source_path,
            ),
        )

    if not absolute_path.is_file():
        return (
            Diagnostic(
                code=INVALID_FILE_DIAGNOSTIC,
                message="generated output path must be a file",
                source_path=source_path,
            ),
        )

    try:
        actual = absolute_path.read_bytes()
    except OSError as exc:
        return (
            Diagnostic(
                code=INVALID_FILE_DIAGNOSTIC,
                message=f"could not read generated output: {exc}",
                source_path=source_path,
            ),
        )

    if actual == expected:
        return ()

    return (
        Diagnostic(
            code=(
                MANIFEST_DRIFT_DIAGNOSTIC
                if manifest
                else CONTENT_DRIFT_DIAGNOSTIC
            ),
            message=(
                "output differs from canonical materialization; "
                f"expected sha256={sha256_bytes(expected)} "
                f"bytes={len(expected)}, "
                f"found sha256={sha256_bytes(actual)} "
                f"bytes={len(actual)}"
            ),
            source_path=source_path,
        ),
    )
