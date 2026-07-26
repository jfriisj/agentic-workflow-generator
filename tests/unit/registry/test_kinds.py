import pytest

from agentic_workflow_generator.registry import RegistryKind


@pytest.mark.parametrize(
    (
        "kind",
        "directory_name",
        "file_pattern",
        "identity_field",
    ),
    [
        (
            RegistryKind.AGENT,
            "agents",
            "*/agent.json",
            "name",
        ),
        (
            RegistryKind.ARTIFACT,
            "artifacts",
            "*/artifact.json",
            "type",
        ),
        (
            RegistryKind.BUNDLE,
            "bundles",
            "*.bundle.json",
            "name",
        ),
        (
            RegistryKind.PERMISSION_PROFILE,
            "permission-profiles",
            "*/permission-profile.json",
            "name",
        ),
        (
            RegistryKind.PROFILE,
            "profiles",
            "*.profile.json",
            "name",
        ),
        (
            RegistryKind.SETUP,
            "setups",
            "*.setup.json",
            "name",
        ),
        (
            RegistryKind.SKILL,
            "skills",
            "*/skill.json",
            "name",
        ),
        (
            RegistryKind.TARGET,
            "targets",
            "*/adapter.json",
            "name",
        ),
        (
            RegistryKind.WORKFLOW,
            "workflows",
            "*.workflow.json",
            "name",
        ),
    ],
)
def test_registry_kind_contract(
    kind: RegistryKind,
    directory_name: str,
    file_pattern: str,
    identity_field: str,
) -> None:
    assert kind.directory_name == directory_name
    assert kind.file_pattern == file_pattern
    assert kind.identity_field == identity_field


def test_registry_kind_iteration_order_is_stable() -> None:
    assert tuple(RegistryKind) == (
        RegistryKind.AGENT,
        RegistryKind.ARTIFACT,
        RegistryKind.BUNDLE,
        RegistryKind.PERMISSION_PROFILE,
        RegistryKind.PROFILE,
        RegistryKind.SETUP,
        RegistryKind.SKILL,
        RegistryKind.TARGET,
        RegistryKind.WORKFLOW,
    )
