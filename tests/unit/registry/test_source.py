from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import (
    JsonObject,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)


def test_registry_source_preserves_source_association() -> None:
    data: JsonObject = {
        "name": "Example",
        "values": ["one", "two"],
    }

    source = RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path("registry/agents/Example/agent.json"),
        data=data,
    )

    assert source.kind is RegistryKind.AGENT
    assert source.source_path == Path("registry/agents/Example/agent.json")
    assert source.data["name"] == "Example"


def test_registry_source_copies_input_mapping() -> None:
    data: JsonObject = {"name": "Original"}

    source = RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path("registry/agents/Original/agent.json"),
        data=data,
    )
    data["name"] = "Changed"

    assert source.data["name"] == "Original"


def test_registry_source_top_level_mapping_is_read_only() -> None:
    source = RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path("registry/agents/Example/agent.json"),
        data={"name": "Example"},
    )

    with pytest.raises(TypeError):
        source.data["name"] = "Changed"  # type: ignore[index]


@pytest.mark.parametrize(
    "source_path",
    [
        Path(),
        Path("/absolute/agent.json"),
        Path("../outside/agent.json"),
        Path("registry/../outside/agent.json"),
    ],
)
def test_registry_source_rejects_unsafe_path(
    source_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match=("Registry source path must be a safe repository-relative path"),
    ):
        RegistrySource(
            kind=RegistryKind.AGENT,
            source_path=source_path,
            data={"name": "Example"},
        )


def test_registry_source_returns_detached_json_object() -> None:
    source = RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path("registry/agents/Example/agent.json"),
        data={
            "name": "Example",
            "nested": {"enabled": True},
        },
    )

    json_object = source.to_json_object()
    json_object["name"] = "Changed"

    nested = json_object["nested"]
    assert isinstance(nested, dict)
    nested["enabled"] = False

    assert source.data["name"] == "Example"
    assert source.data["nested"] == {"enabled": True}
