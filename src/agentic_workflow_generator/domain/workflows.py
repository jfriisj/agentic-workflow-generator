"""Reusable workflow domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowGate:
    """Immutable blocking evidence gate for one workflow state."""

    name: str
    blocking: bool
    required_capabilities: tuple[str, ...]
    required_artifacts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkflowState:
    """Immutable workflow state.

    Concrete agent ownership and role bindings deliberately do not
    belong to the workflow model.
    """

    name: str
    terminal: bool
    gate: WorkflowGate | None


@dataclass(frozen=True, slots=True)
class WorkflowTransition:
    """Immutable event-driven transition between workflow states."""

    source: str
    target: str
    event: str


@dataclass(frozen=True, slots=True)
class Workflow:
    """Immutable reusable fail-closed workflow definition.

    Agent instances, state owners, workflow controllers and artifact
    producers deliberately belong to bundle composition instead.
    """

    name: str
    version: str
    description: str
    start_state: str
    terminal_states: tuple[str, ...]
    default_failure_state: str
    fail_closed: bool
    states: tuple[WorkflowState, ...]
    transitions: tuple[WorkflowTransition, ...]
