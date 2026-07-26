from dataclasses import replace

import pytest

from agentic_workflow_generator.application import (
    SetupMaterializationError,
    materialize_setup_profile,
    setup_profile_to_json,
)
from agentic_workflow_generator.domain import (
    Setup,
    SetupAnswerClassification,
    SetupMode,
    SetupOption,
    SetupOptionClassification,
    SetupQuestion,
    SetupSelection,
    SetupSelectionPatch,
)


def option(
    value: str,
    classification: SetupOptionClassification,
    *,
    bundle: str | None = None,
    targets: tuple[str, ...] | None = None,
) -> SetupOption:
    selection = (
        SetupSelectionPatch(
            bundle=bundle,
            targets=targets,
        )
        if bundle is not None or targets is not None
        else None
    )

    return SetupOption(
        value=value,
        label=value,
        classification=classification,
        reason=f"Reason for {value}.",
        selection=selection,
    )


def question(
    question_id: str,
    default_option: str,
    *options: SetupOption,
) -> SetupQuestion:
    return SetupQuestion(
        id=question_id,
        prompt=f"Prompt for {question_id}?",
        default_option=default_option,
        options=options,
    )


def setup(
    *questions: SetupQuestion,
) -> Setup:
    return Setup(
        name="lean-delivery-greenfield",
        description="Focused setup.",
        version="0.2.0",
        mode=SetupMode.GREENFIELD,
        default_selection=SetupSelection(
            bundle="lean-delivery",
            targets=(
                "opencode",
                "vscode-copilot",
            ),
        ),
        questions=questions,
    )


def standard_setup() -> Setup:
    return setup(
        question(
            "delivery-style",
            "lean",
            option(
                "lean",
                SetupOptionClassification.RECOMMENDED,
                bundle="lean-delivery",
            ),
            option(
                "blocked",
                SetupOptionClassification.BLOCKED,
            ),
        ),
        question(
            "target-platforms",
            "both",
            option(
                "both",
                SetupOptionClassification.RECOMMENDED,
                targets=(
                    "opencode",
                    "vscode-copilot",
                ),
            ),
            option(
                "opencode-only",
                SetupOptionClassification.COMPATIBLE,
                targets=("opencode",),
            ),
        ),
        question(
            "evidence",
            "required",
            option(
                "required",
                SetupOptionClassification.RECOMMENDED,
            ),
        ),
    )


def test_defaults_materialize_typed_profile() -> None:
    profile = materialize_setup_profile(
        standard_setup(),
    )

    assert profile.schema_uri == "./schemas/setup-profile.schema.json"
    assert profile.schema_version == "0.2.0"
    assert profile.mode is SetupMode.GREENFIELD
    assert profile.setup == "lean-delivery-greenfield"
    assert tuple(
        answer.selected
        for answer in profile.answers
    ) == (
        "lean",
        "both",
        "required",
    )
    assert all(
        answer.classification
        is SetupAnswerClassification.RECOMMENDED
        for answer in profile.answers
    )
    assert profile.selected == SetupSelection(
        bundle="lean-delivery",
        targets=(
            "opencode",
            "vscode-copilot",
        ),
    )
    assert profile.policy.fail_fast is True
    assert profile.policy.fallback_allowed is False


def test_compatible_override_materializes_exact_option_metadata() -> None:
    profile = materialize_setup_profile(
        standard_setup(),
        {
            "target-platforms": "opencode-only",
        },
    )

    answer = profile.answers[1]

    assert answer.classification is SetupAnswerClassification.COMPATIBLE
    assert answer.reason == "Reason for opencode-only."
    assert profile.selected.targets == ("opencode",)


def test_unknown_override_question_fails() -> None:
    with pytest.raises(
        SetupMaterializationError,
        match="unknown setup question",
    ):
        materialize_setup_profile(
            standard_setup(),
            {
                "missing": "value",
            },
        )


def test_unknown_selected_option_fails() -> None:
    with pytest.raises(
        SetupMaterializationError,
        match="selected option 'missing' does not exist",
    ):
        materialize_setup_profile(
            standard_setup(),
            {
                "delivery-style": "missing",
            },
        )


def test_blocked_selected_option_fails() -> None:
    with pytest.raises(
        SetupMaterializationError,
        match="selected blocked option 'blocked'",
    ):
        materialize_setup_profile(
            standard_setup(),
            {
                "delivery-style": "blocked",
            },
        )


def test_conflicting_bundle_patches_fail() -> None:
    conflicting = setup(
        question(
            "first",
            "a",
            option(
                "a",
                SetupOptionClassification.RECOMMENDED,
                bundle="bundle-a",
            ),
        ),
        question(
            "second",
            "b",
            option(
                "b",
                SetupOptionClassification.RECOMMENDED,
                bundle="bundle-b",
            ),
        ),
    )

    with pytest.raises(
        SetupMaterializationError,
        match="conflicting bundle selections",
    ):
        materialize_setup_profile(conflicting)


def test_conflicting_target_patches_fail() -> None:
    conflicting = setup(
        question(
            "first",
            "both",
            option(
                "both",
                SetupOptionClassification.RECOMMENDED,
                targets=(
                    "opencode",
                    "vscode-copilot",
                ),
            ),
        ),
        question(
            "second",
            "one",
            option(
                "one",
                SetupOptionClassification.RECOMMENDED,
                targets=("opencode",),
            ),
        ),
    )

    with pytest.raises(
        SetupMaterializationError,
        match="conflicting target selections",
    ):
        materialize_setup_profile(conflicting)


def test_identical_patches_do_not_conflict() -> None:
    repeated = setup(
        question(
            "first",
            "lean",
            option(
                "lean",
                SetupOptionClassification.RECOMMENDED,
                bundle="lean-delivery",
                targets=("opencode",),
            ),
        ),
        question(
            "second",
            "lean",
            option(
                "lean",
                SetupOptionClassification.COMPATIBLE,
                bundle="lean-delivery",
                targets=("opencode",),
            ),
        ),
    )

    profile = materialize_setup_profile(repeated)

    assert profile.selected == SetupSelection(
        bundle="lean-delivery",
        targets=("opencode",),
    )


def test_profile_projects_to_deterministic_json_shape() -> None:
    profile = materialize_setup_profile(
        standard_setup(),
        {
            "target-platforms": "opencode-only",
        },
    )

    assert setup_profile_to_json(profile) == {
        "$schema": "./schemas/setup-profile.schema.json",
        "schemaVersion": "0.2.0",
        "mode": "greenfield",
        "setup": "lean-delivery-greenfield",
        "answers": [
            {
                "question": "delivery-style",
                "selected": "lean",
                "classification": "recommended",
                "reason": "Reason for lean.",
            },
            {
                "question": "target-platforms",
                "selected": "opencode-only",
                "classification": "compatible",
                "reason": "Reason for opencode-only.",
            },
            {
                "question": "evidence",
                "selected": "required",
                "classification": "recommended",
                "reason": "Reason for required.",
            },
        ],
        "selected": {
            "bundle": "lean-delivery",
            "targets": [
                "opencode",
            ],
        },
        "policy": {
            "failFast": True,
            "fallbackAllowed": False,
        },
    }


def test_profile_without_schema_uri_omits_schema_field() -> None:
    profile = replace(
        materialize_setup_profile(
            standard_setup(),
        ),
        schema_uri=None,
    )

    assert "$schema" not in setup_profile_to_json(profile)


def test_missing_default_option_fails_closed() -> None:
    invalid_typed_setup = setup(
        question(
            "delivery-style",
            "missing",
            option(
                "lean",
                SetupOptionClassification.RECOMMENDED,
            ),
        ),
    )

    with pytest.raises(
        SetupMaterializationError,
        match="selected option 'missing' does not exist",
    ):
        materialize_setup_profile(invalid_typed_setup)
