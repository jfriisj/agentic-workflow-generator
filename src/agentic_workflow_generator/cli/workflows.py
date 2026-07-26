"""Workflow registry validation command."""

from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryError,
    RegistryKind,
    RegistryLoader,
)
from agentic_workflow_generator.validation.workflows import (
    WorkflowDependencyProjectionError,
    WorkflowReferenceData,
    project_artifact_statuses,
    project_skill_capabilities,
    validate_workflow_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-WORKFLOW-900"


def main() -> int:
    """Validate the reusable workflow registry."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        loader = RegistryLoader(paths)
        workflow_sources = loader.load(RegistryKind.WORKFLOW)
        skill_sources = loader.load(RegistryKind.SKILL)
        artifact_sources = loader.load(RegistryKind.ARTIFACT)
        schema = read_json_object(
            paths.schema_root / "registry" / "workflow.schema.json"
        )
        references = WorkflowReferenceData(
            skill_capabilities=project_skill_capabilities(skill_sources),
            artifact_statuses=project_artifact_statuses(artifact_sources),
        )
    except (
        InfrastructureError,
        RegistryError,
        WorkflowDependencyProjectionError,
    ) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    result = validate_workflow_registry(
        workflow_sources,
        schema,
        references,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    gate_count = sum(
        state.gate is not None
        for workflow in result.workflows
        for state in workflow.states
    )

    print(
        "PASS: Workflow registry is valid. "
        f"Checked {len(result.workflows)} workflow file(s), "
        f"{gate_count} gate(s), "
        f"{len(references.skill_capabilities)} skill capability "
        "reference(s), and "
        f"{len(references.artifact_statuses)} artifact contract(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Workflow registry', diagnostics)
