"""Canonical compiler-input lockfile validation command."""

from __future__ import annotations

from collections.abc import Sequence

from agentic_workflow_generator.application.lockfile import (
    validate_lockfile,
)
from agentic_workflow_generator.cli.rendering import (
    run_validation_command,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-LOCKFILE-VALIDATION-900"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Validate exact compiler-input lockfile provenance."""

    del argv

    return run_validation_command(
        label="Lockfile",
        failure_code=COMMAND_FAILURE_DIAGNOSTIC,
        validate=validate_lockfile,
        success_message="PASS: Lockfile is valid.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
