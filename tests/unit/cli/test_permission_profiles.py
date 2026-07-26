from pathlib import Path

import pytest

from agentic_workflow_generator.cli.permission_profiles import (
    main,
)
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_SOURCE = (
    REPOSITORY_ROOT
    / ".agentic"
    / "schemas"
    / "registry"
    / "permission-profile.schema.json"
)


def create_repository(
    root: Path,
    *,
    profile_name: str = "read-only",
) -> None:
    schema_target = (
        root / ".agentic" / "schemas" / "registry" / "permission-profile.schema.json"
    )
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    profile: JsonObject = {
        "name": profile_name,
        "version": "0.1.0",
        "description": "Read-only access.",
        "read": True,
        "write": False,
        "edit": False,
        "bash": "deny",
    }
    profile_path = (
        root
        / "registry"
        / "permission-profiles"
        / "read-only"
        / "permission-profile.json"
    )
    profile_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(profile_path, profile)


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
        "PASS: Permission profile registry is valid. "
        "Checked 1 permission profile file(s).\n"
    )


def test_main_renders_semantic_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_repository(
        tmp_path,
        profile_name="wrong-name",
    )
    monkeypatch.chdir(tmp_path)

    result = main()

    output = capsys.readouterr().out
    assert result == 1
    assert ("FAIL: Permission profile registry validation found 1 error(s).") in output
    assert "[AWG-PERMISSION-005]" in output
    assert (
        "registry/permission-profiles/read-only/permission-profile.json name"
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
    assert "[AWG-PERMISSION-900]" in output
    assert "required registry root not found" in output
