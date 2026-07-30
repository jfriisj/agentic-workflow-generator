from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.registry_schemas import (
    DOCUMENT_INPUT_DIAGNOSTIC,
    DOCUMENT_SCHEMA_DIAGNOSTIC,
    SCHEMA_DEFINITION_DIAGNOSTIC,
    RegistrySchemaValidationResult,
    validate_registry_schemas,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> ProjectPaths:
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        tmp_path / ".agentic" / "schemas",
    )
    return ProjectPaths(tmp_path)


def test_real_registry_schemas_validate_all_documents() -> None:
    result = validate_registry_schemas(ProjectPaths(REPOSITORY_ROOT))

    assert result.is_valid
    assert result.checked_document_count == 46
    assert result.diagnostics == ()


def test_agent_version_pattern_is_enforced(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = sorted((tmp_path / "registry" / "agents").glob("*/agent.json"))[0]
    document = _read_json(document_path)
    document["version"] = "0.2"
    _write_json(document_path, document)

    diagnostic = _matching_diagnostic(
        validate_registry_schemas(paths),
        paths.root,
        document_path,
        "does not match",
    )

    assert diagnostic.code == DOCUMENT_SCHEMA_DIAGNOSTIC
    assert diagnostic.location == "$.version"


def test_workflow_states_must_be_non_empty(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = _workflow_path(tmp_path)
    document = _read_json(document_path)
    document["states"] = []
    _write_json(document_path, document)

    diagnostic = _matching_diagnostic(
        validate_registry_schemas(paths),
        paths.root,
        document_path,
        "should be non-empty",
    )

    assert diagnostic.code == DOCUMENT_SCHEMA_DIAGNOSTIC
    assert diagnostic.location == "$.states"


def test_workflow_terminal_state_const_is_enforced(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = _workflow_path(tmp_path)
    document = _read_json(document_path)
    states = cast(list[Any], document["states"])

    for state_value in states:
        state = cast(dict[str, Any], state_value)

        if state.get("terminal") is True:
            state["terminal"] = False
            break
    else:
        raise AssertionError("Expected one terminal workflow state.")

    _write_json(document_path, document)

    diagnostic = _matching_diagnostic(
        validate_registry_schemas(paths),
        paths.root,
        document_path,
        "is not valid under any of the given schemas",
    )

    assert diagnostic.code == DOCUMENT_SCHEMA_DIAGNOSTIC
    assert diagnostic.location is not None
    assert diagnostic.location.startswith("$.states[")


def test_permission_bash_enum_is_enforced(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = (
        tmp_path
        / "registry"
        / "permission-profiles"
        / "read-only"
        / "permission-profile.json"
    )
    document = _read_json(document_path)
    document["bash"] = "root"
    _write_json(document_path, document)

    diagnostic = _matching_diagnostic(
        validate_registry_schemas(paths),
        paths.root,
        document_path,
        "is not one of",
    )

    assert diagnostic.code == DOCUMENT_SCHEMA_DIAGNOSTIC
    assert diagnostic.location == "$.bash"


def test_target_owned_paths_are_required(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = tmp_path / "registry" / "targets" / "opencode" / "adapter.json"
    document = _read_json(document_path)
    del document["ownedPaths"]
    _write_json(document_path, document)

    diagnostic = _matching_diagnostic(
        validate_registry_schemas(paths),
        paths.root,
        document_path,
        "ownedPaths",
    )

    assert diagnostic.code == DOCUMENT_SCHEMA_DIAGNOSTIC
    assert diagnostic.location == "$"


@pytest.mark.parametrize(
    (
        "case",
        "expected_message",
        "expected_location",
    ),
    [
        ("missing-name", "name", "$"),
        ("empty-name", "should be non-empty", "$.name"),
        (
            "invalid-owned-paths-type",
            "is not of type 'array'",
            "$.ownedPaths",
        ),
        (
            "empty-owned-paths",
            "should be non-empty",
            "$.ownedPaths",
        ),
        (
            "empty-owned-path",
            "should be non-empty",
            "$.ownedPaths[0]",
        ),
        (
            "duplicate-owned-path",
            "has non-unique elements",
            "$.ownedPaths",
        ),
        (
            "parent-owned-path",
            "does not match",
            "$.ownedPaths[0]",
        ),
        (
            "absolute-owned-path",
            "does not match",
            "$.ownedPaths[0]",
        ),
        (
            "invalid-description-type",
            "is not of type 'string'",
            "$.description",
        ),
        (
            "empty-version",
            "does not match",
            "$.version",
        ),
        (
            "obsolete-supported-features",
            "supportedFeatures",
            "$",
        ),
    ],
)
def test_target_schema_shape_is_enforced(
    tmp_path: Path,
    case: str,
    expected_message: str,
    expected_location: str,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = _target_path(tmp_path)
    document = _read_json(document_path)
    _mutate_target_schema_case(document, case)
    _write_json(document_path, document)

    diagnostic = _matching_diagnostic(
        validate_registry_schemas(paths),
        paths.root,
        document_path,
        expected_message,
    )

    assert diagnostic.code == DOCUMENT_SCHEMA_DIAGNOSTIC
    assert diagnostic.location == expected_location


def test_non_object_document_root_is_a_schema_failure(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = sorted((tmp_path / "registry" / "agents").glob("*/agent.json"))[0]
    document_path.write_text(
        "[]\n",
        encoding="utf-8",
    )

    diagnostic = _matching_diagnostic(
        validate_registry_schemas(paths),
        paths.root,
        document_path,
        "is not of type 'object'",
    )

    assert diagnostic.code == DOCUMENT_SCHEMA_DIAGNOSTIC
    assert diagnostic.location == "$"


def test_invalid_json_document_is_reported_individually(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    document_path = sorted((tmp_path / "registry" / "agents").glob("*/agent.json"))[0]
    document_path.write_text(
        "{\n",
        encoding="utf-8",
    )

    result = validate_registry_schemas(paths)

    assert result.checked_document_count == 46
    diagnostic = next(
        item for item in result.diagnostics if item.code == DOCUMENT_INPUT_DIAGNOSTIC
    )
    assert diagnostic.source_path == (document_path.relative_to(tmp_path).as_posix())


def test_invalid_schema_definition_is_reported(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    schema_path = tmp_path / ".agentic" / "schemas" / "registry" / "agent.schema.json"
    schema = _read_json(schema_path)
    schema["type"] = 42
    _write_json(schema_path, schema)

    result = validate_registry_schemas(paths)

    diagnostic = next(
        item for item in result.diagnostics if item.code == SCHEMA_DEFINITION_DIAGNOSTIC
    )
    assert diagnostic.source_path == (".agentic/schemas/registry/agent.schema.json")
    assert "invalid Draft 2020-12 schema" in (diagnostic.message)


def _target_path(root: Path) -> Path:
    path = root / "registry" / "targets" / "opencode" / "adapter.json"

    if not path.is_file():
        raise AssertionError("Expected opencode target adapter.")

    return path


def _mutate_target_schema_case(
    document: dict[str, Any],
    case: str,
) -> None:
    if case == "missing-name":
        document.pop("name", None)
        return

    if case == "empty-name":
        document["name"] = ""
        return

    if case == "invalid-owned-paths-type":
        document["ownedPaths"] = "not-a-list"
        return

    if case == "empty-owned-paths":
        document["ownedPaths"] = []
        return

    owned_paths = cast(
        list[Any],
        document["ownedPaths"],
    )

    if case == "empty-owned-path":
        owned_paths[0] = ""
        return

    if case == "duplicate-owned-path":
        owned_paths.append(owned_paths[0])
        return

    if case == "parent-owned-path":
        owned_paths[0] = "../unsafe"
        return

    if case == "absolute-owned-path":
        owned_paths[0] = "/tmp/unsafe"
        return

    if case == "invalid-description-type":
        document["description"] = {
            "not": "a-string",
        }
        return

    if case == "empty-version":
        document["version"] = ""
        return

    if case == "obsolete-supported-features":
        document["supportedFeatures"] = {
            "agents": True,
        }
        return

    raise AssertionError(f"Unknown target schema mutation: {case}")


def _workflow_path(root: Path) -> Path:
    for candidate in sorted((root / "registry" / "workflows").glob("*.workflow.json")):
        if _read_json(candidate).get("name") == ("orchestrated-delivery"):
            return candidate

    raise AssertionError("Expected orchestrated-delivery workflow.")


def _matching_diagnostic(
    result: RegistrySchemaValidationResult,
    repository_root: Path,
    document_path: Path,
    message: str,
) -> Diagnostic:
    diagnostics = result.diagnostics
    relative_path = document_path.relative_to(repository_root).as_posix()

    return next(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.source_path == relative_path and message in diagnostic.message
    )


def _read_json(path: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
