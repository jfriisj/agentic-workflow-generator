from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure.errors import (
    ProcessExecutionError,
)
from agentic_workflow_generator.infrastructure.processes import (
    resolve_executable,
    run_process,
)


def test_resolve_executable_uses_explicit_path(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "example"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    assert resolve_executable(
        "example",
        path=str(tmp_path),
    ) == str(executable)


def test_run_process_captures_output(
    tmp_path: Path,
) -> None:
    result = run_process(
        sys.executable,
        ("-c", "print('available')"),
        cwd=tmp_path,
    )

    assert result.exit_code == 0
    assert result.output == "available"


def test_run_process_preserves_nonzero_exit(
    tmp_path: Path,
) -> None:
    result = run_process(
        sys.executable,
        ("-c", "raise SystemExit(7)"),
        cwd=tmp_path,
    )

    assert result.exit_code == 7


def test_run_process_wraps_execution_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run(
        *args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise OSError("process unavailable")

    monkeypatch.setattr(
        subprocess,
        "run",
        fail_run,
    )

    with pytest.raises(
        ProcessExecutionError,
        match="process unavailable",
    ):
        run_process(
            "/missing",
            (),
            cwd=tmp_path,
        )


def test_run_process_wraps_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run(
        *args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise subprocess.TimeoutExpired(
            cmd=("example", "--version"),
            timeout=30,
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fail_run,
    )

    with pytest.raises(
        ProcessExecutionError,
        match="timed out",
    ):
        run_process(
            "/example",
            ("--version",),
            cwd=tmp_path,
            timeout_seconds=30,
        )
