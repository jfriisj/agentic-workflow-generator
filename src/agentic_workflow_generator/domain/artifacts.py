"""Reusable artifact-contract domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArtifactStatus:
    """Immutable status contract for an artifact."""

    heading: str
    pattern: str


@dataclass(frozen=True, slots=True)
class ArtifactProvenanceContract:
    """Immutable provenance requirement for produced artifact evidence."""

    heading: str
    required_identities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArtifactRevisionContract:
    """Immutable revision requirement for produced artifact evidence."""

    heading: str
    pattern: str


@dataclass(frozen=True, slots=True)
class ArtifactContract:
    """Immutable reusable artifact contract.

    Workflow gate requirements, role-binding production,
    producer ownership and target materialization deliberately
    do not belong to this model.
    """

    type: str
    version: str
    description: str
    path_pattern: str
    status: ArtifactStatus
    provenance: ArtifactProvenanceContract
    revision: ArtifactRevisionContract
    allowed_statuses: tuple[str, ...]
    required_headings: tuple[str, ...]
