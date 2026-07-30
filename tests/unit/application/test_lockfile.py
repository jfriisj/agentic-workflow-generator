from __future__ import annotations

from pathlib import Path

from agentic_workflow_generator.application.lockfile import (
    CONTENT_HASH_DRIFT_DIAGNOSTIC,
    FILE_COUNT_DRIFT_DIAGNOSTIC,
    HASH_DRIFT_DIAGNOSTIC,
    LOCK_PATTERNS,
    MISSING_INPUT_DIAGNOSTIC,
    SHAPE_DIAGNOSTIC,
    SIZE_DRIFT_DIAGNOSTIC,
    build_lockfile_document,
    collect_lockfile_inputs,
    generate_lockfile,
    validate_lockfile,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
    write_json,
)
from agentic_workflow_generator.registry import ProjectPaths
from tests.support.lockfile_repository import (
    build_lockfile_repository,
)


def diagnostic_codes(
    paths: ProjectPaths,
) -> set[str]:
    return {diagnostic.code for diagnostic in validate_lockfile(paths)}


def test_build_lockfile_document_is_deterministic(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)

    first = build_lockfile_document(paths)
    second = build_lockfile_document(paths)

    assert first == second
    inputs = first["inputs"]
    assert isinstance(inputs, dict)
    assert inputs["patterns"] == list(LOCK_PATTERNS)
    assert inputs["fileCount"] == 10


def test_collect_inputs_excludes_cache_and_lockfile(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    cache = (
        tmp_path / "src" / "agentic_workflow_generator" / "__pycache__" / "example.py"
    )
    cache.parent.mkdir()
    cache.write_text("ignored\n", encoding="utf-8")
    paths.lockfile.parent.mkdir(parents=True, exist_ok=True)
    paths.lockfile.write_text("{}\n", encoding="utf-8")

    records = collect_lockfile_inputs(paths)
    record_paths = {record.path for record in records}

    assert paths.lockfile.relative_to(paths.root).as_posix() not in record_paths
    assert not any("__pycache__" in path for path in record_paths)


def test_generate_and_validate_canonical_lockfile(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)

    result = generate_lockfile(paths)

    assert result.input_file_count == 10
    assert result.content_hash.startswith("sha256:")
    assert read_json_object(paths.lockfile) == build_lockfile_document(paths)
    assert validate_lockfile(paths) == ()


def test_validation_reports_hash_drift(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    changed = tmp_path / "registry" / "bundles" / "example.bundle.json"
    changed.write_text("[]\n", encoding="utf-8")

    codes = diagnostic_codes(paths)

    assert HASH_DRIFT_DIAGNOSTIC in codes
    assert CONTENT_HASH_DRIFT_DIAGNOSTIC in codes


def test_validation_reports_new_input(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    new_input = tmp_path / "registry" / "bundles" / "new.bundle.json"
    new_input.write_text("{}\n", encoding="utf-8")

    codes = diagnostic_codes(paths)

    assert MISSING_INPUT_DIAGNOSTIC in codes
    assert FILE_COUNT_DRIFT_DIAGNOSTIC in codes
    assert CONTENT_HASH_DRIFT_DIAGNOSTIC in codes


def test_validation_reports_missing_input_record(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    lockfile = read_json_object(paths.lockfile)
    inputs = lockfile["inputs"]
    assert isinstance(inputs, dict)
    files = inputs["files"]
    assert isinstance(files, list)
    files.pop()
    inputs["fileCount"] = len(files)
    write_json(paths.lockfile, lockfile)

    assert MISSING_INPUT_DIAGNOSTIC in diagnostic_codes(paths)


def test_validation_reports_record_hash_drift(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    lockfile = read_json_object(paths.lockfile)
    inputs = lockfile["inputs"]
    assert isinstance(inputs, dict)
    files = inputs["files"]
    assert isinstance(files, list)
    first = files[0]
    assert isinstance(first, dict)
    first["sha256"] = "sha256:" + "0" * 64
    write_json(paths.lockfile, lockfile)

    assert HASH_DRIFT_DIAGNOSTIC in diagnostic_codes(paths)


def test_validation_reports_record_size_drift(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    lockfile = read_json_object(paths.lockfile)
    inputs = lockfile["inputs"]
    assert isinstance(inputs, dict)
    files = inputs["files"]
    assert isinstance(files, list)
    first = files[0]
    assert isinstance(first, dict)
    size_bytes = first["sizeBytes"]
    assert isinstance(size_bytes, int)
    first["sizeBytes"] = size_bytes + 1
    write_json(paths.lockfile, lockfile)

    assert SIZE_DRIFT_DIAGNOSTIC in diagnostic_codes(paths)


def test_validation_reports_declared_file_count_drift(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    lockfile = read_json_object(paths.lockfile)
    inputs = lockfile["inputs"]
    assert isinstance(inputs, dict)
    file_count = inputs["fileCount"]
    assert isinstance(file_count, int)
    inputs["fileCount"] = file_count + 1
    write_json(paths.lockfile, lockfile)

    assert FILE_COUNT_DRIFT_DIAGNOSTIC in diagnostic_codes(paths)


def test_validation_reports_declared_content_hash_drift(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    lockfile = read_json_object(paths.lockfile)
    inputs = lockfile["inputs"]
    assert isinstance(inputs, dict)
    inputs["contentHash"] = "sha256:" + "0" * 64
    write_json(paths.lockfile, lockfile)

    assert CONTENT_HASH_DRIFT_DIAGNOSTIC in diagnostic_codes(paths)


def test_validation_rejects_empty_tracked_files(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    generate_lockfile(paths)
    lockfile = read_json_object(paths.lockfile)
    inputs = lockfile["inputs"]
    assert isinstance(inputs, dict)
    inputs["files"] = []
    write_json(paths.lockfile, lockfile)

    assert SHAPE_DIAGNOSTIC in diagnostic_codes(paths)


def test_validation_rejects_invalid_shape(
    tmp_path: Path,
) -> None:
    paths = build_lockfile_repository(tmp_path)
    write_json(
        paths.lockfile,
        {
            "lockfileVersion": 0,
        },
    )

    assert SHAPE_DIAGNOSTIC in diagnostic_codes(paths)
