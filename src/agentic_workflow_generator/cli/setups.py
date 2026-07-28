"""Guided setup registry validation command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.cli.setup_context import (
    SetupContextError,
    load_setup_validation_context,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.validation.setups import (
    validate_setup_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-SETUP-900"


def main() -> int:
    """Validate guided setup registry definitions."""

    try:
        context = load_setup_validation_context(
            Path.cwd().resolve()
        )
    except SetupContextError as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    result = validate_setup_registry(
        context.setup_sources,
        context.setup_schema,
        context.references,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    question_count = sum(len(setup.questions) for setup in result.setups)

    print(
        "PASS: Setup registry is valid. "
        f"Checked {len(result.setups)} setup file(s) and "
        f"{question_count} question(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Setup registry', diagnostics)

if __name__ == "__main__":
    raise SystemExit(main())
