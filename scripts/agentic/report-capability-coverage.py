#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
BUNDLES_DIR = ROOT / "registry" / "bundles"
SKILLS_DIR = ROOT / "registry" / "skills"


class ValidationError(Exception):
    pass


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"Required file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"{path}: invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected JSON object")

    return data


def require_registry_files(
    directory: Path,
    pattern: str,
    label: str,
) -> list[Path]:
    paths = sorted(directory.glob(pattern))

    if not paths:
        raise ValidationError(
            f"No {label} registry files found in {directory}"
        )

    return paths


def require_unique_string_list(
    path: Path,
    value: object,
    field: str,
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValidationError(
            f"{path}: {field} must be a non-empty list"
        )

    result: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                f"{path}: {field}[{index}] must be a "
                "non-empty string"
            )

        normalized = item.strip()

        if normalized in seen:
            raise ValidationError(
                f"{path}: {field} entry "
                f"'{normalized}' is duplicated"
            )

        seen.add(normalized)
        result.append(normalized)

    return result


def collect_runtime_requirements() -> dict[str, list[str]]:
    required_by: dict[str, list[str]] = {}

    bundle_paths = require_registry_files(
        BUNDLES_DIR,
        "*.bundle.json",
        "bundle",
    )

    for bundle_path in bundle_paths:
        bundle = load_json_object(bundle_path)
        bundle_name = bundle.get("name")

        if not isinstance(bundle_name, str) or not bundle_name.strip():
            raise ValidationError(
                f"{bundle_path}: name must be a non-empty string"
            )

        bindings = bundle.get("roleBindings")

        if not isinstance(bindings, list) or not bindings:
            raise ValidationError(
                f"{bundle_path}: roleBindings must be a "
                "non-empty list"
            )

        for index, binding in enumerate(bindings):
            if not isinstance(binding, dict):
                raise ValidationError(
                    f"{bundle_path}: roleBindings[{index}] "
                    "must be an object"
                )

            role_name = binding.get("roleName")

            if (
                not isinstance(role_name, str)
                or not role_name.strip()
            ):
                raise ValidationError(
                    f"{bundle_path}: roleBindings[{index}]."
                    "roleName must be a non-empty string"
                )

            capabilities = require_unique_string_list(
                bundle_path,
                binding.get("requiredCapabilities"),
                (
                    f"roleBindings[{index}]."
                    "requiredCapabilities"
                ),
            )

            source = (
                f"{bundle_name.strip()}:{role_name.strip()}"
            )

            for capability in capabilities:
                required_by.setdefault(
                    capability,
                    [],
                ).append(source)

    return required_by


def collect_skill_providers() -> dict[str, list[str]]:
    provided_by: dict[str, list[str]] = {}

    skill_paths = require_registry_files(
        SKILLS_DIR,
        "*/skill.json",
        "skill",
    )

    for skill_path in skill_paths:
        skill = load_json_object(skill_path)
        skill_name = skill.get("name")

        if (
            not isinstance(skill_name, str)
            or not skill_name.strip()
        ):
            raise ValidationError(
                f"{skill_path}: name must be a non-empty string"
            )

        capabilities = require_unique_string_list(
            skill_path,
            skill.get("provides"),
            "provides",
        )

        for capability in capabilities:
            provided_by.setdefault(
                capability,
                [],
            ).append(skill_name.strip())

    return provided_by


def main() -> int:
    try:
        required_by = collect_runtime_requirements()
        provided_by = collect_skill_providers()
    except ValidationError as exc:
        print(f"FAIL: {exc}")
        return 1

    required_capabilities = set(required_by)
    provided_capabilities = set(provided_by)

    missing_skill_coverage = sorted(
        required_capabilities - provided_capabilities
    )
    unused_skill_capabilities = sorted(
        provided_capabilities - required_capabilities
    )
    duplicate_skill_capabilities = {
        capability: providers
        for capability, providers in provided_by.items()
        if len(providers) > 1
    }

    print(
        "Required runtime capabilities: "
        f"{len(required_capabilities)}"
    )
    print(
        f"Skill capabilities: {len(provided_capabilities)}"
    )
    print()

    print("Missing skill coverage:")
    if missing_skill_coverage:
        for capability in missing_skill_coverage:
            consumers = ", ".join(required_by[capability])
            print(
                f"  - {capability} required by bindings: "
                f"{consumers}"
            )
    else:
        print("  none")

    print()
    print("Unused skill capabilities:")
    if unused_skill_capabilities:
        for capability in unused_skill_capabilities:
            providers = ", ".join(provided_by[capability])
            print(
                f"  - {capability} provided by skills: "
                f"{providers}"
            )
    else:
        print("  none")

    print()
    print("Duplicate skill capabilities:")
    if duplicate_skill_capabilities:
        for capability, providers in sorted(
            duplicate_skill_capabilities.items()
        ):
            print(
                f"  - {capability}: {', '.join(providers)}"
            )
    else:
        print("  none")

    if (
        missing_skill_coverage
        or unused_skill_capabilities
        or duplicate_skill_capabilities
    ):
        return 1

    print()
    print(
        "PASS: Runtime capability coverage is complete. "
        f"Checked {len(required_capabilities)} required "
        "capability/capabilities."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
