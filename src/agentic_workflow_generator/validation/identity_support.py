"""Shared registry identity validation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from agentic_workflow_generator.domain import Diagnostic


def folder_name_mismatch_diagnostic(
    name: str,
    source_path: Path,
    diagnostic_code: str,
) -> Diagnostic | None:
    """Return a diagnostic when a registry name differs from its folder."""

    folder_name = source_path.parent.name

    if name == folder_name:
        return None

    return Diagnostic(
        code=diagnostic_code,
        message=(
            f"name {name!r} does not match folder "
            f"{folder_name!r}"
        ),
        source_path=source_path.as_posix(),
        location="name",
        related_identities=(
            name,
            folder_name,
        ),
    )


def duplicate_name_diagnostics(
    entries: Iterable[tuple[str, Path]],
    diagnostic_code: str,
    entity_label: str,
) -> tuple[Diagnostic, ...]:
    """Return deterministic diagnostics for repeated registry names."""

    seen: dict[str, Path] = {}
    diagnostics: list[Diagnostic] = []

    for name, source_path in entries:
        first_path = seen.get(name)

        if first_path is None:
            seen[name] = source_path
            continue

        diagnostics.append(
            Diagnostic(
                code=diagnostic_code,
                message=(
                    f"{entity_label} name {name!r} is duplicated; "
                    "first declared at "
                    f"{first_path.as_posix()}"
                ),
                source_path=source_path.as_posix(),
                location="name",
                related_identities=(name,),
            )
        )

    return tuple(diagnostics)
