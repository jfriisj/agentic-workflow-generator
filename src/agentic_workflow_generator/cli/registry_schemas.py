"""Mechanical registry JSON Schema validation command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.cli.rendering import (
    render_diagnostic,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryError,
)
from agentic_workflow_generator.validation.registry_schemas import (
    validate_registry_schemas,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-REGISTRY-SCHEMA-900"


def main() -> int:
    """Validate all registry schemas and matching documents."""

    try:
        result = validate_registry_schemas(
            ProjectPaths(Path.cwd().resolve())
        )
    except (
        InfrastructureError,
        RegistryError,
        ValueError,
    ) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    print(
        "PASS: Registry JSON schemas are valid. "
        f"Checked {result.checked_document_count} "
        "registry file(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    print("ERROR: Registry schema validation failed.")

    for diagnostic in diagnostics:
        print(f"  - {render_diagnostic(diagnostic)}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
