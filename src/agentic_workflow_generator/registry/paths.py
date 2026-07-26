"""Canonical repository path definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    """Canonical paths rooted in an explicit repository."""

    root: Path

    def __post_init__(self) -> None:
        if not self.root.is_absolute():
            raise ValueError("Repository root must be an absolute path")

        resolved_root = self.root.resolve(strict=True)

        if not resolved_root.is_dir():
            raise ValueError("Repository root must be a directory")

        object.__setattr__(self, "root", resolved_root)

    @property
    def registry_root(self) -> Path:
        return self.root / "registry"

    @property
    def schema_root(self) -> Path:
        return self.root / ".agentic" / "schemas"

    @property
    def active_config(self) -> Path:
        return self.root / ".agentic" / "agentic.json"

    @property
    def setup_profile(self) -> Path:
        return self.root / ".agentic" / "setup-profile.json"

    @property
    def generated_root(self) -> Path:
        return self.root / ".agentic" / "generated"

    @property
    def lockfile(self) -> Path:
        return self.root / ".agentic" / "agentic-lock.json"

    @property
    def manifest(self) -> Path:
        return self.generated_root / "output-manifest.json"

    def repository_path(
        self,
        relative_path: str | Path,
    ) -> Path:
        """Resolve one safe repository-relative path."""

        path = Path(relative_path)

        if not path.parts:
            raise ValueError("Repository-relative path must not be empty")

        if path.is_absolute():
            raise ValueError("Repository-relative path must not be absolute")

        if ".." in path.parts:
            raise ValueError("Repository-relative path must not contain '..'")

        resolved = (self.root / path).resolve(strict=False)

        if not resolved.is_relative_to(self.root):
            raise ValueError("Resolved path escapes the repository root")

        return resolved

    def owned_path(
        self,
        owned_root: str | Path,
        relative_path: str | Path,
    ) -> Path:
        """Resolve a path and require it to stay in an owned root."""

        resolved_owned_root = self.repository_path(owned_root)
        resolved_path = self.repository_path(relative_path)

        if not resolved_path.is_relative_to(resolved_owned_root):
            raise ValueError("Resolved path escapes the owned root")

        return resolved_path
