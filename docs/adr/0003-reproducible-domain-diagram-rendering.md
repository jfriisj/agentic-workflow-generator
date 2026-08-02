# ADR-0003: Reproducible domain diagram rendering

- Status: Accepted
- Date: 2026-08-02

## Context

The repository already treats the detailed PlantUML Chen sources under
`docs/diagrams/domain/` as authoritative for their bounded contexts and requires
the corresponding SVG files to remain synchronized.

The missing contract is reproducible rendering. The repository does not
currently define which renderer version, layout engine or validation procedure
must produce those SVG files. That allows contributor environments to produce
different derived diagrams from the same authoritative source.

The visual output is also stakeholder-facing. Stakeholders must be able to view
the diagrams from the repository without installing a diagram tool.

A local proof on the current repository established that PlantUML 1.2026.6
native Linux amd64 can render every existing domain diagram to SVG with the
Smetana layout engine while Graphviz is unavailable, and that repeated renders
are byte-identical.

## Decision

The existing detailed domain diagrams remain authoritative PlantUML Chen
sources.

The corresponding committed SVG files are derived stakeholder-facing
visualizations. They are not a second architecture authority.

Domain diagram rendering uses:

- PlantUML version `1.2026.6`;
- the official native Linux amd64 distribution;
- SHA-256
  `835c238634ed1b8638c3fdcfe4f94d005fc9664df3da2c88f80d0aaf4471b04b`;
- SVG output;
- the PlantUML Smetana layout engine.

The repository-owned rendering command must download the pinned distribution
only when it is not already available in its tool cache, verify the exact
SHA-256 before execution and fail closed on any mismatch.

The PlantUML executable is tooling, not repository content. The binary must not
be committed to the repository.

Rendering must not depend on:

- Java;
- Graphviz;
- Docker;
- Node.js or npm;
- a remote PlantUML rendering service.

The current rendering contract targets Linux amd64 because that matches the
accepted CI environment and the environment proven by this decision. Additional
host-platform support requires a concrete need and must not weaken the pinned
renderer contract.

CI must prove that committed SVG files are canonical by rendering every
authoritative `.puml` source with the pinned renderer and failing if the
resulting repository diff is non-empty.

A change to an authoritative domain diagram source must include its regenerated
SVG in the same coherent change.

## Alternatives considered

### Mermaid as the authoritative domain format

Rejected for the current detailed domain model.

GitHub renders Mermaid directly and it is useful for stakeholder-facing
diagrams. However, the current model uses PlantUML Chen semantics including
explicit relationship objects, relationship attributes and structural
cardinality ranges. Moving the authoritative model to Mermaid ER would require
semantic remodeling rather than a format-only migration.

Mermaid may be admitted later for a simpler non-authoritative overview if a
separate stakeholder communication need justifies a second diagram notation.

### D2 as the authoritative domain format

Rejected. D2 provides strong general-purpose diagram rendering but does not
provide a current semantic advantage that justifies migrating the established
Chen domain model or introducing another diagram DSL.

### Graphviz DOT

Rejected. DOT is a lower-level graph representation and would move domain
notation and layout responsibility into repository-specific conventions without
improving the current conceptual model.

### PlantUML Java distribution

Rejected for the current requirement. The native PlantUML distribution has been
proven sufficient, so requiring a JVM would add an unnecessary mandatory
technology.

### Remote rendering service

Rejected. A remote renderer would make the validation boundary network
dependent and would weaken local reproducibility.

### Keep SVG regeneration manual and unpinned

Rejected. The repository could not prove that committed stakeholder
visualizations correspond to the authoritative sources.

## Consequences

The repository keeps one authoritative detailed diagram language and one derived
visual format.

Stakeholders can view committed SVG files directly without installing PlantUML.

Contributors and CI use the same pinned renderer contract, and diagram drift
becomes mechanically detectable.

PlantUML becomes an admitted documentation-build technology, but Java, Graphviz,
Docker and Node.js do not become mandatory project technologies.

The accepted renderer is intentionally platform-bounded. Cross-platform local
rendering is deferred until an accepted requirement exists.

## Acceptance scenarios

A conforming implementation must satisfy all of the following:

1. Every authoritative domain `.puml` file renders successfully with the pinned
   PlantUML version and Smetana.
2. Rendering succeeds when Graphviz is unavailable.
3. Two renders of unchanged sources produce byte-identical SVG output.
4. The downloaded renderer is rejected when its SHA-256 does not match the
   pinned value.
5. No PlantUML executable or distribution archive is committed to the
   repository.
6. CI fails when an authoritative `.puml` source and its committed SVG differ.
7. CI passes when every committed SVG matches canonical rendering.
8. Stakeholders can view the committed SVG files independently of the rendering
   tool.
9. No second authoritative diagram model is introduced.
