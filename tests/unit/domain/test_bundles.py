from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from agentic_workflow_generator.domain import (
    AgentInstance,
    Bundle,
    RoleBinding,
    RoleBindingType,
    SeparationMode,
    SeparationPolicy,
    SharedContextPolicy,
)


def bundle() -> Bundle:
    return Bundle(
        name="lean-delivery",
        description="Lean delivery bundle.",
        version="0.2.0",
        profile="lean-delivery",
        workflow="lean-delivery",
        agent_instances=(
            AgentInstance(
                id="requirements-worker",
                profile="Requirements",
                display_name="Requirements",
                permission_profile="read-only",
                shared_context_policy=(SharedContextPolicy.ASSIGNED_BINDINGS),
            ),
            AgentInstance(
                id="workflow-controller",
                profile="Orchestrator",
                display_name="Orchestrator",
                permission_profile="read-only",
                shared_context_policy=(SharedContextPolicy.ASSIGNED_BINDINGS),
            ),
        ),
        role_bindings=(
            RoleBinding(
                role_name="requirements",
                binding_type=RoleBindingType.STATE_OWNER,
                agent_instance="requirements-worker",
                required_capabilities=("requirements.elicit",),
                selected_skills=("requirements-analysis",),
                produces=("Requirements",),
                input_artifacts=(),
                responsibilities=("Clarify requirements",),
                guardrails=("Do not implement",),
                workflow_state="Requirements",
                workflow_gate="requirements-review",
            ),
            RoleBinding(
                role_name="workflow-controller",
                binding_type=(RoleBindingType.WORKFLOW_CONTROLLER),
                agent_instance="workflow-controller",
                required_capabilities=("workflow.route",),
                selected_skills=("workflow-routing",),
                produces=(),
                input_artifacts=(),
                responsibilities=("Route work",),
                guardrails=("Do not override gates",),
                workflow_state=None,
                workflow_gate=None,
            ),
        ),
        separation_policies=(
            SeparationPolicy(
                id="role-independence",
                mode=SeparationMode.REQUIRED,
                role_bindings=(
                    "requirements",
                    "workflow-controller",
                ),
                require_distinct_instances=True,
                reason="Routing authority must remain independent.",
            ),
        ),
        skills=(
            "requirements-analysis",
            "workflow-routing",
        ),
        artifacts=("Requirements",),
        targets=("opencode",),
    )


def test_bundle_enum_values_are_stable() -> None:
    assert tuple(SharedContextPolicy) == (SharedContextPolicy.ASSIGNED_BINDINGS,)
    assert tuple(RoleBindingType) == (
        RoleBindingType.STATE_OWNER,
        RoleBindingType.WORKFLOW_CONTROLLER,
    )
    assert tuple(SeparationMode) == (SeparationMode.REQUIRED,)

    assert (
        SharedContextPolicy.ASSIGNED_BINDINGS.value == "shared-with-assigned-bindings"
    )
    assert RoleBindingType.STATE_OWNER.value == "state-owner"
    assert RoleBindingType.WORKFLOW_CONTROLLER.value == "workflow-controller"
    assert SeparationMode.REQUIRED.value == "required"


def test_bundle_model_preserves_composition_semantics() -> None:
    definition = bundle()

    assert definition.name == "lean-delivery"
    assert definition.profile == "lean-delivery"
    assert definition.workflow == "lean-delivery"
    assert definition.skills == (
        "requirements-analysis",
        "workflow-routing",
    )

    instance = definition.agent_instances[0]
    assert instance.id == "requirements-worker"
    assert instance.profile == "Requirements"
    assert instance.shared_context_policy is SharedContextPolicy.ASSIGNED_BINDINGS

    state_owner = definition.role_bindings[0]
    assert state_owner.binding_type is RoleBindingType.STATE_OWNER
    assert state_owner.workflow_state == "Requirements"
    assert state_owner.workflow_gate == "requirements-review"
    assert state_owner.produces == ("Requirements",)

    controller = definition.role_bindings[1]
    assert controller.binding_type is RoleBindingType.WORKFLOW_CONTROLLER
    assert controller.workflow_state is None
    assert controller.workflow_gate is None
    assert controller.produces == ()

    policy = definition.separation_policies[0]
    assert policy.mode is SeparationMode.REQUIRED
    assert policy.require_distinct_instances is True


@pytest.mark.parametrize(
    ("value", "attribute"),
    [
        (bundle(), "name"),
        (bundle().agent_instances[0], "id"),
        (bundle().role_bindings[0], "role_name"),
        (bundle().separation_policies[0], "id"),
    ],
)
def test_bundle_models_are_immutable(
    value: object,
    attribute: str,
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(cast(Any, value), attribute, "changed")
