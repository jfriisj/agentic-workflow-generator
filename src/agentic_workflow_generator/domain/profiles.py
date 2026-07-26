"""Reusable advisory project-profile domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Profile:
    """Immutable advisory project profile.

    Concrete workflow selection, agent instances, role bindings,
    permissions, skills, artifacts and targets deliberately belong
    to bundle and setup composition instead.
    """

    name: str
    version: str
    description: str
    recommended_workflow: str
    recommended_agents: tuple[str, ...]
    recommended_capabilities: tuple[str, ...]
    recommended_language_profiles: tuple[str, ...]
    recommended_runtime_profiles: tuple[str, ...]
