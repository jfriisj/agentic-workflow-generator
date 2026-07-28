"""Target adapter parsing and semantic validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

from jsonschema import Draft202012Validator

from agentic_workflow_generator.domain import (
    Diagnostic,
    TargetAdapter,
    TargetOutputPath,
    TargetPermissionMapping,
    TargetPermissionSetting,
)
from agentic_workflow_generator.infrastructure import JsonObject
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.identity_support import (
    duplicate_name_diagnostics,
    folder_name_mismatch_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    registry_schema_diagnostics,
)

SCHEMA_DIAGNOSTIC = "AWG-TARGET-001"
OBSOLETE_FIELD_DIAGNOSTIC = "AWG-TARGET-002"
FOLDER_NAME_DIAGNOSTIC = "AWG-TARGET-003"
DUPLICATE_NAME_DIAGNOSTIC = "AWG-TARGET-004"
UNSAFE_OUTPUT_PATH_DIAGNOSTIC = "AWG-TARGET-005"
DUPLICATE_OUTPUT_PATH_DIAGNOSTIC = "AWG-TARGET-006"
UNSAFE_OWNED_PATH_DIAGNOSTIC = "AWG-TARGET-007"
OWNED_PATH_OVERLAP_DIAGNOSTIC = "AWG-TARGET-008"
CROSS_TARGET_OWNERSHIP_DIAGNOSTIC = "AWG-TARGET-009"
UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC = "AWG-TARGET-010"
MISSING_PERMISSION_MAPPING_DIAGNOSTIC = "AWG-TARGET-011"
OUTPUT_OUTSIDE_OWNERSHIP_DIAGNOSTIC = "AWG-TARGET-012"

OBSOLETE_FIELDS = frozenset(
    {
        "capabilities",
        "conventions",
        "files",
        "generatedFiles",
        "generator",
        "output",
        "outputs",
        "supportedFeatures",
        "supports",
    }
)


@dataclass(frozen=True, slots=True)
class TargetReferenceData:
    """Validated external identities required by target adapters."""

    permission_profiles: frozenset[str]


@dataclass(frozen=True, slots=True)
class TargetValidationResult:
    """Validated target adapters and deterministic diagnostics."""

    adapters: tuple[TargetAdapter, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedTarget:
    adapter: TargetAdapter
    source_path: Path


def validate_target_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    references: TargetReferenceData,
) -> TargetValidationResult:
    """Validate target adapters without filesystem side effects."""

    validator = Draft202012Validator(
        cast(Mapping[str, Any], schema)
    )
    parsed_targets: list[_ParsedTarget] = []
    diagnostics: list[Diagnostic] = []

    for source in sources:
        obsolete_diagnostics = _validate_obsolete_fields(
            source
        )
        diagnostics.extend(obsolete_diagnostics)

        if obsolete_diagnostics:
            continue

        schema_diagnostics = registry_schema_diagnostics(
            source,
            validator,
            SCHEMA_DIAGNOSTIC,
        )
        diagnostics.extend(schema_diagnostics)

        if schema_diagnostics:
            continue

        parsed = _parse_target(source)
        parsed_targets.append(parsed)
        diagnostics.extend(
            _validate_target_semantics(
                parsed,
                references,
            )
        )

    diagnostics.extend(
        duplicate_name_diagnostics(
            (
                (
                    parsed.adapter.name,
                    parsed.source_path,
                )
                for parsed in parsed_targets
            ),
            DUPLICATE_NAME_DIAGNOSTIC,
            "target adapter",
        )
    )
    diagnostics.extend(
        _validate_cross_target_ownership(parsed_targets)
    )

    return TargetValidationResult(
        adapters=tuple(
            parsed.adapter
            for parsed in parsed_targets
        ),
        diagnostics=tuple(diagnostics),
    )


def _validate_obsolete_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    return tuple(
        Diagnostic(
            code=OBSOLETE_FIELD_DIAGNOSTIC,
            message=(
                f"{field_name} is obsolete and must not "
                "be declared"
            ),
            source_path=source.source_path.as_posix(),
            location=field_name,
        )
        for field_name in sorted(
            OBSOLETE_FIELDS.intersection(source.data)
        )
    )


def _parse_target(
    source: RegistrySource,
) -> _ParsedTarget:
    output_paths_data = cast(
        Mapping[str, str],
        source.data["outputPaths"],
    )
    permission_mapping_data = cast(
        Mapping[str, Mapping[str, object]],
        source.data["permissionMapping"],
    )

    output_paths = tuple(
        TargetOutputPath(
            name=name,
            path=path,
        )
        for name, path in sorted(
            output_paths_data.items()
        )
    )

    permission_mappings = tuple(
        TargetPermissionMapping(
            permission_profile=permission_profile,
            settings=tuple(
                TargetPermissionSetting(
                    name=setting_name,
                    value=(
                        setting_value
                        if isinstance(setting_value, str)
                        else tuple(cast(list[str], setting_value))
                    ),
                )
                for setting_name, setting_value in sorted(
                    settings.items()
                )
            ),
        )
        for permission_profile, settings in sorted(
            permission_mapping_data.items()
        )
    )

    return _ParsedTarget(
        adapter=TargetAdapter(
            name=cast(str, source.data["name"]),
            version=cast(str, source.data["version"]),
            description=cast(
                str,
                source.data["description"],
            ),
            output_paths=output_paths,
            owned_paths=tuple(
                cast(list[str], source.data["ownedPaths"])
            ),
            permission_mappings=permission_mappings,
        ),
        source_path=source.source_path,
    )


def _validate_target_semantics(
    parsed: _ParsedTarget,
    references: TargetReferenceData,
) -> tuple[Diagnostic, ...]:
    adapter = parsed.adapter
    source_path = parsed.source_path
    diagnostics: list[Diagnostic] = []

    diagnostics.extend(
        folder_name_mismatch_diagnostics(
            adapter.name,
            source_path,
            FOLDER_NAME_DIAGNOSTIC,
        )
    )

    normalized_outputs: dict[str, str] = {}

    for output in adapter.output_paths:
        normalized = _safe_normalized_path(output.path)

        if normalized is None:
            diagnostics.append(
                Diagnostic(
                    code=UNSAFE_OUTPUT_PATH_DIAGNOSTIC,
                    message=(
                        f"output path {output.path!r} must "
                        "be a canonical safe relative path"
                    ),
                    source_path=source_path.as_posix(),
                    location=(
                        f"outputPaths.{output.name}"
                    ),
                    related_identities=(adapter.name,),
                )
            )
            continue

        first_name = normalized_outputs.get(normalized)

        if first_name is not None:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_OUTPUT_PATH_DIAGNOSTIC,
                    message=(
                        f"output path {output.path!r} is "
                        f"already declared as {first_name!r}"
                    ),
                    source_path=source_path.as_posix(),
                    location=(
                        f"outputPaths.{output.name}"
                    ),
                    related_identities=(adapter.name,),
                )
            )
            continue

        normalized_outputs[normalized] = output.name

    normalized_owned: list[tuple[int, str]] = []

    for index, owned_path in enumerate(adapter.owned_paths):
        normalized = _safe_normalized_path(owned_path)

        if normalized is None:
            diagnostics.append(
                Diagnostic(
                    code=UNSAFE_OWNED_PATH_DIAGNOSTIC,
                    message=(
                        f"owned path {owned_path!r} must "
                        "be a canonical safe relative path"
                    ),
                    source_path=source_path.as_posix(),
                    location=f"ownedPaths[{index}]",
                    related_identities=(adapter.name,),
                )
            )
            continue

        normalized_owned.append((index, normalized))

    for left_index, (_left_position, left) in enumerate(
        normalized_owned
    ):
        for right_position, right in normalized_owned[
            left_index + 1 :
        ]:
            if _paths_overlap(left, right):
                diagnostics.append(
                    Diagnostic(
                        code=OWNED_PATH_OVERLAP_DIAGNOSTIC,
                        message=(
                            f"owned path {left!r} overlaps "
                            f"{right!r}"
                        ),
                        source_path=source_path.as_posix(),
                        location=(
                            f"ownedPaths[{right_position}]"
                        ),
                        related_identities=(adapter.name,),
                    )
                )

    owned_values = tuple(
        path
        for _index, path in normalized_owned
    )

    for output_path, output_name in normalized_outputs.items():
        if any(
            _path_is_within(output_path, owned_path)
            for owned_path in owned_values
        ):
            continue

        diagnostics.append(
            Diagnostic(
                code=OUTPUT_OUTSIDE_OWNERSHIP_DIAGNOSTIC,
                message=(
                    f"output path {output_path!r} is outside "
                    "the adapter's owned paths"
                ),
                source_path=source_path.as_posix(),
                location=f"outputPaths.{output_name}",
                related_identities=(adapter.name,),
            )
        )

    mapped_profiles = frozenset(
        mapping.permission_profile
        for mapping in adapter.permission_mappings
    )

    for permission_profile in sorted(
        mapped_profiles.difference(
            references.permission_profiles
        )
    ):
        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,
                message=(
                    f"permission mapping references unknown "
                    f"profile {permission_profile!r}"
                ),
                source_path=source_path.as_posix(),
                location=(
                    f"permissionMapping.{permission_profile}"
                ),
                related_identities=(
                    adapter.name,
                    permission_profile,
                ),
            )
        )

    for permission_profile in sorted(
        references.permission_profiles.difference(
            mapped_profiles
        )
    ):
        diagnostics.append(
            Diagnostic(
                code=MISSING_PERMISSION_MAPPING_DIAGNOSTIC,
                message=(
                    f"target {adapter.name!r} has no "
                    "permission mapping for "
                    f"{permission_profile!r}"
                ),
                source_path=source_path.as_posix(),
                location="permissionMapping",
                related_identities=(
                    adapter.name,
                    permission_profile,
                ),
            )
        )

    return tuple(diagnostics)


def _validate_cross_target_ownership(
    targets: list[_ParsedTarget],
) -> tuple[Diagnostic, ...]:
    ownership: list[tuple[str, str, Path, int]] = []

    for parsed in targets:
        for index, owned_path in enumerate(
            parsed.adapter.owned_paths
        ):
            normalized = _safe_normalized_path(owned_path)

            if normalized is None:
                continue

            ownership.append(
                (
                    parsed.adapter.name,
                    normalized,
                    parsed.source_path,
                    index,
                )
            )

    diagnostics: list[Diagnostic] = []

    for left_index, (
        left_name,
        left_path,
        _left_source,
        _left_position,
    ) in enumerate(ownership):
        for (
            right_name,
            right_path,
            right_source,
            right_position,
        ) in ownership[left_index + 1 :]:
            if left_name == right_name:
                continue

            if not _paths_overlap(left_path, right_path):
                continue

            diagnostics.append(
                Diagnostic(
                    code=CROSS_TARGET_OWNERSHIP_DIAGNOSTIC,
                    message=(
                        f"owned path {right_path!r} for target "
                        f"{right_name!r} overlaps {left_path!r} "
                        f"owned by target {left_name!r}"
                    ),
                    source_path=right_source.as_posix(),
                    location=(
                        f"ownedPaths[{right_position}]"
                    ),
                    related_identities=(
                        left_name,
                        right_name,
                    ),
                )
            )

    return tuple(diagnostics)


def _safe_normalized_path(
    value: str,
) -> str | None:
    if (
        not value
        or value != value.strip()
        or "\\" in value
    ):
        return None

    path = PurePosixPath(value)

    if (
        path.is_absolute()
        or ".." in path.parts
        or path.as_posix() in {"", "."}
    ):
        return None

    normalized = path.as_posix()

    if normalized != value:
        return None

    return normalized


def _paths_overlap(
    left: str,
    right: str,
) -> bool:
    left_path = PurePosixPath(left)
    right_path = PurePosixPath(right)

    return (
        left_path == right_path
        or left_path in right_path.parents
        or right_path in left_path.parents
    )


def _path_is_within(
    path: str,
    owned_path: str,
) -> bool:
    candidate = PurePosixPath(path)
    owner = PurePosixPath(owned_path)

    return candidate == owner or owner in candidate.parents
