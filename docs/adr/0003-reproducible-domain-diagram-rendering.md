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
Smetana layout engine while Graphviz is unavailable. A subsequent CI proof
showed that SVG geometry still varied across hosts because PlantUML resolved
the generic `sans-serif` family through host-installed fonts. Font selection is
therefore part of the canonical rendering input, not an ambient host property.

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
- the PlantUML Smetana layout engine;
- DejaVu Fonts `2.37` from the official TTF distribution;
- DejaVu archive SHA-256
  `7576310b219e04159d35ff61dd4a4ec4cdba4f35c00e002a136f00e96a908b0a`;
- `DejaVu Sans` as the explicit PlantUML default font;
- an isolated Fontconfig configuration that exposes only the pinned DejaVu
  font distribution during rendering.

The repository-owned rendering command must download the pinned PlantUML and
font distributions only when they are not already available in its tool cache,
verify their exact SHA-256 values before use and fail closed on any mismatch.

The PlantUML executable and DejaVu font distribution are tooling inputs, not
repository content. Their binaries and archives must not be committed to the
repository.

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

Contributors and CI use the same pinned renderer and font contract, independent
of host-installed fonts, and diagram drift becomes mechanically detectable.

PlantUML becomes an admitted documentation-build technology, but Java, Graphviz,
Docker and Node.js do not become mandatory project technologies.

The accepted renderer is intentionally platform-bounded. Cross-platform local
rendering is deferred until an accepted requirement exists.

## Acceptance scenarios

A conforming implementation must satisfy all of the following:

1. Every authoritative domain `.puml` file renders successfully with the pinned
   PlantUML version and Smetana.
2. Rendering succeeds when Graphviz is unavailable.
3. Two renders of unchanged sources with the pinned font distribution produce
   byte-identical SVG output.
4. The downloaded PlantUML distribution is rejected when its SHA-256 does not
   match the pinned value.
5. The downloaded DejaVu distribution is rejected when its SHA-256 does not
   match the pinned value.
6. Canonical rendering uses the pinned DejaVu distribution rather than
   host-installed fonts.
7. No PlantUML executable, font binary or distribution archive is committed to
   the repository.
8. CI fails when an authoritative `.puml` source and its committed SVG differ.
9. CI passes when every committed SVG matches canonical rendering.
10. Stakeholders can view the committed SVG files independently of the
    rendering tool.
11. No second authoritative diagram model is introduced.
