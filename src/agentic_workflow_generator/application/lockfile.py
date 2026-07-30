"""Deterministic compiler-input lockfile generation and validation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
    read_json_object,
    sha256_file,
    write_json,
)
from agentic_workflow_generator.registry import ProjectPaths

LOCKFILE_VERSION = 1
GENERATOR_NAME = "agentic-gen"
GENERATOR_MODE = "local-mvp-lockfile"

LOCK_PATTERNS = (
    ".agentic/agentic.json",
    ".agentic/schemas/**/*.json",
    "pyproject.toml",
    "registry/**/*.json",
    "registry/**/SKILL.md",
    "scripts/agentic/*.py",
    "scripts/agentic/*.sh",
    "src/agentic_workflow_generator/**/*.py",
    "uv.lock",
)

_EXCLUDED_PARTS = frozenset(
    {
        "__pycache__",
        ".git",
    }
)
_EXCLUDED_SUFFIXES = frozenset(
    {
        ".pyc",
        ".pyo",
    }
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

SHAPE_DIAGNOSTIC = "AWG-LOCKFILE-001"
PATTERNS_DRIFT_DIAGNOSTIC = "AWG-LOCKFILE-002"
FILE_COUNT_DRIFT_DIAGNOSTIC = "AWG-LOCKFILE-003"
CONTENT_HASH_DRIFT_DIAGNOSTIC = "AWG-LOCKFILE-004"
MISSING_INPUT_DIAGNOSTIC = "AWG-LOCKFILE-005"
UNEXPECTED_INPUT_DIAGNOSTIC = "AWG-LOCKFILE-006"
HASH_DRIFT_DIAGNOSTIC = "AWG-LOCKFILE-007"
SIZE_DRIFT_DIAGNOSTIC = "AWG-LOCKFILE-008"


@dataclass(frozen=True, slots=True)
class LockfileInput:
    """One immutable compiler-input record."""

    path: str
    sha256: str
    size_bytes: int

    def to_json(self) -> JsonObject:
        """Serialize the input record deterministically."""

        return {
            "path": self.path,
            "sha256": self.sha256,
            "sizeBytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class LockfileGenerationResult:
    """Summary of one committed lockfile generation."""

    input_file_count: int
    content_hash: str


def collect_lockfile_inputs(
    paths: ProjectPaths,
) -> tuple[LockfileInput, ...]:
    """Collect and hash all declared compiler inputs."""

    matched_files: set[Path] = set()

    for pattern in LOCK_PATTERNS:
        for path in paths.root.glob(pattern):
            if _should_include(paths, path):
                matched_files.add(path)

    ordered_files = sorted(
        matched_files,
        key=lambda path: path.relative_to(paths.root).as_posix(),
    )

    if not ordered_files:
        raise ValueError(
            "No files matched lockfile input patterns."
        )

    return tuple(
        _build_input_record(paths, path)
        for path in ordered_files
    )


def build_lockfile_document(
    paths: ProjectPaths,
) -> JsonObject:
    """Build the canonical lockfile document."""

    records = collect_lockfile_inputs(paths)
    content_hash = _aggregate_content_hash(records)

    files_json: list[JsonValue] = [
        record.to_json()
        for record in records
    ]
    generator: JsonObject = {
        "name": GENERATOR_NAME,
        "mode": GENERATOR_MODE,
    }
    inputs: JsonObject = {
        "patterns": list(LOCK_PATTERNS),
        "fileCount": len(records),
        "contentHash": content_hash,
        "files": files_json,
    }

    return {
        "lockfileVersion": LOCKFILE_VERSION,
        "generator": generator,
        "inputs": inputs,
    }


def generate_lockfile(
    paths: ProjectPaths,
) -> LockfileGenerationResult:
    """Write the canonical compiler-input lockfile atomically."""

    document = build_lockfile_document(paths)
    inputs = document["inputs"]

    if not isinstance(inputs, dict):
        raise ValueError(
            "Canonical lockfile inputs must be an object"
        )

    file_count = inputs["fileCount"]
    content_hash = inputs["contentHash"]

    if not isinstance(file_count, int):
        raise ValueError(
            "Canonical lockfile fileCount must be an integer"
        )

    if not isinstance(content_hash, str):
        raise ValueError(
            "Canonical lockfile contentHash must be a string"
        )

    write_json(paths.lockfile, document)

    return LockfileGenerationResult(
        input_file_count=file_count,
        content_hash=content_hash,
    )


def validate_lockfile(
    paths: ProjectPaths,
) -> tuple[Diagnostic, ...]:
    """Validate lockfile shape and exact compiler-input provenance."""

    actual = read_json_object(paths.lockfile)
    expected = build_lockfile_document(paths)
    source_path = paths.lockfile.relative_to(
        paths.root
    ).as_posix()

    diagnostics = list(
        _validate_shape(
            actual,
            source_path,
        )
    )
    diagnostics.extend(
        _validate_drift(
            actual,
            expected,
            source_path,
        )
    )
    return tuple(diagnostics)


def _should_include(
    paths: ProjectPaths,
    path: Path,
) -> bool:
    relative = path.relative_to(paths.root)

    if any(
        part in _EXCLUDED_PARTS
        for part in relative.parts
    ):
        return False

    if path.suffix in _EXCLUDED_SUFFIXES:
        return False

    if path == paths.lockfile:
        return False

    return path.is_file()


def _build_input_record(
    paths: ProjectPaths,
    path: Path,
) -> LockfileInput:
    stat = path.stat()

    return LockfileInput(
        path=path.relative_to(paths.root).as_posix(),
        sha256=f"sha256:{sha256_file(path)}",
        size_bytes=stat.st_size,
    )


def _aggregate_content_hash(
    records: tuple[LockfileInput, ...],
) -> str:
    digest = hashlib.sha256()

    for record in records:
        digest.update(record.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(record.sha256.encode("utf-8"))
        digest.update(b"\0")

    return f"sha256:{digest.hexdigest()}"


def _validate_shape(
    lockfile: JsonObject,
    source_path: str,
) -> tuple[Diagnostic, ...]:
    errors: list[str] = []

    if lockfile.get("lockfileVersion") != LOCKFILE_VERSION:
        errors.append(
            f"lockfileVersion must be {LOCKFILE_VERSION}"
        )

    generator = lockfile.get("generator")

    if not isinstance(generator, dict):
        errors.append("generator must be an object")
    else:
        if generator.get("name") != GENERATOR_NAME:
            errors.append(
                f"generator.name must be {GENERATOR_NAME}"
            )

        if generator.get("mode") != GENERATOR_MODE:
            errors.append(
                f"generator.mode must be {GENERATOR_MODE}"
            )

    inputs = lockfile.get("inputs")

    if not isinstance(inputs, dict):
        errors.append("inputs must be an object")
        return _shape_diagnostics(
            errors,
            source_path,
        )

    patterns = inputs.get("patterns")

    if (
        not isinstance(patterns, list)
        or not patterns
        or not all(
            isinstance(pattern, str)
            and bool(pattern.strip())
            for pattern in patterns
        )
    ):
        errors.append(
            "inputs.patterns must be a non-empty list "
            "of non-empty strings"
        )

    file_count = inputs.get("fileCount")

    if (
        not isinstance(file_count, int)
        or isinstance(file_count, bool)
        or file_count <= 0
    ):
        errors.append(
            "inputs.fileCount must be a positive integer"
        )

    content_hash = inputs.get("contentHash")

    if (
        not isinstance(content_hash, str)
        or _SHA256_PATTERN.fullmatch(content_hash) is None
    ):
        errors.append(
            "inputs.contentHash must be a sha256 digest"
        )

    files = inputs.get("files")

    if not isinstance(files, list) or not files:
        errors.append("inputs.files must not be empty")
        return _shape_diagnostics(
            errors,
            source_path,
        )

    seen_paths: set[str] = set()

    for index, entry in enumerate(files):
        label = f"inputs.files[{index}]"

        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue

        path_value = entry.get("path")

        if (
            not isinstance(path_value, str)
            or not path_value.strip()
        ):
            errors.append(
                f"{label}.path must be a non-empty string"
            )
        else:
            path = Path(path_value)

            if path.is_absolute() or ".." in path.parts:
                errors.append(
                    f"{label}.path must be a safe relative path"
                )
            elif path_value in seen_paths:
                errors.append(
                    f"{label}.path is duplicated"
                )
            else:
                seen_paths.add(path_value)

        sha256_value = entry.get("sha256")

        if (
            not isinstance(sha256_value, str)
            or _SHA256_PATTERN.fullmatch(
                sha256_value
            ) is None
        ):
            errors.append(
                f"{label}.sha256 must be a sha256 digest"
            )

        size_bytes = entry.get("sizeBytes")

        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 0
        ):
            errors.append(
                f"{label}.sizeBytes must be a "
                "non-negative integer"
            )

    return _shape_diagnostics(
        errors,
        source_path,
    )


def _shape_diagnostics(
    errors: list[str],
    source_path: str,
) -> tuple[Diagnostic, ...]:
    return tuple(
        Diagnostic(
            code=SHAPE_DIAGNOSTIC,
            message=error,
            source_path=source_path,
        )
        for error in errors
    )


def _validate_drift(
    actual: JsonObject,
    expected: JsonObject,
    source_path: str,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    actual_inputs = actual.get("inputs")
    expected_inputs = expected.get("inputs")

    if not isinstance(expected_inputs, dict):
        raise ValueError(
            "Canonical lockfile inputs must be an object"
        )

    if not isinstance(actual_inputs, dict):
        return ()

    if (
        actual_inputs.get("patterns")
        != expected_inputs.get("patterns")
    ):
        diagnostics.append(
            Diagnostic(
                code=PATTERNS_DRIFT_DIAGNOSTIC,
                message=(
                    "lockfile input patterns drift detected"
                ),
                source_path=source_path,
            )
        )

    if (
        actual_inputs.get("fileCount")
        != expected_inputs.get("fileCount")
    ):
        diagnostics.append(
            Diagnostic(
                code=FILE_COUNT_DRIFT_DIAGNOSTIC,
                message="lockfile file count drift detected",
                source_path=source_path,
            )
        )

    if (
        actual_inputs.get("contentHash")
        != expected_inputs.get("contentHash")
    ):
        diagnostics.append(
            Diagnostic(
                code=CONTENT_HASH_DRIFT_DIAGNOSTIC,
                message=(
                    "lockfile content hash drift detected"
                ),
                source_path=source_path,
            )
        )

    diagnostics.extend(
        _validate_file_drift(
            actual_inputs.get("files"),
            expected_inputs.get("files"),
            source_path,
        )
    )
    return tuple(diagnostics)


def _validate_file_drift(
    actual_value: JsonValue | None,
    expected_value: JsonValue | None,
    source_path: str,
) -> tuple[Diagnostic, ...]:
    actual_by_path = _records_by_path(actual_value)
    expected_by_path = _records_by_path(expected_value)

    if actual_by_path is None or expected_by_path is None:
        return ()

    diagnostics: list[Diagnostic] = []

    for path in sorted(
        set(expected_by_path) - set(actual_by_path)
    ):
        diagnostics.append(
            Diagnostic(
                code=MISSING_INPUT_DIAGNOSTIC,
                message=(
                    f"missing input file in lockfile: {path}"
                ),
                source_path=source_path,
            )
        )

    for path in sorted(
        set(actual_by_path) - set(expected_by_path)
    ):
        diagnostics.append(
            Diagnostic(
                code=UNEXPECTED_INPUT_DIAGNOSTIC,
                message=(
                    f"unexpected input file in lockfile: {path}"
                ),
                source_path=source_path,
            )
        )

    for path in sorted(
        set(actual_by_path) & set(expected_by_path)
    ):
        actual_record = actual_by_path[path]
        expected_record = expected_by_path[path]

        if (
            actual_record.get("sha256")
            != expected_record.get("sha256")
        ):
            diagnostics.append(
                Diagnostic(
                    code=HASH_DRIFT_DIAGNOSTIC,
                    message=(
                        "sha256 drift for input file: "
                        f"{path}"
                    ),
                    source_path=source_path,
                )
            )

        if (
            actual_record.get("sizeBytes")
            != expected_record.get("sizeBytes")
        ):
            diagnostics.append(
                Diagnostic(
                    code=SIZE_DRIFT_DIAGNOSTIC,
                    message=(
                        "sizeBytes drift for input file: "
                        f"{path}"
                    ),
                    source_path=source_path,
                )
            )

    return tuple(diagnostics)


def _records_by_path(
    value: JsonValue | None,
) -> dict[str, JsonObject] | None:
    if not isinstance(value, list):
        return None

    result: dict[str, JsonObject] = {}

    for entry in value:
        if not isinstance(entry, dict):
            return None

        path = entry.get("path")

        if not isinstance(path, str):
            return None

        result[path] = entry

    return result
