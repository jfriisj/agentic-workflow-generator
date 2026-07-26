"""Workflow parsing, projection and semantic validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.domain.workflows import (
    Workflow,
    WorkflowGate,
    WorkflowState,
    WorkflowTransition,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.pipeline_support import (
    validate_and_parse_sources,
)
from agentic_workflow_generator.validation.schema_support import (
    dot_path_registry_schema_diagnostics,
    dot_schema_error_location,
    dot_schema_error_message,
    dot_schema_error_sort_key,
    strict_missing_required_field,
)

SCHEMA_DIAGNOSTIC = "AWG-WORKFLOW-001"
LEGACY_FIELD_DIAGNOSTIC = "AWG-WORKFLOW-002"
FILE_NAME_DIAGNOSTIC = "AWG-WORKFLOW-003"
DUPLICATE_WORKFLOW_DIAGNOSTIC = "AWG-WORKFLOW-004"
DUPLICATE_STATE_DIAGNOSTIC = "AWG-WORKFLOW-005"
DUPLICATE_GATE_DIAGNOSTIC = "AWG-WORKFLOW-006"
FAIL_CLOSED_DIAGNOSTIC = "AWG-WORKFLOW-007"
START_STATE_DIAGNOSTIC = "AWG-WORKFLOW-008"
TERMINAL_STATE_DIAGNOSTIC = "AWG-WORKFLOW-009"
DEFAULT_FAILURE_STATE_DIAGNOSTIC = "AWG-WORKFLOW-010"
UNKNOWN_CAPABILITY_DIAGNOSTIC = "AWG-WORKFLOW-011"
UNKNOWN_ARTIFACT_DIAGNOSTIC = "AWG-WORKFLOW-012"
TRANSITION_ENDPOINT_DIAGNOSTIC = "AWG-WORKFLOW-013"
TERMINAL_OUTGOING_DIAGNOSTIC = "AWG-WORKFLOW-014"
DUPLICATE_EVENT_DIAGNOSTIC = "AWG-WORKFLOW-015"
MISSING_OUTGOING_DIAGNOSTIC = "AWG-WORKFLOW-016"
UNREACHABLE_STATE_DIAGNOSTIC = "AWG-WORKFLOW-017"
NO_TERMINAL_PATH_DIAGNOSTIC = "AWG-WORKFLOW-018"
ARTIFACT_STATUS_EVENT_DIAGNOSTIC = "AWG-WORKFLOW-019"

LEGACY_WORKFLOW_FIELDS = frozenset(
    {
        "defaultFailureRoute",
        "initialState",
    }
)
LEGACY_STATE_FIELDS = frozenset(
    {
        "agent",
        "id",
    }
)
LEGACY_GATE_FIELDS = frozenset(
    {
        "agent",
        "produces",
    }
)


@dataclass(frozen=True, slots=True)
class WorkflowReferenceData:
    """Validated external identities needed by workflow gates."""

    skill_capabilities: frozenset[str]
    artifact_statuses: tuple[tuple[str, frozenset[str]], ...]


@dataclass(frozen=True, slots=True)
class WorkflowValidationResult:
    """Validated workflows and deterministic diagnostics."""

    workflows: tuple[Workflow, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedWorkflow:
    workflow: Workflow
    source_path: Path


class WorkflowDependencyProjectionError(ValueError):
    """Raised when dependency registry data cannot be projected."""


def project_skill_capabilities(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project capability identities without validating skill semantics."""

    capabilities: set[str] = set()

    for source in sources:
        raw_provides = source.data.get("provides")

        if not isinstance(raw_provides, list) or not raw_provides:
            raise WorkflowDependencyProjectionError(
                f"{source.source_path}: provides must be a non-empty list"
            )

        for index, raw_capability in enumerate(raw_provides):
            if not isinstance(raw_capability, str) or not raw_capability.strip():
                raise WorkflowDependencyProjectionError(
                    f"{source.source_path}: provides[{index}] "
                    "must be a non-empty string"
                )

            capabilities.add(raw_capability)

    return frozenset(capabilities)


def project_artifact_statuses(
    sources: Iterable[RegistrySource],
) -> tuple[tuple[str, frozenset[str]], ...]:
    """Project artifact identities and allowed statuses only."""

    statuses_by_type: dict[str, frozenset[str]] = {}

    for source in sources:
        raw_type = source.data.get("type")

        if not isinstance(raw_type, str) or not raw_type.strip():
            raise WorkflowDependencyProjectionError(
                f"{source.source_path}: type must be a non-empty string"
            )

        artifact_type = raw_type.strip()

        if artifact_type in statuses_by_type:
            raise WorkflowDependencyProjectionError(
                f"{source.source_path}: artifact type {artifact_type!r} is duplicated"
            )

        raw_statuses = source.data.get("allowedStatuses")

        if not isinstance(raw_statuses, list) or not raw_statuses:
            raise WorkflowDependencyProjectionError(
                f"{source.source_path}: allowedStatuses must be a non-empty list"
            )

        projected: set[str] = set()

        for index, raw_status in enumerate(raw_statuses):
            if not isinstance(raw_status, str) or not raw_status.strip():
                raise WorkflowDependencyProjectionError(
                    f"{source.source_path}: allowedStatuses[{index}] "
                    "must be a non-empty string"
                )

            projected.add(raw_status.strip().casefold())

        statuses_by_type[artifact_type] = frozenset(projected)

    return tuple(sorted(statuses_by_type.items()))


def validate_workflow_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    references: WorkflowReferenceData,
) -> WorkflowValidationResult:
    """Validate reusable workflows without side effects."""

    validator = Draft202012Validator(
        cast(Mapping[str, Any], schema)
    )
    parsed_workflows, diagnostics = validate_and_parse_sources(
        sources,
        validator,
        _validate_legacy_fields,
        _validate_schema,
        _parse_workflow,
        lambda parsed: _validate_workflow_semantics(parsed, references),
    )

    diagnostics.extend(_validate_unique_workflow_names(parsed_workflows))

    return WorkflowValidationResult(
        workflows=tuple(parsed.workflow for parsed in parsed_workflows),
        diagnostics=tuple(diagnostics),
    )


def _validate_legacy_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []

    for field in sorted(LEGACY_WORKFLOW_FIELDS.intersection(source.data)):
        diagnostics.append(
            _legacy_diagnostic(
                source,
                field,
                field,
            )
        )

    raw_states = source.data.get("states")

    if not isinstance(raw_states, list):
        return tuple(diagnostics)

    for state_index, raw_state in enumerate(raw_states):
        if not isinstance(raw_state, dict):
            continue

        for field in sorted(LEGACY_STATE_FIELDS.intersection(raw_state)):
            diagnostics.append(
                _legacy_diagnostic(
                    source,
                    field,
                    f"states[{state_index}].{field}",
                )
            )

        raw_gate = raw_state.get("gate")

        if not isinstance(raw_gate, dict):
            continue

        for field in sorted(LEGACY_GATE_FIELDS.intersection(raw_gate)):
            diagnostics.append(
                _legacy_diagnostic(
                    source,
                    field,
                    f"states[{state_index}].gate.{field}",
                )
            )

    return tuple(diagnostics)


def _legacy_diagnostic(
    source: RegistrySource,
    field: str,
    location: str,
) -> Diagnostic:
    return Diagnostic(
        code=LEGACY_FIELD_DIAGNOSTIC,
        message=f"legacy workflow field {field!r} is not allowed",
        source_path=source.source_path.as_posix(),
        location=location,
        related_identities=(field,),
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


def _parse_workflow(
    source: RegistrySource,
) -> _ParsedWorkflow:
    raw_states = cast(list[JsonObject], source.data["states"])
    raw_transitions = cast(
        list[JsonObject],
        source.data["transitions"],
    )

    states = tuple(_parse_state(raw_state) for raw_state in raw_states)
    transitions = tuple(
        WorkflowTransition(
            source=cast(str, raw_transition["from"]),
            target=cast(str, raw_transition["to"]),
            event=cast(str, raw_transition["on"]),
        )
        for raw_transition in raw_transitions
    )

    return _ParsedWorkflow(
        workflow=Workflow(
            name=cast(str, source.data["name"]),
            version=cast(str, source.data["version"]),
            description=cast(str, source.data["description"]),
            start_state=cast(str, source.data["startState"]),
            terminal_states=_string_tuple(source.data["terminalStates"]),
            default_failure_state=cast(
                str,
                source.data["defaultFailureState"],
            ),
            fail_closed=cast(
                bool,
                source.data["failClosed"],
            ),
            states=states,
            transitions=transitions,
        ),
        source_path=source.source_path,
    )


def _parse_state(
    raw_state: JsonObject,
) -> WorkflowState:
    raw_gate = raw_state.get("gate")

    if isinstance(raw_gate, dict):
        gate = WorkflowGate(
            name=cast(str, raw_gate["name"]),
            blocking=cast(bool, raw_gate["blocking"]),
            required_capabilities=_string_tuple(raw_gate["requiredCapabilities"]),
            required_artifacts=_string_tuple(raw_gate["requiredArtifacts"]),
        )
        terminal = False
    else:
        gate = None
        terminal = True

    return WorkflowState(
        name=cast(str, raw_state["name"]),
        terminal=terminal,
        gate=gate,
    )


def _string_tuple(
    value: JsonValue,
) -> tuple[str, ...]:
    return tuple(cast(list[str], value))


def _validate_workflow_semantics(
    parsed: _ParsedWorkflow,
    references: WorkflowReferenceData,
) -> tuple[Diagnostic, ...]:
    workflow = parsed.workflow
    source_path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    expected_name = source_path.name.removesuffix(".workflow.json")

    if workflow.name != expected_name:
        diagnostics.append(
            Diagnostic(
                code=FILE_NAME_DIAGNOSTIC,
                message=(
                    f"name {workflow.name!r} does not match file name {expected_name!r}"
                ),
                source_path=source_path.as_posix(),
                location="name",
                related_identities=(
                    workflow.name,
                    expected_name,
                ),
            )
        )

    if not workflow.fail_closed:
        diagnostics.append(
            Diagnostic(
                code=FAIL_CLOSED_DIAGNOSTIC,
                message="failClosed must be true",
                source_path=source_path.as_posix(),
                location="failClosed",
                related_identities=(workflow.name,),
            )
        )

    state_by_name: dict[str, WorkflowState] = {}
    gate_names: set[str] = set()

    for index, state in enumerate(workflow.states):
        first_state = state_by_name.get(state.name)

        if first_state is not None:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_STATE_DIAGNOSTIC,
                    message=f"state name {state.name!r} is duplicated",
                    source_path=source_path.as_posix(),
                    location=f"states[{index}].name",
                    related_identities=(state.name,),
                )
            )
            continue

        state_by_name[state.name] = state

        if state.gate is None:
            continue

        if state.gate.name in gate_names:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_GATE_DIAGNOSTIC,
                    message=(f"gate name {state.gate.name!r} is duplicated"),
                    source_path=source_path.as_posix(),
                    location=f"states[{index}].gate.name",
                    related_identities=(state.gate.name,),
                )
            )
        else:
            gate_names.add(state.gate.name)

    terminal_state_names = {state.name for state in workflow.states if state.terminal}
    declared_terminal_states = set(workflow.terminal_states)

    if workflow.start_state not in state_by_name:
        diagnostics.append(
            Diagnostic(
                code=START_STATE_DIAGNOSTIC,
                message=(
                    f"startState {workflow.start_state!r} is not declared in states"
                ),
                source_path=source_path.as_posix(),
                location="startState",
                related_identities=(workflow.start_state,),
            )
        )
    elif workflow.start_state in terminal_state_names:
        diagnostics.append(
            Diagnostic(
                code=START_STATE_DIAGNOSTIC,
                message=(f"startState {workflow.start_state!r} must not be terminal"),
                source_path=source_path.as_posix(),
                location="startState",
                related_identities=(workflow.start_state,),
            )
        )

    for state_name in sorted(declared_terminal_states - terminal_state_names):
        diagnostics.append(
            Diagnostic(
                code=TERMINAL_STATE_DIAGNOSTIC,
                message=(
                    f"terminalState {state_name!r} must reference a terminal state"
                ),
                source_path=source_path.as_posix(),
                location="terminalStates",
                related_identities=(state_name,),
            )
        )

    for state_name in sorted(terminal_state_names - declared_terminal_states):
        diagnostics.append(
            Diagnostic(
                code=TERMINAL_STATE_DIAGNOSTIC,
                message=(
                    f"terminal state {state_name!r} must be listed in terminalStates"
                ),
                source_path=source_path.as_posix(),
                location="terminalStates",
                related_identities=(state_name,),
            )
        )

    if workflow.default_failure_state not in state_by_name:
        diagnostics.append(
            Diagnostic(
                code=DEFAULT_FAILURE_STATE_DIAGNOSTIC,
                message=(
                    f"defaultFailureState "
                    f"{workflow.default_failure_state!r} "
                    "is not declared in states"
                ),
                source_path=source_path.as_posix(),
                location="defaultFailureState",
                related_identities=(workflow.default_failure_state,),
            )
        )
    elif workflow.default_failure_state not in terminal_state_names:
        diagnostics.append(
            Diagnostic(
                code=DEFAULT_FAILURE_STATE_DIAGNOSTIC,
                message=(
                    f"defaultFailureState "
                    f"{workflow.default_failure_state!r} "
                    "must be terminal"
                ),
                source_path=source_path.as_posix(),
                location="defaultFailureState",
                related_identities=(workflow.default_failure_state,),
            )
        )
    elif workflow.default_failure_state not in declared_terminal_states:
        diagnostics.append(
            Diagnostic(
                code=DEFAULT_FAILURE_STATE_DIAGNOSTIC,
                message=(
                    f"defaultFailureState "
                    f"{workflow.default_failure_state!r} "
                    "must be listed in terminalStates"
                ),
                source_path=source_path.as_posix(),
                location="defaultFailureState",
                related_identities=(workflow.default_failure_state,),
            )
        )

    artifact_statuses = dict(references.artifact_statuses)

    for index, state in enumerate(workflow.states):
        gate = state.gate

        if gate is None:
            continue

        for capability in gate.required_capabilities:
            if capability in references.skill_capabilities:
                continue

            diagnostics.append(
                Diagnostic(
                    code=UNKNOWN_CAPABILITY_DIAGNOSTIC,
                    message=(
                        f"gate requires capability {capability!r} "
                        "not provided by a registered skill"
                    ),
                    source_path=source_path.as_posix(),
                    location=(f"states[{index}].gate.requiredCapabilities"),
                    related_identities=(
                        state.name,
                        gate.name,
                        capability,
                    ),
                )
            )

        for artifact_type in gate.required_artifacts:
            if artifact_type in artifact_statuses:
                continue

            diagnostics.append(
                Diagnostic(
                    code=UNKNOWN_ARTIFACT_DIAGNOSTIC,
                    message=(
                        f"gate requires missing artifact contract {artifact_type!r}"
                    ),
                    source_path=source_path.as_posix(),
                    location=(f"states[{index}].gate.requiredArtifacts"),
                    related_identities=(
                        state.name,
                        gate.name,
                        artifact_type,
                    ),
                )
            )

    diagnostics.extend(
        _validate_transition_graph(
            parsed,
            state_by_name,
            terminal_state_names,
            artifact_statuses,
        )
    )

    return tuple(diagnostics)


def _validate_transition_graph(
    parsed: _ParsedWorkflow,
    state_by_name: dict[str, WorkflowState],
    terminal_state_names: set[str],
    artifact_statuses: dict[str, frozenset[str]],
) -> tuple[Diagnostic, ...]:
    workflow = parsed.workflow
    source_path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    outgoing: dict[str, set[str]] = {}
    reverse_edges: dict[str, set[str]] = {}
    outgoing_events: dict[str, set[str]] = {}
    seen_events: set[tuple[str, str]] = set()

    for index, transition in enumerate(workflow.transitions):
        source_valid = transition.source in state_by_name
        target_valid = transition.target in state_by_name
        event = transition.event.casefold()

        if not source_valid:
            diagnostics.append(
                Diagnostic(
                    code=TRANSITION_ENDPOINT_DIAGNOSTIC,
                    message=(
                        f"transition source {transition.source!r} "
                        "is not declared in states"
                    ),
                    source_path=source_path.as_posix(),
                    location=f"transitions[{index}].from",
                    related_identities=(transition.source,),
                )
            )
        elif transition.source in terminal_state_names:
            diagnostics.append(
                Diagnostic(
                    code=TERMINAL_OUTGOING_DIAGNOSTIC,
                    message=(
                        f"terminal state {transition.source!r} "
                        "must not have outgoing transition"
                    ),
                    source_path=source_path.as_posix(),
                    location=f"transitions[{index}].from",
                    related_identities=(transition.source,),
                )
            )

        if not target_valid:
            diagnostics.append(
                Diagnostic(
                    code=TRANSITION_ENDPOINT_DIAGNOSTIC,
                    message=(
                        f"transition target {transition.target!r} "
                        "is not declared in states"
                    ),
                    source_path=source_path.as_posix(),
                    location=f"transitions[{index}].to",
                    related_identities=(transition.target,),
                )
            )

        source_event = (
            transition.source,
            event,
        )

        if source_event in seen_events:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_EVENT_DIAGNOSTIC,
                    message=(
                        f"transition event {event!r} from state "
                        f"{transition.source!r} is duplicated"
                    ),
                    source_path=source_path.as_posix(),
                    location=f"transitions[{index}].on",
                    related_identities=(
                        transition.source,
                        event,
                    ),
                )
            )
        else:
            seen_events.add(source_event)

        if (
            source_valid
            and target_valid
            and transition.source not in terminal_state_names
        ):
            outgoing.setdefault(
                transition.source,
                set(),
            ).add(transition.target)
            reverse_edges.setdefault(
                transition.target,
                set(),
            ).add(transition.source)
            outgoing_events.setdefault(
                transition.source,
                set(),
            ).add(event)

    non_terminal_names = {state.name for state in workflow.states if not state.terminal}

    for state_name in sorted(non_terminal_names):
        if state_name in outgoing:
            continue

        diagnostics.append(
            Diagnostic(
                code=MISSING_OUTGOING_DIAGNOSTIC,
                message=(
                    f"non-terminal state {state_name!r} has no outgoing transition"
                ),
                source_path=source_path.as_posix(),
                location="transitions",
                related_identities=(state_name,),
            )
        )

    for state in workflow.states:
        gate = state.gate

        if gate is None:
            continue

        events = outgoing_events.get(
            state.name,
            set(),
        )

        for artifact_type in gate.required_artifacts:
            allowed_statuses = artifact_statuses.get(artifact_type)

            if allowed_statuses is None:
                continue

            for event in sorted(events - allowed_statuses):
                diagnostics.append(
                    Diagnostic(
                        code=ARTIFACT_STATUS_EVENT_DIAGNOSTIC,
                        message=(
                            f"state {state.name!r} gate "
                            f"{gate.name!r} transition event "
                            f"{event!r} is not allowed by required "
                            f"artifact {artifact_type!r} statuses"
                        ),
                        source_path=source_path.as_posix(),
                        location="transitions",
                        related_identities=_unique_identities(
                            state.name,
                            gate.name,
                            event,
                            artifact_type,
                        ),
                    )
                )

    if workflow.start_state in state_by_name:
        reachable = _reachable_from(
            workflow.start_state,
            outgoing,
        )

        for state_name in sorted(set(state_by_name) - reachable):
            diagnostics.append(
                Diagnostic(
                    code=UNREACHABLE_STATE_DIAGNOSTIC,
                    message=(
                        f"state {state_name!r} is unreachable "
                        f"from startState "
                        f"{workflow.start_state!r}"
                    ),
                    source_path=source_path.as_posix(),
                    location="states",
                    related_identities=(
                        workflow.start_state,
                        state_name,
                    ),
                )
            )

    if terminal_state_names:
        reaching_terminal = _states_reaching_terminal(
            terminal_state_names,
            reverse_edges,
        )

        for state_name in sorted(set(state_by_name) - reaching_terminal):
            diagnostics.append(
                Diagnostic(
                    code=NO_TERMINAL_PATH_DIAGNOSTIC,
                    message=(f"state {state_name!r} cannot reach a terminal state"),
                    source_path=source_path.as_posix(),
                    location="transitions",
                    related_identities=(state_name,),
                )
            )

    return tuple(diagnostics)


def _unique_identities(
    *identities: str,
) -> tuple[str, ...]:
    return tuple(dict.fromkeys(identities))


def _reachable_from(
    start: str,
    outgoing: dict[str, set[str]],
) -> set[str]:
    reachable: set[str] = set()
    stack = [start]

    while stack:
        current = stack.pop()

        reachable.add(current)
        stack.extend(
            sorted(
                outgoing.get(current, set()) - reachable,
                reverse=True,
            )
        )

    return reachable


def _states_reaching_terminal(
    terminal_states: set[str],
    reverse_edges: dict[str, set[str]],
) -> set[str]:
    reachable = set(terminal_states)
    stack = sorted(
        terminal_states,
        reverse=True,
    )

    while stack:
        current = stack.pop()

        for source in sorted(
            reverse_edges.get(current, set()),
            reverse=True,
        ):
            if source in reachable:
                continue

            reachable.add(source)
            stack.append(source)

    return reachable


def _validate_unique_workflow_names(
    parsed_workflows: list[_ParsedWorkflow],
) -> tuple[Diagnostic, ...]:
    seen: dict[str, Path] = {}
    diagnostics: list[Diagnostic] = []

    for parsed in parsed_workflows:
        name = parsed.workflow.name
        first_path = seen.get(name)

        if first_path is None:
            seen[name] = parsed.source_path
            continue

        diagnostics.append(
            Diagnostic(
                code=DUPLICATE_WORKFLOW_DIAGNOSTIC,
                message=(
                    f"workflow name {name!r} is duplicated; "
                    f"first declared at "
                    f"{first_path.as_posix()}"
                ),
                source_path=parsed.source_path.as_posix(),
                location="name",
                related_identities=(name,),
            )
        )

    return tuple(diagnostics)
