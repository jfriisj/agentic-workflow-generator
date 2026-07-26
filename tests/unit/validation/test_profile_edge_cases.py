from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.validation.profiles import (
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


def test_schema_error_location_formats_array_index() -> None:
    validation_error = error(
        "invalid",
        validator="type",
        path=(
            "recommendedAgents",
            0,
        ),
    )

    assert _schema_error_location(validation_error) == ("$.recommendedAgents[0]")


def test_required_list_field_preserves_cli_message() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=[
            "recommendedAgents",
        ],
        instance={},
    )

    assert _schema_error_message(validation_error) == (
        "recommendedAgents must be a non-empty list"
    )


def test_required_string_field_preserves_cli_message() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=[
            "recommendedWorkflow",
        ],
        instance={},
    )

    assert _schema_error_message(validation_error) == (
        "recommendedWorkflow must be a non-empty string"
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
        path=("recommendedCapabilities",),
    )

    assert _schema_error_message(validation_error) == (
        "recommendedCapabilities must be a non-empty list"
    )


def test_unique_items_reports_duplicate_string() -> None:
    validation_error = error(
        "not unique",
        validator="uniqueItems",
        instance=[
            "workflow.route",
            "workflow.route",
        ],
        path=("recommendedCapabilities",),
    )

    assert _schema_error_message(validation_error) == (
        "recommendedCapabilities entry 'workflow.route' is duplicated"
    )


def test_unique_items_without_string_duplicate_falls_back() -> None:
    validation_error = error(
        "not unique",
        validator="uniqueItems",
        instance=[
            1,
            1,
        ],
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
            "recommendedRuntimeProfiles",
            0,
        ),
    )

    assert _schema_error_message(validation_error) == (
        "recommendedRuntimeProfiles[0] must be a non-empty string"
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
        path=("recommendedWorkflow",),
    )

    assert _schema_error_message(validation_error) == (
        "recommendedWorkflow must be a non-empty string"
    )


def test_array_type_preserves_list_message() -> None:
    validation_error = error(
        "wrong type",
        validator="type",
        validator_value="array",
        instance="local",
        path=("recommendedRuntimeProfiles",),
    )

    assert _schema_error_message(validation_error) == (
        "recommendedRuntimeProfiles must be a non-empty list"
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
        validator_value=[
            "name",
        ],
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


def test_missing_required_field_skips_non_string_contract_entry() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=[
            42,
            "name",
        ],
        instance={},
    )

    assert _missing_required_field(validation_error) == "name"


def test_missing_required_field_returns_none_when_present() -> None:
    validation_error = error(
        "required",
        validator="required",
        validator_value=[
            "name",
        ],
        instance={
            "name": "lean-delivery",
        },
    )

    assert _missing_required_field(validation_error) is None


def test_first_duplicate_rejects_non_list() -> None:
    assert _first_duplicate("not-a-list") is None


def test_first_duplicate_ignores_non_strings() -> None:
    assert (
        _first_duplicate(
            [
                1,
                "one",
                "two",
            ]
        )
        is None
    )


def test_first_duplicate_returns_none_without_duplicate() -> None:
    assert (
        _first_duplicate(
            [
                "one",
                "two",
            ]
        )
        is None
    )
