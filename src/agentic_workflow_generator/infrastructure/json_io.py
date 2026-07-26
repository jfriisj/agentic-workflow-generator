"""Strict deterministic JSON input and output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from .errors import (
    JsonDecodeFailure,
    JsonFileNotFoundError,
    JsonReadError,
    JsonRootTypeError,
    JsonSerializationError,
)
from .filesystem import atomic_write_text

JsonScalar: TypeAlias = bool | int | float | str | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


def read_json(path: Path) -> JsonValue:
    """Read one required strict JSON document."""

    if not path.is_file():
        raise JsonFileNotFoundError(
            path,
            "required JSON file not found",
        )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JsonReadError(
            path,
            f"could not read JSON file: {exc}",
        ) from exc

    try:
        value: JsonValue = json.loads(content)
    except json.JSONDecodeError as exc:
        raise JsonDecodeFailure(
            path,
            line=exc.lineno,
            column=exc.colno,
            reason=exc.msg,
        ) from exc

    return value


def read_json_object(path: Path) -> JsonObject:
    """Read one required JSON document with an object root."""

    value = read_json(path)

    if not isinstance(value, dict):
        raise JsonRootTypeError(
            path,
            expected="object",
            actual=_json_type_name(value),
        )

    return value


def serialize_json(value: JsonValue) -> str:
    """Serialize strict JSON with stable indentation and newline."""

    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        )
    except (TypeError, ValueError) as exc:
        raise JsonSerializationError(
            f"Value cannot be serialized as strict JSON: {exc}"
        ) from exc


def write_json(path: Path, value: JsonValue) -> None:
    """Atomically write one deterministic JSON document."""

    atomic_write_text(path, serialize_json(value))


def _json_type_name(value: JsonValue) -> str:
    if value is None:
        return "null"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, str):
        return "string"

    if isinstance(value, list):
        return "array"

    return "number"
