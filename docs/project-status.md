# Projektstatus — `agentic-workflow-generator`

Opdateret: 18. august 2026

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
- Workflow-gaten ejer canonical required test-evidence categories, når den kræver
  `TestReport`.
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
- canonical input-artifact reference semantics via ADR-0010 og bounded end-to-end implementation i registry, validation, canonical compilation, active configuration og begge nuværende targets;
- canonical workflow routing semantics via ADR-0011 og bounded end-to-end
  implementation i typed domain, schemas, registry, validation, canonical
  compilation og begge nuværende targets;
- canonical workflow test-evidence semantics via ADR-0012 og bounded end-to-end
  implementation i typed domain, schemas, registry, validation, canonical
  compilation, active configuration og begge nuværende targets;
- Python/uv-baseret obligatorisk toolchain uden Node/npm-krav;
- canonical Structurizr DSL architecture-model med repository-owned validation
  og reproducible stakeholder-SVG rendering;
- Goal #50 canonical V1 target preservation accepteret på `development` ved
  `68951d38788df6379f9c35df470de79884015b81` gennem PR #75, med generaliseret
  all-bundle, both-target evidence for applicable canonical semantics;
- Goal #51 consumer acceptance and release readiness accepteret på den endelige
  validerede Milestone-5 integration-state ved
  `80f86b5a2b74f4d3d0930bb44a433087e790d976`, med clean-consumer evidence for
  initialization, compilation, validation, materialization, repeat execution,
  generated-state ownership og fail-closed representative invalid input.

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

Milestone 4, canonical target preservation, er gennemført og accepteret gennem
Goal #50 på `development` ved
`68951d38788df6379f9c35df470de79884015b81`. Milestone 5 consumer acceptance
og release readiness er gennemført gennem Goal #51 med final repository-wide
validation grøn på `development` ved
`80f86b5a2b74f4d3d0930bb44a433087e790d976`. Milestone 6 controlled evolution
er det eneste resterende v1-milestone.

## Kendte v1-gaps

### Artifact contracts

ADR-0010 input-artifact reference semantics er implementeret end to end som en
statisk compiler-ejet kontrakt. Role bindings deklarerer eksplicitte governed
inputs, validering fejler lukket, `CompiledComposition` bevarer resolved producer
identity, active configuration serialiserer den canonical relation, og begge
nuværende targets bevarer samme semantics.

Der er ikke et kendt resterende v1-gap i den bounded ADR-0010 implementation.

### Workflows

ADR-0011 definerer canonical workflow routing semantics: `PASS`, `FAIL` og
`BLOCKED` er de eneste routable gate results, hver ikke-terminal state skal have
én eksplicit route for hvert resultat, `BLOCKED` routes eksplicit til
`defaultFailureState`, og workflow-controlleren er den eneste route-selector.

Den bounded ADR-0011 routing-implementation er gennemført end to end. Den typed
transition-model bruger den lukkede `PASS`/`FAIL`/`BLOCKED` vocabulary, alle
ikke-terminale states har total eksplicit routing, canonical serialization er
deterministisk, og begge targets bevarer controller-only route-selection uden
state-owner-owned transition handoffs.

ADR-0012 canonical workflow test-evidence semantics er implementeret end to end.
Hver `TestReport`-gate ejer en non-empty canonical `requiredTestEvidence` set med
den lukkede vocabulary `changed-behavior-tests` og
`project-validation-suite`. Parser, semantic validation, bundle projection,
`CompiledWorkflowGate`, active config `0.11.0` og begge nuværende targets
bevarer den komplette semantik deterministisk. Targets repræsenterer category
meaning, requiredness, reproducible `TestReport`
`claim`/`source`/`reproduction`/`result` evidence, statuskonsekvenser,
static/runtime boundary og controller-only routing uden test discovery eller
prose inference.

ADR-0013 bounded canonical AI-evaluation execution semantics er implementeret
end to end gennem den eksisterende target-preservation path. Begge nuværende
targets bevarer de tre gate-required AI-evaluation capabilities som canonical
required evaluation dimensions fra compiled gate data, de governed
`Requirements`- og `ImplementationReport`-inputs, `AIEvaluationReport` som sole
evidence/status authority, den effektive read-only / no-shell permission boundary
og ADR-0011 controller-only routing. Targetrendering fejler lukket ved manglende
eller svækket statisk preservation, mens manglende eller unverificerbar runtime
evidence fortsat giver `BLOCKED` frem for `PASS`. Compileren parser ikke produced
artifact Markdown eller project content og udfører ikke evaluation jobs eller
modelinvokation.

Retry, escalation og artifact invalidation er ikke v1-krav og er ikke accepteret
scope.

### Profiles, bundles og setups

Goal #48 registry-honesty arbejdet er gennemført på `development`. Den accepterede
registry er auditeret mod materialiseret adfærd; de identificerede no-effect
guided setupvalg og stale claims er fjernet; required capability coverage er
komplet; advisory profile-felter fungerer ikke som implicit runtime authority;
og klassifikationer matcher den composition, compileren faktisk materialiserer.

ADR-0014 fastlægger desuden artifact content-production/materialization-boundary.
Begge nuværende targets bevarer nu eksplicit, at `produces` ejer komplet governed
artifact content og klassifikation uden at udvide effective permissions.
Read-only producers bruger mediated target/framework handoff til materialisering,
conversation-only content er ikke materialized governed input, downstream
consumption kræver materialized/readable availability, og materialization failure
forbliver fail-closed uden at gøre workflow-controlleren til artifact writer.

Der er ikke et kendt resterende v1-gap i den bounded registry-honesty scope.

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

Goal #51 consumer acceptance and release readiness er gennemført på den
accepterede Milestone-5 integration-state. Den version-controlled clean-consumer
acceptance evidence beviser:

- clean initialization for den accepterede bundle/setup matrix;
- deterministic active configuration og canonical compiler-input lock state;
- canonical materialization og generated-state/output-manifest validation for
  begge nuværende targets;
- repeat execution uden drift eller unmanaged target-owned output;
- fail-closed rejection af en repræsentativ strukturelt incomplete active
  composition uden fallback, silent repair eller accepteret downstream generated
  state;
- full repository validation på den endelige accepterede integration-state.

Historiske test counts er fortsat ikke release criterion.

## Næste prioritet

Goal #50 canonical V1 target preservation er gennemført og accepteret på
`development` ved `68951d38788df6379f9c35df470de79884015b81` gennem PR #75.
Goal #51 consumer acceptance and release readiness er ligeledes gennemført med
final repository-wide validation grøn på den accepterede Milestone-5 state ved
`80f86b5a2b74f4d3d0930bb44a433087e790d976`.

Den næste planning workstream er Goal #52 controlled evolution. Goal #52 skal
re-reades mod current `development` og promoveres/dekomponeres gennem normal
issue/readiness-flow før executable work autoriseres. V1 er endnu ikke complete,
fordi Milestone 6 fortsat mangler acceptance.

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
