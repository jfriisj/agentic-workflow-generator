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


def test_transactional_write_bytes_updates_all_files(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_bytes(b"old-first")

    from agentic_workflow_generator.infrastructure import (
        transactional_write_bytes,
    )

    transactional_write_bytes(
        {
            first: b"new-first",
            second: b"new-second",
        }
    )

    assert first.read_bytes() == b"new-first"
    assert second.read_bytes() == b"new-second"


def test_transactional_write_bytes_restores_all_files_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_bytes(b"old-first")
    second.write_bytes(b"old-second")

    import agentic_workflow_generator.infrastructure.filesystem as filesystem_module
    from agentic_workflow_generator.infrastructure import (
        AtomicWriteError,
        transactional_write_bytes,
    )

    original_write = filesystem_module.atomic_write_bytes
    calls = 0

    def fail_second_write(
        path: Path,
        content: bytes,
    ) -> None:
        nonlocal calls
        calls += 1

        if calls == 2:
            raise AtomicWriteError(
                path,
                "injected failure",
            )

        original_write(path, content)

    monkeypatch.setattr(
        filesystem_module,
        "atomic_write_bytes",
        fail_second_write,
    )

    with pytest.raises(
        AtomicWriteError,
        match="injected failure",
    ):
        transactional_write_bytes(
            {
                first: b"new-first",
                second: b"new-second",
            }
        )

    assert first.read_bytes() == b"old-first"
    assert second.read_bytes() == b"old-second"


def test_transactional_write_bytes_removes_new_file_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = tmp_path / "created.json"
    failing = tmp_path / "failing.json"

    import agentic_workflow_generator.infrastructure.filesystem as filesystem_module
    from agentic_workflow_generator.infrastructure import (
        AtomicWriteError,
        transactional_write_bytes,
    )

    original_write = filesystem_module.atomic_write_bytes
    calls = 0

    def fail_second_write(
        path: Path,
        content: bytes,
    ) -> None:
        nonlocal calls
        calls += 1

        if calls == 2:
            raise AtomicWriteError(
                path,
                "injected failure",
            )

        original_write(path, content)

    monkeypatch.setattr(
        filesystem_module,
        "atomic_write_bytes",
        fail_second_write,
    )

    with pytest.raises(AtomicWriteError):
        transactional_write_bytes(
            {
                created: b"created",
                failing: b"never-written",
            }
        )

    assert not created.exists()
    assert not failing.exists()


def test_transactional_write_bytes_rejects_empty_transaction() -> None:
    from agentic_workflow_generator.infrastructure import (
        transactional_write_bytes,
    )

    with pytest.raises(
        ValueError,
        match="at least one file",
    ):
        transactional_write_bytes({})


def test_transactional_write_reports_rollback_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_bytes(b"old-first")
    second.write_bytes(b"old-second")

    import agentic_workflow_generator.infrastructure.filesystem as filesystem_module
    from agentic_workflow_generator.infrastructure import (
        AtomicWriteError,
        TransactionRollbackError,
        transactional_write_bytes,
    )

    original_write = filesystem_module.atomic_write_bytes
    calls = 0

    def fail_write_and_restore(
        path: Path,
        content: bytes,
    ) -> None:
        nonlocal calls
        calls += 1

        if calls >= 2:
            raise AtomicWriteError(
                path,
                "injected failure",
            )

        original_write(path, content)

    monkeypatch.setattr(
        filesystem_module,
        "atomic_write_bytes",
        fail_write_and_restore,
    )

    with pytest.raises(
        TransactionRollbackError,
        match="additionally failed to restore",
    ) as captured:
        transactional_write_bytes(
            {
                first: b"new-first",
                second: b"new-second",
            }
        )

    assert captured.value.restoration_errors


def test_transactional_write_rejects_resolved_duplicate_paths(
    tmp_path: Path,
) -> None:
    from agentic_workflow_generator.infrastructure import (
        transactional_write_bytes,
    )

    with pytest.raises(
        ValueError,
        match="paths must be unique",
    ):
        transactional_write_bytes(
            {
                tmp_path / "output.json": b"first",
                tmp_path
                / "missing-directory"
                / ".."
                / "output.json": b"second",
            }
        )


def test_transactional_write_rejects_missing_parent(
    tmp_path: Path,
) -> None:
    from agentic_workflow_generator.infrastructure import (
        AtomicWriteError,
        transactional_write_bytes,
    )

    target = tmp_path / "missing" / "output.json"

    with pytest.raises(
        AtomicWriteError,
        match="parent directory does not exist",
    ):
        transactional_write_bytes(
            {
                target: b"content",
            }
        )


def test_transactional_write_wraps_snapshot_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentic_workflow_generator.infrastructure import (
        AtomicWriteError,
        transactional_write_bytes,
    )

    target = tmp_path / "output.json"
    target.write_bytes(b"old")
    original_read_bytes = Path.read_bytes

    def fail_target_snapshot(self: Path) -> bytes:
        if self == target:
            raise OSError("snapshot unavailable")

        return original_read_bytes(self)

    monkeypatch.setattr(
        Path,
        "read_bytes",
        fail_target_snapshot,
    )

    with pytest.raises(
        AtomicWriteError,
        match="could not snapshot existing file",
    ):
        transactional_write_bytes(
            {
                target: b"new",
            }
        )
