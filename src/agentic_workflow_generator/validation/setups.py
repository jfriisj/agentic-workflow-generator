"""Guided setup parsing, projection and semantic validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import (
    Diagnostic,
    Setup,
    SetupMode,
    SetupOption,
    SetupOptionClassification,
    SetupQuestion,
    SetupSelection,
    SetupSelectionPatch,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import RegistrySource
from agentic_workflow_generator.validation.schema_support import (
    registry_schema_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_location as shared_schema_error_location,
)

SCHEMA_DIAGNOSTIC = "AWG-SETUP-001"
OBSOLETE_FIELD_DIAGNOSTIC = "AWG-SETUP-002"
FILE_NAME_DIAGNOSTIC = "AWG-SETUP-003"
DUPLICATE_NAME_DIAGNOSTIC = "AWG-SETUP-004"
UNKNOWN_BUNDLE_DIAGNOSTIC = "AWG-SETUP-005"
UNKNOWN_TARGET_DIAGNOSTIC = "AWG-SETUP-006"
TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC = "AWG-SETUP-007"
DUPLICATE_QUESTION_DIAGNOSTIC = "AWG-SETUP-008"
DEFAULT_OPTION_DIAGNOSTIC = "AWG-SETUP-009"
DEFAULT_CLASSIFICATION_DIAGNOSTIC = "AWG-SETUP-010"
DUPLICATE_OPTION_DIAGNOSTIC = "AWG-SETUP-011"
BLOCKED_SELECTION_DIAGNOSTIC = "AWG-SETUP-012"

_ROOT_OBSOLETE_FIELDS = frozenset(
    {
        "defaultBundle",
        "finalRecommendation",
    }
)
_QUESTION_OBSOLETE_FIELDS = frozenset(
    {
        "recommended",
        "compatible",
        "blocked",
    }
)
_OPTION_OBSOLETE_FIELDS = frozenset(
    {
        "recommends",
    }
)
_SELECTION_OBSOLETE_FIELDS = frozenset(
    {
        "profile",
        "workflow",
        "agents",
        "skills",
        "artifacts",
    }
)


@dataclass(frozen=True, slots=True)
class ProjectedSetupBundle:
    """Minimal bundle surface required by guided setup selection."""

    name: str
    targets: frozenset[str]


@dataclass(frozen=True, slots=True)
class SetupReferenceData:
    """Validated identities required by guided setup selection."""

    bundles: tuple[ProjectedSetupBundle, ...]
    targets: frozenset[str]


@dataclass(frozen=True, slots=True)
class SetupValidationResult:
    """Validated setup definitions and deterministic diagnostics."""

    setups: tuple[Setup, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True)
class _ParsedSetup:
    setup: Setup
    source_path: Path


class SetupDependencyProjectionError(ValueError):
    """Raised when setup dependency data cannot be projected."""


def project_setup_bundles(
    sources: Iterable[RegistrySource],
) -> tuple[ProjectedSetupBundle, ...]:
    """Project bundle identities and supported targets."""

    projected: dict[str, ProjectedSetupBundle] = {}

    for source in sources:
        name = _project_name(source)

        if name in projected:
            raise SetupDependencyProjectionError(
                f"{source.source_path}: bundle identity {name!r} is duplicated"
            )

        raw_targets = source.data.get("targets")

        if not isinstance(raw_targets, list) or not raw_targets:
            raise SetupDependencyProjectionError(
                f"{source.source_path}: targets must be a non-empty list"
            )

        targets: set[str] = set()

        for index, raw_target in enumerate(raw_targets):
            if not isinstance(raw_target, str) or not raw_target.strip():
                raise SetupDependencyProjectionError(
                    f"{source.source_path}: targets[{index}] must be a non-empty string"
                )

            if raw_target in targets:
                raise SetupDependencyProjectionError(
                    f"{source.source_path}: target {raw_target!r} is duplicated"
                )

            targets.add(raw_target)

        projected[name] = ProjectedSetupBundle(
            name=name,
            targets=frozenset(targets),
        )

    return tuple(projected[name] for name in sorted(projected))


def project_target_names(
    sources: Iterable[RegistrySource],
) -> frozenset[str]:
    """Project target adapter identities."""

    names: set[str] = set()

    for source in sources:
        name = _project_name(source)

        if name in names:
            raise SetupDependencyProjectionError(
                f"{source.source_path}: target identity {name!r} is duplicated"
            )

        names.add(name)

    return frozenset(names)


def validate_setup_registry(
    sources: tuple[RegistrySource, ...],
    schema: JsonObject,
    references: SetupReferenceData,
) -> SetupValidationResult:
    """Validate guided setup registry definitions without side effects."""

    validator = Draft202012Validator(cast(Mapping[str, Any], schema))
    parsed_setups: list[_ParsedSetup] = []
    diagnostics: list[Diagnostic] = []

    for source in sources:
        obsolete_diagnostics = _validate_obsolete_fields(source)
        diagnostics.extend(obsolete_diagnostics)

        if obsolete_diagnostics:
            continue

        schema_diagnostics = _validate_schema(source, validator)
        diagnostics.extend(schema_diagnostics)

        if schema_diagnostics:
            continue

        parsed = _parse_setup(source)
        parsed_setups.append(parsed)
        diagnostics.extend(
            _validate_setup_semantics(
                parsed,
                references,
            )
        )

    diagnostics.extend(_validate_unique_names(parsed_setups))

    return SetupValidationResult(
        setups=tuple(parsed.setup for parsed in parsed_setups),
        diagnostics=tuple(diagnostics),
    )


def _project_name(source: RegistrySource) -> str:
    raw_name = source.data.get("name")

    if not isinstance(raw_name, str) or not raw_name.strip():
        raise SetupDependencyProjectionError(
            f"{source.source_path}: name must be a non-empty string"
        )

    return raw_name


def _validate_obsolete_fields(
    source: RegistrySource,
) -> tuple[Diagnostic, ...]:
    found: list[tuple[str, str]] = []

    for field in sorted(_ROOT_OBSOLETE_FIELDS.intersection(source.data)):
        found.append((field, field))

    raw_default = source.data.get("defaultSelection")

    if isinstance(raw_default, Mapping):
        for field in sorted(_SELECTION_OBSOLETE_FIELDS.intersection(raw_default)):
            found.append((f"defaultSelection.{field}", field))

    raw_questions = source.data.get("questions")

    if isinstance(raw_questions, list):
        for question_index, raw_question in enumerate(raw_questions):
            if not isinstance(raw_question, Mapping):
                continue

            for field in sorted(_QUESTION_OBSOLETE_FIELDS.intersection(raw_question)):
                found.append(
                    (
                        f"questions[{question_index}].{field}",
                        field,
                    )
                )

            raw_options = raw_question.get("options")

            if not isinstance(raw_options, list):
                continue

            for option_index, raw_option in enumerate(raw_options):
                if not isinstance(raw_option, Mapping):
                    continue

                for field in sorted(_OPTION_OBSOLETE_FIELDS.intersection(raw_option)):
                    found.append(
                        (
                            "questions"
                            f"[{question_index}].options"
                            f"[{option_index}].{field}",
                            field,
                        )
                    )

                raw_selection = raw_option.get("selection")

                if not isinstance(raw_selection, Mapping):
                    continue

                for field in sorted(
                    _SELECTION_OBSOLETE_FIELDS.intersection(raw_selection)
                ):
                    found.append(
                        (
                            "questions"
                            f"[{question_index}].options"
                            f"[{option_index}].selection.{field}",
                            field,
                        )
                    )

    return tuple(
        Diagnostic(
            code=OBSOLETE_FIELD_DIAGNOSTIC,
            message=f"obsolete setup field {field!r} is not allowed",
            source_path=source.source_path.as_posix(),
            location=location,
            related_identities=(field,),
        )
        for location, field in found
    )


def _validate_schema(
    source: RegistrySource,
    validator: Draft202012Validator,
) -> tuple[Diagnostic, ...]:
    return registry_schema_diagnostics(
        source,
        validator,
        SCHEMA_DIAGNOSTIC,
    )


def _schema_error_location(
    error: ValidationError,
) -> str:
    return shared_schema_error_location(error)


def _parse_setup(source: RegistrySource) -> _ParsedSetup:
    raw_default = cast(Mapping[str, JsonValue], source.data["defaultSelection"])
    raw_questions = cast(list[JsonValue], source.data["questions"])

    return _ParsedSetup(
        setup=Setup(
            name=cast(str, source.data["name"]),
            description=cast(str, source.data["description"]),
            version=cast(str, source.data["version"]),
            mode=SetupMode(cast(str, source.data["mode"])),
            default_selection=_parse_selection(raw_default),
            questions=tuple(
                _parse_question(cast(Mapping[str, JsonValue], raw_question))
                for raw_question in raw_questions
            ),
        ),
        source_path=source.source_path,
    )


def _parse_selection(
    raw_selection: Mapping[str, JsonValue],
) -> SetupSelection:
    return SetupSelection(
        bundle=cast(str, raw_selection["bundle"]),
        targets=tuple(cast(list[str], raw_selection["targets"])),
    )


def _parse_selection_patch(
    raw_selection: Mapping[str, JsonValue],
) -> SetupSelectionPatch:
    raw_targets = raw_selection.get("targets")

    return SetupSelectionPatch(
        bundle=cast(str | None, raw_selection.get("bundle")),
        targets=(
            tuple(cast(list[str], raw_targets)) if raw_targets is not None else None
        ),
    )


def _parse_question(
    raw_question: Mapping[str, JsonValue],
) -> SetupQuestion:
    raw_options = cast(list[JsonValue], raw_question["options"])

    return SetupQuestion(
        id=cast(str, raw_question["id"]),
        prompt=cast(str, raw_question["prompt"]),
        default_option=cast(str, raw_question["defaultOption"]),
        options=tuple(
            _parse_option(cast(Mapping[str, JsonValue], raw_option))
            for raw_option in raw_options
        ),
    )


def _parse_option(
    raw_option: Mapping[str, JsonValue],
) -> SetupOption:
    raw_selection = raw_option.get("selection")

    return SetupOption(
        value=cast(str, raw_option["value"]),
        label=cast(str, raw_option["label"]),
        classification=SetupOptionClassification(
            cast(str, raw_option["classification"])
        ),
        reason=cast(str, raw_option["reason"]),
        selection=(
            _parse_selection_patch(cast(Mapping[str, JsonValue], raw_selection))
            if raw_selection is not None
            else None
        ),
    )


def _validate_setup_semantics(
    parsed: _ParsedSetup,
    references: SetupReferenceData,
) -> tuple[Diagnostic, ...]:
    setup = parsed.setup
    path = parsed.source_path
    diagnostics: list[Diagnostic] = []
    expected_name = path.name.removesuffix(".setup.json")

    if setup.name != expected_name:
        diagnostics.append(
            Diagnostic(
                code=FILE_NAME_DIAGNOSTIC,
                message=(
                    f"setup name {setup.name!r} must match file name {expected_name!r}"
                ),
                source_path=path.as_posix(),
                location="name",
                related_identities=(
                    setup.name,
                    expected_name,
                ),
            )
        )

    bundle_map = {bundle.name: bundle for bundle in references.bundles}

    diagnostics.extend(
        _validate_selection(
            setup.default_selection.bundle,
            setup.default_selection.targets,
            bundle_map,
            references.targets,
            path,
            "defaultSelection",
        )
    )

    question_ids: set[str] = set()

    for question_index, question in enumerate(setup.questions):
        question_location = f"questions[{question_index}]"

        if question.id in question_ids:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_QUESTION_DIAGNOSTIC,
                    message=f"question id {question.id!r} is duplicated",
                    source_path=path.as_posix(),
                    location=f"{question_location}.id",
                    related_identities=(question.id,),
                )
            )

        question_ids.add(question.id)
        diagnostics.extend(
            _validate_question(
                question,
                question_index,
                setup.default_selection,
                bundle_map,
                references.targets,
                path,
            )
        )

    return tuple(diagnostics)


def _validate_question(
    question: SetupQuestion,
    question_index: int,
    default_selection: SetupSelection,
    bundles: Mapping[str, ProjectedSetupBundle],
    targets: frozenset[str],
    path: Path,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    question_location = f"questions[{question_index}]"
    option_map: dict[str, SetupOption] = {}

    for option_index, option in enumerate(question.options):
        option_location = f"{question_location}.options[{option_index}]"

        if option.value in option_map:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_OPTION_DIAGNOSTIC,
                    message=(
                        f"question {question.id!r} option "
                        f"value {option.value!r} is duplicated"
                    ),
                    source_path=path.as_posix(),
                    location=f"{option_location}.value",
                    related_identities=(
                        question.id,
                        option.value,
                    ),
                )
            )

        option_map[option.value] = option

        if (
            option.classification is SetupOptionClassification.BLOCKED
            and option.selection is not None
        ):
            diagnostics.append(
                Diagnostic(
                    code=BLOCKED_SELECTION_DIAGNOSTIC,
                    message=(
                        f"blocked option {option.value!r} must not define a selection"
                    ),
                    source_path=path.as_posix(),
                    location=f"{option_location}.selection",
                    related_identities=(
                        question.id,
                        option.value,
                    ),
                )
            )

        if option.selection is None:
            continue

        effective_bundle = (
            option.selection.bundle
            if option.selection.bundle is not None
            else default_selection.bundle
        )
        effective_targets = (
            option.selection.targets
            if option.selection.targets is not None
            else default_selection.targets
        )
        diagnostics.extend(
            _validate_selection(
                effective_bundle,
                effective_targets,
                bundles,
                targets,
                path,
                f"{option_location}.selection",
            )
        )

    default_option = option_map.get(question.default_option)

    if default_option is None:
        diagnostics.append(
            Diagnostic(
                code=DEFAULT_OPTION_DIAGNOSTIC,
                message=(
                    f"question {question.id!r} defaultOption "
                    f"{question.default_option!r} does not reference "
                    "an option"
                ),
                source_path=path.as_posix(),
                location=f"{question_location}.defaultOption",
                related_identities=(
                    question.id,
                    question.default_option,
                ),
            )
        )
    elif default_option.classification is not SetupOptionClassification.RECOMMENDED:
        diagnostics.append(
            Diagnostic(
                code=DEFAULT_CLASSIFICATION_DIAGNOSTIC,
                message=(
                    f"question {question.id!r} defaultOption "
                    f"{question.default_option!r} must be classified "
                    "as recommended"
                ),
                source_path=path.as_posix(),
                location=f"{question_location}.defaultOption",
                related_identities=(
                    question.id,
                    question.default_option,
                ),
            )
        )

    return tuple(diagnostics)


def _validate_selection(
    bundle_name: str,
    selected_targets: tuple[str, ...],
    bundles: Mapping[str, ProjectedSetupBundle],
    targets: frozenset[str],
    path: Path,
    location: str,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    bundle = bundles.get(bundle_name)

    if bundle is None:
        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_BUNDLE_DIAGNOSTIC,
                message=f"selection references missing bundle {bundle_name!r}",
                source_path=path.as_posix(),
                location=f"{location}.bundle",
                related_identities=(bundle_name,),
            )
        )

    unknown_targets = sorted(set(selected_targets) - targets)

    for target in unknown_targets:
        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_TARGET_DIAGNOSTIC,
                message=f"selection references missing target {target!r}",
                source_path=path.as_posix(),
                location=f"{location}.targets",
                related_identities=(target,),
            )
        )

    if bundle is None:
        return tuple(diagnostics)

    outside_bundle = sorted((set(selected_targets) & targets) - bundle.targets)

    for target in outside_bundle:
        diagnostics.append(
            Diagnostic(
                code=TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC,
                message=(
                    f"target {target!r} is not supported by bundle {bundle_name!r}"
                ),
                source_path=path.as_posix(),
                location=f"{location}.targets",
                related_identities=(
                    bundle_name,
                    target,
                ),
            )
        )

    return tuple(diagnostics)


def _validate_unique_names(
    parsed_setups: list[_ParsedSetup],
) -> tuple[Diagnostic, ...]:
    seen: dict[str, Path] = {}
    diagnostics: list[Diagnostic] = []

    for parsed in parsed_setups:
        name = parsed.setup.name
        previous = seen.get(name)

        if previous is not None:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_NAME_DIAGNOSTIC,
                    message=f"setup name {name!r} is duplicated",
                    source_path=parsed.source_path.as_posix(),
                    location="name",
                    related_identities=(
                        previous.as_posix(),
                        parsed.source_path.as_posix(),
                        name,
                    ),
                )
            )
            continue

        seen[name] = parsed.source_path

    return tuple(diagnostics)
