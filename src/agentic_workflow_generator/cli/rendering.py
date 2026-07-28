"""Deterministic shared CLI diagnostic rendering."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from jsonschema.exceptions import SchemaError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths

ValidationCommand = Callable[
    [ProjectPaths],
    tuple[Diagnostic, ...],
]


def run_validation_command(
    *,
    label: str,
    failure_code: str,
    validate: ValidationCommand,
    success_message: str,
) -> int:
    """Run one validation command through the shared CLI boundary."""

    try:
        diagnostics = validate(
            ProjectPaths(Path.cwd().resolve())
        )
    except (
        InfrastructureError,
        SchemaError,
        ValueError,
    ) as exc:
        diagnostics = (
            Diagnostic(
                code=failure_code,
                message=str(exc),
            ),
        )

    if diagnostics:
        return render_failure(
            label,
            diagnostics,
        )

    print(success_message)
    return 0


def render_failure(
    label: str,
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    """Render a validation failure and return exit code 1."""

    print(
        f"FAIL: {label} validation found "
        f"{len(diagnostics)} error(s)."
    )

    for diagnostic in diagnostics:
        print(f"  - {render_diagnostic(diagnostic)}")

    return 1


def render_diagnostic(
    diagnostic: Diagnostic,
) -> str:
    """Render one structured diagnostic deterministically."""

    parts = [f"[{diagnostic.code}]"]

    if diagnostic.source_path is not None:
        parts.append(diagnostic.source_path)

    if diagnostic.location is not None:
        parts.append(diagnostic.location)

    parts.append(diagnostic.message)
    return " ".join(parts)
