from __future__ import annotations

import shutil
from pathlib import Path

from agentic_workflow_generator.application.target_materialization import (
    materialize_targets,
)
from agentic_workflow_generator.application.target_output_validation import (
    CONTENT_DRIFT_DIAGNOSTIC,
    MANIFEST_DRIFT_DIAGNOSTIC,
    MISSING_FILE_DIAGNOSTIC,
    OBSOLETE_OUTPUT_DIAGNOSTIC,
    UNMANAGED_FILE_DIAGNOSTIC,
    validate_target_output,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> ProjectPaths:
    agentic_root = tmp_path / ".agentic"
    agentic_root.mkdir()

    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        agentic_root / "schemas",
    )
    shutil.copy2(
        REPOSITORY_ROOT / ".agentic" / "agentic.json",
        agentic_root / "agentic.json",
    )
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        tmp_path / "registry",
    )

    return ProjectPaths(tmp_path.resolve())


def diagnostic_codes(
    paths: ProjectPaths,
) -> set[str]:
    return {
        diagnostic.code
        for diagnostic in validate_target_output(paths)
    }


def test_materialized_output_is_canonical(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)

    materialize_targets(paths)

    assert validate_target_output(paths) == ()


def test_missing_generated_file_is_detected(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    materialize_targets(paths)
    generated = paths.repository_path(
        ".opencode/agents/requirements-worker.md"
    )
    generated.unlink()

    assert MISSING_FILE_DIAGNOSTIC in diagnostic_codes(
        paths
    )


def test_generated_content_drift_is_detected(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    materialize_targets(paths)
    generated = paths.repository_path(
        ".github/agents/requirements-worker.agent.md"
    )
    generated.write_bytes(b"drift")

    assert CONTENT_DRIFT_DIAGNOSTIC in diagnostic_codes(
        paths
    )


def test_unmanaged_owned_file_is_detected(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    materialize_targets(paths)
    stale = paths.repository_path(
        ".opencode/agents/unmanaged.md"
    )
    stale.write_bytes(b"unmanaged")

    assert UNMANAGED_FILE_DIAGNOSTIC in diagnostic_codes(
        paths
    )


def test_manifest_drift_is_detected(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    materialize_targets(paths)
    paths.manifest.write_bytes(b"drift")

    assert MANIFEST_DRIFT_DIAGNOSTIC in diagnostic_codes(
        paths
    )


def test_obsolete_resolution_output_is_rejected(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    materialize_targets(paths)
    resolution = (
        paths.generated_root / "resolution.json"
    )
    resolution.write_bytes(b"{}")

    assert OBSOLETE_OUTPUT_DIAGNOSTIC in diagnostic_codes(
        paths
    )
