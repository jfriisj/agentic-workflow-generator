# Projektstatus — `agentic-workflow-generator`

Opdateret: 4. august 2026

Denne fil er projektets autoritative aktuelle status.

Accepteret scope ejes af `docs/scope.md`. Governance ejes af
`docs/governance.md`. Den operationelle leveranceproces ejes alene af
`docs/workflow.md`. Arkitekturnarrativet ejes af `docs/architecture.md`, den eneste semantiske
architecture-model ejes af `docs/architecture/workspace.dsl`, og rationale ejes af
accepterede ADRs. Teknologibaselinen dokumenteres i `docs/tech-stack.md`.

## Aktuel fase

**V1 completion**

Migrationen til den typed `AgentInstance` / `RoleBinding`-arkitektur,
`CompiledComposition` som canonical compiler-authoritet og typed top-level CLI er
afsluttet.

ADR-0008 fastlægger v1-produktmål, seks målbare milestones, controlled evolution
og en finite release-readiness exit condition. `docs/scope.md` er nu alignet med
den beslutning og autoriserer kun det bounded arbejde, der kræves for at afslutte
de seks milestones.

Projektet arbejder derfor mod en repository-verificerbar v1 completion state
frem for en åben post-migration hardening-fase.

## V1 outcome

V1 er en færdig, lokalt kørbar, deterministic compiler, der fra en valideret
declarative composition genererer komplette og reproducible software-delivery
agent configurations til VS Code Copilot og OpenCode med fail-closed workflows,
permissions, artifacts og evidence uden selv at være workflow runtime.

V1 skal samtidig bevare controlled evolution: sandsynlige bounded områder skal
senere kunne tilføjes, ændres eller fjernes gennem eksplicitte kontrakter og
beslutninger uden second compiler authority, parallel resolution paths eller
implicit fallback.

ADR-0008 ejer det fulde v1-outcome, milestone-definitionerne og release exit
criteria.

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
- canonical Structurizr DSL architecture-model med pinned Structurizr/Docker
  validation og reproducible derived SVG via pinned PlantUML, Smetana og DejaVu.

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

Disse regler er v1-invarianter. Ændring kræver en eksplicit scope- og
arkitekturbeslutning og må ikke ske indirekte som del af roadmap-implementation.

## Senest afsluttede hardening-slices

Følgende repository-foundation er etableret på `development`:

- governed delivery med `development` som integration og `production` som
  stable/release;
- artifact provenance contract semantics;
- artifact revision contract semantics og end-to-end contractimplementation;
- shared og artifact-specifik statussemantik;
- reproducible artifact evidence contract;
- Python/uv-baseret obligatorisk toolchain uden Node/npm-krav;
- canonical Structurizr DSL architecture-model med repository-owned validation
  og reproducible stakeholder-SVG rendering.

Historisk test- og migrationsstatistik bevares i Git-historikken og er ikke
aktuel projektstatus.

## V1 milestones

1. Product and architecture clarity.
2. Complete compiler contracts.
3. Honest registry compositions.
4. Canonical target preservation.
5. Consumer acceptance and release readiness.
6. Controlled evolution.

Milestones og deres målbare completion criteria ejes af ADR-0008. Fremtidige
issues skal angive hvilket milestone og hvilket exit criterion de fremmer.

## Kendte v1-gaps

### Artifact contracts

Den eksisterende artifact-model mangler fortsat fuld implementation for:

- input-artifact references.

### Workflows

Den eksisterende workflow-model mangler fortsat hardening omkring:

- eksplicit `BLOCKED`-routing;
- entydig controller- og routingsemantik;
- klar test-evidens i eksisterende flows;
- klar execution-semantik for det eksisterende AI-evalueringsflow.

Retry, escalation og artifact invalidation er ikke v1-krav og er ikke accepteret
scope.

### Profiles, bundles og setups

Registry-indholdet kræver fortsat audit og hardening for stale tekst,
capability completeness, placebo-lignende setupvalg og præcis klassifikation af
den composition, der faktisk materialiseres.

### Architecture and documentation

ADR-0009 architecture-model migrationen og den efterfølgende bounded
architecture/documentation consolidation er gennemført i den nuværende
integration-target state:

- `docs/architecture/workspace.dsl` er den eneste semantiske architecture-model;
- `docs/architecture.md` er reduceret til den concise current-state
  architecture narrative;
- `docs/core-domain-model.md` ejer fortsat detailed platform-neutral
  core-domain semantics;
- stakeholder-visninger er derived SVG under `docs/architecture/diagrams/`;
- Structurizr-validering/export er pinned og repository-owned;
- de tidligere authoritative PlantUML-domainkilder er fjernet;
- PlantUML er kun retained som ephemeral derived rendering-input.

Konsolideringen ændrer ikke produkt-, compiler-, registry-, workflow-, artifact-
eller target-scope.

### Testkvalitet og consumer acceptance

Testsuiten har kendt duplicate-code-gæld. Den må reduceres uden at deaktivere
kvalitetsregler, svække assertions eller skjule duplication gennem exclusions.

V1 kræver desuden consumer-oriented acceptance coverage, der beviser
deterministic compilation, materialization og validation for de understøttede
compositions og begge nuværende targets.

## Næste prioritet

Architecture/documentation consolidation er afsluttet. Denne ændring vælger ikke
en ny workstream. Næste konkrete prioritet skal vælges fra de resterende
accepterede v1-gaps gennem repository issue/readiness-flowet.

De resterende roadmap-områder omfatter input-artifact references,
workflow-semantics, registry-audit, target preservation og consumer acceptance.

## Accepted architecture-model decision

ADR-0009 selects Structurizr DSL as the v1 canonical architecture-model
technology, and the migration cutover has established:

```text
docs/architecture/workspace.dsl
```

as the sole semantic architecture model.

The accepted documentation toolchain is:

- Structurizr vNext `2026.06.28`;
- official image tag `structurizr/structurizr:2026.06.28-noble`;
- accepted content digest
  `sha256:b5140a2a783b0cc780fe4b54dcfeecb565ddd5fce5a578e7ff600b78ad0cc03a`;
- Linux amd64;
- Docker as a development/documentation toolchain prerequisite only;
- PlantUML `1.2026.6`, Smetana and DejaVu `2.37` only for the retained
  reproducible derived SVG stage.

Normal architecture validation uses the content-addressed local Structurizr
image with networking disabled. Explicit preparation is the only acquisition
step. No Structurizr, Docker or Java dependency enters the product/compiler
runtime boundary.

Native Structurizr browser/Playwright rendering remains excluded.

## Autoritativ arkitektur

Den aktuelle authority efter ADR-0009 cutover er:

- `docs/architecture.md` — current-state architecture narrative;
- `docs/architecture/workspace.dsl` — sole semantic architecture model;
- `docs/core-domain-model.md` — detailed textual core-domain semantics;
- `docs/adr/` — architecture rationale and accepted decisions.

Stakeholder-facing derived architecture output er:

- `docs/architecture/diagrams/system-context.svg`;
- `docs/architecture/diagrams/compiler-responsibilities.svg`.

De committed SVG-filer er ikke semantic authority. Deres ephemeral PlantUML
input genereres deterministisk fra Structurizr-workspacet og renderes med den
retained ADR-0003 PlantUML/Smetana/DejaVu-kontrakt.
