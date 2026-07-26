"""Guided setup and materialized setup-profile domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SetupMode(StrEnum):
    """Supported guided setup modes."""

    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"


class SetupOptionClassification(StrEnum):
    """Supported classifications for registered setup options."""

    RECOMMENDED = "recommended"
    COMPATIBLE = "compatible"
    BLOCKED = "blocked"


class SetupAnswerClassification(StrEnum):
    """Supported classifications for materialized setup answers."""

    RECOMMENDED = "recommended"
    COMPATIBLE = "compatible"


@dataclass(frozen=True, slots=True)
class SetupSelection:
    """Complete setup selection used as default and materialized output."""

    bundle: str
    targets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SetupSelectionPatch:
    """Optional bundle or target override contributed by one setup option."""

    bundle: str | None
    targets: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class SetupOption:
    """Immutable answer option for one guided setup question."""

    value: str
    label: str
    classification: SetupOptionClassification
    reason: str
    selection: SetupSelectionPatch | None


@dataclass(frozen=True, slots=True)
class SetupQuestion:
    """Immutable guided setup question."""

    id: str
    prompt: str
    default_option: str
    options: tuple[SetupOption, ...]


@dataclass(frozen=True, slots=True)
class Setup:
    """Immutable guided selection definition.

    Setups select a bundle and enabled targets. The selected bundle owns
    the effective profile, workflow, instances, bindings and runtime
    composition.
    """

    name: str
    description: str
    version: str
    mode: SetupMode
    default_selection: SetupSelection
    questions: tuple[SetupQuestion, ...]


@dataclass(frozen=True, slots=True)
class SetupAnswer:
    """Immutable recorded answer to one setup question."""

    question: str
    selected: str
    classification: SetupAnswerClassification
    reason: str


@dataclass(frozen=True, slots=True)
class SetupPolicy:
    """Immutable fail-fast setup materialization policy."""

    fail_fast: bool
    fallback_allowed: bool


@dataclass(frozen=True, slots=True)
class SetupProfile:
    """Immutable materialized guided setup decision."""

    schema_uri: str | None
    schema_version: str
    mode: SetupMode
    setup: str
    answers: tuple[SetupAnswer, ...]
    selected: SetupSelection
    policy: SetupPolicy
