# Domain diagrams

The domain model is divided into focused bounded-context diagrams.

## Navigation

~~~text
agentic-domain-overview.puml
  High-level navigation only

setup-selection-chen.puml
  Project, guided setup, profile and concrete selection

workflow-control-chen.puml
  Workflow state machine, transitions, gates and ownership

agent-composition-chen.puml
  Bundle workers, role bindings and separation of duties

capabilities-artifacts-targets-chen.puml
  Skills, capabilities, artifacts, permissions and targets
~~~

## Authority

The overview diagram is not authoritative for attributes or cardinalities.

Each detailed Chen diagram is authoritative for the entities and relationships
owned by its bounded context.

Entities imported from another context are marked `<<reference>>` and contain
only their identity. Their complete definition belongs to the diagram where
they are a full entity.

Cross-context compiler rules remain documented in:

~~~text
docs/architecture.md
docs/core-domain-model.md
project-status.md
~~~

The rendered SVG for every PlantUML source must be regenerated in the same
migration slice.

## Rendering

The `.puml` files are the authoritative domain model. The committed `.svg`
files are derived stakeholder-facing visualizations.

Render all diagrams with the repository-pinned renderer:

```bash
uv run render-domain-diagrams
```

Verify that committed SVGs match canonical rendering without changing files:

```bash
uv run render-domain-diagrams --check
```

The renderer version, distribution checksum and layout-engine decision are
defined by ADR-0003.
