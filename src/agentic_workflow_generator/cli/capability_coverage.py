"""Global typed capability-coverage report command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.application.capability_coverage import (
    analyze_capability_coverage,
)
from agentic_workflow_generator.application.registry_snapshot import (
    RegistrySnapshotError,
    RegistrySnapshotValidationError,
)
from agentic_workflow_generator.cli.rendering import render_diagnostic
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.capability_coverage import (
    DUPLICATE_PROVIDER_DIAGNOSTIC,
    MISSING_CAPABILITY_DIAGNOSTIC,
    UNUSED_CAPABILITY_DIAGNOSTIC,
    CapabilityCoverageResult,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-CAPABILITY-COVERAGE-900"


def main() -> int:
    """Report global runtime capability coverage."""

    try:
        result = analyze_capability_coverage(
            ProjectPaths(Path.cwd().resolve())
        )
    except RegistrySnapshotValidationError as exc:
        return _render_snapshot_failure(exc.diagnostics)
    except (
        InfrastructureError,
        RegistrySnapshotError,
        ValueError,
    ) as exc:
        return _render_snapshot_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    _render_report(result)
    return 0 if result.is_complete else 1


def _render_report(
    result: CapabilityCoverageResult,
) -> None:
    print(
        "Required runtime capabilities: "
        f"{result.required_count}"
    )
    print(
        f"Skill capabilities: {result.provided_count}"
    )
    print()

    _render_section(
        "Missing skill coverage:",
        result.diagnostics,
        MISSING_CAPABILITY_DIAGNOSTIC,
    )
    print()
    _render_section(
        "Unused skill capabilities:",
        result.diagnostics,
        UNUSED_CAPABILITY_DIAGNOSTIC,
    )
    print()
    _render_section(
        "Duplicate skill capabilities:",
        result.diagnostics,
        DUPLICATE_PROVIDER_DIAGNOSTIC,
    )

    if result.is_complete:
        print()
        print(
            "PASS: Runtime capability coverage is complete. "
            f"Checked {result.required_count} required "
            "capability/capabilities."
        )


def _render_section(
    heading: str,
    diagnostics: tuple[Diagnostic, ...],
    diagnostic_code: str,
) -> None:
    print(heading)
    matching = tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code == diagnostic_code
    )

    if not matching:
        print("  none")
        return

    for diagnostic in matching:
        print(f"  - {render_diagnostic(diagnostic)}")


def _render_snapshot_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    print("FAIL: Capability coverage could not be analyzed.")

    for diagnostic in diagnostics:
        print(f"  - {render_diagnostic(diagnostic)}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
