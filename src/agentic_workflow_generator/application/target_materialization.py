"""Typed target materialization from the active compiled composition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workflow_generator.compiler import (
    CompiledComposition,
    CompositionError,
    compile_bundle_composition,
    composition_to_json_object,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    read_json_object,
    serialize_json,
    sha256_bytes,
    transactional_update_files,
)
from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.schema_support import (
    object_schema_diagnostics,
)

from .initialization import (
    InitializationError,
    load_project_metadata,
)
from .registry_snapshot import (
    ValidatedRegistrySnapshot,
    load_validated_registry_snapshot,
)
from .target_rendering import (
    RenderedTarget,
    render_enabled_targets,
)


class TargetMaterializationError(ValueError):
    """Raised when canonical target materialization cannot be prepared."""


class TargetMaterializationValidationError(
    TargetMaterializationError
):
    """Raised when the active composition fails schema validation."""

    def __init__(
        self,
        diagnostics: tuple[Diagnostic, ...],
    ) -> None:
        self.diagnostics = diagnostics
        super().__init__(
            "active composition validation failed with "
            f"{len(diagnostics)} diagnostic(s)"
        )


class TargetManifestValidationError(
    TargetMaterializationError
):
    """Raised when an internally built manifest violates its schema."""

    def __init__(
        self,
        diagnostics: tuple[Diagnostic, ...],
    ) -> None:
        self.diagnostics = diagnostics
        super().__init__(
            "output manifest validation failed with "
            f"{len(diagnostics)} diagnostic(s)"
        )


class TargetMaterializationDriftError(
    TargetMaterializationError
):
    """Raised when active configuration differs from canonical compilation."""


@dataclass(frozen=True, slots=True)
class ActiveComposition:
    """Canonical typed composition loaded from persistent authority."""

    composition: CompiledComposition
    serialized: JsonObject


@dataclass(frozen=True, slots=True)
class TargetMaterializationPlan:
    """Complete deterministic target filesystem update."""

    composition: CompiledComposition
    rendered_targets: tuple[RenderedTarget, ...]
    stale_files: tuple[Path, ...]
    manifest: JsonObject
    manifest_bytes: bytes


@dataclass(frozen=True, slots=True)
class TargetMaterializationCommitResult:
    """Summary of one committed target materialization."""

    target_count: int
    generated_file_count: int
    removed_file_count: int


def load_active_composition(
    paths: ProjectPaths,
    *,
    registry: ValidatedRegistrySnapshot | None = None,
) -> ActiveComposition:
    """Validate and recompile the active serialized composition."""

    config = read_json_object(paths.active_config)
    schema = read_json_object(
        paths.schema_root / "agentic.schema.json"
    )

    Draft202012Validator.check_schema(schema)
    diagnostics = object_schema_diagnostics(
        config,
        paths.active_config,
        Draft202012Validator(schema),
        "AWG-TARGET-MATERIALIZATION-001",
    )

    if diagnostics:
        raise TargetMaterializationValidationError(
            diagnostics
        )

    validated_registry = (
        registry
        if registry is not None
        else load_validated_registry_snapshot(paths)
    )
    bundle_name = _selected_bundle_name(
        config,
        paths.active_config,
    )
    selected_targets = _selected_target_names(
        config,
        paths.active_config,
    )

    try:
        bundle = validated_registry.bundle_by_name(bundle_name)
        profile = validated_registry.profile_by_name(bundle.profile)
        composition = compile_bundle_composition(
            validated_registry,
            load_project_metadata(paths, profile),
            bundle_name,
            selected_targets,
        )
    except (
        CompositionError,
        InitializationError,
        LookupError,
    ) as exc:
        raise TargetMaterializationError(
            f"{paths.active_config}: cannot compile canonical "
            f"active composition: {exc}"
        ) from exc

    canonical = composition_to_json_object(composition)

    if canonical != config:
        raise TargetMaterializationDriftError(
            f"{paths.active_config}: active configuration does "
            "not match the canonical compiled composition"
        )

    return ActiveComposition(
        composition=composition,
        serialized=config,
    )


def build_target_materialization_plan(
    paths: ProjectPaths,
) -> TargetMaterializationPlan:
    """Build a complete target update without mutating the repository."""

    active = load_active_composition(paths)
    rendered_targets = render_enabled_targets(
        paths,
        active.composition,
    )
    _validate_rendered_targets(
        active.composition,
        rendered_targets,
    )
    stale_files = _collect_stale_files(
        paths,
        rendered_targets,
    )
    manifest = _build_output_manifest(
        active,
        rendered_targets,
    )
    manifest_bytes = serialize_json(manifest).encode("utf-8")
    _validate_output_manifest(
        paths,
        manifest,
    )

    return TargetMaterializationPlan(
        composition=active.composition,
        rendered_targets=rendered_targets,
        stale_files=stale_files,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
    )


def commit_target_materialization(
    paths: ProjectPaths,
    plan: TargetMaterializationPlan,
) -> TargetMaterializationCommitResult:
    """Commit one prebuilt target update transactionally."""

    writes: dict[Path, bytes] = {}

    for target in plan.rendered_targets:
        for rendered_file in target.files:
            absolute_path = paths.repository_path(
                rendered_file.path
            )

            if absolute_path in writes:
                raise TargetMaterializationError(
                    "Materialization plan contains duplicate write "
                    f"path: {rendered_file.path}"
                )

            writes[absolute_path] = rendered_file.content

    if paths.manifest in writes:
        raise TargetMaterializationError(
            "Output manifest path collides with target output"
        )

    writes[paths.manifest] = plan.manifest_bytes
    removals = tuple(
        paths.repository_path(path)
        for path in plan.stale_files
    )

    transactional_update_files(
        writes,
        removals,
    )

    return TargetMaterializationCommitResult(
        target_count=len(plan.rendered_targets),
        generated_file_count=sum(
            len(target.files)
            for target in plan.rendered_targets
        ),
        removed_file_count=len(plan.stale_files),
    )


def materialize_targets(
    paths: ProjectPaths,
) -> TargetMaterializationCommitResult:
    """Build and commit canonical target output."""

    return commit_target_materialization(
        paths,
        build_target_materialization_plan(paths),
    )


def _validate_rendered_targets(
    composition: CompiledComposition,
    rendered_targets: tuple[RenderedTarget, ...],
) -> None:
    expected = tuple(
        target.adapter.name
        for target in composition.targets
    )
    actual = tuple(
        target.name
        for target in rendered_targets
    )

    if actual != expected:
        raise TargetMaterializationError(
            "Rendered target order differs from compiled target "
            f"order: expected {expected}, found {actual}"
        )

    rendered_paths: set[Path] = set()
    owned_roots: list[tuple[str, Path]] = []

    for compiled, rendered in zip(
        composition.targets,
        rendered_targets,
        strict=True,
    ):
        if rendered.owned_paths != compiled.adapter.owned_paths:
            raise TargetMaterializationError(
                f"Rendered target {rendered.name!r} changed its "
                "compiled owned paths"
            )

        for owned_path in rendered.owned_paths:
            root = Path(owned_path)

            for owner_name, existing in owned_roots:
                if (
                    root == existing
                    or root.is_relative_to(existing)
                    or existing.is_relative_to(root)
                ):
                    raise TargetMaterializationError(
                        f"Target owned paths overlap: "
                        f"{owner_name!r}:{existing} and "
                        f"{rendered.name!r}:{root}"
                    )

            owned_roots.append(
                (rendered.name, root)
            )

        for rendered_file in rendered.files:
            if rendered_file.path in rendered_paths:
                raise TargetMaterializationError(
                    "Multiple targets rendered the same file: "
                    f"{rendered_file.path}"
                )

            rendered_paths.add(rendered_file.path)


def _collect_stale_files(
    paths: ProjectPaths,
    rendered_targets: tuple[RenderedTarget, ...],
) -> tuple[Path, ...]:
    planned = {
        paths.repository_path(rendered_file.path)
        for target in rendered_targets
        for rendered_file in target.files
    }
    stale: set[Path] = set()
    obsolete_resolution = (
        paths.generated_root / "resolution.json"
    )

    if obsolete_resolution.is_symlink():
        raise TargetMaterializationError(
            "Obsolete resolution output must not be a symlink: "
            f"{obsolete_resolution}"
        )

    if obsolete_resolution.exists():
        if not obsolete_resolution.is_file():
            raise TargetMaterializationError(
                "Obsolete resolution output must be a file: "
                f"{obsolete_resolution}"
            )

        stale.add(obsolete_resolution)

    for target in rendered_targets:
        for owned_path in target.owned_paths:
            owned_root = paths.repository_path(owned_path)

            if owned_root.is_symlink():
                raise TargetMaterializationError(
                    "Target owned path must not be a symlink: "
                    f"{owned_root}"
                )

            if not owned_root.exists():
                continue

            if owned_root.is_file():
                if owned_root not in planned:
                    stale.add(owned_root)
                continue

            if not owned_root.is_dir():
                raise TargetMaterializationError(
                    "Target owned path must be a file or directory: "
                    f"{owned_root}"
                )

            for candidate in sorted(
                owned_root.rglob("*"),
                key=lambda item: item.relative_to(
                    paths.root
                ).as_posix(),
            ):
                if candidate.is_symlink():
                    raise TargetMaterializationError(
                        "Target owned output must not contain "
                        f"symlinks: {candidate}"
                    )

                if candidate.is_file():
                    if candidate not in planned:
                        stale.add(candidate)
                elif not candidate.is_dir():
                    raise TargetMaterializationError(
                        "Target owned output contains unsupported "
                        f"filesystem entry: {candidate}"
                    )

    return tuple(
        path.relative_to(paths.root)
        for path in sorted(
            stale,
            key=lambda item: item.relative_to(
                paths.root
            ).as_posix(),
        )
    )


def _build_output_manifest(
    active: ActiveComposition,
    rendered_targets: tuple[RenderedTarget, ...],
) -> JsonObject:
    canonical_config = serialize_json(
        active.serialized
    ).encode("utf-8")
    target_entries: list[JsonValue] = []
    generated_file_count = 0

    for compiled, rendered in zip(
        active.composition.targets,
        rendered_targets,
        strict=True,
    ):
        generated_files: list[JsonValue] = []

        for rendered_file in rendered.files:
            generated_files.append(
                {
                    "path": rendered_file.path.as_posix(),
                    "sha256": sha256_bytes(
                        rendered_file.content
                    ),
                    "bytes": len(rendered_file.content),
                }
            )

        generated_file_count += len(generated_files)
        target_entries.append(
            {
                "name": rendered.name,
                "version": compiled.adapter.version,
                "ownedPaths": list(
                    rendered.owned_paths
                ),
                "generatedFiles": generated_files,
                "generatedFileCount": len(
                    generated_files
                ),
            }
        )

    return {
        "schemaVersion": "0.3.0",
        "description": (
            "Deterministic ownership and integrity manifest "
            "for generated target output."
        ),
        "composition": {
            "path": ".agentic/agentic.json",
            "sha256": sha256_bytes(
                canonical_config
            ),
        },
        "targets": target_entries,
        "summary": {
            "targetCount": len(target_entries),
            "generatedFileCount": generated_file_count,
        },
    }


def _validate_output_manifest(
    paths: ProjectPaths,
    manifest: JsonObject,
) -> None:
    schema_path = (
        paths.schema_root
        / "generated"
        / "output-manifest.schema.json"
    )
    schema = read_json_object(schema_path)

    Draft202012Validator.check_schema(schema)
    diagnostics = object_schema_diagnostics(
        manifest,
        paths.manifest,
        Draft202012Validator(schema),
        "AWG-TARGET-MATERIALIZATION-002",
    )

    if diagnostics:
        raise TargetManifestValidationError(
            diagnostics
        )


def _selected_bundle_name(
    config: JsonObject,
    source_path: Path,
) -> str:
    selection = _required_object(
        config,
        "selection",
        source_path,
    )
    bundle = _required_object(
        selection,
        "bundle",
        source_path,
    )
    return _required_string(
        bundle,
        "name",
        source_path,
        "selection.bundle.name",
    )


def _selected_target_names(
    config: JsonObject,
    source_path: Path,
) -> tuple[str, ...]:
    raw_targets = config.get("targets")

    if not isinstance(raw_targets, list) or not raw_targets:
        raise TargetMaterializationError(
            f"{source_path}: targets must be a non-empty list"
        )

    names: list[str] = []

    for index, raw_target in enumerate(
        raw_targets,
        start=1,
    ):
        if not isinstance(raw_target, dict):
            raise TargetMaterializationError(
                f"{source_path}: targets[{index - 1}] "
                "must be an object"
            )

        target = raw_target
        name = _required_string(
            target,
            "name",
            source_path,
            f"targets[{index - 1}].name",
        )

        if target.get("enabled") is not True:
            raise TargetMaterializationError(
                f"{source_path}: targets[{index - 1}].enabled "
                "must be true"
            )

        priority = target.get("priority")

        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or priority != index
        ):
            raise TargetMaterializationError(
                f"{source_path}: targets[{index - 1}].priority "
                f"must equal {index}"
            )

        names.append(name)

    return tuple(names)


def _required_object(
    parent: JsonObject,
    field: str,
    source_path: Path,
) -> JsonObject:
    value = parent.get(field)

    if not isinstance(value, dict):
        raise TargetMaterializationError(
            f"{source_path}: {field} must be an object"
        )

    return value


def _required_string(
    parent: JsonObject,
    field: str,
    source_path: Path,
    location: str,
) -> str:
    value = parent.get(field)

    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise TargetMaterializationError(
            f"{source_path}: {location} must be a "
            "non-empty trimmed string"
        )

    return value
