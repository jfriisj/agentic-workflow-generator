import os
import subprocess
import sys
from pathlib import Path

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


def run_launcher(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_workflow_generator.cli.permission_profiles",
        ],
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_launcher_preserves_success_contract(
    tmp_path: Path,
) -> None:
    create_repository(tmp_path)

    result = run_launcher(tmp_path)

    assert result.returncode == 0
    assert result.stdout == (
        "PASS: Permission profile registry is valid. "
        "Checked 1 permission profile file(s).\n"
    )


def test_launcher_renders_structured_failure(
    tmp_path: Path,
) -> None:
    create_repository(
        tmp_path,
        profile_name="wrong-name",
    )

    result = run_launcher(tmp_path)

    assert result.returncode == 1
    assert "[AWG-PERMISSION-005]" in result.stdout
    assert ("name 'wrong-name' does not match folder 'read-only'") in result.stdout
