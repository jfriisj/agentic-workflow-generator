"""Materialized guided setup-profile parsing and validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.domain import (
    Diagnostic,
    Setup,
    SetupAnswer,
    SetupAnswerClassification,
    SetupMode,
    SetupOption,
    SetupOptionClassification,
    SetupPolicy,
    SetupProfile,
    SetupSelection,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.validation.schema_support import (
    object_schema_diagnostics,
)
from agentic_workflow_generator.validation.schema_support import (
    schema_error_location as shared_schema_error_location,
)
from agentic_workflow_generator.validation.setups import (
    ProjectedSetupBundle,
    SetupReferenceData,
)

SCHEMA_DIAGNOSTIC = "AWG-SETUP-PROFILE-001"
OBSOLETE_FIELD_DIAGNOSTIC = "AWG-SETUP-PROFILE-002"
UNKNOWN_SETUP_DIAGNOSTIC = "AWG-SETUP-PROFILE-003"
MODE_MISMATCH_DIAGNOSTIC = "AWG-SETUP-PROFILE-004"
DUPLICATE_ANSWER_DIAGNOSTIC = "AWG-SETUP-PROFILE-005"
MISSING_ANSWER_DIAGNOSTIC = "AWG-SETUP-PROFILE-006"
UNKNOWN_QUESTION_DIAGNOSTIC = "AWG-SETUP-PROFILE-007"
UNKNOWN_OPTION_DIAGNOSTIC = "AWG-SETUP-PROFILE-008"
BLOCKED_OPTION_DIAGNOSTIC = "AWG-SETUP-PROFILE-009"
CLASSIFICATION_DIAGNOSTIC = "AWG-SETUP-PROFILE-010"
REASON_DIAGNOSTIC = "AWG-SETUP-PROFILE-011"
SELECTION_CONFLICT_DIAGNOSTIC = "AWG-SETUP-PROFILE-012"
SELECTED_MISMATCH_DIAGNOSTIC = "AWG-SETUP-PROFILE-013"
UNKNOWN_BUNDLE_DIAGNOSTIC = "AWG-SETUP-PROFILE-014"
UNKNOWN_TARGET_DIAGNOSTIC = "AWG-SETUP-PROFILE-015"
TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC = "AWG-SETUP-PROFILE-016"

_OBSOLETE_SELECTED_FIELDS = frozenset(
    {
        "profile",
        "workflow",
        "agents",
        "skills",
        "artifacts",
    }
)


@dataclass(frozen=True, slots=True)
class SetupProfileValidationResult:
    """Parsed setup profile and deterministic diagnostics."""

    profile: SetupProfile | None
    diagnostics: tuple[Diagnostic, ...]

    @property
    def is_valid(self) -> bool:
        return not self.diagnostics


def validate_setup_profile(
    data: JsonObject,
    source_path: Path,
    schema: JsonObject,
    setups: tuple[Setup, ...],
    references: SetupReferenceData,
) -> SetupProfileValidationResult:
    """Validate one materialized setup profile without side effects."""

    obsolete_diagnostics = _validate_obsolete_fields(
        data,
        source_path,
    )

    if obsolete_diagnostics:
        return SetupProfileValidationResult(
            profile=None,
            diagnostics=obsolete_diagnostics,
        )

    validator = Draft202012Validator(cast(Mapping[str, Any], schema))
    schema_diagnostics = _validate_schema(
        data,
        source_path,
        validator,
    )

    if schema_diagnostics:
        return SetupProfileValidationResult(
            profile=None,
            diagnostics=schema_diagnostics,
        )

    profile = _parse_profile(data)
    diagnostics = _validate_semantics(
        profile,
        source_path,
        setups,
        references,
    )

    return SetupProfileValidationResult(
        profile=profile,
        diagnostics=diagnostics,
    )


def _validate_obsolete_fields(
    data: JsonObject,
    source_path: Path,
) -> tuple[Diagnostic, ...]:
    selected = data.get("selected")

    if not isinstance(selected, Mapping):
        return ()

    fields = sorted(_OBSOLETE_SELECTED_FIELDS.intersection(selected))

    return tuple(
        Diagnostic(
            code=OBSOLETE_FIELD_DIAGNOSTIC,
            message=(f"obsolete selected field {field!r} is not allowed"),
            source_path=source_path.as_posix(),
            location=f"selected.{field}",
            related_identities=(field,),
        )
        for field in fields
    )


def _validate_schema(
    data: JsonObject,
    source_path: Path,
    validator: Draft202012Validator,
) -> tuple[Diagnostic, ...]:
    return object_schema_diagnostics(
        data,
        source_path,
        validator,
        SCHEMA_DIAGNOSTIC,
    )


def _schema_error_location(
    error: ValidationError,
) -> str:
    return shared_schema_error_location(error)


def _parse_profile(
    data: JsonObject,
) -> SetupProfile:
    raw_answers = cast(list[JsonValue], data["answers"])
    raw_selected = cast(
        Mapping[str, JsonValue],
        data["selected"],
    )
    raw_policy = cast(
        Mapping[str, JsonValue],
        data["policy"],
    )

    return SetupProfile(
        schema_uri=cast(str | None, data.get("$schema")),
        schema_version=cast(str, data["schemaVersion"]),
        mode=SetupMode(cast(str, data["mode"])),
        setup=cast(str, data["setup"]),
        answers=tuple(
            _parse_answer(cast(Mapping[str, JsonValue], raw_answer))
            for raw_answer in raw_answers
        ),
        selected=SetupSelection(
            bundle=cast(str, raw_selected["bundle"]),
            targets=tuple(cast(list[str], raw_selected["targets"])),
        ),
        policy=SetupPolicy(
            fail_fast=cast(bool, raw_policy["failFast"]),
            fallback_allowed=cast(
                bool,
                raw_policy["fallbackAllowed"],
            ),
        ),
    )


def _parse_answer(
    raw_answer: Mapping[str, JsonValue],
) -> SetupAnswer:
    return SetupAnswer(
        question=cast(str, raw_answer["question"]),
        selected=cast(str, raw_answer["selected"]),
        classification=SetupAnswerClassification(
            cast(str, raw_answer["classification"])
        ),
        reason=cast(str, raw_answer["reason"]),
    )


def _validate_semantics(
    profile: SetupProfile,
    source_path: Path,
    setups: tuple[Setup, ...],
    references: SetupReferenceData,
) -> tuple[Diagnostic, ...]:
    setup_map = {setup.name: setup for setup in setups}
    setup = setup_map.get(profile.setup)

    if setup is None:
        return (
            Diagnostic(
                code=UNKNOWN_SETUP_DIAGNOSTIC,
                message=(f"setup profile references missing setup {profile.setup!r}"),
                source_path=source_path.as_posix(),
                location="setup",
                related_identities=(profile.setup,),
            ),
        )

    diagnostics: list[Diagnostic] = []

    if profile.mode is not setup.mode:
        diagnostics.append(
            Diagnostic(
                code=MODE_MISMATCH_DIAGNOSTIC,
                message=(
                    f"mode {profile.mode.value!r} must match "
                    f"setup mode {setup.mode.value!r}"
                ),
                source_path=source_path.as_posix(),
                location="mode",
                related_identities=(
                    profile.mode.value,
                    setup.mode.value,
                ),
            )
        )

    answer_map: dict[str, SetupAnswer] = {}
    question_map = {question.id: question for question in setup.questions}

    for index, answer in enumerate(profile.answers):
        location = f"answers[{index}]"
        previous = answer_map.get(answer.question)

        if previous is not None:
            diagnostics.append(
                Diagnostic(
                    code=DUPLICATE_ANSWER_DIAGNOSTIC,
                    message=(f"answer for question {answer.question!r} is duplicated"),
                    source_path=source_path.as_posix(),
                    location=f"{location}.question",
                    related_identities=(answer.question,),
                )
            )
            continue

        answer_map[answer.question] = answer
        question = question_map.get(answer.question)

        if question is None:
            diagnostics.append(
                Diagnostic(
                    code=UNKNOWN_QUESTION_DIAGNOSTIC,
                    message=(f"answer references unknown question {answer.question!r}"),
                    source_path=source_path.as_posix(),
                    location=f"{location}.question",
                    related_identities=(answer.question,),
                )
            )
            continue

        option = _option_by_value(
            question.options,
            answer.selected,
        )

        if option is None:
            diagnostics.append(
                Diagnostic(
                    code=UNKNOWN_OPTION_DIAGNOSTIC,
                    message=(
                        f"answer for question {answer.question!r} "
                        f"selects missing option "
                        f"{answer.selected!r}"
                    ),
                    source_path=source_path.as_posix(),
                    location=f"{location}.selected",
                    related_identities=(
                        answer.question,
                        answer.selected,
                    ),
                )
            )
            continue

        diagnostics.extend(
            _validate_answer(
                answer,
                option,
                source_path,
                location,
            )
        )

    for question in setup.questions:
        if question.id not in answer_map:
            diagnostics.append(
                Diagnostic(
                    code=MISSING_ANSWER_DIAGNOSTIC,
                    message=(f"missing answer for setup question {question.id!r}"),
                    source_path=source_path.as_posix(),
                    location="answers",
                    related_identities=(question.id,),
                )
            )

    expected, selection_diagnostics = _expected_selection(
        setup,
        answer_map,
        source_path,
    )
    diagnostics.extend(selection_diagnostics)

    if expected is not None:
        if profile.selected.bundle != expected.bundle:
            diagnostics.append(
                Diagnostic(
                    code=SELECTED_MISMATCH_DIAGNOSTIC,
                    message=(
                        "selected bundle must match the materialized setup answers"
                    ),
                    source_path=source_path.as_posix(),
                    location="selected.bundle",
                    related_identities=(
                        profile.selected.bundle,
                        expected.bundle,
                    ),
                )
            )

        if profile.selected.targets != expected.targets:
            diagnostics.append(
                Diagnostic(
                    code=SELECTED_MISMATCH_DIAGNOSTIC,
                    message=(
                        "selected targets must match the materialized setup answers"
                    ),
                    source_path=source_path.as_posix(),
                    location="selected.targets",
                    related_identities=tuple(
                        dict.fromkeys(
                            (
                                *profile.selected.targets,
                                *expected.targets,
                            )
                        )
                    ),
                )
            )

    diagnostics.extend(
        _validate_selected_references(
            profile.selected,
            references,
            source_path,
        )
    )

    return tuple(diagnostics)


def _option_by_value(
    options: tuple[SetupOption, ...],
    value: str,
) -> SetupOption | None:
    return next(
        (option for option in options if option.value == value),
        None,
    )


def _validate_answer(
    answer: SetupAnswer,
    option: SetupOption,
    source_path: Path,
    location: str,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []

    if option.classification is SetupOptionClassification.BLOCKED:
        diagnostics.append(
            Diagnostic(
                code=BLOCKED_OPTION_DIAGNOSTIC,
                message=(
                    f"answer for question {answer.question!r} "
                    f"selects blocked option {answer.selected!r}"
                ),
                source_path=source_path.as_posix(),
                location=f"{location}.selected",
                related_identities=(
                    answer.question,
                    answer.selected,
                ),
            )
        )
        return tuple(diagnostics)

    expected_classification = SetupAnswerClassification(option.classification.value)

    if answer.classification is not expected_classification:
        diagnostics.append(
            Diagnostic(
                code=CLASSIFICATION_DIAGNOSTIC,
                message=(
                    f"classification "
                    f"{answer.classification.value!r} must be "
                    f"{expected_classification.value!r}"
                ),
                source_path=source_path.as_posix(),
                location=f"{location}.classification",
                related_identities=(
                    answer.question,
                    answer.selected,
                ),
            )
        )

    if answer.reason != option.reason:
        diagnostics.append(
            Diagnostic(
                code=REASON_DIAGNOSTIC,
                message=(
                    f"reason for question {answer.question!r} "
                    "does not match the setup option reason"
                ),
                source_path=source_path.as_posix(),
                location=f"{location}.reason",
                related_identities=(
                    answer.question,
                    answer.selected,
                ),
            )
        )

    return tuple(diagnostics)


def _expected_selection(
    setup: Setup,
    answers: Mapping[str, SetupAnswer],
    source_path: Path,
) -> tuple[
    SetupSelection | None,
    tuple[Diagnostic, ...],
]:
    bundle = setup.default_selection.bundle
    targets = setup.default_selection.targets
    bundle_source: str | None = None
    targets_source: str | None = None
    diagnostics: list[Diagnostic] = []

    for question in setup.questions:
        answer = answers.get(question.id)

        if answer is None:
            continue

        option = _option_by_value(
            question.options,
            answer.selected,
        )

        if option is None or option.selection is None:
            continue

        patch = option.selection
        source = f"{question.id}={answer.selected}"

        if patch.bundle is not None:
            if bundle_source is not None and patch.bundle != bundle:
                diagnostics.append(
                    _selection_conflict(
                        source_path,
                        "bundle",
                        bundle_source,
                        source,
                    )
                )
            else:
                bundle = patch.bundle
                bundle_source = source

        if patch.targets is not None:
            if targets_source is not None and patch.targets != targets:
                diagnostics.append(
                    _selection_conflict(
                        source_path,
                        "targets",
                        targets_source,
                        source,
                    )
                )
            else:
                targets = patch.targets
                targets_source = source

    if diagnostics:
        return None, tuple(diagnostics)

    return (
        SetupSelection(
            bundle=bundle,
            targets=targets,
        ),
        (),
    )


def _selection_conflict(
    source_path: Path,
    field: str,
    first_source: str,
    second_source: str,
) -> Diagnostic:
    return Diagnostic(
        code=SELECTION_CONFLICT_DIAGNOSTIC,
        message=(
            f"conflicting setup selection for {field} "
            f"from {first_source} and {second_source}"
        ),
        source_path=source_path.as_posix(),
        location=f"selected.{field}",
        related_identities=(
            first_source,
            second_source,
        ),
    )


def _validate_selected_references(
    selected: SetupSelection,
    references: SetupReferenceData,
    source_path: Path,
) -> tuple[Diagnostic, ...]:
    bundle_map: dict[str, ProjectedSetupBundle] = {
        bundle.name: bundle for bundle in references.bundles
    }
    bundle = bundle_map.get(selected.bundle)
    diagnostics: list[Diagnostic] = []

    if bundle is None:
        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_BUNDLE_DIAGNOSTIC,
                message=(f"selected bundle {selected.bundle!r} is not registered"),
                source_path=source_path.as_posix(),
                location="selected.bundle",
                related_identities=(selected.bundle,),
            )
        )

    unknown_targets = sorted(set(selected.targets) - references.targets)

    for target in unknown_targets:
        diagnostics.append(
            Diagnostic(
                code=UNKNOWN_TARGET_DIAGNOSTIC,
                message=(f"selected target {target!r} is not registered"),
                source_path=source_path.as_posix(),
                location="selected.targets",
                related_identities=(target,),
            )
        )

    if bundle is None:
        return tuple(diagnostics)

    outside_bundle = sorted(
        (set(selected.targets) & references.targets) - bundle.targets
    )

    for target in outside_bundle:
        diagnostics.append(
            Diagnostic(
                code=TARGET_OUTSIDE_BUNDLE_DIAGNOSTIC,
                message=(
                    f"selected target {target!r} is not supported "
                    f"by bundle {selected.bundle!r}"
                ),
                source_path=source_path.as_posix(),
                location="selected.targets",
                related_identities=(
                    selected.bundle,
                    target,
                ),
            )
        )

    return tuple(diagnostics)
