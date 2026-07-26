"""Typed, side-effect-free guided setup materialization."""

from __future__ import annotations

from collections.abc import Mapping

from agentic_workflow_generator.domain import (
    Setup,
    SetupAnswer,
    SetupAnswerClassification,
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

SETUP_PROFILE_SCHEMA_URI = "./schemas/setup-profile.schema.json"
SETUP_PROFILE_SCHEMA_VERSION = "0.2.0"


class SetupMaterializationError(ValueError):
    """Raised when validated setup choices cannot be materialized."""


def materialize_setup_profile(
    setup: Setup,
    answer_overrides: Mapping[str, str] | None = None,
) -> SetupProfile:
    """Materialize one immutable setup profile from typed setup input."""

    overrides = dict(answer_overrides or {})
    question_ids = {question.id for question in setup.questions}
    unknown_questions = sorted(set(overrides) - question_ids)

    if unknown_questions:
        raise SetupMaterializationError(
            "answer overrides reference unknown setup question(s): "
            f"{unknown_questions}"
        )

    answers: list[SetupAnswer] = []
    selected_options: list[tuple[str, SetupOption]] = []

    for question in setup.questions:
        selected_value = overrides.get(
            question.id,
            question.default_option,
        )
        option = _option_by_value(
            question.options,
            selected_value,
        )

        if option is None:
            raise SetupMaterializationError(
                f"question {question.id!r} selected option "
                f"{selected_value!r} does not exist"
            )

        if option.classification is SetupOptionClassification.BLOCKED:
            raise SetupMaterializationError(
                f"question {question.id!r} selected blocked option "
                f"{selected_value!r}"
            )

        answers.append(
            SetupAnswer(
                question=question.id,
                selected=option.value,
                classification=SetupAnswerClassification(
                    option.classification.value
                ),
                reason=option.reason,
            )
        )
        selected_options.append(
            (
                question.id,
                option,
            )
        )

    return SetupProfile(
        schema_uri=SETUP_PROFILE_SCHEMA_URI,
        schema_version=SETUP_PROFILE_SCHEMA_VERSION,
        mode=setup.mode,
        setup=setup.name,
        answers=tuple(answers),
        selected=_materialize_selection(
            setup.default_selection,
            tuple(selected_options),
        ),
        policy=SetupPolicy(
            fail_fast=True,
            fallback_allowed=False,
        ),
    )


def setup_profile_to_json(
    profile: SetupProfile,
) -> JsonObject:
    """Project one immutable setup profile to its JSON boundary."""

    answers: list[JsonValue] = []

    for answer in profile.answers:
        answers.append(
            {
                "question": answer.question,
                "selected": answer.selected,
                "classification": answer.classification.value,
                "reason": answer.reason,
            }
        )

    targets: list[JsonValue] = [
        target
        for target in profile.selected.targets
    ]

    data: JsonObject = {
        "schemaVersion": profile.schema_version,
        "mode": profile.mode.value,
        "setup": profile.setup,
        "answers": answers,
        "selected": {
            "bundle": profile.selected.bundle,
            "targets": targets,
        },
        "policy": {
            "failFast": profile.policy.fail_fast,
            "fallbackAllowed": profile.policy.fallback_allowed,
        },
    }

    if profile.schema_uri is not None:
        data["$schema"] = profile.schema_uri

    return data


def _option_by_value(
    options: tuple[SetupOption, ...],
    value: str,
) -> SetupOption | None:
    return next(
        (
            option
            for option in options
            if option.value == value
        ),
        None,
    )


def _materialize_selection(
    default_selection: SetupSelection,
    selected_options: tuple[tuple[str, SetupOption], ...],
) -> SetupSelection:
    bundle = default_selection.bundle
    targets = default_selection.targets
    bundle_source: str | None = None
    targets_source: str | None = None

    for question_id, option in selected_options:
        if option.selection is None:
            continue

        patch = option.selection
        source = f"{question_id}={option.value}"

        if patch.bundle is not None:
            if (
                bundle_source is not None
                and patch.bundle != bundle
            ):
                raise SetupMaterializationError(
                    "conflicting bundle selections from "
                    f"{bundle_source} and {source}"
                )

            bundle = patch.bundle

            if bundle_source is None:
                bundle_source = source

        if patch.targets is not None:
            if (
                targets_source is not None
                and patch.targets != targets
            ):
                raise SetupMaterializationError(
                    "conflicting target selections from "
                    f"{targets_source} and {source}"
                )

            targets = patch.targets

            if targets_source is None:
                targets_source = source

    return SetupSelection(
        bundle=bundle,
        targets=targets,
    )
