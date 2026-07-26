from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.validation.agents import (
    _first_duplicate,
    _missing_required_field,
    _schema_error_location,
    _schema_error_message,
)


def error(
    message: str,
    *,
    validator: str,
    validator_value: object = None,
    instance: object = None,
    path: tuple[str | int, ...] = (),
) -> ValidationError:
    return ValidationError(
        message,
        validator=validator,
        validator_value=validator_value,
        instance=instance,
        path=path,
    )


def test_schema_location_formats_object_and_array_path() -> None:
    validation_error = error(
        "invalid item",
        validator="type",
        path=(
            "recommendedCapabilities",
            0,
        ),
    )

    assert _schema_error_location(validation_error) == "$.recommendedCapabilities[0]"


def test_required_list_field_preserves_cli_message() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=[
            "recommendedCapabilities",
        ],
        instance={},
    )

    assert _schema_error_message(validation_error) == (
        "recommendedCapabilities must be a non-empty list"
    )


def test_required_string_field_preserves_cli_message() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=[
            "defaultPermissionProfile",
        ],
        instance={},
    )

    assert _schema_error_message(validation_error) == (
        "defaultPermissionProfile must be a non-empty string"
    )


def test_empty_version_pattern_preserves_cli_message() -> None:
    validation_error = error(
        "pattern mismatch",
        validator="pattern",
        instance="",
        path=("version",),
    )

    assert _schema_error_message(validation_error) == (
        "version must be a non-empty string"
    )


def test_non_empty_version_pattern_uses_schema_message() -> None:
    validation_error = error(
        "pattern mismatch",
        validator="pattern",
        instance="invalid",
        path=("version",),
    )

    assert _schema_error_message(validation_error) == (
        "schema violation: pattern mismatch"
    )


def test_min_items_preserves_list_message() -> None:
    validation_error = error(
        "too short",
        validator="minItems",
        instance=[],
        path=("defaultGuardrails",),
    )

    assert _schema_error_message(validation_error) == (
        "defaultGuardrails must be a non-empty list"
    )


def test_unique_items_reports_duplicate_string() -> None:
    validation_error = error(
        "not unique",
        validator="uniqueItems",
        instance=[
            1,
            "review.tests",
            "review.tests",
        ],
        path=("recommendedCapabilities",),
    )

    assert _schema_error_message(validation_error) == (
        "recommendedCapabilities entry 'review.tests' is duplicated"
    )


def test_unique_items_without_string_duplicate_falls_back() -> None:
    validation_error = error(
        "not unique",
        validator="uniqueItems",
        instance=[1, 1],
        path=("recommendedCapabilities",),
    )

    assert _schema_error_message(validation_error) == ("schema violation: not unique")


def test_min_length_top_level_preserves_string_message() -> None:
    validation_error = error(
        "too short",
        validator="minLength",
        instance="",
        path=("description",),
    )

    assert _schema_error_message(validation_error) == (
        "description must be a non-empty string"
    )


def test_min_length_array_entry_preserves_string_message() -> None:
    validation_error = error(
        "too short",
        validator="minLength",
        instance="",
        path=(
            "defaultGuardrails",
            0,
        ),
    )

    assert _schema_error_message(validation_error) == (
        "defaultGuardrails[0] must be a non-empty string"
    )


def test_deep_min_length_path_uses_schema_message() -> None:
    validation_error = error(
        "too short",
        validator="minLength",
        instance="",
        path=(
            "nested",
            "items",
            0,
        ),
    )

    assert _schema_error_message(validation_error) == ("schema violation: too short")


def test_string_type_preserves_string_message() -> None:
    validation_error = error(
        "wrong type",
        validator="type",
        validator_value="string",
        instance=42,
        path=("role",),
    )

    assert _schema_error_message(validation_error) == (
        "role must be a non-empty string"
    )


def test_array_type_preserves_list_message() -> None:
    validation_error = error(
        "wrong type",
        validator="type",
        validator_value="array",
        instance="wrong",
        path=("defaultGuardrails",),
    )

    assert _schema_error_message(validation_error) == (
        "defaultGuardrails must be a non-empty list"
    )


def test_other_type_uses_schema_message() -> None:
    validation_error = error(
        "wrong type",
        validator="type",
        validator_value="object",
        instance=[],
        path=("value",),
    )

    assert _schema_error_message(validation_error) == ("schema violation: wrong type")


def test_missing_required_field_rejects_non_object() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=["name"],
        instance=[],
    )

    assert _missing_required_field(validation_error) is None


def test_missing_required_field_rejects_invalid_contract() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value="name",
        instance={},
    )

    assert _missing_required_field(validation_error) is None


def test_missing_required_field_returns_none_when_present() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=["name"],
        instance={"name": "Agent"},
    )

    assert _missing_required_field(validation_error) is None


def test_first_duplicate_rejects_non_list() -> None:
    assert _first_duplicate("not-a-list") is None


def test_first_duplicate_returns_none_without_duplicate() -> None:
    assert _first_duplicate([1, "one", "two"]) is None
