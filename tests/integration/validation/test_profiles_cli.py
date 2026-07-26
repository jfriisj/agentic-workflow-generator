import os
import subprocess
import sys
from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    write_json,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
LAUNCHER = REPOSITORY_ROOT / "scripts" / "agentic" / "validate-profile-registry.py"
SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "profile.schema.json"
)


def create_repository(
    root: Path,
    *,
    recommended_workflow: str = "lean-delivery",
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "profile.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    registry_directories = (
        root / "registry" / "profiles",
        root / "registry" / "workflows",
        root / "registry" / "agents" / "Implementer",
        root / "registry" / "skills" / "implementation",
    )

    for directory in registry_directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    profile: JsonObject = {
        "name": "lean-delivery",
        "version": "0.2.0",
        "description": "Advisory delivery defaults.",
        "recommendedWorkflow": recommended_workflow,
        "recommendedAgents": [
            "Implementer",
        ],
        "recommendedCapabilities": [
            "implementation.code",
        ],
        "recommendedLanguageProfiles": [
            "language-agnostic",
        ],
        "recommendedRuntimeProfiles": [
            "local",
        ],
    }
    write_json(
        root / "registry" / "profiles" / "lean-delivery.profile.json",
        profile,
    )

    write_json(
        root / "registry" / "workflows" / "lean-delivery.workflow.json",
        {
            "name": "lean-delivery",
        },
    )

    write_json(
        root / "registry" / "agents" / "Implementer" / "agent.json",
        {
            "name": "Implementer",
        },
    )

    write_json(
        root / "registry" / "skills" / "implementation" / "skill.json",
        {
            "name": "implementation",
            "provides": [
                "implementation.code",
            ],
        },
    )


def run_launcher(
    root: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")

    return subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
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
        "PASS: Profile registry is valid. "
        "Checked 1 profile file(s), "
        "1 recommended agent reference(s), and "
        "1 recommended capability reference(s).\n"
    )


def test_launcher_renders_structured_failure(
    tmp_path: Path,
) -> None:
    create_repository(
        tmp_path,
        recommended_workflow="does-not-exist",
    )

    result = run_launcher(tmp_path)

    assert result.returncode == 1
    assert "[AWG-PROFILE-005]" in result.stdout
    assert (
        "recommendedWorkflow 'does-not-exist' must reference an existing workflow"
    ) in result.stdout
