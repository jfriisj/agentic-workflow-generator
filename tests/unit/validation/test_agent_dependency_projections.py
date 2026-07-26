from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import JsonValue
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.agents import (
    AgentDependencyProjectionError,
    project_permission_profile_names,
    project_skill_capabilities,
)


def skill_source(
    provides: JsonValue,
    *,
    name: str = "implementation",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.SKILL,
        source_path=Path(f"registry/skills/{name}/skill.json"),
        data={
            "name": name,
            "provides": provides,
        },
    )


def permission_source(
    name: JsonValue,
    *,
    folder: str = "implementation",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.PERMISSION_PROFILE,
        source_path=Path(
            f"registry/permission-profiles/{folder}/permission-profile.json"
        ),
        data={"name": name},
    )


def test_skill_capabilities_are_projected() -> None:
    result = project_skill_capabilities(
        (
            skill_source(
                [
                    "implementation.code",
                    "implementation.update-tests",
                ]
            ),
            skill_source(
                ["implementation.code"],
                name="duplicate-provider",
            ),
        )
    )

    assert result == frozenset(
        {
            "implementation.code",
            "implementation.update-tests",
        }
    )


@pytest.mark.parametrize(
    "provides",
    [
        None,
        [],
    ],
)
def test_skill_provides_must_be_non_empty_list(
    provides: JsonValue,
) -> None:
    with pytest.raises(
        AgentDependencyProjectionError,
        match="provides must be a non-empty list",
    ):
        project_skill_capabilities((skill_source(provides),))


@pytest.mark.parametrize(
    "capability",
    [
        42,
        "",
        " ",
    ],
)
def test_skill_capability_must_be_non_empty_string(
    capability: JsonValue,
) -> None:
    with pytest.raises(
        AgentDependencyProjectionError,
        match=r"provides\[0\] must be a non-empty string",
    ):
        project_skill_capabilities((skill_source([capability]),))


def test_permission_profile_names_are_projected() -> None:
    result = project_permission_profile_names(
        (
            permission_source("implementation"),
            permission_source(
                "read-only",
                folder="read-only",
            ),
        )
    )

    assert result == frozenset(
        {
            "implementation",
            "read-only",
        }
    )


@pytest.mark.parametrize(
    "name",
    [
        None,
        42,
        "",
        " ",
    ],
)
def test_permission_profile_name_must_be_non_empty(
    name: JsonValue,
) -> None:
    with pytest.raises(
        AgentDependencyProjectionError,
        match="name must be a non-empty string",
    ):
        project_permission_profile_names((permission_source(name),))
