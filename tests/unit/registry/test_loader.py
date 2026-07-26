from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    write_json,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryAreaNotFoundError,
    RegistryFilesNotFoundError,
    RegistryKind,
    RegistryLoader,
    RegistryRootNotFoundError,
    RegistrySourcePathError,
)


def write_registry_file(
    repository_root: Path,
    relative_path: str,
    data: JsonObject,
) -> Path:
    path = repository_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, data)
    return path


def test_discover_rejects_missing_registry_root(
    tmp_path: Path,
) -> None:
    loader = RegistryLoader(ProjectPaths(tmp_path))

    with pytest.raises(
        RegistryRootNotFoundError,
        match="required registry root not found",
    ) as captured:
        loader.discover(RegistryKind.AGENT)

    assert captured.value.path == tmp_path / "registry"


def test_discover_rejects_missing_registry_area(
    tmp_path: Path,
) -> None:
    (tmp_path / "registry").mkdir()
    loader = RegistryLoader(ProjectPaths(tmp_path))

    with pytest.raises(
        RegistryAreaNotFoundError,
        match="required agents registry area not found",
    ) as captured:
        loader.discover(RegistryKind.AGENT)

    assert captured.value.kind is RegistryKind.AGENT


def test_discover_rejects_area_without_matching_files(
    tmp_path: Path,
) -> None:
    area = tmp_path / "registry" / "agents"
    area.mkdir(parents=True)
    write_registry_file(
        tmp_path,
        "registry/agents/Example/unrelated.json",
        {"name": "Example"},
    )
    loader = RegistryLoader(ProjectPaths(tmp_path))

    with pytest.raises(
        RegistryFilesNotFoundError,
        match="no agents registry files match",
    ) as captured:
        loader.discover(RegistryKind.AGENT)

    assert captured.value.pattern == "*/agent.json"


def test_discover_returns_deterministic_order(
    tmp_path: Path,
) -> None:
    second = write_registry_file(
        tmp_path,
        "registry/agents/Zulu/agent.json",
        {"name": "Zulu"},
    )
    first = write_registry_file(
        tmp_path,
        "registry/agents/Alpha/agent.json",
        {"name": "Alpha"},
    )
    loader = RegistryLoader(ProjectPaths(tmp_path))

    assert loader.discover(RegistryKind.AGENT) == (
        first.resolve(),
        second.resolve(),
    )


def test_artifact_discovery_ignores_schema_files(
    tmp_path: Path,
) -> None:
    contract = write_registry_file(
        tmp_path,
        "registry/artifacts/Report/artifact.json",
        {"type": "Report"},
    )
    write_registry_file(
        tmp_path,
        ("registry/artifacts/Report/artifact.schema.json"),
        {"type": "object"},
    )
    loader = RegistryLoader(ProjectPaths(tmp_path))

    assert loader.discover(RegistryKind.ARTIFACT) == (contract.resolve(),)


def test_load_preserves_kind_path_and_data(
    tmp_path: Path,
) -> None:
    write_registry_file(
        tmp_path,
        "registry/skills/example/skill.json",
        {
            "name": "example",
            "provides": ["example-capability"],
        },
    )
    loader = RegistryLoader(ProjectPaths(tmp_path))

    sources = loader.load(RegistryKind.SKILL)

    assert len(sources) == 1
    assert sources[0].kind is RegistryKind.SKILL
    assert sources[0].source_path == Path("registry/skills/example/skill.json")
    assert sources[0].data["name"] == "example"


def test_discover_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    outside = tmp_path / "outside.json"
    write_json(outside, {"name": "Outside"})

    source = repository / "registry" / "agents" / "Outside" / "agent.json"
    source.parent.mkdir(parents=True)
    source.symlink_to(outside)

    loader = RegistryLoader(ProjectPaths(repository))

    with pytest.raises(
        RegistrySourcePathError,
        match="escapes the repository root",
    ):
        loader.discover(RegistryKind.AGENT)


def test_discover_rejects_matching_directory(
    tmp_path: Path,
) -> None:
    matching_directory = tmp_path / "registry" / "agents" / "Example" / "agent.json"
    matching_directory.mkdir(parents=True)
    loader = RegistryLoader(ProjectPaths(tmp_path))

    with pytest.raises(
        RegistrySourcePathError,
        match="discovered path is not a file",
    ):
        loader.discover(RegistryKind.AGENT)


def test_load_all_uses_registry_kind_order(
    tmp_path: Path,
) -> None:
    fixtures: dict[RegistryKind, tuple[str, JsonObject]] = {
        RegistryKind.AGENT: (
            "registry/agents/Agent/agent.json",
            {"name": "Agent"},
        ),
        RegistryKind.ARTIFACT: (
            "registry/artifacts/Report/artifact.json",
            {"type": "Report"},
        ),
        RegistryKind.BUNDLE: (
            "registry/bundles/example.bundle.json",
            {"name": "bundle"},
        ),
        RegistryKind.PERMISSION_PROFILE: (
            ("registry/permission-profiles/read-only/permission-profile.json"),
            {"name": "read-only"},
        ),
        RegistryKind.PROFILE: (
            "registry/profiles/example.profile.json",
            {"name": "profile"},
        ),
        RegistryKind.SETUP: (
            "registry/setups/example.setup.json",
            {"name": "setup"},
        ),
        RegistryKind.SKILL: (
            "registry/skills/example/skill.json",
            {"name": "skill"},
        ),
        RegistryKind.TARGET: (
            "registry/targets/example/adapter.json",
            {"name": "target"},
        ),
        RegistryKind.WORKFLOW: (
            "registry/workflows/example.workflow.json",
            {"name": "workflow"},
        ),
    }

    for relative_path, data in fixtures.values():
        write_registry_file(
            tmp_path,
            relative_path,
            data,
        )

    loader = RegistryLoader(ProjectPaths(tmp_path))

    assert tuple(source.kind for source in loader.load_all()) == tuple(RegistryKind)
