"""Deterministic shared CLI diagnostic rendering."""

from __future__ import annotations

from agentic_workflow_generator.domain import Diagnostic


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
