"""Global capability-coverage analysis over typed registry models."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_workflow_generator.domain import (
    Bundle,
    Diagnostic,
    Skill,
)

MISSING_CAPABILITY_DIAGNOSTIC = "AWG-CAPABILITY-COVERAGE-001"
UNUSED_CAPABILITY_DIAGNOSTIC = "AWG-CAPABILITY-COVERAGE-002"
DUPLICATE_PROVIDER_DIAGNOSTIC = "AWG-CAPABILITY-COVERAGE-003"


@dataclass(frozen=True, slots=True)
class CapabilityConsumers:
    """One runtime-required capability and its role-binding consumers."""

    capability: str
    role_bindings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityProviders:
    """One registered capability and its skill providers."""

    capability: str
    skills: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityCoverageResult:
    """Deterministic global capability-coverage result."""

    required: tuple[CapabilityConsumers, ...]
    provided: tuple[CapabilityProviders, ...]
    missing: tuple[CapabilityConsumers, ...]
    unused: tuple[CapabilityProviders, ...]
    duplicates: tuple[CapabilityProviders, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def required_count(self) -> int:
        """Return the number of distinct runtime-required capabilities."""

        return len(self.required)

    @property
    def provided_count(self) -> int:
        """Return the number of distinct registered capabilities."""

        return len(self.provided)

    @property
    def is_complete(self) -> bool:
        """Return whether global capability coverage is complete."""

        return not self.diagnostics


def validate_capability_coverage(
    bundles: tuple[Bundle, ...],
    skills: tuple[Skill, ...],
) -> CapabilityCoverageResult:
    """Analyze global capability coverage without side effects."""

    required_by: dict[str, set[str]] = {}
    provided_by: dict[str, set[str]] = {}

    for bundle in bundles:
        for binding in bundle.role_bindings:
            consumer = f"{bundle.name}:{binding.role_name}"

            for capability in binding.required_capabilities:
                required_by.setdefault(
                    capability,
                    set(),
                ).add(consumer)

    for skill in skills:
        for capability in skill.provides:
            provided_by.setdefault(
                capability,
                set(),
            ).add(skill.name)

    required = tuple(
        CapabilityConsumers(
            capability=capability,
            role_bindings=tuple(
                sorted(required_by[capability])
            ),
        )
        for capability in sorted(required_by)
    )
    provided = tuple(
        CapabilityProviders(
            capability=capability,
            skills=tuple(sorted(provided_by[capability])),
        )
        for capability in sorted(provided_by)
    )

    missing = tuple(
        item
        for item in required
        if item.capability not in provided_by
    )
    unused = tuple(
        item
        for item in provided
        if item.capability not in required_by
    )
    duplicates = tuple(
        item
        for item in provided
        if len(item.skills) > 1
    )

    diagnostics = (
        tuple(_missing_diagnostic(item) for item in missing)
        + tuple(_unused_diagnostic(item) for item in unused)
        + tuple(
            _duplicate_diagnostic(item)
            for item in duplicates
        )
    )

    return CapabilityCoverageResult(
        required=required,
        provided=provided,
        missing=missing,
        unused=unused,
        duplicates=duplicates,
        diagnostics=diagnostics,
    )


def _missing_diagnostic(
    item: CapabilityConsumers,
) -> Diagnostic:
    consumers = ", ".join(item.role_bindings)

    return Diagnostic(
        code=MISSING_CAPABILITY_DIAGNOSTIC,
        message=(
            f"capability {item.capability!r} has no registered "
            f"skill provider; required by bindings: {consumers}"
        ),
        related_identities=(
            item.capability,
            *item.role_bindings,
        ),
    )


def _unused_diagnostic(
    item: CapabilityProviders,
) -> Diagnostic:
    providers = ", ".join(item.skills)

    return Diagnostic(
        code=UNUSED_CAPABILITY_DIAGNOSTIC,
        message=(
            f"capability {item.capability!r} is provided by "
            f"skills but unused by all bundle role bindings: "
            f"{providers}"
        ),
        related_identities=(
            item.capability,
            *item.skills,
        ),
    )


def _duplicate_diagnostic(
    item: CapabilityProviders,
) -> Diagnostic:
    providers = ", ".join(item.skills)

    return Diagnostic(
        code=DUPLICATE_PROVIDER_DIAGNOSTIC,
        message=(
            f"capability {item.capability!r} has multiple "
            f"registered skill providers: {providers}"
        ),
        related_identities=(
            item.capability,
            *item.skills,
        ),
    )
