"""Validated typed registry snapshot for application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from agentic_workflow_generator.domain import (
    AgentProfile,
    ArtifactContract,
    Bundle,
    Diagnostic,
    PermissionProfile,
    Profile,
    Skill,
    Workflow,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
    serialize_json,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryError,
    RegistryIndex,
    RegistryKind,
    RegistryLoader,
    RegistrySource,
)
from agentic_workflow_generator.validation.agents import (
    AgentReferenceData,
    project_permission_profile_names,
    project_skill_capabilities,
    validate_agent_registry,
)
from agentic_workflow_generator.validation.artifacts import (
    ArtifactSchemaSnapshot,
    validate_artifact_registry,
)
from agentic_workflow_generator.validation.bundles import (
    BundleReferenceData,
    project_artifact_contracts,
    project_profile_names,
    project_skills,
    project_target_names,
    project_workflows,
    validate_bundle_registry,
)
from agentic_workflow_generator.validation.bundles import (
    project_agent_profile_names as project_bundle_agent_names,
)
from agentic_workflow_generator.validation.bundles import (
    project_permission_profile_names as project_bundle_permission_names,
)
from agentic_workflow_generator.validation.permission_profiles import (
    validate_permission_profile_registry,
)
from agentic_workflow_generator.validation.profiles import (
    ProfileReferenceData,
    project_workflow_names,
    validate_profile_registry,
)
from agentic_workflow_generator.validation.profiles import (
    project_agent_profile_names as project_profile_agent_names,
)
from agentic_workflow_generator.validation.profiles import (
    project_skill_capabilities as project_profile_skill_capabilities,
)
from agentic_workflow_generator.validation.skills import (
    SkillReferenceData,
    project_agent_names,
    validate_skill_registry,
)
from agentic_workflow_generator.validation.workflows import (
    WorkflowReferenceData,
    project_artifact_statuses,
    validate_workflow_registry,
)
from agentic_workflow_generator.validation.workflows import (
    project_skill_capabilities as project_workflow_skill_capabilities,
)


class RegistrySnapshotError(RuntimeError):
    """Base error for validated registry snapshot loading."""


class RegistrySnapshotLoadError(RegistrySnapshotError):
    """Raised when registry input cannot be loaded or projected."""


class RegistrySnapshotValidationError(RegistrySnapshotError):
    """Raised when one typed registry boundary rejects input."""

    def __init__(
        self,
        boundary: str,
        diagnostics: tuple[Diagnostic, ...],
    ) -> None:
        self.boundary = boundary
        self.diagnostics = diagnostics
        super().__init__(
            f"{boundary} validation failed with "
            f"{len(diagnostics)} diagnostic(s)"
        )


class RegistrySnapshotLookupError(RegistrySnapshotError):
    """Raised when an exact validated registry identity is missing."""


RegistryItemT = TypeVar("RegistryItemT")


@dataclass(frozen=True, slots=True)
class ValidatedRegistrySnapshot:
    """Complete validated typed registry input for application services."""

    agents: tuple[AgentProfile, ...]
    artifacts: tuple[ArtifactContract, ...]
    bundles: tuple[Bundle, ...]
    permission_profiles: tuple[PermissionProfile, ...]
    profiles: tuple[Profile, ...]
    skills: tuple[Skill, ...]
    workflows: tuple[Workflow, ...]
    targets: frozenset[str]

    def agent_by_name(self, name: str) -> AgentProfile:
        """Return one exact validated agent profile."""

        return _lookup_identity(
            self.agents,
            name,
            "agent profile",
            lambda item: item.name,
        )

    def artifact_by_type(self, artifact_type: str) -> ArtifactContract:
        """Return one exact validated artifact contract."""

        return _lookup_identity(
            self.artifacts,
            artifact_type,
            "artifact contract",
            lambda item: item.type,
        )

    def bundle_by_name(self, name: str) -> Bundle:
        """Return one exact validated bundle."""

        return _lookup_identity(
            self.bundles,
            name,
            "bundle",
            lambda item: item.name,
        )

    def permission_profile_by_name(
        self,
        name: str,
    ) -> PermissionProfile:
        """Return one exact validated permission profile."""

        return _lookup_identity(
            self.permission_profiles,
            name,
            "permission profile",
            lambda item: item.name,
        )

    def profile_by_name(self, name: str) -> Profile:
        """Return one exact validated advisory profile."""

        return _lookup_identity(
            self.profiles,
            name,
            "profile",
            lambda item: item.name,
        )

    def skill_by_name(self, name: str) -> Skill:
        """Return one exact validated skill."""

        return _lookup_identity(
            self.skills,
            name,
            "skill",
            lambda item: item.name,
        )

    def workflow_by_name(self, name: str) -> Workflow:
        """Return one exact validated workflow."""

        return _lookup_identity(
            self.workflows,
            name,
            "workflow",
            lambda item: item.name,
        )


def load_validated_registry_snapshot(
    paths: ProjectPaths,
) -> ValidatedRegistrySnapshot:
    """Load and validate all typed registry domains in dependency order."""

    try:
        loader = RegistryLoader(paths)
        index = RegistryIndex(
            source
            for kind in RegistryKind
            for source in loader.load(kind)
        )
        agent_sources = index.sources(RegistryKind.AGENT)
        artifact_sources = index.sources(RegistryKind.ARTIFACT)
        bundle_sources = index.sources(RegistryKind.BUNDLE)
        permission_sources = index.sources(
            RegistryKind.PERMISSION_PROFILE
        )
        profile_sources = index.sources(RegistryKind.PROFILE)
        skill_sources = index.sources(RegistryKind.SKILL)
        target_sources = index.sources(RegistryKind.TARGET)
        workflow_sources = index.sources(RegistryKind.WORKFLOW)

        permission_result = validate_permission_profile_registry(
            permission_sources,
            _registry_schema(
                paths,
                "permission-profile.schema.json",
            ),
        )
        _require_valid(
            "permission profile registry",
            permission_result.diagnostics,
        )

        skill_result = validate_skill_registry(
            skill_sources,
            _registry_schema(paths, "skill.schema.json"),
            SkillReferenceData(
                agent_names=project_agent_names(agent_sources),
                existing_content_paths=_existing_skill_content_paths(
                    skill_sources
                ),
            ),
        )
        _require_valid(
            "skill registry",
            skill_result.diagnostics,
        )

        agent_result = validate_agent_registry(
            agent_sources,
            _registry_schema(paths, "agent.schema.json"),
            AgentReferenceData(
                skill_capabilities=project_skill_capabilities(
                    skill_sources
                ),
                permission_profiles=project_permission_profile_names(
                    permission_sources
                ),
            ),
        )
        _require_valid(
            "agent registry",
            agent_result.diagnostics,
        )

        artifact_result = validate_artifact_registry(
            artifact_sources,
            _registry_schema(paths, "artifact.schema.json"),
            _artifact_schema_snapshots(paths),
        )
        _require_valid(
            "artifact registry",
            artifact_result.diagnostics,
        )

        workflow_result = validate_workflow_registry(
            workflow_sources,
            _registry_schema(paths, "workflow.schema.json"),
            WorkflowReferenceData(
                skill_capabilities=(
                    project_workflow_skill_capabilities(
                        skill_sources
                    )
                ),
                artifact_statuses=project_artifact_statuses(
                    artifact_sources
                ),
            ),
        )
        _require_valid(
            "workflow registry",
            workflow_result.diagnostics,
        )

        profile_result = validate_profile_registry(
            profile_sources,
            _registry_schema(paths, "profile.schema.json"),
            ProfileReferenceData(
                workflows=project_workflow_names(workflow_sources),
                agent_profiles=project_profile_agent_names(
                    agent_sources
                ),
                skill_capabilities=(
                    project_profile_skill_capabilities(
                        skill_sources
                    )
                ),
            ),
        )
        _require_valid(
            "profile registry",
            profile_result.diagnostics,
        )

        target_names = project_target_names(target_sources)
        bundle_result = validate_bundle_registry(
            bundle_sources,
            _registry_schema(paths, "bundle.schema.json"),
            BundleReferenceData(
                profiles=project_profile_names(profile_sources),
                workflows=project_workflows(workflow_sources),
                agent_profiles=project_bundle_agent_names(
                    agent_sources
                ),
                skills=project_skills(skill_sources),
                artifact_contracts=project_artifact_contracts(
                    artifact_sources
                ),
                permission_profiles=project_bundle_permission_names(
                    permission_sources
                ),
                targets=target_names,
            ),
        )
        _require_valid(
            "bundle registry",
            bundle_result.diagnostics,
        )
    except (
        InfrastructureError,
        RegistryError,
        ValueError,
    ) as exc:
        raise RegistrySnapshotLoadError(str(exc)) from exc

    return ValidatedRegistrySnapshot(
        agents=agent_result.profiles,
        artifacts=artifact_result.contracts,
        bundles=bundle_result.bundles,
        permission_profiles=permission_result.profiles,
        profiles=profile_result.profiles,
        skills=skill_result.skills,
        workflows=workflow_result.workflows,
        targets=target_names,
    )


def _registry_schema(
    paths: ProjectPaths,
    filename: str,
) -> JsonObject:
    return read_json_object(
        paths.schema_root / "registry" / filename
    )


def _existing_skill_content_paths(
    skill_sources: tuple[RegistrySource, ...],
) -> frozenset[str]:
    existing_paths: set[str] = set()

    for source in skill_sources:
        content_path = source.data.get("contentPath")

        if not isinstance(content_path, str):
            continue

        resolved = source.source_path.parent / content_path

        if resolved.is_file():
            existing_paths.add(resolved.as_posix())

    return frozenset(existing_paths)


def _artifact_schema_snapshots(
    paths: ProjectPaths,
) -> tuple[ArtifactSchemaSnapshot, ...]:
    artifact_root = (
        paths.registry_root
        / RegistryKind.ARTIFACT.directory_name
    )

    return tuple(
        ArtifactSchemaSnapshot(
            source_path=path.relative_to(paths.root).as_posix(),
            canonical_json=serialize_json(read_json_object(path)),
        )
        for path in sorted(
            artifact_root.glob("*/artifact.schema.json"),
            key=lambda item: item.relative_to(
                paths.registry_root
            ).as_posix(),
        )
    )


def _require_valid(
    boundary: str,
    diagnostics: tuple[Diagnostic, ...],
) -> None:
    if diagnostics:
        raise RegistrySnapshotValidationError(
            boundary,
            diagnostics,
        )


def _lookup_identity(
    items: tuple[RegistryItemT, ...],
    identity: str,
    label: str,
    identity_of: object,
) -> RegistryItemT:
    if not callable(identity_of):
        raise TypeError("identity projection must be callable")

    for item in items:
        if identity_of(item) == identity:
            return item

    raise RegistrySnapshotLookupError(
        f"unknown {label} {identity!r}"
    )
