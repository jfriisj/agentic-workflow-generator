# Projektstatus — `agentic-workflow-generator`

Opdateret: 3. august 2026

Denne fil er projektets autoritative aktuelle status.

Accepteret scope ejes af `docs/scope.md`. Governance ejes af
`docs/governance.md`. Den operationelle leveranceproces ejes alene af
`docs/workflow.md`. Arkitektur ejes af `docs/architecture.md`, de deri udpegede
autoritative diagramkilder og accepterede ADRs. Teknologibaselinen dokumenteres i
`docs/tech-stack.md`.

## Aktuel fase

**Post-migration hardening**

Migrationen til den typed `AgentInstance` / `RoleBinding`-arkitektur,
`CompiledComposition` som canonical compiler-authoritet og typed top-level CLI er
afsluttet.

Projektet er nu begrænset til hardening af den allerede accepterede compiler-,
workflow-, artifact- og registry-model samt kendte kvalitets- og
dokumentationsgaps.

## Implementeret baseline

Følgende er implementeret og accepteret:

- typed registry-loading og immutable domænemodeller;
- bundle-owned agent instances og explicit role bindings;
- én canonical `CompiledComposition`;
- `.agentic/agentic.json` som persistent aktiv composition;
- compiler-input provenance via `.agentic/agentic-lock.json`;
- typed targetrendering og transaktionel materialisering;
- canonical output manifest og generated-output validation;
- guided initialization og bundle initialization;
- fail-fast diagnostics og semantic validation;
- Python-baseret top-level CLI;
- target adapters for `vscode-copilot` og `opencode`;
- release-CI-validering på Python 3.11 og 3.13 for pull requests til
  `production`;
- reproducerbar domain-diagram-rendering med pinned PlantUML, Smetana og pinned
  DejaVu-fontinput.

Der findes ingen separat resolution-authoritet, compatibility projection eller
silent fallback-path.

## Hårde arkitekturinvarianter

- `CompiledComposition` er compilerens eneste canonical interne composition.
- Bundles ejer konkrete agent instances og role bindings.
- Agentprofiler og profiles er rådgivende og må ikke være runtime fallback.
- Hver ikke-terminal workflow-state har præcis én state owner.
- Hvert workflow har præcis én controller.
- Controlleren ejer routing, men ingen workflow-state eller gate.
- Effective permissions tilhører agent instances.
- Capabilities, skills, artifacts, responsibilities og guardrails tilhører role
  bindings.
- Targetrenderere bruger canonical typed composition og genfortolker ikke raw
  registry.
- Lockfile ejer compiler-input provenance.
- Output manifest ejer generated-output provenance og integritet.
- Manglende eller ugyldige krav fejler eksplicit.

Ændring af disse regler kræver en eksplicit scope- og arkitekturbeslutning.

## Senest afsluttede hardening-slices

Følgende repository-foundation er etableret på `development`:

- governed delivery med `development` som integration og `production` som
  stable/release;
- artifact provenance contract semantics;
- artifact revision contract semantics og end-to-end contractimplementation;
- Python/uv-baseret obligatorisk toolchain uden Node/npm-krav;
- canonical domain-diagram-rendering med PlantUML 1.2026.6, Smetana og isoleret
  DejaVu 2.37 font-resolution.

Historisk test- og migrationsstatistik bevares i Git-historikken og er ikke
aktuel projektstatus.

## Kendte gaps

### Artifact contracts

Den eksisterende artifact-model mangler fortsat fuld implementation for:

- reproducerbar evidens;
- input-artifact references;
- artifact-specifik statussemantik.

### Workflows

Den eksisterende workflow-model mangler fortsat hardening omkring:

- eksplicit `BLOCKED`-routing;
- entydig controller- og routingsemantik;
- klar test-evidens i eksisterende flows;
- klar execution-semantik for det eksisterende AI-evalueringsflow.

Retry, escalation og artifact invalidation er ikke accepteret scope.

### Profiles, bundles og setups

Registry-indholdet kræver fortsat audit og hardening for stale tekst,
capability completeness, placebo-lignende setupvalg og præcis klassifikation af
den composition, der faktisk materialiseres.

### Testkvalitet

Testsuiten har kendt duplicate-code-gæld. Den må reduceres uden at deaktivere
kvalitetsregler, svække assertions eller skjule duplication gennem exclusions.

## Næste prioritet

**Artifact contract hardening** er fortsat den accepterede produktprioritet.

Canonical artifact provenance semantics, artifact revision contract og shared
artifact status-invariant contract er implementeret end-to-end. Status-invariant
semantikken følger ADR-0005.

Artifact-specifik statusklassifikation er nu besluttet i ADR-0006 for de syv
eksisterende governed artifacts. Beslutningen fastlægger artifact-specifikke
`PASS`, `FAIL` og `BLOCKED`-definitioner samt mixed-condition-reglen uden at
indføre workflow-routing, runtime artifact validation eller et generisk policy
engine.

Næste mindste sammenhængende slice er at implementere ADR-0006 end-to-end i den
eksisterende artifact-contract boundary. Implementation skal mindst:

- tilføje én typed artifact-specifik status-semantics contract;
- gøre de canonical semantics obligatoriske for alle syv artifact contracts;
- bevare semantics deterministisk i generated schemas, active config og begge
  eksisterende targetrenderere;
- validere contract shape og canonical projection fail-closed;
- opdatere producer-facing instruktioner, tests, generated output og lock state
  hvor den eksisterende compilerpipeline kræver det;
- evolvere berørte artifact contract versions eksplicit.

Slicen må ikke implementere workflow- eller `BLOCKED`-routing, retry,
escalation, artifact invalidation, reproducible evidence hashes,
input-artifact lineage, produced-artifact persistence, execution history,
runtime artifact validation, configurable policy engines eller nye targets.

## Autoritativ arkitektur

- `docs/architecture.md`
- `docs/core-domain-model.md`
- `docs/adr/`
- `docs/diagrams/domain/agentic-domain-overview.puml`
- `docs/diagrams/domain/setup-selection-chen.puml`
- `docs/diagrams/domain/workflow-control-chen.puml`
- `docs/diagrams/domain/agent-composition-chen.puml`
- `docs/diagrams/domain/capabilities-artifacts-targets-chen.puml`

De detaljerede PlantUML-kilder er autoritative for deres respektive bounded
contexts. De committed SVG-filer er derived stakeholder-visualiseringer og skal
forblive canonical med de pinnede rendering-inputs.
