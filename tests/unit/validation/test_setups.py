import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from agentic_workflow_generator.domain import (
    SetupMode,
    SetupOptionClassification,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.setups import (
    BLOCKED_SELECTION_DIAGNOSTIC,
    DEFAULT_CLASSIFICATION_DIAGNOSTIC,
    DEFAULT_OPTION_DIAGNOSTIC,
    DUPLICATE_NAME_DIAGNOSTIC,
    DUPLICATE_OPTION_DIAGNOSTIC,
    DUPLICATE_QUESTION_DIAGNOSTIC,
    FILE_NAME_DIAGNOSTIC,
    NO_EFFECT_SELECTION_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC,
    UNKNOWN_BUNDLE_DIAGNOSTIC,
    UNKNOWN_TARGET_DIAGNOSTIC,
    ProjectedSetupBundle,
    SetupReferenceData,
    SetupValidationResult,
    validate_setup_registry,
)


def setup_schema() -> JsonObject:
    return cast(
        JsonObject,
        json.loads(
            Path(".agentic/schemas/registry/setup.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    )


def setup_data() -> JsonObject:
    return {
        "name": "lean-delivery-greenfield",
        "description": "Focused guided setup.",
        "version": "0.2.0",
        "mode": "greenfield",
        "defaultSelection": {
            "bundle": "lean-delivery",
            "targets": [
                "opencode",
                "vscode-copilot",
            ],
        },
        "questions": [
            {
                "id": "target-platforms",
                "prompt": "Which targets should be generated?",
                "defaultOption": "both",
                "options": [
                    {
                        "value": "both",
                        "label": "Both targets",
                        "classification": "recommended",
                        "reason": "Both adapters are supported.",
                        "selection": {
                            "targets": [
                                "opencode",
                                "vscode-copilot",
                            ],
                        },
                    },
                    {
                        "value": "opencode-only",
                        "label": "OpenCode only",
                        "classification": "compatible",
                        "reason": "OpenCode is supported.",
                        "selection": {
                            "targets": [
                                "opencode",
                            ],
                        },
                    },
                    {
                        "value": "unsupported",
                        "label": "Unsupported",
                        "classification": "blocked",
                        "reason": "The adapter is not registered.",
                    },
                ],
            },
        ],
    }


def source(
    *,
    filename: str = "lean-delivery-greenfield.setup.json",
    data: JsonObject | None = None,
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.SETUP,
        source_path=Path(f"registry/setups/{filename}"),
        data=setup_data() if data is None else data,
    )


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
                name="opencode-bundle",
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
    filename: str = "lean-delivery-greenfield.setup.json",
) -> SetupValidationResult:
    return validate_setup_registry(
        (
            source(
                filename=filename,
                data=data,
            ),
        ),
        setup_schema(),
        references(),
    )


def test_valid_setup_is_parsed() -> None:
    result = validate()

    assert result.is_valid
    assert not result.diagnostics
    assert result.setups[0].mode is SetupMode.GREENFIELD
    assert result.setups[0].default_selection.bundle == "lean-delivery"
    assert result.setups[0].questions[0].options[0].classification is (
        SetupOptionClassification.RECOMMENDED
    )


@pytest.mark.parametrize(
    ("mutator", "location"),
    [
        (
            lambda data: data.update(
                {
                    "defaultBundle": "lean-delivery",
                }
            ),
            "defaultBundle",
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                cast(list[JsonValue], data["questions"])[0],
            ).update(
                {
                    "recommended": [
                        "both",
                    ],
                }
            ),
            "questions[0].recommended",
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                cast(
                    list[JsonValue],
                    cast(
                        dict[str, JsonValue],
                        cast(list[JsonValue], data["questions"])[0],
                    )["options"],
                )[0],
            ).update(
                {
                    "recommends": {
                        "bundle": "lean-delivery",
                    },
                }
            ),
            "questions[0].options[0].recommends",
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                cast(
                    dict[str, JsonValue],
                    cast(
                        list[JsonValue],
                        cast(
                            dict[str, JsonValue],
                            cast(list[JsonValue], data["questions"])[0],
                        )["options"],
                    )[0],
                )["selection"],
            ).update(
                {
                    "workflow": "lean-delivery",
                }
            ),
            "questions[0].options[0].selection.workflow",
        ),
    ],
)
def test_obsolete_fields_are_rejected_before_schema(
    mutator: Callable[[JsonObject], None],
    location: str,
) -> None:
    data = setup_data()
    mutator(data)

    result = validate(data)

    assert result.setups == ()
    assert result.diagnostics[0].code == OBSOLETE_FIELD_DIAGNOSTIC
    assert result.diagnostics[0].location == location


def test_obsolete_agent_selection_is_rejected() -> None:
    data = setup_data()
    questions = cast(
        list[JsonValue],
        data["questions"],
    )
    question = cast(
        dict[str, JsonValue],
        questions[0],
    )
    options = cast(
        list[JsonValue],
        question["options"],
    )
    option = cast(
        dict[str, JsonValue],
        options[0],
    )
    selection = cast(
        dict[str, JsonValue],
        option["selection"],
    )
    selection["agents"] = ["Requirements"]

    result = validate(data)

    assert result.setups == ()
    assert result.diagnostics[0].code == (OBSOLETE_FIELD_DIAGNOSTIC)
    assert result.diagnostics[0].location == (
        "questions[0].options[0].selection.agents"
    )


def test_schema_failure_is_structured() -> None:
    data = setup_data()
    data["questions"] = []

    result = validate(data)

    assert result.setups == ()
    assert result.diagnostics[0].code == SCHEMA_DIAGNOSTIC
    assert result.diagnostics[0].location == "$.questions"


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (
            lambda data: cast(
                dict[str, JsonValue],
                data["defaultSelection"],
            ).update(
                {
                    "bundle": "missing",
                }
            ),
            UNKNOWN_BUNDLE_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                data["defaultSelection"],
            ).update(
                {
                    "targets": [
                        "missing",
                    ],
                }
            ),
            UNKNOWN_TARGET_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                data["defaultSelection"],
            ).update(
                {
                    "bundle": "opencode-bundle",
                    "targets": [
                        "vscode-copilot",
                    ],
                }
            ),
            TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                list[JsonValue],
                data["questions"],
            ).append(cast(list[JsonValue], data["questions"])[0]),
            DUPLICATE_QUESTION_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                cast(list[JsonValue], data["questions"])[0],
            ).update(
                {
                    "defaultOption": "missing",
                }
            ),
            DEFAULT_OPTION_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                cast(list[JsonValue], data["questions"])[0],
            ).update(
                {
                    "defaultOption": "opencode-only",
                }
            ),
            DEFAULT_CLASSIFICATION_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                list[JsonValue],
                cast(
                    dict[str, JsonValue],
                    cast(list[JsonValue], data["questions"])[0],
                )["options"],
            ).append(
                cast(
                    list[JsonValue],
                    cast(
                        dict[str, JsonValue],
                        cast(list[JsonValue], data["questions"])[0],
                    )["options"],
                )[0]
            ),
            DUPLICATE_OPTION_DIAGNOSTIC,
        ),
        (
            lambda data: cast(
                dict[str, JsonValue],
                cast(
                    list[JsonValue],
                    cast(
                        dict[str, JsonValue],
                        cast(list[JsonValue], data["questions"])[0],
                    )["options"],
                )[2],
            ).update(
                {
                    "selection": {
                        "bundle": "lean-delivery",
                    },
                }
            ),
            BLOCKED_SELECTION_DIAGNOSTIC,
        ),
    ],
)
def test_semantic_failures_are_structured(
    mutator: Callable[[JsonObject], None],
    code: str,
) -> None:
    data = setup_data()
    mutator(data)

    result = validate(data)

    assert result.diagnostics[0].code == code


def test_supported_non_default_option_must_change_effective_selection() -> None:
    data = setup_data()
    selected_option = cast(
        dict[str, JsonValue],
        cast(
            list[JsonValue],
            cast(
                dict[str, JsonValue],
                cast(list[JsonValue], data["questions"])[0],
            )["options"],
        )[1],
    )
    selected_option["selection"] = {
        "targets": [
            "opencode",
            "vscode-copilot",
        ],
    }

    result = validate(data)

    assert result.diagnostics[0].code == NO_EFFECT_SELECTION_DIAGNOSTIC
    assert result.diagnostics[0].location == "questions[0].options[1].selection"


def test_supported_non_default_option_without_selection_is_rejected() -> None:
    data = setup_data()
    selected_option = cast(
        dict[str, JsonValue],
        cast(
            list[JsonValue],
            cast(
                dict[str, JsonValue],
                cast(list[JsonValue], data["questions"])[0],
            )["options"],
        )[1],
    )
    del selected_option["selection"]

    result = validate(data)

    assert result.diagnostics[0].code == NO_EFFECT_SELECTION_DIAGNOSTIC
    assert result.diagnostics[0].location == "questions[0].options[1].selection"


def test_option_bundle_patch_validates_inherited_targets() -> None:
    data = setup_data()
    option = cast(
        dict[str, JsonValue],
        cast(
            list[JsonValue],
            cast(
                dict[str, JsonValue],
                cast(list[JsonValue], data["questions"])[0],
            )["options"],
        )[1],
    )
    option["selection"] = {
        "bundle": "opencode-bundle",
    }

    result = validate(data)

    assert result.diagnostics[0].code == (TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC)


def test_file_name_mismatch_is_rejected() -> None:
    result = validate(
        filename="wrong.setup.json",
    )

    assert result.diagnostics[0].code == FILE_NAME_DIAGNOSTIC


def test_duplicate_setup_name_is_rejected() -> None:
    result = validate_setup_registry(
        (
            source(),
            source(
                filename="duplicate.setup.json",
            ),
        ),
        setup_schema(),
        references(),
    )

    assert result.diagnostics[-1].code == (DUPLICATE_NAME_DIAGNOSTIC)
