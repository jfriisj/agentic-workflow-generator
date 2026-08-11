from pathlib import Path

from jsonschema.exceptions import ValidationError

import agentic_workflow_generator.validation.workflows as workflows_module
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.workflows import (
    BLOCKED_TARGET_DIAGNOSTIC,
    DUPLICATE_RESULT_DIAGNOSTIC,
    FAIL_CLOSED_DIAGNOSTIC,
    FILE_NAME_DIAGNOSTIC,
    MISSING_RESULT_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    PASS_FAILURE_TARGET_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    UNKNOWN_ARTIFACT_DIAGNOSTIC,
    UNKNOWN_CAPABILITY_DIAGNOSTIC,
    WorkflowReferenceData,
    WorkflowValidationResult,
    validate_workflow_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA = read_json_object(
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "workflow.schema.json"
)


def workflow_data() -> JsonObject:
    return {
        "name": "lean-delivery",
        "version": "0.3.0",
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
                "to": "Done",
                "on": "pass",
            },
            {
                "from": "Requirements",
                "to": "Blocked",
                "on": "fail",
            },
            {
                "from": "Requirements",
                "to": "Blocked",
                "on": "blocked",
            },
        ],
    }


def source(
    *,
    data: JsonObject | None = None,
    filename: str = "lean-delivery.workflow.json",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.WORKFLOW,
        source_path=Path(f"registry/workflows/{filename}"),
        data=workflow_data() if data is None else data,
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


def test_valid_workflow_is_parsed() -> None:
    result = validate(source())

    assert result.is_valid
    assert result.diagnostics == ()
    assert len(result.workflows) == 1

    workflow = result.workflows[0]
    assert workflow.name == "lean-delivery"
    assert workflow.start_state == "Requirements"
    assert workflow.terminal_states == (
        "Done",
        "Blocked",
    )
    assert workflow.fail_closed is True
    assert workflow.states[0].gate is not None
    assert workflow.states[0].gate.required_artifacts == ("Requirements",)
    assert workflow.transitions[0].result.value == "pass"


def test_file_name_must_match_workflow_name() -> None:
    result = validate(source(filename="different.workflow.json"))

    assert any(
        diagnostic.code == FILE_NAME_DIAGNOSTIC for diagnostic in result.diagnostics
    )


def test_fail_closed_must_be_true() -> None:
    data = workflow_data()
    data["failClosed"] = False

    result = validate(source(data=data))

    assert any(
        diagnostic.code == FAIL_CLOSED_DIAGNOSTIC for diagnostic in result.diagnostics
    )


def test_obsolete_state_agent_is_rejected() -> None:
    data = workflow_data()
    states = data["states"]
    assert isinstance(states, list)
    first = states[0]
    assert isinstance(first, dict)
    first["agent"] = "Requirements"

    result = validate(source(data=data))

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == OBSOLETE_FIELD_DIAGNOSTIC
    assert diagnostic.location == "states[0].agent"


def test_unknown_gate_references_are_rejected() -> None:
    data = workflow_data()
    states = data["states"]
    assert isinstance(states, list)
    first = states[0]
    assert isinstance(first, dict)
    gate = first["gate"]
    assert isinstance(gate, dict)
    gate["requiredCapabilities"] = ["missing.capability"]
    gate["requiredArtifacts"] = ["MissingArtifact"]

    result = validate(source(data=data))

    codes = {diagnostic.code for diagnostic in result.diagnostics}
    assert UNKNOWN_CAPABILITY_DIAGNOSTIC in codes
    assert UNKNOWN_ARTIFACT_DIAGNOSTIC in codes


def test_duplicate_source_result_route_is_rejected() -> None:
    data = workflow_data()
    transitions = data["transitions"]
    assert isinstance(transitions, list)
    transitions.append(
        {
            "from": "Requirements",
            "to": "Done",
            "on": "pass",
        }
    )

    result = validate(source(data=data))

    assert any(
        diagnostic.code == DUPLICATE_RESULT_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_non_terminal_state_requires_every_canonical_result() -> None:
    data = workflow_data()
    data["transitions"] = [
        {
            "from": "Done",
            "to": "Blocked",
            "on": "fail",
        }
    ]

    result = validate(source(data=data))

    assert any(
        diagnostic.code == MISSING_RESULT_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_unsupported_transition_result_is_rejected_by_schema() -> None:
    data = workflow_data()
    transitions = data["transitions"]
    assert isinstance(transitions, list)
    first = transitions[0]
    assert isinstance(first, dict)
    first["on"] = "approve"

    result = validate(source(data=data))

    assert any(
        diagnostic.code == SCHEMA_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_blocked_route_must_target_default_failure_state() -> None:
    data = workflow_data()
    transitions = data["transitions"]
    assert isinstance(transitions, list)
    blocked = transitions[2]
    assert isinstance(blocked, dict)
    blocked["to"] = "Done"

    result = validate(source(data=data))

    assert any(
        diagnostic.code == BLOCKED_TARGET_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_pass_route_must_not_target_default_failure_state() -> None:
    data = workflow_data()
    transitions = data["transitions"]
    assert isinstance(transitions, list)
    passed = transitions[0]
    assert isinstance(passed, dict)
    passed["to"] = "Blocked"

    result = validate(source(data=data))

    assert any(
        diagnostic.code == PASS_FAILURE_TARGET_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_workflow_schema_wrapper_helpers_delegate() -> None:
    path_error = ValidationError(
        "invalid transition",
        path=["transitions", 0, "on"],
    )
    required_error = ValidationError(
        "name is required",
        validator="required",
        validator_value=["name"],
        instance={},
    )

    assert workflows_module._schema_error_sort_key(
        path_error
    ) == (
        "transitions.0.on",
        "invalid transition",
    )
    assert (
        workflows_module._missing_required_field(
            required_error
        )
        == "name"
    )
