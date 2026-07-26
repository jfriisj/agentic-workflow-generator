from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.pipeline_support import (
    validate_and_parse_sources,
)


@dataclass(frozen=True, slots=True)
class Parsed:
    name: str


def source(name: str) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.AGENT,
        source_path=Path(f"{name}.json"),
        data={"name": name},
    )


def diagnostic(
    code: str,
    item: RegistrySource,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=code,
        source_path=item.source_path.as_posix(),
    )


def test_pipeline_preserves_fail_fast_order() -> None:
    sources = (
        source("legacy"),
        source("schema"),
        source("valid"),
    )

    parsed, diagnostics = validate_and_parse_sources(
        sources,
        Draft202012Validator({}),
        lambda item: (
            (diagnostic("AWG-TEST-001", item),)
            if item.data["name"] == "legacy"
            else ()
        ),
        lambda item, _validator: (
            (diagnostic("AWG-TEST-002", item),)
            if item.data["name"] == "schema"
            else ()
        ),
        lambda item: Parsed(str(item.data["name"])),
        lambda item: (
            Diagnostic(
                code="AWG-TEST-003",
                message=item.name,
            ),
        ),
    )

    assert parsed == [Parsed("valid")]
    assert tuple(item.code for item in diagnostics) == (
        "AWG-TEST-001",
        "AWG-TEST-002",
        "AWG-TEST-003",
    )


def test_pipeline_can_defer_semantic_validation() -> None:
    parsed, diagnostics = validate_and_parse_sources(
        (source("valid"),),
        Draft202012Validator({}),
        lambda _item: (),
        lambda _item, _validator: (),
        lambda item: Parsed(str(item.data["name"])),
    )

    assert parsed == [Parsed("valid")]
    assert diagnostics == []
