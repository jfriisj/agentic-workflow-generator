import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from jsonschema.exceptions import ValidationError

import agentic_workflow_generator.validation.setup_profiles as setup_profiles_module
from agentic_workflow_generator.domain import (
    Setup,
    SetupMode,
    SetupOption,
    SetupOptionClassification,
    SetupQuestion,
    SetupSelection,
    SetupSelectionPatch,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.validation.setup_profiles import (
    BLOCKED_OPTION_DIAGNOSTIC,
    CLASSIFICATION_DIAGNOSTIC,
    DUPLICATE_ANSWER_DIAGNOSTIC,
    LEGACY_FIELD_DIAGNOSTIC,
    MISSING_ANSWER_DIAGNOSTIC,
    MODE_MISMATCH_DIAGNOSTIC,
    REASON_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    SELECTED_MISMATCH_DIAGNOSTIC,
    SELECTION_CONFLICT_DIAGNOSTIC,
    TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC,
    UNKNOWN_BUNDLE_DIAGNOSTIC,
    UNKNOWN_OPTION_DIAGNOSTIC,
    UNKNOWN_QUESTION_DIAGNOSTIC,
    UNKNOWN_SETUP_DIAGNOSTIC,
    UNKNOWN_TARGET_DIAGNOSTIC,
    SetupProfileValidationResult,
    validate_setup_profile,
)
from agentic_workflow_generator.validation.setups import (
    ProjectedSetupBundle,
    SetupReferenceData,
)


def setup_profile_schema() -> JsonObject:
    return cast(
        JsonObject,
        json.loads(
            Path(".agentic/schemas/setup-profile.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    )


def setup_definition() -> Setup:
    return Setup(
        name="lean-delivery-greenfield",
        description="Focused guided setup.",
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
                id="delivery-style",
                prompt="How should delivery be controlled?",
                default_option="lean",
                options=(
                    SetupOption(
                        value="lean",
                        label="Lean",
                        classification=(SetupOptionClassification.RECOMMENDED),
                        reason="Lean delivery is appropriate.",
                        selection=SetupSelectionPatch(
                            bundle="lean-delivery",
                            targets=None,
                        ),
                    ),
                    SetupOption(
                        value="review",
                        label="Review heavy",
                        classification=(SetupOptionClassification.COMPATIBLE),
                        reason="Review-heavy delivery is supported.",
                        selection=SetupSelectionPatch(
                            bundle="review-heavy-delivery",
                            targets=None,
                        ),
                    ),
                    SetupOption(
                        value="unsafe",
                        label="Unsafe",
                        classification=(SetupOptionClassification.BLOCKED),
                        reason="Unsafe delivery is blocked.",
                        selection=None,
                    ),
                ),
            ),
            SetupQuestion(
                id="target-platforms",
                prompt="Which targets should be generated?",
                default_option="both",
                options=(
                    SetupOption(
                        value="both",
                        label="Both",
                        classification=(SetupOptionClassification.RECOMMENDED),
                        reason="Both targets are supported.",
                        selection=SetupSelectionPatch(
                            bundle=None,
                            targets=(
                                "opencode",
                                "vscode-copilot",
                            ),
                        ),
                    ),
                    SetupOption(
                        value="opencode-only",
                        label="OpenCode only",
                        classification=(SetupOptionClassification.COMPATIBLE),
                        reason="OpenCode is supported.",
                        selection=SetupSelectionPatch(
                            bundle=None,
                            targets=("opencode",),
                        ),
                    ),
                ),
            ),
        ),
    )


def profile_data() -> JsonObject:
    return {
        "$schema": "./schemas/setup-profile.schema.json",
        "schemaVersion": "0.2.0",
        "mode": "greenfield",
        "setup": "lean-delivery-greenfield",
        "answers": [
            {
                "question": "delivery-style",
                "selected": "lean",
                "classification": "recommended",
                "reason": "Lean delivery is appropriate.",
            },
            {
                "question": "target-platforms",
                "selected": "both",
                "classification": "recommended",
                "reason": "Both targets are supported.",
            },
        ],
        "selected": {
            "bundle": "lean-delivery",
            "targets": [
                "opencode",
                "vscode-copilot",
            ],
        },
        "policy": {
            "failFast": True,
            "fallbackAllowed": False,
        },
    }


def references() -> SetupReferenceData:
    return SetupReferenceData(
        bundles=(
            ProjectedSetupBundle(
                name="lean-delivery",
                targets=frozenset(
                    {
                        "opencode",
                        "vscode-copilot",
                    }
                ),
            ),
            ProjectedSetupBundle(
                name="review-heavy-delivery",
                targets=frozenset(
                    {
                        "opencode",
                    }
                ),
            ),
        ),
        targets=frozenset(
            {
                "opencode",
                "vscode-copilot",
            }
        ),
    )


def validate(
    data: JsonObject | None = None,
    *,
    setups: tuple[Setup, ...] | None = None,
) -> SetupProfileValidationResult:
    return validate_setup_profile(
        profile_data() if data is None else data,
        Path(".agentic/setup-profile.json"),
        setup_profile_schema(),
        (setup_definition(),) if setups is None else setups,
        references(),
    )


def answer(
    data: JsonObject,
    index: int,
) -> dict[str, JsonValue]:
    return cast(
        dict[str, JsonValue],
        cast(list[JsonValue], data["answers"])[index],
    )


def selected(
    data: JsonObject,
) -> dict[str, JsonValue]:
    return cast(
        dict[str, JsonValue],
        data["selected"],
    )


def test_valid_setup_profile_is_parsed() -> None:
    result = validate()

    assert result.is_valid
    assert result.profile is not None
    assert result.profile.selected.bundle == "lean-delivery"
    assert len(result.profile.answers) == 2


def test_legacy_selected_field_is_rejected_before_schema() -> None:
    data = profile_data()
    selected(data)["workflow"] = "lean-delivery"

    result = validate(data)

    assert result.profile is None
    assert result.diagnostics[0].code == LEGACY_FIELD_DIAGNOSTIC
    assert result.diagnostics[0].location == "selected.workflow"


def test_schema_failure_prevents_parsing() -> None:
    data = profile_data()
    data["answers"] = []

    result = validate(data)

    assert result.profile is None
    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (
            lambda data: data.update(
                {
                    "setup": "missing",
                }
            ),
            UNKNOWN_SETUP_DIAGNOSTIC,
        ),
        (
            lambda data: data.update(
                {
                    "mode": "brownfield",
                }
            ),
            MODE_MISMATCH_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                list[JsonValue],
                data["answers"],
            ).append(cast(list[JsonValue], data["answers"])[0]),
            DUPLICATE_ANSWER_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                list[JsonValue],
                data["answers"],
            ).pop(),
            MISSING_ANSWER_DIAGNOSTIC,
        ),
        (
            lambda data: answer(data, 0).update(
                {
                    "question": "missing",
                }
            ),
            UNKNOWN_QUESTION_DIAGNOSTIC,
        ),
        (
            lambda data: answer(data, 0).update(
                {
                    "selected": "missing",
                }
            ),
            UNKNOWN_OPTION_DIAGNOSTIC,
        ),
        (
            lambda data: answer(data, 0).update(
                {
                    "selected": "unsafe",
                    "classification": "recommended",
                    "reason": "Unsafe delivery is blocked.",
                }
            ),
            BLOCKED_OPTION_DIAGNOSTIC,
        ),
        (
            lambda data: answer(data, 0).update(
                {
                    "classification": "compatible",
                }
            ),
            CLASSIFICATION_DIAGNOSTIC,
        ),
        (
            lambda data: answer(data, 0).update(
                {
                    "reason": "Drifted reason.",
                }
            ),
            REASON_DIAGNOSTIC,
        ),
        (
            lambda data: selected(data).update(
                {
                    "bundle": "review-heavy-delivery",
                }
            ),
            SELECTED_MISMATCH_DIAGNOSTIC,
        ),
        (
            lambda data: selected(data).update(
                {
                    "bundle": "missing",
                }
            ),
            UNKNOWN_BUNDLE_DIAGNOSTIC,
        ),
        (
            lambda data: selected(data).update(
                {
                    "targets": [
                        "missing",
                    ],
                }
            ),
            UNKNOWN_TARGET_DIAGNOSTIC,
        ),
        (
            lambda data: selected(data).update(
                {
                    "bundle": "review-heavy-delivery",
                    "targets": [
                        "vscode-copilot",
                    ],
                }
            ),
            TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC,
        ),
    ],
)
def test_semantic_failures_are_structured(
    mutator: Callable[[JsonObject], None],
    code: str,
) -> None:
    data = profile_data()
    mutator(data)

    result = validate(data)

    assert any(diagnostic.code == code for diagnostic in result.diagnostics)


def test_conflicting_bundle_patches_are_rejected() -> None:
    setup = setup_definition()
    target_question = setup.questions[1]
    conflicting_option = replace(
        target_question.options[0],
        selection=SetupSelectionPatch(
            bundle="review-heavy-delivery",
            targets=(
                "opencode",
                "vscode-copilot",
            ),
        ),
    )
    conflicting_question = replace(
        target_question,
        options=(
            conflicting_option,
            *target_question.options[1:],
        ),
    )
    conflicting_setup = replace(
        setup,
        questions=(
            setup.questions[0],
            conflicting_question,
        ),
    )

    result = validate(setups=(conflicting_setup,))

    assert any(
        diagnostic.code == SELECTION_CONFLICT_DIAGNOSTIC
        for diagnostic in result.diagnostics
    )


def test_non_object_selected_reaches_schema_validation() -> None:
    data = profile_data()
    data["selected"] = "invalid"

    result = validate(data)

    assert result.profile is None
    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC
    assert result.diagnostics[0].location == "$.selected"


def test_schema_diagnostic_formats_answer_array_index() -> None:
    data = profile_data()
    answer(data, 0).pop("reason")

    result = validate(data)

    assert result.profile is None
    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC
    assert result.diagnostics[0].location == "$.answers[0]"


def test_conflicting_target_patches_are_rejected() -> None:
    setup = setup_definition()
    delivery_question = setup.questions[0]
    conflicting_delivery_option = replace(
        delivery_question.options[0],
        selection=SetupSelectionPatch(
            bundle="lean-delivery",
            targets=("opencode",),
        ),
    )
    conflicting_delivery_question = replace(
        delivery_question,
        options=(
            conflicting_delivery_option,
            *delivery_question.options[1:],
        ),
    )
    conflicting_setup = replace(
        setup,
        questions=(
            conflicting_delivery_question,
            setup.questions[1],
        ),
    )

    result = validate(setups=(conflicting_setup,))

    assert any(
        diagnostic.code == SELECTION_CONFLICT_DIAGNOSTIC
        and diagnostic.location == "selected.targets"
        for diagnostic in result.diagnostics
    )


def test_setup_profile_schema_location_wrapper_delegates() -> None:
    error = ValidationError(
        "reason is required",
        path=["answers", 0],
    )

    assert (
        setup_profiles_module._schema_error_location(error)
        == "$.answers[0]"
    )
