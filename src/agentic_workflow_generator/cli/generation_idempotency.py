"""Typed generation-idempotency validation command."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from jsonschema.exceptions import SchemaError

from agentic_workflow_generator.application.generation_idempotency import (
    GenerationIdempotencyAnalysis,
    GenerationIdempotencyValidationError,
    GenerationSnapshotError,
    validate_generation_idempotency,
)
from agentic_workflow_generator.application.target_materialization import (
    TargetManifestValidationError,
    TargetMaterializationValidationError,
)
from agentic_workflow_generator.cli.rendering import render_diagnostic
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths

COMMAND_FAILURE_DIAGNOSTIC = "AWG-GENERATION-IDEMPOTENCY-900"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Validate deterministic typed generation."""

    del argv

    try:
        analysis = validate_generation_idempotency(
            ProjectPaths(Path.cwd().resolve())
        )
    except GenerationSnapshotError as exc:
        print(
            "FAIL: Could not collect "
            f"{exc.phase} idempotency snapshot: {exc}"
        )
        return 1
    except (
        GenerationIdempotencyValidationError,
        TargetManifestValidationError,
        TargetMaterializationValidationError,
    ) as exc:
        return _render_generation_failure(
            exc.diagnostics
        )
    except (
        InfrastructureError,
        SchemaError,
        OSError,
        ValueError,
    ) as exc:
        return _render_generation_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    return _render_analysis(analysis)


def _render_analysis(
    analysis: GenerationIdempotencyAnalysis,
) -> int:
    result = analysis.result

    if result.is_idempotent:
        print(
            "PASS: Generation is idempotent. "
            f"Checked {result.checked_file_count} file(s)."
        )
        return 0

    print("FAIL: Generation is not idempotent.")

    for path in result.missing_after:
        print(f"  - missing after generation: {path}")

    for path in result.added_after:
        print(f"  - added after generation: {path}")

    for path in result.changed_after:
        print(f"  - changed after generation: {path}")

    return 1


def _render_generation_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    print("FAIL: idempotency generation run failed.")

    for diagnostic in diagnostics:
        print(f"  - {render_diagnostic(diagnostic)}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
