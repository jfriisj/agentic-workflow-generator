"""Target adapter domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

TargetPermissionValue: TypeAlias = str | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TargetOutputPath:
    """One named repository-relative target output path."""

    name: str
    path: str


@dataclass(frozen=True, slots=True)
class TargetPermissionSetting:
    """One target-specific permission setting."""

    name: str
    value: TargetPermissionValue


@dataclass(frozen=True, slots=True)
class TargetPermissionMapping:
    """One permission profile mapped to target-specific settings."""

    permission_profile: str
    settings: tuple[TargetPermissionSetting, ...]


@dataclass(frozen=True, slots=True)
class TargetAdapter:
    """Immutable validated target adapter definition."""

    name: str
    version: str
    description: str
    output_paths: tuple[TargetOutputPath, ...]
    owned_paths: tuple[str, ...]
    permission_mappings: tuple[TargetPermissionMapping, ...]
