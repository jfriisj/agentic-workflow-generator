# Projektstatus — `agentic-workflow-generator`

Opdateret: 28. juli 2026

Denne fil er projektets autoritative status og roadmap. Den skal kun indeholde den aktuelle tilstand, afsluttede hovedleverancer, kendte mangler og næste prioriterede arbejde.

## Slutmål

`agentic-workflow-generator` skal være en deterministisk, fail-fast compiler, der kan omsætte en valideret og genanvendelig registry-komposition til et komplet, target-specifikt agentisk udviklingsmiljø.

En bruger skal kunne vælge et setup eller et bundle og uden manuel efterredigering få genereret agenter, skills, workflows, permissions, handoffs, artifact-kontrakter og targetkonfiguration, som er konsistente med hinanden og kan anvendes direkte i det valgte framework.

Projektet betragtes som færdigt, når følgende er opfyldt:

* Registry-modellen understøtter genanvendelige agentprofiler, konkrete agent-instances, role bindings, separation policies, capabilities, skills, artifact contracts, workflows, permission-profiler og target adapters.
* Den samme registry kan sammensætte både kompakte generalistsetups og specialiserede teams uden at svække sikkerhedsinvarianter eller kræve duplikerede agentdefinitioner.
* Setup vælger et bundle og aktive targets. Det valgte bundle ejer alle øvrige konkrete runtimevalg, herunder profile, workflow, agent-instances, roller, skills, capabilities, permissions, artifacts og krav om separation of duties.
* Alle workflows er fail-closed og har entydige state owners, controller-binding, transitions, gates, evidenskrav, `BLOCKED`-routing og en eksplicit default failure state.
* Artifact contracts kan validere status, provenance, revision, inputreferencer og reproducerbar evidens ved workflow-gates.
* Genereret output bevarer den fulde semantik fra registryet og er gyldigt, konsistent og operationelt anvendeligt for hvert understøttet target.
* Init, compilation, generation, lockfile og manifest er deterministiske, idempotente og byte-identiske ved gentaget kørsel med samme input.
* Ugyldige registries, usikre kompositioner, manglende bindings og outputdrift afvises eksplicit uden fallback eller silent degradation.
* Alle registrerede setups kan initialiseres og genereres fra et tomt, isoleret consumer-repository og bestå schema-, semantic-, compatibility-, runtime- og negative-gate-tests.
* Nye agents, skills, workflows, artifacts, setups, bundles, profiles og targets kan tilføjes gennem dokumenterede kontrakter uden ændringer i compilerens kerne, medmindre et nyt domænekoncept introduceres.
* Dokumentation, schemas, validators, genereret output og `project-status.md` beskriver den samme implementerede model.

Projektets mål er at generere og validere agentiske udviklingsmiljøer. Det er ikke i sig selv en modelhost, en autonom runtime-orchestrator eller en erstatning for de frameworks, som outputtet genereres til.

## Aktuel status

Projektet er i gang med en atomisk breaking migration fra den tidligere statiske agentmodel til den autoritative `AgentInstance`- og `RoleBinding`-model.

Registrydata, registry-schemaer og de semantiske validator-slices for permissions, agents, skills, artifacts, workflows, bundles, profiles, setups, materialiserede setup-profiler og target adapters er migreret. Den typed initialization pipeline kompilerer de virkelige registryfiler til én autoritativ `CompiledComposition`, som serialiseres i `.agentic/agentic.json`. Targetrendering, transaktionel materialisering, outputmanifest og outputvalidering anvender samme typed composition uden et separat resolutionlag.

Target-materialiseringsslicen er committed og pushed som `344699c`. `doctor-strict` bestod på et rent working tree med alle 109 negative gates.

Lockfile-slicen er committed og pushed som `71e4231`. Lockfile-generation og lockfile-validation er migreret fra `scripts/agentic` til typed application- og CLI-moduler. De gamle `generate-lockfile.py`- og `validate-lockfile.py`-scripts er fjernet, og shell-routeren kalder de nye CLI-grænser direkte.

Environment-slicen er committed og pushed som `b87629e`. Den består med 12 fokuserede tests, 767 samlede pytest-tests, Ruff, strict mypy over 183 sourcefiler, alle 109 negative gates og den samlede `agentic-gen.sh all`-pipeline. Det fokuserede environment-scope består Pylint med rating 10,00/10, og `doctor-strict` består på et rent working tree. En fuld `pylint src tests`-kørsel rapporterer eksisterende duplicate-code-gæld i testsuiten, som skal håndteres separat og ikke skjules.

Registry-reference- og registry-schema-slicen er committed og pushed som `4d6e190`. De offentlige shell-routes anvender nu typed application-, validation- og CLI-grænser, de to obsolete scripts er fjernet, og aktiv kompositionsdrift valideres mod den samme canonical `CompiledComposition` som targetmaterialiseringen. Slicen består med 21 fokuserede tests, 785 samlede pytest-tests, Ruff, strict mypy over 79 sourcefiler, fokuseret Pylint 10,00/10, alle 105 resterende negative gates og den samlede `agentic-gen.sh all`-pipeline. `doctor-strict` består på et rent working tree, og lockfilen indeholder 161 compilerinput.

Capability-coverage-slicen er committed og pushed som `8ad0c4d`. Den globale analyse anvender kun immutable bundle-role-bindings og registrerede skill-providers fra ét `ValidatedRegistrySnapshot`; legacy-scriptet er fjernet, og den offentlige `coverage`-route anvender det typed CLI-modul. Slicen består med 11 fokuserede tests, 796 samlede pytest-tests, Ruff, strict mypy over 82 sourcefiler, fokuseret Pylint 10,00/10, alle 104 resterende negative gates og `agentic-gen.sh all`. `doctor-strict` består på et rent working tree, og lockfilen indeholder 163 compilerinput.

Migrationen gennemføres fortsat uden compatibility projection, fallback eller parallel autoritet.

Målflowet er:

~~~text
registry
→ setup eller bundle
→ agent instances og role bindings
→ compiled composition
→ agentic.json
→ lockfile over compilerinput
→ target-output
→ output manifest over genererede filer
→ validering
~~~

### Fastlåst scope for migrationsfasen

* `CompiledComposition` er compilerens eneste interne mellemrepræsentation.
* `.agentic/agentic.json` er den persistente aktive serialisering af kompositionen.
* Det separate resolutionlag er fjernet. `.agentic/agentic.json` er den eneste persistente serialisering af den kompilerede komposition.
* Lockfile og output manifest bevares med adskilte ansvar: inputprovenance henholdsvis outputejerskab og outputintegritet.
* Runtime-context-generation er ikke del af den aktuelle compiler og må ikke materialiseres som deaktiveret konfiguration.
* Fail-closed-, artifact- og evidencekrav er compilerinvarianter, ikke konfigurerbare validation policies.
* Target adapters begrænses til identity, output paths, owned paths og permission mapping. Targetspecifik adfærd ejes af renderer-kode og contract tests.
* Der tilføjes ingen nye targets, runtime-orchestration, plugin discovery, template engine eller generisk target-DSL, før den breaking migration er green.
* Hver afsluttet migrationsslice skal samtidig opdatere kode, tests, `docs/`, relevante diagramkilder og renderede diagrammer samt `project-status.md`, så alle beskriver den samme implementerede model.

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
* Permission-, agent-, skill-, artifact-, workflow-, bundle-, profile-, setup- og setup-profile-validatorerne er migreret til den nye Python-pakkearkitektur med typed immutable domænemodeller og stabile diagnostics. `agentic-gen.sh` kalder deres CLI-moduler direkte; de midlertidige script-launchers er fjernet.
* Validation-laget anvender fælles fail-fast support for schema diagnostics, registry-identiteter og en pre-schema rejection pipeline uden fallback eller parallel autoritet.

* Typed targetrendering er implementeret eksplicit for OpenCode og VS Code Copilot og anvender agent-instance-id som runtimeidentitet.
* Targetmaterialisering bygger først en komplet kanonisk plan og skriver targetfiler og outputmanifest i én transaktion.
* Stale targetejede filer og det obsolete `resolution.json` fjernes i samme rollback-sikrede transaktion.
* Outputmanifest version `0.3.0` indeholder composition-hash, targetidentitet, ejede paths samt hashes og byte-størrelser for genererede filer.
* Typed outputvalidering kræver byte-identitet med den kanoniske renderingsplan og afviser manglende, ændrede, unmanaged og obsolete outputs.
* OpenCode-runtimevalidering kontrollerer den effektive default-agent, alle kompilerede agent-instances, modes og skills mod den typed composition.
* Ti obsolete resolution-, generator-, manifest-, cleanup- og compatibility-scripts er fjernet.

* CLI-laget anvender fælles diagnostic-rendering og et typed setup-validation context.
* Pylint duplicate-code er konfigureret som dev-gate for `src/agentic_workflow_generator` og består med rating 10,00/10.
* Setup registry og setup profiles er migreret til version `0.2.0`.
* Setupvalg ejer kun `bundle` og `targets`; profile, workflow, agent-instances, role bindings, skills, capabilities, permissions og artifacts ejes af det valgte bundle.
* Legacyfelterne `defaultBundle`, `finalRecommendation`, question-level classification-lister, option `recommends` samt setup-profile-felterne `profile` og `workflow` er fjernet uden fallback.
* Den offentlige setup-registry-CLI validerer 4 setupfiler og 12 spørgsmål, og den materialiserede `.agentic/setup-profile.json` består den nye setup-profile-validator.
* Den typed setupmaterialiseringsservice producerer immutable `SetupProfile`-objekter, anvender answer overrides eller default options og afviser ukendte, blocked eller modstridende valg fail-fast.
* Den typed guided-init application service adskiller terminal-IO fra selection og materialisering, validerer før writes og bevarer back-navigation, cancellation og dry-run.
* En typed initialization service loader hele registryet til et valideret immutable snapshot, compiler bundle-ejet runtimeautoritet til én canonical `CompiledComposition` og serialiserer den direkte til den aktive konfiguration.
* `.agentic/agentic.json` og `.agentic/schemas/agentic.schema.json` er migreret til schemaVersion `0.3.0` med fulde agent-instances, role bindings, state ownership, controller binding, workflow gates, artifact production og separation constraints. De fjernede felter `agents`, `gates`, `runtimeContext` og `validation` materialiseres ikke. Target-adapterfeltet `supportedFeatures` er fjernet og afvises eksplicit.
* De 2 registrerede target adapters er migreret til immutable typed `TargetAdapter`-, output-path- og permission-mapping-værdier med et stramt Draft 2020-12-schema.
* Target-valideringen afviser usikre eller overlappende ejerskaber, output uden for ejede paths, duplicate identities og manglende eller ukendte permission mappings med stabile `AWG-TARGET-*` diagnostics.
* Hver target adapter skal mappe præcis alle 3 registrerede permission-profiler. `ValidatedRegistrySnapshot` ejer de validerede adapterobjekter, og `CompiledTarget` refererer direkte til den validerede adapter uden en parallel target-projection.
* `validate-targets` er den eneste autoritative target-registry-kommando. `agentic-gen.sh` kalder nu CLI-modulet `agentic_workflow_generator.cli.targets` direkte. Både den separate semantikvalidator og den midlertidige script-launcher er fjernet.
* Active-config-schemaet kræver unikke target entries og `enabled: true`; disse kontrakter valideres af active-config-grænsen og ikke af target-registry-validatoren.
* Runtimevalidering af `.agentic/agentic.json` anvender nu den typed Python-CLI `agentic_workflow_generator.cli.active_config` med Draft 2020-12 og stabile `AWG-ACTIVE-CONFIG-*` diagnostics. Den separate shell-, Node- og AJV-baserede validator er fjernet.
* Den fokuserede target-slice består med 43 domain-, validation-, CLI-, contract- og integrationstests samt 17 target-gates og 2 active-config-target-gates. Hele Python-suiten består med 703 tests; Ruff, mypy og Pylint består, og Pylint vurderer pakken til 10,00/10.
* Initialization commit-grænsen schema-validerer alle outputs før side effects, springer byte-identiske filer over og skriver guided setup-profil samt aktiv konfiguration som én flerfilstransaktion med fail-fast rollback.
* Den offentlige init-CLI anvender kun typed application services. Direct bundle init, non-interactive guided init, answer overrides, dry-run, interaktivt setupvalg, back-navigation, cancellation og confirmation er bevaret uden raw registry- eller kompositionslogik i CLI-laget.
* `agentic-gen.sh` kalder nu det typed init-CLI-modul direkte. Den midlertidige `init-from-bundle.py`-launcher og de obsolete helper-moduler `init_support.py`, `setup_materializer.py` og `guided_init.py` er fjernet.
* Typed lockfile-generation og lockfile-validation er implementeret under application- og CLI-lagene med canonical inputmønstre, deterministisk SHA-256-provenance, atomisk JSON-write og stabile `AWG-LOCKFILE-*` diagnostics.
* De obsolete `generate-lockfile.py`- og `validate-lockfile.py`-scripts er fjernet. `agentic-gen.sh lock`, `validate-lockfile`, `generate` og den samlede pipeline anvender de typed CLI-moduler direkte.
* `scripts/agentic` er reduceret fra 34 til 3 resterende filer. De resterende filer er shell-orchestratoren, generation-idempotency og den monolitiske negative-gate-runner.
* Typed registry-reference-validation er implementeret under application- og CLI-lagene. Den genbruger `ValidatedRegistrySnapshot` og den canonical active-composition-grænse, så registryidentiteter, versioner og materialiseret komposition ikke valideres gennem en parallel parser.
* Typed registry-schema-validation er implementeret under validation- og CLI-lagene med Draft 2020-12, deterministisk discovery, individuel JSON-læsning og aggregerede `AWG-REGISTRY-SCHEMA-*` diagnostics for alle 46 registryfiler.
* De obsolete `validate-registry-references.py`- og `validate-registry-schemas.py`-scripts er fjernet. `agentic-gen.sh validate-references`, `validate-registry-schemas` og den samlede pipeline anvender de typed CLI-moduler direkte.
* Typed global capability coverage er implementeret under validation-, application- og CLI-lagene. Analysen anvender kun immutable `Bundle`-role-bindings og `Skill.provides` fra ét `ValidatedRegistrySnapshot`, returnerer stabile `AWG-CAPABILITY-COVERAGE-*` diagnostics og bevarer det offentlige rapportformat.
* Det obsolete `report-capability-coverage.py`-script er fjernet. `agentic-gen.sh coverage` og den samlede pipeline anvender nu det typed CLI-modul direkte. Den tidligere capability-mutation er flyttet fra den monolitiske negative-gate-runner til en fokuseret integrationstest.
* Typed environment-validation er implementeret under application-, infrastructure- og CLI-lagene med seks obligatoriske command contracts, eksplicit PATH-resolution, typed process-resultater og stabile `AWG-ENVIRONMENT-*` diagnostics.
* Det obsolete `validate-environment.py`-script er fjernet. `agentic-gen.sh validate-environment` kalder nu det typed CLI-modul direkte.
* Den aktuelle environment-slice består med 12 fokuserede tests, 767 samlede pytest-tests, Ruff, strict mypy over 183 sourcefiler, alle 109 negative gates og `agentic-gen.sh all`. Lockfilen indeholder 159 aktuelle compilerinput og dækker alle 12 schemafiler rekursivt.
* Den fokuserede init-migrationsgate består med 39 tests samt script- og JSON-syntaxkontrol.
* Alle fire setups materialiserer gyldige profiler med defaults, OpenCode-only og VS Code Copilot-only.
* `target-platforms` er nu den eneste spørgsmålsdimension, der ejer targetvalget; dobbelt target-autoritet er fjernet fra `project-domain` og `project-type`.
* Global capability coverage bruger nu `roleBindings[].requiredCapabilities` som autoritativt runtimekrav.
* Artifact-produktion valideres mod `roleBindings[].produces` i stedet for agentprofiler.
* Registry-schema-validation består for 46 registryfiler.
* De migrerede semantic validators består isoleret på den aktuelle registry.
* Obsolete felter afvises eksplicit i de migrerede schemaer og validators.
* Den konceptuelle domænemodel er opdelt i ét navigationsdiagram og fire autoritative bounded-context Chen-diagrammer med synkroniserede SVG-filer.
* `README.md`, registrydokumentationen og de autoritative dokumenter under `docs/` er synkroniseret med den reducerede compilerarkitektur uden et separat resolutionlag, runtime-context-policy eller konfigurerbar validation policy.

### Resterende migrations- og afslutningsarbejde

* `agentic-gen.sh` fungerer fortsat midlertidigt som shell-router og pipeline-orchestrator.
* `validate-generation-idempotency.py` skal migreres til pakkens application-, validation- og CLI-lag.
* Den monolitiske `test-negative-gates.py` skal erstattes af fokuserede pytest-suiter ved de relevante domæne- og application-boundaries.
* Et installeret offentligt Python-entrypoint skal overtage command-routing, pipeline, status og doctor-kontrakterne.
* Hele `scripts/agentic` skal slettes, når de sidste consumers, hooks, CI-kald og dokumentationsreferencer er migreret.
* Lockfile-slicen er committed som `71e4231`, valideret med `doctor-strict` på et rent working tree og pushed.
* Den eksisterende duplicate-code-gæld i testsuiten skal håndteres eksplicit uden at svække eller deaktivere Pylint-gaten.

Der indføres ingen compatibility projection, fallback eller parallel pre-migration-model. Hver migreret vertikal slice skal erstatte og fjerne den gamle implementation i samme ændring.

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

Disse to E2E-kommandoer tilhører den historiske før-migrationspipeline.
Det tidligere `test-isolated-e2e.py` er nu fjernet; init-E2E ligger under
pytest, mens target-runtime-E2E genetableres i target-slicen.

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

Følgende er observeret grønt på den aktuelle migrationsbranch:

~~~text
agentic-gen.sh all
  PASS: script- og JSON-syntax
  PASS: active configuration
  PASS: 46 registry-schemafiler
  PASS: 8 agents
  PASS: 10 skills og 21 capabilities
  PASS: 4 workflows og 23 gates
  PASS: 4 profiles
  PASS: 4 bundles, 27 agent instances og 27 role bindings
  PASS: 4 setups og 12 questions
  PASS: setup profile
  PASS: 3 permission profiles
  PASS: registry references
  PASS: komplet capability coverage
  PASS: 7 artifact contracts
  PASS: typed lockfile med 163 compilerinput og alle 12 schemafiler
  PASS: 2 targets og 53 kanoniske outputfiler

agentic-gen.sh test-negative
  PASS: All 104 negative gate tests passed

samlet Python-suite
  PASS: 796 tests

Ruff
  PASS

strict mypy
  PASS: 79 source files

Pylint, fokuseret registry-reference- og schema-scope
  PASS: rating 10.00/10

Pylint, samlet src og tests
  kendt test duplicate-code-gæld rapporteres
~~~

Targetrendering, materialisering, outputvalidering og OpenCode-runtimevalidering anvender den autoritative typed `CompiledComposition`. Det separate resolutionformat og dets consumers er fjernet.

Lockfile-generation og validation anvender nu én typed canonical implementation. De tidligere scripts og deres dynamiske `runpy`-kobling er fjernet.

Den historiske før-migrationsbaseline nedenfor bevares kun som reference og må ikke bruges som evidens for den aktuelle model.


## Aktuel repositorytilstand

Arbejdet foregår på branch `refactor/typed-init-consumers`.

Target-materialiseringsslicen er committed og pushed som `344699c`, og `doctor-strict` bestod på det rene working tree.

Working tree er rent. Capability-coverage-slicen er committed og pushed som `8ad0c4d`, og `doctor-strict` består med alle 104 resterende negative gates.

Den aktuelle branch består med 796 pytest-tests, Ruff, strict mypy over 82 sourcefiler, fokuseret Pylint 10,00/10, alle 104 resterende negative gates og `agentic-gen.sh all`.

De genererede outputs er canonical: materialiseringen producerer 53 filer for 2 targets, og lockfilen indeholder 163 compilerinput og alle 12 schemafiler.


## Registry-audit — vigtigste fund

### Compiler- og testarkitektur

Kodebasen er nu struktureret som en typed compiler med eksplicit dependency direction mellem domain, registry, compiler, application, validation, targets og CLI.

Resterende arkitekturarbejde:

* `agentic-gen.sh` fungerer fortsat midlertidigt som shell-router og pipeline-orchestrator
* capability-coverage- og generation-idempotency-grænserne ligger fortsat under `scripts/agentic`
* negative gates er fortsat samlet i én monolitisk runner, selv om domæneejede gates er flyttet til fokuserede pytest-suiter
* enkelte negative gates matcher fortsat tekst i stedet for stabile diagnostic-koder
* den offentlige Python-entrypoint skal overtage command-routing, pipeline, status og doctor
* hele `scripts/agentic` skal fjernes efter de sidste migrationsslices

`registry/core` er tomt og skal ikke bruges som placering for Python-kode. Registryet forbliver deklarativt compiler-input.

Ny produktionskode placeres under `src/agentic_workflow_generator`. `scripts/agentic` må kun indeholde midlertidig aktiv orkestrering eller endnu ikke migrerede grænser og skal fjernes helt, når migrationen er afsluttet.

Compiler- og validatorinfrastrukturen er stærk, men registry-indholdet er fortsat et MVP.

### Agents og skills

* `mvp-core-capabilities` er fjernet uden fallback.
* 10 fokuserede skills leverer alle 21 registrerede capabilities med én entydig provider per capability.
* Requirements, Architecture, Implementation, Test, QA, Security, AI-evaluering, code review og workflow-routing har konkrete arbejdsmetoder og evidenskontrakter.
* Alle skill-poster bruger rådgivende `recommendedAgents`; feltet begrænser ikke kompositionen.
* Skill-afhængigheder udtrykkes med `requiresCapabilities` og valideres mod registrerede capability-providers.
* Skill-validatoren afviser ugyldige typer, tomme værdier, dubletter, manglende agent- og capability-referencer samt selvafhængighed.
* CodeReviewer må ikke eje routing, og Orchestratorens routing er fail-closed.

### Typed targetmaterialisering

Følgende er observeret grøn isoleret i den aktuelle slice:

~~~text
target materialization, planning and output validation
  PASS: 18 tests

OpenCode runtime validation
  PASS: 5 tests

typed target-output negative gates
  PASS: 5 tests

generation idempotency
  PASS: 55 tracked output files
~~~

Lockfilens compilerinput omfatter nu `pyproject.toml`, `uv.lock` og hele
`src/agentic_workflow_generator/**/*.py`, så ændringer i compiler,
renderer eller materialisering ændrer inputprovenancen.

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

Den downstream target-slice er nu migreret:

* resolveren, resolution-outputtet og resolution-validatoren er fjernet
* targetrendererne bruger direkte `CompiledComposition`
* outputmanifestet er reduceret til outputejerskab og integritet
* generation er transaktionel og fjerner stale targetoutput
* generated-output- og runtimevalidering er typed
* obsolete resolution-, manifest- og cleanup-gates er fjernet

Før slicen kan afsluttes, mangler:

* review af resterende aktive dokumentationsreferencer
* genkørsel af fuld pytest-, Ruff-, strict-mypy- og Pylint-pipeline efter de sidste ændringer
* regenerering og validering af lockfilen efter dokumentationsændringerne
* samlet diff-review og `git diff --check`
* commit, `doctor-strict` på rent working tree og push

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
* targetoutput skal bevare workflowets eksisterende fail-closed routing og eksplicitte default failure state
* artifact-invalidation efter ændringer
* klar test-evidens i review-heavy-flowet
* klar execution-model for AI-evaluering

### Profiles og setups

* Profile metadata er rådgivende, mens bundle er autoritativ for workflow og konkret runtimekomposition.
* Setup-schemaet og setup-profile-schemaet duplikerer ikke længere bundle-ejede profile-, workflow-, agent-, skill- eller artifactvalg.
* Setupmaterialisering og init læser nu kun `selected.bundle` og `selected.targets`; bundle compiler resten af den konkrete runtimekomposition.
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
* De fire fokuserede Chen-diagrammer under `docs/diagrams/domain/` er autoritative for entities, relationer og cardinalities i hvert deres bounded context; oversigtsdiagrammet er kun navigation.
* Python-kode skal flyttes til en pakke under `src/agentic_workflow_generator/`.
* Tests skal opdeles under `tests/unit`, `tests/contract`, `tests/integration`, `tests/negative` og `tests/e2e`.
* `scripts/agentic/agentic-gen.sh` er kun en midlertidig migrationslauncher, må ikke eje domæne- eller compilerlogik og skal fjernes sammen med resten af `scripts/agentic`, når pakkens CLI dækker den offentlige kontrakt.
* Registry-loading, diagnostics, JSON IO, path-sikkerhed og hashing skal have én implementation.
* Rå JSON dictionaries må kun være den eksterne grænse. Compilerens interne lag skal bruge typed modeller.
* Targetgenerering skal anvende den canonical `CompiledComposition` og må ikke indføre et separat resolution- eller compiler-IR-lag.
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
12. resterende setup-relaterede init-consumers — afsluttet
13. targets — afsluttet

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

pre-migration negative gates
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

pre-migration negative gates
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

pre-migration negative gates
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

pre-migration negative gates
  17 artifact-ejede tests er fjernet fra test-negative-gates.py
  De tilsvarende cases dækkes af den isolerede artifact-testpakke
~~~

Den fulde pre-migration negative-gate-runner blev ikke gjort til artifact-slicens gate. Den starter stale downstream-targetgeneratorer, som fortsat forventer det fjernede `workflow.states[].agent`-felt.

Workflow-slicen omfatter nu:

* immutable `Workflow`, `WorkflowState`, `WorkflowGate` og `WorkflowTransition`
* eksplicit parsing fra `RegistrySource`
* strikt JSON Schema Draft 2020-12-kontrakt
* særskilte diagnostics for obsolete workflow-, state- og gatefelter
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
* fuldstændig erstatning af den 778-linjers tidligere workflow-validator
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

pre-migration negative gates
  30 workflow-ejede tests er fjernet fra test-negative-gates.py
  31 workflow-ejede mutationshelpers er fjernet
  De tilsvarende cases dækkes af den isolerede workflow-testpakke
~~~

Stale downstream-forbrug af det fjernede `workflow.states[].agent`-felt findes fortsat i resolution- og targetlagene. De må ikke repareres med compatibility projection.

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
* fuldstændig erstatning af den 1.085-linjers tidligere bundle-validator
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

pre-migration negative gates
  23 bundle-ejede semantic gates er fjernet
  2 bundle-ejede schema gates er fjernet
  5 fælles bundle-mutationshelpers er fjernet
  Den separate artifact-production-validator og dens 5 pre-migration-gates er fjernet
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

pre-migration negative gates
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
  PASS: strict mypy for 145 source files
  PASS: 678 tests
  PASS: Pylint duplicate-code for src/agentic_workflow_generator, rating 10.00/10
  Aktuel samlet coverage-baseline:
    PASS: 3.574 statements
    PASS: 982 branches
    PASS: 100 procent coverage
~~~

Den typed setupmaterialiseringsservice, guided-init application service og initialization service er implementeret under application-laget og integreret med valideret registry-loading, canonical bundlekomposition, setup-profile-validation og transaktionelle writes. Den offentlige init-consumer er migreret uden raw-dict compatibility logic.

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
  PASS: strict mypy for 145 source files
  PASS: 678 tests
  PASS: Pylint duplicate-code for src/agentic_workflow_generator, rating 10.00/10
  Aktuel samlet coverage-baseline:
    PASS: 3.574 statements
    PASS: 982 branches
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

De resterende init-consumers er migreret:

* `validate-init-idempotency` delegerer gennem en tynd launcher til den
  typed `cli.init_idempotency`-grænse.
* Gentagen direct og guided init valideres gennem
  `InitializationService`, typed planer og byte-identiske commits.
* Clean-consumer init-E2E ligger under `tests/e2e` og dækker alle fire
  registrerede setups uden pre-migration resolution- eller target-antagelser.
* `scripts/agentic/test-isolated-e2e.py` og dets offentlige
  `test-isolated-e2e`/`test-target-runtime-e2e`-routes er fjernet.
* Target-generation og runtime-E2E migreres separat i target-slicen.

~~~text
fokuseret afsluttende init-consumer-gate
  PASS: Ruff
  PASS: strict mypy
  PASS: 18 tests
  PASS: script syntax
  PASS: JSON syntax
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

#### 0.5 Migrér compilerens downstream-lag — afsluttet

* `CompiledComposition` er den eneste canonical compilerrepræsentation
* active-config-schemaet og typed deserialisering af `.agentic/agentic.json` er migreret
* init og setupmaterialisering anvender typed application services
* resolveren, resolution-formatet og deres sidste consumers er fjernet
* lockfilen følger den aktuelle compilerinputmodel
* OpenCode- og VS Code Copilot-rendererne bruger direkte `CompiledComposition`
* outputmanifest version `0.3.0` ejer kun outputprovenance og integritet
* generated-output- og runtimevalidering er typed
* alle targetoutputs er regenereret og valideret kanonisk

### Fase 1 — Artifact contracts

* tilføj provenance og revision
* tilføj statusafhængige invariants
* tilføj reproducerbare evidenskrav
* definer artifact-specifik statussemantik

### Fase 2 — Workflows

* implementér eksplicit `BLOCKED`-routing
* afklar controller- og routingsemantik
* retry- og eskalationspolitik er uden for migrationsscopet og kræver en separat beslutning efter green baseline
* artifact-invalidation er uden for migrationsscopet og kræver en separat beslutning efter green baseline
* funktionelle udvidelser af review-heavy- og AI-evalueringsflow er udsat, indtil den breaking migration er green

### Fase 3 — Profiles, bundles og setups

* adskil generic og microservice profiles
* ret capability completeness
* fjern stale og placebo-baserede setupvalg
* dokumentér generalist- og specialistkompositioner

### Fase 4 — Targetmaterialisering — afsluttet

* role-binding responsibilities, guardrails og permissions bevares direkte fra `CompiledComposition`
* artifact-specifikke outputkrav materialiseres
* fuld workflow-routing inklusive `BLOCKED` materialiseres
* OpenCode og VS Code Copilot anvender samme compilerautoritet
* agent-instance-id, profile- og workflowidentitet bevares uden afledning eller fallback
* outputplanen valideres komplet før transaktionelle writes
* stale targetoutput og obsolete resolution-output fjernes transaktionelt

### Fase 5 — Dokumentation og afslutning — igangværende

* target-materialiseringsslicen er committed, valideret med `doctor-strict` og pushed
* typed lockfile-generation og validation er implementeret
* de to obsolete lockfile-scripts er fjernet
* lockfile, targets og manifest er regenereret
* `agentic-gen.sh all` består
* registry-reference- og registry-schema-validation er migreret til typed application-, validation- og CLI-grænser
* de to obsolete registry-validation-scripts er fjernet
* alle 104 resterende negative gates består
* 796 pytest-tests, Ruff og strict mypy over 82 sourcefiler består
* det fokuserede capability-coverage-scope består Pylint med rating 10,00/10
* lockfile-slicen er committed som `71e4231`, valideret med `doctor-strict` og pushed
* environment-slicen er committed som `b87629e`, valideret med `doctor-strict` på et rent working tree og pushed
* registry-reference- og registry-schema-slicen er committed som `4d6e190`, valideret med `doctor-strict` på et rent working tree og pushed
* capability-coverage-slicen er committed som `8ad0c4d`, valideret med `doctor-strict` på et rent working tree og pushed
* de sidste 3 filer under `scripts/agentic` skal migreres og mappen derefter slettes helt

## Næste konkrete opgave

Migrér generation-idempotency fra `scripts/agentic/validate-generation-idempotency.py` til pakkens typed application-, validation- og CLI-lag.

Slicen skal:

1. kortlægge den nuværende generation-idempotency-kontrakt og alle consumers
2. anvende de eksisterende typed generation-, lockfile- og target-materialization-grænser uden parallel compilerlogik
3. bevare den offentlige `validate-idempotency`-route og dens fail-fast-kontrakt
4. returnere stabile typed diagnostics uden print-baseret valideringslogik
5. migrere den relevante negative gate til fokuserede pytest-tests
6. erstatte shell-routerens scriptkald atomisk
7. slette det obsolete idempotency-script i samme ændring
8. regenerere og validere lockfilen
9. synkronisere dokumentation og denne statusfil
10. bestå fokuserede tests, hele pipelinen og `doctor-strict`

Der må ikke indføres fallback, parallel generation, compatibility paths eller skjult normalisering af drift.


## Autoritativ domænemodel

Domænemodellen er opdelt efter bounded context.

Oversigten er kun navigation:

- [Domain overview](docs/diagrams/domain/agentic-domain-overview.puml)

De autoritative Chen-modeller er:

- [Setup and selection](docs/diagrams/domain/setup-selection-chen.puml)
- [Workflow control](docs/diagrams/domain/workflow-control-chen.puml)
- [Agent composition](docs/diagrams/domain/agent-composition-chen.puml)
- [Capabilities, artifacts and targets](docs/diagrams/domain/capabilities-artifacts-targets-chen.puml)

Hvert detaljeret diagram er autoritativt for entities, boundaries, relationer og
cardinalities i sit eget område. Cross-context entities markeres som references
og defineres fuldt i det diagram, som ejer dem.

`project-status.md` indeholder kun implementeringsstatus, beslutninger, kendte
mangler og prioriteret arbejde. PlantUML-kilder og renderede SVG-filer
vedligeholdes under `docs/diagrams/domain/`.
