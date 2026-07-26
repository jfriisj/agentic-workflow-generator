"""Explicit registry area contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RegistryKind(StrEnum):
    """Supported declarative registry areas."""

    AGENT = "agents"
    ARTIFACT = "artifacts"
    BUNDLE = "bundles"
    PERMISSION_PROFILE = "permission-profiles"
    PROFILE = "profiles"
    SETUP = "setups"
    SKILL = "skills"
    TARGET = "targets"
    WORKFLOW = "workflows"

    @property
    def directory_name(self) -> str:
        return _REGISTRY_KIND_SPECS[self].directory_name

    @property
    def file_pattern(self) -> str:
        return _REGISTRY_KIND_SPECS[self].file_pattern

    @property
    def identity_field(self) -> str:
        return _REGISTRY_KIND_SPECS[self].identity_field


@dataclass(frozen=True, slots=True)
class RegistryKindSpec:
    """Filesystem and identity contract for one registry kind."""

    directory_name: str
    file_pattern: str
    identity_field: str


_REGISTRY_KIND_SPECS = {
    RegistryKind.AGENT: RegistryKindSpec(
        directory_name="agents",
        file_pattern="*/agent.json",
        identity_field="name",
    ),
    RegistryKind.ARTIFACT: RegistryKindSpec(
        directory_name="artifacts",
        file_pattern="*/artifact.json",
        identity_field="type",
    ),
    RegistryKind.BUNDLE: RegistryKindSpec(
        directory_name="bundles",
        file_pattern="*.bundle.json",
        identity_field="name",
    ),
    RegistryKind.PERMISSION_PROFILE: RegistryKindSpec(
        directory_name="permission-profiles",
        file_pattern="*/permission-profile.json",
        identity_field="name",
    ),
    RegistryKind.PROFILE: RegistryKindSpec(
        directory_name="profiles",
        file_pattern="*.profile.json",
        identity_field="name",
    ),
    RegistryKind.SETUP: RegistryKindSpec(
        directory_name="setups",
        file_pattern="*.setup.json",
        identity_field="name",
    ),
    RegistryKind.SKILL: RegistryKindSpec(
        directory_name="skills",
        file_pattern="*/skill.json",
        identity_field="name",
    ),
    RegistryKind.TARGET: RegistryKindSpec(
        directory_name="targets",
        file_pattern="*/adapter.json",
        identity_field="name",
    ),
    RegistryKind.WORKFLOW: RegistryKindSpec(
        directory_name="workflows",
        file_pattern="*.workflow.json",
        identity_field="name",
    ),
}
