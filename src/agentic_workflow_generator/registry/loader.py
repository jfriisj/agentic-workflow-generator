"""Deterministic registry file discovery and loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_workflow_generator.infrastructure import (
    read_json_object,
)

from .errors import (
    RegistryAreaNotFoundError,
    RegistryFilesNotFoundError,
    RegistryRootNotFoundError,
    RegistrySourcePathError,
)
from .kinds import RegistryKind
from .paths import ProjectPaths
from .source import RegistrySource


@dataclass(frozen=True, slots=True)
class RegistryLoader:
    """Load registry sources through explicit kind contracts."""

    paths: ProjectPaths

    def discover(
        self,
        kind: RegistryKind,
    ) -> tuple[Path, ...]:
        """Discover required files in deterministic order."""

        registry_root = self.paths.registry_root

        if not registry_root.is_dir():
            raise RegistryRootNotFoundError(
                registry_root,
                "required registry root not found",
            )

        area_root = registry_root / kind.directory_name

        if not area_root.is_dir():
            raise RegistryAreaNotFoundError(
                kind,
                area_root,
            )

        discovered = sorted(
            area_root.glob(kind.file_pattern),
            key=lambda path: path.relative_to(registry_root).as_posix(),
        )

        if not discovered:
            raise RegistryFilesNotFoundError(
                kind,
                area_root,
                kind.file_pattern,
            )

        safe_paths = tuple(self._require_safe_source(kind, path) for path in discovered)

        return safe_paths

    def load(
        self,
        kind: RegistryKind,
    ) -> tuple[RegistrySource, ...]:
        """Load all sources for one registry kind."""

        return tuple(
            RegistrySource(
                kind=kind,
                source_path=path.relative_to(self.paths.root),
                data=read_json_object(path),
            )
            for path in self.discover(kind)
        )

    def load_all(
        self,
    ) -> tuple[RegistrySource, ...]:
        """Load every required registry kind."""

        return tuple(source for kind in RegistryKind for source in self.load(kind))

    def _require_safe_source(
        self,
        kind: RegistryKind,
        path: Path,
    ) -> Path:
        relative_path = path.relative_to(self.paths.root)

        try:
            safe_path = self.paths.repository_path(relative_path)
        except ValueError as exc:
            raise RegistrySourcePathError(
                kind,
                relative_path,
                str(exc),
            ) from exc

        if not safe_path.is_file():
            raise RegistrySourcePathError(
                kind,
                relative_path,
                "discovered path is not a file",
            )

        return safe_path
