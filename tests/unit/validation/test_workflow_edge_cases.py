import re
from collections.abc import Callable
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    read_json_object,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.workflows import (
    DEFAULT_FAILURE_STATE_DIAGNOSTIC,
    DUPLICATE_GATE_DIAGNOSTIC,
    DUPLICATE_STATE_DIAGNOSTIC,
    DUPLICATE_WORKFLOW_DIAGNOSTIC,
    NO_TERMINAL_PATH_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    START_STATE_DIAGNOSTIC,
    TERMINAL_OUTGOING_DIAGNOSTIC,
    TERMINAL_STATE_DIAGNOSTIC,
    TRANSITION_ENDPOINT_DIAGNOSTIC,
    UNREACHABLE_STATE_DIAGNOSTIC,
    WorkflowDependencyProjectionError,
    WorkflowReferenceData,
    WorkflowValidationResult,
    _schema_error_location,
    _schema_error_message,
    project_artifact_statuses,
    project_skill_capabilities,
    validate_workflow_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA = read_json_object(
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "workflow.schema.json"
)


def workflow_data() -> JsonObject:
    return {
        "name": "lean-delivery",
        "version": "0.2.0",
        "description": "Lean workflow.",
        "startState": "Requirements",
        "terminalStates": [
            "Done",
            "Blocked",
        ],
        "defaultFailureState": "Blocked",
        "failClosed": True,
        "states": [
            {
                "name": "Requirements",
                "gate": {
                    "name": "requirements-review",
                    "blocking": True,
                    "requiredCapabilities": [
                        "requirements.elicit",
                    ],
                    "requiredArtifacts": [
                        "Requirements",
                    ],
                },
            },
            {
                "name": "Review",
                "gate": {
                    "name": "review",
                    "blocking": True,
                    "requiredCapabilities": [
                        "requirements.elicit",
                    ],
                    "requiredArtifacts": [
                        "Requirements",
                    ],
                },
            },
            {
                "name": "Done",
                "terminal": True,
            },
            {
                "name": "Blocked",
                "terminal": True,
            },
        ],
        "transitions": [
            {
                "from": "Requirements",
                "to": "Review",
                "on": "pass",
            },
            {
                "from": "Requirements",
                "to": "Blocked",
                "on": "fail",
            },
            {
                "from": "Review",
                "to": "Done",
                "on": "pass",
            },
            {
                "from": "Review",
                "to": "Blocked",
                "on": "fail",
            },
        ],
    }


def workflow_source(
    *,
    data: JsonObject | None = None,
    filename: str = "lean-delivery.workflow.json",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.WORKFLOW,
        source_path=Path(f"registry/workflows/{filename}"),
        data=workflow_data() if data is None else data,
    )


def skill_source(
    provides: JsonValue,
    *,
    folder: str = "requirements",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.SKILL,
        source_path=Path(f"registry/skills/{folder}/skill.json"),
        data={
            "name": folder,
            "provides": provides,
        },
    )


def artifact_source(
    artifact_type: JsonValue,
    statuses: JsonValue,
    *,
    folder: str = "Requirements",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=Path(f"registry/artifacts/{folder}/artifact.json"),
        data={
            "type": artifact_type,
            "allowedStatuses": statuses,
        },
    )


def references() -> WorkflowReferenceData:
    return WorkflowReferenceData(
        skill_capabilities=frozenset(
            {
                "requirements.elicit",
            }
        ),
        artifact_statuses=(
            (
                "Requirements",
                frozenset(
                    {
                        "pass",
                        "fail",
                        "blocked",
                    }
                ),
            ),
        ),
    )


def validate(
    *sources: RegistrySource,
) -> WorkflowValidationResult:
    return validate_workflow_registry(
        tuple(sources),
        SCHEMA,
        references(),
    )


def first_state(
    data: JsonObject,
) -> JsonObject:
    states = data["states"]
    assert isinstance(states, list)
    state = states[0]
    assert isinstance(state, dict)
    return state


def first_gate(
    data: JsonObject,
) -> JsonObject:
    gate = first_state(data)["gate"]
    assert isinstance(gate, dict)
    return gate


def transitions(
    data: JsonObject,
) -> list[JsonValue]:
    value = data["transitions"]
    assert isinstance(value, list)
    return value


def diagnostic_codes(
    result: WorkflowValidationResult,
) -> set[str]:
    return {diagnostic.code for diagnostic in result.diagnostics}


def test_dependency_projections_are_deterministic() -> None:
    capabilities = project_skill_capabilities(
        (
            skill_source(
                [
                    "requirements.elicit",
                    "requirements.define",
                ],
                folder="requirements",
            ),
            skill_source(
                [
                    "requirements.elicit",
                    "review.code",
                ],
                folder="review",
            ),
        )
    )
    statuses = project_artifact_statuses(
        (
            artifact_source(
                "TestReport",
                [
                    "PASS",
                    "FAIL",
                ],
                folder="TestReport",
            ),
            artifact_source(
                "Requirements",
                [
                    "PASS",
                    "BLOCKED",
                ],
            ),
        )
    )

    assert capabilities == frozenset(
        {
            "requirements.elicit",
            "requirements.define",
            "review.code",
        }
    )
    assert statuses == (
        (
            "Requirements",
            frozenset(
                {
                    "pass",
                    "blocked",
                }
            ),
        ),
        (
            "TestReport",
            frozenset(
                {
                    "pass",
                    "fail",
                }
            ),
        ),
    )


@pytest.mark.parametrize(
    ("provides", "expected"),
    [
        (
            None,
            "provides must be a non-empty list",
        ),
        (
            [],
            "provides must be a non-empty list",
        ),
        (
            [""],
            "provides[0] must be a non-empty string",
        ),
        (
            [1],
            "provides[0] must be a non-empty string",
        ),
    ],
)
def test_skill_projection_rejects_invalid_data(
    provides: JsonValue,
    expected: str,
) -> None:
    with pytest.raises(
        WorkflowDependencyProjectionError,
        match=re.escape(expected),
    ):
        project_skill_capabilities((skill_source(provides),))


@pytest.mark.parametrize(
    ("artifact_type", "statuses", "expected"),
    [
        (
            None,
            ["PASS"],
            "type must be a non-empty string",
        ),
        (
            "",
            ["PASS"],
            "type must be a non-empty string",
        ),
        (
            "Requirements",
            None,
            "allowedStatuses must be a non-empty list",
        ),
        (
            "Requirements",
            [],
            "allowedStatuses must be a non-empty list",
        ),
        (
            "Requirements",
            [""],
            "allowedStatuses[0] must be a non-empty string",
        ),
        (
            "Requirements",
            [1],
            "allowedStatuses[0] must be a non-empty string",
        ),
    ],
)
def test_artifact_projection_rejects_invalid_data(
    artifact_type: JsonValue,
    statuses: JsonValue,
    expected: str,
) -> None:
    with pytest.raises(
        WorkflowDependencyProjectionError,
        match=re.escape(expected),
    ):
        project_artifact_statuses(
            (
                artifact_source(
                    artifact_type,
                    statuses,
                ),
            )
        )


def test_artifact_projection_rejects_duplicate_types() -> None:
    with pytest.raises(
        WorkflowDependencyProjectionError,
        match="artifact type 'Requirements' is duplicated",
    ):
        project_artifact_statuses(
            (
                artifact_source(
                    "Requirements",
                    ["PASS"],
                ),
                artifact_source(
                    "Requirements",
                    ["FAIL"],
                    folder="Duplicate",
                ),
            )
        )


def test_schema_error_helpers_cover_nested_required_and_types() -> None:
    nested_required = next(
        Draft202012Validator(
            {
                "type": "object",
                "properties": {
                    "nested": {
                        "type": "object",
                        "required": ["name"],
                    }
                },
            }
        ).iter_errors(
            {
                "nested": {},
            }
        )
    )

    object_type = next(
        Draft202012Validator(
            {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "object",
                    }
                },
            }
        ).iter_errors(
            {
                "value": "invalid",
            }
        )
    )

    string_type = next(
        Draft202012Validator(
            {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                    }
                },
            }
        ).iter_errors(
            {
                "value": 1,
            }
        )
    )

    assert _schema_error_location(nested_required) == "nested.name"
    assert _schema_error_message(object_type) == "value must be an object"
    assert _schema_error_message(string_type) == "value must be a non-empty string"


@pytest.mark.parametrize(
    ("mutator", "expected_location", "expected_message"),
    [
        (
            lambda data: data.pop("name"),
            "name",
            "name is required",
        ),
        (
            lambda data: data.__setitem__(
                "version",
                "v1",
            ),
            "version",
            "version must be a semantic version",
        ),
        (
            lambda data: data.__setitem__(
                "description",
                "",
            ),
            "description",
            "description must be a non-empty string",
        ),
        (
            lambda data: data.__setitem__(
                "terminalStates",
                [],
            ),
            "terminalStates",
            "terminalStates must be a non-empty list",
        ),
        (
            lambda data: data.__setitem__(
                "terminalStates",
                [
                    "Done",
                    "Done",
                ],
            ),
            "terminalStates",
            "terminalStates entries must be unique",
        ),
        (
            lambda data: data.__setitem__(
                "states",
                "invalid",
            ),
            "states",
            "states must be a non-empty list",
        ),
        (
            lambda data: data.__setitem__(
                "failClosed",
                "true",
            ),
            "failClosed",
            "failClosed must be a boolean",
        ),
        (
            lambda data: data.__setitem__(
                "states",
                [
                    "invalid",
                ],
            ),
            "states.0",
            "schema violation:",
        ),
        (
            lambda data: first_state(data).pop("gate"),
            "states.0",
            "schema violation:",
        ),
        (
            lambda data: first_gate(data).__setitem__(
                "blocking",
                False,
            ),
            "states.0",
            "schema violation:",
        ),
    ],
)
def test_schema_diagnostics_cover_public_error_shapes(
    mutator: Callable[[JsonObject], object],
    expected_location: str,
    expected_message: str,
) -> None:
    data = workflow_data()
    mutator(data)

    result = validate(workflow_source(data=data))

    assert result.workflows == ()
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == SCHEMA_DIAGNOSTIC
    assert diagnostic.location == expected_location
    assert expected_message in diagnostic.message


@pytest.mark.parametrize(
    ("field", "location"),
    [
        (
            "defaultFailureRoute",
            "defaultFailureRoute",
        ),
        (
            "initialState",
            "initialState",
        ),
    ],
)
def test_obsolete_root_fields_are_rejected(
    field: str,
    location: str,
) -> None:
    data = workflow_data()
    data[field] = "obsolete"

    result = validate(workflow_source(data=data))

    assert result.diagnostics[0].code == OBSOLETE_FIELD_DIAGNOSTIC
    assert result.diagnostics[0].location == location


@pytest.mark.parametrize(
    ("field", "location"),
    [
        (
            "agent",
            "states[0].agent",
        ),
        (
            "id",
            "states[0].id",
        ),
    ],
)
def test_obsolete_state_fields_are_rejected(
    field: str,
    location: str,
) -> None:
    data = workflow_data()
    first_state(data)[field] = "obsolete"

    result = validate(workflow_source(data=data))

    assert result.diagnostics[0].code == OBSOLETE_FIELD_DIAGNOSTIC
    assert result.diagnostics[0].location == location


@pytest.mark.parametrize(
    ("field", "location"),
    [
        (
            "agent",
            "states[0].gate.agent",
        ),
        (
            "produces",
            "states[0].gate.produces",
        ),
    ],
)
def test_obsolete_gate_fields_are_rejected(
    field: str,
    location: str,
) -> None:
    data = workflow_data()
    first_gate(data)[field] = "obsolete"

    result = validate(workflow_source(data=data))

    assert result.diagnostics[0].code == OBSOLETE_FIELD_DIAGNOSTIC
    assert result.diagnostics[0].location == location


def test_obsolete_scan_tolerates_invalid_state_shapes() -> None:
    data = workflow_data()
    data["states"] = "invalid"

    result = validate(workflow_source(data=data))

    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC

    data = workflow_data()
    states = data["states"]
    assert isinstance(states, list)
    states.insert(0, "invalid")

    result = validate(workflow_source(data=data))

    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC


def test_duplicate_workflow_names_are_rejected() -> None:
    result = validate(
        workflow_source(),
        workflow_source(
            filename="duplicate.workflow.json",
        ),
    )

    assert DUPLICATE_WORKFLOW_DIAGNOSTIC in diagnostic_codes(result)


def test_duplicate_states_and_gates_are_rejected() -> None:
    data = workflow_data()
    states = data["states"]
    assert isinstance(states, list)

    duplicate_state = states[0]
    assert isinstance(duplicate_state, dict)
    states.insert(1, duplicate_state.copy())

    result = validate(workflow_source(data=data))

    assert DUPLICATE_STATE_DIAGNOSTIC in diagnostic_codes(result)

    data = workflow_data()
    states = data["states"]
    assert isinstance(states, list)
    review = states[1]
    assert isinstance(review, dict)
    gate = review["gate"]
    assert isinstance(gate, dict)
    gate["name"] = "requirements-review"

    result = validate(workflow_source(data=data))

    assert DUPLICATE_GATE_DIAGNOSTIC in diagnostic_codes(result)


@pytest.mark.parametrize(
    ("start_state", "expected_message"),
    [
        (
            "Missing",
            "is not declared in states",
        ),
        (
            "Done",
            "must not be terminal",
        ),
    ],
)
def test_start_state_invariants(
    start_state: str,
    expected_message: str,
) -> None:
    data = workflow_data()
    data["startState"] = start_state

    result = validate(workflow_source(data=data))

    diagnostic = next(
        item for item in result.diagnostics if item.code == START_STATE_DIAGNOSTIC
    )
    assert expected_message in diagnostic.message


def test_terminal_state_must_reference_declared_state() -> None:
    data = workflow_data()
    data["terminalStates"] = [
        "Done",
        "Blocked",
        "MissingTerminal",
    ]

    result = validate(workflow_source(data=data))

    diagnostic = next(
        item
        for item in result.diagnostics
        if (
            item.code == TERMINAL_STATE_DIAGNOSTIC and "MissingTerminal" in item.message
        )
    )
    assert (
        diagnostic.message
        == "terminalState 'MissingTerminal' must reference a terminal state"
    )


def test_terminal_state_declarations_must_match_state_objects() -> None:
    data = workflow_data()
    data["terminalStates"] = [
        "Review",
        "Blocked",
    ]

    result = validate(workflow_source(data=data))

    terminal_messages = [
        diagnostic.message
        for diagnostic in result.diagnostics
        if diagnostic.code == TERMINAL_STATE_DIAGNOSTIC
    ]

    assert "terminalState 'Review' must reference a terminal state" in terminal_messages
    assert "terminal state 'Done' must be listed in terminalStates" in terminal_messages


@pytest.mark.parametrize(
    ("failure_state", "terminal_states", "expected_message"),
    [
        (
            "Missing",
            [
                "Done",
                "Blocked",
            ],
            "is not declared in states",
        ),
        (
            "Review",
            [
                "Done",
                "Blocked",
            ],
            "must be terminal",
        ),
        (
            "Blocked",
            [
                "Done",
            ],
            "must be listed in terminalStates",
        ),
    ],
)
def test_default_failure_state_invariants(
    failure_state: str,
    terminal_states: JsonValue,
    expected_message: str,
) -> None:
    data = workflow_data()
    data["defaultFailureState"] = failure_state
    data["terminalStates"] = terminal_states

    result = validate(workflow_source(data=data))

    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == DEFAULT_FAILURE_STATE_DIAGNOSTIC
    )
    assert expected_message in diagnostic.message


def test_transition_endpoint_and_terminal_source_invariants() -> None:
    data = workflow_data()
    transitions(data).extend(
        [
            {
                "from": "MissingSource",
                "to": "Done",
                "on": "fail",
            },
            {
                "from": "Requirements",
                "to": "MissingTarget",
                "on": "blocked",
            },
            {
                "from": "Done",
                "to": "Blocked",
                "on": "fail",
            },
        ]
    )

    result = validate(workflow_source(data=data))
    codes = diagnostic_codes(result)

    assert TRANSITION_ENDPOINT_DIAGNOSTIC in codes
    assert TERMINAL_OUTGOING_DIAGNOSTIC in codes


def test_unreachable_state_and_missing_terminal_path_are_rejected() -> None:
    data = workflow_data()
    data["transitions"] = [
        {
            "from": "Requirements",
            "to": "Blocked",
            "on": "fail",
        },
        {
            "from": "Review",
            "to": "Review",
            "on": "pass",
        },
    ]

    result = validate(workflow_source(data=data))
    codes = diagnostic_codes(result)

    assert UNREACHABLE_STATE_DIAGNOSTIC in codes
    assert NO_TERMINAL_PATH_DIAGNOSTIC in codes


def test_cycle_helpers_terminate_deterministically() -> None:
    data = workflow_data()
    data["transitions"] = [
        {
            "from": "Requirements",
            "to": "Review",
            "on": "pass",
        },
        {
            "from": "Review",
            "to": "Requirements",
            "on": "blocked",
        },
        {
            "from": "Review",
            "to": "Done",
            "on": "fail",
        },
        {
            "from": "Requirements",
            "to": "Blocked",
            "on": "fail",
        },
    ]

    result = validate(workflow_source(data=data))

    assert result.is_valid


def test_workflow_without_terminal_state_objects_is_rejected() -> None:
    data = workflow_data()
    states = data["states"]
    assert isinstance(states, list)
    data["states"] = states[:2]
    data["terminalStates"] = [
        "Requirements",
    ]
    data["defaultFailureState"] = "Requirements"
    data["transitions"] = [
        {
            "from": "Requirements",
            "to": "Review",
            "on": "pass",
        },
        {
            "from": "Review",
            "to": "Requirements",
            "on": "fail",
        },
    ]

    result = validate(workflow_source(data=data))

    assert TERMINAL_STATE_DIAGNOSTIC in diagnostic_codes(result)
