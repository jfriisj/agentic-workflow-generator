"""Reusable skill domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkillContextBudget:
    """Immutable context budget for a reusable skill."""

    max_tokens: int


@dataclass(frozen=True, slots=True)
class Skill:
    """Immutable reusable skill definition.

    Runtime selection, agent assignment, authorization,
    artifact ownership and workflow routing deliberately
    do not belong to this model.
    """

    name: str
    version: str
    description: str
    provides: tuple[str, ...]
    content_path: str
    context_budget: SkillContextBudget
    requires_capabilities: tuple[str, ...]
    recommended_agents: tuple[str, ...]
