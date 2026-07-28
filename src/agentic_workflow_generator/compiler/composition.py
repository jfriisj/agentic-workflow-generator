"""Canonical typed compiled composition."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from agentic_workflow_generator.domain import (
    AgentInstance,
    AgentProfile,
    ArtifactContract,
    Bundle,
    PermissionProfile,
    Profile,
    RoleBinding,
    RoleBindingType,
    SeparationMode,
    SeparationPolicy,
    SharedContextPolicy,
    Skill,
    Workflow,
)


class CompositionError(ValueError):
    """Raised when validated registry input cannot be compiled."""


class CompositionRegistry(Protocol):
    """Typed lookup surface required by composition compilation."""

    @property
    def targets(self) -> frozenset[str]:
        """Return all registered target identities."""

        ...

    def agent_by_name(self, name: str) -> AgentProfile: ...

    def artifact_by_type(
        self,
        artifact_type: str,
    ) -> ArtifactContract: ...

    def bundle_by_name(self, name: str) -> Bundle: ...

    def permission_profile_by_name(
        self,
        name: str,
    ) -> PermissionProfile: ...

    def profile_by_name(self, name: str) -> Profile: ...

    def skill_by_name(self, name: str) -> Skill: ...

    def workflow_by_name(self, name: str) -> Workflow: ...


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """Project-specific metadata preserved in active configuration."""

    name: str
    project_type: str
    description: str
    language_profiles: tuple[str, ...]
    runtime_profiles: tuple[str, ...]
    architecture_profile: str


@dataclass(frozen=True, slots=True)
class CompiledTarget:
    """One enabled target with deterministic priority."""

    name: str
    priority: int


@dataclass(frozen=True, slots=True)
class CompiledRoleBinding:
    """Resolved authoritative runtime role assignment."""

    role_name: str
    binding_type: RoleBindingType
    agent_instance: str
    workflow_state: str | None
    workflow_gate: str | None
    required_capabilities: tuple[str, ...]
    selected_skills: tuple[Skill, ...]
    provided_capabilities: tuple[str, ...]
    produces: tuple[ArtifactContract, ...]
    responsibilities: tuple[str, ...]
    guardrails: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompiledAgentInstance:
    """Resolved concrete worker with effective binding requirements."""

    id: str
    profile: AgentProfile
    display_name: str
    permission_profile: PermissionProfile
    shared_context_policy: SharedContextPolicy
    role_bindings: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    selected_skills: tuple[Skill, ...]
    produces: tuple[ArtifactContract, ...]
    responsibilities: tuple[str, ...]
    guardrails: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompiledStateOwnership:
    """Resolved owner of one non-terminal workflow state."""

    workflow_state: str
    role_binding: str
    agent_instance: str


@dataclass(frozen=True, slots=True)
class CompiledWorkflowGate:
    """Resolved workflow gate and its authoritative owner."""

    workflow_state: str
    name: str
    blocking: bool
    owner_role_binding: str
    owner_agent_instance: str
    required_capabilities: tuple[str, ...]
    required_artifacts: tuple[ArtifactContract, ...]


@dataclass(frozen=True, slots=True)
class CompiledArtifactProduction:
    """Resolved artifact production ownership."""

    artifact: ArtifactContract
    role_binding: str
    agent_instance: str


@dataclass(frozen=True, slots=True)
class CompiledSeparationConstraint:
    """Resolved separation-of-duties constraint."""

    id: str
    mode: SeparationMode
    role_bindings: tuple[str, ...]
    agent_instances: tuple[str, ...]
    require_distinct_instances: bool
    reason: str


@dataclass(frozen=True, slots=True)
class CompiledComposition:
    """Canonical resolved runtime authority for one selected bundle."""

    project: ProjectMetadata
    bundle: str
    bundle_version: str
    profile: Profile
    workflow: Workflow
    targets: tuple[CompiledTarget, ...]
    agent_instances: tuple[CompiledAgentInstance, ...]
    role_bindings: tuple[CompiledRoleBinding, ...]
    state_ownership: tuple[CompiledStateOwnership, ...]
    controller_binding: str
    permission_profiles: tuple[PermissionProfile, ...]
    skills: tuple[Skill, ...]
    artifacts: tuple[ArtifactContract, ...]
    workflow_gates: tuple[CompiledWorkflowGate, ...]
    artifact_production: tuple[CompiledArtifactProduction, ...]
    separation_constraints: tuple[CompiledSeparationConstraint, ...]


RegistryItemT = TypeVar("RegistryItemT")


def compile_bundle_composition(
    registry: CompositionRegistry,
    project: ProjectMetadata,
    bundle_name: str,
    selected_targets: Iterable[str] | None = None,
) -> CompiledComposition:
    """Compile one validated bundle into canonical runtime authority."""

    bundle = registry.bundle_by_name(bundle_name)
    profile = registry.profile_by_name(bundle.profile)
    workflow = registry.workflow_by_name(bundle.workflow)
    targets = _compile_targets(
        registry,
        bundle,
        selected_targets,
    )
    skills = tuple(
        registry.skill_by_name(name)
        for name in bundle.skills
    )
    artifacts = tuple(
        registry.artifact_by_type(artifact_type)
        for artifact_type in bundle.artifacts
    )
    bindings = tuple(
        _compile_binding(registry, binding)
        for binding in bundle.role_bindings
    )
    instances = tuple(
        _compile_instance(
            registry,
            instance,
            bindings,
        )
        for instance in bundle.agent_instances
    )
    state_ownership = tuple(
        CompiledStateOwnership(
            workflow_state=_required(
                binding.workflow_state,
                "workflow state",
            ),
            role_binding=binding.role_name,
            agent_instance=binding.agent_instance,
        )
        for binding in bindings
        if binding.binding_type is RoleBindingType.STATE_OWNER
    )
    controller_bindings = tuple(
        binding
        for binding in bindings
        if binding.binding_type
        is RoleBindingType.WORKFLOW_CONTROLLER
    )

    if len(controller_bindings) != 1:
        raise CompositionError(
            "compiled composition requires exactly one "
            "workflow controller"
        )

    workflow_gates = _compile_workflow_gates(
        registry,
        workflow,
        bindings,
    )
    artifact_production = tuple(
        CompiledArtifactProduction(
            artifact=artifact,
            role_binding=binding.role_name,
            agent_instance=binding.agent_instance,
        )
        for binding in bindings
        for artifact in binding.produces
    )
    separation_constraints = tuple(
        _compile_separation_constraint(
            policy,
            bindings,
        )
        for policy in bundle.separation_policies
    )
    effective_permissions = _unique_by_identity(
        (
            instance.permission_profile
            for instance in instances
        ),
        lambda item: item.name,
    )

    return CompiledComposition(
        project=project,
        bundle=bundle.name,
        bundle_version=bundle.version,
        profile=profile,
        workflow=workflow,
        targets=targets,
        agent_instances=instances,
        role_bindings=bindings,
        state_ownership=state_ownership,
        controller_binding=(
            controller_bindings[0].role_name
        ),
        permission_profiles=effective_permissions,
        skills=skills,
        artifacts=artifacts,
        workflow_gates=workflow_gates,
        artifact_production=artifact_production,
        separation_constraints=separation_constraints,
    )


def _compile_targets(
    registry: CompositionRegistry,
    bundle: Bundle,
    selected_targets: Iterable[str] | None,
) -> tuple[CompiledTarget, ...]:
    names = (
        tuple(selected_targets)
        if selected_targets is not None
        else bundle.targets
    )

    if not names:
        raise CompositionError(
            "compiled composition requires at least one target"
        )

    if len(set(names)) != len(names):
        raise CompositionError(
            "selected targets must be unique"
        )

    outside_bundle = tuple(
        name
        for name in names
        if name not in bundle.targets
    )

    if outside_bundle:
        raise CompositionError(
            "selected targets are not included in bundle "
            f"{bundle.name!r}: {outside_bundle}"
        )

    unknown = tuple(
        name
        for name in names
        if name not in registry.targets
    )

    if unknown:
        raise CompositionError(
            f"selected targets are not registered: {unknown}"
        )

    return tuple(
        CompiledTarget(
            name=name,
            priority=index,
        )
        for index, name in enumerate(names, start=1)
    )


def _compile_binding(
    registry: CompositionRegistry,
    binding: RoleBinding,
) -> CompiledRoleBinding:
    selected_skills = tuple(
        registry.skill_by_name(name)
        for name in binding.selected_skills
    )
    produces = tuple(
        registry.artifact_by_type(artifact_type)
        for artifact_type in binding.produces
    )

    return CompiledRoleBinding(
        role_name=binding.role_name,
        binding_type=binding.binding_type,
        agent_instance=binding.agent_instance,
        workflow_state=binding.workflow_state,
        workflow_gate=binding.workflow_gate,
        required_capabilities=(
            binding.required_capabilities
        ),
        selected_skills=selected_skills,
        provided_capabilities=_ordered_unique(
            capability
            for skill in selected_skills
            for capability in skill.provides
        ),
        produces=produces,
        responsibilities=binding.responsibilities,
        guardrails=binding.guardrails,
    )


def _compile_instance(
    registry: CompositionRegistry,
    instance: AgentInstance,
    bindings: tuple[CompiledRoleBinding, ...],
) -> CompiledAgentInstance:
    assigned = tuple(
        binding
        for binding in bindings
        if binding.agent_instance == instance.id
    )

    if not assigned:
        raise CompositionError(
            f"agent instance {instance.id!r} "
            "has no role bindings"
        )

    return CompiledAgentInstance(
        id=instance.id,
        profile=registry.agent_by_name(
            instance.profile
        ),
        display_name=instance.display_name,
        permission_profile=(
            registry.permission_profile_by_name(
                instance.permission_profile
            )
        ),
        shared_context_policy=(
            instance.shared_context_policy
        ),
        role_bindings=tuple(
            binding.role_name
            for binding in assigned
        ),
        required_capabilities=_ordered_unique(
            capability
            for binding in assigned
            for capability
            in binding.required_capabilities
        ),
        selected_skills=_unique_by_identity(
            (
                skill
                for binding in assigned
                for skill in binding.selected_skills
            ),
            lambda item: item.name,
        ),
        produces=_unique_by_identity(
            (
                artifact
                for binding in assigned
                for artifact in binding.produces
            ),
            lambda item: item.type,
        ),
        responsibilities=_ordered_unique(
            responsibility
            for binding in assigned
            for responsibility
            in binding.responsibilities
        ),
        guardrails=_ordered_unique(
            guardrail
            for binding in assigned
            for guardrail in binding.guardrails
        ),
    )


def _compile_workflow_gates(
    registry: CompositionRegistry,
    workflow: Workflow,
    bindings: tuple[CompiledRoleBinding, ...],
) -> tuple[CompiledWorkflowGate, ...]:
    owners = {
        _required(
            binding.workflow_state,
            "workflow state",
        ): binding
        for binding in bindings
        if binding.binding_type
        is RoleBindingType.STATE_OWNER
    }
    compiled: list[CompiledWorkflowGate] = []

    for state in workflow.states:
        if state.terminal:
            continue

        if state.gate is None:
            raise CompositionError(
                "non-terminal workflow state "
                f"{state.name!r} has no gate"
            )

        try:
            owner = owners[state.name]
        except KeyError as exc:
            raise CompositionError(
                "workflow state "
                f"{state.name!r} has no compiled owner"
            ) from exc

        compiled.append(
            CompiledWorkflowGate(
                workflow_state=state.name,
                name=state.gate.name,
                blocking=state.gate.blocking,
                owner_role_binding=(
                    owner.role_name
                ),
                owner_agent_instance=(
                    owner.agent_instance
                ),
                required_capabilities=(
                    state.gate.required_capabilities
                ),
                required_artifacts=tuple(
                    registry.artifact_by_type(
                        artifact_type
                    )
                    for artifact_type
                    in state.gate.required_artifacts
                ),
            )
        )

    return tuple(compiled)


def _compile_separation_constraint(
    policy: SeparationPolicy,
    bindings: tuple[CompiledRoleBinding, ...],
) -> CompiledSeparationConstraint:
    by_name = {
        binding.role_name: binding
        for binding in bindings
    }

    try:
        instances = tuple(
            by_name[role_name].agent_instance
            for role_name in policy.role_bindings
        )
    except KeyError as exc:
        raise CompositionError(
            "separation policy "
            f"{policy.id!r} references "
            "unknown role binding"
        ) from exc

    if (
        policy.require_distinct_instances
        and len(set(instances)) != len(instances)
    ):
        raise CompositionError(
            "separation policy "
            f"{policy.id!r} requires "
            "distinct instances"
        )

    return CompiledSeparationConstraint(
        id=policy.id,
        mode=policy.mode,
        role_bindings=policy.role_bindings,
        agent_instances=instances,
        require_distinct_instances=(
            policy.require_distinct_instances
        ),
        reason=policy.reason,
    )


def _required(
    value: str | None,
    label: str,
) -> str:
    if value is None:
        raise CompositionError(
            f"compiled {label} must not be missing"
        )

    return value


def _ordered_unique(
    values: Iterable[str],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _unique_by_identity(
    values: Iterable[RegistryItemT],
    identity_of: Callable[
        [RegistryItemT],
        str,
    ],
) -> tuple[RegistryItemT, ...]:
    unique: dict[str, RegistryItemT] = {}

    for value in values:
        unique.setdefault(
            identity_of(value),
            value,
        )

    return tuple(unique.values())
