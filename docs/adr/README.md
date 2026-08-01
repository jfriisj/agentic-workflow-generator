# Architecture Decision Records

This directory contains accepted and proposed Architecture Decision Records
(ADRs) for `agentic-workflow-generator`.

ADRs preserve the rationale behind significant architectural decisions. They do
not replace current architecture documentation. Current architecture is defined
by `docs/architecture.md` and its authoritative diagram sources.

## When an ADR is required

Create an ADR when a change makes a significant or long-lived decision about,
for example:

- bounded-context or component boundaries;
- dependency direction;
- ownership;
- canonical representations;
- persistence ownership;
- external contracts;
- deployment topology;
- cross-cutting execution behavior;
- technology choices with architectural consequences.

Routine implementation details do not require ADRs.

## Naming

Use sequential four-digit identifiers:

~~~text
0001-short-decision-title.md
0002-another-decision.md
~~~

Do not reuse an identifier.

## Status

Use one of:

- `Proposed`
- `Accepted`
- `Superseded`
- `Rejected`

An accepted ADR is historical evidence and must not be silently rewritten to
represent a later decision.

If a later decision changes an accepted ADR, create a new ADR and mark the
earlier one as superseded.

## Minimal format

~~~markdown
# ADR-NNNN: Decision title

- Status: Proposed
- Date: YYYY-MM-DD

## Context

What problem or constraint requires a decision?

## Decision

What has been decided?

## Alternatives considered

What reasonable alternatives were considered?

## Consequences

What becomes easier, harder, constrained or intentionally deferred?
~~~

## Workflow

1. Identify the architectural decision during the scope and architecture gates.
2. Create the ADR on the same topic branch as the change that requires it.
3. Keep the ADR focused on one decision.
4. Update affected authoritative architecture documentation and diagrams.
5. Review the ADR with the implementation pull request.
6. Treat the ADR as accepted only when the pull request is merged.

Governance for scope, branches, review and delivery is defined in
`docs/governance.md`.
