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
class ArtifactStatusInvariantContract:
    """Immutable fail-closed status policy for artifact evidence."""

    pass_requires_complete_evidence: bool
    pass_forbids_demonstrated_nonconformance: bool
    fail_requires_demonstrated_nonconformance: bool
    blocked_requires_unavailable_prerequisite: bool


@dataclass(frozen=True, slots=True)
class ArtifactStatusSemanticsContract:
    """Immutable artifact-specific status classification semantics."""

    pass_definition: str
    fail_definition: str
    blocked_definition: str
    mixed_condition_rule: str


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
    status_invariants: ArtifactStatusInvariantContract
    status_semantics: ArtifactStatusSemanticsContract
    allowed_statuses: tuple[str, ...]
    required_headings: tuple[str, ...]
