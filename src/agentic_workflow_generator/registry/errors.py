"""Structured registry boundary exceptions."""

from __future__ import annotations

from pathlib import Path

from .kinds import RegistryKind


class RegistryError(Exception):
    """Base class for expected registry failures."""


class RegistryPathError(RegistryError):
    """Registry failure associated with one path."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.detail = message
        super().__init__(f"{path}: {message}")


class RegistryRootNotFoundError(RegistryPathError):
    """Raised when the registry root is missing."""


class RegistryAreaNotFoundError(RegistryPathError):
    """Raised when a required registry area is missing."""

    def __init__(
        self,
        kind: RegistryKind,
        path: Path,
    ) -> None:
        self.kind = kind
        super().__init__(
            path,
            f"required {kind.value} registry area not found",
        )


class RegistryFilesNotFoundError(RegistryPathError):
    """Raised when a registry area has no required files."""

    def __init__(
        self,
        kind: RegistryKind,
        path: Path,
        pattern: str,
    ) -> None:
        self.kind = kind
        self.pattern = pattern
        super().__init__(
            path,
            (f"no {kind.value} registry files match {pattern!r}"),
        )


class RegistrySourcePathError(RegistryPathError):
    """Raised when a discovered source escapes the repository."""

    def __init__(
        self,
        kind: RegistryKind,
        path: Path,
        reason: str,
    ) -> None:
        self.kind = kind
        super().__init__(
            path,
            (f"unsafe {kind.value} registry source: {reason}"),
        )


class RegistryIdentityError(RegistryPathError):
    """Raised when a registry identity is invalid."""

    def __init__(
        self,
        *,
        kind: RegistryKind,
        source_path: Path,
        identity_field: str,
        reason: str,
    ) -> None:
        self.kind = kind
        self.identity_field = identity_field
        super().__init__(
            source_path,
            (f"invalid {kind.value} identity field {identity_field!r}: {reason}"),
        )


class DuplicateRegistryIdentityError(RegistryError):
    """Raised when one kind declares an identity twice."""

    def __init__(
        self,
        *,
        kind: RegistryKind,
        identity: str,
        first_path: Path,
        duplicate_path: Path,
    ) -> None:
        self.kind = kind
        self.identity = identity
        self.first_path = first_path
        self.duplicate_path = duplicate_path
        super().__init__(
            f"{duplicate_path}: duplicate {kind.value} "
            f"identity {identity!r}; first declared at "
            f"{first_path}"
        )


class RegistryEntryNotFoundError(RegistryError):
    """Raised when indexed lookup cannot resolve an identity."""

    def __init__(
        self,
        kind: RegistryKind,
        identity: str,
    ) -> None:
        self.kind = kind
        self.identity = identity
        super().__init__(f"Unknown {kind.value} registry identity: {identity!r}")
