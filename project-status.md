# Projektstatus — `agentic-workflow-generator`

Opdateret: 26. juli 2026

Denne fil er projektets autoritative status og roadmap. Den skal kun indeholde den aktuelle tilstand, afsluttede hovedleverancer, kendte mangler og næste prioriterede arbejde.

## Slutmål

`agentic-workflow-generator` skal være en deterministisk, fail-fast compiler, der kan omsætte en valideret og genanvendelig registry-komposition til et komplet, target-specifikt agentisk udviklingsmiljø.

En bruger skal kunne vælge et setup eller et bundle og uden manuel efterredigering få genereret agenter, skills, workflows, permissions, handoffs, artifact-kontrakter og targetkonfiguration, som er konsistente med hinanden og kan anvendes direkte i det valgte framework.

Projektet betragtes som færdigt, når følgende er opfyldt:

* Registry-modellen understøtter genanvendelige agentprofiler, konkrete agent-instances, role bindings, separation policies, capabilities, skills, artifact contracts, workflows, permission-profiler og target adapters.
* Den samme registry kan sammensætte både kompakte generalistsetups og specialiserede teams uden at svække sikkerhedsinvarianter eller kræve duplikerede agentdefinitioner.
* Setup vælger et bundle og aktive targets. Det valgte bundle ejer alle øvrige konkrete runtimevalg, herunder profile, workflow, agent-instances, roller, skills, capabilities, permissions, artifacts og krav om separation of duties.
* Alle workflows er fail-closed og har entydige state owners, controller-binding, transitions, gates, evidenskrav, `BLOCKED`-routing samt definerede retry- og eskalationsgrænser.
* Artifact contracts kan validere status, provenance, revision, inputreferencer og reproducerbar evidens ved workflow-gates.
* Genereret output bevarer den fulde semantik fra registryet og er gyldigt, konsistent og operationelt anvendeligt for hvert understøttet target.
* Init, resolution, generation, lockfile og manifest er deterministiske, idempotente og byte-identiske ved gentaget kørsel med samme input.
* Ugyldige registries, usikre kompositioner, manglende bindings og outputdrift afvises eksplicit uden fallback eller silent degradation.
* Alle registrerede setups kan initialiseres og genereres fra et tomt, isoleret consumer-repository og bestå schema-, semantic-, compatibility-, runtime- og negative-gate-tests.
* Nye agents, skills, workflows, artifacts, setups, bundles, profiles og targets kan tilføjes gennem dokumenterede kontrakter uden ændringer i compilerens kerne, medmindre et nyt domænekoncept introduceres.
* Dokumentation, schemas, validators, genereret output og `project-status.md` beskriver den samme implementerede model.

Projektets mål er at generere og validere agentiske udviklingsmiljøer. Det er ikke i sig selv en modelhost, en autonom runtime-orchestrator eller en erstatning for de frameworks, som outputtet genereres til.

## Aktuel status

Projektet er i gang med en atomisk breaking migration fra den tidligere statiske agentmodel til den autoritative `AgentInstance`- og `RoleBinding`-model.

Registrydata, registry-schemaer og de semantiske validator-slices for permissions, agents, skills, artifacts, workflows, bundles, profiles, setups og materialiserede setup-profiler er migreret. Den typed, side-effect-free setupmaterialiseringsservice og guided-init application service er implementeret og integreret med alle fire virkelige setup-registryfiler. Runtime-schema, bundle-init, resolution, targetgenerering og flere downstream-consumers anvender fortsat legacy-modellen.

Repositoryet er derfor fortsat bevidst ikke globalt green. Den dokumenterede compilerarkitektur og den nye testarkitektur anvendes nu til kontrollerede vertikale migrations-slices uden compatibility projection eller fallback.

Målflowet er:

~~~text
registry
→ setup eller bundle
→ agent instances og role bindings
→ compiled composition
→ agentic.json
→ resolution
→ lockfile
→ target-output
→ output manifest
→ validering
~~~

### Implementeret på migrationsbranchen

* 8 agentprofiler er migreret til version `0.2.0`.
* Agentprofiler indeholder kun rådgivende responsibilities, guardrails, capabilities og default permission.
* 4 workflows er migreret til version `0.2.0`.
* Workflow-states indeholder ikke længere konkrete agenter.
* Workflow-gates ejer eksplicit required capabilities og required artifacts.
* `defaultFailureRoute` er fjernet og erstattet af `defaultFailureState`.
* 4 bundles er migreret til version `0.2.0`.
* Bundles ejer konkrete `agentInstances`, `roleBindings` og `separationPolicies`.
* Role bindings ejer autoritative capabilities, valgte skills, producerede artifacts, responsibilities og guardrails.
* Hver agent-instance har én eksplicit effektiv permission-profil.
* Hvert bundle har én eksplicit workflow-controller-binding.
* De nuværende bundles kræver forskellige instanser for alle role bindings gennem en eksplicit separation policy.
* 3 permission-profiler og tilhørende schema og semantisk validator er implementeret.
* 8 agentprofiler og 10 skills har typed immutable domænemodeller, strikte schemaer og strukturerede semantiske validators.
* Permission-, agent-, skill-, artifact-, workflow-, bundle-, profile-, setup- og setup-profile-validatorerne er migreret til den nye Python-pakkearkitektur med typed immutable domænemodeller, stabile diagnostics og midlertidige tynde launchers.
* Validation-laget anvender fælles fail-fast support for schema diagnostics, registry-identiteter og legacy-schema-parse-pipelinen uden fallback eller parallel autoritet.
* CLI-laget anvender fælles diagnostic-rendering og et typed setup-validation context.
* Pylint duplicate-code er konfigureret som dev-gate og består med rating 10,00/10.
* Setup registry og setup profiles er migreret til version `0.2.0`.
* Setupvalg ejer kun `bundle` og `targets`; profile, workflow, agent-instances, role bindings, skills, capabilities, permissions og artifacts ejes af det valgte bundle.
* Legacyfelterne `defaultBundle`, `finalRecommendation`, question-level classification-lister, option `recommends` samt setup-profile-felterne `profile` og `workflow` er fjernet uden fallback.
* Den offentlige setup-registry-CLI validerer 4 setupfiler og 12 spørgsmål, og den materialiserede `.agentic/setup-profile.json` består den nye setup-profile-validator.
* Den typed setupmaterialiseringsservice producerer immutable `SetupProfile`-objekter, anvender answer overrides eller default options og afviser ukendte, blocked eller modstridende valg fail-fast.
* Den typed guided-init application service adskiller terminal-IO fra selection og materialisering, validerer før writes og bevarer back-navigation, cancellation, dry-run og transaktionel rollback.
* Alle fire setups materialiserer gyldige profiler med defaults, OpenCode-only og VS Code Copilot-only.
* `target-platforms` er nu den eneste spørgsmålsdimension, der ejer targetvalget; dobbelt target-autoritet er fjernet fra `project-domain` og `project-type`.
* Global capability coverage bruger nu `roleBindings[].requiredCapabilities` som autoritativt runtimekrav.
* Artifact-produktion valideres mod `roleBindings[].produces` i stedet for agentprofiler.
* Registry-schema-validation består for 46 registryfiler.
* De migrerede semantic validators består isoleret på den aktuelle registry.
* Legacy-felter afvises eksplicit i de migrerede schemaer og validators.

### Endnu ikke migreret eller afsluttet

* typed domain models og validators for targets
* migration af `init-from-bundle.py`, fuld bundlematerialisering og de resterende setup-relaterede init-consumers
* `agentic.schema.json` og den aktive runtimekonfiguration
* `validate-registry-references.py`
* resolution-format, resolver og resolution-validator
* lockfile-inputmodellen efter den endelige compilerstruktur
* OpenCode- og Copilot-generatorerne
* output manifest og target compatibility-validering
* generated-output-validering
* negative-gate-arkitekturen
* isolerede end-to-end- og target runtime-tests
* regenerering af alle `.agentic`- og targetfiler
* opdatering af arkitektur-, registry- og brugerdokumentation

Der indføres ingen compatibility projection, fallback eller parallel legacy-model. Hver migreret vertikal slice skal erstatte og fjerne den gamle implementation i samme ændring.

## Afsluttet

### Milepæl 1 — Guided init

Milepæl 1 er implementeret, valideret og pushed.

Færdige funktioner:

* interaktivt `init --guided`
* deterministisk `--guided --setup`
* answer overrides
* dry-run
* back-navigation
* cancellation uden filændringer
* transaktionel rollback
* PTY-regressionstests
* modulopdelt init-implementering
* fire reelle setups
* isoleret clean-consumer end-to-end-test

### Milepæl 2 — Første vertical slice

`ai-application` er implementeret med:

* `AIEvaluator`
* `ai-evaluation`
* `AIEvaluationReport`
* AI-profile
* AI-bundle
* AI-workflow
* AI-guided setup

### Target framework-kompatibilitet

Framework-auditten er implementeret og committed som:

~~~text
8e13da3 Validate target framework compatibility
~~~

Færdige forbedringer omfatter:

* gyldigt OpenCode-output
* OpenCode primary/subagent-topologi
* validerede OpenCode-permissions
* validerede Copilot-tools og native handoffs
* deterministisk skill-materialisering
* target compatibility-validator
* OpenCode runtime parsing
* runtime context eksplicit deaktiveret indtil senere milepæl

## Aktuel validering

### Seneste green baseline før migrationen

Følgende bestod før den aktuelle breaking migration:

~~~text
agentic-gen.sh all
  PASS
  10 skills
  21 capability providers
  8 agent profiles
  43 registry files

agentic-gen.sh test-isolated-e2e
  PASS for alle 4 setups
  222 kumulative deterministiske tracked files

agentic-gen.sh test-target-runtime-e2e
  PASS for alle 4 setups
  OpenCode runtime parser alle setups

agentic-gen.sh test-negative
  PASS: 373 negative gate tests

agentic-gen.sh validate-manifest
  PASS: 2 targets og 53 genererede filer

agentic-gen.sh doctor-strict
  PASS
  PASS: 373 negative gate tests
  PASS: Working tree is clean
~~~

OpenCode 1.17.10 parsede config, agents og skills for alle fire isolerede setups ved denne baseline.

### Aktuel migrationsstatus

Følgende validering er observeret grøn isoleret på den aktuelle migrationsbranch:

~~~text
validate-registry-schemas
  PASS: 46 registryfiler

validate-agents
  PASS: 8 agentprofiler
  PASS: 21 capability-referencer
  PASS: 3 permission-profiler

validate-skills
  PASS: 10 skill directories
  PASS: 21 capability providers
  PASS: 8 agent profiles

validate-artifacts
  PASS: 7 artifact contracts

dedikeret artifact-testpakke
  PASS: 35 tests
  PASS: 237 statements
  PASS: 66 branches
  PASS: 100 procent coverage

validate-workflows
  PASS: 4 workflows
  PASS: 23 gates

validate-profiles
  PASS: 4 profiles
  PASS: 27 recommended agent references
  PASS: 60 recommended capability references

dedikeret profile-testpakke
  PASS: 45 tests
  PASS: 229 statements
  PASS: 84 branches
  PASS: 100 procent coverage

validate-bundles
  PASS: 4 bundles
  PASS: 27 agent instances
  PASS: 27 role bindings
  PASS: 4 separation policies

dedikeret bundle-testpakke
  PASS: 86 tests
  PASS: 513 statements
  PASS: 174 branches
  PASS: 100 procent coverage

samlet migreret Python-pakke
  PASS: Ruff
  PASS: strict mypy for 129 source files
  PASS: 576 tests
  PASS: Pylint duplicate-code, rating 10.00/10
  Senest separat målte coverage-baseline:
    PASS: 2.999 statements
    PASS: 952 branches
    PASS: 100 procent coverage

validate-setups
  PASS: 4 setup files
  PASS: 12 questions

setup-registry testpakke
  PASS: 37 tests
  PASS: 276 statements
  PASS: 84 branches
  PASS: 100 procent coverage

validate-setup-profile
  PASS: .agentic/setup-profile.json
  PASS: schema version 0.2.0

setup-profile testpakke
  PASS: 25 tests
  PASS: 227 statements
  PASS: 62 branches
  PASS: 100 procent coverage

validate-permission-profiles
  PASS: 3 permission-profiler

coverage
  PASS: 21 required runtime capabilities
  PASS: 21 skill capabilities


skill legacy regression gates
  PASS: 16 tests

artifact legacy regression gates
  17 artifact-ejede gates er fjernet fra monolitten
  De dækkes nu af den isolerede artifact-testpakke

workflow legacy regression gates
  30 workflow-ejede tests og 31 helpers er fjernet fra monolitten
  De dækkes nu af den isolerede workflow-testpakke

Den fulde legacy-runner er ikke en migrationsgate
~~~

Den fulde `all`-, negative-gate-, idempotency- og end-to-end-pipeline betragtes ikke som grøn efter migrationen.

Den eksisterende negative-gate-runner er en monolit og flere tests starter hele `all`-pipelinen som fixture. Derfor kan en isoleret validator-test fejle på en senere stale compilerkomponent. Denne testarkitektur skal ændres, før den bruges som migrationsstyring.

Den tidligere green baseline dokumenterer kun den gamle model og må ikke bruges som evidens for den nye model.

## Aktuel repositorytilstand

Seneste green commit på `main` før migrationen:

~~~text
79bfe7c Harden registry skills and document agent instance model
~~~

Det aktuelle working tree indeholder en stor, ikke-committed breaking migration.

Auditten den 24. juli 2026 viste:

~~~text
45 ændrede eller nye filer
7.462 tilføjede linjer
3.000 fjernede linjer
24 validator-scripts
9.314 linjer i test-negative-gates.py
509 funktioner i test-negative-gates.py
ingen pytest-, ruff-, mypy- eller coverage-konfiguration
~~~

Auditten identificerede før de afsluttede validator-slices flere store legacy-komponenter. Permission-, agent-, skill-, artifact-, workflow-, bundle-, profile-, setup- og setup-profile-validatorerne er siden erstattet af pakkebaserede implementationer med tynde midlertidige launchers. Setupmaterialisering og guided init er flyttet til typed application services. Bundle-init, resolution, targetgenerering og pipeline-orchestrering forbliver endnu i legacy-strukturen.

Der findes omfattende duplikation af blandt andet:

* JSON-loading
* string- og list-validering
* registry-filopdagelse
* repository-relative path-sikkerhed
* hashing
* subprocess execution
* targetgenerering
* test-fixtures

Migrationen udføres på den pushede branch `refactor/validation-deduplication`. Branchen er sikret på origin, men er ikke klar til merge til `main`, før:

* compilerarkitekturen er dokumenteret
* refaktoreringen er opdelt i kontrollerede slices
* stale downstream-consumers er migreret
* legacy-kode er fjernet
* generated output er regenereret
* den fulde pipeline igen er grøn
* `project-status.md` og dokumentationen matcher implementationen

## Registry-audit — vigtigste fund

### Compiler- og testarkitektur

Registryets konceptuelle model er blevet stærkere, men kodebasen er ikke struktureret som en compiler.

Aktuelle problemer:

* næsten al Python-kode ligger fladt i `scripts/agentic/`
* `agentic-gen.sh` fungerer både som CLI-router og pipeline-orchestrator
* validators fortolker rå JSON uafhængigt af hinanden
* resolver og targetgeneratorer har egne modelantagelser
* validatorernes fælles schema-, identity- og pipeline-helpers er samlet under `validation/` og består duplicate-code-gaten
* negative gates er samlet i én fil på mere end 9.000 linjer
* komponenttests starter ofte hele pipelinen
* tests er primært koblet til fejltekst frem for stabile diagnostics
* der findes ingen tydelig dependency direction mellem CLI, application, domain, registry, compiler og targets
* `pytest`, Ruff, strict mypy, coverage og Pylint duplicate-code er konfigureret; legacy negative- og E2E-gates mangler fortsat migration

`registry/core` er tomt og skal ikke bruges som placering for Python-kode. Registryet forbliver deklarativt compiler-input.

Målkoden placeres under en rigtig Python-pakke. `scripts/agentic/agentic-gen.sh` må kun fungere som en midlertidig tynd launcher under migrationen og skal erstattes af pakkens offentlige Python-entrypoint.

Compiler- og validatorinfrastrukturen er stærk, men registry-indholdet er fortsat et MVP.

### Agents og skills

* `mvp-core-capabilities` er fjernet uden fallback.
* 10 fokuserede skills leverer alle 21 registrerede capabilities med én entydig provider per capability.
* Requirements, Architecture, Implementation, Test, QA, Security, AI-evaluering, code review og workflow-routing har konkrete arbejdsmetoder og evidenskontrakter.
* Alle skill-poster bruger rådgivende `recommendedAgents`; feltet begrænser ikke kompositionen.
* Skill-afhængigheder udtrykkes med `requiresCapabilities` og valideres mod registrerede capability-providers.
* Skill-validatoren afviser ugyldige typer, tomme værdier, dubletter, manglende agent- og capability-referencer samt selvafhængighed.
* CodeReviewer må ikke eje routing, og Orchestratorens routing er fail-closed.

### Artifacts

Artifact contracts validerer struktur og headings, men mangler blandt andet:

* statusafhængige evidenskrav
* provenance og revision
* input-artifact-referencer
* reproducerbar evidens
* validerbar handoff- eller dispositionssemantik

### Kompositionsmigration — aktuel status

De tidligere statiske låse er fjernet fra agent-, workflow- og bundle-registryet:

* bundles indeholder ikke længere en statisk liste af agentprofiler
* workflow-states indeholder ikke længere et `agent`-felt
* agentprofiler ejer ikke længere konkrete runtime-capabilities
* agentprofiler ejer ikke længere artifact-produktion
* workflow-controlleren udledes ikke længere af `defaultFailureRoute`
* konkrete permissions er flyttet til agent-instances
* konkrete capabilities, skills, artifacts, responsibilities og guardrails er flyttet til role bindings

Legacy-antagelser findes fortsat i downstream-koden og skal fjernes helt fra:

* `setup_materializer.py`
* `guided_init.py`
* `init-from-bundle.py`
* `resolve-agentic-config.py`
* runtime-schemaet og den aktive konfiguration
* output-manifestet
* targetgeneratorerne
* generated-output validators
* negative gates
* end-to-end-tests
* genererede snapshots

Der må ikke tilføjes fallback til agentprofilernes anbefalinger. Profile defaults må kun anvendes, når bundleforfatteren eksplicit vælger og materialiserer dem som konkrete instance- eller bindingværdier.

Følgende sikkerhedsinvarianter forbliver hårde:

* fail-closed workflowudførelse
* kun validerede og entydige transitions
* præcis én state-owner-binding per ikke-terminal state
* præcis én controller-binding per workflow
* ingen controllerbinding med state- eller gate-ejerskab
* obligatoriske artifacts og evidens ved gates
* valgte skills skal være inkluderet i bundlet
* valgte skills skal dække bindingens krævede capabilities
* eksplicit separation of duties, når bundlet kræver uafhængighed
* ingen implicit fallback eller selvopfundne routes

### Workflows

Workflowmodellen mangler blandt andet:

* eksplicit `BLOCKED`-routing
* entydig Orchestrator/controller-semantik
* retry- og eskalationsgrænser
* artifact-invalidation efter ændringer
* klar test-evidens i review-heavy-flowet
* klar execution-model for AI-evaluering

### Profiles og setups

* Profile metadata er rådgivende, mens bundle er autoritativ for workflow og konkret runtimekomposition.
* Setup-schemaet og setup-profile-schemaet duplikerer ikke længere bundle-ejede profile-, workflow-, agent-, skill- eller artifactvalg.
* Den eksisterende legacy-materializer forventer fortsat de fjernede felter `defaultBundle`, `finalRecommendation` og option `recommends` og kan derfor ikke anvendes som den nye materialiseringsimplementation.
* `init-from-bundle.py` forventer fortsat `selected.workflow`, selv om setup-profilen nu kun indeholder `selected.bundle` og `selected.targets`.
* `orchestrated-delivery-greenfield` indeholder fortsat forældet tekst om, at et dedikeret review-heavy-workflow ikke er registreret.
* Flere compatible setupvalg ændrer kun klassifikation og begrundelse, men ikke den valgte bundlekomposition; dette skal vurderes som registry-indhold efter hardening-fasen.

### Targetmaterialisering

* Agenternes `responsibilities` forsvinder før targetgenerering.
* Generiske outputkrav matcher ikke de artifact-specifikke kontrakter.
* OpenCode materialiserer ikke den fulde workflow-routing til runtimefilerne.
* Copilot mangler eksplicitte `BLOCKED`-handoffs.
* TestRunner-permissions er forskellige mellem targets.
* Profile- og workflowidentitet bruges inkonsistent.

## Beslutninger

### Compiler architecture hardening

* Reaktiv fejl-for-fejl-patching af downstream-scripts er sat på pause.
* Architecture hardening er en nødvendig del af den igangværende migration og ikke en ny produktfeature.
* `docs/architecture.md` er autoritativ for compilerens kodearkitektur.
* Chen-modellen i `docs/diagrams/agentic-domain-model-chen.puml` er fortsat autoritativ for domæneentities og relationer.
* Python-kode skal flyttes til en pakke under `src/agentic_workflow_generator/`.
* Tests skal opdeles under `tests/unit`, `tests/contract`, `tests/integration`, `tests/negative` og `tests/e2e`.
* `scripts/agentic/agentic-gen.sh` er kun en midlertidig migrationslauncher, må ikke eje domæne- eller compilerlogik og skal fjernes sammen med resten af `scripts/agentic`, når pakkens CLI dækker den offentlige kontrakt.
* Registry-loading, diagnostics, JSON IO, path-sikkerhed og hashing skal have én implementation.
* Rå JSON dictionaries må kun være den eksterne grænse. Compilerens interne lag skal bruge typed modeller.
* Resolver og targets skal anvende den samme canonical compiled composition eller compiler-IR.
* Validatorer skal returnere strukturerede diagnostics med stabile fejlkoder.
* Unit- og negative tests skal kalde den relevante Python-komponent direkte.
* Kun egentlige integration- og E2E-tests må starte hele pipelinen.
* `test-negative-gates.py` skal opdeles og fjernes som monolit.
* Refaktoreringen udføres i vertikale slices.
* Hver slice skal fjerne den gamle implementation samtidig med, at den nye aktiveres.
* Der må ikke eksistere parallel gammel og ny implementation eller compatibility alias.
* Kvalitetsbaselinen er `pytest`, Ruff, strict mypy, coverage og Pylint duplicate-code.
* Nye features, setups og targets er sat på pause under hardening-fasen.

### Domæne- og kompositionsmodel

* `mvp-core-capabilities` er fjernet uden fallback.
* En capability betragtes kun som dækket, når dens skill har en reel arbejdsmetode og evidenskontrakt.
* Skills er komponerbare capability-providers og må ikke som standard hardlåses til bestemte agenter.
* Agentdefinitioner er genanvendelige standardprofiler, ikke komplette runtimeinstanser.
* `recommendedAgents` og profile defaults er kun rådgivende metadata.
* Setup- og bundlekompositionen ejer konkrete agent-instances, role bindings, capabilities, skills, permissions, artifacts og rollegrænser.
* `AgentProfile`, `AgentInstance`, `RoleBinding` og `SeparationPolicy` er adskilte koncepter.
* En agent-instance må bindes til flere workflowroller.
* Hver agent-instance har præcis én effektiv permission-profil.
* Hver ikke-terminal workflow-state har præcis én state-owner-binding.
* Hvert workflow har præcis én controller-binding uden state- eller gate-ejerskab.
* Uafhængighed håndhæves gennem eksplicitte separation policies.
* Skill-afhængigheder udtrykkes gennem `requiresCapabilities`.
* Profiles må anbefale workflows; bundlet vælger det effektive workflow.
* Capability coverage bruger autoritative runtimekrav fra role bindings.
* Artifact-produktion ejes af role bindings, ikke agentprofiler.
* Strukturel framework-kompatibilitet må ikke beskrives som fuld operationel runtime-kompatibilitet.

## Prioriteret arbejde

### Fase 0 — Compiler architecture hardening

#### 0.1 Dokumentér grænser og dependency rules — afsluttet

* `docs/architecture.md` beskriver package-struktur
* dependency direction og forbudte imports er fastlagt
* registryets rå JSON-grænse er fastlagt
* canonical compiled composition er defineret
* diagnostics og stabile fejlkoder er defineret
* teststrategi og fixtureprincipper er defineret
* vertikal migrationsstrategi er fastlagt
* kvalitets- og reviewkrav er fastlagt
* definition of done for architecture hardening er fastlagt

#### 0.2 Etablér fælles fundament — afsluttet

Implementeret:

* src-baseret Python-package med Hatchling
* ansvarsdelt teststruktur under `tests/`
* `pytest`, `pytest-cov`, `ruff` og strict `mypy`
* immutable `Diagnostic` og `Severity`
* valideret diagnostic-code-format
* eksplicit root-baseret `ProjectPaths`
* repository-relative og owned-root path-sikkerhed
* strukturerede infrastructure exceptions
* strict fail-fast JSON reader
* JSON-object root validation
* deterministisk JSON serialization
* atomiske byte-, tekst- og JSON-writes
* rå SHA-256 for bytes og filer
* eksplicit `RegistryKind` for alle registryområder
* kind-specifikke filpatterns og identity-felter
* immutable `RegistrySource`
* deterministic `RegistryLoader`
* source-path association
* fail-fast discovery af manglende roots, områder og filer
* `RegistryIndex` med entydig identity-lookup
* afvisning af manglende, tomme, utrimmende og duplikerede identities
* artifact discovery, som kun læser `artifact.json` og ikke artifact schemas

Typed domænemodeller tilføjes fremover kun i den vertikale slice, der konkret anvender dem.

Valideret:

~~~text
ruff format --check
  PASS: 24 files

ruff check
  PASS

mypy
  PASS: 24 source files

pytest
  PASS: 100 tests

coverage
  PASS: 375 statements
  PASS: 66 branches
  PASS: 100 procent
~~~

#### 0.3 Migrér validators i vertikale slices — i gang

Planlagt rækkefølge:

1. permissions — afsluttet
2. agents — afsluttet
3. skills — afsluttet
4. artifacts — afsluttet
5. workflows — afsluttet
6. bundles — afsluttet
7. profiles — afsluttet
8. setups og setup profiles — validator-slice afsluttet
9. typed setupmaterialisering — afsluttet
10. real-registry- og setup-profile-integration — afsluttet
11. guided init application service — afsluttet
12. resterende setup-relaterede init-consumers — næste
13. targets

Permission-profile-slicen omfatter nu:

* immutable `PermissionProfile`
* eksplicit `BashPermission`
* parsing fra `RegistrySource`
* JSON Schema Draft 2020-12-validering
* semantiske permission-invariants
* stabile `AWG-PERMISSION-*` diagnostics
* deterministisk diagnostic-rækkefølge
* unit-, contract-, negative- og integrationstests
* bevaret CLI-kommando `validate-permission-profiles`
* tynd launcher på den eksisterende scriptsti
* fuldstændig fjernelse af den gamle validatorimplementation
* eksplicit immutable-til-JSON boundary for eksterne biblioteker

Valideret:

~~~text
ruff format --check
  PASS: 48 files

ruff check
  PASS

mypy
  PASS: 48 source files

pytest
  PASS: 128 tests

coverage
  PASS: 530 statements
  PASS: 104 branches
  PASS: 100 procent

public CLI
  PASS: 3 permission profiles

legacy negative gates
  PASS: 4 permission-profile tests
~~~

Agent-profile-slicen omfatter nu:

* immutable `AgentProfile`
* eksplicit parsing fra `RegistrySource`
* JSON Schema Draft 2020-12-validering
* særskilte diagnostics for legacyfelter
* folder- og identitetsvalidering
* unikke agentnavne
* eksplicit projektion af skill-capabilities
* eksplicit projektion af permission-profile-identiteter
* referencevalidering uden at overtage skill- eller permission-semantik
* stabile `AWG-AGENT-*` diagnostics
* deterministisk diagnostic-rækkefølge
* unit-, contract-, negative- og integrationstests
* bevaret CLI-kommando `validate-agents`
* tynd launcher på den eksisterende scriptsti
* fuldstændig fjernelse af den gamle agent-validatorimplementation
* fortsat forbud mod legacyfelter som `produces`

Valideret:

~~~text
ruff format --check
  PASS: 59 files

ruff check
  PASS

mypy
  PASS: 59 source files

pytest
  PASS: 186 tests

coverage
  PASS: 748 statements
  PASS: 182 branches
  PASS: 100 procent

public CLI
  PASS: 8 agent profiles
  PASS: 21 skill capability references
  PASS: 3 permission profiles

legacy negative gates
  PASS: 8 agent-registry tests
~~~

Skill-slicen omfatter nu:

* immutable `Skill` og `SkillContextBudget`
* eksplicit parsing fra `RegistrySource`
* strikt JSON Schema Draft 2020-12-kontrakt uden capability-aliases
* særskilte diagnostics for legacyfelter
* folder- og identitetsvalidering
* unikke skillnavne og globale capability-providers
* deterministisk capability-provider-projektion
* validering af `requiresCapabilities` uden selvafhængighed
* rådgivende `recommendedAgents` valideret mod agentidentiteter
* eksplicit validering af sikre og eksisterende content paths
* referencevalidering uden at overtage agent-, bundle-, workflow- eller targetsemantik
* stabile `AWG-SKILL-*` diagnostics
* deterministisk diagnostic-rækkefølge
* unit-, contract- og integrationstests
* bevaret CLI-kommando `validate-skills`
* tynd launcher på den eksisterende scriptsti
* fuldstændig fjernelse af den gamle skill-validatorimplementation
* fortsat forbud mod capability-aliases og parallel autoritet

Valideret:

~~~text
ruff format --check
  PASS: 67 files

ruff check
  PASS

mypy
  PASS: 67 source files

pytest
  PASS: 234 tests

coverage
  PASS: 982 statements
  PASS: 260 branches
  PASS: 100 procent

dedikeret skill-testpakke
  PASS: 48 tests
  PASS: 100 procent statement- og branch coverage

public CLI
  PASS: 10 skill directories
  PASS: 21 capability providers
  PASS: 8 agent profiles

legacy negative gates
  PASS: 16 skill-registry tests
~~~

Artifact-slicen omfatter nu:

* immutable `ArtifactContract` og `ArtifactStatus`
* eksplicit parsing fra `RegistrySource`
* strikt JSON Schema Draft 2020-12-kontrakt
* obligatorisk semantisk version, description, path pattern, status og headings
* særskilte diagnostics for legacyfelter
* folder- og artifact-identitetsvalidering
* unikke artifact-identiteter
* validering af status-regex og sammenhæng med allowed statuses
* validering af status-heading mod required headings
* deterministisk projektion af de syv genererede artifact-schemaer
* validering af manglende, orphaned og driftede genererede schemaer
* stabile `AWG-ARTIFACT-*` diagnostics
* deterministisk diagnostic-rækkefølge
* unit-, negative- og integrationstests
* bevaret CLI-kommando `validate-artifacts`
* tynd midlertidig launcher på den eksisterende scriptsti
* fuldstændig fjernelse af den gamle artifact-validatorimplementation
* fortsat forbud mod `binding`, `producedBy`, `required`, aliases og fallback
* eksplicit afgrænsning: workflow-gates ejes af workflow-slicen, og artifact-produktion ejes af bundle-kompositionen

Valideret:

~~~text
dedikeret artifact-testpakke
  PASS: 35 tests
  PASS: 237 statements
  PASS: 66 branches
  PASS: 100 procent coverage

public CLI
  PASS: 7 artifact contracts

registry schema validation
  PASS: 46 registryfiler

legacy negative gates
  17 artifact-ejede tests er fjernet fra test-negative-gates.py
  De tilsvarende cases dækkes af den isolerede artifact-testpakke
~~~

Den fulde legacy negative-gate-runner blev ikke gjort til artifact-slicens gate. Den starter stale downstream-targetgeneratorer, som fortsat forventer det fjernede `workflow.states[].agent`-felt.

Workflow-slicen omfatter nu:

* immutable `Workflow`, `WorkflowState`, `WorkflowGate` og `WorkflowTransition`
* eksplicit parsing fra `RegistrySource`
* strikt JSON Schema Draft 2020-12-kontrakt
* særskilte diagnostics for workflow-, state- og gate-legacyfelter
* filnavns- og workflow-identitetsvalidering
* unikke workflow-, state- og gate-identiteter
* semantisk krav om `failClosed=true`
* validering af start state, terminal states og default failure state
* validering af transition-kilder, transition-mål og terminale states uden outgoing transitions
* case-insensitive entydighed for events per source state
* krav om outgoing transitions fra alle ikke-terminale states
* reachability fra start state
* krav om, at alle states kan nå en terminal state
* projektion af skill-capabilities uden overtagelse af skill-semantik
* projektion af artifact-statusser uden overtagelse af artifact-semantik
* validering af gate-capabilities og gate-artifacts mod registrerede referencer
* validering af transition-events mod required artifact-statusser
* stabile `AWG-WORKFLOW-*` diagnostics
* deterministisk diagnostic-rækkefølge
* unit-, edge-case-, CLI- og integrationstests
* bevaret offentlig CLI-kommando `validate-workflows`
* tynd midlertidig launcher på den eksisterende scriptsti
* fuldstændig erstatning af den 778-linjers legacy workflow-validator
* eksplicit afgrænsning: state-owner- og controller-bindings forbliver bundle-ejet
* fortsat forbud mod genindførelse af `workflow.states[].agent`

Valideret:

~~~text
dedikeret workflow-testpakke
  PASS: 63 tests
  PASS: 375 statements
  PASS: 156 branches
  PASS: 100 procent coverage

public CLI
  PASS: 4 workflow files
  PASS: 23 gates
  PASS: 21 skill capability references
  PASS: 7 artifact contracts

legacy negative gates
  30 workflow-ejede tests er fjernet fra test-negative-gates.py
  31 workflow-ejede mutationshelpers er fjernet
  De tilsvarende cases dækkes af den isolerede workflow-testpakke
~~~

Stale downstream-forbrug af det fjernede `workflow.states[].agent`-felt findes fortsat i init-, resolution- og targetlagene. De må ikke repareres med compatibility projection i workflow-slicen.

Bundle-slicen omfatter nu:

* immutable `Bundle`, `AgentInstance`, `RoleBinding` og `SeparationPolicy`
* eksplicit parsing fra `RegistrySource`
* strikt JSON Schema Draft 2020-12-kontrakt
* validering af bundle-, instance-, binding- og separation-policy-identiteter
* validering af profile-, workflow-, agent-, permission-, skill-, capability-, artifact- og targetreferencer
* præcis én workflow-controller-binding per bundle
* præcis én state-owner-binding per ikke-terminal workflow-state
* forbud mod controllerbindinger med state-, gate- eller artifact-ejerskab
* validering af valgte skills og deres capability-afhængigheder
* validering af workflow-gates mod bindingens krævede capabilities og producerede artifacts
* autoritativ artifact-produktion gennem `roleBindings[].produces`
* globalt krav om mindst én producent for hvert registreret artifact contract
* eksplicit separation of duties gennem forskellige agent-instances
* stabile `AWG-BUNDLE-*` diagnostics
* deterministiske dependency-projektioner
* unit-, projection-, CLI- og semantiske tests
* bevaret offentlig CLI-kommando `validate-bundles`
* tynd midlertidig launcher på den eksisterende scriptsti
* fuldstændig erstatning af den 1.085-linjers legacy bundle-validator
* fuldstændig fjernelse af den separate `validate-artifact-production.py`
* fortsat forbud mod legacyfeltet `agents`, aliases, fallback og parallel autoritet

Valideret:

~~~text
dedikeret bundle-testpakke
  PASS: 86 tests
  PASS: 513 statements
  PASS: 174 branches
  PASS: 100 procent coverage

samlet migreret Python-pakke
  PASS: 470 tests
  PASS: 2.344 statements
  PASS: 740 branches
  PASS: 100 procent coverage

public CLI
  PASS: 4 bundle files
  PASS: 27 agent instances
  PASS: 27 role bindings
  PASS: 4 separation policies

registry schema validation
  PASS: 46 registryfiler

legacy negative gates
  23 bundle-ejede semantic gates er fjernet
  2 bundle-ejede schema gates er fjernet
  5 fælles bundle-mutationshelpers er fjernet
  Den separate artifact-production-validator og dens 5 legacy-gates er fjernet
  De tilsvarende kontrakter dækkes af den isolerede bundle-testpakke
~~~

Target-permission mapping, profile-workflow-anbefalinger, setupmaterialisering, resolveren og targetgeneratorerne forbliver downstream-ejede og blev ikke flyttet ind i bundle-validatoren.

Profile-slicen omfatter nu:

* immutable `Profile`
* eksplicit parsing fra `RegistrySource`
* strikt JSON Schema Draft 2020-12-kontrakt
* eksplicit `recommendedWorkflow` som rådgivende metadata
* validering af profile-identitet og unikke profilenavne
* deterministiske projektioner af workflow-, agent- og skill-capability-referencer
* validering af anbefalede workflows, agents og capabilities
* stabile `AWG-PROFILE-*` diagnostics
* deterministisk diagnostic-rækkefølge
* unit-, edge-case-, contract-, CLI- og integrationstests
* bevaret offentlig CLI-kommando `validate-profiles`
* tynd midlertidig launcher på den eksisterende scriptsti
* fuldstændig erstatning af den gamle profile-validator
* eksplicit test af, at profile-anbefalingen ikke begrænser bundlets effektive workflow
* fortsat forbud mod legacyfeltet `workflow`, aliases, fallback og parallel runtimeautoritet

Valideret:

~~~text
dedikeret profile-testpakke
  PASS: 45 tests
  PASS: 229 statements
  PASS: 84 branches
  PASS: 100 procent coverage

public CLI
  PASS: 4 profile files
  PASS: 27 recommended agent references
  PASS: 60 recommended capability references

registry schema validation
  PASS: 46 registryfiler

legacy negative gates
  12 direkte profile-gates er fjernet
  Den forældede profile/workflow-mismatch-gate er fjernet
  De tilsvarende kontrakter dækkes af den isolerede profile-testpakke og bundle-kontrakttesten
~~~

Profile metadata er rådgivende. Bundlet ejer fortsat det effektive workflow og alle konkrete runtimevalg. Setupmaterialisering, resolver og targets blev ikke repareret med compatibility projection i profile-slicen.

Setup- og setup-profile-slicen omfatter nu:

* immutable `Setup`, `SetupQuestion`, `SetupOption`, `SetupSelection`, `SetupProfile`, `SetupAnswer` og `SetupPolicy`
* strikte setup- og setup-profile-schemaer i version `0.2.0`
* setupvalg begrænset til bundle og targets
* inline option-classification som `recommended`, `compatible` eller `blocked`
* deterministiske selection patches fra `defaultSelection` og valgte options
* eksplicit projektion af bundleidentiteter, bundle-targets og registrerede targets
* validering af identiteter, spørgsmål, default options, blocked options, duplikater og referencer
* validering af materialiserede answers, classification, reason, selection conflicts og selected drift
* stabile `AWG-SETUP-*` og `AWG-SETUP-PROFILE-*` diagnostics
* offentlige CLI-kommandoer for setup registry og materialiseret setup profile
* tynde midlertidige launchers på de eksisterende scriptstier
* fuldstændig erstatning af den 680-linjers setup-validator og den 963-linjers setup-profile-validator
* fortsat forbud mod `defaultBundle`, `finalRecommendation`, `recommends`, profile/workflow-duplikation, aliases og fallback

Valideret:

~~~text
setup-registry testpakke
  PASS: 37 tests
  PASS: 276 statements
  PASS: 84 branches
  PASS: 100 procent coverage

setup-profile testpakke
  PASS: 25 tests
  PASS: 227 statements
  PASS: 62 branches
  PASS: 100 procent coverage

CLI-tests
  PASS: 4 setup CLI tests
  PASS: 6 setup-profile CLI tests

public CLI
  PASS: 4 setup files
  PASS: 12 questions
  PASS: .agentic/setup-profile.json

samlet migreret Python-pakke
  PASS: Ruff
  PASS: strict mypy for 129 source files
  PASS: 576 tests
  PASS: Pylint duplicate-code, rating 10.00/10
  Senest separat målte coverage-baseline:
    PASS: 2.999 statements
    PASS: 952 branches
    PASS: 100 procent coverage
~~~

Den typed setupmaterialiseringsservice og guided-init application service er implementeret under application-laget og integreret med registry-loading og setup-profile-validation. De resterende init-consumers mangler fortsat og må ikke repareres gennem raw-dict compatibility logic.

Materialiseringsintegrationen er valideret med:

~~~text
dedikeret application-testpakke
  PASS: 11 tests
  PASS: 59 statements
  PASS: 28 branches
  PASS: 100 procent coverage

real-registry integration
  PASS: 4 setups med defaults
  PASS: 4 setups med OpenCode-only
  PASS: 4 setups med VS Code Copilot-only
  PASS: eksisterende .agentic/setup-profile.json matcher materialiseringen
  PASS: setup-profile-schema og semantic validator

samlet migreret Python-pakke
  PASS: Ruff
  PASS: strict mypy for 129 source files
  PASS: 576 tests
  PASS: Pylint duplicate-code, rating 10.00/10
  Senest separat målte coverage-baseline:
    PASS: 2.999 statements
    PASS: 952 branches
    PASS: 100 procent coverage
~~~

Guided-init application service er valideret isoleret med:

~~~text
dedikeret guided-init testpakke
  PASS: Ruff
  PASS: strict mypy
  PASS: 11 tests
  PASS: 58 statements
  PASS: 20 branches
  PASS: 100 procent coverage
~~~

For hver resterende slice:

* auditér schema-, validator- og CLI-kontrakten først
* tilføj typed immutable domænemodeller
* returnér strukturerede diagnostics
* tilføj unit-, contract-, negative- og integrationstests
* aktiver den nye implementation
* fjern den gamle implementation atomisk
* behold den offentlige CLI-kontrakt
* undgå compatibility fallback og parallel autoritet

#### 0.4 Opdel testarkitekturen

* erstat `test-negative-gates.py` med domæneopdelte tests
* fjern fuld-pipeline-fixtures fra komponenttests
* opret navngivne, minimale fixtures
* brug diagnostics-koder som stabile assertions
* begræns E2E til få komplette consumer-scenarier

#### 0.5 Migrér compilerens downstream-lag

* definer canonical compiled composition
* migrér runtime-schema og `agentic.json`
* migrér init og materialisering
* migrér registry-reference-validation
* migrér resolver og resolution-format
* migrér lockfile
* migrér targetgeneratorer
* migrér manifest
* migrér generated-output- og compatibility-validation
* regenerér alle outputs

### Fase 1 — Artifact contracts

* tilføj provenance og revision
* tilføj statusafhængige invariants
* tilføj reproducerbare evidenskrav
* definer artifact-specifik statussemantik

### Fase 2 — Workflows

* implementér eksplicit `BLOCKED`-routing
* afklar controller- og routingsemantik
* tilføj retry- og eskalationspolitik
* implementér artifact-invalidation
* ret review-heavy- og AI-evalueringsflow

### Fase 3 — Profiles, bundles og setups

* adskil generic og microservice profiles
* ret capability completeness
* fjern stale og placebo-baserede setupvalg
* dokumentér generalist- og specialistkompositioner

### Fase 4 — Targetmaterialisering

* bevar role-binding responsibilities og guardrails
* generér artifact-specifikke outputkrav
* materialisér fuld routing og `BLOCKED`
* harmonisér permissions på tværs af targets
* ret profile- og workflowidentitet

### Fase 5 — Dokumentation og afslutning

* opdatér `registry/README.md`
* opdatér hoved-README
* opdatér relevante udviklerguides
* regenerér lockfile, targets og manifest
* kør fuld validering
* commit og push

## Næste konkrete opgave

Migrér `init-from-bundle.py` og de resterende setup-relaterede init-consumers til den typed application- og bundlekompositionsmodel.

Guided init er nu implementeret som typed application service med adskilt terminal-IO, deterministisk setupmaterialisering, validering før writes, cancellation, back-navigation, dry-run og transaktionel rollback.

Arbejdet skal nu:

1. lade bundle eje effektiv profile, workflow, agent-instances, role bindings, skills, capabilities, permissions og artifacts
2. stoppe al læsning af `selected.profile` og `selected.workflow`
3. erstatte raw-dict-komposition med typed inputs og outputs
4. validere den materialiserede setup-profil før øvrige init-side effects
5. bevare atomiske writes og fail-fast rollback
6. tilføje isolerede unit- og integrationstests uden den fulde legacy-pipeline
7. reducere eller fjerne de tilsvarende scripts under `scripts/agentic`

Arbejdet må ikke:

* genindføre legacyfelter eller compatibility projections
* placere ny application- eller domænelogik under `scripts/agentic`
* lade terminal-UI eller launchers eje kompositionssemantik
* skrive delvise filer ved cancellation eller failure
* bruge `test-negative-gates.py` eller hele legacy-pipelinen som komponentgate

Efter migrationen af de resterende init-consumers er næste vertikale registry-slice targets.

## Autoritativ domænemodel

Chen-målmodellen er autoritativ for konceptuelle entities, boundaries, relationer og cardinalities:
- [docs/diagrams/agentic-domain-model-chen.puml](docs/diagrams/agentic-domain-model-chen.puml)


`project-status.md` indeholder kun implementeringsstatus, beslutninger, kendte mangler og prioriteret arbejde. Diagrammets fulde PlantUML-kilde vedligeholdes kun i diagramfilen.
