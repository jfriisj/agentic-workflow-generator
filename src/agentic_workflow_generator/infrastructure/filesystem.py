"""Fail-fast atomic filesystem writes."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from .errors import (
    AtomicWriteError,
    TransactionRollbackError,
)


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



def transactional_write_bytes(
    contents: Mapping[Path, bytes],
) -> None:
    """Atomically replace several files with fail-fast rollback."""

    if not contents:
        raise ValueError(
            "Transactional write requires at least one file"
        )

    ordered_items = tuple(contents.items())
    resolved_paths = tuple(
        path.resolve(strict=False)
        for path, _content in ordered_items
    )

    if len(set(resolved_paths)) != len(resolved_paths):
        raise ValueError(
            "Transactional write paths must be unique"
        )

    previous: dict[Path, bytes | None] = {}

    for path, _content in ordered_items:
        if not path.parent.is_dir():
            raise AtomicWriteError(
                path,
                "parent directory does not exist",
            )

        try:
            previous[path] = (
                path.read_bytes()
                if path.is_file()
                else None
            )
        except OSError as exc:
            raise AtomicWriteError(
                path,
                f"could not snapshot existing file: {exc}",
            ) from exc

    try:
        for path, content in ordered_items:
            atomic_write_bytes(path, content)
    except Exception as exc:
        restoration_errors: list[str] = []

        for path, previous_content in previous.items():
            try:
                if previous_content is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write_bytes(
                        path,
                        previous_content,
                    )
            except Exception as restoration_exc:
                restoration_errors.append(
                    f"{path}: {restoration_exc}"
                )

        if restoration_errors:
            raise TransactionRollbackError(
                exc,
                tuple(restoration_errors),
            ) from exc

        raise
