"""Bundle-composition registry validation command."""

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
from agentic_workflow_generator.validation.bundles import (
    BundleDependencyProjectionError,
    BundleReferenceData,
    project_agent_profile_names,
    project_artifact_contracts,
    project_permission_profile_names,
    project_profile_names,
    project_skills,
    project_target_names,
    project_workflows,
    validate_bundle_registry,
)

COMMAND_FAILURE_DIAGNOSTIC = "AWG-BUNDLE-900"


def main() -> int:
    """Validate authoritative bundle composition."""

    try:
        paths = ProjectPaths(Path.cwd().resolve())
        loader = RegistryLoader(paths)

        bundle_sources = loader.load(RegistryKind.BUNDLE)
        profile_sources = loader.load(RegistryKind.PROFILE)
        workflow_sources = loader.load(RegistryKind.WORKFLOW)
        agent_sources = loader.load(RegistryKind.AGENT)
        skill_sources = loader.load(RegistryKind.SKILL)
        artifact_sources = loader.load(RegistryKind.ARTIFACT)
        permission_sources = loader.load(RegistryKind.PERMISSION_PROFILE)
        target_sources = loader.load(RegistryKind.TARGET)

        schema = read_json_object(paths.schema_root / "registry" / "bundle.schema.json")

        references = BundleReferenceData(
            profiles=project_profile_names(profile_sources),
            workflows=project_workflows(workflow_sources),
            agent_profiles=(project_agent_profile_names(agent_sources)),
            skills=project_skills(skill_sources),
            artifact_contracts=(project_artifact_contracts(artifact_sources)),
            permission_profiles=(project_permission_profile_names(permission_sources)),
            targets=project_target_names(target_sources),
        )
    except (
        BundleDependencyProjectionError,
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

    result = validate_bundle_registry(
        bundle_sources,
        schema,
        references,
    )

    if not result.is_valid:
        return _render_failure(result.diagnostics)

    instance_count = sum(len(bundle.agent_instances) for bundle in result.bundles)
    binding_count = sum(len(bundle.role_bindings) for bundle in result.bundles)
    separation_policy_count = sum(
        len(bundle.separation_policies) for bundle in result.bundles
    )

    print(
        "PASS: Bundle registry is valid. "
        f"Checked {len(result.bundles)} bundle file(s), "
        f"{instance_count} agent instance(s), "
        f"{binding_count} role binding(s), and "
        f"{separation_policy_count} separation policy file entry(ies)."
    )
    return 0


def _render_failure(
    diagnostics: tuple[Diagnostic, ...],
) -> int:
    return render_failure('Bundle registry', diagnostics)

if __name__ == "__main__":
    raise SystemExit(main())
