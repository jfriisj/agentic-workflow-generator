"""Structured compiler diagnostics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_DIAGNOSTIC_CODE_PATTERN = re.compile(r"^AWG-[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-\d{3}$")


class Severity(StrEnum):
    """Supported diagnostic severity levels."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Immutable structured validation or compiler diagnostic."""

    code: str
    message: str
    severity: Severity = Severity.ERROR
    source_path: str | None = None
    location: str | None = None
    related_identities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _DIAGNOSTIC_CODE_PATTERN.fullmatch(self.code):
            raise ValueError("Diagnostic code must match 'AWG-<DOMAIN>-<NNN>'")

        if not self.message or self.message != self.message.strip():
            raise ValueError("Diagnostic message must be non-empty and trimmed")

        if self.source_path is not None and (
            not self.source_path or self.source_path != self.source_path.strip()
        ):
            raise ValueError(
                "Diagnostic source_path must be non-empty and trimmed when provided"
            )

        if self.location is not None and (
            not self.location or self.location != self.location.strip()
        ):
            raise ValueError(
                "Diagnostic location must be non-empty and trimmed when provided"
            )

        if any(
            not identity or identity != identity.strip()
            for identity in self.related_identities
        ):
            raise ValueError("Related identities must be non-empty and trimmed")

        if len(set(self.related_identities)) != len(self.related_identities):
            raise ValueError("Related identities must be unique")
