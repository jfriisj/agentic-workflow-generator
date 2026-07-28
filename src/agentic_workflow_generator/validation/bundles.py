"""Bundle-composition parsing, projection and semantic validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.domain.bundles import (
    AgentInstance,
    Bundle,
    RoleBinding,
    RoleBindingType,
    SeparationMode,
    SeparationPolicy,
    SharedContextPolicy,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.schema_support import (
    dot_path_registry_schema_diagnostics,
    dot_schema_error_location,
    dot_schema_error_message,
    dot_schema_error_sort_key,
    strict_missing_required_field,
)

SCHEMA_DIAGNOSTIC = "AWG-BUNDLE-001"
OBSOLETE_FIELD_DIAGNOSTIC = "AWG-BUNDLE-002"
FILE_NAME_DIAGNOSTIC = "AWG-BUNDLE-003"
DUPLICATE_BUNDLE_DIAGNOSTIC = "AWG-BUNDLE-004"
UNKNOWN_PROFILE_DIAGNOSTIC = "AWG-BUNDLE-005"
UNKNOWN_WORKFLOW_DIAGNOSTIC = "AWG-BUNDLE-006"
UNKNOWN_SKILL_DIAGNOSTIC = "AWG-BUNDLE-007"
UNKNOWN_ARTIFACT_DIAGNOSTIC = "AWG-BUNDLE-008"
UNKNOWN_TARGET_DIAGNOSTIC = "AWG-BUNDLE-009"
DUPLICATE_INSTANCE_DIAGNOSTIC = "AWG-BUNDLE-010"
UNKNOWN_AGENT_PROFILE_DIAGNOSTIC = "AWG-BUNDLE-011"
UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC = "AWG-BUNDLE-012"
UNASSIGNED_INSTANCE_DIAGNOSTIC = "AWG-BUNDLE-013"
DUPLICATE_ROLE_BINDING_DIAGNOSTIC = "AWG-BUNDLE-014"
UNKNOWN_INSTANCE_DIAGNOSTIC = "AWG-BUNDLE-015"
SKILL_OUTSIDE_BUNDLE_DIAGNOSTIC = "AWG-BUNDLE-016"
UNKNOWN_SELECTED_SKILL_DIAGNOSTIC = "AWG-BUNDLE-017"
UNPROVIDED_CAPABILITY_DIAGNOSTIC = "AWG-BUNDLE-018"
UNSATISFIED_SKILL_REQUIREMENT_DIAGNOSTIC = "AWG-BUNDLE-019"
ARTIFACT_OUTSIDE_BUNDLE_DIAGNOSTIC = "AWG-BUNDLE-020"
UNKNOWN_PRODUCED_ARTIFACT_DIAGNOSTIC = "AWG-BUNDLE-021"
WORKFLOW_STATE_DIAGNOSTIC = "AWG-BUNDLE-022"
DUPLICATE_STATE_OWNER_DIAGNOSTIC = "AWG-BUNDLE-023"
MISSING_STATE_OWNER_DIAGNOSTIC = "AWG-BUNDLE-024"
WORKFLOW_GATE_DIAGNOSTIC = "AWG-BUNDLE-025"
MISSING_GATE_CAPABILITY_DIAGNOSTIC = "AWG-BUNDLE-026"
MISSING_GATE_ARTIFACT_DIAGNOSTIC = "AWG-BUNDLE-027"
CONTROLLER_DIAGNOSTIC = "AWG-BUNDLE-028"
DUPLICATE_SEPARATION_POLICY_DIAGNOSTIC = "AWG-BUNDLE-029"
UNKNOWN_SEPARATION_BINDING_DIAGNOSTIC = "AWG-BUNDLE-030"
SEPARATION_INSTANCE_DIAGNOSTIC = "AWG-BUNDLE-031"
UNPRODUCED_BUNDLE_ARTIFACT_DIAGNOSTIC = "AWG-BUNDLE-032"
UNPRODUCED_CONTRACT_DIAGNOSTIC = "AWG-BUNDLE-033"

OBSOLETE_BUNDLE_FIELDS = frozenset(
    {
        "agents",
    }
)


@dataclass(frozen=True, slots=True)
class ProjectedSkill:
    """Minimal skill data required by bundle composition."""

    name: str
    provides: frozenset[str]
    requires: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProjectedWorkflowGate:
    """Minimal workflow-gate data required by role bindings."""

    name: str
    required_capabilities: frozenset[str]
    required_artifacts: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProjectedWorkflowState:
    """Minimal workflow-state data required by bundle ownership."""

    name: str
    terminal: bool
    gate: ProjectedWorkflowGate | None


@dataclass(frozen=True, slots=True)
class ProjectedWorkflow:
    """Minimal workflow surface required by bundle composition."""

    name: str
    states: tuple[ProjectedWorkflowState, ...]


@dataclass(frozen=True, slots=True)
class BundleReferenceData:
    """Validated external identities needed by bundle composition."""

    profiles: frozenset[str]
    workflows: tuple[ProjectedWorkflow, ...]
    agent_profiles: frozenset[str]
    skills: tuple[ProjectedSkill, ...]
    artifact_contracts: tuple[tuple[str, str], ...]
    permission_profiles: frozenset[str]
    targets: frozenset[str]


@dataclass(frozen=True, slots=True)
class BundleValidationResult:
    """Validated bundles and deterministic diagnostics."""

    bundles: tuple[Bundle, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedBundle:
    bundle: Bundle
    source_path: Path


class BundleDependencyProjectionError(ValueError):
    """Raised when dependency registry data cannot be projected."""


def project_profile_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project profile identities without treating recommendations as authority."""

    return _project_identity_names(
        sources,
        "name",
    )


def project_workflows(
    sources: Iterable[RegistrySource],
) -> tuple[ProjectedWorkflow, ...]:
    """Project workflow states and gates required by bundle ownership."""

    projected: dict[str, ProjectedWorkflow] = {}

    for source in sources:
        name = _project_string(
            source,
            "name",
        )
        _reject_duplicate_projection(
            source,
            name,
            projected,
        )

        raw_states = source.data.get("states")

        if not isinstance(raw_states, list) or not raw_states:
            raise BundleDependencyProjectionError(
                f"{source.source_path}: states must be a non-empty list"
            )

        states: list[ProjectedWorkflowState] = []

        for index, raw_state in enumerate(raw_states):
            label = f"states[{index}]"

            if not isinstance(raw_state, dict):
                raise BundleDependencyProjectionError(
                    f"{source.source_path}: {label} must be an object"
                )

            state_name = _project_nested_string(
                source,
                raw_state,
                "name",
                f"{label}.name",
            )
            terminal = raw_state.get("terminal") is True
            gate: ProjectedWorkflowGate | None = None

            if not terminal:
                raw_gate = raw_state.get("gate")

                if not isinstance(raw_gate, dict):
                    raise BundleDependencyProjectionError(
                        f"{source.source_path}: {label}.gate must be an object"
                    )

                gate = ProjectedWorkflowGate(
                    name=_project_nested_string(
                        source,
                        raw_gate,
                        "name",
                        f"{label}.gate.name",
                    ),
                    required_capabilities=frozenset(
                        _project_nested_string_list(
                            source,
                            raw_gate,
                            "requiredCapabilities",
                            (f"{label}.gate.requiredCapabilities"),
                        )
                    ),
                    required_artifacts=frozenset(
                        _project_nested_string_list(
                            source,
                            raw_gate,
                            "requiredArtifacts",
                            f"{label}.gate.requiredArtifacts",
                        )
                    ),
                )

            states.append(
                ProjectedWorkflowState(
                    name=state_name,
                    terminal=terminal,
                    gate=gate,
                )
            )

        projected[name] = ProjectedWorkflow(
            name=name,
            states=tuple(states),
        )

    return tuple(projected[name] for name in sorted(projected))


def project_agent_profile_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project reusable agent-profile identities only."""

    return _project_identity_names(
        sources,
        "name",
    )


def project_skills(
    sources: Iterable[RegistrySource],
) -> tuple[ProjectedSkill, ...]:
    """Project skill capability surfaces required by bindings."""

    projected: dict[str, ProjectedSkill] = {}

    for source in sources:
        name = _project_string(
            source,
            "name",
        )
        _reject_duplicate_projection(
            source,
            name,
            projected,
        )

        projected[name] = ProjectedSkill(
            name=name,
            provides=frozenset(
                _project_string_list(
                    source,
                    "provides",
                )
            ),
            requires=frozenset(
                _project_string_list(
                    source,
                    "requiresCapabilities",
                    allow_empty=True,
                )
            ),
        )

    return tuple(projected[name] for name in sorted(projected))


def project_artifact_contracts(
    sources: Iterable[RegistrySource],
) -> tuple[tuple[str, str], ...]:
    """Project artifact identities and their source paths."""

    projected: dict[str, str] = {}

    for source in sources:
        artifact_type = _project_string(
            source,
            "type",
        )
        _reject_duplicate_projection(
            source,
            artifact_type,
            projected,
        )
        projected[artifact_type] = source.source_path.as_posix()

    return tuple(sorted(projected.items()))


def project_permission_profile_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project permission-profile identities only."""

    return _project_identity_names(
        sources,
        "name",
    )


def project_target_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project target identities without validating target mappings."""

    return _project_identity_names(
        sources,
        "name",
    )


def validate_bundle_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    references: BundleReferenceData,
) -> BundleValidationResult:
    """Validate authoritative bundle composition without side effects."""

    validator = Draft202012Validator(
        cast(
            Mapping[str, Any],
            schema,
        )
    )
    parsed_bundles: list[_ParsedBundle] = []
    diagnostics: list[Diagnostic] = []
    fully_parsed = True

    for source in sources:
        obsolete_diagnostics = _validate_obsolete_fields(source)
        diagnostics.extend(obsolete_diagnostics)

        if obsolete_diagnostics:
            fully_parsed = False
            continue

        schema_diagnostics = _validate_schema(
            source,
            validator,
        )
        diagnostics.extend(schema_diagnostics)

        if schema_diagnostics:
            fully_parsed = False
            continue

        parsed = _parse_bundle(source)
        parsed_bundles.append(parsed)
        diagnostics.extend(
            _validate_bundle_semantics(
                parsed,
                references,
            )
        )

    diagnostics.extend(_validate_unique_bundle_names(parsed_bundles))

    if fully_parsed:
        diagnostics.extend(
            _validate_global_artifact_production(
                parsed_bundles,
                references,
            )
        )

    return BundleValidationResult(
        bundles=tuple(parsed.bundle for parsed in parsed_bundles),
        diagnostics=tuple(diagnostics),
    )


def _project_identity_names(
    sources: Iterable[RegistrySource],
    field: str,
) -> frozenset[str]:
    names: set[str] = set()

    for source in sources:
        name = _project_string(
            source,
            field,
        )

        if name in names:
            raise BundleDependencyProjectionError(
                f"{source.source_path}: {field} {name!r} is duplicated"
            )

        names.add(name)

    return frozenset(names)


def _project_string(
    source: RegistrySource,
    field: str,
) -> str:
    raw_value = source.data.get(field)

    if not isinstance(raw_value, str) or not raw_value.strip():
        raise BundleDependencyProjectionError(
            f"{source.source_path}: {field} must be a non-empty string"
        )

    return raw_value.strip()


def _project_string_list(
    source: RegistrySource,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    raw_values = source.data.get(field)

    if not isinstance(raw_values, list):
        raise BundleDependencyProjectionError(
            f"{source.source_path}: {field} must be a list"
        )

    if not raw_values and not allow_empty:
        raise BundleDependencyProjectionError(
            f"{source.source_path}: {field} must be a non-empty list"
        )

    values: list[str] = []

    for index, raw_value in enumerate(raw_values):
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise BundleDependencyProjectionError(
                f"{source.source_path}: {field}[{index}] must be a non-empty string"
            )

        values.append(raw_value.strip())

    return tuple(values)


def _project_nested_string(
    source: RegistrySource,
    data: Mapping[str, JsonValue],
    field: str,
    label: str,
) -> str:
    raw_value = data.get(field)

    if not isinstance(raw_value, str) or not raw_value.strip():
        raise BundleDependencyProjectionError(
            f"{source.source_path}: {label} must be a non-empty string"
        )

    return raw_value.strip()


def _project_nested_string_list(
    source: RegistrySource,
    data: Mapping[str, JsonValue],
    field: str,
    label: str,
) -> tuple[str, ...]:
    raw_values = data.get(field)

    if not isinstance(raw_values, list) or not raw_values:
        raise BundleDependencyProjectionError(
            f"{source.source_path}: {label} must be a non-empty list"
        )

    values: list[str] = []

    for index, raw_value in enumerate(raw_values):
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise BundleDependencyProjectionError(
                f"{source.source_path}: {label}[{index}] must be a non-empty string"
            )

        values.append(raw_value.strip())

    return tuple(values)


def _reject_duplicate_projection(
    source: RegistrySource,
    identity: str,
    projected: Mapping[str, object],
) -> None:
    if identity in projected:
        raise BundleDependencyProjectionError(
            f"{source.source_path}: identity {identity!r} is duplicated"
        )


def _validate_obsolete_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    fields = sorted(OBSOLETE_BUNDLE_FIELDS.intersection(source.data))

    return tuple(
        Diagnostic(
            code=OBSOLETE_FIELD_DIAGNOSTIC,
            message=(f"obsolete bundle field {field!r} is not allowed"),
            source_path=(source.source_path.as_posix()),
            location=field,
            related_identities=(field,),
        )
        for field in fields
    )


def _validate_schema(
    source: RegistrySource,
    validator: Draft202012Validator,
) -> tuple[Diagnostic, ...]:
    return dot_path_registry_schema_diagnostics(
        source,
        validator,
        SCHEMA_DIAGNOSTIC,
    )


def _schema_error_sort_key(
    error: ValidationError,
) -> tuple[str, str]:
    return dot_schema_error_sort_key(error)


def _schema_error_location(
    error: ValidationError,
) -> str:
    return dot_schema_error_location(error)


def _schema_error_message(
    error: ValidationError,
) -> str:
    return dot_schema_error_message(error)


def _missing_required_field(
    error: ValidationError,
) -> str:
    return strict_missing_required_field(error)


def _parse_bundle(
    source: RegistrySource,
) -> _ParsedBundle:
    raw_instances = cast(
        list[JsonObject],
        source.data["agentInstances"],
    )
    raw_bindings = cast(
        list[JsonObject],
        source.data["roleBindings"],
    )
    raw_policies = cast(
        list[JsonObject],
        source.data["separationPolicies"],
    )

    return _ParsedBundle(
        bundle=Bundle(
            name=cast(
                str,
                source.data["name"],
            ),
            description=cast(
                str,
                source.data["description"],
            ),
            version=cast(
                str,
                source.data["version"],
            ),
            profile=cast(
                str,
                source.data["profile"],
            ),
            workflow=cast(
                str,
                source.data["workflow"],
            ),
            agent_instances=tuple(
                AgentInstance(
                    id=cast(
                        str,
                        raw_instance["id"],
                    ),
                    profile=cast(
                        str,
                        raw_instance["profile"],
                    ),
                    display_name=cast(
                        str,
                        raw_instance["displayName"],
                    ),
                    permission_profile=cast(
                        str,
                        raw_instance["permissionProfile"],
                    ),
                    shared_context_policy=(
                        SharedContextPolicy(
                            cast(
                                str,
                                raw_instance["sharedContextPolicy"],
                            )
                        )
                    ),
                )
                for raw_instance in raw_instances
            ),
            role_bindings=tuple(
                _parse_role_binding(raw_binding) for raw_binding in raw_bindings
            ),
            separation_policies=tuple(
                SeparationPolicy(
                    id=cast(
                        str,
                        raw_policy["id"],
                    ),
                    mode=SeparationMode(
                        cast(
                            str,
                            raw_policy["mode"],
                        )
                    ),
                    role_bindings=_string_tuple(raw_policy["roleBindings"]),
                    require_distinct_instances=cast(
                        bool,
                        raw_policy["requireDistinctInstances"],
                    ),
                    reason=cast(
                        str,
                        raw_policy["reason"],
                    ),
                )
                for raw_policy in raw_policies
            ),
            skills=_string_tuple(source.data["skills"]),
            artifacts=_string_tuple(source.data["artifacts"]),
            targets=_string_tuple(source.data["targets"]),
        ),
        source_path=source.source_path,
    )


def _parse_role_binding(
    raw_binding: JsonObject,
) -> RoleBinding:
    return RoleBinding(
        role_name=cast(
            str,
            raw_binding["roleName"],
        ),
        binding_type=RoleBindingType(
            cast(
                str,
                raw_binding["bindingType"],
            )
        ),
        agent_instance=cast(
            str,
            raw_binding["agentInstance"],
        ),
        required_capabilities=_string_tuple(raw_binding["requiredCapabilities"]),
        selected_skills=_string_tuple(raw_binding["selectedSkills"]),
        produces=_string_tuple(raw_binding["produces"]),
        responsibilities=_string_tuple(raw_binding["responsibilities"]),
        guardrails=_string_tuple(raw_binding["guardrails"]),
        workflow_state=cast(
            str | None,
            raw_binding.get("workflowState"),
        ),
        workflow_gate=cast(
            str | None,
            raw_binding.get("workflowGate"),
        ),
    )


def _string_tuple(
    value: JsonValue,
) -> tuple[str, ...]:
    return tuple(
        cast(
            list[str],
            value,
        )
    )


def _validate_bundle_semantics(
    parsed: _ParsedBundle,
    references: BundleReferenceData,
) -> tuple[Diagnostic, ...]:
    bundle = parsed.bundle
    path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    expected_name = path.name.removesuffix(".bundle.json")
    workflows = {workflow.name: workflow for workflow in references.workflows}
    skills = {skill.name: skill for skill in references.skills}
    artifact_types = {
        artifact_type for artifact_type, _source_path in references.artifact_contracts
    }

    if bundle.name != expected_name:
        diagnostics.append(
            _diagnostic(
                FILE_NAME_DIAGNOSTIC,
                (f"name {bundle.name!r} does not match file name {expected_name!r}"),
                path,
                "name",
                bundle.name,
                expected_name,
            )
        )

    if bundle.profile not in references.profiles:
        diagnostics.append(
            _diagnostic(
                UNKNOWN_PROFILE_DIAGNOSTIC,
                (f"profile {bundle.profile!r} is not registered"),
                path,
                "profile",
                bundle.profile,
            )
        )

    workflow = workflows.get(bundle.workflow)

    if workflow is None:
        diagnostics.append(
            _diagnostic(
                UNKNOWN_WORKFLOW_DIAGNOSTIC,
                (f"workflow {bundle.workflow!r} is not registered"),
                path,
                "workflow",
                bundle.workflow,
            )
        )

    diagnostics.extend(
        _validate_bundle_references(
            bundle,
            path,
            references,
            skills,
            artifact_types,
        )
    )
    diagnostics.extend(
        _validate_composition(
            bundle,
            path,
            references,
            workflow,
            skills,
            artifact_types,
        )
    )

    return tuple(diagnostics)


def _validate_bundle_references(
    bundle: Bundle,
    path: Path,
    references: BundleReferenceData,
    skills: Mapping[str, ProjectedSkill],
    artifact_types: set[str],
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []

    for index, skill_name in enumerate(bundle.skills):
        if skill_name not in skills:
            diagnostics.append(
                _diagnostic(
                    UNKNOWN_SKILL_DIAGNOSTIC,
                    (f"skill {skill_name!r} is not registered"),
                    path,
                    f"skills[{index}]",
                    skill_name,
                )
            )

    for index, artifact_type in enumerate(bundle.artifacts):
        if artifact_type not in artifact_types:
            diagnostics.append(
                _diagnostic(
                    UNKNOWN_ARTIFACT_DIAGNOSTIC,
                    (f"artifact {artifact_type!r} is not registered"),
                    path,
                    f"artifacts[{index}]",
                    artifact_type,
                )
            )

    for index, target_name in enumerate(bundle.targets):
        if target_name not in references.targets:
            diagnostics.append(
                _diagnostic(
                    UNKNOWN_TARGET_DIAGNOSTIC,
                    (f"target {target_name!r} is not registered"),
                    path,
                    f"targets[{index}]",
                    target_name,
                )
            )

    return tuple(diagnostics)


def _validate_composition(
    bundle: Bundle,
    path: Path,
    references: BundleReferenceData,
    workflow: ProjectedWorkflow | None,
    skills: Mapping[str, ProjectedSkill],
    artifact_types: set[str],
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    instances: dict[str, AgentInstance] = {}

    for index, instance in enumerate(bundle.agent_instances):
        location = f"agentInstances[{index}]"

        if instance.id in instances:
            diagnostics.append(
                _diagnostic(
                    DUPLICATE_INSTANCE_DIAGNOSTIC,
                    (f"agent instance id {instance.id!r} is duplicated"),
                    path,
                    f"{location}.id",
                    instance.id,
                )
            )
        else:
            instances[instance.id] = instance

        if instance.profile not in references.agent_profiles:
            diagnostics.append(
                _diagnostic(
                    UNKNOWN_AGENT_PROFILE_DIAGNOSTIC,
                    (f"agent profile {instance.profile!r} is not registered"),
                    path,
                    f"{location}.profile",
                    instance.profile,
                )
            )

        if instance.permission_profile not in references.permission_profiles:
            diagnostics.append(
                _diagnostic(
                    (UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC),
                    (
                        f"permission profile "
                        f"{instance.permission_profile!r} "
                        "is not registered"
                    ),
                    path,
                    (f"{location}.permissionProfile"),
                    instance.permission_profile,
                )
            )

    (
        binding_diagnostics,
        bindings,
        assigned_instances,
        produced_artifacts,
    ) = _validate_role_bindings(
        bundle,
        path,
        instances,
        workflow,
        skills,
        artifact_types,
    )
    diagnostics.extend(binding_diagnostics)

    for instance_id in sorted(set(instances) - assigned_instances):
        diagnostics.append(
            _diagnostic(
                UNASSIGNED_INSTANCE_DIAGNOSTIC,
                (f"agent instance {instance_id!r} is not assigned to a role binding"),
                path,
                "agentInstances",
                instance_id,
            )
        )

    diagnostics.extend(
        _validate_separation_policies(
            bundle,
            path,
            bindings,
        )
    )

    known_bundle_artifacts = set(bundle.artifacts) & artifact_types

    for artifact_type in sorted(known_bundle_artifacts - produced_artifacts):
        diagnostics.append(
            _diagnostic(
                (UNPRODUCED_BUNDLE_ARTIFACT_DIAGNOSTIC),
                (
                    f"bundle artifact {artifact_type!r} "
                    "is not produced by a "
                    "state-owner binding"
                ),
                path,
                "artifacts",
                artifact_type,
            )
        )

    return tuple(diagnostics)


def _validate_role_bindings(
    bundle: Bundle,
    path: Path,
    instances: Mapping[str, AgentInstance],
    workflow: ProjectedWorkflow | None,
    skills: Mapping[str, ProjectedSkill],
    artifact_types: set[str],
) -> tuple[
    tuple[Diagnostic, ...],
    dict[str, RoleBinding],
    set[str],
    set[str],
]:
    diagnostics: list[Diagnostic] = []
    bindings: dict[str, RoleBinding] = {}
    assigned_instances: set[str] = set()
    produced_artifacts: set[str] = set()
    state_owners: dict[str, str] = {}
    controller_count = 0
    bundle_skills = set(bundle.skills)
    bundle_artifacts = set(bundle.artifacts)
    workflow_states = (
        {state.name: state for state in workflow.states} if workflow is not None else {}
    )

    for index, binding in enumerate(bundle.role_bindings):
        location = f"roleBindings[{index}]"

        if binding.role_name in bindings:
            diagnostics.append(
                _diagnostic(
                    (DUPLICATE_ROLE_BINDING_DIAGNOSTIC),
                    (f"role binding {binding.role_name!r} is duplicated"),
                    path,
                    f"{location}.roleName",
                    binding.role_name,
                )
            )
        else:
            bindings[binding.role_name] = binding

        if binding.agent_instance not in instances:
            diagnostics.append(
                _diagnostic(
                    UNKNOWN_INSTANCE_DIAGNOSTIC,
                    (
                        f"agent instance "
                        f"{binding.agent_instance!r} "
                        "is not declared by the bundle"
                    ),
                    path,
                    f"{location}.agentInstance",
                    binding.agent_instance,
                )
            )
        else:
            assigned_instances.add(binding.agent_instance)

        provided_capabilities: set[str] = set()
        required_by_skills: set[str] = set()

        for skill_index, skill_name in enumerate(binding.selected_skills):
            skill_location = f"{location}.selectedSkills[{skill_index}]"

            if skill_name not in bundle_skills:
                diagnostics.append(
                    _diagnostic(
                        (SKILL_OUTSIDE_BUNDLE_DIAGNOSTIC),
                        (
                            f"selected skill "
                            f"{skill_name!r} is not "
                            "included in bundle skills"
                        ),
                        path,
                        skill_location,
                        binding.role_name,
                        skill_name,
                    )
                )

            skill = skills.get(skill_name)

            if skill is None:
                diagnostics.append(
                    _diagnostic(
                        (UNKNOWN_SELECTED_SKILL_DIAGNOSTIC),
                        (f"selected skill {skill_name!r} is not registered"),
                        path,
                        skill_location,
                        binding.role_name,
                        skill_name,
                    )
                )
                continue

            provided_capabilities.update(skill.provides)
            required_by_skills.update(skill.requires)

        for capability_index, capability in enumerate(binding.required_capabilities):
            if capability not in provided_capabilities:
                diagnostics.append(
                    _diagnostic(
                        (UNPROVIDED_CAPABILITY_DIAGNOSTIC),
                        (
                            f"required capability "
                            f"{capability!r} is not "
                            "provided by selected skills"
                        ),
                        path,
                        (f"{location}.requiredCapabilities[{capability_index}]"),
                        binding.role_name,
                        capability,
                    )
                )

        for capability in sorted(required_by_skills - provided_capabilities):
            diagnostics.append(
                _diagnostic(
                    (UNSATISFIED_SKILL_REQUIREMENT_DIAGNOSTIC),
                    (
                        f"selected skills require "
                        f"capability {capability!r} "
                        "not provided by the same "
                        "binding's selected skills"
                    ),
                    path,
                    f"{location}.selectedSkills",
                    binding.role_name,
                    capability,
                )
            )

        for artifact_index, artifact_type in enumerate(binding.produces):
            artifact_location = f"{location}.produces[{artifact_index}]"

            if artifact_type not in bundle_artifacts:
                diagnostics.append(
                    _diagnostic(
                        (ARTIFACT_OUTSIDE_BUNDLE_DIAGNOSTIC),
                        (
                            f"produced artifact "
                            f"{artifact_type!r} is not "
                            "included in bundle artifacts"
                        ),
                        path,
                        artifact_location,
                        binding.role_name,
                        artifact_type,
                    )
                )

            if artifact_type not in artifact_types:
                diagnostics.append(
                    _diagnostic(
                        (UNKNOWN_PRODUCED_ARTIFACT_DIAGNOSTIC),
                        (f"produced artifact {artifact_type!r} is not registered"),
                        path,
                        artifact_location,
                        binding.role_name,
                        artifact_type,
                    )
                )

        if binding.binding_type is RoleBindingType.STATE_OWNER:
            produced_artifacts.update(binding.produces)

            if workflow is not None:
                diagnostics.extend(
                    _validate_state_owner(
                        binding,
                        path,
                        location,
                        workflow_states,
                        state_owners,
                    )
                )
        else:
            controller_count += 1

            if binding.produces:
                diagnostics.append(
                    _diagnostic(
                        CONTROLLER_DIAGNOSTIC,
                        ("workflow-controller must not produce artifacts"),
                        path,
                        f"{location}.produces",
                        binding.role_name,
                    )
                )

    if workflow is not None:
        non_terminal_states = {
            state.name for state in workflow.states if not state.terminal
        }

        for state_name in sorted(non_terminal_states - set(state_owners)):
            diagnostics.append(
                _diagnostic(
                    MISSING_STATE_OWNER_DIAGNOSTIC,
                    (f"workflow state {state_name!r} has no state-owner binding"),
                    path,
                    "roleBindings",
                    workflow.name,
                    state_name,
                )
            )

    if controller_count != 1:
        diagnostics.append(
            _diagnostic(
                CONTROLLER_DIAGNOSTIC,
                (
                    "bundle must declare exactly one "
                    "workflow-controller binding, "
                    f"found {controller_count}"
                ),
                path,
                "roleBindings",
                bundle.name,
            )
        )

    return (
        tuple(diagnostics),
        bindings,
        assigned_instances,
        produced_artifacts,
    )


def _validate_state_owner(
    binding: RoleBinding,
    path: Path,
    location: str,
    workflow_states: Mapping[
        str,
        ProjectedWorkflowState,
    ],
    state_owners: dict[str, str],
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    state_name = cast(
        str,
        binding.workflow_state,
    )
    state = workflow_states.get(state_name)

    if state is None:
        diagnostics.append(
            _diagnostic(
                WORKFLOW_STATE_DIAGNOSTIC,
                (
                    f"workflow state {state_name!r} "
                    "is not declared by the "
                    "selected workflow"
                ),
                path,
                f"{location}.workflowState",
                binding.role_name,
                state_name,
            )
        )
        return tuple(diagnostics)

    if state.terminal:
        diagnostics.append(
            _diagnostic(
                WORKFLOW_STATE_DIAGNOSTIC,
                (
                    f"terminal workflow state "
                    f"{state_name!r} must not have "
                    "a state-owner binding"
                ),
                path,
                f"{location}.workflowState",
                binding.role_name,
                state_name,
            )
        )
        return tuple(diagnostics)

    first_owner = state_owners.get(state_name)

    if first_owner is not None:
        diagnostics.append(
            _diagnostic(
                (DUPLICATE_STATE_OWNER_DIAGNOSTIC),
                (f"workflow state {state_name!r} has multiple state-owner bindings"),
                path,
                f"{location}.workflowState",
                state_name,
                first_owner,
                binding.role_name,
            )
        )
    else:
        state_owners[state_name] = binding.role_name

    gate = cast(
        ProjectedWorkflowGate,
        state.gate,
    )

    if binding.workflow_gate != gate.name:
        diagnostics.append(
            _diagnostic(
                WORKFLOW_GATE_DIAGNOSTIC,
                (
                    f"workflowGate "
                    f"{binding.workflow_gate!r} "
                    "does not match workflow state "
                    f"{state_name!r} gate "
                    f"{gate.name!r}"
                ),
                path,
                f"{location}.workflowGate",
                binding.role_name,
                state_name,
                gate.name,
            )
        )

    missing_capabilities = gate.required_capabilities - set(
        binding.required_capabilities
    )

    for capability in sorted(missing_capabilities):
        diagnostics.append(
            _diagnostic(
                (MISSING_GATE_CAPABILITY_DIAGNOSTIC),
                (f"binding does not require gate capability {capability!r}"),
                path,
                (f"{location}.requiredCapabilities"),
                binding.role_name,
                capability,
            )
        )

    missing_artifacts = gate.required_artifacts - set(binding.produces)

    for artifact_type in sorted(missing_artifacts):
        diagnostics.append(
            _diagnostic(
                (MISSING_GATE_ARTIFACT_DIAGNOSTIC),
                (f"binding does not produce gate artifact {artifact_type!r}"),
                path,
                f"{location}.produces",
                binding.role_name,
                artifact_type,
            )
        )

    return tuple(diagnostics)


def _validate_separation_policies(
    bundle: Bundle,
    path: Path,
    bindings: Mapping[str, RoleBinding],
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    seen_policy_ids: set[str] = set()

    for index, policy in enumerate(bundle.separation_policies):
        location = f"separationPolicies[{index}]"

        if policy.id in seen_policy_ids:
            diagnostics.append(
                _diagnostic(
                    (DUPLICATE_SEPARATION_POLICY_DIAGNOSTIC),
                    (f"separation policy id {policy.id!r} is duplicated"),
                    path,
                    f"{location}.id",
                    policy.id,
                )
            )
        else:
            seen_policy_ids.add(policy.id)

        instance_ids: list[str] = []

        for role_index, role_name in enumerate(policy.role_bindings):
            binding = bindings.get(role_name)

            if binding is None:
                diagnostics.append(
                    _diagnostic(
                        (UNKNOWN_SEPARATION_BINDING_DIAGNOSTIC),
                        (
                            "separation policy references "
                            "missing role binding "
                            f"{role_name!r}"
                        ),
                        path,
                        (f"{location}.roleBindings[{role_index}]"),
                        policy.id,
                        role_name,
                    )
                )
                continue

            instance_ids.append(binding.agent_instance)

        if len(instance_ids) != len(set(instance_ids)):
            diagnostics.append(
                _diagnostic(
                    (SEPARATION_INSTANCE_DIAGNOSTIC),
                    (
                        "separation policy requires "
                        "distinct agent instances but "
                        "constrained bindings share "
                        "an instance"
                    ),
                    path,
                    f"{location}.roleBindings",
                    policy.id,
                )
            )

    return tuple(diagnostics)


def _validate_unique_bundle_names(
    parsed_bundles: list[_ParsedBundle],
) -> tuple[Diagnostic, ...]:
    seen: dict[str, Path] = {}
    diagnostics: list[Diagnostic] = []

    for parsed in parsed_bundles:
        name = parsed.bundle.name
        first_path = seen.get(name)

        if first_path is None:
            seen[name] = parsed.source_path
            continue

        diagnostics.append(
            _diagnostic(
                DUPLICATE_BUNDLE_DIAGNOSTIC,
                (
                    f"bundle name {name!r} "
                    "is duplicated; first declared "
                    f"at {first_path.as_posix()}"
                ),
                parsed.source_path,
                "name",
                name,
            )
        )

    return tuple(diagnostics)


def _validate_global_artifact_production(
    parsed_bundles: list[_ParsedBundle],
    references: BundleReferenceData,
) -> tuple[Diagnostic, ...]:
    produced = {
        artifact_type
        for parsed in parsed_bundles
        for binding in parsed.bundle.role_bindings
        if (binding.binding_type is RoleBindingType.STATE_OWNER)
        for artifact_type in binding.produces
    }
    diagnostics: list[Diagnostic] = []

    for (
        artifact_type,
        source_path,
    ) in references.artifact_contracts:
        if artifact_type in produced:
            continue

        diagnostics.append(
            Diagnostic(
                code=(UNPRODUCED_CONTRACT_DIAGNOSTIC),
                message=(
                    f"artifact contract "
                    f"{artifact_type!r} requires "
                    "a producer but is not produced "
                    "by any state-owner binding"
                ),
                source_path=source_path,
                location="type",
                related_identities=(artifact_type,),
            )
        )

    return tuple(diagnostics)


def _diagnostic(
    code: str,
    message: str,
    path: Path,
    location: str,
    *identities: str,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        source_path=path.as_posix(),
        location=location,
        related_identities=(_unique_identities(identities)),
    )


def _unique_identities(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
