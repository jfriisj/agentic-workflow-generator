"""Capability-coverage application service."""

from __future__ import annotations

from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.capability_coverage import (
    CapabilityCoverageResult,
    validate_capability_coverage,
)

from .registry_snapshot import load_validated_registry_snapshot


def analyze_capability_coverage(
    paths: ProjectPaths,
) -> CapabilityCoverageResult:
    """Load validated registry authority and analyze capability coverage."""

    snapshot = load_validated_registry_snapshot(paths)

    return validate_capability_coverage(
        snapshot.bundles,
        snapshot.skills,
    )
