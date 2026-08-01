# Projektstatus — `agentic-workflow-generator`

Opdateret: 1. august 2026

Denne fil er projektets autoritative aktuelle status.

Accepteret scope ejes af `docs/scope.md`.
Leveranceregler og governance ejes af `docs/governance.md`.
Arkitektur ejes af `docs/architecture.md` og de deri udpegede autoritative diagramkilder.

Historiske migrationsdetaljer bevares i Git-historikken og må ikke bruges som konkurrerende projektstatus.

## Slutmål

`agentic-workflow-generator` skal være en deterministisk, fail-fast compiler, der omsætter en valideret og genanvendelig registry-komposition til et komplet target-specifikt agentisk udviklingsmiljø.

Målflowet er:

~~~text
validated registry
      ↓
setup eller bundle
      ↓
agent instances og role bindings
      ↓
CompiledComposition
      ↓
.agentic/agentic.json
      ↓
compiler-input lockfile
      ↓
target-specific output
      ↓
output manifest
      ↓
validation
~~~

Projektet genererer og validerer agentiske udviklingsmiljøer.

Det er ikke en modelhost, autonom runtime-orchestrator eller erstatning for de frameworks, som output genereres til.

## Aktuel fase

**Post-migration hardening**

Den atomiske migration fra den tidligere statiske agentmodel og scriptbaserede orchestration til den typed `AgentInstance` / `RoleBinding`-arkitektur er afsluttet.

Den aktive implementation anvender én canonical `CompiledComposition`, typed application- og CLI-lag og det installerede `agentic-workflow-generator`-entrypoint.

Der findes ikke længere et separat resolutionlag eller aktiv compiler-orchestration under `scripts/agentic`.

## Aktuel implementeret model

Følgende er implementeret og accepteret:

- 8 genanvendelige agentprofiler.
- 10 skills med 21 registrerede capabilities.
- 4 workflows med eksplicitte gates og fail-closed routing.
- 4 profiles.
- 4 bundles.
- 27 agent instances.
- 27 role bindings.
- eksplicitte separation policies.
- 4 guided setups med 12 spørgsmål.
- 3 permission profiles.
- 7 artifact contracts.
- 2 target adapters:
  - `vscode-copilot`
  - `opencode`
- typed registry-loading og immutable domænemodeller.
- typed schema- og semantic validation.
- canonical `CompiledComposition`.
- typed initialization og guided initialization.
- `.agentic/agentic.json` som aktiv persistent composition.
- typed lockfile-generation og validation.
- typed targetrendering og transaktionel materialisering.
- canonical output manifest.
- generated-output validation.
- generation- og init-idempotency validation.
- typed top-level CLI.
- fail-fast diagnostics med stabile diagnostic-koder.
- fokuserede unit-, contract-, negative-, integration- og end-to-end-tests.

## Arkitekturinvarianter

Den accepterede implementation følger disse hårde regler:

- `CompiledComposition` er compilerens eneste canonical interne composition.
- `.agentic/agentic.json` er den persistente aktive serialisering.
- Bundles ejer konkrete agent instances og role bindings.
- Agentprofiler og profiles er rådgivende og må ikke fungere som runtime fallback.
- Hver ikke-terminal workflow-state har præcis én state-owner-binding.
- Hvert workflow har præcis én controller-binding.
- Controlleren ejer routing men ingen workflow-state eller gate.
- Effective permissions tilhører agent instances.
- Concrete capabilities, skills, artifacts, responsibilities og guardrails tilhører role bindings.
- Targetrenderere anvender canonical typed composition og må ikke genfortolke raw registry.
- Lockfile ejer compiler-input provenance.
- Output manifest ejer generated-output provenance og integritet.
- Generation er deterministisk og idempotent.
- Manglende eller ugyldige inputs, references, tools og outputs fejler eksplicit.
- Der findes ingen compatibility projection, silent degradation eller fallback authority.

Ændring af disse regler kræver en eksplicit scope- og arkitekturbeslutning.

## Seneste validerede baseline

Den afsluttede typed top-level CLI-migration blev valideret med:

~~~text
pytest
  PASS: 856 tests

Ruff
  PASS

strict mypy
  PASS: 206 source files

typed all-pipeline
  PASS
  165 compiler inputs

doctor-strict
  PASS på rent working tree
~~~

Denne baseline er historisk evidens for den senest afsluttede hovedleverance.

Nye ændringer skal valideres på deres egen branch og må ikke antage, at denne baseline automatisk gælder efter senere ændringer.

## Governance

Projektet anvender nu governed project delivery.

Permanent branch-semantik:

~~~text
main = stable/release
dev  = integration
~~~

Normalt arbejde følger:

~~~text
dev
 ↓
topic branch
 ↓
validation
 ↓
pull request
 ↓
review
 ↓
squash merge
 ↓
dev
~~~

Scope, status, arkitektur og implementation er separate autoritative concerns.

Chat-historik, AI-samtaler og lokale antagelser er ikke projektets source of truth.

CI validerer pushes og pull requests mod både `dev` og `main` med den eksisterende
`doctor-strict`-gate. GitHub-hosted runners installerer en eksplicit pinned
`uv`-version før validering.

## Kendte gaps

### Artifact contracts

Den eksisterende artifact-model mangler fortsat fuldt defineret semantik for:

- provenance;
- revision;
- statusafhængige invariants;
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

Registry-indholdet kræver fortsat audit og hardening:

- stale tekst skal fjernes;
- capability completeness skal kontrolleres;
- placebo-lignende setupvalg skal fjernes eller gøres materielle;
- classifications skal svare til den composition, der faktisk materialiseres;
- generalist- og specialistkompositioner skal være tydelige.

### Testkvalitet

Den samlede testsuite har kendt duplicate-code-gæld.

Denne gæld skal reduceres uden at:

- deaktivere Pylint-regler;
- svække assertions;
- samle tests i nye monolitiske helpers;
- skjule reel duplication gennem exclusions.

## Næste prioritet

Når governance-ændringen er merged til `dev`, er næste accepterede leverance:

**Artifact contract hardening**

Arbejdet skal starte som en ny topic branch fra den opdaterede `dev` og afgrænses til den mindste sammenhængende artifact-contract-slice.

Før implementation skal den konkrete slice definere:

- hvilket artifact-problem der løses;
- hvilke contracts og schemas der berøres;
- hvilke invariants der tilføjes;
- hvilke tests der beviser semantikken;
- hvilke relaterede ændringer der eksplicit er uden for slicen.

Workflow-, setup- eller targetarbejde må ikke blandes ind i samme PR, medmindre det er strengt nødvendigt for artifact-kontraktens accepterede end-to-end-semantik.

## Autoritativ arkitektur

Arkitekturprincipper:

- `docs/architecture.md`

Core domain documentation:

- `docs/core-domain-model.md`

Navigationsdiagram:

- `docs/diagrams/domain/agentic-domain-overview.puml`

Autoritative bounded-context-diagrammer:

- `docs/diagrams/domain/setup-selection-chen.puml`
- `docs/diagrams/domain/workflow-control-chen.puml`
- `docs/diagrams/domain/agent-composition-chen.puml`
- `docs/diagrams/domain/capabilities-artifacts-targets-chen.puml`

De detaljerede PlantUML-kilder er autoritative for entities, relationships og cardinalities i deres respektive bounded contexts.

Renderede SVG-filer skal holdes synkroniseret med deres autoritative kilder.
