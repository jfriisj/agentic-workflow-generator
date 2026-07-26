import os
import tempfile
from pathlib import Path
from typing import NoReturn

import pytest

from agentic_workflow_generator.infrastructure import (
    AtomicWriteError,
    atomic_write_bytes,
    atomic_write_text,
)


def test_atomic_write_bytes_creates_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "output.bin"

    atomic_write_bytes(target, b"content")

    assert target.read_bytes() == b"content"
    assert list(tmp_path.glob(".output.bin.*.tmp")) == []


def test_atomic_write_bytes_replaces_existing_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "output.bin"
    target.write_bytes(b"old")

    atomic_write_bytes(target, b"new")

    assert target.read_bytes() == b"new"


def test_atomic_write_text_uses_requested_encoding(
    tmp_path: Path,
) -> None:
    target = tmp_path / "output.txt"

    atomic_write_text(
        target,
        "æøå",
        encoding="utf-8",
    )

    assert target.read_bytes() == "æøå".encode()


def test_atomic_write_rejects_missing_parent(
    tmp_path: Path,
) -> None:
    target = tmp_path / "missing" / "output.json"

    with pytest.raises(
        AtomicWriteError,
        match="parent directory does not exist",
    ) as captured:
        atomic_write_bytes(target, b"content")

    assert captured.value.path == target


def test_atomic_write_wraps_temporary_file_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "output.json"

    def fail_mkstemp(
        *args: object,
        **kwargs: object,
    ) -> NoReturn:
        raise OSError("temporary file unavailable")

    monkeypatch.setattr(
        tempfile,
        "mkstemp",
        fail_mkstemp,
    )

    with pytest.raises(
        AtomicWriteError,
        match="temporary file unavailable",
    ):
        atomic_write_bytes(target, b"content")


def test_atomic_write_removes_temporary_file_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "output.json"

    def fail_replace(
        *args: object,
        **kwargs: object,
    ) -> NoReturn:
        raise OSError("replace unavailable")

    monkeypatch.setattr(
        os,
        "replace",
        fail_replace,
    )

    with pytest.raises(
        AtomicWriteError,
        match="replace unavailable",
    ):
        atomic_write_bytes(target, b"content")

    assert list(tmp_path.glob(".output.json.*.tmp")) == []


def test_atomic_write_handles_removed_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "output.json"

    def remove_then_fail_replace(
        source: Path,
        destination: Path,
    ) -> NoReturn:
        del destination
        os.unlink(source)
        raise OSError("replace failed after removal")

    monkeypatch.setattr(
        os,
        "replace",
        remove_then_fail_replace,
    )

    with pytest.raises(
        AtomicWriteError,
        match="replace failed after removal",
    ):
        atomic_write_bytes(target, b"content")

    assert list(tmp_path.glob(".output.json.*.tmp")) == []


def test_atomic_write_reports_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "output.json"
    original_unlink = Path.unlink

    def fail_replace(
        *args: object,
        **kwargs: object,
    ) -> NoReturn:
        raise OSError("replace unavailable")

    def fail_unlink(
        self: Path,
        missing_ok: bool = False,
    ) -> NoReturn:
        del self, missing_ok
        raise OSError("cleanup unavailable")

    monkeypatch.setattr(
        os,
        "replace",
        fail_replace,
    )
    monkeypatch.setattr(
        Path,
        "unlink",
        fail_unlink,
    )

    with pytest.raises(
        AtomicWriteError,
        match=("temporary-file cleanup also failed: cleanup unavailable"),
    ):
        atomic_write_bytes(target, b"content")

    temporary_files = list(tmp_path.glob(".output.json.*.tmp"))
    assert len(temporary_files) == 1

    original_unlink(temporary_files[0])
