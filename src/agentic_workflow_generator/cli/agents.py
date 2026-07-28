"""Agent-profile registry validation command."""

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
from agentic_workflow_generator.validation.agents import (
    AgentDependencyProjectionError,
    AgentReferenceData,
    project_permission_profile_names,
    project_skill_capabilities,
    validate_agent_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-AGENT-900"


def main() -> int:
    """Validate the reusable agent-profile registry."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        loader = RegistryLoader(paths)
        agent_sources = loader.load(RegistryKind.AGENT)
        skill_sources = loader.load(RegistryKind.SKILL)
        permission_sources = loader.load(RegistryKind.PERMISSION_PROFILE)
        schema = read_json_object(paths.schema_root / "registry" / "agent.schema.json")
        references = AgentReferenceData(
            skill_capabilities=(project_skill_capabilities(skill_sources)),
            permission_profiles=(project_permission_profile_names(permission_sources)),
        )
    except (
        AgentDependencyProjectionError,
        InfrastructureError,
        RegistryError,
    ) as exc:
        return _render_failure(
            (
                Diagnostic(
                    code=COMMAND_FAILURE_DIAGNOSTIC,
                    message=str(exc),
                ),
            )
        )

    result = validate_agent_registry(
        agent_sources,
        schema,
        references,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    print(
        "PASS: Agent registry is valid. "
        f"Checked {len(result.profiles)} agent file(s), "
        f"{len(references.skill_capabilities)} skill "
        "capability reference(s), and "
        f"{len(references.permission_profiles)} "
        "permission profile(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Agent registry', diagnostics)

if __name__ == "__main__":
    raise SystemExit(main())
