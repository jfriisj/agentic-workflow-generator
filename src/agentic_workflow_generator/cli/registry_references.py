"""Canonical registry-reference validation command."""

from __future__ import annotations

from pathlib import Path

from jsonschema.exceptions import SchemaError

from agentic_workflow_generator.application.registry_references import (
    validate_registry_references,
)
from agentic_workflow_generator.application.registry_snapshot import (
    RegistrySnapshotError,
    RegistrySnapshotValidationError,
)
from agentic_workflow_generator.application.target_materialization import (
    TargetMaterializationError,
    TargetMaterializationValidationError,
)
from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths

COMMAND_FAILURE_DIAGNOSTIC = "AWG-REGISTRY-REFERENCE-900"


def main() -> int:
    """Validate canonical registry references and active composition."""

    try:
        result = validate_registry_references(
            ProjectPaths(Path.cwd().resolve())
        )
    except RegistrySnapshotValidationError as exc:
        return render_failure(
            "Registry reference",
            exc.diagnostics,
        )
    except TargetMaterializationValidationError as exc:
        return render_failure(
            "Registry reference",
            exc.diagnostics,
        )
    except (
        InfrastructureError,
        RegistrySnapshotError,
        SchemaError,
        TargetMaterializationError,
        ValueError,
    ) as exc:
        return render_failure(
            "Registry reference",
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            ),
        )

    summary = result.summary
    print("PASS: Registry references are valid.")
    print(f"Agents: {summary.agent_count}")
    print(f"Targets: {summary.target_count}")
    print(f"Workflows: {summary.workflow_count}")
    print(f"Profiles: {summary.profile_count}")
    print(f"Artifacts: {summary.artifact_count}")
    print(
        "Skill capabilities: "
        f"{summary.skill_capability_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
