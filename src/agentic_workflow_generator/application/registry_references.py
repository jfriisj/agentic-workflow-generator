"""Canonical registry-reference validation application service."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_workflow_generator.registry import ProjectPaths

from .registry_snapshot import load_validated_registry_snapshot
from .target_materialization import load_active_composition


@dataclass(frozen=True, slots=True)
class RegistryReferenceSummary:
    """Deterministic counts for the complete validated registry."""

    agent_count: int
    target_count: int
    workflow_count: int
    profile_count: int
    artifact_count: int
    skill_capability_count: int


@dataclass(frozen=True, slots=True)
class RegistryReferenceValidationResult:
    """Successful canonical registry-reference validation result."""

    summary: RegistryReferenceSummary


def validate_registry_references(
    paths: ProjectPaths,
) -> RegistryReferenceValidationResult:
    """Validate registry references and active-composition identity drift."""

    snapshot = load_validated_registry_snapshot(paths)
    load_active_composition(
        paths,
        registry=snapshot,
    )

    capabilities = frozenset(
        capability
        for skill in snapshot.skills
        for capability in skill.provides
    )

    return RegistryReferenceValidationResult(
        summary=RegistryReferenceSummary(
            agent_count=len(snapshot.agents),
            target_count=len(snapshot.targets),
            workflow_count=len(snapshot.workflows),
            profile_count=len(snapshot.profiles),
            artifact_count=len(snapshot.artifacts),
            skill_capability_count=len(capabilities),
        )
    )
