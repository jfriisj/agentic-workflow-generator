#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
SETUPS_DIR = ROOT / "registry" / "setups"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")

    return data


def expected_setup_name(path: Path) -> str:
    return path.name.removesuffix(".setup.json")


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


def require_string(value: object, path: Path, field: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: {field} must be a non-empty string")
        return None

    return value


def require_unique_string_list(value: object, path: Path, field: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path}: {field} must be a list")
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


def require_non_empty_unique_string_list(value: object, path: Path, field: str, errors: list[str]) -> list[str]:
    result = require_unique_string_list(value, path, field, errors)

    if not result:
        errors.append(f"{path}: {field} must contain at least one item")

    return result


def validate_reference(path: Path, context: str, field: str, value: str, available: set[str], label: str, errors: list[str]) -> None:
    if value not in available:
        errors.append(f"{path}: {context} {field} references missing {label} '{value}'")


def validate_reference_list(
    path: Path,
    context: str,
    field: str,
    values: object,
    available: set[str],
    label: str,
    errors: list[str],
) -> None:
    items = require_unique_string_list(values, path, f"{context}.{field}", errors)

    for value in items:
        validate_reference(path, context, field, value, available, label, errors)


def validate_recommendation_object(
    path: Path,
    context: str,
    value: object,
    registries: dict[str, set[str]],
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: {context} must be an object")
        return

    bundle = value.get("bundle")
    if bundle is not None:
        if isinstance(bundle, str) and bundle.strip():
            validate_reference(path, context, "bundle", bundle, registries["bundles"], "bundle", errors)
        else:
            errors.append(f"{path}: {context}.bundle must be a non-empty string")

    profile = value.get("profile")
    if profile is not None:
        if isinstance(profile, str) and profile.strip():
            validate_reference(path, context, "profile", profile, registries["profiles"], "profile", errors)
        else:
            errors.append(f"{path}: {context}.profile must be a non-empty string")

    workflow = value.get("workflow")
    if workflow is not None:
        if isinstance(workflow, str) and workflow.strip():
            validate_reference(path, context, "workflow", workflow, registries["workflows"], "workflow", errors)
        else:
            errors.append(f"{path}: {context}.workflow must be a non-empty string")

    if "agents" in value:
        validate_reference_list(path, context, "agents", value["agents"], registries["agents"], "agent", errors)

    if "skills" in value:
        validate_reference_list(path, context, "skills", value["skills"], registries["skills"], "skill", errors)

    if "artifacts" in value:
        validate_reference_list(path, context, "artifacts", value["artifacts"], registries["artifacts"], "artifact", errors)

    if "targets" in value:
        validate_reference_list(path, context, "targets", value["targets"], registries["targets"], "target", errors)


def validate_question(path: Path, question: object, index: int, registries: dict[str, set[str]], errors: list[str]) -> None:
    if not isinstance(question, dict):
        errors.append(f"{path}: questions[{index}] must be an object")
        return

    question_id = require_string(question.get("id"), path, f"questions[{index}].id", errors) or f"questions[{index}]"
    options = question.get("options")

    if not isinstance(options, list) or not options:
        errors.append(f"{path}: question '{question_id}' options must be a non-empty list")
        return

    option_values: list[str] = []
    seen_options: set[str] = set()

    for option_index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"{path}: question '{question_id}' option[{option_index}] must be an object")
            continue

        value = require_string(option.get("value"), path, f"question '{question_id}' option[{option_index}].value", errors)
        require_string(option.get("label"), path, f"question '{question_id}' option[{option_index}].label", errors)
        require_string(option.get("reason"), path, f"question '{question_id}' option[{option_index}].reason", errors)

        if value is not None:
            if value in seen_options:
                errors.append(f"{path}: question '{question_id}' option value '{value}' is duplicated")

            seen_options.add(value)
            option_values.append(value)

        recommends = option.get("recommends")
        if recommends is not None:
            validate_recommendation_object(
                path,
                f"question '{question_id}' option '{value or option_index}'.recommends",
                recommends,
                registries,
                errors,
            )

    option_value_set = set(option_values)

    recommended = require_non_empty_unique_string_list(
        question.get("recommended"),
        path,
        f"question '{question_id}'.recommended",
        errors,
    )
    compatible = require_unique_string_list(
        question.get("compatible"),
        path,
        f"question '{question_id}'.compatible",
        errors,
    )
    blocked = require_unique_string_list(
        question.get("blocked"),
        path,
        f"question '{question_id}'.blocked",
        errors,
    )

    categories = {
        "recommended": set(recommended),
        "compatible": set(compatible),
        "blocked": set(blocked),
    }

    for category, values in categories.items():
        for value in values:
            if value not in option_value_set:
                errors.append(f"{path}: question '{question_id}' {category} references missing option '{value}'")

    for left_name, right_name in [
        ("recommended", "compatible"),
        ("recommended", "blocked"),
        ("compatible", "blocked"),
    ]:
        overlap = sorted(categories[left_name] & categories[right_name])
        if overlap:
            errors.append(
                f"{path}: question '{question_id}' has overlapping {left_name}/{right_name} values: {overlap}"
            )


def validate_setup_file(path: Path, registries: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    data = load_json(path)

    name = require_string(data.get("name"), path, "name", errors)
    if name is not None and name != expected_setup_name(path):
        errors.append(f"{path}: setup name '{name}' must match file name '{expected_setup_name(path)}'")

    mode = require_string(data.get("mode"), path, "mode", errors)
    if mode is not None and mode not in {"greenfield", "brownfield"}:
        errors.append(f"{path}: mode must be one of ['greenfield', 'brownfield']")

    default_bundle = require_string(data.get("defaultBundle"), path, "defaultBundle", errors)
    if default_bundle is not None:
        validate_reference(path, "defaultBundle", "defaultBundle", default_bundle, registries["bundles"], "bundle", errors)

    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        errors.append(f"{path}: questions must be a non-empty list")
    else:
        seen_question_ids: set[str] = set()

        for index, question in enumerate(questions):
            if isinstance(question, dict):
                question_id = question.get("id")
                if isinstance(question_id, str) and question_id.strip():
                    if question_id in seen_question_ids:
                        errors.append(f"{path}: question id '{question_id}' is duplicated")

                    seen_question_ids.add(question_id)

            validate_question(path, question, index, registries, errors)

    final_recommendation = data.get("finalRecommendation")
    validate_recommendation_object(path, "finalRecommendation", final_recommendation, registries, errors)

    if isinstance(final_recommendation, dict):
        for field in ["bundle", "profile", "workflow", "agents", "skills", "artifacts", "targets"]:
            if field not in final_recommendation:
                errors.append(f"{path}: finalRecommendation missing required field '{field}'")

        if default_bundle is not None and final_recommendation.get("bundle") != default_bundle:
            errors.append(
                f"{path}: finalRecommendation bundle '{final_recommendation.get('bundle')}' "
                f"must match defaultBundle '{default_bundle}'"
            )

    return errors


def main() -> int:
    if not SETUPS_DIR.is_dir():
        print(f"ERROR: Setup registry directory not found: {SETUPS_DIR}")
        return 1

    setup_files = sorted(SETUPS_DIR.glob("*.setup.json"))
    if not setup_files:
        print(f"ERROR: No setup registry files found in {SETUPS_DIR}")
        return 1

    registries = {
        "agents": set(registry_items_by_parent_folder("registry/agents/*/agent.json")),
        "skills": set(registry_items_by_parent_folder("registry/skills/*/skill.json")),
        "artifacts": set(registry_items_by_parent_folder("registry/artifacts/*/artifact.json")),
        "targets": set(registry_items_by_parent_folder("registry/targets/*/adapter.json")),
        "workflows": set(registry_items("registry/workflows/*.workflow.json")),
        "profiles": set(registry_items("registry/profiles/*.profile.json")),
        "bundles": set(registry_items("registry/bundles/*.bundle.json")),
    }

    all_errors: list[str] = []

    for path in setup_files:
        try:
            all_errors.extend(validate_setup_file(path, registries))
        except json.JSONDecodeError as exc:
            all_errors.append(f"{path}: invalid JSON: {exc}")
        except ValueError as exc:
            all_errors.append(str(exc))

    if all_errors:
        print("ERROR: Setup registry validation failed.")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print(f"PASS: Setup registry is valid. Checked {len(setup_files)} setup file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
