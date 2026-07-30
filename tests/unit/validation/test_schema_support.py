from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.infrastructure import JsonObject
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.schema_support import (
    json_value_schema_diagnostics,
    object_schema_diagnostics,
    registry_schema_diagnostics,
    schema_error_location,
    schema_error_sort_key,
)


def test_schema_error_location_formats_mixed_path() -> None:
    error = ValidationError(
        "invalid",
        path=("items", 0, "name"),
    )

    assert schema_error_location(error) == "$.items[0].name"
    assert schema_error_sort_key(error) == (
        ("items", "0", "name"),
        "invalid",
    )


def test_registry_schema_diagnostics_are_deterministic() -> None:
    source = RegistrySource(
        kind=RegistryKind.SETUP,
        source_path=Path("registry/setups/example.setup.json"),
        data={
            "items": [],
        },
    )
    validator = Draft202012Validator(
        {
            "type": "object",
            "required": ["name"],
            "properties": {
                "items": {
                    "type": "array",
                    "minItems": 1,
                },
            },
        }
    )

    diagnostics = registry_schema_diagnostics(
        source,
        validator,
        "AWG-TEST-001",
    )

    assert tuple(item.location for item in diagnostics) == (
        "$",
        "$.items",
    )
    assert all(
        item.code == "AWG-TEST-001"
        for item in diagnostics
    )
    assert all(
        item.source_path
        == "registry/setups/example.setup.json"
        for item in diagnostics
    )
    assert all(
        item.message.startswith("schema violation: ")
        for item in diagnostics
    )


def test_object_schema_diagnostics_use_explicit_path() -> None:
    data: JsonObject = {
        "enabled": "yes",
    }
    validator = Draft202012Validator(
        {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                },
            },
        }
    )

    diagnostics = object_schema_diagnostics(
        data,
        Path(".agentic/setup-profile.json"),
        validator,
        "AWG-TEST-002",
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "AWG-TEST-002"
    assert diagnostics[0].source_path == (
        ".agentic/setup-profile.json"
    )
    assert diagnostics[0].location == "$.enabled"
    assert diagnostics[0].message.startswith(
        "schema violation: "
    )

def test_json_value_schema_diagnostics_validate_root_type() -> None:
    validator = Draft202012Validator(
        {
            "type": "object",
        }
    )

    diagnostics = json_value_schema_diagnostics(
        [],
        Path("registry/agents/example/agent.json"),
        validator,
        "AWG-TEST-003",
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "AWG-TEST-003"
    assert diagnostics[0].location == "$"
    assert diagnostics[0].message == (
        "schema violation: [] is not of type 'object'"
    )
