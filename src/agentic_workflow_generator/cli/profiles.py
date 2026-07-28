"""Advisory project-profile registry validation command."""

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
from agentic_workflow_generator.validation.profiles import (
    ProfileDependencyProjectionError,
    ProfileReferenceData,
    project_agent_profile_names,
    project_skill_capabilities,
    project_workflow_names,
    validate_profile_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-PROFILE-900"


def main() -> int:
    """Validate the advisory project-profile registry."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        loader = RegistryLoader(paths)

        profile_sources = loader.load(RegistryKind.PROFILE)
        workflow_sources = loader.load(RegistryKind.WORKFLOW)
        agent_sources = loader.load(RegistryKind.AGENT)
        skill_sources = loader.load(RegistryKind.SKILL)

        schema = read_json_object(
            paths.schema_root / "registry" / "profile.schema.json"
        )

        references = ProfileReferenceData(
            workflows=project_workflow_names(workflow_sources),
            agent_profiles=project_agent_profile_names(agent_sources),
            skill_capabilities=project_skill_capabilities(skill_sources),
        )
    except (
        InfrastructureError,
        ProfileDependencyProjectionError,
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

    result = validate_profile_registry(
        profile_sources,
        schema,
        references,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    recommended_agent_count = sum(
        len(profile.recommended_agents) for profile in result.profiles
    )
    recommended_capability_count = sum(
        len(profile.recommended_capabilities) for profile in result.profiles
    )

    print(
        "PASS: Profile registry is valid. "
        f"Checked {len(result.profiles)} profile file(s), "
        f"{recommended_agent_count} recommended agent "
        "reference(s), and "
        f"{recommended_capability_count} recommended "
        "capability reference(s)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Profile registry', diagnostics)

if __name__ == "__main__":
    raise SystemExit(main())
