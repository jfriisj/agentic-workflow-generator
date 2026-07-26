from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain import (
    Setup,
    SetupAnswer,
    SetupAnswerClassification,
    SetupMode,
    SetupOption,
    SetupOptionClassification,
    SetupPolicy,
    SetupProfile,
    SetupQuestion,
    SetupSelection,
    SetupSelectionPatch,
)


def setup_definition() -> Setup:
    return Setup(
        name="lean-delivery-greenfield",
        description="Focused guided delivery setup.",
        version="0.2.0",
        mode=SetupMode.GREENFIELD,
        default_selection=SetupSelection(
            bundle="lean-delivery",
            targets=(
                "opencode",
                "vscode-copilot",
            ),
        ),
        questions=(
            SetupQuestion(
                id="target-platforms",
                prompt="Which targets should be generated?",
                default_option="both",
                options=(
                    SetupOption(
                        value="both",
                        label="Both targets",
                        classification=(SetupOptionClassification.RECOMMENDED),
                        reason="Both adapters are supported.",
                        selection=SetupSelectionPatch(
                            bundle=None,
                            targets=(
                                "opencode",
                                "vscode-copilot",
                            ),
                        ),
                    ),
                    SetupOption(
                        value="unsupported",
                        label="Unsupported target",
                        classification=SetupOptionClassification.BLOCKED,
                        reason="The adapter is not registered.",
                        selection=None,
                    ),
                ),
            ),
        ),
    )


def test_setup_preserves_selection_boundaries() -> None:
    setup = setup_definition()

    assert setup.mode is SetupMode.GREENFIELD
    assert setup.default_selection.bundle == "lean-delivery"
    assert setup.questions[0].default_option == "both"
    assert setup.questions[0].options[0].selection == (
        SetupSelectionPatch(
            bundle=None,
            targets=(
                "opencode",
                "vscode-copilot",
            ),
        )
    )


def test_setup_profile_preserves_materialized_decision() -> None:
    profile = SetupProfile(
        schema_uri="./schemas/setup-profile.schema.json",
        schema_version="0.2.0",
        mode=SetupMode.GREENFIELD,
        setup="lean-delivery-greenfield",
        answers=(
            SetupAnswer(
                question="target-platforms",
                selected="both",
                classification=(SetupAnswerClassification.RECOMMENDED),
                reason="Both adapters are supported.",
            ),
        ),
        selected=SetupSelection(
            bundle="lean-delivery",
            targets=(
                "opencode",
                "vscode-copilot",
            ),
        ),
        policy=SetupPolicy(
            fail_fast=True,
            fallback_allowed=False,
        ),
    )

    assert profile.selected.bundle == "lean-delivery"
    assert profile.policy.fail_fast
    assert not profile.policy.fallback_allowed


@pytest.mark.parametrize(
    ("value", "attribute"),
    [
        (
            setup_definition(),
            "name",
        ),
        (
            setup_definition().questions[0],
            "prompt",
        ),
        (
            setup_definition().questions[0].options[0],
            "reason",
        ),
    ],
)
def test_setup_models_are_immutable(
    value: object,
    attribute: str,
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(
            value,
            attribute,
            "changed",
        )
