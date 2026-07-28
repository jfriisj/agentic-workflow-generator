"""Canonical target materialization command."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from jsonschema.exceptions import SchemaError

from agentic_workflow_generator.application.target_materialization import (
    TargetManifestValidationError,
    TargetMaterializationValidationError,
    materialize_targets,
)
from agentic_workflow_generator.cli.rendering import (
    render_failure,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths

COMMAND_FAILURE_DIAGNOSTIC = "AWG-TARGET-MATERIALIZATION-900"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Materialize every enabled target transactionally."""

    del argv

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        result = materialize_targets(paths)
    except (
        TargetMaterializationValidationError,
        TargetManifestValidationError,
    ) as exc:
        return render_failure(
            "Target materialization",
            exc.diagnostics,
        )
    except (
        InfrastructureError,
        SchemaError,
        ValueError,
    ) as exc:
        return render_failure(
            "Target materialization",
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            ),
        )

    print("PASS: Materialized canonical target output.")
    print(f"Targets: {result.target_count}")
    print(
        "Generated files: "
        f"{result.generated_file_count}"
    )
    print(
        "Removed stale files: "
        f"{result.removed_file_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
