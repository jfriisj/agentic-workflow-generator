"""Required development-environment validation command."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from agentic_workflow_generator.application.environment import (
    EnvironmentCheck,
    validate_environment,
)
from agentic_workflow_generator.cli.rendering import (
    render_diagnostic,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths

COMMAND_FAILURE_DIAGNOSTIC = "AWG-ENVIRONMENT-900"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Validate every mandatory development command."""

    del argv

    paths = ProjectPaths(Path.cwd().resolve())
    path_value = os.environ.get("PATH", "")

    print("== Agentic environment validation ==")
    print(f"Working directory: {paths.root}")
    print(f"PATH: {path_value}")

    try:
        result = validate_environment(
            paths,
            path_value=path_value,
        )
    except (
        InfrastructureError,
        OSError,
        ValueError,
    ) as exc:
        diagnostic = Diagnostic(
            code=COMMAND_FAILURE_DIAGNOSTIC,
            message=str(exc),
        )
        print(f"FAIL: {render_diagnostic(diagnostic)}")
        print()
        print(
            "FAIL: Environment validation failed before "
            "command checks completed."
        )
        return 1

    for check in result.checks:
        print(_render_check(check))

    if result.diagnostics:
        failed_names = ", ".join(
            check.requirement.name
            for check in result.checks
            if check.diagnostic is not None
        )
        print()
        print(
            "FAIL: Environment validation failed for "
            f"{len(result.diagnostics)} required command(s): "
            f"{failed_names}"
        )
        return 1

    print()
    print(
        "PASS: Environment validation passed. Checked "
        f"{len(result.checks)} required command(s)."
    )
    return 0


def _render_check(
    check: EnvironmentCheck,
) -> str:
    if check.diagnostic is not None:
        return f"FAIL: {render_diagnostic(check.diagnostic)}"

    if check.executable is None or check.version is None:
        raise ValueError(
            "Successful environment check lacks executable or version"
        )

    return (
        f"PASS: {check.requirement.name} available at "
        f"{check.executable} ({check.version})"
    )


if __name__ == "__main__":
    raise SystemExit(main())
