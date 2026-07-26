from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain import (
    Skill,
    SkillContextBudget,
)


def test_skill_domain_model_is_immutable() -> None:
    skill = Skill(
        name="implementation",
        version="1.0.0",
        description="Implements approved work.",
        provides=("implementation.code",),
        content_path="SKILL.md",
        context_budget=SkillContextBudget(max_tokens=4000),
        requires_capabilities=(),
        recommended_agents=("Implementer",),
    )

    assert skill.context_budget.max_tokens == 4000

    with pytest.raises(FrozenInstanceError):
        skill.name = "changed"  # type: ignore[misc]


def test_context_budget_is_immutable() -> None:
    budget = SkillContextBudget(max_tokens=4000)

    with pytest.raises(FrozenInstanceError):
        budget.max_tokens = 8000  # type: ignore[misc]
