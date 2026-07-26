from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain import AgentProfile


def profile() -> AgentProfile:
    return AgentProfile(
        name="Implementer",
        version="0.2.0",
        role="implementation",
        description="Implements approved work.",
        recommended_responsibilities=("Modify product code",),
        default_guardrails=("Do not self-approve",),
        recommended_capabilities=("implementation.code",),
        default_permission_profile="implementation",
    )


def test_agent_profile_preserves_typed_values() -> None:
    agent = profile()

    assert agent.name == "Implementer"
    assert agent.recommended_responsibilities == ("Modify product code",)
    assert agent.default_guardrails == ("Do not self-approve",)
    assert agent.recommended_capabilities == ("implementation.code",)


def test_agent_profile_is_immutable() -> None:
    agent = profile()

    with pytest.raises(FrozenInstanceError):
        agent.name = "Changed"  # type: ignore[misc]
