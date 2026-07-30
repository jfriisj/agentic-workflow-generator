from __future__ import annotations

from pathlib import Path

import pytest

import agentic_workflow_generator.cli.generation_idempotency as command
from agentic_workflow_generator.application.generation_idempotency import (
    GenerationIdempotencyAnalysis,
    GenerationIdempotencyValidationError,
    GenerationRunSummary,
    GenerationSnapshotError,
)
from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.validation.generation_idempotency import (
    GenerationIdempotencyResult,
    GenerationSnapshot,
    GenerationSnapshotFile,
)


def analysis(
    *,
    missing: tuple[str, ...] = (),
    added: tuple[str, ...] = (),
    changed: tuple[str, ...] = (),
) -> GenerationIdempotencyAnalysis:
    before = GenerationSnapshot(
        files=(
            GenerationSnapshotFile(
                path="before.txt",
                sha256="111",
            ),
        )
    )
    after = GenerationSnapshot(
        files=(
            GenerationSnapshotFile(
                path="after.txt",
                sha256="222",
            ),
        )
    )
    diagnostics = tuple(
        Diagnostic(
            code="AWG-GENERATION-IDEMPOTENCY-003",
            message="changed after generation",
            source_path=path,
        )
        for path in changed
    )

    return GenerationIdempotencyAnalysis(
        result=GenerationIdempotencyResult(
            before=before,
            after=after,
            missing_after=missing,
            added_after=added,
            changed_after=changed,
            diagnostics=diagnostics,
        ),
        generation=GenerationRunSummary(
            lockfile_input_count=1,
            generated_target_count=1,
            generated_file_count=1,
            removed_file_count=0,
        ),
    )


def test_cli_preserves_success_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        command,
        "validate_generation_idempotency",
        lambda paths: analysis(),
    )

    result = command.main([])

    assert result == 0
    assert capsys.readouterr().out == (
        "PASS: Generation is idempotent. Checked 1 file(s).\n"
    )


def test_cli_renders_drift_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        command,
        "validate_generation_idempotency",
        lambda paths: analysis(
            missing=("missing.txt",),
            added=("added.txt",),
            changed=("changed.txt",),
        ),
    )

    result = command.main([])

    assert result == 1
    assert capsys.readouterr().out == (
        "FAIL: Generation is not idempotent.\n"
        "  - missing after generation: missing.txt\n"
        "  - added after generation: added.txt\n"
        "  - changed after generation: changed.txt\n"
    )


def test_cli_renders_snapshot_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    def fail(paths: object) -> GenerationIdempotencyAnalysis:
        del paths
        raise GenerationSnapshotError(
            "baseline",
            "missing manifest",
        )

    monkeypatch.setattr(
        command,
        "validate_generation_idempotency",
        fail,
    )

    result = command.main([])

    assert result == 1
    assert capsys.readouterr().out == (
        "FAIL: Could not collect baseline idempotency snapshot: "
        "missing manifest\n"
    )


def test_cli_renders_typed_generation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    def fail(paths: object) -> GenerationIdempotencyAnalysis:
        del paths
        raise GenerationIdempotencyValidationError(
            "lockfile",
            (
                Diagnostic(
                    code="AWG-LOCKFILE-007",
                    message="hash drift",
                ),
            ),
        )

    monkeypatch.setattr(
        command,
        "validate_generation_idempotency",
        fail,
    )

    result = command.main([])

    assert result == 1
    assert capsys.readouterr().out == (
        "FAIL: idempotency generation run failed.\n"
        "  - [AWG-LOCKFILE-007] hash drift\n"
    )


def test_cli_renders_command_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    def fail(paths: object) -> GenerationIdempotencyAnalysis:
        del paths
        raise ValueError("broken command")

    monkeypatch.setattr(
        command,
        "validate_generation_idempotency",
        fail,
    )

    result = command.main([])

    assert result == 1
    assert capsys.readouterr().out == (
        "FAIL: idempotency generation run failed.\n"
        "  - [AWG-GENERATION-IDEMPOTENCY-900] broken command\n"
    )
