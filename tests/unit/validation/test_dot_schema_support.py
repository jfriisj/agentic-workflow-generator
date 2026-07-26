from typing import cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.validation.schema_support import (
    dot_schema_error_location,
    dot_schema_error_message,
    dot_schema_error_sort_key,
    strict_missing_required_field,
)


def first_error(
    schema: dict[str, object],
    instance: object,
) -> ValidationError:
    return cast(
        ValidationError,
        next(
            Draft202012Validator(schema).iter_errors(
                instance
            )
        ),
    )


def test_nested_required_field_uses_dot_path() -> None:
    error = first_error(
        {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "required": ["name"],
                },
            },
        },
        {
            "nested": {},
        },
    )

    assert strict_missing_required_field(error) == "name"
    assert dot_schema_error_location(error) == "nested.name"
    assert dot_schema_error_message(error) == (
        "nested.name is required"
    )
    assert dot_schema_error_sort_key(error) == (
        "nested.name",
        error.message,
    )


def test_semantic_version_message_is_stable() -> None:
    error = first_error(
        {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "pattern": r"^\\d+\\.\\d+\\.\\d+$",
                },
            },
        },
        {
            "version": "invalid",
        },
    )

    assert dot_schema_error_location(error) == "version"
    assert dot_schema_error_message(error) == (
        "version must be a semantic version"
    )


def test_dot_schema_type_messages_are_stable() -> None:
    expectations = (
        ("array", "value must be a non-empty list"),
        ("object", "value must be an object"),
        ("boolean", "value must be a boolean"),
        ("string", "value must be a non-empty string"),
    )

    for expected_type, expected_message in expectations:
        error = first_error(
            {
                "type": "object",
                "properties": {
                    "value": {
                        "type": expected_type,
                    },
                },
            },
            {
                "value": None,
            },
        )

        assert dot_schema_error_message(error) == (
            expected_message
        )
