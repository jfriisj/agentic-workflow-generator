"""Fail-fast atomic filesystem writes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .errors import AtomicWriteError


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Atomically replace one file with the supplied bytes."""

    parent = path.parent

    if not parent.is_dir():
        raise AtomicWriteError(
            path,
            "parent directory does not exist",
        )

    temporary_path: Path | None = None

    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as exc:
        cleanup_detail = ""

        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError as cleanup_exc:
                cleanup_detail = f"; temporary-file cleanup also failed: {cleanup_exc}"

        raise AtomicWriteError(
            path,
            f"atomic write failed: {exc}{cleanup_detail}",
        ) from exc


def atomic_write_text(
    path: Path,
    content: str,
    *,
    encoding: str = "utf-8",
) -> None:
    """Atomically replace one text file."""

    atomic_write_bytes(path, content.encode(encoding))
