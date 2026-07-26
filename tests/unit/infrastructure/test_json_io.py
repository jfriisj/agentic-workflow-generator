import json
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest

from agentic_workflow_generator.infrastructure import (
    AtomicWriteError,
    JsonDecodeFailure,
    JsonFileNotFoundError,
    JsonObject,
    JsonReadError,
    JsonRootTypeError,
    JsonSerializationError,
    read_json,
    read_json_object,
    serialize_json,
    write_json,
)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("null", None),
        ("true", True),
        ("42", 42),
        ('"text"', "text"),
        ("[1, 2]", [1, 2]),
        ('{"name": "agentic"}', {"name": "agentic"}),
    ],
)
def test_read_json_accepts_all_json_root_types(
    tmp_path: Path,
    content: str,
    expected: object,
) -> None:
    target = tmp_path / "input.json"
    target.write_text(content, encoding="utf-8")

    assert read_json(target) == expected


def test_read_json_rejects_missing_file(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.json"

    with pytest.raises(
        JsonFileNotFoundError,
        match="required JSON file not found",
    ) as captured:
        read_json(missing)

    assert captured.value.path == missing
    assert captured.value.detail == ("required JSON file not found")


def test_read_json_wraps_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "input.json"
    target.write_text("{}", encoding="utf-8")

    def fail_read_text(
        self: Path,
        *args: object,
        **kwargs: object,
    ) -> NoReturn:
        del self, args, kwargs
        raise OSError("read unavailable")

    monkeypatch.setattr(
        Path,
        "read_text",
        fail_read_text,
    )

    with pytest.raises(
        JsonReadError,
        match="read unavailable",
    ) as captured:
        read_json(target)

    assert captured.value.path == target


def test_read_json_reports_decode_location(
    tmp_path: Path,
) -> None:
    target = tmp_path / "invalid.json"
    target.write_text(
        '{\n  "name":\n}',
        encoding="utf-8",
    )

    with pytest.raises(
        JsonDecodeFailure,
        match="invalid JSON at line 3",
    ) as captured:
        read_json(target)

    assert captured.value.path == target
    assert captured.value.line == 3
    assert captured.value.column == 1
    assert captured.value.reason


def test_read_json_object_accepts_object_root(
    tmp_path: Path,
) -> None:
    target = tmp_path / "object.json"
    target.write_text(
        '{"name": "agentic"}',
        encoding="utf-8",
    )

    assert read_json_object(target) == {"name": "agentic"}


@pytest.mark.parametrize(
    ("content", "actual_type"),
    [
        ("null", "null"),
        ("true", "boolean"),
        ("1", "number"),
        ('"value"', "string"),
        ("[]", "array"),
    ],
)
def test_read_json_object_rejects_non_object_roots(
    tmp_path: Path,
    content: str,
    actual_type: str,
) -> None:
    target = tmp_path / "value.json"
    target.write_text(content, encoding="utf-8")

    with pytest.raises(
        JsonRootTypeError,
        match=(f"expected JSON object, found {actual_type}"),
    ) as captured:
        read_json_object(target)

    assert captured.value.expected == "object"
    assert captured.value.actual == actual_type


def test_serialize_json_uses_stable_format() -> None:
    value: JsonObject = {
        "name": "agentic",
        "enabled": True,
        "labels": ["æ", "ø", "å"],
    }

    assert serialize_json(value) == (
        "{\n"
        '  "name": "agentic",\n'
        '  "enabled": true,\n'
        '  "labels": [\n'
        '    "æ",\n'
        '    "ø",\n'
        '    "å"\n'
        "  ]\n"
        "}\n"
    )


def test_serialize_json_rejects_nan() -> None:
    with pytest.raises(
        JsonSerializationError,
        match="strict JSON",
    ):
        serialize_json(float("nan"))


def test_serialize_json_rejects_unsupported_value() -> None:
    unsupported = cast(Any, object())

    with pytest.raises(
        JsonSerializationError,
        match="strict JSON",
    ):
        serialize_json(unsupported)


def test_write_json_is_atomic_and_deterministic(
    tmp_path: Path,
) -> None:
    target = tmp_path / "output.json"
    value: JsonObject = {
        "version": 2,
        "enabled": True,
    }

    write_json(target, value)

    assert target.read_text(encoding="utf-8") == (
        '{\n  "version": 2,\n  "enabled": true\n}\n'
    )
    assert read_json_object(target) == value
    assert list(tmp_path.glob(".output.json.*.tmp")) == []


def test_write_json_preserves_existing_file_on_failure(
    tmp_path: Path,
) -> None:
    target = tmp_path / "missing" / "output.json"

    with pytest.raises(
        AtomicWriteError,
        match="parent directory does not exist",
    ):
        write_json(target, {"value": 1})


def test_serialized_json_is_parseable_by_stdlib() -> None:
    serialized = serialize_json({"items": [1, 2, 3]})

    assert json.loads(serialized) == {"items": [1, 2, 3]}
