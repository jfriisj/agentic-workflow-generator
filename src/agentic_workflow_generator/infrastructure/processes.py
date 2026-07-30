"""Typed process-execution infrastructure adapters."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import ProcessExecutionError


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Immutable result from one completed external process."""

    executable: str
    arguments: tuple[str, ...]
    exit_code: int
    output: str


def resolve_executable(
    command: str,
    *,
    path: str | None = None,
) -> str | None:
    """Resolve one executable through an explicit PATH value."""

    return shutil.which(
        command,
        path=path,
    )


def run_process(
    executable: str,
    arguments: tuple[str, ...],
    *,
    cwd: Path,
    timeout_seconds: float | None = None,
) -> ProcessResult:
    """Run one resolved executable and capture combined output."""

    command = [
        executable,
        *arguments,
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout_seconds,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        raise ProcessExecutionError(
            executable,
            arguments,
            reason=str(exc),
        ) from exc

    return ProcessResult(
        executable=executable,
        arguments=arguments,
        exit_code=completed.returncode,
        output=completed.stdout.strip(),
    )
