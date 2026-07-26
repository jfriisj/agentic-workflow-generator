from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain.profiles import Profile


def profile() -> Profile:
    return Profile(
        name="lean-delivery",
        version="0.2.0",
        description="Advisory defaults for focused delivery.",
        recommended_workflow="lean-delivery",
        recommended_agents=(
            "Orchestrator",
            "Requirements",
            "Implementer",
        ),
        recommended_capabilities=(
            "workflow.route",
            "requirements.elicit",
            "implementation.code",
        ),
        recommended_language_profiles=("language-agnostic",),
        recommended_runtime_profiles=(
            "local",
            "ci",
        ),
    )


def test_profile_preserves_advisory_metadata() -> None:
    definition = profile()

    assert definition.name == "lean-delivery"
    assert definition.version == "0.2.0"
    assert definition.recommended_workflow == "lean-delivery"
    assert definition.recommended_agents == (
        "Orchestrator",
        "Requirements",
        "Implementer",
    )
    assert definition.recommended_capabilities == (
        "workflow.route",
        "requirements.elicit",
        "implementation.code",
    )
    assert definition.recommended_language_profiles == ("language-agnostic",)
    assert definition.recommended_runtime_profiles == (
        "local",
        "ci",
    )


def test_profile_is_immutable() -> None:
    attribute = "name"

    with pytest.raises(FrozenInstanceError):
        setattr(profile(), attribute, "different")
