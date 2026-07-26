"""Structured infrastructure exceptions."""

from __future__ import annotations

from pathlib import Path


class InfrastructureError(Exception):
    """Base class for expected infrastructure failures."""


class PathInfrastructureError(InfrastructureError):
    """Infrastructure error associated with one path."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.detail = message
        super().__init__(f"{path}: {message}")


class JsonFileNotFoundError(PathInfrastructureError):
    """Raised when a required JSON file is missing."""


class JsonReadError(PathInfrastructureError):
    """Raised when an existing JSON file cannot be read."""


class JsonDecodeFailure(PathInfrastructureError):
    """Raised when JSON syntax is invalid."""

    def __init__(
        self,
        path: Path,
        *,
        line: int,
        column: int,
        reason: str,
    ) -> None:
        self.line = line
        self.column = column
        self.reason = reason
        super().__init__(
            path,
            (f"invalid JSON at line {line}, column {column}: {reason}"),
        )


class JsonRootTypeError(PathInfrastructureError):
    """Raised when a JSON document has the wrong root type."""

    def __init__(
        self,
        path: Path,
        *,
        expected: str,
        actual: str,
    ) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            path,
            (f"expected JSON {expected}, found {actual}"),
        )


class JsonSerializationError(InfrastructureError):
    """Raised when a value cannot be serialized as strict JSON."""


class AtomicWriteError(PathInfrastructureError):
    """Raised when an atomic filesystem write fails."""


class HashReadError(PathInfrastructureError):
    """Raised when a file cannot be hashed."""
