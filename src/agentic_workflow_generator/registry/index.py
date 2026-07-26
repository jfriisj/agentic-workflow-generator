"""Unique registry identity indexing."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from .errors import (
    DuplicateRegistryIdentityError,
    RegistryEntryNotFoundError,
    RegistryIdentityError,
)
from .kinds import RegistryKind
from .source import RegistrySource


class RegistryIndex:
    """Immutable lookup index for loaded registry sources."""

    __slots__ = (
        "_entries_by_kind",
        "_sources_by_kind",
    )

    def __init__(
        self,
        sources: Iterable[RegistrySource],
    ) -> None:
        entries_by_kind: dict[
            RegistryKind,
            dict[str, RegistrySource],
        ] = {kind: {} for kind in RegistryKind}
        sources_by_kind: dict[
            RegistryKind,
            list[RegistrySource],
        ] = {kind: [] for kind in RegistryKind}

        for source in sources:
            identity = self._require_identity(source)
            entries = entries_by_kind[source.kind]

            if identity in entries:
                raise DuplicateRegistryIdentityError(
                    kind=source.kind,
                    identity=identity,
                    first_path=entries[identity].source_path,
                    duplicate_path=source.source_path,
                )

            entries[identity] = source
            sources_by_kind[source.kind].append(source)

        self._entries_by_kind = MappingProxyType(
            {
                kind: MappingProxyType(entries)
                for kind, entries in entries_by_kind.items()
            }
        )
        self._sources_by_kind = MappingProxyType(
            {
                kind: tuple(kind_sources)
                for kind, kind_sources in (sources_by_kind.items())
            }
        )

    def get(
        self,
        kind: RegistryKind,
        identity: str,
    ) -> RegistrySource:
        """Return one source or fail explicitly."""

        try:
            return self._entries_by_kind[kind][identity]
        except KeyError as exc:
            raise RegistryEntryNotFoundError(
                kind,
                identity,
            ) from exc

    def sources(
        self,
        kind: RegistryKind,
    ) -> tuple[RegistrySource, ...]:
        """Return sources in deterministic load order."""

        return self._sources_by_kind[kind]

    def identities(
        self,
        kind: RegistryKind,
    ) -> tuple[str, ...]:
        """Return identities in deterministic load order."""

        return tuple(self._require_identity(source) for source in self.sources(kind))

    def count(
        self,
        kind: RegistryKind,
    ) -> int:
        """Return the number of indexed entries for one kind."""

        return len(self._sources_by_kind[kind])

    @staticmethod
    def _require_identity(
        source: RegistrySource,
    ) -> str:
        identity_field = source.kind.identity_field
        raw_identity = source.data.get(identity_field)

        if raw_identity is None:
            raise RegistryIdentityError(
                kind=source.kind,
                source_path=source.source_path,
                identity_field=identity_field,
                reason="field is missing",
            )

        if not isinstance(raw_identity, str):
            raise RegistryIdentityError(
                kind=source.kind,
                source_path=source.source_path,
                identity_field=identity_field,
                reason="value must be a string",
            )

        if not raw_identity:
            raise RegistryIdentityError(
                kind=source.kind,
                source_path=source.source_path,
                identity_field=identity_field,
                reason="value must not be empty",
            )

        if raw_identity != raw_identity.strip():
            raise RegistryIdentityError(
                kind=source.kind,
                source_path=source.source_path,
                identity_field=identity_field,
                reason="value must be trimmed",
            )

        return raw_identity

    @property
    def entries_by_kind(
        self,
    ) -> Mapping[
        RegistryKind,
        Mapping[str, RegistrySource],
    ]:
        """Expose an immutable indexed view."""

        return self._entries_by_kind
