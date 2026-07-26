from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.workflows import (
    ARTIFACT_STATUS_EVENT_DIAGNOSTIC,
    DUPLICATE_EVENT_DIAGNOSTIC,
    FAIL_CLOSED_DIAGNOSTIC,
    FILE_NAME_DIAGNOSTIC,
    LEGACY_FIELD_DIAGNOSTIC,
    MISSING_OUTGOING_DIAGNOSTIC,
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
    assert workflow.transitions[0].event == "pass"


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


def test_legacy_state_agent_is_rejected() -> None:
    data = workflow_data()
    states = data["states"]
    assert isinstance(states, list)
    first = states[0]
    assert isinstance(first, dict)
    first["agent"] = "Requirements"

    result = validate(source(data=data))

    diagnostic = result.diagnostics[0]
    assert diagnostic.code == LEGACY_FIELD_DIAGNOSTIC
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


def test_transition_events_are_case_insensitive_for_duplicates() -> None:
    data = workflow_data()
    transitions = data["transitions"]
    assert isinstance(transitions, list)
    transitions.append(
        {
            "from": "Requirements",
            "to": "Done",
            "on": "PASS",
        }
    )

    result = validate(source(data=data))

    assert any(
        diagnostic.code == DUPLICATE_EVENT_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_non_terminal_state_requires_outgoing_transition() -> None:
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
        diagnostic.code == MISSING_OUTGOING_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_transition_event_must_match_required_artifact_status() -> None:
    data = workflow_data()
    transitions = data["transitions"]
    assert isinstance(transitions, list)
    first = transitions[0]
    assert isinstance(first, dict)
    first["on"] = "approve"

    result = validate(source(data=data))

    assert any(
        diagnostic.code == ARTIFACT_STATUS_EVENT_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )
