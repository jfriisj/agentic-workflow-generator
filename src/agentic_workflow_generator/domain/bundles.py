"""Concrete bundle-composition domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SharedContextPolicy(StrEnum):
    """Supported runtime context-sharing policies."""

    ASSIGNED_BINDINGS = "shared-with-assigned-bindings"


class RoleBindingType(StrEnum):
    """Supported authoritative role-binding types."""

    STATE_OWNER = "state-owner"
    WORKFLOW_CONTROLLER = "workflow-controller"


class SeparationMode(StrEnum):
    """Supported separation-policy modes."""

    REQUIRED = "required"


@dataclass(frozen=True, slots=True)
class ModelAssignment:
    """Explicit provider/model identity owned by one concrete agent instance."""

    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class AgentInstance:
    """Immutable concrete worker instantiated from an agent profile."""

    id: str
    profile: str
    display_name: str
    permission_profile: str
    shared_context_policy: SharedContextPolicy
    model_assignment: ModelAssignment | None = None


@dataclass(frozen=True, slots=True)
class InputArtifactReference:
    """Immutable governed dependency on one artifact-production relationship."""

    artifact_type: str
    role_binding: str


@dataclass(frozen=True, slots=True)
class RoleBinding:
    """Immutable authoritative workflow assignment.

    State ownership, selected skills, required capabilities and produced
    artifacts belong to this composition model rather than agent profiles.
    """

    role_name: str
    binding_type: RoleBindingType
    agent_instance: str
    required_capabilities: tuple[str, ...]
    selected_skills: tuple[str, ...]
    produces: tuple[str, ...]
    input_artifacts: tuple[InputArtifactReference, ...]
    responsibilities: tuple[str, ...]
    guardrails: tuple[str, ...]
    workflow_state: str | None
    workflow_gate: str | None


@dataclass(frozen=True, slots=True)
class SeparationPolicy:
    """Immutable bundle-specific independence requirement."""

    id: str
    mode: SeparationMode
    role_bindings: tuple[str, ...]
    require_distinct_instances: bool
    reason: str


@dataclass(frozen=True, slots=True)
class Bundle:
    """Immutable concrete composition of reusable registry definitions.

    Target-specific permission mapping and materialization deliberately do
    not belong to this model.
    """

    name: str
    description: str
    version: str
    profile: str
    workflow: str
    agent_instances: tuple[AgentInstance, ...]
    role_bindings: tuple[RoleBinding, ...]
    separation_policies: tuple[SeparationPolicy, ...]
    skills: tuple[str, ...]
    artifacts: tuple[str, ...]
    targets: tuple[str, ...]
