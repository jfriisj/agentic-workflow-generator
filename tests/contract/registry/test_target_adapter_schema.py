from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryKind,
    RegistryLoader,
)

REPOSITORY_ROOT = Path(__file__).parents[3]


def target_adapter_schema() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        read_json_object(
            REPOSITORY_ROOT
            / ".agentic"
            / "schemas"
            / "registry"
            / "target-adapter.schema.json"
        ),
    )


def first_target_adapter() -> dict[str, Any]:
    paths = ProjectPaths(REPOSITORY_ROOT)
    sources = RegistryLoader(paths).load(
        RegistryKind.TARGET
    )

    return cast(
        dict[str, Any],
        sources[0].to_json_object(),
    )


def test_target_adapter_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        target_adapter_schema()
    )


def test_registered_target_adapters_match_schema() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    validator = Draft202012Validator(
        target_adapter_schema()
    )
    sources = RegistryLoader(paths).load(
        RegistryKind.TARGET
    )

    errors = [
        (
            source.source_path,
            error.json_path,
            error.message,
        )
        for source in sources
        for error in validator.iter_errors(
            source.to_json_object()
        )
    ]

    assert errors == []


def test_schema_rejects_unknown_fields() -> None:
    adapter = first_target_adapter()
    adapter["supportedFeatures"] = {
        "agents": True,
    }

    errors = list(
        Draft202012Validator(
            target_adapter_schema()
        ).iter_errors(adapter)
    )

    assert any(
        error.validator == "additionalProperties"
        and "supportedFeatures" in error.message
        for error in errors
    )


def test_schema_requires_permission_mapping() -> None:
    adapter = first_target_adapter()
    del adapter["permissionMapping"]

    errors = list(
        Draft202012Validator(
            target_adapter_schema()
        ).iter_errors(adapter)
    )

    assert any(
        error.validator == "required"
        and "permissionMapping" in error.message
        for error in errors
    )
