"""Reusable advisory agent-profile domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """Immutable reusable agent profile.

    Runtime ownership, selected skills, produced artifacts and
    workflow bindings deliberately do not belong to this model.
    """

    name: str
    version: str
    role: str
    description: str
    recommended_responsibilities: tuple[str, ...]
    default_guardrails: tuple[str, ...]
    recommended_capabilities: tuple[str, ...]
    default_permission_profile: str
