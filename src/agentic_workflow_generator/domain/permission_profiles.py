"""Permission profile domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BashPermission(StrEnum):
    """Supported effective shell permission levels."""

    DENY = "deny"
    LIMITED = "limited"
    ALLOW = "allow"


@dataclass(frozen=True, slots=True)
class PermissionProfile:
    """Immutable effective permission profile."""

    name: str
    version: str
    description: str
    read: bool
    write: bool
    edit: bool
    bash: BashPermission
