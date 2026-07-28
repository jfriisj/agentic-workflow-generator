from pathlib import Path

from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.infrastructure import JsonObject
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.setups import (
    OBSOLETE_FIELD_DIAGNOSTIC,
    _schema_error_location,
    _validate_obsolete_fields,
)


def source(data: JsonObject) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.SETUP,
        source_path=Path("registry/setups/example.setup.json"),
        data=data,
    )


def test_schema_location_formats_array_indexes() -> None:
    error = ValidationError(
        "invalid",
        path=(
            "questions",
            0,
            "options",
            1,
        ),
    )

    assert _schema_error_location(error) == ("$.questions[0].options[1]")


def test_default_selection_obsolete_field_is_reported() -> None:
    diagnostics = _validate_obsolete_fields(
        source(
            {
                "defaultSelection": {
                    "bundle": "lean-delivery",
                    "targets": [
                        "opencode",
                    ],
                    "profile": "lean-delivery",
                },
            }
        )
    )

    assert diagnostics[0].code == OBSOLETE_FIELD_DIAGNOSTIC
    assert diagnostics[0].location == ("defaultSelection.profile")


def test_non_list_questions_are_ignored_by_obsolete_scan() -> None:
    assert not _validate_obsolete_fields(
        source(
            {
                "questions": "invalid",
            }
        )
    )


def test_non_object_question_is_ignored_by_obsolete_scan() -> None:
    assert not _validate_obsolete_fields(
        source(
            {
                "questions": [
                    "invalid",
                ],
            }
        )
    )


def test_non_list_options_are_ignored_by_obsolete_scan() -> None:
    assert not _validate_obsolete_fields(
        source(
            {
                "questions": [
                    {
                        "options": "invalid",
                    },
                ],
            }
        )
    )


def test_non_object_option_is_ignored_by_obsolete_scan() -> None:
    assert not _validate_obsolete_fields(
        source(
            {
                "questions": [
                    {
                        "options": [
                            "invalid",
                        ],
                    },
                ],
            }
        )
    )


def test_non_object_selection_is_ignored_by_obsolete_scan() -> None:
    assert not _validate_obsolete_fields(
        source(
            {
                "questions": [
                    {
                        "options": [
                            {
                                "selection": "invalid",
                            },
                        ],
                    },
                ],
            }
        )
    )
