"""Typed guided-init orchestration without terminal or filesystem writes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from agentic_workflow_generator.domain import (
    Diagnostic,
    Setup,
    SetupProfile,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
)
from agentic_workflow_generator.registry import (
    ProjectPaths,
    RegistryKind,
    RegistryLoader,
)
from agentic_workflow_generator.validation.setup_profiles import (
    validate_setup_profile,
)
from agentic_workflow_generator.validation.setups import (
    SetupReferenceData,
    project_setup_bundles,
    project_target_names,
    validate_setup_registry,
)

from .setup_materialization import (
    materialize_setup_profile,
    setup_profile_to_json,
)


class GuidedInitError(ValueError):
    """Base error for guided-init application failures."""


class GuidedInitValidationError(GuidedInitError):
    """Raised when a guided-init validation boundary rejects data."""

    def __init__(
        self,
        boundary: str,
        diagnostics: tuple[Diagnostic, ...],
    ) -> None:
        self.boundary = boundary
        self.diagnostics = diagnostics
        super().__init__(
            f"{boundary} validation failed with "
            f"{len(diagnostics)} diagnostic(s)"
        )


@dataclass(frozen=True, slots=True)
class GuidedInitService:
    """Validated guided setup registry and materialization boundary."""

    setups: tuple[Setup, ...]
    references: SetupReferenceData
    profile_schema: JsonObject

    def setup_by_name(
        self,
        setup_name: str,
    ) -> Setup:
        """Return one exact registered setup identity."""

        for setup in self.setups:
            if setup.name == setup_name:
                return setup

        raise GuidedInitError(
            f"unknown guided setup {setup_name!r}"
        )

    def materialize(
        self,
        setup_name: str,
        answer_overrides: Mapping[str, str] | None = None,
    ) -> SetupProfile:
        """Materialize and independently validate one setup profile."""

        setup = self.setup_by_name(setup_name)
        profile = materialize_setup_profile(
            setup,
            answer_overrides,
        )
        result = validate_setup_profile(
            setup_profile_to_json(profile),
            Path(f"<guided-init:{setup_name}>"),
            self.profile_schema,
            self.setups,
            self.references,
        )

        if not result.is_valid:
            raise GuidedInitValidationError(
                "setup profile",
                result.diagnostics,
            )

        if result.profile != profile:
            raise GuidedInitError(
                "validated setup profile does not match "
                "the materialized profile"
            )

        return profile


def load_guided_init_service(
    paths: ProjectPaths,
) -> GuidedInitService:
    """Load and validate all registry input required by guided init."""

    loader = RegistryLoader(paths)
    references = SetupReferenceData(
        bundles=project_setup_bundles(
            loader.load(RegistryKind.BUNDLE)
        ),
        targets=project_target_names(
            loader.load(RegistryKind.TARGET)
        ),
    )
    result = validate_setup_registry(
        loader.load(RegistryKind.SETUP),
        read_json_object(
            paths.schema_root
            / "registry"
            / "setup.schema.json"
        ),
        references,
    )

    if not result.is_valid:
        raise GuidedInitValidationError(
            "setup registry",
            result.diagnostics,
        )

    return GuidedInitService(
        setups=result.setups,
        references=references,
        profile_schema=read_json_object(
            paths.schema_root
            / "setup-profile.schema.json"
        ),
    )


def parse_answer_overrides(
    raw_answers: Sequence[str] | None,
) -> dict[str, str]:
    """Parse repeated question=value CLI arguments fail-fast."""

    overrides: dict[str, str] = {}

    for raw_answer in raw_answers or ():
        if "=" not in raw_answer:
            raise GuidedInitError(
                f"invalid answer override {raw_answer!r}; "
                "expected question=value"
            )

        question, selected = raw_answer.split("=", 1)
        question = question.strip()
        selected = selected.strip()

        if not question:
            raise GuidedInitError(
                f"invalid answer override {raw_answer!r}; "
                "question id must be non-empty"
            )

        if not selected:
            raise GuidedInitError(
                f"invalid answer override {raw_answer!r}; "
                "selected value must be non-empty"
            )

        if question in overrides:
            raise GuidedInitError(
                f"duplicate answer override for question "
                f"{question!r}"
            )

        overrides[question] = selected

    return overrides
