from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agentic_workflow_generator.application.generation_idempotency import (
    GenerationSnapshotError,
    validate_generation_idempotency,
)
from agentic_workflow_generator.application.lockfile import (
    generate_lockfile,
)
from agentic_workflow_generator.application.target_materialization import (
    materialize_targets,
)
from agentic_workflow_generator.registry import ProjectPaths
from agentic_workflow_generator.validation.generation_idempotency import (
    CHANGED_AFTER_DIAGNOSTIC,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def copy_repository(
    tmp_path: Path,
) -> ProjectPaths:
    shutil.copytree(
        REPOSITORY_ROOT,
        tmp_path,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
        ),
    )
    return ProjectPaths(tmp_path.resolve())


def establish_canonical_generation(
    paths: ProjectPaths,
) -> None:
    generate_lockfile(paths)
    materialize_targets(paths)


def test_real_generation_is_idempotent(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    establish_canonical_generation(paths)

    analysis = validate_generation_idempotency(paths)

    assert analysis.result.is_idempotent
    assert analysis.result.checked_file_count == 55
    assert analysis.generation.generated_target_count == 2
    assert analysis.generation.generated_file_count == 53


def test_compiler_input_change_is_detected(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    establish_canonical_generation(paths)
    renderer = (
        paths.root
        / "src"
        / "agentic_workflow_generator"
        / "application"
        / "target_rendering.py"
    )
    renderer.write_text(
        renderer.read_text(encoding="utf-8")
        + "\n# focused idempotency drift marker\n",
        encoding="utf-8",
    )

    analysis = validate_generation_idempotency(paths)

    assert not analysis.result.is_idempotent
    assert analysis.result.changed_after == (
        ".agentic/agentic-lock.json",
    )
    assert tuple(
        diagnostic.code
        for diagnostic in analysis.result.diagnostics
    ) == (CHANGED_AFTER_DIAGNOSTIC,)

def test_missing_baseline_manifest_preserves_snapshot_phase(
    tmp_path: Path,
) -> None:
    paths = copy_repository(tmp_path)
    establish_canonical_generation(paths)
    paths.manifest.unlink()

    with pytest.raises(
        GenerationSnapshotError,
        match=r"output-manifest\.json",
    ) as error:
        validate_generation_idempotency(paths)

    assert error.value.phase == "baseline"
