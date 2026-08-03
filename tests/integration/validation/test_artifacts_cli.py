import os
import subprocess
import sys
from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
    write_json,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.artifacts import (
    validate_artifact_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_SOURCE = (
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "artifact.schema.json"
)
SCHEMA = read_json_object(SCHEMA_SOURCE)


def create_repository(
    root: Path,
    *,
    artifact_type: str = "Requirements",
) -> None:
    schema_target = root / ".agentic" / "schemas" / "registry" / "artifact.schema.json"
    schema_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    schema_target.write_text(
        SCHEMA_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    artifact: JsonObject = {
        "type": artifact_type,
        "version": "0.5.0",
        "description": "Requirements contract.",
        "pathPattern": "agent-output/requirements/*.md",
        "status": {
            "heading": "## Status",
            "pattern": "PASS|FAIL|BLOCKED",
        },
        "provenance": {
            "heading": "## Provenance",
            "requiredIdentities": [
                "artifactType",
                "artifactVersion",
                "workflow",
                "workflowVersion",
                "roleBinding",
                "agentInstance",
            ],
        },
        "revision": {
            "heading": "## Revision",
            "pattern": "^[1-9][0-9]*$",
        },
        "statusInvariants": {
            "passRequiresCompleteEvidence": True,
            "passForbidsDemonstratedNonconformance": True,
            "failRequiresDemonstratedNonconformance": True,
            "blockedRequiresUnavailablePrerequisite": True,
        },
        "allowedStatuses": [
            "PASS",
            "FAIL",
            "BLOCKED",
        ],
        "requiredHeadings": [
            "# Requirements",
            "## Status",
            "## Provenance",
            "## Revision",
            "## Summary",
        ],
    }
    artifact_path = root / "registry" / "artifacts" / "Requirements" / "artifact.json"
    artifact_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_json(artifact_path, artifact)

    source = RegistrySource(
        kind=RegistryKind.ARTIFACT,
        source_path=Path("registry/artifacts/Requirements/artifact.json"),
        data=artifact,
    )
    projection = validate_artifact_registry(
        (source,),
        SCHEMA,
        (),
    ).schema_projections[0]
    artifact_path.with_name("artifact.schema.json").write_text(
        projection.canonical_json,
        encoding="utf-8",
    )


def run_launcher(
    root: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_workflow_generator.cli.artifacts",
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
        "PASS: Artifact contracts are valid. Checked 1 artifact file(s).\n"
    )


def test_launcher_renders_structured_failure(
    tmp_path: Path,
) -> None:
    create_repository(
        tmp_path,
        artifact_type="DifferentType",
    )

    result = run_launcher(tmp_path)

    assert result.returncode == 1
    assert "[AWG-ARTIFACT-003]" in result.stdout
    assert (
        "type 'DifferentType' does not match folder 'Requirements'"
    ) in result.stdout
