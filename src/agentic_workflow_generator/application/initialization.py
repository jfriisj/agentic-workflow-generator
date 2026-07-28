"""Typed initialization planning from validated bundle or setup input."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workflow_generator.compiler import (
    CompiledComposition,
    ProjectMetadata,
    compile_bundle_composition,
    composition_to_json_object,
)
from agentic_workflow_generator.domain import (
    Diagnostic,
    Profile,
    SetupProfile,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
    serialize_json,
    transactional_write_bytes,
)
from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.schema_support import (
    object_schema_diagnostics,
)
from agentic_workflow_generator.validation.setup_profiles import (
    validate_setup_profile,
)

from .guided_init import (
    GuidedInitService,
    load_guided_init_service,
)
from .registry_snapshot import (
    ValidatedRegistrySnapshot,
    load_validated_registry_snapshot,
)
from .setup_materialization import setup_profile_to_json


class InitializationError(ValueError):
    """Raised when typed initialization planning cannot complete."""


class InitializationValidationError(InitializationError):
    """Raised when a planned output fails its commit boundary."""

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
class InitializationCommitResult:
    """Immutable result of one initialization commit."""

    written_paths: tuple[Path, ...]

    @property
    def changed(self) -> bool:
        """Return whether any file content changed."""

        return bool(self.written_paths)


@dataclass(frozen=True, slots=True)
class InitializationPlan:
    """Immutable validated initialization output before filesystem writes."""

    composition: CompiledComposition
    active_config: JsonObject
    setup_profile: SetupProfile | None
    setup_profile_json: JsonObject | None

    @property
    def bundle(self) -> str:
        """Return the selected bundle identity."""

        return self.composition.bundle

    @property
    def targets(self) -> tuple[str, ...]:
        """Return enabled target identities in deterministic order."""

        return tuple(
            target.adapter.name
            for target in self.composition.targets
        )


@dataclass(frozen=True, slots=True)
class InitializationService:
    """Plan direct and guided initialization from validated typed input."""

    paths: ProjectPaths
    registry: ValidatedRegistrySnapshot
    guided_init: GuidedInitService

    def plan_bundle(
        self,
        bundle_name: str,
        selected_targets: tuple[str, ...] | None = None,
    ) -> InitializationPlan:
        """Compile one direct bundle selection without writing files."""

        bundle = self.registry.bundle_by_name(bundle_name)
        profile = self.registry.profile_by_name(bundle.profile)
        composition = compile_bundle_composition(
            self.registry,
            load_project_metadata(
                self.paths,
                profile,
            ),
            bundle_name,
            selected_targets,
        )

        return InitializationPlan(
            composition=composition,
            active_config=composition_to_json_object(
                composition
            ),
            setup_profile=None,
            setup_profile_json=None,
        )

    def validate_plan(
        self,
        plan: InitializationPlan,
    ) -> None:
        """Validate every serialized output at the commit boundary."""

        config_diagnostics = object_schema_diagnostics(
            plan.active_config,
            self.paths.active_config,
            Draft202012Validator(
                read_json_object(
                    self.paths.schema_root
                    / "agentic.schema.json"
                )
            ),
            "AWG-INIT-001",
        )

        if config_diagnostics:
            raise InitializationValidationError(
                "active configuration",
                config_diagnostics,
            )

        if plan.setup_profile_json is None:
            if plan.setup_profile is not None:
                raise InitializationError(
                    "setup profile model exists without JSON output"
                )

            return

        if plan.setup_profile is None:
            raise InitializationError(
                "setup profile JSON exists without typed model"
            )

        profile_result = validate_setup_profile(
            plan.setup_profile_json,
            self.paths.setup_profile,
            self.guided_init.profile_schema,
            self.guided_init.setups,
            self.guided_init.references,
        )

        if not profile_result.is_valid:
            raise InitializationValidationError(
                "setup profile",
                profile_result.diagnostics,
            )

        if profile_result.profile != plan.setup_profile:
            raise InitializationError(
                "validated setup profile does not match "
                "the planned typed profile"
            )

    def commit(
        self,
        plan: InitializationPlan,
    ) -> InitializationCommitResult:
        """Validate and transactionally write changed plan outputs."""

        self.validate_plan(plan)

        outputs: dict[Path, bytes] = {
            self.paths.active_config: serialize_json(
                plan.active_config
            ).encode("utf-8"),
        }

        if plan.setup_profile_json is not None:
            outputs[self.paths.setup_profile] = serialize_json(
                plan.setup_profile_json
            ).encode("utf-8")

        changed_outputs = {
            path: content
            for path, content in outputs.items()
            if not path.is_file()
            or path.read_bytes() != content
        }

        if not changed_outputs:
            return InitializationCommitResult(
                written_paths=(),
            )

        transactional_write_bytes(changed_outputs)

        return InitializationCommitResult(
            written_paths=tuple(changed_outputs),
        )

    def plan_setup(
        self,
        setup_name: str,
        answer_overrides: Mapping[str, str] | None = None,
    ) -> InitializationPlan:
        """Compile one guided setup selection without writing files."""

        setup_profile = self.guided_init.materialize(
            setup_name,
            answer_overrides,
        )
        bundle = self.registry.bundle_by_name(
            setup_profile.selected.bundle
        )
        profile = self.registry.profile_by_name(bundle.profile)
        composition = compile_bundle_composition(
            self.registry,
            load_project_metadata(
                self.paths,
                profile,
            ),
            setup_profile.selected.bundle,
            setup_profile.selected.targets,
        )

        return InitializationPlan(
            composition=composition,
            active_config=composition_to_json_object(
                composition
            ),
            setup_profile=setup_profile,
            setup_profile_json=setup_profile_to_json(
                setup_profile
            ),
        )


def load_initialization_service(
    paths: ProjectPaths,
) -> InitializationService:
    """Load every validated registry boundary required by init."""

    return InitializationService(
        paths=paths,
        registry=load_validated_registry_snapshot(paths),
        guided_init=load_guided_init_service(paths),
    )


def load_project_metadata(
    paths: ProjectPaths,
    default_profile: Profile,
) -> ProjectMetadata:
    """Preserve existing project metadata or create explicit defaults."""

    if not paths.active_config.is_file():
        return _default_project_metadata(
            paths,
            default_profile,
        )

    config = read_json_object(paths.active_config)
    raw_project = config.get("project")

    if not isinstance(raw_project, dict):
        raise InitializationError(
            f"{paths.active_config}: project must be an object"
        )

    return ProjectMetadata(
        name=_required_string(
            raw_project,
            "name",
            paths,
        ),
        project_type=_required_string(
            raw_project,
            "type",
            paths,
        ),
        description=_required_string(
            raw_project,
            "description",
            paths,
        ),
        language_profiles=_required_string_tuple(
            raw_project,
            "languageProfiles",
            paths,
        ),
        runtime_profiles=_required_string_tuple(
            raw_project,
            "runtimeProfiles",
            paths,
        ),
        architecture_profile=_required_string(
            raw_project,
            "architectureProfile",
            paths,
        ),
    )


def _default_project_metadata(
    paths: ProjectPaths,
    profile: Profile,
) -> ProjectMetadata:
    if not profile.recommended_language_profiles:
        raise InitializationError(
            f"profile {profile.name!r} has no recommended "
            "language profiles for initial project metadata"
        )

    if not profile.recommended_runtime_profiles:
        raise InitializationError(
            f"profile {profile.name!r} has no recommended "
            "runtime profiles for initial project metadata"
        )

    return ProjectMetadata(
        name=paths.root.name,
        project_type="agentic-project",
        description=(
            "Generated agentic configuration for "
            f"{paths.root.name}."
        ),
        language_profiles=(
            profile.recommended_language_profiles
        ),
        runtime_profiles=(
            profile.recommended_runtime_profiles
        ),
        architecture_profile=profile.name,
    )


def _required_string(
    project: JsonObject,
    field: str,
    paths: ProjectPaths,
) -> str:
    value = project.get(field)

    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise InitializationError(
            f"{paths.active_config}: project.{field} "
            "must be a non-empty trimmed string"
        )

    return value


def _required_string_tuple(
    project: JsonObject,
    field: str,
    paths: ProjectPaths,
) -> tuple[str, ...]:
    value = project.get(field)

    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, str)
            or not item
            or item != item.strip()
            for item in value
        )
    ):
        raise InitializationError(
            f"{paths.active_config}: project.{field} "
            "must be a non-empty list of trimmed strings"
        )

    values = tuple(
        item
        for item in value
        if isinstance(item, str)
    )

    if len(set(values)) != len(values):
        raise InitializationError(
            f"{paths.active_config}: project.{field} "
            "must contain unique values"
        )

    return values
