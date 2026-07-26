"""Immutable registry source records."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)

from .kinds import RegistryKind


@dataclass(frozen=True, slots=True)
class RegistrySource:
    """One loaded registry object and its source association."""

    kind: RegistryKind
    source_path: Path
    data: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        if (
            not self.source_path.parts
            or self.source_path.is_absolute()
            or ".." in self.source_path.parts
        ):
            raise ValueError(
                "Registry source path must be a safe repository-relative path"
            )

        snapshot: JsonObject = deepcopy(dict(self.data))
        immutable_data = MappingProxyType(snapshot)
        object.__setattr__(
            self,
            "data",
            cast(
                Mapping[str, JsonValue],
                immutable_data,
            ),
        )

    def to_json_object(self) -> JsonObject:
        """Return a detached JSON object for external libraries."""

        return deepcopy(dict(self.data))
