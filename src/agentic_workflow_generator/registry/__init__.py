"""Registry boundary support."""

from .errors import (
    DuplicateRegistryIdentityError,
    RegistryAreaNotFoundError,
    RegistryEntryNotFoundError,
    RegistryError,
    RegistryFilesNotFoundError,
    RegistryIdentityError,
    RegistryRootNotFoundError,
    RegistrySourcePathError,
)
from .index import RegistryIndex
from .kinds import RegistryKind
from .loader import RegistryLoader
from .paths import ProjectPaths
from .source import RegistrySource

__all__ = [
    "DuplicateRegistryIdentityError",
    "ProjectPaths",
    "RegistryAreaNotFoundError",
    "RegistryEntryNotFoundError",
    "RegistryError",
    "RegistryFilesNotFoundError",
    "RegistryIdentityError",
    "RegistryIndex",
    "RegistryKind",
    "RegistryLoader",
    "RegistryRootNotFoundError",
    "RegistrySource",
    "RegistrySourcePathError",
]
