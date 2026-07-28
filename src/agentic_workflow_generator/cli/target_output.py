"""Canonical generated target output validation command."""

from __future__ import annotations

from collections.abc import Sequence

from agentic_workflow_generator.application.target_output_validation import (
    validate_target_output,
)
from agentic_workflow_generator.cli.rendering import (
    run_validation_command,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-TARGET-OUTPUT-900"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Validate committed output against canonical rendering."""

    del argv

    return run_validation_command(
        label="Target output",
        failure_code=COMMAND_FAILURE_DIAGNOSTIC,
        validate=validate_target_output,
        success_message=(
            "PASS: Generated target output is canonical."
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
