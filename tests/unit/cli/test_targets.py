from pathlib import Path

import pytest

from agentic_workflow_generator.cli.targets import main
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
TARGET_SCHEMA_SOURCE = (
    REPOSITORY_ROOT
    / ".agentic"
    / "schemas"
    / "registry"
    / "target-adapter.schema.json"
)
PERMISSION_SCHEMA_SOURCE = (
    REPOSITORY_ROOT
    / ".agentic"
    / "schemas"
    / "registry"
    / "permission-profile.schema.json"
)


def create_repository(
    root: Path,
    *,
    target_name: str = "opencode",
) -> None:
    schema_root = (
        root
        / ".agentic"
        / "schemas"
        / "registry"
    )
    schema_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    (
        schema_root
        / "target-adapter.schema.json"
    ).write_text(
        TARGET_SCHEMA_SOURCE.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (
        schema_root
        / "permission-profile.schema.json"
    ).write_text(
        PERMISSION_SCHEMA_SOURCE.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    permission_profiles: dict[str, JsonObject] = {
        "read-only": {
            "read": True,
            "write": False,
            "edit": False,
            "bash": "deny",
        },
        "implementation": {
            "read": True,
            "write": True,
            "edit": True,
            "bash": "allow",
        },
        "test-runner": {
            "read": True,
            "write": False,
            "edit": False,
            "bash": "limited",
        },
    }

    for name, values in permission_profiles.items():
        profile: JsonObject = {
            "name": name,
            "version": "0.1.0",
            "description": f"{name} permissions.",
            **values,
        }
        profile_path = (
            root
            / "registry"
            / "permission-profiles"
            / name
            / "permission-profile.json"
        )
        profile_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        write_json(profile_path, profile)

    target: JsonObject = {
        "name": target_name,
        "version": "0.1.0",
        "description": "OpenCode target adapter.",
        "outputPaths": {
            "agents": ".opencode/agents",
            "instructions": "AGENTS.md",
        },
        "ownedPaths": [
            ".opencode/agents",
            "AGENTS.md",
        ],
        "permissionMapping": {
            "read-only": {
                "bash": "deny",
            },
            "implementation": {
                "bash": "allow",
            },
            "test-runner": {
                "bash": "allow",
            },
        },
    }
    target_path = (
        root
        / "registry"
        / "targets"
        / "opencode"
        / "adapter.json"
    )
    target_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(target_path, target)


def test_main_returns_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main()

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Target adapter registry is valid. "
        "Checked 1 target adapter file(s) against "
        "3 permission profile(s).\n"
    )


def test_main_renders_target_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        target_name="wrong-name",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert (
        "FAIL: Target adapter registry validation "
        "found 1 error(s)."
    ) in output
    assert "[AWG-TARGET-003]" in output
    assert (
        "registry/targets/opencode/adapter.json name"
    ) in output


def test_main_renders_registry_boundary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert "[AWG-TARGET-900]" in output
    assert "required registry root not found" in output
