"""Shared mechanical JSON Schema diagnostic support."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import RegistrySource


def schema_error_sort_key(
    error: ValidationError,
) -> tuple[tuple[str, ...], str]:
    """Return the deterministic generic schema-error order."""

    return (
        tuple(str(component) for component in error.absolute_path),
        error.message,
    )


def schema_error_location(
    error: ValidationError,
) -> str:
    """Render a JSON-style location beginning at the document root."""

    location = "$"

    for component in error.absolute_path:
        if isinstance(component, int):
            location += f"[{component}]"
        else:
            location += f".{component}"

    return location



def missing_required_field(
    error: ValidationError,
) -> str | None:
    """Return the first missing string field from a required error."""

    if not isinstance(error.instance, dict):
        return None

    required = error.validator_value

    if not isinstance(required, list):
        return None

    return next(
        (
            field
            for field in required
            if isinstance(field, str)
            and field not in error.instance
        ),
        None,
    )


def first_duplicate_string(
    instance: object,
) -> str | None:
    """Return the first duplicated string in a list."""

    if not isinstance(instance, list):
        return None

    seen: set[str] = set()

    for entry in instance:
        if not isinstance(entry, str):
            continue

        if entry in seen:
            return entry

        seen.add(entry)

    return None


def field_schema_error_message(
    error: ValidationError,
    list_fields: frozenset[str],
) -> str:
    """Render stable field-oriented schema diagnostics."""

    path = tuple(error.absolute_path)
    field_name = (
        str(path[0])
        if path
        else missing_required_field(error)
    )

    if error.validator == "required" and field_name is not None:
        if field_name in list_fields:
            return f"{field_name} must be a non-empty list"

        return f"{field_name} must be a non-empty string"

    if error.validator == "minItems" and field_name is not None:
        return f"{field_name} must be a non-empty list"

    if error.validator == "uniqueItems" and field_name is not None:
        duplicate = first_duplicate_string(error.instance)

        if duplicate is not None:
            return (
                f"{field_name} entry {duplicate!r} "
                "is duplicated"
            )

    if (
        error.validator == "pattern"
        and field_name == "version"
        and (
            not isinstance(error.instance, str)
            or not error.instance.strip()
        )
    ):
        return "version must be a non-empty string"

    if error.validator == "minLength" and path:
        if len(path) == 1:
            return (
                f"{field_name} must be a non-empty string"
            )

        if len(path) == 2:
            return (
                f"{field_name}[{path[1]}] "
                "must be a non-empty string"
            )

    if error.validator == "type" and field_name is not None:
        expected = error.validator_value

        if expected == "string":
            return (
                f"{field_name} must be a non-empty string"
            )

        if expected == "array":
            return f"{field_name} must be a non-empty list"

    return f"schema violation: {error.message}"


def strict_missing_required_field(
    error: ValidationError,
) -> str:
    """Return the missing field from a valid required error."""

    instance = cast(
        dict[str, object],
        error.instance,
    )
    required = cast(
        list[str],
        error.validator_value,
    )

    return next(
        field
        for field in required
        if field not in instance
    )


def dot_schema_error_location(
    error: ValidationError,
) -> str:
    """Render the stable dot-path schema location."""

    path = tuple(error.absolute_path)

    if error.validator == "required":
        missing = strict_missing_required_field(error)

        if path:
            return ".".join(
                (
                    *(str(component) for component in path),
                    missing,
                )
            )

        return missing

    return ".".join(
        str(component)
        for component in path
    )


def dot_schema_error_sort_key(
    error: ValidationError,
) -> tuple[str, str]:
    """Return deterministic ordering for dot-path diagnostics."""

    return (
        dot_schema_error_location(error),
        error.message,
    )


def dot_schema_error_message(
    error: ValidationError,
) -> str:
    """Render stable dot-path schema messages."""

    location = dot_schema_error_location(error)

    if error.validator == "required":
        return f"{location} is required"

    if error.validator == "minItems":
        return f"{location} must be a non-empty list"

    if error.validator == "uniqueItems":
        return f"{location} entries must be unique"

    if error.validator == "minLength":
        return f"{location} must be a non-empty string"

    if error.validator == "type":
        expected = error.validator_value

        if expected == "array":
            return f"{location} must be a non-empty list"

        if expected == "object":
            return f"{location} must be an object"

        if expected == "boolean":
            return f"{location} must be a boolean"

        return f"{location} must be a non-empty string"

    if (
        error.validator == "pattern"
        and location == "version"
    ):
        return "version must be a semantic version"

    return f"schema violation: {error.message}"


def dot_path_registry_schema_diagnostics(
    source: RegistrySource,
    validator: Draft202012Validator,
    diagnostic_code: str,
) -> tuple[Diagnostic, ...]:
    """Validate a registry source using dot-path diagnostics."""

    errors = sorted(
        validator.iter_errors(source.to_json_object()),
        key=dot_schema_error_sort_key,
    )

    return tuple(
        Diagnostic(
            code=diagnostic_code,
            message=dot_schema_error_message(error),
            source_path=source.source_path.as_posix(),
            location=dot_schema_error_location(error),
        )
        for error in errors
    )


def custom_registry_schema_diagnostics(
    source: RegistrySource,
    validator: Draft202012Validator,
    diagnostic_code: str,
    message_formatter: Callable[[ValidationError], str],
) -> tuple[Diagnostic, ...]:
    """Validate a registry source with a custom message formatter."""

    errors = sorted(
        validator.iter_errors(source.to_json_object()),
        key=schema_error_sort_key,
    )

    return tuple(
        Diagnostic(
            code=diagnostic_code,
            message=message_formatter(error),
            source_path=source.source_path.as_posix(),
            location=schema_error_location(error),
        )
        for error in errors
    )

def registry_schema_diagnostics(
    source: RegistrySource,
    validator: Draft202012Validator,
    diagnostic_code: str,
) -> tuple[Diagnostic, ...]:
    """Validate one registry source with generic schema messages."""

    errors = sorted(
        validator.iter_errors(source.to_json_object()),
        key=schema_error_sort_key,
    )

    return tuple(
        Diagnostic(
            code=diagnostic_code,
            message=f"schema violation: {error.message}",
            source_path=source.source_path.as_posix(),
            location=schema_error_location(error),
        )
        for error in errors
    )


def json_value_schema_diagnostics(
    data: JsonValue,
    source_path: Path,
    validator: Draft202012Validator,
    diagnostic_code: str,
) -> tuple[Diagnostic, ...]:
    """Validate one arbitrary JSON value with generic schema messages."""

    errors = sorted(
        validator.iter_errors(data),
        key=schema_error_sort_key,
    )

    return tuple(
        Diagnostic(
            code=diagnostic_code,
            message=f"schema violation: {error.message}",
            source_path=source_path.as_posix(),
            location=schema_error_location(error),
        )
        for error in errors
    )


def object_schema_diagnostics(
    data: JsonObject,
    source_path: Path,
    validator: Draft202012Validator,
    diagnostic_code: str,
) -> tuple[Diagnostic, ...]:
    """Validate one JSON object with generic schema messages."""

    return json_value_schema_diagnostics(
        data,
        source_path,
        validator,
        diagnostic_code,
    )
