# Projektstatus — `agentic-workflow-generator`

Opdateret: 3. august 2026

Denne fil er projektets autoritative aktuelle status.

Accepteret scope ejes af `docs/scope.md`. Governance ejes af
`docs/governance.md`. Den operationelle leveranceproces ejes alene af
`docs/workflow.md`. Arkitektur ejes af `docs/architecture.md`, de deri udpegede
autoritative diagramkilder og accepterede ADRs. Teknologibaselinen dokumenteres i
`docs/tech-stack.md`.

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
- canonical domain-diagram-rendering med PlantUML 1.2026.6, Smetana og isoleret
  DejaVu 2.37 font-resolution.

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

Den nuværende architecture/documentation authority er mere kompleks end det
ønskede v1-niveau. Et separat roadmap skal beslutte og gennemføre:

- én kort og præcis architecture narrative;
- én canonical architecture model;
- fjernelse af redundant current-state documentation;
- en separat teknologibeslutning før en eventuel migration fra PlantUML til
  Structurizr DSL.

ADR-0008 vælger ikke diagramteknologi.

### Testkvalitet og consumer acceptance

Testsuiten har kendt duplicate-code-gæld. Den må reduceres uden at deaktivere
kvalitetsregler, svække assertions eller skjule duplication gennem exclusions.

V1 kræver desuden consumer-oriented acceptance coverage, der beviser
deterministic compilation, materialization og validation for de understøttede
compositions og begge nuværende targets.

## Næste prioritet

**Architecture-model migration** er næste sammenhængende architecture workstream.

ADR-0008, `docs/scope.md` og ADR-0009 giver nu authority til at fortsætte det
dependency-ordered v1 roadmap. Roadmappet skal:

1. mappe hvert kendt v1-gap til et ADR-0008 milestone og exit criterion;
2. oprette research/decision work før implementation, hvor semantics eller
   technology endnu ikke er accepteret;
3. gøre dependencies eksplicitte med `Blocked by #...` / `Blocks #...`;
4. holde implementation issues blocked, indtil deres nødvendige decisions og
   prerequisites er resolved;
5. holde hver implementation som én bounded, validerbar slice.

Architecture-model research og technology selection er nu afsluttet. Den næste
bounded architecture-slice er migrationen til den ADR-0009-valgte Structurizr
DSL-model. Architecture/documentation consolidation følger separat efter
migrationen.

De øvrige roadmap-områder omfatter input-artifact references,
workflow-semantics, registry-audit, target preservation og consumer acceptance.

Indtil migrationens atomiske authority-cutover er merged, gælder den nuværende
PlantUML authority fortsat operationelt.

## Accepted architecture-model decision

ADR-0009 selects Structurizr DSL as the v1 canonical architecture-model
technology.

The accepted target authority is:

```text
docs/architecture/workspace.dsl
```

with local included `.dsl` fragments as part of the same workspace.

The decision does not itself perform the migration. Until a migration PR creates
and validates that workspace and updates authority references atomically, the
current ADR-0003 PlantUML sources remain the operational architecture authority.

The migration will use pinned Structurizr vNext validation through an official
Docker image pinned by digest. Docker is admitted only as documentation
build/validation tooling and does not enter the compiler/runtime dependency
boundary.

Native Structurizr browser/Playwright image export is not part of the accepted v1
rendering boundary. If committed SVG remains required, PlantUML may remain only
as a derived, reproducible rendering stage.

The next architecture action is therefore a bounded implementation issue for
the architecture-model migration. General architecture/documentation
consolidation remains a separate subsequent slice.

## Autoritativ arkitektur

ADR-0009 er accepteret, men architecture-model migrationen er endnu ikke
gennemført. Indtil migrationens atomiske authority-cutover etablerer og
validerer `docs/architecture/workspace.dsl`, er den operationelle architecture
authority fortsat:

- `docs/architecture.md`
- `docs/core-domain-model.md`
- `docs/adr/`
- `docs/diagrams/domain/agentic-domain-overview.puml`
- `docs/diagrams/domain/setup-selection-chen.puml`
- `docs/diagrams/domain/workflow-control-chen.puml`
- `docs/diagrams/domain/agent-composition-chen.puml`
- `docs/diagrams/domain/capabilities-artifacts-targets-chen.puml`

De detaljerede PlantUML-kilder er fortsat operationelt autoritative for deres
respektive bounded contexts frem til cutover. Ved cutover bliver den validerede
Structurizr-workspace den eneste semantiske architecture-model authority, og
PlantUML kan kun bevares som afledt rendering-input.

Committed SVG-filer er stakeholder-facing derived output og skal forblive
canonical med de accepterede pinnede rendering-inputs, så længe den nuværende
afledte rendering-pipeline anvendes.
