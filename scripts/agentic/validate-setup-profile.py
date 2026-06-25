#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
DEFAULT_PROFILE_PATH = ROOT / ".agentic" / "setup-profile.json"
SCHEMA_VERSION = "0.1.0"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")

    return data


def registry_items(pattern: str, preferred_key: str = "name") -> dict[str, tuple[Path, dict[str, Any]]]:
    items: dict[str, tuple[Path, dict[str, Any]]] = {}

    for path in sorted(ROOT.glob(pattern)):
        data = load_json(path)
        value = data.get(preferred_key) or data.get("id") or path.stem.split(".")[0]

        if isinstance(value, str) and value.strip():
            items[value] = (path, data)

    return items


def registry_items_by_parent_folder(pattern: str) -> dict[str, tuple[Path, dict[str, Any]]]:
    items: dict[str, tuple[Path, dict[str, Any]]] = {}

    for path in sorted(ROOT.glob(pattern)):
        data = load_json(path)
        items[path.parent.name] = (path, data)

    return items


def require_string(data: dict[str, Any], field: str, path: Path, errors: list[str]) -> str | None:
    value = data.get(field)

    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: {field} must be a non-empty string")
        return None

    return value


def require_bool(data: dict[str, Any], field: str, path: Path, errors: list[str]) -> bool | None:
    value = data.get(field)

    if not isinstance(value, bool):
        errors.append(f"{path}: {field} must be a boolean")
        return None

    return value


def require_unique_string_list(data: dict[str, Any], field: str, path: Path, errors: list[str]) -> list[str]:
    value = data.get(field)

    if not isinstance(value, list) or not value:
        errors.append(f"{path}: {field} must be a non-empty list")
        return []

    result: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}: {field}[{index}] must be a non-empty string")
            continue

        if item in seen:
            errors.append(f"{path}: {field}[{index}] '{item}' is duplicated")

        seen.add(item)
        result.append(item)

    return result


def validate_reference(
    path: Path,
    field: str,
    value: str,
    available: set[str],
    label: str,
    errors: list[str],
) -> None:
    if value not in available:
        errors.append(f"{path}: selected {field} references missing {label} '{value}'")


def validate_reference_list(
    path: Path,
    field: str,
    values: list[str],
    available: set[str],
    label: str,
    errors: list[str],
) -> None:
    for value in values:
        validate_reference(path, field, value, available, label, errors)


def setup_file_for_name(setup_name: str) -> Path:
    return ROOT / "registry" / "setups" / f"{setup_name}.setup.json"


def validate_answers(profile_path: Path, profile: dict[str, Any], setup: dict[str, Any], errors: list[str]) -> None:
    answers = profile.get("answers")
    if not isinstance(answers, list) or not answers:
        errors.append(f"{profile_path}: answers must be a non-empty list")
        return

    setup_questions = setup.get("questions")
    if not isinstance(setup_questions, list) or not setup_questions:
        errors.append(f"{profile_path}: referenced setup questions must be a non-empty list")
        return

    questions_by_id: dict[str, dict[str, Any]] = {}
    for index, question in enumerate(setup_questions):
        if not isinstance(question, dict):
            errors.append(f"{profile_path}: setup question[{index}] must be an object")
            continue

        question_id = question.get("id")
        if not isinstance(question_id, str) or not question_id.strip():
            errors.append(f"{profile_path}: setup question[{index}].id must be a non-empty string")
            continue

        questions_by_id[question_id] = question

    seen_answers: set[str] = set()
    answered_questions: set[str] = set()

    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            errors.append(f"{profile_path}: answers[{index}] must be an object")
            continue

        question_id = require_string(answer, "question", profile_path, errors)
        selected = require_string(answer, "selected", profile_path, errors)
        classification = require_string(answer, "classification", profile_path, errors)
        reason = require_string(answer, "reason", profile_path, errors)

        if question_id is None or selected is None:
            continue

        if question_id in seen_answers:
            errors.append(f"{profile_path}: answers question '{question_id}' is duplicated")

        seen_answers.add(question_id)
        answered_questions.add(question_id)

        question = questions_by_id.get(question_id)
        if question is None:
            errors.append(f"{profile_path}: answers question '{question_id}' does not exist in setup")
            continue

        options = question.get("options")
        if not isinstance(options, list) or not options:
            errors.append(f"{profile_path}: setup question '{question_id}' options must be a non-empty list")
            continue

        options_by_value = {
            option.get("value"): option
            for option in options
            if isinstance(option, dict) and isinstance(option.get("value"), str) and option.get("value").strip()
        }

        selected_option = options_by_value.get(selected)
        if selected_option is None:
            errors.append(f"{profile_path}: answer for question '{question_id}' selects missing option '{selected}'")
            continue

        blocked = question.get("blocked")
        if isinstance(blocked, list) and selected in blocked:
            errors.append(f"{profile_path}: answer for question '{question_id}' selects blocked option '{selected}'")

        recommended = question.get("recommended")
        compatible = question.get("compatible")

        expected_classification: str | None = None
        if isinstance(recommended, list) and selected in recommended:
            expected_classification = "recommended"
        elif isinstance(compatible, list) and selected in compatible:
            expected_classification = "compatible"

        if expected_classification is None:
            errors.append(
                f"{profile_path}: answer for question '{question_id}' selects option '{selected}' "
                "which is neither recommended nor compatible"
            )
        elif classification != expected_classification:
            errors.append(
                f"{profile_path}: answer for question '{question_id}' classification '{classification}' "
                f"must be '{expected_classification}'"
            )

        expected_reason = selected_option.get("reason")
        if isinstance(expected_reason, str) and reason is not None and reason != expected_reason:
            errors.append(f"{profile_path}: answer for question '{question_id}' reason does not match setup option reason")

    expected_questions = set(questions_by_id)
    missing_answers = sorted(expected_questions - answered_questions)
    extra_answers = sorted(answered_questions - expected_questions)

    if missing_answers:
        errors.append(f"{profile_path}: missing answers for setup questions: {missing_answers}")

    if extra_answers:
        errors.append(f"{profile_path}: answers reference unknown setup questions: {extra_answers}")


def validate_selected(profile_path: Path, profile: dict[str, Any], setup: dict[str, Any], registries: dict[str, set[str]], errors: list[str]) -> None:
    selected = profile.get("selected")
    if not isinstance(selected, dict):
        errors.append(f"{profile_path}: selected must be an object")
        return

    bundle = require_string(selected, "bundle", profile_path, errors)
    profile_name = require_string(selected, "profile", profile_path, errors)
    workflow = require_string(selected, "workflow", profile_path, errors)
    agents = require_unique_string_list(selected, "agents", profile_path, errors)
    skills = require_unique_string_list(selected, "skills", profile_path, errors)
    artifacts = require_unique_string_list(selected, "artifacts", profile_path, errors)
    targets = require_unique_string_list(selected, "targets", profile_path, errors)

    if bundle is not None:
        validate_reference(profile_path, "bundle", bundle, registries["bundles"], "bundle", errors)

    if profile_name is not None:
        validate_reference(profile_path, "profile", profile_name, registries["profiles"], "profile", errors)

    if workflow is not None:
        validate_reference(profile_path, "workflow", workflow, registries["workflows"], "workflow", errors)

    validate_reference_list(profile_path, "agents", agents, registries["agents"], "agent", errors)
    validate_reference_list(profile_path, "skills", skills, registries["skills"], "skill", errors)
    validate_reference_list(profile_path, "artifacts", artifacts, registries["artifacts"], "artifact", errors)
    validate_reference_list(profile_path, "targets", targets, registries["targets"], "target", errors)

    default_bundle = setup.get("defaultBundle")
    if isinstance(default_bundle, str) and bundle is not None and bundle != default_bundle:
        errors.append(f"{profile_path}: selected bundle '{bundle}' must match setup defaultBundle '{default_bundle}'")

    final_recommendation = setup.get("finalRecommendation")
    if isinstance(final_recommendation, dict):
        expected_bundle = final_recommendation.get("bundle")
        expected_profile = final_recommendation.get("profile")
        expected_workflow = final_recommendation.get("workflow")

        if isinstance(expected_bundle, str) and bundle is not None and bundle != expected_bundle:
            errors.append(f"{profile_path}: selected bundle '{bundle}' must match setup finalRecommendation bundle '{expected_bundle}'")

        if isinstance(expected_profile, str) and profile_name is not None and profile_name != expected_profile:
            errors.append(f"{profile_path}: selected profile '{profile_name}' must match setup finalRecommendation profile '{expected_profile}'")

        if isinstance(expected_workflow, str) and workflow is not None and workflow != expected_workflow:
            errors.append(f"{profile_path}: selected workflow '{workflow}' must match setup finalRecommendation workflow '{expected_workflow}'")


def validate_policy(profile_path: Path, profile: dict[str, Any], errors: list[str]) -> None:
    policy = profile.get("policy")
    if not isinstance(policy, dict):
        errors.append(f"{profile_path}: policy must be an object")
        return

    fail_fast = require_bool(policy, "failFast", profile_path, errors)
    fallback_allowed = require_bool(policy, "fallbackAllowed", profile_path, errors)

    if fail_fast is not True:
        errors.append(f"{profile_path}: policy.failFast must be true")

    if fallback_allowed is not False:
        errors.append(f"{profile_path}: policy.fallbackAllowed must be false")


def validate_setup_profile(profile_path: Path) -> list[str]:
    errors: list[str] = []

    if not profile_path.is_file():
        return [f"Setup profile file not found: {profile_path}"]

    profile = load_json(profile_path)

    schema_version = require_string(profile, "schemaVersion", profile_path, errors)
    if schema_version is not None and schema_version != SCHEMA_VERSION:
        errors.append(f"{profile_path}: schemaVersion must be '{SCHEMA_VERSION}'")

    mode = require_string(profile, "mode", profile_path, errors)
    if mode is not None and mode not in {"greenfield", "brownfield"}:
        errors.append(f"{profile_path}: mode must be one of ['greenfield', 'brownfield']")

    setup_name = require_string(profile, "setup", profile_path, errors)
    if setup_name is None:
        return errors

    setup_path = setup_file_for_name(setup_name)
    if not setup_path.is_file():
        errors.append(f"{profile_path}: setup references missing setup registry file '{setup_name}'")
        return errors

    setup = load_json(setup_path)

    setup_mode = setup.get("mode")
    if isinstance(setup_mode, str) and mode is not None and setup_mode != mode:
        errors.append(f"{profile_path}: mode '{mode}' must match setup mode '{setup_mode}'")

    registries = {
        "agents": set(registry_items_by_parent_folder("registry/agents/*/agent.json")),
        "skills": set(registry_items_by_parent_folder("registry/skills/*/skill.json")),
        "artifacts": set(registry_items_by_parent_folder("registry/artifacts/*/artifact.json")),
        "targets": set(registry_items_by_parent_folder("registry/targets/*/adapter.json")),
        "workflows": set(registry_items("registry/workflows/*.workflow.json")),
        "profiles": set(registry_items("registry/profiles/*.profile.json")),
        "bundles": set(registry_items("registry/bundles/*.bundle.json")),
    }

    validate_answers(profile_path, profile, setup, errors)
    validate_selected(profile_path, profile, setup, registries, errors)
    validate_policy(profile_path, profile, errors)

    return errors


def main() -> int:
    profile_path = Path(DEFAULT_PROFILE_PATH)

    errors = validate_setup_profile(profile_path)

    if errors:
        print("ERROR: Setup profile validation failed.")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Setup profile is valid: {profile_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
