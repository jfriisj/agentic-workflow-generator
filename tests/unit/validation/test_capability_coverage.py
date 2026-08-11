"""Tests for typed global capability-coverage analysis."""

from __future__ import annotations

from agentic_workflow_generator.domain import (
    Bundle,
    RoleBinding,
    RoleBindingType,
    Skill,
    SkillContextBudget,
)
from agentic_workflow_generator.validation.capability_coverage import (
    DUPLICATE_PROVIDER_DIAGNOSTIC,
    MISSING_CAPABILITY_DIAGNOSTIC,
    UNUSED_CAPABILITY_DIAGNOSTIC,
    validate_capability_coverage,
)


def binding(
    role_name: str,
    *capabilities: str,
) -> RoleBinding:
    return RoleBinding(
        role_name=role_name,
        binding_type=RoleBindingType.STATE_OWNER,
        agent_instance=f"{role_name}-worker",
        required_capabilities=capabilities,
        selected_skills=(),
        produces=(),
        input_artifacts=(),
        responsibilities=("Own the assigned role.",),
        guardrails=("Remain within the assigned role.",),
        workflow_state="State",
        workflow_gate="gate",
    )


def bundle(
    name: str,
    *bindings: RoleBinding,
) -> Bundle:
    return Bundle(
        name=name,
        description=f"{name} bundle.",
        version="1.0.0",
        profile=name,
        workflow=name,
        agent_instances=(),
        role_bindings=bindings,
        separation_policies=(),
        skills=(),
        artifacts=(),
        targets=(),
    )


def skill(
    name: str,
    *capabilities: str,
) -> Skill:
    return Skill(
        name=name,
        version="1.0.0",
        description=f"{name} skill.",
        provides=capabilities,
        content_path="SKILL.md",
        context_budget=SkillContextBudget(max_tokens=4000),
        requires_capabilities=(),
        recommended_agents=(),
    )


def test_complete_coverage_is_projected_deterministically() -> None:
    result = validate_capability_coverage(
        (
            bundle(
                "z-bundle",
                binding(
                    "reviewer",
                    "review.tests",
                    "implementation.code",
                ),
            ),
            bundle(
                "a-bundle",
                binding(
                    "implementer",
                    "implementation.code",
                ),
            ),
        ),
        (
            skill("review", "review.tests"),
            skill("implementation", "implementation.code"),
        ),
    )

    assert result.is_complete
    assert result.required_count == 2
    assert result.provided_count == 2
    assert tuple(
        item.capability
        for item in result.required
    ) == (
        "implementation.code",
        "review.tests",
    )
    assert result.required[0].role_bindings == (
        "a-bundle:implementer",
        "z-bundle:reviewer",
    )
    assert result.missing == ()
    assert result.unused == ()
    assert result.duplicates == ()
    assert result.diagnostics == ()


def test_missing_provider_is_reported() -> None:
    result = validate_capability_coverage(
        (
            bundle(
                "delivery",
                binding(
                    "implementer",
                    "implementation.code",
                ),
            ),
        ),
        (),
    )

    assert not result.is_complete
    assert result.missing[0].capability == "implementation.code"
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == MISSING_CAPABILITY_DIAGNOSTIC
    assert "delivery:implementer" in diagnostic.message


def test_unused_provider_is_reported() -> None:
    result = validate_capability_coverage(
        (),
        (
            skill(
                "implementation",
                "implementation.code",
            ),
        ),
    )

    assert not result.is_complete
    assert result.unused[0].capability == "implementation.code"
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == UNUSED_CAPABILITY_DIAGNOSTIC
    assert "implementation" in diagnostic.message


def test_duplicate_providers_are_reported() -> None:
    result = validate_capability_coverage(
        (
            bundle(
                "delivery",
                binding(
                    "implementer",
                    "implementation.code",
                ),
            ),
        ),
        (
            skill(
                "implementation-a",
                "implementation.code",
            ),
            skill(
                "implementation-b",
                "implementation.code",
            ),
        ),
    )

    assert not result.is_complete
    assert result.duplicates[0].skills == (
        "implementation-a",
        "implementation-b",
    )
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == DUPLICATE_PROVIDER_DIAGNOSTIC
    assert "implementation-a, implementation-b" in diagnostic.message


def test_diagnostic_groups_have_stable_order() -> None:
    result = validate_capability_coverage(
        (
            bundle(
                "delivery",
                binding(
                    "owner",
                    "missing.capability",
                    "duplicate.capability",
                ),
            ),
        ),
        (
            skill(
                "duplicate-a",
                "duplicate.capability",
            ),
            skill(
                "duplicate-b",
                "duplicate.capability",
            ),
            skill(
                "unused",
                "unused.capability",
            ),
        ),
    )

    assert tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
    ) == (
        MISSING_CAPABILITY_DIAGNOSTIC,
        UNUSED_CAPABILITY_DIAGNOSTIC,
        DUPLICATE_PROVIDER_DIAGNOSTIC,
    )
