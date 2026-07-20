#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from init_support import (
    ROOT,
    SETUP_PROFILE_PATH,
    SETUP_REGISTRY_VALIDATOR,
    load_json,
    load_setup,
    require_string,
    require_string_list,
)
from setup_materializer import materialize_answer


def require_interactive_terminal() -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError(
            "Interactive --guided requires an attached terminal. "
            "Use --guided --setup <setup-name> for non-interactive execution."
        )


def read_interactive_input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError as exc:
        raise ValueError(
            "Interactive guided init received EOF; no files were written"
        ) from exc
    except KeyboardInterrupt as exc:
        print()
        raise ValueError(
            "Interactive guided init was cancelled; no files were written"
        ) from exc


def validate_setup_registry() -> None:
    if not SETUP_REGISTRY_VALIDATOR.is_file():
        raise ValueError(
            "Required setup registry validator not found: "
            f"{SETUP_REGISTRY_VALIDATOR}"
        )

    result = subprocess.run(
        [sys.executable, str(SETUP_REGISTRY_VALIDATOR)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode != 0:
        raise ValueError(
            "setup registry validation failed:\n"
            + result.stdout.rstrip()
        )


def registered_interactive_setups() -> list[tuple[str, str]]:
    setup_directory = ROOT / "registry" / "setups"
    if not setup_directory.is_dir():
        raise ValueError(
            f"Required setup registry directory not found: {setup_directory}"
        )

    registered: list[tuple[str, str]] = []
    for setup_path in sorted(setup_directory.glob("*.setup.json")):
        setup = load_json(setup_path)
        name = require_string(setup, "name", setup_path)
        description = require_string(setup, "description", setup_path)

        expected_filename = f"{name}.setup.json"
        if setup_path.name != expected_filename:
            raise ValueError(
                f"{setup_path}: setup name '{name}' "
                f"requires filename '{expected_filename}'"
            )

        registered.append((name, description))

    if not registered:
        raise ValueError(
            f"No guided setups are registered in {setup_directory}"
        )

    return registered


def choose_interactive_setup() -> str:
    registered = registered_interactive_setups()

    print("== Guided Agentic Initialization ==")
    print()
    print("Select a registered guided setup:")

    for index, (name, description) in enumerate(registered, start=1):
        default_marker = " [default]" if len(registered) == 1 else ""
        print(f"  {index}. {name}{default_marker}")
        print(f"     {description}")

    print()
    raw = read_interactive_input(
        "Setup number or name"
        + (" [1]" if len(registered) == 1 else "")
        + " (q to cancel): "
    )

    if raw.lower() in {"q", "quit"}:
        raise ValueError(
            "Interactive guided init was cancelled; no files were written"
        )

    if not raw:
        if len(registered) != 1:
            raise ValueError(
                "A setup selection is required "
                "when multiple setups are registered"
            )
        return registered[0][0]

    if raw.isdigit():
        selected_index = int(raw)
        if selected_index < 1 or selected_index > len(registered):
            raise ValueError(
                f"Invalid setup number '{raw}'. "
                f"Expected a value from 1 to {len(registered)}"
            )
        return registered[selected_index - 1][0]

    names = {name for name, _ in registered}
    if raw not in names:
        raise ValueError(f"Unknown guided setup '{raw}'")

    return raw


def optional_question_values(
    setup_path: Path,
    question: dict[str, Any],
    question_id: str,
    field: str,
) -> list[str]:
    value = question.get(field, [])
    if not isinstance(value, list):
        raise ValueError(
            f"{setup_path}: question '{question_id}' "
            f"{field} must be a list"
        )

    result: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"{field}[{index}] must be a non-empty string"
            )

        if item in seen:
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"{field}[{index}] duplicates '{item}'"
            )

        seen.add(item)
        result.append(item)

    return result


def interactive_question_selection(
    setup_path: Path,
    question: dict[str, Any],
    question_index: int,
    question_count: int,
) -> str | None:
    question_id = require_string(question, "id", setup_path)
    prompt = require_string(question, "prompt", setup_path)
    recommended = require_string_list(
        question,
        "recommended",
        setup_path,
    )
    compatible = optional_question_values(
        setup_path,
        question,
        question_id,
        "compatible",
    )
    blocked = optional_question_values(
        setup_path,
        question,
        question_id,
        "blocked",
    )

    options = question.get("options")
    if not isinstance(options, list) or not options:
        raise ValueError(
            f"{setup_path}: question '{question_id}' options "
            "must be a non-empty list"
        )

    print()
    print(
        f"Question {question_index + 1}/{question_count}: {prompt}"
    )

    option_values: list[str] = []

    for option_index, option in enumerate(options, start=1):
        if not isinstance(option, dict):
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"options[{option_index - 1}] must be an object"
            )

        value = require_string(option, "value", setup_path)
        label = require_string(option, "label", setup_path)
        reason = require_string(option, "reason", setup_path)
        option_values.append(value)

        if value in recommended:
            classification = "recommended"
        elif value in compatible:
            classification = "compatible"
        elif value in blocked:
            classification = "blocked"
        else:
            raise ValueError(
                f"{setup_path}: question '{question_id}' "
                f"option '{value}' is not classified as "
                "recommended, compatible, or blocked"
            )

        default_marker = (
            " [default]" if value == recommended[0] else ""
        )
        print(
            f"  {option_index}. {label} "
            f"[{classification}]{default_marker}"
        )
        print(f"     {value}")
        print(f"     {reason}")

    print()
    raw = read_interactive_input(
        f"Selection [{recommended[0]}] "
        "(b to go back, q to cancel): "
    )

    lowered = raw.lower()
    if lowered in {"q", "quit"}:
        raise ValueError(
            "Interactive guided init was cancelled; no files were written"
        )

    if lowered in {"b", "back"}:
        return None

    if not raw:
        selected = recommended[0]
    elif raw.isdigit():
        selected_index = int(raw)
        if (
            selected_index < 1
            or selected_index > len(option_values)
        ):
            raise ValueError(
                f"Invalid option number '{raw}' "
                f"for question '{question_id}'. "
                f"Expected a value from 1 to {len(option_values)}"
            )
        selected = option_values[selected_index - 1]
    else:
        selected = raw

    used_overrides: set[str] = set()
    materialized = materialize_answer(
        setup_path,
        question,
        question_index,
        {question_id: selected},
        used_overrides,
    )
    return materialized["selected"]


def collect_interactive_answers(
    setup_name: str,
) -> dict[str, str] | None:
    setup_path, setup = load_setup(setup_name)
    questions = setup.get("questions")

    if not isinstance(questions, list) or not questions:
        raise ValueError(
            f"{setup_path}: questions must be a non-empty list"
        )

    overrides: dict[str, str] = {}
    question_index = 0

    while question_index < len(questions):
        question = questions[question_index]
        if not isinstance(question, dict):
            raise ValueError(
                f"{setup_path}: questions[{question_index}] "
                "must be an object"
            )

        selected = interactive_question_selection(
            setup_path,
            question,
            question_index,
            len(questions),
        )

        if selected is None:
            if question_index == 0:
                return None

            previous_question = questions[question_index - 1]
            if not isinstance(previous_question, dict):
                raise ValueError(
                    f"{setup_path}: questions[{question_index - 1}] "
                    "must be an object"
                )

            previous_id = require_string(
                previous_question,
                "id",
                setup_path,
            )
            overrides.pop(previous_id, None)
            question_index -= 1
            continue

        question_id = require_string(
            question,
            "id",
            setup_path,
        )
        overrides[question_id] = selected
        question_index += 1

    return overrides


def print_guided_plan(
    setup_profile: dict[str, Any],
) -> None:
    setup_name = require_string(
        setup_profile,
        "setup",
        SETUP_PROFILE_PATH,
    )
    mode = require_string(
        setup_profile,
        "mode",
        SETUP_PROFILE_PATH,
    )

    answers = setup_profile.get("answers")
    if not isinstance(answers, list) or not answers:
        raise ValueError(
            f"{SETUP_PROFILE_PATH}: answers must be a non-empty list"
        )

    selected = setup_profile.get("selected")
    if not isinstance(selected, dict):
        raise ValueError(
            f"{SETUP_PROFILE_PATH}: selected must be an object"
        )

    print()
    print("== Generated Setup Plan ==")
    print(f"Setup: {setup_name}")
    print(f"Mode: {mode}")
    print("Answers:")

    for answer in answers:
        if not isinstance(answer, dict):
            raise ValueError(
                f"{SETUP_PROFILE_PATH}: "
                "each answer must be an object"
            )

        question_id = require_string(
            answer,
            "question",
            SETUP_PROFILE_PATH,
        )
        selected_value = require_string(
            answer,
            "selected",
            SETUP_PROFILE_PATH,
        )
        classification = require_string(
            answer,
            "classification",
            SETUP_PROFILE_PATH,
        )
        print(
            f"  {question_id}: "
            f"{selected_value} [{classification}]"
        )

    print("Selected composition:")

    for field in ("bundle", "profile", "workflow"):
        print(
            f"  {field}: "
            f"{require_string(selected, field, SETUP_PROFILE_PATH)}"
        )

    for field in ("agents", "skills", "artifacts", "targets"):
        values = require_string_list(
            selected,
            field,
            SETUP_PROFILE_PATH,
        )
        print(f"  {field}: {', '.join(values)}")

    print("Policy:")
    print("  failFast: true")
    print("  fallbackAllowed: false")


def confirm_guided_plan() -> None:
    print()
    answer = read_interactive_input(
        "Write .agentic/setup-profile.json "
        "and .agentic/agentic.json? [y/N]: "
    ).lower()

    if answer in {"y", "yes"}:
        return

    if answer in {"", "n", "no", "q", "quit"}:
        raise ValueError(
            "Interactive guided init was cancelled; no files were written"
        )

    raise ValueError(
        f"Invalid confirmation '{answer}'. "
        "Expected 'y' or 'n'; no files were written"
    )
