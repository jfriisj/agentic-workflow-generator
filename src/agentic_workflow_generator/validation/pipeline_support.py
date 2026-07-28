"""Shared fail-fast registry validation pipeline."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from jsonschema import Draft202012Validator

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.registry import RegistrySource

ParsedT = TypeVar("ParsedT")


def validate_and_parse_sources(
    sources: Iterable[RegistrySource],
    validator: Draft202012Validator,
    pre_schema_validator: Callable[
        [RegistrySource],
        tuple[Diagnostic, ...],
    ],
    schema_validator: Callable[
        [RegistrySource, Draft202012Validator],
        tuple[Diagnostic, ...],
    ],
    parser: Callable[[RegistrySource], ParsedT],
    semantic_validator: Callable[
        [ParsedT],
        tuple[Diagnostic, ...],
    ]
    | None = None,
) -> tuple[list[ParsedT], list[Diagnostic]]:
    """Validate and parse registry sources in source order."""

    parsed_items: list[ParsedT] = []
    diagnostics: list[Diagnostic] = []

    for source in sources:
        pre_schema_diagnostics = pre_schema_validator(source)
        diagnostics.extend(pre_schema_diagnostics)

        if pre_schema_diagnostics:
            continue

        schema_diagnostics = schema_validator(
            source,
            validator,
        )
        diagnostics.extend(schema_diagnostics)

        if schema_diagnostics:
            continue

        parsed = parser(source)
        parsed_items.append(parsed)

        if semantic_validator is not None:
            diagnostics.extend(
                semantic_validator(parsed)
            )

    return parsed_items, diagnostics
