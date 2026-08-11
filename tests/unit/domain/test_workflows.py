from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from agentic_workflow_generator.domain import (
    Workflow,
    WorkflowGate,
    WorkflowRoutingResult,
    WorkflowState,
    WorkflowTransition,
)


def workflow() -> Workflow:
    gate = WorkflowGate(
        name="requirements-review",
        blocking=True,
        required_capabilities=(
            "requirements.elicit",
            "requirements.define-acceptance-criteria",
        ),
        required_artifacts=("Requirements",),
    )

    return Workflow(
        name="lean-delivery",
        version="0.3.0",
        description="Lean delivery workflow.",
        start_state="Requirements",
        terminal_states=(
            "Done",
            "Blocked",
        ),
        default_failure_state="Blocked",
        fail_closed=True,
        states=(
            WorkflowState(
                name="Requirements",
                terminal=False,
                gate=gate,
            ),
            WorkflowState(
                name="Done",
                terminal=True,
                gate=None,
            ),
            WorkflowState(
                name="Blocked",
                terminal=True,
                gate=None,
            ),
        ),
        transitions=(
            WorkflowTransition(
                source="Requirements",
                target="Done",
                result=WorkflowRoutingResult.PASS,
            ),
            WorkflowTransition(
                source="Requirements",
                target="Blocked",
                result=WorkflowRoutingResult.FAIL,
            ),
            WorkflowTransition(
                source="Requirements",
                target="Blocked",
                result=WorkflowRoutingResult.BLOCKED,
            ),
        ),
    )


def test_workflow_model_preserves_validated_semantics() -> None:
    definition = workflow()

    assert definition.name == "lean-delivery"
    assert definition.start_state == "Requirements"
    assert definition.terminal_states == (
        "Done",
        "Blocked",
    )
    assert definition.default_failure_state == "Blocked"
    assert definition.fail_closed is True

    requirements = definition.states[0]
    assert requirements.terminal is False
    assert requirements.gate is not None
    assert requirements.gate.name == "requirements-review"
    assert requirements.gate.blocking is True
    assert requirements.gate.required_artifacts == ("Requirements",)

    transition = definition.transitions[0]
    assert transition.source == "Requirements"
    assert transition.target == "Done"
    assert transition.result is WorkflowRoutingResult.PASS
    assert transition.result.value == "pass"


def test_workflow_routing_result_is_closed_and_serializable() -> None:
    assert tuple(result.value for result in WorkflowRoutingResult) == (
        "pass",
        "fail",
        "blocked",
    )

    with pytest.raises(ValueError):
        WorkflowRoutingResult("approve")


@pytest.mark.parametrize(
    ("value", "attribute"),
    [
        (workflow(), "name"),
        (workflow().states[0], "name"),
        (workflow().states[0].gate, "name"),
        (workflow().transitions[0], "source"),
    ],
)
def test_workflow_models_are_immutable(
    value: object,
    attribute: str,
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(cast(Any, value), attribute, "changed")
