from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import (
    JsonObject,
)
from agentic_workflow_generator.registry import (
    DuplicateRegistryIdentityError,
    RegistryEntryNotFoundError,
    RegistryIdentityError,
    RegistryIndex,
    RegistryKind,
    RegistrySource,
)


def source(
    kind: RegistryKind,
    identity: object,
    *,
    path_name: str,
    include_identity: bool = True,
) -> RegistrySource:
    data: JsonObject = {}

    if include_identity:
        data[kind.identity_field] = identity  # type: ignore[assignment]

    return RegistrySource(
        kind=kind,
        source_path=Path(path_name),
        data=data,
    )


def test_index_uses_kind_specific_identity_field() -> None:
    agent = source(
        RegistryKind.AGENT,
        "Agent",
        path_name=("registry/agents/Agent/agent.json"),
    )
    artifact = source(
        RegistryKind.ARTIFACT,
        "Report",
        path_name=("registry/artifacts/Report/artifact.json"),
    )

    index = RegistryIndex([agent, artifact])

    assert (
        index.get(
            RegistryKind.AGENT,
            "Agent",
        )
        is agent
    )
    assert (
        index.get(
            RegistryKind.ARTIFACT,
            "Report",
        )
        is artifact
    )


def test_index_preserves_source_order() -> None:
    second = source(
        RegistryKind.AGENT,
        "Second",
        path_name=("registry/agents/Second/agent.json"),
    )
    first = source(
        RegistryKind.AGENT,
        "First",
        path_name=("registry/agents/First/agent.json"),
    )

    index = RegistryIndex([second, first])

    assert index.sources(RegistryKind.AGENT) == (
        second,
        first,
    )
    assert index.identities(RegistryKind.AGENT) == (
        "Second",
        "First",
    )
    assert index.count(RegistryKind.AGENT) == 2
    assert index.count(RegistryKind.BUNDLE) == 0


def test_index_rejects_missing_identity() -> None:
    missing = source(
        RegistryKind.AGENT,
        "unused",
        path_name=("registry/agents/Missing/agent.json"),
        include_identity=False,
    )

    with pytest.raises(
        RegistryIdentityError,
        match="field is missing",
    ) as captured:
        RegistryIndex([missing])

    assert captured.value.identity_field == "name"


@pytest.mark.parametrize(
    ("identity", "reason"),
    [
        (42, "value must be a string"),
        ("", "value must not be empty"),
        (" Agent", "value must be trimmed"),
        ("Agent ", "value must be trimmed"),
    ],
)
def test_index_rejects_invalid_identity(
    identity: object,
    reason: str,
) -> None:
    invalid = source(
        RegistryKind.AGENT,
        identity,
        path_name=("registry/agents/Invalid/agent.json"),
    )

    with pytest.raises(
        RegistryIdentityError,
        match=reason,
    ):
        RegistryIndex([invalid])


def test_index_rejects_duplicate_identity() -> None:
    first = source(
        RegistryKind.AGENT,
        "Agent",
        path_name=("registry/agents/First/agent.json"),
    )
    duplicate = source(
        RegistryKind.AGENT,
        "Agent",
        path_name=("registry/agents/Second/agent.json"),
    )

    with pytest.raises(
        DuplicateRegistryIdentityError,
        match="duplicate agents identity",
    ) as captured:
        RegistryIndex([first, duplicate])

    assert captured.value.first_path == (first.source_path)
    assert captured.value.duplicate_path == (duplicate.source_path)


def test_index_allows_same_identity_across_kinds() -> None:
    agent = source(
        RegistryKind.AGENT,
        "shared",
        path_name=("registry/agents/shared/agent.json"),
    )
    skill = source(
        RegistryKind.SKILL,
        "shared",
        path_name=("registry/skills/shared/skill.json"),
    )

    index = RegistryIndex([agent, skill])

    assert (
        index.get(
            RegistryKind.AGENT,
            "shared",
        )
        is agent
    )
    assert (
        index.get(
            RegistryKind.SKILL,
            "shared",
        )
        is skill
    )


def test_get_rejects_unknown_identity() -> None:
    index = RegistryIndex([])

    with pytest.raises(
        RegistryEntryNotFoundError,
        match="Unknown agents registry identity",
    ) as captured:
        index.get(RegistryKind.AGENT, "Missing")

    assert captured.value.identity == "Missing"


def test_entries_by_kind_is_read_only() -> None:
    entry = source(
        RegistryKind.AGENT,
        "Agent",
        path_name=("registry/agents/Agent/agent.json"),
    )
    index = RegistryIndex([entry])

    with pytest.raises(TypeError):
        index.entries_by_kind[RegistryKind.AGENT]["Other"] = entry  # type: ignore[index]
