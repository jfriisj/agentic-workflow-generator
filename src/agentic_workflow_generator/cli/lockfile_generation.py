"""Canonical compiler-input lockfile generation command."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from agentic_workflow_generator.application.lockfile import (
    generate_lockfile,
)
from agentic_workflow_generator.cli.rendering import (
    render_failure,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths

COMMAND_FAILURE_DIAGNOSTIC = "AWG-LOCKFILE-GENERATION-900"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Generate the canonical compiler-input lockfile."""

    del argv

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        result = generate_lockfile(paths)
    except (
        InfrastructureError,
        OSError,
        ValueError,
    ) as exc:
        return render_failure(
            "Lockfile generation",
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            ),
        )

    print("PASS: Generated deterministic lockfile.")
    print(f"Input files: {result.input_file_count}")
    print(f"Content hash: {result.content_hash}")
    print(
        "Lockfile: "
        f"{paths.lockfile.relative_to(paths.root).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
