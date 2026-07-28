"""OpenCode runtime validation command."""

from __future__ import annotations

from collections.abc import Sequence

from agentic_workflow_generator.application.target_runtime_validation import (
    validate_opencode_runtime,
)
from agentic_workflow_generator.cli.rendering import (
    run_validation_command,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-TARGET-RUNTIME-900"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Require OpenCode to parse generated target output."""

    del argv

    return run_validation_command(
        label="OpenCode runtime",
        failure_code=COMMAND_FAILURE_DIAGNOSTIC,
        validate=validate_opencode_runtime,
        success_message=(
            "PASS: OpenCode runtime parsed canonical config, "
            "agents, and skills."
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
