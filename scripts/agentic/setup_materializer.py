#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from init_support import load_setup, require_string, require_string_list


def parse_answer_overrides(
    raw_answers: list[str] | None,
) -> dict[str, str]:
    overrides: dict[str, str] = {}

    for raw_answer in raw_answers or []:
        if "=" not in raw_answer:
            raise ValueError(
                f"Invalid --answer '{raw_answer}'. "
                "Expected format: question=value"
            )

        question, selected = raw_answer.split("=", 1)
        question = question.strip()
        selected = selected.strip()

        if not question:
            raise ValueError(
                f"Invalid --answer '{raw_answer}'. "
                "Question id must be non-empty"
            )

        if not selected:
            raise ValueError(
                f"Invalid --answer '{raw_answer}'. "
                "Selected value must be non-empty"
            )

        if question in overrides:
            raise ValueError(
                f"Duplicate --answer for question '{question}'"
            )

        overrides[question] = selected

    return overrides


def materialize_answer(
    setup_path: Path,
    question: dict[str, Any],
    index: int,
    answer_overrides: dict[str, str],
    used_overrides: set[str],
) -> dict[str, str]:
    question_id = require_string(question, "id", setup_path)
    recommended = require_string_list(
        question,
        "recommended",
        setup_path,
    )

    if question_id in answer_overrides:
        selected = answer_overrides[question_id]
        used_overrides.add(question_id)
    else:
        selected = recommended[0]

    options = question.get("options")
    if not isinstance(options, list) or not options:
        raise ValueError(
            f"{setup_path}: question '{question_id}' options "
            "must be a non-empty list"
        )

    options_by_value: dict[str, dict[str, Any]] = {}
    for option_index, option in enumerate(options):
        if not isinstance(option, dict):
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"options[{option_index}] must be an object"
            )

        option_value = option.get("value")
        if not isinstance(option_value, str) or not option_value.strip():
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"options[{option_index}].value must be a non-empty string"
            )

        options_by_value[option_value] = option

    selected_option = options_by_value.get(selected)
    if selected_option is None:
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"selected option '{selected}' does not exist"
        )

    blocked = question.get("blocked")
    if isinstance(blocked, list) and selected in blocked:
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"selected option '{selected}' is blocked"
        )

    compatible = question.get("compatible")
    if selected in recommended:
        classification = "recommended"
    elif isinstance(compatible, list) and selected in compatible:
        classification = "compatible"
    else:
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"selected option '{selected}' is neither recommended nor compatible"
        )

    reason = selected_option.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"option '{selected}' reason must be a non-empty string"
        )

    return {
        "question": question_id,
        "selected": selected,
        "classification": classification,
        "reason": reason,
    }


def selected_option_for_answer(
    setup_path: Path,
    setup: dict[str, Any],
    answer: dict[str, str],
) -> dict[str, Any]:
    question_id = answer["question"]
    selected = answer["selected"]

    questions = setup.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError(
            f"{setup_path}: questions must be a non-empty list"
        )

    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            raise ValueError(
                f"{setup_path}: questions[{index}] must be an object"
            )

        if question.get("id") != question_id:
            continue

        options = question.get("options")
        if not isinstance(options, list) or not options:
            raise ValueError(
                f"{setup_path}: question '{question_id}' options "
                "must be a non-empty list"
            )

        for option_index, option in enumerate(options):
            if not isinstance(option, dict):
                raise ValueError(
                    f"{setup_path}: question '{question_id}' "
                    f"options[{option_index}] must be an object"
                )

            if option.get("value") == selected:
                return option

        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"selected option '{selected}' does not exist"
        )

    raise ValueError(
        f"{setup_path}: answer references unknown "
        f"setup question '{question_id}'"
    )


def require_recommends(
    option: dict[str, Any],
    setup_path: Path,
    question_id: str,
    selected: str,
) -> dict[str, Any]:
    recommends = option.get("recommends", {})

    if not isinstance(recommends, dict):
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"option '{selected}' recommends must be an object"
        )

    return recommends


def require_optional_recommend_string(
    recommends: dict[str, Any],
    field: str,
    setup_path: Path,
    question_id: str,
    selected: str,
) -> str | None:
    if field not in recommends:
        return None

    value = recommends.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"option '{selected}' recommends.{field} "
            "must be a non-empty string"
        )

    return value


def require_optional_recommend_string_list(
    recommends: dict[str, Any],
    field: str,
    setup_path: Path,
    question_id: str,
    selected: str,
) -> list[str] | None:
    if field not in recommends:
        return None

    value = recommends.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"option '{selected}' recommends.{field} "
            "must be a non-empty list"
        )

    result: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"option '{selected}' recommends.{field}[{index}] "
                "must be a non-empty string"
            )

        if item in seen:
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"option '{selected}' recommends.{field}[{index}] "
                f"'{item}' is duplicated"
            )

        seen.add(item)
        result.append(item)

    return result


def materialize_selected(
    setup_path: Path,
    setup: dict[str, Any],
    default_bundle: str,
    answers: list[dict[str, str]],
) -> dict[str, Any]:
    final_recommendation = setup.get("finalRecommendation")
    if not isinstance(final_recommendation, dict):
        raise ValueError(
            f"{setup_path}: finalRecommendation must be an object"
        )

    selected: dict[str, Any] = {
        "bundle": require_string(
            final_recommendation,
            "bundle",
            setup_path,
        ),
        "profile": require_string(
            final_recommendation,
            "profile",
            setup_path,
        ),
        "workflow": require_string(
            final_recommendation,
            "workflow",
            setup_path,
        ),
        "agents": require_string_list(
            final_recommendation,
            "agents",
            setup_path,
        ),
        "skills": require_string_list(
            final_recommendation,
            "skills",
            setup_path,
        ),
        "artifacts": require_string_list(
            final_recommendation,
            "artifacts",
            setup_path,
        ),
        "targets": require_string_list(
            final_recommendation,
            "targets",
            setup_path,
        ),
    }

    if selected["bundle"] != default_bundle:
        raise ValueError(
            f"{setup_path}: finalRecommendation bundle "
            f"'{selected['bundle']}' must match defaultBundle "
            f"'{default_bundle}'"
        )

    scalar_sources: dict[str, str] = {}

    for answer in answers:
        question_id = answer["question"]
        answer_selected = answer["selected"]
        option = selected_option_for_answer(
            setup_path,
            setup,
            answer,
        )
        recommends = require_recommends(
            option,
            setup_path,
            question_id,
            answer_selected,
        )

        for field in ("bundle", "profile", "workflow"):
            recommended_value = require_optional_recommend_string(
                recommends,
                field,
                setup_path,
                question_id,
                answer_selected,
            )
            if recommended_value is None:
                continue

            previous_source = scalar_sources.get(field)
            if (
                previous_source is not None
                and selected[field] != recommended_value
            ):
                raise ValueError(
                    f"{setup_path}: conflicting recommends.{field} "
                    f"from {previous_source} and "
                    f"{question_id}={answer_selected}"
                )

            selected[field] = recommended_value
            scalar_sources[field] = (
                f"{question_id}={answer_selected}"
            )

        for field in ("agents", "skills", "artifacts", "targets"):
            recommended_values = (
                require_optional_recommend_string_list(
                    recommends,
                    field,
                    setup_path,
                    question_id,
                    answer_selected,
                )
            )
            if recommended_values is None:
                continue

            current_values = selected[field]
            if not isinstance(current_values, list):
                raise ValueError(
                    f"{setup_path}: selected.{field} "
                    "must be a list before applying recommends"
                )

            extra_values = sorted(
                set(recommended_values) - set(current_values)
            )
            if extra_values:
                raise ValueError(
                    f"{setup_path}: question '{question_id}' "
                    f"option '{answer_selected}' recommends.{field} "
                    "contains values outside the current selection: "
                    f"{extra_values}"
                )

            selected[field] = recommended_values

    if selected["bundle"] != default_bundle:
        raise ValueError(
            f"{setup_path}: selected bundle "
            f"'{selected['bundle']}' must match "
            f"defaultBundle '{default_bundle}'"
        )

    return selected


def materialize_setup_profile(
    setup_name: str,
    answer_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    setup_path, setup = load_setup(setup_name)

    mode = require_string(setup, "mode", setup_path)
    default_bundle = require_string(
        setup,
        "defaultBundle",
        setup_path,
    )

    questions = setup.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError(
            f"{setup_path}: questions must be a non-empty list"
        )

    overrides = answer_overrides or {}
    used_overrides: set[str] = set()

    answers: list[dict[str, str]] = []
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            raise ValueError(
                f"{setup_path}: questions[{index}] must be an object"
            )

        answers.append(
            materialize_answer(
                setup_path,
                question,
                index,
                overrides,
                used_overrides,
            )
        )

    unused_overrides = sorted(set(overrides) - used_overrides)
    if unused_overrides:
        raise ValueError(
            f"{setup_path}: --answer references unknown "
            f"setup question(s): {unused_overrides}"
        )

    return {
        "$schema": "./schemas/setup-profile.schema.json",
        "schemaVersion": "0.1.0",
        "mode": mode,
        "setup": setup_name,
        "answers": answers,
        "selected": materialize_selected(
            setup_path,
            setup,
            default_bundle,
            answers,
        ),
        "policy": {
            "failFast": True,
            "fallbackAllowed": False,
        },
    }
