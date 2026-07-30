from agentic_workflow_generator.validation.generation_idempotency import (
    ADDED_AFTER_DIAGNOSTIC,
    CHANGED_AFTER_DIAGNOSTIC,
    MISSING_AFTER_DIAGNOSTIC,
    GenerationSnapshot,
    GenerationSnapshotFile,
    compare_generation_snapshots,
)


def snapshot(
    *files: tuple[str, str],
) -> GenerationSnapshot:
    return GenerationSnapshot(
        files=tuple(
            GenerationSnapshotFile(
                path=path,
                sha256=sha256,
            )
            for path, sha256 in files
        )
    )


def test_equal_snapshots_are_idempotent() -> None:
    before = snapshot(
        ("a.txt", "aaa"),
        ("b.txt", "bbb"),
    )

    result = compare_generation_snapshots(
        before,
        before,
    )

    assert result.is_idempotent
    assert result.checked_file_count == 2
    assert result.diagnostics == ()


def test_snapshot_drift_is_sorted_and_typed() -> None:
    result = compare_generation_snapshots(
        snapshot(
            ("missing.txt", "111"),
            ("changed.txt", "222"),
        ),
        snapshot(
            ("added.txt", "333"),
            ("changed.txt", "444"),
        ),
    )

    assert not result.is_idempotent
    assert result.missing_after == ("missing.txt",)
    assert result.added_after == ("added.txt",)
    assert result.changed_after == ("changed.txt",)
    assert tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
    ) == (
        MISSING_AFTER_DIAGNOSTIC,
        ADDED_AFTER_DIAGNOSTIC,
        CHANGED_AFTER_DIAGNOSTIC,
    )
    assert tuple(
        diagnostic.source_path
        for diagnostic in result.diagnostics
    ) == (
        "missing.txt",
        "added.txt",
        "changed.txt",
    )
